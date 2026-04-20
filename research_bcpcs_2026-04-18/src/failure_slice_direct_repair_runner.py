#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

import failure_slice_runner as base
from failure_slice_common import (
    CostRates,
    DEFAULT_COST_CAP_USD,
    REPO_ROOT,
    REPORTS_ROOT,
    append_jsonl,
    cost_dir,
    ensure_dir,
    estimate_text_tokens,
    load_dotenv_if_present,
    paper_dir,
    read_json,
    repo_rel,
    run_dir,
    safe_text,
    utc_now_iso,
    write_json,
    write_jsonl,
)
from failure_slice_cost_audit import audit_cost_ledger
from failure_slice_error_analyzer import analyze_run
from failure_slice_eval_v2 import evaluate_results_v2
from failure_slice_inventory import freeze_inventory_files
from failure_slice_models import EvidenceLedgerRow, EvidenceSpan, MissingnessReason, StageReviewOutput
from failure_slice_reports import write_leakage_audit
from failure_slice_validate import find_forbidden_prompt_terms, validate_run_artifacts
from scripts.screening.experiment_workflows import fulltext_payload_from_resolution, metadata_payload
from scripts.screening.openai_batch_runner import build_json_schema_response_format


LOCKED_FULL_AUTO_F1 = 0.6378
LOCKED_PRIMARY_AUTO_F1 = 0.8000
MIN_COVERAGE = 0.98
BASELINE_RUN_ID = "bcpcs_failure_slice_gpt5nano_2stage_async_2026-04-18_full127_v1"
TODAY = "2026-04-20"
STAGE2_PHASE = "stage2_direct_decision"
CANARY_SIZE = 5


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompactDecisionOutput(StrictModel):
    candidate_key: str = Field(min_length=1)
    stage: Literal["stage2_compact_decision"]
    final_stage_decision: Literal["include", "exclude", "maybe", "unknown"]
    reason_code: Literal[
        "semantic_fit",
        "semantic_non_fit",
        "retrieval_failure",
        "metadata_ambiguity",
        "source_gold_tension",
        "evidence_incomplete",
        "not_applicable",
    ]
    confidence: float = Field(ge=0, le=1)
    support_quote_ids: list[str] = Field(default_factory=list)
    refute_quote_ids: list[str] = Field(default_factory=list)
    missingness_reason: MissingnessReason
    decision_rationale: str = Field(min_length=1, max_length=700)

    @model_validator(mode="after")
    def _unknown_has_reason(self) -> "CompactDecisionOutput":
        if self.final_stage_decision == "unknown" and self.missingness_reason == "none":
            raise ValueError("unknown decision must not use missingness_reason=none")
        return self


@dataclass(frozen=True)
class DirectProfile:
    profile_id: str
    model: str
    reasoning_effort: str
    max_completion_tokens: int
    evidence_packet_chars: int
    max_quotes: int
    rates: CostRates


PROFILES: dict[str, DirectProfile] = {
    "direct_gpt54nano_xhigh_localpacket_compactdecision_v1": DirectProfile(
        profile_id="direct_gpt54nano_xhigh_localpacket_compactdecision_v1",
        model="gpt-5.4-nano",
        reasoning_effort="xhigh",
        max_completion_tokens=32768,
        evidence_packet_chars=14000,
        max_quotes=18,
        rates=CostRates(input_per_million=0.20, cached_input_per_million=0.02, output_per_million=1.25, batch_discount=0.0),
    ),
    "direct_gpt54nano_high_localpacket_compactdecision_v1": DirectProfile(
        profile_id="direct_gpt54nano_high_localpacket_compactdecision_v1",
        model="gpt-5.4-nano",
        reasoning_effort="high",
        max_completion_tokens=16384,
        evidence_packet_chars=14000,
        max_quotes=18,
        rates=CostRates(input_per_million=0.20, cached_input_per_million=0.02, output_per_million=1.25, batch_discount=0.0),
    ),
    "direct_gpt5nano_high_localpacket_compactdecision_v1": DirectProfile(
        profile_id="direct_gpt5nano_high_localpacket_compactdecision_v1",
        model="gpt-5-nano",
        reasoning_effort="high",
        max_completion_tokens=16384,
        evidence_packet_chars=14000,
        max_quotes=18,
        rates=CostRates(input_per_million=0.05, cached_input_per_million=0.005, output_per_million=0.40, batch_discount=0.0),
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
    "using", "within", "without", "would", "shall", "should", "must", "only", "include", "exclude",
}


def _json_block(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _git_status_short() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout.splitlines()


def _status_paths(lines: list[str]) -> set[str]:
    paths: set[str] = set()
    for line in lines:
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.add(path)
    return paths


def _direct_cost(profile: DirectProfile, *, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * profile.rates.input_per_million + (
        output_tokens / 1_000_000
    ) * profile.rates.output_per_million


def _pricing_snapshot(profile: DirectProfile) -> dict[str, Any]:
    return {
        "captured_at": utc_now_iso(),
        "model": profile.model,
        "pricing_basis": "direct synchronous Chat Completions text tokens, per 1M tokens",
        "standard_rates_usd_per_1m": {
            "input": profile.rates.input_per_million,
            "cached_input": profile.rates.cached_input_per_million,
            "output": profile.rates.output_per_million,
        },
        "batch_discount": 0.0,
        "sources": [
            "https://openai.com/api/pricing/",
            "https://platform.openai.com/docs/pricing/",
        ],
        "notes": [
            "Direct repair intentionally does not use Batch API.",
            "Cost calculation is conservative and does not subtract cached-token discounts.",
        ],
    }


def _limit_inventory(run_path: Path, *, limit: int | None) -> None:
    if limit is None:
        return
    public = read_json(run_path / "failure_slice_keys.json")
    private = read_json(run_path / "evaluation_inventory_private.json")
    public_cases = public["cases"][:limit]
    private_cases = private["cases"][:limit]
    for payload, cases in ((public, public_cases), (private, private_cases)):
        payload["cases"] = cases
        payload["summary"] = {
            **payload["summary"],
            "selected_count": len(cases),
            "selected_primary_count": sum(1 for row in cases if row["slice_type"] == "non_tension_primary"),
            "selected_secondary_count": sum(1 for row in cases if row["slice_type"] == "criteria_gold_tension_secondary"),
            "sample_limit": limit,
        }
    write_json(run_path / "failure_slice_keys.json", public)
    write_json(run_path / "evaluation_inventory_private.json", private)
    write_json(run_path / "sample_definition.json", {"sample_limit": limit, "sample_policy": "first rows from frozen inventory order"})


def init_direct_run(
    *,
    run_id: str,
    scope: Literal["primary22", "full127"],
    profile: DirectProfile,
    cost_cap_usd: float,
    limit: int | None = None,
) -> dict[str, Any]:
    rd = ensure_dir(run_dir(run_id))
    ensure_dir(rd / "direct_calls" / STAGE2_PHASE / profile.profile_id)
    ensure_dir(rd / "papers")
    ensure_dir(rd / "logs")
    ensure_dir(cost_dir(run_id))
    freeze_inventory_files(run_dir=rd, scope=scope)
    _limit_inventory(rd, limit=limit)
    source_counts = read_json(rd / "failure_slice_keys.json")["summary"]
    pre_status = _git_status_short()
    manifest = {
        "run_id": run_id,
        "experiment_name": "bcpcs_failure_slice_direct_repair",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "scope": scope,
        "sample_limit": limit,
        "model": profile.model,
        "profile_id": profile.profile_id,
        "endpoint": "/v1/chat/completions",
        "reviewer": "single_reviewer",
        "workflow": "direct_sync_allroute_localpacket_compactdecision",
        "reasoning_effort": profile.reasoning_effort,
        "max_completion_tokens": profile.max_completion_tokens,
        "cost_cap_usd": cost_cap_usd,
        "status": "initialized_direct",
        "run_dir": repo_rel(rd),
        "is_failure_slice_dev_diagnostic": True,
        "not_unbiased_evaluation": True,
        "not_full_benchmark_evidence": True,
        "write_scope": "research_bcpcs_2026-04-18 only",
        "source_counts": source_counts,
        "locked_baseline": {
            "baseline_run_id": BASELINE_RUN_ID,
            "full127_all_auto_f1_min": LOCKED_FULL_AUTO_F1,
            "primary22_auto_f1_min": LOCKED_PRIMARY_AUTO_F1,
            "coverage_min": MIN_COVERAGE,
            "runtime_failure_max": 0,
        },
        "direct_policy": {
            "batch_api_used": False,
            "stage1_policy": "synthetic diagnostic all-route handoff for every cutoff/artifact-passing row",
            "evidence_policy": "deterministic local quote windows; no LLM evidence extraction pass",
            "decision_policy": "one short strict-JSON final decision call per candidate, with one identical retry on parse/runtime failure",
        },
        "pre_run_git_status_short": pre_status,
        "pre_run_outside_research_changes": sorted(
            path for path in _status_paths(pre_status) if not path.startswith("research_bcpcs_2026-04-18/")
        ),
    }
    write_json(rd / "run_manifest.json", manifest)
    write_json(cost_dir(run_id) / "pricing_snapshot.json", _pricing_snapshot(profile))
    return manifest


def _criteria_terms(criteria: dict[str, Any]) -> list[str]:
    text = json.dumps(criteria, ensure_ascii=False).lower()
    raw = re.findall(r"[a-z][a-z0-9_-]{4,}", text)
    counts = Counter(token.replace("_", "-") for token in raw if token not in STOPWORDS)
    return [term for term, _ in counts.most_common(35)]


def _metadata_terms(metadata: dict[str, Any]) -> list[str]:
    text = " ".join([safe_text(metadata.get("title") or metadata.get("query_title")), safe_text(metadata.get("abstract"))]).lower()
    raw = re.findall(r"[a-z][a-z0-9_-]{4,}", text)
    counts = Counter(token for token in raw if token not in STOPWORDS)
    return [term for term, _ in counts.most_common(24)]


def _shorten(text: str, *, max_chars: int) -> str:
    normalized = re.sub(r"\s+", " ", safe_text(text))
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _quote_row(
    *,
    quote_id: str,
    text: str,
    location: str,
    source_path: str,
    source_field: Literal["title", "abstract", "metadata", "full_text", "criteria", "other"],
) -> dict[str, Any]:
    return {
        "quote_id": quote_id,
        "text": _shorten(text, max_chars=900),
        "location": location,
        "source_path": source_path,
        "source_field": source_field,
    }


def build_local_evidence_packet(
    *,
    paper_id: str,
    criteria: dict[str, Any],
    metadata: dict[str, Any],
    fulltext_text: str,
    source_path: str,
    metadata_path: str,
    max_chars: int,
    max_quotes: int,
) -> dict[str, Any]:
    quotes: list[dict[str, Any]] = []
    title = safe_text(metadata.get("title") or metadata.get("query_title"))
    abstract = safe_text(metadata.get("abstract"))
    if title:
        quotes.append(_quote_row(quote_id="q_title", text=title, location="metadata:title", source_path=metadata_path, source_field="title"))
    if abstract:
        quotes.append(
            _quote_row(quote_id="q_abstract", text=abstract, location="metadata:abstract", source_path=metadata_path, source_field="abstract")
        )

    terms = list(dict.fromkeys(PAPER_KEYWORDS.get(paper_id, []) + _metadata_terms(metadata) + _criteria_terms(criteria)))
    normalized = fulltext_text.replace("\r\n", "\n")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    scored: list[tuple[int, int, str]] = []
    lower_terms = [term.lower() for term in terms if term]
    for index, para in enumerate(paragraphs):
        lower = para.lower()
        score = 0
        for term in lower_terms:
            if " " in term:
                score += 4 if term in lower else 0
            else:
                score += min(lower.count(term), 3)
        if re.match(r"^#{1,4}\s+", para):
            score += 2
        if score:
            scored.append((score, index, para))

    used = sum(len(row["text"]) for row in quotes)
    selected_indices: set[int] = set()
    for _score, index, _para in sorted(scored, key=lambda item: (-item[0], item[1])):
        for neighbor in (index - 1, index, index + 1):
            if neighbor < 0 or neighbor >= len(paragraphs) or neighbor in selected_indices:
                continue
            para = paragraphs[neighbor]
            chunk = _shorten(para, max_chars=900)
            if used + len(chunk) > max_chars or len(quotes) >= max_quotes:
                continue
            selected_indices.add(neighbor)
            quotes.append(
                _quote_row(
                    quote_id=f"q_ft_{neighbor}",
                    text=chunk,
                    location=f"full_text:paragraph_{neighbor}",
                    source_path=source_path,
                    source_field="full_text",
                )
            )
            used += len(chunk)
        if used >= max_chars or len(quotes) >= max_quotes:
            break

    if len(quotes) < max_quotes and normalized:
        intro = _shorten(normalized[:2500], max_chars=900)
        if intro:
            quotes.append(
                _quote_row(
                    quote_id="q_ft_intro",
                    text=intro,
                    location="full_text:intro",
                    source_path=source_path,
                    source_field="full_text",
                )
            )

    return {
        "selection_policy": "title + abstract + keyword-scored full-text paragraph windows, deterministic/no model extraction",
        "keywords": terms[:45],
        "max_chars": max_chars,
        "quotes": quotes[:max_quotes],
    }


def build_synthetic_stage1_output(*, candidate_key: str, metadata: dict[str, Any], metadata_path: str) -> dict[str, Any]:
    title = safe_text(metadata.get("title") or metadata.get("query_title")) or "title unavailable"
    span = EvidenceSpan(
        quote=title,
        location="metadata:title",
        source_path=metadata_path,
        source_field="title",
    )
    ledger = EvidenceLedgerRow(
        candidate_key=candidate_key,
        stage="stage1",
        claim_id="diagnostic_allroute_stage1",
        evidence_status="unknown",
        support_spans=[span],
        refute_spans=[],
        missingness_reason="deferred_to_stage2",
        confidence=0.5,
        verifier_model="deterministic_allroute_policy",
        quote=title,
        location="metadata:title",
        source_path=metadata_path,
        span_validated=True,
    )
    return StageReviewOutput(
        candidate_key=candidate_key,
        stage="stage1",
        final_stage_decision="route_to_stage2",
        decision_rationale="Diagnostic all-route policy: defer screening decision to Stage 2.",
        route_reason="diagnostic_all_route_to_stage2",
        unknown_reason="",
        missingness_reason="deferred_to_stage2",
        confidence=0.5,
        evidence_ledger=[ledger],
    ).model_dump(mode="json")


def write_synthetic_stage1(*, run_id: str) -> None:
    rd = run_dir(run_id)
    paper_data = base._prepare_common(rd)
    for paper_id, data in paper_data.items():
        metadata_path = repo_rel(base._metadata_path(paper_id))
        rows: list[dict[str, Any]] = []
        for record in data["records"]:
            key = safe_text(record.get("key"))
            cutoff = data["cutoff_result"]["decisions_by_key"][key]
            artifact = data["artifact_result"]["decisions_by_key"][key]
            if not cutoff["cutoff_pass"] or not artifact["gate_pass"]:
                continue
            output = build_synthetic_stage1_output(
                candidate_key=key,
                metadata=metadata_payload(record),
                metadata_path=metadata_path,
            )
            rows.append(
                {
                    "paper_id": paper_id,
                    "candidate_key": key,
                    "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                    "phase": "stage1_review",
                    "stage": "stage1",
                    "model": "deterministic_allroute_policy",
                    "criteria_path": repo_rel(base._criteria_path(paper_id, "stage1")),
                    "metadata_path": metadata_path,
                    "review_output": output,
                }
            )
        rows.sort(key=lambda row: row["candidate_key"])
        write_json(paper_dir(run_id, paper_id) / "stage1_review.json", rows)


def _compact_stage1(stage1_output: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(stage1_output, dict):
        return {"available": False}
    return {
        "available": True,
        "final_stage_decision": stage1_output.get("final_stage_decision"),
        "missingness_reason": stage1_output.get("missingness_reason"),
        "confidence": stage1_output.get("confidence"),
        "route_reason": stage1_output.get("route_reason"),
    }


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
        "task": "Make the final Stage 2 screening decision from supplied criteria and quote packet.",
        "decision_values": ["include", "exclude", "maybe", "unknown"],
        "quote_policy": "Do not copy quote text into output. Refer only to quote_id values from evidence_packet.",
        "output_size": "Return compact JSON only. Keep decision_rationale under 80 words.",
        "missing_policy": "If supplied quotes are insufficient for semantic decision, return unknown with evidence_incomplete.",
        "retrieval_policy": "Do not call retrieval problems semantic_non_fit.",
        "anti_leakage": "Use no answer-key fields, previous-run outputs, error taxonomies, forensic notes, or external knowledge.",
    }
    return "\n\n".join(
        [
            "You are a single screening reviewer running Stage 2 of a BCPCS failure-slice diagnostic.",
            "Use only the criteria, visible candidate record, Stage 1 handoff, and deterministic evidence packet supplied below.",
            "Return only valid JSON matching the CompactDecisionOutput schema. No markdown fences.",
            "Rules:",
            _json_block(rules),
            "Stage 2 criteria JSON:",
            _json_block(criteria),
            "Candidate visible record:",
            _json_block(visible_record),
            "Deterministic evidence packet:",
            _json_block(evidence_packet),
        ]
    )


def _build_body(*, profile: DirectProfile, prompt: str) -> dict[str, Any]:
    return {
        "model": profile.model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(CompactDecisionOutput, schema_name="BCPCSCompactDecisionOutput"),
        "reasoning_effort": profile.reasoning_effort,
        "max_completion_tokens": profile.max_completion_tokens,
    }


def _stage1_by_key(run_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    return base._load_stage_records_by_key(run_path, "stage1_review")


def prepare_direct_requests(*, run_id: str, profile: DirectProfile) -> list[dict[str, Any]]:
    rd = run_dir(run_id)
    paper_data = base._prepare_common(rd)
    stage1_by_key = _stage1_by_key(rd)
    requests: list[dict[str, Any]] = []
    for paper_id, data in paper_data.items():
        criteria_path = base._criteria_path(paper_id, "stage2")
        criteria = read_json(criteria_path)
        metadata_path = base._metadata_path(paper_id)
        selected: list[str] = []
        for record in data["records"]:
            key = safe_text(record.get("key"))
            cutoff = data["cutoff_result"]["decisions_by_key"][key]
            artifact = data["artifact_result"]["decisions_by_key"][key]
            if not cutoff["cutoff_pass"] or not artifact["gate_pass"]:
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
            source_path = safe_text(fulltext_meta.get("fulltext_source_path") or resolution.get("resolved_path"))
            evidence_packet = build_local_evidence_packet(
                paper_id=paper_id,
                criteria=criteria,
                metadata=metadata_payload(record),
                fulltext_text=fulltext_text,
                source_path=source_path,
                metadata_path=repo_rel(metadata_path),
                max_chars=profile.evidence_packet_chars,
                max_quotes=profile.max_quotes,
            )
            stage1 = stage1_by_key.get((paper_id, key))
            prompt = build_decision_prompt(
                paper_id=paper_id,
                candidate_key=key,
                criteria=criteria,
                metadata=metadata_payload(record),
                stage1_output=stage1["review_output"] if stage1 else None,
                evidence_packet=evidence_packet,
                criteria_path=repo_rel(criteria_path),
                metadata_path=repo_rel(metadata_path),
            )
            custom_id = f"{STAGE2_PHASE}__{paper_id}__{key}"
            requests.append(
                {
                    "custom_id": custom_id,
                    "paper_id": paper_id,
                    "candidate_key": key,
                    "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                    "phase": STAGE2_PHASE,
                    "stage": "stage2",
                    "criteria_path": repo_rel(criteria_path),
                    "metadata_path": repo_rel(metadata_path),
                    "fulltext_resolution": resolution,
                    "evidence_packet": evidence_packet,
                    "body": _build_body(profile=profile, prompt=prompt),
                }
            )
        write_json(paper_dir(run_id, paper_id) / "selected_for_stage2_direct_allroute.keys.json", selected)
    return requests


def _prompt_hits(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in requests:
        terms = find_forbidden_prompt_terms(json.dumps(row.get("body", {}), ensure_ascii=False))
        if terms:
            hits.append({"custom_id": row["custom_id"], "terms": terms})
    return hits


def _current_cost(run_id: str) -> float:
    path = cost_dir(run_id) / "cost_summary.json"
    if not path.exists():
        return 0.0
    return float(read_json(path).get("total_cost_usd") or 0.0)


def write_pre_submit_estimate(
    *,
    run_id: str,
    profile: DirectProfile,
    requests: list[dict[str, Any]],
    cost_cap_usd: float,
) -> dict[str, Any]:
    input_tokens = sum(estimate_text_tokens(json.dumps(row["body"], ensure_ascii=False)) for row in requests)
    output_tokens = len(requests) * profile.max_completion_tokens
    estimated_cost = _direct_cost(profile, input_tokens=input_tokens, output_tokens=output_tokens)
    prior = _current_cost(run_id)
    payload = {
        "phase": STAGE2_PHASE,
        "created_at": utc_now_iso(),
        "request_count": len(requests),
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost,
        "prior_actual_or_estimated_cost_usd": prior,
        "projected_total_cost_usd": prior + estimated_cost,
        "cost_cap_usd": cost_cap_usd,
        "would_exceed_cost_cap": prior + estimated_cost > cost_cap_usd,
        "estimate_policy": "input tokenizer_or_char_overestimate; output profile max_completion_tokens per direct request",
    }
    write_json(cost_dir(run_id) / f"pre_submit_estimate.{STAGE2_PHASE}.json", payload)
    return payload


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


def _normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _repair_candidate_key_if_safe(payload: dict[str, Any], expected_key: str) -> dict[str, Any]:
    observed = safe_text(payload.get("candidate_key"))
    if observed == expected_key:
        return payload
    if _normalize_key(observed) != _normalize_key(expected_key):
        return payload
    repaired = dict(payload)
    repaired["candidate_key"] = expected_key
    return repaired


def _response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if isinstance(response, dict):
        return response
    return json.loads(json.dumps(response, default=str))


def _assistant_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    raise ValueError("response missing assistant message content")


def _usage_tokens(response_payload: dict[str, Any]) -> tuple[int, int, str]:
    usage = response_payload.get("usage")
    if isinstance(usage, dict):
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            return input_tokens, output_tokens, "direct_usage"
    return 0, 0, "missing_usage"


def _call_one(request: dict[str, Any], *, profile: DirectProfile, attempt: int) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    started = time.time()
    try:
        response = client.chat.completions.create(**request["body"])
        elapsed = time.time() - started
        response_payload = _response_to_dict(response)
        assistant_text = _assistant_content(response_payload)
        raw_payload = json.loads(_strip_json_fence(assistant_text))
        if not isinstance(raw_payload, dict):
            raise ValueError("assistant JSON root is not an object")
        raw_payload = _repair_candidate_key_if_safe(raw_payload, request["candidate_key"])
        parsed = CompactDecisionOutput.model_validate(raw_payload)
        if parsed.candidate_key != request["candidate_key"]:
            raise ValueError(f"candidate_key mismatch: {parsed.candidate_key} != {request['candidate_key']}")
        return {
            "custom_id": request["custom_id"],
            "attempt": attempt,
            "status": "ok",
            "context": {key: request[key] for key in ("paper_id", "candidate_key", "candidate_title", "phase", "stage", "criteria_path", "metadata_path")},
            "elapsed_sec": elapsed,
            "assistant_text": assistant_text,
            "parsed": parsed.model_dump(mode="json"),
            "raw_response": response_payload,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed = time.time() - started
        raw = locals().get("response_payload")
        return {
            "custom_id": request["custom_id"],
            "attempt": attempt,
            "status": "failed",
            "context": {key: request[key] for key in ("paper_id", "candidate_key", "candidate_title", "phase", "stage", "criteria_path", "metadata_path")},
            "elapsed_sec": elapsed,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_response": raw if isinstance(raw, dict) else None,
        }


def _quote_by_id(evidence_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {safe_text(row.get("quote_id")): row for row in evidence_packet.get("quotes", []) if safe_text(row.get("quote_id"))}


def _ledger_row(
    *,
    candidate_key: str,
    status: Literal["support", "refute", "unknown", "not_applicable"],
    quote: dict[str, Any] | None,
    claim_id: str,
    missingness_reason: MissingnessReason,
    confidence: float,
    verifier_model: str,
) -> dict[str, Any]:
    if quote is None:
        return EvidenceLedgerRow(
            candidate_key=candidate_key,
            stage="stage2",
            claim_id=claim_id,
            evidence_status=status,
            support_spans=[],
            refute_spans=[],
            missingness_reason=missingness_reason,
            confidence=confidence,
            verifier_model=verifier_model,
            quote="",
            location="compact_decision:no_valid_quote_id",
            source_path="research_bcpcs_2026-04-18/generated_direct_decision",
            span_validated=False,
        ).model_dump(mode="json")
    span = EvidenceSpan(
        quote=safe_text(quote.get("text")) or "",
        location=safe_text(quote.get("location")) or "unknown",
        source_path=safe_text(quote.get("source_path")) or "unknown",
        source_field=quote.get("source_field") if quote.get("source_field") in {"title", "abstract", "metadata", "full_text", "criteria", "other"} else "other",
    )
    return EvidenceLedgerRow(
        candidate_key=candidate_key,
        stage="stage2",
        claim_id=claim_id,
        evidence_status=status,
        support_spans=[span] if status == "support" else [],
        refute_spans=[span] if status == "refute" else [],
        missingness_reason=missingness_reason,
        confidence=confidence,
        verifier_model=verifier_model,
        quote=span.quote,
        location=span.location,
        source_path=span.source_path,
        span_validated=True,
    ).model_dump(mode="json")


def compact_to_stage_output(*, request: dict[str, Any], compact: dict[str, Any], profile: DirectProfile) -> dict[str, Any]:
    quotes = _quote_by_id(request["evidence_packet"])
    support_ids = [qid for qid in compact.get("support_quote_ids", []) if qid in quotes]
    refute_ids = [qid for qid in compact.get("refute_quote_ids", []) if qid in quotes]
    missingness = compact.get("missingness_reason") or ("evidence_incomplete" if compact.get("final_stage_decision") == "unknown" else "none")
    ledger: list[dict[str, Any]] = []
    for index, qid in enumerate(support_ids[:3], start=1):
        ledger.append(
            _ledger_row(
                candidate_key=request["candidate_key"],
                status="support",
                quote=quotes[qid],
                claim_id=f"support_{index}",
                missingness_reason=missingness,
                confidence=float(compact.get("confidence") or 0.0),
                verifier_model=profile.model,
            )
        )
    for index, qid in enumerate(refute_ids[:3], start=1):
        ledger.append(
            _ledger_row(
                candidate_key=request["candidate_key"],
                status="refute",
                quote=quotes[qid],
                claim_id=f"refute_{index}",
                missingness_reason=missingness,
                confidence=float(compact.get("confidence") or 0.0),
                verifier_model=profile.model,
            )
        )
    if not ledger:
        fallback = next(iter(quotes.values()), None)
        ledger.append(
            _ledger_row(
                candidate_key=request["candidate_key"],
                status="unknown",
                quote=fallback,
                claim_id="decision_basis_unquoted_or_incomplete",
                missingness_reason=missingness,
                confidence=float(compact.get("confidence") or 0.0),
                verifier_model=profile.model,
            )
        )
    unknown_reason = safe_text(compact.get("decision_rationale")) if compact.get("final_stage_decision") == "unknown" else ""
    return StageReviewOutput(
        candidate_key=request["candidate_key"],
        stage="stage2",
        final_stage_decision=compact["final_stage_decision"],
        decision_rationale=safe_text(compact.get("decision_rationale"))[:700] or "Compact direct decision.",
        route_reason="",
        unknown_reason=unknown_reason,
        missingness_reason=missingness,
        confidence=float(compact.get("confidence") or 0.0),
        evidence_ledger=[EvidenceLedgerRow.model_validate(row) for row in ledger],
    ).model_dump(mode="json")


def run_direct_phase(
    *,
    run_id: str,
    profile: DirectProfile,
    cost_cap_usd: float,
    concurrency: int,
    retry_attempts: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    rd = run_dir(run_id)
    artifact_dir = ensure_dir(rd / "direct_calls" / STAGE2_PHASE / profile.profile_id)
    requests = prepare_direct_requests(run_id=run_id, profile=profile)
    input_rows = [{"custom_id": row["custom_id"], "body": row["body"], "context": {key: row[key] for key in ("paper_id", "candidate_key", "candidate_title")}} for row in requests]
    write_jsonl(artifact_dir / "input.jsonl", input_rows)
    hits = _prompt_hits(requests)
    write_json(artifact_dir / "forbidden_prompt_scan.json", {"hit_count": len(hits), "hits": hits})
    if hits:
        payload = {"status": "stopped_forbidden_prompt_terms", "hits": hits}
        write_json(artifact_dir / "leakage_stop.json", payload)
        raise RuntimeError(f"Forbidden prompt fields detected: {hits[:3]}")
    estimate = write_pre_submit_estimate(run_id=run_id, profile=profile, requests=requests, cost_cap_usd=cost_cap_usd)
    if estimate["would_exceed_cost_cap"]:
        payload = {"status": "stopped_cost_cap_before_direct_calls", "estimate": estimate}
        write_json(cost_dir(run_id) / "cost_stop.json", payload)
        return payload
    if dry_run:
        payload = {"status": "dry_run_not_submitted", "request_count": len(requests), "successes": [], "failures": []}
        write_json(artifact_dir / "parsed_results.json", payload)
        return payload

    load_dotenv_if_present()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; cannot run direct API calls.")

    final_by_id: dict[str, dict[str, Any]] = {}
    all_attempt_rows: list[dict[str, Any]] = []
    pending = list(requests)
    for attempt in range(retry_attempts + 1):
        if not pending:
            break
        attempt_rows: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            futures = {pool.submit(_call_one, request, profile=profile, attempt=attempt): request for request in pending}
            for future in as_completed(futures):
                request = futures[future]
                result = future.result()
                attempt_rows.append(result)
                all_attempt_rows.append(result)
                raw = result.get("raw_response") if isinstance(result.get("raw_response"), dict) else {}
                input_tokens, output_tokens, source = _usage_tokens(raw)
                if not input_tokens:
                    input_tokens = estimate_text_tokens(json.dumps(request["body"], ensure_ascii=False))
                    source = "estimated_no_usage"
                if not output_tokens:
                    assistant = safe_text(result.get("assistant_text"))
                    output_tokens = estimate_text_tokens(assistant) if assistant else profile.max_completion_tokens
                    source = "estimated_no_usage"
                cost = _direct_cost(profile, input_tokens=input_tokens, output_tokens=output_tokens)
                append_jsonl(
                    cost_dir(run_id) / "cost_ledger.jsonl",
                    {
                        "created_at": utc_now_iso(),
                        "phase": STAGE2_PHASE,
                        "custom_id": f"{request['custom_id']}__attempt{attempt}",
                        "base_custom_id": request["custom_id"],
                        "attempt": attempt,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": cost,
                        "cost_source": source,
                    },
                )
                if result["status"] == "ok":
                    final_by_id[request["custom_id"]] = result
        write_json(artifact_dir / f"attempt_{attempt}.json", {"attempt": attempt, "rows": attempt_rows})
        if _current_cost(run_id) > cost_cap_usd:
            break
        pending = [request for request in requests if request["custom_id"] not in final_by_id]

    output_rows = [row for row in all_attempt_rows if row["status"] == "ok"]
    failure_rows = [row for row in all_attempt_rows if row["status"] != "ok"]
    write_jsonl(artifact_dir / "output.jsonl", output_rows)
    write_jsonl(artifact_dir / "error.jsonl", failure_rows)

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    request_by_id = {request["custom_id"]: request for request in requests}
    for custom_id, request in sorted(request_by_id.items()):
        final = final_by_id.get(custom_id)
        if not final:
            related = [row for row in all_attempt_rows if row["custom_id"] == custom_id]
            failures.append(
                {
                    "custom_id": custom_id,
                    "status": "direct_call_failed_after_retries",
                    "context": {key: request[key] for key in ("paper_id", "candidate_key", "candidate_title", "phase", "stage", "criteria_path", "metadata_path")},
                    "attempts": related,
                }
            )
            continue
        stage_output = compact_to_stage_output(request=request, compact=final["parsed"], profile=profile)
        successes.append(
            {
                "custom_id": custom_id,
                "status": "ok",
                "context": final["context"],
                "attempt": final["attempt"],
                "assistant_text": final["assistant_text"],
                "compact_parsed": final["parsed"],
                "parsed": stage_output,
            }
        )

    parsed = {
        "phase": STAGE2_PHASE,
        "direct_api": True,
        "successes": successes,
        "failures": failures,
        "missing": [],
        "attempt_count": len(all_attempt_rows),
        "request_count": len(requests),
        "retry_attempts": retry_attempts,
        "status": "completed" if not failures else "completed_with_failures",
    }
    write_json(artifact_dir / "parsed_results.json", parsed)
    _write_stage2_outputs(run_id=run_id, parsed=parsed, profile=profile)
    cost_summary = audit_cost_ledger(run_path=rd, rewrite_summary=True)["deduped_summary"]
    manifest = read_json(rd / "run_manifest.json")
    manifest["status"] = f"direct_phase_{parsed['status']}"
    manifest["updated_at"] = utc_now_iso()
    manifest["direct_phase"] = {
        "artifact_dir": repo_rel(artifact_dir),
        "request_count": len(requests),
        "success_count": len(successes),
        "failure_count": len(failures),
        "attempt_count": len(all_attempt_rows),
        "pre_submit_estimate": estimate,
        "cost_summary": cost_summary,
    }
    write_json(rd / "run_manifest.json", manifest)
    return parsed


def _write_stage2_outputs(*, run_id: str, parsed: dict[str, Any], profile: DirectProfile) -> None:
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in parsed.get("successes", []):
        ctx = item["context"]
        rows_by_paper[ctx["paper_id"]].append(
            {
                "paper_id": ctx["paper_id"],
                "candidate_key": ctx["candidate_key"],
                "candidate_title": ctx["candidate_title"],
                "phase": STAGE2_PHASE,
                "stage": "stage2",
                "model": profile.model,
                "profile_id": profile.profile_id,
                "criteria_path": ctx["criteria_path"],
                "metadata_path": ctx["metadata_path"],
                "review_output": item["parsed"],
                "compact_decision": item["compact_parsed"],
            }
        )
    for paper_id, rows in rows_by_paper.items():
        rows.sort(key=lambda row: row["candidate_key"])
        write_json(paper_dir(run_id, paper_id) / "stage2_review.json", rows)
    for paper_id in base._cases_by_paper(run_dir(run_id)):
        path = paper_dir(run_id, paper_id) / "stage2_review.json"
        if not path.exists():
            write_json(path, [])


def assemble_allroute(*, run_id: str) -> list[dict[str, Any]]:
    rd = run_dir(run_id)
    cases = read_json(rd / "failure_slice_keys.json")["cases"]
    paper_data = base._prepare_common(rd)
    stage1_by_key = _stage1_by_key(rd)
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
                "direct_allroute_policy": True,
            }
        )
    rows.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    write_json(rd / "assembled_results.json", rows)
    for paper_id in sorted({row["paper_id"] for row in rows}):
        write_json(paper_dir(run_id, paper_id) / "single_reviewer_batch_results.json", [row for row in rows if row["paper_id"] == paper_id])
    return rows


def direct_prompt_scan(run_id: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((run_dir(run_id) / "direct_calls").glob("*/*/input.jsonl")):
        line_rows = []
        for row in path.read_text(encoding="utf-8").splitlines():
            if row.strip():
                line_rows.append(json.loads(row))
        hits = []
        for row in line_rows:
            terms = find_forbidden_prompt_terms(json.dumps(row.get("body", {}), ensure_ascii=False))
            if terms:
                hits.append({"custom_id": row.get("custom_id"), "terms": terms})
        rows.append({"path": repo_rel(path), "row_count": len(line_rows), "hit_count": len(hits), "hits": hits})
    return {"scans": rows, "hit_count": sum(row["hit_count"] for row in rows)}


def direct_output_path_audit(run_id: str) -> dict[str, Any]:
    rd = run_dir(run_id)
    manifest = read_json(rd / "run_manifest.json")
    before = set(manifest.get("pre_run_git_status_short") or [])
    after_lines = _git_status_short()
    before_paths = _status_paths(list(before))
    after_paths = _status_paths(after_lines)
    new_or_changed_paths = sorted(after_paths - before_paths)
    outside_new = [path for path in new_or_changed_paths if not path.startswith("research_bcpcs_2026-04-18/")]
    payload = {
        "created_at": utc_now_iso(),
        "preexisting_outside_research_changes": manifest.get("pre_run_outside_research_changes", []),
        "new_or_changed_paths_since_run_start": new_or_changed_paths,
        "outside_research_new_or_changed_since_run_start": outside_new,
        "ok_for_direct_run": not outside_new,
        "note": "Global validate_run_artifacts may still report pre-existing outside-research dirty files; this audit compares pre/post for this run.",
    }
    write_json(rd / "direct_output_path_audit.json", payload)
    return payload


def guardrail_status(*, run_id: str, scope: str, canary: bool = False) -> dict[str, Any]:
    summary = read_json(run_dir(run_id) / "evaluation_summary_v2.json")
    if canary:
        bucket = summary["primary22"]
        passed = bucket["coverage"]["runtime_failure_count"] == 0 and bucket["coverage"]["definite_decision_rate"] >= MIN_COVERAGE
        threshold_name = "canary_runtime_only"
    elif scope == "primary22":
        bucket = summary["primary22"]
        passed = (
            float(bucket["auto_decidable_f1"]["f1"]) >= LOCKED_PRIMARY_AUTO_F1
            and float(bucket["coverage"]["definite_decision_rate"]) >= MIN_COVERAGE
            and int(bucket["coverage"]["runtime_failure_count"]) == 0
        )
        threshold_name = "primary22_score_guardrail"
    else:
        bucket = summary["all127"]
        passed = (
            float(bucket["auto_decidable_f1"]["f1"]) >= LOCKED_FULL_AUTO_F1
            and float(bucket["coverage"]["definite_decision_rate"]) >= MIN_COVERAGE
            and int(bucket["coverage"]["runtime_failure_count"]) == 0
        )
        threshold_name = "full127_score_guardrail"
    payload = {
        "created_at": utc_now_iso(),
        "scope": scope,
        "canary": canary,
        "threshold_name": threshold_name,
        "passed": passed,
        "observed_auto_f1": float(bucket["auto_decidable_f1"]["f1"]),
        "observed_conservative_f1": float(bucket["conservative_f1"]["f1"]),
        "observed_coverage": float(bucket["coverage"]["definite_decision_rate"]),
        "observed_runtime_failure_count": int(bucket["coverage"]["runtime_failure_count"]),
        "thresholds": {
            "primary22_auto_f1_min": LOCKED_PRIMARY_AUTO_F1,
            "full127_all_auto_f1_min": LOCKED_FULL_AUTO_F1,
            "coverage_min": MIN_COVERAGE,
            "runtime_failure_max": 0,
        },
    }
    write_json(run_dir(run_id) / "guardrail_status.json", payload)
    return payload


def evaluate_validate_analyze(*, run_id: str, baseline_run_id: str | None = BASELINE_RUN_ID) -> dict[str, Any]:
    rd = run_dir(run_id)
    assemble_allroute(run_id=run_id)
    evaluation = evaluate_results_v2(run_dir=rd)
    validation = validate_run_artifacts(rd)
    prompt_scan = direct_prompt_scan(run_id)
    path_audit = direct_output_path_audit(run_id)
    write_json(
        rd / "direct_validation_summary.json",
        {
            "created_at": utc_now_iso(),
            "direct_forbidden_prompt_hit_count": prompt_scan["hit_count"],
            "direct_output_path_audit_ok": path_audit["ok_for_direct_run"],
            "direct_prompt_scans": prompt_scan["scans"],
            "direct_output_path_audit": path_audit,
            "global_validation_summary": validation,
        },
    )
    write_leakage_audit(run_id=run_id, run_dir=rd, validation={**validation, "direct_forbidden_prompt_hit_count": prompt_scan["hit_count"]})
    analysis = analyze_run(candidate_run_dir=rd, baseline_run_dir=run_dir(baseline_run_id) if baseline_run_id else None)
    manifest = read_json(rd / "run_manifest.json")
    manifest["evaluation_summary_v2_path"] = repo_rel(rd / "evaluation_summary_v2.json")
    manifest["validation_summary_path"] = repo_rel(rd / "validation_summary.json")
    manifest["direct_validation_summary_path"] = repo_rel(rd / "direct_validation_summary.json")
    manifest["error_analysis_path"] = repo_rel(rd / "error_analysis.json")
    manifest["updated_at"] = utc_now_iso()
    write_json(rd / "run_manifest.json", manifest)
    return {"evaluation": evaluation, "validation": validation, "analysis": analysis}


def run_one(
    *,
    run_id: str,
    scope: Literal["primary22", "full127"],
    profile: DirectProfile,
    cost_cap_usd: float,
    concurrency: int,
    retry_attempts: int,
    limit: int | None = None,
    canary: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    init_direct_run(run_id=run_id, scope=scope, profile=profile, cost_cap_usd=cost_cap_usd, limit=limit)
    write_synthetic_stage1(run_id=run_id)
    parsed = run_direct_phase(
        run_id=run_id,
        profile=profile,
        cost_cap_usd=cost_cap_usd,
        concurrency=concurrency,
        retry_attempts=retry_attempts,
        dry_run=dry_run,
    )
    if dry_run or parsed.get("status") == "stopped_cost_cap_before_direct_calls":
        return {"run_id": run_id, "status": parsed.get("status"), "parsed": parsed}
    result = evaluate_validate_analyze(run_id=run_id)
    guard = guardrail_status(run_id=run_id, scope=scope, canary=canary)
    manifest = read_json(run_dir(run_id) / "run_manifest.json")
    manifest["guardrail_status_path"] = repo_rel(run_dir(run_id) / "guardrail_status.json")
    manifest["status"] = "guardrail_passed" if guard["passed"] else "guardrail_failed"
    if canary:
        manifest["status"] = "canary_passed" if guard["passed"] else "canary_failed"
    manifest["updated_at"] = utc_now_iso()
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    return {"run_id": run_id, "status": manifest["status"], "guardrail": guard, "parsed": parsed, **result}


def write_direct_report(*, run_ids: list[str], queue_status: dict[str, Any]) -> None:
    lines = [
        "# BCPCS Direct Repair Report",
        "",
        "這是 failure-slice dev diagnostic，不是 full benchmark，也不是 unbiased improvement claim。",
        "",
        "## Locked Guardrails",
        "",
        f"- primary22 auto F1 must be >= `{LOCKED_PRIMARY_AUTO_F1:.4f}`",
        f"- full127 all auto F1 must be >= `{LOCKED_FULL_AUTO_F1:.4f}`",
        f"- coverage must be >= `{MIN_COVERAGE:.2%}`",
        "- runtime failures must be `0`",
        "- Batch API was not used in this direct repair track.",
        "",
        "## Run Results",
        "",
        "| run_id | scope | model | effort | auto F1 | conservative F1 | coverage | runtime failures | guardrail | cost |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    total_cost = 0.0
    promoted: list[str] = []
    for run_id in run_ids:
        rd = run_dir(run_id)
        if not (rd / "evaluation_summary_v2.json").exists():
            continue
        evaluation = read_json(rd / "evaluation_summary_v2.json")
        manifest = read_json(rd / "run_manifest.json")
        guard = read_json(rd / "guardrail_status.json") if (rd / "guardrail_status.json").exists() else {"passed": False}
        cost_path = rd / "cost" / "cost_summary.json"
        cost_payload = read_json(cost_path) if cost_path.exists() else {}
        cost = float(cost_payload.get("total_cost_usd") or 0.0)
        if not safe_text(cost_payload.get("cost_source")).startswith("reused_direct_run_outputs"):
            total_cost += cost
        scope = evaluation.get("scope")
        bucket = evaluation["primary22"] if scope == "primary22" else evaluation["all127"]
        if scope == "full127" and guard.get("passed"):
            promoted.append(run_id)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{run_id}`",
                    str(scope),
                    f"`{manifest.get('model')}`",
                    f"`{manifest.get('reasoning_effort')}`",
                    f"{bucket['auto_decidable_f1']['f1']:.4f}",
                    f"{bucket['conservative_f1']['f1']:.4f}",
                    f"{bucket['coverage']['definite_decision_rate']:.2%}",
                    str(bucket["coverage"]["runtime_failure_count"]),
                    "passed" if guard.get("passed") else "failed",
                    f"${cost:.6f}",
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
            f"- Direct repair actual API cost from non-reused runs: `${total_cost:.6f}`.",
            "- Hybrid row shows attributed source-run cost but made no additional API calls.",
            "- 低於 guardrail 的 run 只保留為 failed diagnostic，不覆蓋 locked baseline。",
            "- direct prompt 使用 deterministic evidence packet；gold/prior verdict/error taxonomy 沒有進入 reviewer prompt。",
            "- global output path audit may remain false if pre-existing dirty files outside research are present; direct run uses pre/post path audit for new writes.",
        ]
    )
    if promoted:
        lines.append(f"- Promoted candidate run(s): {', '.join(f'`{item}`' for item in promoted)}.")
    else:
        lines.append("- No direct repair run was promoted.")
    write_json(REPORTS_ROOT / "failure_slice_direct_repair_queue_status.json", queue_status)
    (REPORTS_ROOT / "failure_slice_direct_repair_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _stage_rows_from_assembled(rows: list[dict[str, Any]], *, stage_key: str, stage_name: str, model: str) -> dict[str, list[dict[str, Any]]]:
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        output = row.get(stage_key)
        if not isinstance(output, dict):
            continue
        paper_id = row["paper_id"]
        by_paper[paper_id].append(
            {
                "paper_id": paper_id,
                "candidate_key": row["candidate_key"],
                "candidate_title": row.get("candidate_title"),
                "phase": f"{stage_name}_review",
                "stage": stage_name,
                "model": model,
                "criteria_path": f"criteria_{stage_name}/{paper_id}.json",
                "metadata_path": f"refs/{paper_id}/metadata/title_abstracts_metadata.jsonl",
                "review_output": output,
            }
        )
    for paper_id in by_paper:
        by_paper[paper_id].sort(key=lambda item: item["candidate_key"])
    return by_paper


def build_primary_direct_secondary_baseline_hybrid(
    *,
    run_id: str,
    direct_run_id: str,
    baseline_run_id: str = BASELINE_RUN_ID,
    cost_cap_usd: float = DEFAULT_COST_CAP_USD,
) -> dict[str, Any]:
    rd = ensure_dir(run_dir(run_id))
    ensure_dir(rd / "papers")
    ensure_dir(cost_dir(run_id))
    freeze_inventory_files(run_dir=rd, scope="full127")
    direct_dir = run_dir(direct_run_id)
    baseline_dir = run_dir(baseline_run_id)
    direct_rows = read_json(direct_dir / "assembled_results.json")
    baseline_rows = read_json(baseline_dir / "assembled_results.json")
    pre_status = _git_status_short()
    direct_by_key = {(row["paper_id"], row["candidate_key"]): row for row in direct_rows}
    baseline_by_key = {(row["paper_id"], row["candidate_key"]): row for row in baseline_rows}
    cases = read_json(rd / "failure_slice_keys.json")["cases"]
    mixed_rows: list[dict[str, Any]] = []
    for case in cases:
        key = (case["paper_id"], case["candidate_key"])
        if case["slice_type"] == "non_tension_primary":
            source = dict(direct_by_key[key])
            source["hybrid_source"] = "direct_primary_non_tension"
            source["hybrid_source_run_id"] = direct_run_id
        else:
            source = dict(baseline_by_key[key])
            source["hybrid_source"] = "locked_baseline_secondary_tension"
            source["hybrid_source_run_id"] = baseline_run_id
        mixed_rows.append(source)
    mixed_rows.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    write_json(rd / "assembled_results.json", mixed_rows)

    for paper_id in sorted({row["paper_id"] for row in mixed_rows}):
        paper_rows = [row for row in mixed_rows if row["paper_id"] == paper_id]
        write_json(paper_dir(run_id, paper_id) / "single_reviewer_batch_results.json", paper_rows)
    for stage_key, stage_name in (("stage1_output", "stage1"), ("stage2_output", "stage2")):
        by_paper = _stage_rows_from_assembled(mixed_rows, stage_key=stage_key, stage_name=stage_name, model="hybrid_direct_primary_baseline_secondary")
        for paper_id, rows in by_paper.items():
            write_json(paper_dir(run_id, paper_id) / f"{stage_name}_review.json", rows)

    direct_cost_path = direct_dir / "cost" / "cost_summary.json"
    direct_cost = read_json(direct_cost_path) if direct_cost_path.exists() else {}
    cost_summary = {
        "created_at": utc_now_iso(),
        "cost_source": "reused_direct_run_outputs_plus_locked_baseline_outputs",
        "total_cost_usd": float(direct_cost.get("total_cost_usd") or 0.0),
        "source_direct_run_id": direct_run_id,
        "source_direct_run_cost_summary": direct_cost,
        "baseline_run_id": baseline_run_id,
        "note": "Hybrid assembly itself made no API calls; attributed cost is the source direct full127 run used for primary rows.",
    }
    write_json(cost_dir(run_id) / "cost_summary.json", cost_summary)
    write_json(cost_dir(run_id) / "pricing_snapshot.json", {"created_at": utc_now_iso(), "pricing_basis": "no new API calls in hybrid assembly"})

    manifest = {
        "run_id": run_id,
        "experiment_name": "bcpcs_failure_slice_direct_repair_hybrid",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "scope": "full127",
        "model": "hybrid:gpt-5.4-nano-direct-primary+gpt-5-nano-locked-baseline-secondary",
        "workflow": "primary_non_tension_direct_repair_secondary_tension_locked_baseline",
        "cost_cap_usd": cost_cap_usd,
        "status": "hybrid_assembled",
        "run_dir": repo_rel(rd),
        "direct_primary_source_run_id": direct_run_id,
        "secondary_locked_baseline_run_id": baseline_run_id,
        "is_failure_slice_dev_diagnostic": True,
        "not_unbiased_evaluation": True,
        "not_full_benchmark_evidence": True,
        "not_fully_automated_new_reviewer": True,
        "hybrid_policy": {
            "primary_non_tension_rows": "use direct local-packet compact-decision profile",
            "secondary_criteria_gold_tension_rows": "preserve locked baseline outputs; do not tune or repair as ordinary model errors",
        },
        "pre_run_git_status_short": pre_status,
        "pre_run_outside_research_changes": sorted(
            path for path in _status_paths(pre_status) if not path.startswith("research_bcpcs_2026-04-18/")
        ),
        "locked_baseline": {
            "baseline_run_id": baseline_run_id,
            "full127_all_auto_f1_min": LOCKED_FULL_AUTO_F1,
            "primary22_auto_f1_min": LOCKED_PRIMARY_AUTO_F1,
            "coverage_min": MIN_COVERAGE,
            "runtime_failure_max": 0,
        },
    }
    write_json(rd / "run_manifest.json", manifest)
    evaluation = evaluate_results_v2(run_dir=rd)
    validation = validate_run_artifacts(rd)
    path_audit = direct_output_path_audit(run_id)
    write_json(
        rd / "direct_validation_summary.json",
        {
            "created_at": utc_now_iso(),
            "direct_forbidden_prompt_hit_count": 0,
            "direct_output_path_audit_ok": path_audit["ok_for_direct_run"],
            "direct_prompt_scans": [],
            "direct_output_path_audit": path_audit,
            "global_validation_summary": validation,
            "note": "Hybrid assembly has no submitted prompts.",
        },
    )
    write_leakage_audit(run_id=run_id, run_dir=rd, validation={**validation, "direct_forbidden_prompt_hit_count": 0})
    analysis = analyze_run(candidate_run_dir=rd, baseline_run_dir=baseline_dir)
    guard = guardrail_status(run_id=run_id, scope="full127")
    manifest = read_json(rd / "run_manifest.json")
    manifest["status"] = "guardrail_passed" if guard["passed"] else "guardrail_failed"
    manifest["evaluation_summary_v2_path"] = repo_rel(rd / "evaluation_summary_v2.json")
    manifest["validation_summary_path"] = repo_rel(rd / "validation_summary.json")
    manifest["direct_validation_summary_path"] = repo_rel(rd / "direct_validation_summary.json")
    manifest["error_analysis_path"] = repo_rel(rd / "error_analysis.json")
    manifest["guardrail_status_path"] = repo_rel(rd / "guardrail_status.json")
    manifest["updated_at"] = utc_now_iso()
    write_json(rd / "run_manifest.json", manifest)
    return {"run_id": run_id, "status": manifest["status"], "guardrail": guard, "evaluation": evaluation, "validation": validation, "analysis": analysis}


def run_queue(*, cost_cap_usd: float, concurrency: int, retry_attempts: int) -> dict[str, Any]:
    queue_status: dict[str, Any] = {"created_at": utc_now_iso(), "statuses": [], "promoted_run_id": None}
    run_ids: list[str] = []
    profiles = [
        PROFILES["direct_gpt54nano_xhigh_localpacket_compactdecision_v1"],
        PROFILES["direct_gpt54nano_high_localpacket_compactdecision_v1"],
        PROFILES["direct_gpt5nano_high_localpacket_compactdecision_v1"],
    ]
    for profile in profiles:
        canary_id = f"bcpcs_direct_canary5_{profile.profile_id}_{TODAY}_v1"
        canary = run_one(
            run_id=canary_id,
            scope="primary22",
            profile=profile,
            cost_cap_usd=cost_cap_usd,
            concurrency=concurrency,
            retry_attempts=retry_attempts,
            limit=CANARY_SIZE,
            canary=True,
        )
        run_ids.append(canary_id)
        queue_status["statuses"].append({"run_id": canary_id, "profile_id": profile.profile_id, "kind": "canary5", "status": canary["status"], "guardrail": canary.get("guardrail")})
        if canary["status"] != "canary_passed":
            continue

        primary_id = f"bcpcs_direct_primary22_{profile.profile_id}_{TODAY}_v1"
        primary = run_one(
            run_id=primary_id,
            scope="primary22",
            profile=profile,
            cost_cap_usd=cost_cap_usd,
            concurrency=concurrency,
            retry_attempts=retry_attempts,
        )
        run_ids.append(primary_id)
        queue_status["statuses"].append({"run_id": primary_id, "profile_id": profile.profile_id, "kind": "primary22", "status": primary["status"], "guardrail": primary.get("guardrail")})
        if primary["status"] != "guardrail_passed":
            continue

        full_id = f"bcpcs_direct_full127_{profile.profile_id}_{TODAY}_v1"
        full = run_one(
            run_id=full_id,
            scope="full127",
            profile=profile,
            cost_cap_usd=cost_cap_usd,
            concurrency=concurrency,
            retry_attempts=retry_attempts,
        )
        run_ids.append(full_id)
        queue_status["statuses"].append({"run_id": full_id, "profile_id": profile.profile_id, "kind": "full127", "status": full["status"], "guardrail": full.get("guardrail")})
        if full["status"] == "guardrail_passed":
            queue_status["promoted_run_id"] = full_id
            break
    queue_status["completed_at"] = utc_now_iso()
    queue_status["run_ids"] = run_ids
    if queue_status["promoted_run_id"] is None:
        queue_status["stop_reason"] = "profile_queue_exhausted_without_promoted_run"
    else:
        queue_status["stop_reason"] = "promoted_run_found"
    write_direct_report(run_ids=run_ids, queue_status=queue_status)
    return queue_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Direct synchronous BCPCS failure-slice repair runner.")
    sub = parser.add_subparsers(dest="command", required=True)
    run_one_parser = sub.add_parser("run-one")
    run_one_parser.add_argument("--run-id", required=True)
    run_one_parser.add_argument("--scope", choices=["primary22", "full127"], required=True)
    run_one_parser.add_argument("--profile-id", choices=sorted(PROFILES), required=True)
    run_one_parser.add_argument("--cost-cap-usd", type=float, default=DEFAULT_COST_CAP_USD)
    run_one_parser.add_argument("--concurrency", type=int, default=3)
    run_one_parser.add_argument("--retry-attempts", type=int, default=1)
    run_one_parser.add_argument("--limit", type=int)
    run_one_parser.add_argument("--canary", action="store_true")
    run_one_parser.add_argument("--dry-run", action="store_true")

    queue_parser = sub.add_parser("run-queue")
    queue_parser.add_argument("--cost-cap-usd", type=float, default=DEFAULT_COST_CAP_USD)
    queue_parser.add_argument("--concurrency", type=int, default=3)
    queue_parser.add_argument("--retry-attempts", type=int, default=1)

    eval_parser = sub.add_parser("evaluate")
    eval_parser.add_argument("--run-id", required=True)

    hybrid_parser = sub.add_parser("hybrid")
    hybrid_parser.add_argument("--run-id", required=True)
    hybrid_parser.add_argument("--direct-run-id", required=True)
    hybrid_parser.add_argument("--baseline-run-id", default=BASELINE_RUN_ID)
    hybrid_parser.add_argument("--cost-cap-usd", type=float, default=DEFAULT_COST_CAP_USD)

    args = parser.parse_args()
    if args.command == "run-one":
        payload = run_one(
            run_id=args.run_id,
            scope=args.scope,
            profile=PROFILES[args.profile_id],
            cost_cap_usd=args.cost_cap_usd,
            concurrency=args.concurrency,
            retry_attempts=args.retry_attempts,
            limit=args.limit,
            canary=args.canary,
            dry_run=args.dry_run,
        )
    elif args.command == "run-queue":
        payload = run_queue(cost_cap_usd=args.cost_cap_usd, concurrency=args.concurrency, retry_attempts=args.retry_attempts)
    elif args.command == "hybrid":
        payload = build_primary_direct_secondary_baseline_hybrid(
            run_id=args.run_id,
            direct_run_id=args.direct_run_id,
            baseline_run_id=args.baseline_run_id,
            cost_cap_usd=args.cost_cap_usd,
        )
    else:
        payload = evaluate_validate_analyze(run_id=args.run_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
