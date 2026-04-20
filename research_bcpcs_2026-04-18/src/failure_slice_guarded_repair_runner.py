#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

import failure_slice_common as common
import failure_slice_runner as base
from failure_slice_common import (
    CostRates,
    DEFAULT_COST_CAP_USD,
    DEFAULT_ENDPOINT,
    REPO_ROOT,
    batch_dir,
    cost_dir,
    ensure_dir,
    estimate_text_tokens,
    load_dotenv_if_present,
    paper_dir,
    read_json,
    read_jsonl,
    repo_rel,
    request_rows_token_estimate,
    run_dir,
    safe_text,
    usage_from_batch_output_row,
    utc_now_iso,
    write_json,
    write_jsonl,
)
from failure_slice_cost_audit import audit_cost_ledger
from failure_slice_error_analyzer import analyze_run
from failure_slice_eval_v2 import evaluate_results_v2
from failure_slice_models import EvidenceLedgerRow, StageReviewOutput, validate_stage_output
from failure_slice_reports import write_leakage_audit
from failure_slice_validate import find_forbidden_prompt_terms, validate_run_artifacts
from scripts.screening.experiment_workflows import fulltext_payload_from_resolution, metadata_payload
from scripts.screening.openai_batch_runner import BatchRequestSpec, OpenAIBatchRunner, build_json_schema_response_format


LOCKED_FULL_AUTO_F1 = 0.6378
LOCKED_PRIMARY_AUTO_F1 = 0.8000
MIN_COVERAGE = 0.98
BASELINE_RUN_ID = "bcpcs_failure_slice_gpt5nano_2stage_async_2026-04-18_full127_v1"
PHASES = ("stage1_review", "stage2_review_evidence_packet", "stage2_review_decision")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidencePacketItem(StrictModel):
    claim_id: str = Field(min_length=1)
    evidence_status: Literal["support", "refute", "unknown", "not_applicable"]
    quote: str
    location: str
    source_path: str = Field(min_length=1)
    source_field: Literal["title", "abstract", "metadata", "full_text", "criteria", "other"]
    span_validated: bool
    missingness_reason: Literal[
        "none",
        "semantic_non_fit",
        "retrieval_failure",
        "metadata_ambiguity",
        "evidence_incomplete",
        "not_applicable",
    ]
    confidence: float = Field(ge=0, le=1)


class EvidencePacketOutput(StrictModel):
    candidate_key: str = Field(min_length=1)
    stage: Literal["stage2_evidence_packet"]
    extraction_status: Literal["ok", "evidence_incomplete", "retrieval_failure", "metadata_ambiguity"]
    packet_summary: str = Field(min_length=1)
    evidence_items: list[EvidencePacketItem]
    missingness_reason: Literal["none", "retrieval_failure", "metadata_ambiguity", "evidence_incomplete"]
    confidence: float = Field(ge=0, le=1)


@dataclass(frozen=True)
class GuardedProfile:
    model: str
    stage1_effort: str
    evidence_effort: str
    decision_effort: str
    stage1_max_tokens: int
    evidence_max_tokens: int
    decision_max_tokens: int
    fulltext_window_chars: int
    rates: CostRates


PROFILES = {
    "gpt-5-nano": GuardedProfile(
        model="gpt-5-nano",
        stage1_effort="high",
        evidence_effort="high",
        decision_effort="high",
        stage1_max_tokens=32768,
        evidence_max_tokens=16384,
        decision_max_tokens=16384,
        fulltext_window_chars=24000,
        rates=CostRates(input_per_million=0.05, cached_input_per_million=0.005, output_per_million=0.40, batch_discount=0.5),
    ),
    "gpt-5.4-nano": GuardedProfile(
        model="gpt-5.4-nano",
        stage1_effort="xhigh",
        evidence_effort="xhigh",
        decision_effort="xhigh",
        stage1_max_tokens=32768,
        evidence_max_tokens=16384,
        decision_max_tokens=16384,
        fulltext_window_chars=24000,
        rates=CostRates(input_per_million=0.20, cached_input_per_million=0.02, output_per_million=1.25, batch_discount=0.5),
    ),
}


PAPER_KEYWORDS = {
    "2307.05527": ["generative", "audio", "speech", "music", "synthesis", "voice", "ethical", "ethics", "misuse"],
    "2409.13738": ["process", "extraction", "natural language", "nlp", "declarative", "workflow", "empirical"],
    "2511.13936": ["preference", "ranking", "audio", "clips", "comparison", "reinforcement", "rl", "learning"],
    "2601.19926": ["transformer", "language model", "syntax", "syntactic", "grammar", "probing", "bert", "attention"],
}

STOPWORDS = {
    "about", "after", "against", "available", "based", "being", "between", "could", "criteria", "defined",
    "describes", "domain", "empirical", "evidence", "full", "includes", "inside", "model", "models", "paper",
    "papers", "primary", "research", "review", "source", "stage", "study", "text", "their", "these", "those",
    "using", "within", "without", "would",
}


def _json_block(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _apply_profile(profile: GuardedProfile) -> None:
    common.DEFAULT_MODEL = profile.model
    base.DEFAULT_MODEL = profile.model


def _cost_for_tokens(profile: GuardedProfile, *, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * profile.rates.effective_input_per_million() + (
        output_tokens / 1_000_000
    ) * profile.rates.effective_output_per_million()


def _pricing_snapshot(profile: GuardedProfile) -> dict[str, Any]:
    return {
        "captured_at": utc_now_iso(),
        "model": profile.model,
        "pricing_basis": "Batch API text tokens, per 1M tokens",
        "standard_rates_usd_per_1m": {
            "input": profile.rates.input_per_million,
            "cached_input": profile.rates.cached_input_per_million,
            "output": profile.rates.output_per_million,
        },
        "batch_discount": profile.rates.batch_discount,
        "effective_batch_rates_usd_per_1m": {
            "input": profile.rates.effective_input_per_million(),
            "output": profile.rates.effective_output_per_million(),
        },
        "sources": [
            "https://openai.com/api/pricing/",
            "https://developers.openai.com/api/docs/models/gpt-5.4-nano",
        ],
    }


def _build_body(*, profile: GuardedProfile, prompt: str, effort: str, max_tokens: int, model: type[BaseModel], schema_name: str) -> dict[str, Any]:
    return {
        "model": profile.model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(model, schema_name=schema_name),
        "reasoning_effort": effort,
        "max_completion_tokens": max_tokens,
    }


def _repair_candidate_key_if_safe(payload: dict[str, Any], expected_key: str) -> dict[str, Any]:
    observed = safe_text(payload.get("candidate_key"))
    if observed == expected_key:
        return payload
    norm = lambda text: re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    if norm(observed) != norm(expected_key):
        return payload
    repaired = dict(payload)
    repaired["candidate_key"] = expected_key
    ledger = repaired.get("evidence_ledger")
    if isinstance(ledger, list):
        repaired["evidence_ledger"] = [
            {**item, "candidate_key": expected_key} if isinstance(item, dict) else item
            for item in ledger
        ]
    return repaired


def _validate_evidence_packet(payload: EvidencePacketOutput, *, candidate_key: str) -> None:
    if payload.candidate_key != candidate_key:
        raise ValueError(f"Expected candidate_key={candidate_key}, observed={payload.candidate_key}")


def _validate_stage2(payload: StageReviewOutput, *, candidate_key: str) -> None:
    validate_stage_output(payload, stage="stage2", candidate_key=candidate_key)


def init_run(*, run_id: str, scope: Literal["primary22", "full127"], profile: GuardedProfile, cost_cap_usd: float) -> dict[str, Any]:
    _apply_profile(profile)
    manifest = base.init_run(run_id=run_id, scope=scope, reasoning_effort=profile.stage1_effort, cost_cap_usd=cost_cap_usd)
    manifest.update(
        {
            "experiment_name": "bcpcs_failure_slice_guarded_repair",
            "model": profile.model,
            "workflow": "guarded_allroute_evidencepacket_two_pass_batch",
            "status": "initialized_guarded_repair",
            "is_failure_slice_dev_diagnostic": True,
            "not_unbiased_evaluation": True,
            "locked_baseline": {
                "baseline_run_id": BASELINE_RUN_ID,
                "full127_all_auto_f1_min": LOCKED_FULL_AUTO_F1,
                "primary22_auto_f1_min": LOCKED_PRIMARY_AUTO_F1,
                "coverage_min": MIN_COVERAGE,
                "runtime_failure_max": 0,
            },
            "guarded_profile": {
                "stage1_effort": profile.stage1_effort,
                "evidence_effort": profile.evidence_effort,
                "decision_effort": profile.decision_effort,
                "stage1_max_tokens": profile.stage1_max_tokens,
                "evidence_max_tokens": profile.evidence_max_tokens,
                "decision_max_tokens": profile.decision_max_tokens,
                "fulltext_window_chars": profile.fulltext_window_chars,
                "stage1_policy": "diagnostic all-route: Stage 1 exclude does not block Stage 2 except cutoff/artifact gates",
                "stage2_policy": "two pass: evidence packet over local windows, then strict JSON decision over evidence packet",
            },
        }
    )
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    write_json(cost_dir(run_id) / "pricing_snapshot.json", _pricing_snapshot(profile))
    return manifest


def _criteria_terms(criteria: dict[str, Any]) -> list[str]:
    text = json.dumps(criteria, ensure_ascii=False).lower()
    raw = re.findall(r"[a-z][a-z0-9_-]{4,}", text)
    counts = Counter(token.replace("_", "-") for token in raw if token not in STOPWORDS)
    return [term for term, _ in counts.most_common(30)]


def _metadata_terms(metadata: dict[str, Any]) -> list[str]:
    text = " ".join([safe_text(metadata.get("title") or metadata.get("query_title")), safe_text(metadata.get("abstract"))]).lower()
    raw = re.findall(r"[a-z][a-z0-9_-]{4,}", text)
    counts = Counter(token for token in raw if token not in STOPWORDS)
    return [term for term, _ in counts.most_common(20)]


def _make_windows(*, paper_id: str, criteria: dict[str, Any], metadata: dict[str, Any], fulltext_text: str, source_path: str, max_chars: int) -> dict[str, Any]:
    terms = list(dict.fromkeys(PAPER_KEYWORDS.get(paper_id, []) + _metadata_terms(metadata) + _criteria_terms(criteria)))
    normalized = fulltext_text.replace("\r\n", "\n")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    scored: list[tuple[int, int, str]] = []
    lower_terms = [term.lower() for term in terms if term]
    for index, para in enumerate(paragraphs):
        lower = para.lower()
        score = sum(3 if " " in term and term in lower else lower.count(term) for term in lower_terms)
        if re.match(r"^#{1,4}\s+", para):
            score += 2
        if score:
            scored.append((score, index, para))
    selected_indices: set[int] = set()
    budget = max_chars
    intro = normalized[: min(4000, len(normalized))]
    tail = normalized[-3000:] if len(normalized) > 3000 else ""
    used = len(intro) + len(tail)
    for _score, index, _para in sorted(scored, key=lambda item: (-item[0], item[1])):
        for neighbor in (index - 1, index, index + 1):
            if neighbor < 0 or neighbor >= len(paragraphs) or neighbor in selected_indices:
                continue
            chunk_len = len(paragraphs[neighbor]) + 120
            if used + chunk_len > budget:
                continue
            selected_indices.add(neighbor)
            used += chunk_len
        if used >= budget:
            break
    windows = [
        {"window_id": "intro", "location": "full_text:intro", "text": intro, "source_path": source_path}
    ]
    for index in sorted(selected_indices):
        windows.append(
            {
                "window_id": f"kw_{index}",
                "location": f"full_text:paragraph_{index}",
                "text": paragraphs[index],
                "source_path": source_path,
            }
        )
    if tail and used < budget:
        windows.append({"window_id": "tail", "location": "full_text:tail", "text": tail, "source_path": source_path})
    return {
        "selection_policy": "intro + keyword-scored local paragraph windows + tail within char budget",
        "keywords": terms[:40],
        "max_chars": max_chars,
        "selected_window_count": len(windows),
        "windows": windows,
    }


def _compact_stage1(stage1_output: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(stage1_output, dict):
        return {"available": False}
    return {
        "available": True,
        "final_stage_decision": stage1_output.get("final_stage_decision"),
        "missingness_reason": stage1_output.get("missingness_reason"),
        "confidence": stage1_output.get("confidence"),
        "route_reason": stage1_output.get("route_reason"),
        "unknown_reason": stage1_output.get("unknown_reason"),
        "ledger": [
            {
                "claim_id": row.get("claim_id"),
                "evidence_status": row.get("evidence_status"),
                "missingness_reason": row.get("missingness_reason"),
                "confidence": row.get("confidence"),
                "quote": row.get("quote"),
            }
            for row in (stage1_output.get("evidence_ledger") or [])[:5]
            if isinstance(row, dict)
        ],
    }


def build_evidence_packet_prompt(
    *,
    paper_id: str,
    candidate_key: str,
    criteria: dict[str, Any],
    metadata: dict[str, Any],
    stage1_output: dict[str, Any] | None,
    fulltext_windows: dict[str, Any],
    criteria_path: str,
    metadata_path: str,
) -> str:
    visible_record = {
        "paper_id": paper_id,
        "candidate_key": candidate_key,
        "title": metadata.get("title") or metadata.get("query_title") or "",
        "abstract": metadata.get("abstract") or "",
        "metadata": {
            "source": metadata.get("source"),
            "source_id": metadata.get("source_id"),
            "match_status": metadata.get("match_status"),
            "missing_reason": metadata.get("missing_reason"),
            "published_date": metadata.get("published_date"),
        },
        "source_paths": {"criteria_path": criteria_path, "metadata_path": metadata_path},
        "stage1_bcpcs_handoff_compact": _compact_stage1(stage1_output),
    }
    rules = {
        "task": "Extract a short evidence packet only. Do not make the final include/exclude decision.",
        "quote_policy": "Quotes must be exact substrings from supplied fields/windows. Prefer 2-6 short decisive quotes.",
        "missing_policy": "If local windows are insufficient, use extraction_status=evidence_incomplete rather than fabricating evidence.",
        "anti_leakage": "Do not use prior verdicts, gold labels, error taxonomies, or external knowledge.",
    }
    return "\n\n".join(
        [
            "You are preparing a BCPCS evidence packet for a later screening decision.",
            "Use only the criteria, visible candidate record, Stage 1 handoff, and full-text windows supplied here.",
            "Return only valid JSON matching the schema.",
            "Rules:",
            _json_block(rules),
            "Stage 2 criteria JSON:",
            _json_block(criteria),
            "Candidate visible record:",
            _json_block(visible_record),
            "Full-text local windows:",
            _json_block(fulltext_windows),
        ]
    )


def build_decision_prompt(
    *,
    paper_id: str,
    candidate_key: str,
    criteria: dict[str, Any],
    metadata: dict[str, Any],
    stage1_output: dict[str, Any] | None,
    evidence_packet: dict[str, Any],
    criteria_path: str,
    metadata_path: str,
) -> str:
    visible_record = {
        "paper_id": paper_id,
        "candidate_key": candidate_key,
        "title": metadata.get("title") or metadata.get("query_title") or "",
        "abstract": metadata.get("abstract") or "",
        "metadata": {
            "source": metadata.get("source"),
            "source_id": metadata.get("source_id"),
            "match_status": metadata.get("match_status"),
            "missing_reason": metadata.get("missing_reason"),
            "published_date": metadata.get("published_date"),
        },
        "source_paths": {"criteria_path": criteria_path, "metadata_path": metadata_path},
        "stage1_bcpcs_handoff_compact": _compact_stage1(stage1_output),
    }
    rules = {
        "task": "Make the final Stage 2 screening decision from criteria, metadata, Stage 1 handoff, and the evidence packet.",
        "decision_values": ["include", "exclude", "maybe", "unknown"],
        "rationale_limit": "Keep decision_rationale under 80 words.",
        "ledger_policy": "Use evidence_packet quotes as ledger spans. Do not invent quotes not present in the packet.",
        "missing_policy": "If packet evidence is incomplete for a semantic decision, use unknown/evidence_incomplete.",
        "anti_leakage": "Do not use prior verdicts, gold labels, error taxonomies, or external knowledge.",
    }
    return "\n\n".join(
        [
            "You are a single screening reviewer running Stage 2 of a BCPCS failure-slice diagnostic.",
            "Return only valid JSON matching the StageReviewOutput schema.",
            "Rules:",
            _json_block(rules),
            "Stage 2 criteria JSON:",
            _json_block(criteria),
            "Candidate visible record:",
            _json_block(visible_record),
            "Evidence packet:",
            _json_block(evidence_packet),
        ]
    )


def _stage1_specs(*, run_path: Path, profile: GuardedProfile) -> list[BatchRequestSpec]:
    base.MAX_COMPLETION_TOKENS = profile.stage1_max_tokens
    specs = base.prepare_stage1_specs(run_path=run_path, reasoning_effort=profile.stage1_effort)
    fixed: list[BatchRequestSpec] = []
    for spec in specs:
        body = dict(spec.body)
        body["model"] = profile.model
        body["reasoning_effort"] = profile.stage1_effort
        body["max_completion_tokens"] = profile.stage1_max_tokens
        fixed.append(
            BatchRequestSpec(
                custom_id=spec.custom_id,
                model=profile.model,
                body=body,
                response_model=StageReviewOutput,
                validator=spec.validator,
                context=spec.context,
            )
        )
    return fixed


def _load_stage1_by_key(run_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    return base._load_stage_records_by_key(run_path, "stage1_review")


def _load_evidence_by_key(run_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted((run_path / "papers").glob("*/stage2_evidence_packet.json")):
        paper_id = path.parent.name
        rows = read_json(path)
        if not isinstance(rows, list):
            continue
        for row in rows:
            key = safe_text(row.get("candidate_key"))
            if key:
                out[(paper_id, key)] = row
    return out


def _evidence_specs(*, run_path: Path, profile: GuardedProfile) -> list[BatchRequestSpec]:
    specs: list[BatchRequestSpec] = []
    paper_data = base._prepare_common(run_path)
    stage1_by_key = _load_stage1_by_key(run_path)
    for paper_id, data in paper_data.items():
        criteria_path = base._criteria_path(paper_id, "stage2")
        criteria = read_json(criteria_path)
        metadata_path = base._metadata_path(paper_id)
        selected: list[str] = []
        for record in data["records"]:
            key = safe_text(record.get("key"))
            cutoff_decision = data["cutoff_result"]["decisions_by_key"][key]
            artifact_decision = data["artifact_result"]["decisions_by_key"][key]
            if not cutoff_decision["cutoff_pass"] or not artifact_decision["gate_pass"]:
                continue
            resolution = data["resolution_by_key"][key]
            if resolution["resolution_status"] not in {"exact", "normalized"} or not resolution.get("fulltext_gate_pass", True):
                continue
            selected.append(key)
            fulltext_text, fulltext_meta = fulltext_payload_from_resolution(
                resolution,
                repo_root=REPO_ROOT,
                head_chars=120_000,
                tail_chars=0,
            )
            windows = _make_windows(
                paper_id=paper_id,
                criteria=criteria,
                metadata=metadata_payload(record),
                fulltext_text=fulltext_text,
                source_path=safe_text(fulltext_meta.get("fulltext_source_path") or resolution.get("resolved_path")),
                max_chars=profile.fulltext_window_chars,
            )
            stage1 = stage1_by_key.get((paper_id, key))
            prompt = build_evidence_packet_prompt(
                paper_id=paper_id,
                candidate_key=key,
                criteria=criteria,
                metadata=metadata_payload(record),
                stage1_output=stage1["review_output"] if stage1 else None,
                fulltext_windows=windows,
                criteria_path=repo_rel(criteria_path),
                metadata_path=repo_rel(metadata_path),
            )
            specs.append(
                BatchRequestSpec(
                    custom_id=f"stage2_evidence_packet__{paper_id}__{key}",
                    model=profile.model,
                    body=_build_body(
                        profile=profile,
                        prompt=prompt,
                        effort=profile.evidence_effort,
                        max_tokens=profile.evidence_max_tokens,
                        model=EvidencePacketOutput,
                        schema_name="BCPCSEvidencePacketOutput",
                    ),
                    response_model=EvidencePacketOutput,
                    validator=lambda payload, expected_key=key: _validate_evidence_packet(payload, candidate_key=expected_key),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                        "phase": "stage2_review_evidence_packet",
                        "stage": "stage2_evidence_packet",
                        "criteria_path": repo_rel(criteria_path),
                        "metadata_path": repo_rel(metadata_path),
                        "fulltext_resolution": resolution,
                        "all_route_policy": True,
                    },
                )
            )
        selection_path = paper_dir(run_path.name, paper_id) / "selected_for_stage2_allroute.keys.txt"
        selection_path.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")
    return specs


def _decision_specs(*, run_path: Path, profile: GuardedProfile) -> list[BatchRequestSpec]:
    specs: list[BatchRequestSpec] = []
    paper_data = base._prepare_common(run_path)
    stage1_by_key = _load_stage1_by_key(run_path)
    evidence_by_key = _load_evidence_by_key(run_path)
    for paper_id, data in paper_data.items():
        criteria_path = base._criteria_path(paper_id, "stage2")
        criteria = read_json(criteria_path)
        metadata_path = base._metadata_path(paper_id)
        for record in data["records"]:
            key = safe_text(record.get("key"))
            evidence_row = evidence_by_key.get((paper_id, key))
            if not evidence_row:
                continue
            stage1 = stage1_by_key.get((paper_id, key))
            prompt = build_decision_prompt(
                paper_id=paper_id,
                candidate_key=key,
                criteria=criteria,
                metadata=metadata_payload(record),
                stage1_output=stage1["review_output"] if stage1 else None,
                evidence_packet=evidence_row["review_output"],
                criteria_path=repo_rel(criteria_path),
                metadata_path=repo_rel(metadata_path),
            )
            specs.append(
                BatchRequestSpec(
                    custom_id=f"stage2_decision__{paper_id}__{key}",
                    model=profile.model,
                    body=_build_body(
                        profile=profile,
                        prompt=prompt,
                        effort=profile.decision_effort,
                        max_tokens=profile.decision_max_tokens,
                        model=StageReviewOutput,
                        schema_name="BCPCSStageReviewOutput",
                    ),
                    response_model=StageReviewOutput,
                    validator=lambda payload, expected_key=key: _validate_stage2(payload, candidate_key=expected_key),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                        "phase": "stage2_review_decision",
                        "stage": "stage2",
                        "criteria_path": repo_rel(criteria_path),
                        "metadata_path": repo_rel(metadata_path),
                        "all_route_policy": True,
                    },
                )
            )
    return specs


def prepare_specs(*, run_path: Path, phase: str, profile: GuardedProfile) -> list[BatchRequestSpec]:
    if phase == "stage1_review":
        return _stage1_specs(run_path=run_path, profile=profile)
    if phase == "stage2_review_evidence_packet":
        return _evidence_specs(run_path=run_path, profile=profile)
    if phase == "stage2_review_decision":
        return _decision_specs(run_path=run_path, profile=profile)
    raise ValueError(f"Unsupported phase: {phase}")


def _serialize(specs: list[BatchRequestSpec]) -> list[dict[str, Any]]:
    return [{"custom_id": spec.custom_id, "method": "POST", "url": DEFAULT_ENDPOINT, "body": spec.body} for spec in specs]


def _prompt_hits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in rows:
        terms = find_forbidden_prompt_terms(json.dumps(row.get("body", {}), ensure_ascii=False))
        if terms:
            hits.append({"custom_id": row.get("custom_id"), "terms": terms})
    return hits


def _current_cost(run_id: str) -> float:
    path = cost_dir(run_id) / "cost_summary.json"
    if not path.exists():
        return 0.0
    return float(read_json(path).get("total_cost_usd") or 0.0)


def _max_tokens_for_phase(profile: GuardedProfile, phase: str) -> int:
    if phase == "stage1_review":
        return profile.stage1_max_tokens
    if phase == "stage2_review_evidence_packet":
        return profile.evidence_max_tokens
    return profile.decision_max_tokens


def _pre_submit_estimate(*, run_id: str, phase: str, profile: GuardedProfile, rows: list[dict[str, Any]], cost_cap_usd: float) -> dict[str, Any]:
    input_tokens = request_rows_token_estimate(rows)
    output_tokens = len(rows) * _max_tokens_for_phase(profile, phase)
    estimated_cost = _cost_for_tokens(profile, input_tokens=input_tokens, output_tokens=output_tokens)
    prior = _current_cost(run_id)
    payload = {
        "phase": phase,
        "created_at": utc_now_iso(),
        "request_count": len(rows),
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost,
        "prior_actual_or_estimated_cost_usd": prior,
        "projected_total_cost_usd": prior + estimated_cost,
        "cost_cap_usd": cost_cap_usd,
        "would_exceed_cost_cap": prior + estimated_cost > cost_cap_usd,
        "estimate_policy": "input tokenizer_or_char_overestimate; output phase max_completion_tokens per request",
    }
    write_json(cost_dir(run_id) / f"pre_submit_estimate.{phase}.json", payload)
    return payload


def submit_phase(*, run_id: str, phase: str, profile: GuardedProfile, cost_cap_usd: float, dry_run: bool = False) -> dict[str, Any]:
    _apply_profile(profile)
    rd = run_dir(run_id)
    specs = prepare_specs(run_path=rd, phase=phase, profile=profile)
    artifact_dir = ensure_dir(batch_dir(run_id, phase, profile.model))
    rows = _serialize(specs)
    write_jsonl(artifact_dir / "input.jsonl", rows)
    estimate = _pre_submit_estimate(run_id=run_id, phase=phase, profile=profile, rows=rows, cost_cap_usd=cost_cap_usd)
    hits = _prompt_hits(rows)
    if hits:
        payload = {"created_at": utc_now_iso(), "phase": phase, "reason": "forbidden_prompt_terms", "hits": hits}
        write_json(artifact_dir / "leakage_stop.json", payload)
        raise RuntimeError(f"Forbidden prompt fields detected for {phase}: {hits[:3]}")
    if estimate["would_exceed_cost_cap"]:
        payload = {"created_at": utc_now_iso(), "phase": phase, "reason": "cost_cap_projected_exceeded", "estimate": estimate}
        write_json(cost_dir(run_id) / "cost_stop.json", payload)
        return payload
    if dry_run or not specs:
        payload = {
            "batch_id": None,
            "batch_status": "dry_run_not_submitted" if dry_run else "skipped_no_requests",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
        write_json(artifact_dir / "parsed_results.json", payload)
        return {"phase": phase, "batch_status": payload["batch_status"], "request_count": len(specs), "pre_submit_estimate": estimate}
    load_dotenv_if_present()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; cannot submit Batch job.")
    from openai import OpenAI

    client = OpenAI()
    client.models.retrieve(profile.model)
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=30.0)
    submit_payload = runner.submit_requests(
        specs=specs,
        endpoint=DEFAULT_ENDPOINT,
        artifact_dir=artifact_dir,
        metadata={"experiment": "bcpcs_guarded_repair", "run_id": run_id, "phase": phase, "model": profile.model},
    )
    manifest = read_json(rd / "run_manifest.json")
    manifest.setdefault("phase_jobs", {})[phase] = {
        "phase": phase,
        "batch_artifact_dir": repo_rel(artifact_dir),
        "batch_id": submit_payload["batch_create"]["id"],
        "batch_status": submit_payload["batch_create"]["status"],
        "request_count": len(specs),
        "pre_submit_estimate": estimate,
        "upload_file_id": submit_payload["upload_file"]["id"],
    }
    manifest["status"] = f"submitted_{phase}"
    manifest["updated_at"] = utc_now_iso()
    write_json(rd / "run_manifest.json", manifest)
    return manifest["phase_jobs"][phase]


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _assistant_content(row: dict[str, Any]) -> str:
    body = row.get("response", {}).get("body", {})
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message")
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
    raise ValueError("response body missing assistant message content")


def _parse_outputs(*, specs: list[BatchRequestSpec], artifact_dir: Path, batch_payload: dict[str, Any]) -> dict[str, Any]:
    output_rows = read_jsonl(artifact_dir / "output.jsonl") if (artifact_dir / "output.jsonl").exists() else []
    error_rows = read_jsonl(artifact_dir / "error.jsonl") if (artifact_dir / "error.jsonl").exists() else []
    output_by_id = {str(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
    error_by_id = {str(row.get("custom_id")): row for row in error_rows if row.get("custom_id")}
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for spec in specs:
        if spec.custom_id in error_by_id:
            failures.append({"custom_id": spec.custom_id, "status": "error_file", "context": spec.context, "error": error_by_id[spec.custom_id]})
            continue
        raw_row = output_by_id.get(spec.custom_id)
        if raw_row is None:
            missing.append({"custom_id": spec.custom_id, "status": "missing", "context": spec.context})
            continue
        try:
            response = raw_row.get("response")
            if not isinstance(response, dict) or int(response.get("status_code") or 0) != 200:
                raise ValueError(f"status_code={response.get('status_code') if isinstance(response, dict) else None}")
            text = _assistant_content(raw_row)
            raw_payload = json.loads(_strip_json_fence(text))
            if isinstance(raw_payload, dict):
                raw_payload = _repair_candidate_key_if_safe(raw_payload, safe_text(spec.context.get("candidate_key")))
            parsed = spec.response_model.model_validate(raw_payload)
            if spec.validator is not None:
                spec.validator(parsed)
            successes.append(
                {
                    "custom_id": spec.custom_id,
                    "status": "ok",
                    "context": spec.context,
                    "assistant_text": text,
                    "parsed": parsed.model_dump(mode="json"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "custom_id": spec.custom_id,
                    "status": "parse_or_validation_failed",
                    "context": spec.context,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "raw_output": raw_row,
                }
            )
    payload = {
        "batch_id": batch_payload.get("id"),
        "batch_status": batch_payload.get("status"),
        "successes": successes,
        "failures": failures,
        "missing": missing,
        "output_row_count": len(output_rows),
        "error_row_count": len(error_rows),
    }
    write_json(artifact_dir / "parsed_results.json", payload)
    return payload


def _write_phase_outputs(*, run_id: str, phase: str, parsed: dict[str, Any]) -> None:
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    target_name = "stage1_review.json" if phase == "stage1_review" else (
        "stage2_evidence_packet.json" if phase == "stage2_review_evidence_packet" else "stage2_review.json"
    )
    for item in parsed.get("successes", []):
        ctx = item["context"]
        rows_by_paper[ctx["paper_id"]].append(
            {
                "paper_id": ctx["paper_id"],
                "candidate_key": ctx["candidate_key"],
                "candidate_title": ctx["candidate_title"],
                "phase": phase,
                "stage": ctx["stage"],
                "model": ctx.get("model") or "",
                "criteria_path": ctx["criteria_path"],
                "metadata_path": ctx["metadata_path"],
                "review_output": item["parsed"],
            }
        )
    for paper_id, rows in rows_by_paper.items():
        rows.sort(key=lambda row: row["candidate_key"])
        write_json(paper_dir(run_id, paper_id) / target_name, rows)
    for paper_id in base._cases_by_paper(run_dir(run_id)):
        path = paper_dir(run_id, paper_id) / target_name
        if not path.exists():
            write_json(path, [])


def _update_cost(*, run_id: str, phase: str, profile: GuardedProfile, artifact_dir: Path, specs: list[BatchRequestSpec], parsed: dict[str, Any]) -> dict[str, Any]:
    output_rows = read_jsonl(artifact_dir / "output.jsonl") if (artifact_dir / "output.jsonl").exists() else []
    output_by_id = {str(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
    success_by_id = {row["custom_id"]: row for row in parsed.get("successes", [])}
    from failure_slice_common import append_jsonl

    batch_id = safe_text(parsed.get("batch_id"))
    for spec in specs:
        raw = output_by_id.get(spec.custom_id, {})
        usage = usage_from_batch_output_row(raw)
        text = safe_text(success_by_id.get(spec.custom_id, {}).get("assistant_text"))
        if usage and "input_tokens" in usage and "output_tokens" in usage:
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
            source = "batch_usage"
        else:
            input_tokens = estimate_text_tokens(json.dumps(spec.body, ensure_ascii=False))
            output_tokens = estimate_text_tokens(text) if text else _max_tokens_for_phase(profile, phase)
            source = "estimated"
        cost = _cost_for_tokens(profile, input_tokens=input_tokens, output_tokens=output_tokens)
        append_jsonl(
            cost_dir(run_id) / "cost_ledger.jsonl",
            {
                "created_at": utc_now_iso(),
                "phase": phase,
                "custom_id": spec.custom_id,
                "batch_id": batch_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "cost_source": source,
            },
        )
    return audit_cost_ledger(run_path=run_dir(run_id), rewrite_summary=True)["deduped_summary"]


def collect_phase(*, run_id: str, phase: str, profile: GuardedProfile, poll_interval_sec: float, max_wait_minutes: float) -> dict[str, Any]:
    _apply_profile(profile)
    rd = run_dir(run_id)
    specs = prepare_specs(run_path=rd, phase=phase, profile=profile)
    artifact_dir = batch_dir(run_id, phase, profile.model)
    batch_payload = None
    for name in ("batch_latest.json", "batch_create.json"):
        path = artifact_dir / name
        if path.exists():
            batch_payload = read_json(path)
            break
    if batch_payload is None or not batch_payload.get("id"):
        parsed = read_json(artifact_dir / "parsed_results.json") if (artifact_dir / "parsed_results.json").exists() else {
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
    else:
        load_dotenv_if_present()
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set; cannot collect Batch job.")
        from openai import OpenAI

        runner = OpenAIBatchRunner(client=OpenAI(), poll_interval_sec=poll_interval_sec)
        latest = runner.wait_until_terminal(str(batch_payload["id"]), artifact_dir=artifact_dir, max_wait_minutes=max_wait_minutes)
        if latest.get("status") in {"failed", "expired", "cancelled"}:
            write_json(artifact_dir / "terminal_failure.json", latest)
        output_text = runner.download_file_text(latest.get("output_file_id"))
        error_text = runner.download_file_text(latest.get("error_file_id"))
        if output_text is not None:
            (artifact_dir / "output.jsonl").write_text(output_text, encoding="utf-8")
        if error_text is not None:
            (artifact_dir / "error.jsonl").write_text(error_text, encoding="utf-8")
        parsed = _parse_outputs(specs=specs, artifact_dir=artifact_dir, batch_payload=latest)
        batch_payload = latest
    _write_phase_outputs(run_id=run_id, phase=phase, parsed=parsed)
    cost_summary = _update_cost(run_id=run_id, phase=phase, profile=profile, artifact_dir=artifact_dir, specs=specs, parsed=parsed)
    manifest = read_json(rd / "run_manifest.json")
    manifest.setdefault("phase_jobs", {}).setdefault(phase, {}).update(
        {
            "batch_status": parsed.get("batch_status"),
            "parsed_summary": {
                "success_count": len(parsed.get("successes", [])),
                "failure_count": len(parsed.get("failures", [])),
                "missing_count": len(parsed.get("missing", [])),
            },
            "cost_summary": cost_summary.get("phases", {}).get(phase),
        }
    )
    manifest["status"] = f"collected_{phase}"
    manifest["updated_at"] = utc_now_iso()
    write_json(rd / "run_manifest.json", manifest)
    return parsed


def assemble_allroute(*, run_id: str) -> list[dict[str, Any]]:
    rd = run_dir(run_id)
    cases = read_json(rd / "failure_slice_keys.json")["cases"]
    paper_data = base._prepare_common(rd)
    stage1_by_key = _load_stage1_by_key(rd)
    stage2_by_key = base._load_stage_records_by_key(rd, "stage2_review")
    rows: list[dict[str, Any]] = []
    for case in cases:
        paper_id = case["paper_id"]
        key = case["candidate_key"]
        data = paper_data[paper_id]
        record = data["record_by_key"][key]
        cutoff = data["cutoff_result"]["decisions_by_key"][key]
        artifact = data["artifact_result"]["decisions_by_key"][key]
        resolution = data["resolution_by_key"][key]
        stage1 = stage1_by_key.get((paper_id, key))
        stage2 = stage2_by_key.get((paper_id, key))
        review_state = "reviewed"
        discard_reason = None
        final_stage = "stage2"
        if not cutoff["cutoff_pass"]:
            review_state = "cutoff_filtered"
            discard_reason = "cutoff_time_window"
            final_decision = "exclude"
            final_stage = "cutoff"
        elif not artifact["gate_pass"]:
            review_state = "artifact_filtered"
            discard_reason = f"artifact_gate:{artifact.get('gate_reason')}"
            final_decision = "exclude"
            final_stage = "artifact_gate"
        elif stage2:
            final_decision = safe_text(stage2["review_output"].get("final_stage_decision")) or "unknown"
        elif resolution["resolution_status"] not in {"exact", "normalized"}:
            review_state = "fulltext_unresolved"
            discard_reason = resolution["resolution_status"]
            final_decision = "unknown"
        elif not stage1:
            review_state = "stage1_not_available"
            final_decision = "unknown"
            final_stage = "stage1"
        else:
            review_state = "stage2_not_available"
            final_decision = "unknown"
        rows.append(
            {
                "paper_id": paper_id,
                "candidate_key": key,
                "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                "slice_type": case["slice_type"],
                "allowed_for_unbiased_eval": case["allowed_for_unbiased_eval"],
                "review_state": review_state,
                "discard_reason": discard_reason,
                "final_stage": final_stage,
                "final_stage_decision": final_decision,
                "final_verdict": f"{final_decision} ({final_stage})",
                "stage1_output": stage1["review_output"] if stage1 else None,
                "stage2_output": stage2["review_output"] if stage2 else None,
                "fulltext_resolution_status": resolution["resolution_status"],
                "fulltext_source_path": resolution.get("resolved_path"),
                "all_route_policy": True,
            }
        )
    rows.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    write_json(rd / "assembled_results.json", rows)
    for paper_id in sorted({row["paper_id"] for row in rows}):
        write_json(paper_dir(run_id, paper_id) / "single_reviewer_batch_results.json", [row for row in rows if row["paper_id"] == paper_id])
    return rows


def evaluate_validate_analyze(*, run_id: str, baseline_run_id: str | None = BASELINE_RUN_ID) -> dict[str, Any]:
    rd = run_dir(run_id)
    assemble_allroute(run_id=run_id)
    evaluation = evaluate_results_v2(run_dir=rd)
    validation = validate_run_artifacts(rd)
    write_leakage_audit(run_id=run_id, run_dir=rd, validation=validation)
    analysis = analyze_run(candidate_run_dir=rd, baseline_run_dir=run_dir(baseline_run_id) if baseline_run_id else None)
    return {"evaluation": evaluation, "validation": validation, "analysis": analysis}


def guardrail_status(*, run_id: str, scope: str) -> dict[str, Any]:
    summary = read_json(run_dir(run_id) / "evaluation_summary_v2.json")
    primary = summary["primary22"]
    all_rows = summary["all127"]
    if scope == "primary22":
        f1 = float(primary["auto_decidable_f1"]["f1"])
        coverage = float(primary["coverage"]["definite_decision_rate"])
        runtime = int(primary["coverage"]["runtime_failure_count"])
        passed = f1 >= LOCKED_PRIMARY_AUTO_F1 and coverage >= MIN_COVERAGE and runtime == 0
    else:
        f1 = float(all_rows["auto_decidable_f1"]["f1"])
        coverage = float(all_rows["coverage"]["definite_decision_rate"])
        runtime = int(all_rows["coverage"]["runtime_failure_count"])
        passed = f1 >= LOCKED_FULL_AUTO_F1 and coverage >= MIN_COVERAGE and runtime == 0
    payload = {
        "created_at": utc_now_iso(),
        "scope": scope,
        "passed": passed,
        "observed_auto_f1": f1,
        "observed_coverage": coverage,
        "observed_runtime_failure_count": runtime,
        "thresholds": {
            "primary22_auto_f1_min": LOCKED_PRIMARY_AUTO_F1,
            "full127_all_auto_f1_min": LOCKED_FULL_AUTO_F1,
            "coverage_min": MIN_COVERAGE,
            "runtime_failure_max": 0,
        },
    }
    write_json(run_dir(run_id) / "guardrail_status.json", payload)
    return payload


def run_one(*, run_id: str, scope: Literal["primary22", "full127"], profile: GuardedProfile, cost_cap_usd: float, poll_interval_sec: float, max_wait_minutes: float) -> dict[str, Any]:
    init_run(run_id=run_id, scope=scope, profile=profile, cost_cap_usd=cost_cap_usd)
    for phase in PHASES:
        submit_payload = submit_phase(run_id=run_id, phase=phase, profile=profile, cost_cap_usd=cost_cap_usd)
        if submit_payload.get("reason") == "cost_cap_projected_exceeded":
            return {"run_id": run_id, "status": "paused_cost_cap_before_submit", "phase": phase}
        parsed = collect_phase(run_id=run_id, phase=phase, profile=profile, poll_interval_sec=poll_interval_sec, max_wait_minutes=max_wait_minutes)
        if parsed.get("batch_status") in {"failed", "expired", "cancelled"}:
            evaluate_validate_analyze(run_id=run_id)
            return {"run_id": run_id, "status": "terminal_batch_failure", "phase": phase}
        if parsed.get("failures") or parsed.get("missing"):
            evaluate_validate_analyze(run_id=run_id)
            guard = guardrail_status(run_id=run_id, scope=scope)
            return {"run_id": run_id, "status": "parse_or_missing_failure", "phase": phase, "guardrail": guard}
        if _current_cost(run_id) > cost_cap_usd:
            evaluate_validate_analyze(run_id=run_id)
            return {"run_id": run_id, "status": "paused_cost_cap_after_collect", "phase": phase}
    result = evaluate_validate_analyze(run_id=run_id)
    guard = guardrail_status(run_id=run_id, scope=scope)
    manifest = read_json(run_dir(run_id) / "run_manifest.json")
    manifest["status"] = "guardrail_passed" if guard["passed"] else "guardrail_failed"
    manifest["guardrail_status_path"] = repo_rel(run_dir(run_id) / "guardrail_status.json")
    manifest["updated_at"] = utc_now_iso()
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    return {"run_id": run_id, "status": manifest["status"], "guardrail": guard, **result}


def write_guarded_report(*, run_ids: list[str], queue_status: dict[str, Any]) -> None:
    lines = [
        "# BCPCS Guarded Repair Report",
        "",
        "這是 failure-slice dev diagnostic，不是 full benchmark，也不是 unbiased improvement claim。",
        "",
        "## Locked Guardrails",
        "",
        f"- primary22 auto F1 must be >= `{LOCKED_PRIMARY_AUTO_F1:.4f}`",
        f"- full127 all auto F1 must be >= `{LOCKED_FULL_AUTO_F1:.4f}`",
        f"- coverage must be >= `{MIN_COVERAGE:.2%}`",
        "- runtime failures must be `0`",
        "",
        "## Run Results",
        "",
        "| run_id | scope | model | auto F1 | conservative F1 | coverage | runtime failures | guardrail | cost |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for run_id in run_ids:
        rd = run_dir(run_id)
        if not (rd / "evaluation_summary_v2.json").exists():
            continue
        eval_payload = read_json(rd / "evaluation_summary_v2.json")
        manifest = read_json(rd / "run_manifest.json")
        guard = read_json(rd / "guardrail_status.json") if (rd / "guardrail_status.json").exists() else {"passed": False}
        cost_path = rd / "cost" / "cost_summary.json"
        cost = read_json(cost_path).get("total_cost_usd") if cost_path.exists() else None
        scope_key = "primary22" if eval_payload.get("scope") == "primary22" else "all127"
        bucket = eval_payload[scope_key]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{run_id}`",
                    str(eval_payload.get("scope")),
                    f"`{manifest.get('model')}`",
                    f"{bucket['auto_decidable_f1']['f1']:.4f}",
                    f"{bucket['conservative_f1']['f1']:.4f}",
                    f"{bucket['coverage']['definite_decision_rate']:.2%}",
                    str(bucket["coverage"]["runtime_failure_count"]),
                    "passed" if guard.get("passed") else "failed",
                    f"${float(cost):.6f}" if cost is not None else "n/a",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Queue Status",
            "",
            "```json",
            json.dumps(queue_status, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Interpretation",
            "",
            "- 任何低於 locked guardrail 的 variant 都只能保留為 failed diagnostic，不得 promote。",
            "- dev analyzer 可使用 gold 做錯誤分類，但 gold/error taxonomy 沒有進入 reviewer prompts。",
            "- 如果 primary smoke 失敗，full127 不會提交。",
        ]
    )
    write_path = common.REPORTS_ROOT / "failure_slice_guarded_repair_zh.md"
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_queue(*, cost_cap_usd: float, poll_interval_sec: float, max_wait_minutes: float) -> dict[str, Any]:
    today = "2026-04-20"
    queue = [
        {
            "run_id": f"bcpcs_guarded_primary22_smoke_gpt54nano_xhigh_allroute_evidencepacket_{today}_v1",
            "scope": "primary22",
            "profile": PROFILES["gpt-5.4-nano"],
        },
        {
            "run_id": f"bcpcs_guarded_primary22_smoke_gpt5nano_high_allroute_evidencepacket_{today}_v1",
            "scope": "primary22",
            "profile": PROFILES["gpt-5-nano"],
        },
    ]
    completed: list[str] = []
    statuses: list[dict[str, Any]] = []
    primary_passed = True
    for item in queue:
        result = run_one(
            run_id=item["run_id"],
            scope=item["scope"],
            profile=item["profile"],
            cost_cap_usd=cost_cap_usd,
            poll_interval_sec=poll_interval_sec,
            max_wait_minutes=max_wait_minutes,
        )
        completed.append(item["run_id"])
        statuses.append({"run_id": item["run_id"], "status": result.get("status"), "guardrail": result.get("guardrail")})
        if not result.get("guardrail", {}).get("passed"):
            primary_passed = False
    queue_status: dict[str, Any] = {
        "created_at": utc_now_iso(),
        "primary_smoke_passed": primary_passed,
        "full127_submitted": False,
        "statuses": statuses,
    }
    if primary_passed:
        full_queue = [
            {
                "run_id": f"bcpcs_guarded_full127_gpt54nano_xhigh_allroute_evidencepacket_{today}_v1",
                "scope": "full127",
                "profile": PROFILES["gpt-5.4-nano"],
            },
            {
                "run_id": f"bcpcs_guarded_full127_gpt5nano_high_allroute_evidencepacket_{today}_v1",
                "scope": "full127",
                "profile": PROFILES["gpt-5-nano"],
            },
        ]
        queue_status["full127_submitted"] = True
        for item in full_queue:
            result = run_one(
                run_id=item["run_id"],
                scope=item["scope"],
                profile=item["profile"],
                cost_cap_usd=cost_cap_usd,
                poll_interval_sec=poll_interval_sec,
                max_wait_minutes=max_wait_minutes,
            )
            completed.append(item["run_id"])
            statuses.append({"run_id": item["run_id"], "status": result.get("status"), "guardrail": result.get("guardrail")})
            if not result.get("guardrail", {}).get("passed"):
                queue_status["full127_guardrail_failed"] = True
    else:
        queue_status["stop_reason"] = "primary22_smoke_guardrail_failed"
    write_guarded_report(run_ids=completed, queue_status=queue_status)
    return queue_status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["run-queue", "run-one", "evaluate", "report"], required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--scope", choices=["primary22", "full127"], default="primary22")
    parser.add_argument("--model", choices=sorted(PROFILES), default="gpt-5.4-nano")
    parser.add_argument("--cost-cap-usd", type=float, default=DEFAULT_COST_CAP_USD)
    parser.add_argument("--poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--max-wait-minutes", type=float, default=24 * 60.0)
    args = parser.parse_args()
    if args.mode == "run-queue":
        payload = run_queue(
            cost_cap_usd=args.cost_cap_usd,
            poll_interval_sec=args.poll_interval_sec,
            max_wait_minutes=args.max_wait_minutes,
        )
    elif args.mode == "run-one":
        if not args.run_id:
            raise SystemExit("--run-id is required for run-one")
        payload = run_one(
            run_id=args.run_id,
            scope=args.scope,
            profile=PROFILES[args.model],
            cost_cap_usd=args.cost_cap_usd,
            poll_interval_sec=args.poll_interval_sec,
            max_wait_minutes=args.max_wait_minutes,
        )
    elif args.mode == "evaluate":
        if not args.run_id:
            raise SystemExit("--run-id is required for evaluate")
        payload = evaluate_validate_analyze(run_id=args.run_id)
        payload["guardrail"] = guardrail_status(run_id=args.run_id, scope=args.scope)
    else:
        runs = [args.run_id] if args.run_id else []
        write_guarded_report(run_ids=[run for run in runs if run], queue_status={"manual_report": True})
        payload = {"reported": runs}
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
