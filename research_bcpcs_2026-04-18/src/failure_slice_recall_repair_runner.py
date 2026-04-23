#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bcpcs_utils import compile_stub_graph
import failure_slice_direct_repair_runner as direct
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


TODAY = time.strftime("%Y-%m-%d")
BASELINE_RUN_ID = "bcpcs_failure_slice_gpt5nano_2stage_async_2026-04-18_full127_v1"
PROMOTION_AUTO_F1_STRICT_MIN = 0.8
MIN_COVERAGE = 0.98
REQUIRED_MODELS = ("gpt-5-nano", "gpt-5.4-nano")
PHASE = "stage2_recall_repair_decision"
CANARY_SIZE = 5


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CriterionAssessment(StrictModel):
    claim_id: str = Field(min_length=1)
    claim_type: Literal["inclusion", "exclusion"]
    judgment: Literal["supported", "ambiguous", "not_supported"]
    support_quote_ids: list[str] = Field(default_factory=list)
    refute_quote_ids: list[str] = Field(default_factory=list)
    short_rationale: str = Field(min_length=1, max_length=200)


class RecallRepairDecisionOutput(StrictModel):
    candidate_key: str = Field(min_length=1)
    stage: Literal["stage2_global_checklist"]
    proposed_decision: Literal["include", "exclude", "maybe", "unknown"]
    confidence: float = Field(ge=0, le=1)
    missingness_reason: MissingnessReason
    criterion_assessments: list[CriterionAssessment] = Field(min_length=1)
    decision_rationale: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def _criterion_ids_unique(self) -> "RecallRepairDecisionOutput":
        claim_ids = [row.claim_id for row in self.criterion_assessments]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("criterion_assessments claim_id values must be unique")
        return self


@dataclass(frozen=True)
class RecallProfile:
    profile_id: str
    model: str
    reasoning_effort: str
    max_completion_tokens: int
    evidence_packet_chars: int
    max_quotes: int
    promotable: bool
    rates: CostRates


PROFILES: dict[str, RecallProfile] = {
    "recall_boundary_maybe_v1_gpt5nano": RecallProfile(
        profile_id="recall_boundary_maybe_v1",
        model="gpt-5-nano",
        reasoning_effort="low",
        max_completion_tokens=4096,
        evidence_packet_chars=9000,
        max_quotes=12,
        promotable=True,
        rates=CostRates(input_per_million=0.05, cached_input_per_million=0.005, output_per_million=0.40, batch_discount=0.0),
    ),
    "recall_boundary_maybe_v1_gpt54nano": RecallProfile(
        profile_id="recall_boundary_maybe_v1",
        model="gpt-5.4-nano",
        reasoning_effort="low",
        max_completion_tokens=4096,
        evidence_packet_chars=9000,
        max_quotes=12,
        promotable=True,
        rates=CostRates(input_per_million=0.20, cached_input_per_million=0.02, output_per_million=1.25, batch_discount=0.0),
    ),
    "recall_boundary_maybe_v1_gpt54mini": RecallProfile(
        profile_id="recall_boundary_maybe_v1",
        model="gpt-5.4-mini",
        reasoning_effort="low",
        max_completion_tokens=4096,
        evidence_packet_chars=9000,
        max_quotes=12,
        promotable=False,
        rates=CostRates(input_per_million=0.75, cached_input_per_million=0.075, output_per_million=4.50, batch_discount=0.0),
    ),
}


def _json_block(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _direct_cost(profile: RecallProfile, *, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * profile.rates.input_per_million + (
        output_tokens / 1_000_000
    ) * profile.rates.output_per_million


def _pricing_snapshot(profile: RecallProfile) -> dict[str, Any]:
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
        "sources": ["https://openai.com/api/pricing/", "https://platform.openai.com/docs/pricing/"],
        "notes": ["V3 recall repair does not use Batch API."],
    }


def init_recall_run(*, run_id: str, scope: Literal["primary22", "full127"], profile: RecallProfile, cost_cap_usd: float, limit: int | None = None) -> dict[str, Any]:
    rd = ensure_dir(run_dir(run_id))
    ensure_dir(rd / "direct_calls" / PHASE / profile.profile_id)
    ensure_dir(rd / "papers")
    ensure_dir(cost_dir(run_id))
    freeze_inventory_files(run_dir=rd, scope=scope)
    if limit is not None:
        direct._limit_inventory(rd, limit=limit)
    source_counts = read_json(rd / "failure_slice_keys.json")["summary"]
    pre_status = direct._git_status_short()
    manifest = {
        "run_id": run_id,
        "experiment_name": "bcpcs_failure_slice_recall_repair_v3",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "scope": scope,
        "sample_limit": limit,
        "model": profile.model,
        "profile_id": profile.profile_id,
        "endpoint": "/v1/chat/completions",
        "reviewer": "single_reviewer",
        "workflow": "direct_sync_allroute_recall_boundary_maybe",
        "reasoning_effort": profile.reasoning_effort,
        "max_completion_tokens": profile.max_completion_tokens,
        "cost_cap_usd": cost_cap_usd,
        "status": "initialized_recall_repair",
        "run_dir": repo_rel(rd),
        "is_failure_slice_dev_diagnostic": True,
        "not_unbiased_evaluation": True,
        "not_full_benchmark_evidence": True,
        "write_scope": "research_bcpcs_2026-04-18 only",
        "source_counts": source_counts,
        "promotion_requirements_v2": {
            "pure_model_full127_auto_f1_must_be_greater_than": PROMOTION_AUTO_F1_STRICT_MIN,
            "pure_models_required": list(REQUIRED_MODELS),
            "coverage_min": MIN_COVERAGE,
            "runtime_failure_max": 0,
            "hybrid_or_reused_baseline_runs_promotable": False,
        },
        "recall_repair_policy": {
            "stage1_policy": "synthetic diagnostic all-route handoff",
            "decision_threshold": "exclude only when model asserts a clear hard exclusion; otherwise include/maybe/unknown are compiled recall-first",
            "maybe_policy": "boundary, partial match, adjacent evidence, and evidence-incomplete cases compile to maybe rather than semantic exclude",
            "maybe_counts_reported": True,
        },
        "pre_run_git_status_short": pre_status,
        "pre_run_outside_research_changes": sorted(path for path in direct._status_paths(pre_status) if not path.startswith("research_bcpcs_2026-04-18/")),
    }
    write_json(rd / "run_manifest.json", manifest)
    write_json(cost_dir(run_id) / "pricing_snapshot.json", _pricing_snapshot(profile))
    return manifest


def _claim_terms(text: str) -> list[str]:
    raw = [token.replace("_", "-") for token in re.findall(r"[a-z][a-z0-9_-]{3,}", safe_text(text).lower())]
    return [token for token in raw if token not in direct.STOPWORDS]


def _claim_packets(*, paper_id: str, criteria: dict[str, Any], evidence_packet: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    graph = compile_stub_graph(paper_id, "stage2")
    quotes = evidence_packet.get("quotes", [])
    packets: list[dict[str, Any]] = []
    for claim in graph.get("claims", []):
        claim_terms = _claim_terms(safe_text(claim.get("claim_text")))
        ranked: list[tuple[int, str]] = []
        for quote in quotes:
            qid = safe_text(quote.get("quote_id"))
            qtext = safe_text(quote.get("text")).lower()
            if not qid or not qtext:
                continue
            score = 0
            for term in claim_terms:
                if " " in term:
                    score += 4 if term in qtext else 0
                else:
                    score += min(qtext.count(term), 2)
            if score:
                ranked.append((score, qid))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        packets.append(
            {
                "claim_id": claim["claim_id"],
                "claim_type": claim["claim_type"],
                "claim_text": claim["claim_text"],
                "candidate_quote_ids": [qid for _score, qid in ranked[:3]],
            }
        )
    return graph, packets


def build_recall_prompt(*, paper_id: str, candidate_key: str, criteria: dict[str, Any], metadata: dict[str, Any], stage1_output: dict[str, Any] | None, evidence_packet: dict[str, Any], criteria_path: str, metadata_path: str) -> str:
    _graph, claim_packets = _claim_packets(paper_id=paper_id, criteria=criteria, evidence_packet=evidence_packet)
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
        "stage1_bcpcs_handoff_compact": direct._compact_stage1(stage1_output),
    }
    rules = {
        "task": "Assess every stage-2 criterion separately, then provide a compact proposed verdict. A deterministic compiler will recompute the final decision from your checklist.",
        "decision_values": ["include", "exclude", "maybe", "unknown"],
        "criterion_judgment_values": ["supported", "ambiguous", "not_supported"],
        "criterion_semantics": [
            "For inclusion claims: supported means the supplied quotes positively support the requirement; not_supported means the supplied quotes positively contradict it; ambiguous means the supplied evidence is insufficient or mixed.",
            "For exclusion claims: supported means the supplied quotes positively support the exclusion; not_supported means the supplied quotes positively indicate the exclusion does not apply; ambiguous means the supplied evidence is insufficient or mixed.",
            "Do not mark a claim as supported or not_supported without quote-backed evidence. If the quote support is weak or absent, use ambiguous.",
            "Do not treat adjacency, partial topical overlap, lack of explicit wording, or boundary cases as quote-backed contradiction. Those remain ambiguous unless the quote explicitly says the claim is absent or the exclusion applies.",
            "If most criteria are positive but one criterion is borderline or only indirectly suggested, keep that criterion ambiguous instead of forcing a negative judgment.",
        ],
        "decision_policy": [
            "Do not use maybe as a default safety bucket.",
            "Use include only when the required criteria appear satisfied and no exclusion criterion appears to apply.",
            "Use exclude when supplied evidence clearly supports an exclusion criterion or clearly contradicts a required criterion.",
            "Use maybe only when there is meaningful positive support for in-scope eligibility but at least one critical criterion remains unresolved.",
            "Use unknown when the supplied evidence does not support either include or exclude strongly enough.",
            "If your checklist is mostly positive but one criterion remains borderline, proposed_decision should usually be maybe rather than exclude.",
        ],
        "quote_policy": "Return quote_id values only; do not copy quote text into output.",
        "anti_leakage": "Use no answer-key fields, previous-run outputs, error taxonomies, forensic notes, or external knowledge.",
        "output_size": "Return compact JSON only. Keep decision_rationale under 70 words.",
    }
    return "\n\n".join(
        [
            "You are a single screening reviewer. This is a BCPCS failure-slice diagnostic with recall-calibrated boundary handling.",
            "Use only the criteria, visible candidate record, Stage 1 handoff, and deterministic evidence packet below.",
            "Return only valid JSON matching the RecallRepairDecisionOutput schema. No markdown fences.",
            "Rules:",
            _json_block(rules),
            "Stage 2 criteria JSON:",
            _json_block(criteria),
            "Criterion checklist to assess:",
            _json_block(claim_packets),
            "Candidate visible record:",
            _json_block(visible_record),
            "Deterministic evidence packet:",
            _json_block(evidence_packet),
        ]
    )


def _build_body(*, profile: RecallProfile, prompt: str) -> dict[str, Any]:
    return {
        "model": profile.model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(RecallRepairDecisionOutput, schema_name="BCPCSRecallRepairDecisionOutput"),
        "reasoning_effort": profile.reasoning_effort,
        "max_completion_tokens": profile.max_completion_tokens,
    }


def prepare_recall_requests(*, run_id: str, profile: RecallProfile) -> list[dict[str, Any]]:
    rd = run_dir(run_id)
    paper_data = base._prepare_common(rd)
    stage1_by_key = direct._stage1_by_key(rd)
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
                head_chars=90_000,
                tail_chars=0,
            )
            source_path = safe_text(fulltext_meta.get("fulltext_source_path") or resolution.get("resolved_path"))
            evidence_packet = direct.build_local_evidence_packet(
                paper_id=paper_id,
                criteria=criteria,
                metadata=metadata_payload(record),
                fulltext_text=fulltext_text,
                source_path=source_path,
                metadata_path=repo_rel(metadata_path),
                max_chars=profile.evidence_packet_chars,
                max_quotes=profile.max_quotes,
            )
            criteria_graph, claim_packets = _claim_packets(paper_id=paper_id, criteria=criteria, evidence_packet=evidence_packet)
            stage1 = stage1_by_key.get((paper_id, key))
            prompt = build_recall_prompt(
                paper_id=paper_id,
                candidate_key=key,
                criteria=criteria,
                metadata=metadata_payload(record),
                stage1_output=stage1["review_output"] if stage1 else None,
                evidence_packet=evidence_packet,
                criteria_path=repo_rel(criteria_path),
                metadata_path=repo_rel(metadata_path),
            )
            custom_id = f"{PHASE}__{paper_id}__{key}"
            requests.append(
                {
                    "custom_id": custom_id,
                    "paper_id": paper_id,
                    "candidate_key": key,
                    "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                    "phase": PHASE,
                    "stage": "stage2",
                    "criteria_path": repo_rel(criteria_path),
                    "metadata_path": repo_rel(metadata_path),
                    "fulltext_resolution": resolution,
                    "evidence_packet": evidence_packet,
                    "criteria_graph": criteria_graph,
                    "claim_packets": claim_packets,
                    "body": _build_body(profile=profile, prompt=prompt),
                }
            )
        write_json(paper_dir(run_id, paper_id) / "selected_for_stage2_recall_repair.keys.json", selected)
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


def write_pre_submit_estimate(*, run_id: str, profile: RecallProfile, requests: list[dict[str, Any]], cost_cap_usd: float) -> dict[str, Any]:
    input_tokens = sum(estimate_text_tokens(json.dumps(row["body"], ensure_ascii=False)) for row in requests)
    output_tokens = len(requests) * profile.max_completion_tokens
    estimated_cost = _direct_cost(profile, input_tokens=input_tokens, output_tokens=output_tokens)
    prior = _current_cost(run_id)
    payload = {
        "phase": PHASE,
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
    write_json(cost_dir(run_id) / f"pre_submit_estimate.{PHASE}.json", payload)
    return payload


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


def _usage_tokens(response_payload: dict[str, Any]) -> tuple[int, int, str]:
    usage = response_payload.get("usage")
    if isinstance(usage, dict):
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            return input_tokens, output_tokens, "direct_usage"
    return 0, 0, "missing_usage"


def _call_one(request: dict[str, Any], *, profile: RecallProfile, attempt: int) -> dict[str, Any]:
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
        raw_payload = direct._repair_candidate_key_if_safe(raw_payload, request["candidate_key"])
        parsed = RecallRepairDecisionOutput.model_validate(raw_payload)
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


def _valid_quote_ids(values: Any, quotes: dict[str, dict[str, Any]]) -> list[str]:
    if not isinstance(values, list):
        return []
    return [safe_text(value) for value in values if safe_text(value) in quotes]


def _normalized_assessment(row: dict[str, Any], *, quotes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    support_ids = _valid_quote_ids(row.get("support_quote_ids"), quotes)
    refute_ids = _valid_quote_ids(row.get("refute_quote_ids"), quotes)
    judgment = safe_text(row.get("judgment"))
    if judgment == "supported" and support_ids and not refute_ids:
        normalized = "supported"
    elif judgment == "not_supported" and refute_ids and not support_ids:
        normalized = "not_supported"
    else:
        normalized = "ambiguous"
    return {
        "claim_id": safe_text(row.get("claim_id")),
        "claim_type": safe_text(row.get("claim_type")),
        "judgment": normalized,
        "support_quote_ids": support_ids,
        "refute_quote_ids": refute_ids,
        "short_rationale": safe_text(row.get("short_rationale")) or "no rationale supplied",
    }


def _compiled_assessments(compact: dict[str, Any], *, criteria_graph: dict[str, Any], quotes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    source_rows = compact.get("criterion_assessments") if isinstance(compact.get("criterion_assessments"), list) else []
    source_by_id = {safe_text(row.get("claim_id")): row for row in source_rows if isinstance(row, dict) and safe_text(row.get("claim_id"))}
    compiled: list[dict[str, Any]] = []
    for claim in criteria_graph.get("claims", []):
        row = source_by_id.get(safe_text(claim.get("claim_id")))
        if row:
            compiled.append(_normalized_assessment(row, quotes=quotes))
        else:
            compiled.append(
                {
                    "claim_id": safe_text(claim.get("claim_id")),
                    "claim_type": safe_text(claim.get("claim_type")),
                    "judgment": "ambiguous",
                    "support_quote_ids": [],
                    "refute_quote_ids": [],
                    "short_rationale": "criterion omitted by model; compiled as ambiguous",
                }
            )
    return compiled


def _compile_final_decision(compact: dict[str, Any], *, criteria_graph: dict[str, Any], quotes: dict[str, dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    compiled = _compiled_assessments(compact, criteria_graph=criteria_graph, quotes=quotes)
    required = [row for row in compiled if row["claim_type"] == "inclusion"]
    exclusions = [row for row in compiled if row["claim_type"] == "exclusion"]
    required_supported = sum(1 for row in required if row["judgment"] == "supported")
    required_not_supported = sum(1 for row in required if row["judgment"] == "not_supported")
    exclusion_supported = sum(1 for row in exclusions if row["judgment"] == "supported")
    exclusion_not_supported = sum(1 for row in exclusions if row["judgment"] == "not_supported")
    proposed = safe_text(compact.get("proposed_decision"))
    if required and required_supported == len(required) and exclusion_supported == 0:
        return "include", compiled
    if required_supported == 0 and (required_not_supported > 0 or exclusion_supported > 0):
        if proposed == "unknown" and exclusion_supported == 0 and exclusion_not_supported > 0:
            return "maybe", compiled
        return "exclude", compiled
    if required_supported > 0:
        return "maybe", compiled
    if proposed == "unknown" and exclusion_supported == 0 and exclusion_not_supported > 0:
        return "maybe", compiled
    return "unknown", compiled


def _span_from_quote(quote: dict[str, Any]) -> EvidenceSpan:
    return EvidenceSpan(
        quote=safe_text(quote.get("text")) or "quote unavailable",
        location=safe_text(quote.get("location")) or "unknown",
        source_path=safe_text(quote.get("source_path")) or "unknown",
        source_field=quote.get("source_field") if quote.get("source_field") in {"title", "abstract", "metadata", "full_text", "criteria", "other"} else "other",
    )


def _ledger_row(*, candidate_key: str, status: Literal["support", "refute", "unknown"], quote: dict[str, Any] | None, claim_id: str, missingness_reason: MissingnessReason, confidence: float, verifier_model: str) -> dict[str, Any]:
    if quote is None:
        return EvidenceLedgerRow(
            candidate_key=candidate_key,
            stage="stage2",
            claim_id=claim_id,
            evidence_status="unknown",
            support_spans=[],
            refute_spans=[],
            missingness_reason=missingness_reason,
            confidence=confidence,
            verifier_model=verifier_model,
            quote="",
            location="recall_repair:no_valid_quote_id",
            source_path="research_bcpcs_2026-04-18/generated_recall_repair_decision",
            span_validated=False,
        ).model_dump(mode="json")
    span = _span_from_quote(quote)
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


def recall_output_to_stage_output(*, request: dict[str, Any], compact: dict[str, Any], profile: RecallProfile) -> dict[str, Any]:
    quotes = _quote_by_id(request["evidence_packet"])
    final_decision, compiled = _compile_final_decision(compact, criteria_graph=request["criteria_graph"], quotes=quotes)
    missingness: MissingnessReason = compact.get("missingness_reason") or ("evidence_incomplete" if final_decision == "unknown" else "none")
    if final_decision != "unknown" and missingness == "none":
        missingness = "none"
    confidence = float(compact.get("confidence") or 0.0)
    ledger: list[dict[str, Any]] = []
    for row in compiled:
        support_ids = row["support_quote_ids"]
        refute_ids = row["refute_quote_ids"]
        if row["judgment"] == "supported" and support_ids:
            ledger.append(_ledger_row(candidate_key=request["candidate_key"], status="support", quote=quotes[support_ids[0]], claim_id=row["claim_id"], missingness_reason=missingness, confidence=confidence, verifier_model=profile.model))
        elif row["judgment"] == "not_supported" and refute_ids:
            ledger.append(_ledger_row(candidate_key=request["candidate_key"], status="refute", quote=quotes[refute_ids[0]], claim_id=row["claim_id"], missingness_reason=missingness, confidence=confidence, verifier_model=profile.model))
        else:
            fallback = next((quotes[qid] for qid in support_ids + refute_ids if qid in quotes), None)
            ledger.append(_ledger_row(candidate_key=request["candidate_key"], status="unknown", quote=fallback, claim_id=row["claim_id"], missingness_reason=missingness, confidence=confidence, verifier_model=profile.model))
    if not ledger:
        fallback = next(iter(quotes.values()), None)
        ledger.append(_ledger_row(candidate_key=request["candidate_key"], status="unknown", quote=fallback, claim_id="decision_basis_boundary_or_incomplete", missingness_reason=missingness, confidence=confidence, verifier_model=profile.model))
    rationale = safe_text(compact.get("decision_rationale"))
    compiler_note = f"Global checklist compiler final={final_decision}; proposed={compact.get('proposed_decision')}; supported_claims={sum(1 for row in compiled if row['judgment'] == 'supported')}; contradicted_required={sum(1 for row in compiled if row['claim_type'] == 'inclusion' and row['judgment'] == 'not_supported')}."
    return StageReviewOutput(
        candidate_key=request["candidate_key"],
        stage="stage2",
        final_stage_decision=final_decision,
        decision_rationale=(compiler_note + " " + rationale)[:700],
        route_reason="",
        unknown_reason=rationale if final_decision == "unknown" else "",
        missingness_reason=missingness,
        confidence=confidence,
        evidence_ledger=[EvidenceLedgerRow.model_validate(row) for row in ledger],
    ).model_dump(mode="json")


def run_direct_phase(*, run_id: str, profile: RecallProfile, cost_cap_usd: float, concurrency: int, retry_attempts: int, dry_run: bool = False) -> dict[str, Any]:
    rd = run_dir(run_id)
    artifact_dir = ensure_dir(rd / "direct_calls" / PHASE / profile.profile_id)
    requests = prepare_recall_requests(run_id=run_id, profile=profile)
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
                append_jsonl(
                    cost_dir(run_id) / "cost_ledger.jsonl",
                    {
                        "created_at": utc_now_iso(),
                        "phase": PHASE,
                        "custom_id": f"{request['custom_id']}__attempt{attempt}",
                        "base_custom_id": request["custom_id"],
                        "attempt": attempt,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": _direct_cost(profile, input_tokens=input_tokens, output_tokens=output_tokens),
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
            failures.append({"custom_id": custom_id, "status": "direct_call_failed_after_retries", "context": {key: request[key] for key in ("paper_id", "candidate_key", "candidate_title", "phase", "stage", "criteria_path", "metadata_path")}, "attempts": related})
            continue
        stage_output = recall_output_to_stage_output(request=request, compact=final["parsed"], profile=profile)
        successes.append({"custom_id": custom_id, "status": "ok", "context": final["context"], "attempt": final["attempt"], "assistant_text": final["assistant_text"], "recall_parsed": final["parsed"], "parsed": stage_output})

    parsed = {
        "phase": PHASE,
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
    manifest["status"] = f"recall_phase_{parsed['status']}"
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


def rebuild_direct_phase_from_source(*, run_id: str, source_run_id: str, profile: RecallProfile) -> dict[str, Any]:
    rd = run_dir(run_id)
    artifact_dir = ensure_dir(rd / "direct_calls" / PHASE / profile.profile_id)
    source_artifact_dir = run_dir(source_run_id) / "direct_calls" / PHASE / profile.profile_id
    source_parsed_path = source_artifact_dir / "parsed_results.json"
    if not source_parsed_path.exists():
        raise FileNotFoundError(f"source parsed results not found: {source_parsed_path}")

    requests = prepare_recall_requests(run_id=run_id, profile=profile)
    input_rows = [{"custom_id": row["custom_id"], "body": row["body"], "context": {key: row[key] for key in ("paper_id", "candidate_key", "candidate_title")}} for row in requests]
    write_jsonl(artifact_dir / "input.jsonl", input_rows)
    hits = _prompt_hits(requests)
    write_json(artifact_dir / "forbidden_prompt_scan.json", {"hit_count": len(hits), "hits": hits})
    if hits:
        payload = {"status": "stopped_forbidden_prompt_terms", "hits": hits}
        write_json(artifact_dir / "leakage_stop.json", payload)
        raise RuntimeError(f"Forbidden prompt fields detected during rebuild: {hits[:3]}")

    estimate_path = source_artifact_dir.parent.parent.parent / "cost" / f"pre_submit_estimate.{PHASE}.json"
    if estimate_path.exists():
        shutil.copy2(estimate_path, cost_dir(run_id) / estimate_path.name)

    source_parsed = read_json(source_parsed_path)
    source_success_by_id = {row["custom_id"]: row for row in source_parsed.get("successes", [])}
    request_by_id = {request["custom_id"]: request for request in requests}

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for custom_id in sorted(request_by_id):
        request = request_by_id[custom_id]
        source_row = source_success_by_id.get(custom_id)
        if not source_row:
            failures.append(
                {
                    "custom_id": custom_id,
                    "status": "missing_source_success",
                    "context": {key: request[key] for key in ("paper_id", "candidate_key", "candidate_title", "phase", "stage", "criteria_path", "metadata_path")},
                }
            )
            continue
        stage_output = recall_output_to_stage_output(request=request, compact=source_row["recall_parsed"], profile=profile)
        successes.append(
            {
                "custom_id": custom_id,
                "status": "ok",
                "context": source_row["context"],
                "attempt": source_row.get("attempt", 0),
                "assistant_text": source_row.get("assistant_text", ""),
                "recall_parsed": source_row["recall_parsed"],
                "parsed": stage_output,
            }
        )

    parsed = {
        "phase": PHASE,
        "direct_api": False,
        "reused_direct_outputs_from_run_id": source_run_id,
        "successes": successes,
        "failures": failures,
        "missing": [],
        "attempt_count": len(successes),
        "request_count": len(requests),
        "retry_attempts": 0,
        "status": "recompiled_from_source" if not failures else "recompiled_from_source_with_failures",
    }
    write_json(artifact_dir / "parsed_results.json", parsed)
    write_jsonl(artifact_dir / "output.jsonl", [row for row in source_parsed.get("successes", [])])
    write_jsonl(artifact_dir / "error.jsonl", [row for row in source_parsed.get("failures", [])])
    _write_stage2_outputs(run_id=run_id, parsed=parsed, profile=profile)

    cost_summary = {
        "created_at": utc_now_iso(),
        "cost_source": "reused_direct_outputs",
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost_usd": 0.0,
        "incremental_total_cost_usd": 0.0,
        "reused_direct_outputs_from_run_id": source_run_id,
        "source_cost_summary_path": repo_rel(run_dir(source_run_id) / "cost" / "cost_summary.json"),
        "phases": {},
    }
    write_json(cost_dir(run_id) / "cost_summary.json", cost_summary)
    write_json(
        cost_dir(run_id) / "cost_audit.json",
        {
            "created_at": utc_now_iso(),
            "run_dir": str(rd),
            "ledger_exists": False,
            "row_count": 0,
            "deduped_row_count": 0,
            "duplicate_row_count": 0,
            "duplicates": [],
            "deduped_summary": cost_summary,
        },
    )

    manifest = read_json(rd / "run_manifest.json")
    manifest["status"] = f"recall_phase_{parsed['status']}"
    manifest["updated_at"] = utc_now_iso()
    manifest["reused_direct_outputs_from_run_id"] = source_run_id
    manifest["direct_phase"] = {
        "artifact_dir": repo_rel(artifact_dir),
        "request_count": len(requests),
        "success_count": len(successes),
        "failure_count": len(failures),
        "attempt_count": len(successes),
        "pre_submit_estimate": read_json(cost_dir(run_id) / estimate_path.name) if estimate_path.exists() else None,
        "cost_summary": cost_summary,
        "reused_direct_outputs_from_run_id": source_run_id,
    }
    write_json(rd / "run_manifest.json", manifest)
    return parsed


def _write_stage2_outputs(*, run_id: str, parsed: dict[str, Any], profile: RecallProfile) -> None:
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in parsed.get("successes", []):
        ctx = item["context"]
        rows_by_paper[ctx["paper_id"]].append(
            {
                "paper_id": ctx["paper_id"],
                "candidate_key": ctx["candidate_key"],
                "candidate_title": ctx["candidate_title"],
                "phase": PHASE,
                "stage": "stage2",
                "model": profile.model,
                "profile_id": profile.profile_id,
                "criteria_path": ctx["criteria_path"],
                "metadata_path": ctx["metadata_path"],
                "review_output": item["parsed"],
                "recall_repair_decision": item["recall_parsed"],
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
    rows = direct.assemble_allroute(run_id=run_id)
    for row in rows:
        row["recall_repair_policy"] = True
    write_json(run_dir(run_id) / "assembled_results.json", rows)
    return rows


def direct_prompt_scan(run_id: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted((run_dir(run_id) / "direct_calls").glob("*/*/input.jsonl")):
        line_rows = []
        hits: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            line_rows.append(row)
            terms = find_forbidden_prompt_terms(json.dumps(row.get("body", {}), ensure_ascii=False))
            if terms:
                hits.append({"custom_id": row.get("custom_id"), "terms": terms})
        rows.append({"path": repo_rel(path), "row_count": len(line_rows), "hit_count": len(hits), "hits": hits})
    return {"scans": rows, "hit_count": sum(row["hit_count"] for row in rows)}


def evaluate_validate_analyze(*, run_id: str, baseline_run_id: str | None = BASELINE_RUN_ID) -> dict[str, Any]:
    rd = run_dir(run_id)
    assemble_allroute(run_id=run_id)
    evaluation = evaluate_results_v2(run_dir=rd)
    validation = validate_run_artifacts(rd)
    prompt_scan = direct_prompt_scan(run_id)
    path_audit = direct.direct_output_path_audit(run_id)
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


def guardrail_status(*, run_id: str, scope: str, canary: bool = False) -> dict[str, Any]:
    summary = read_json(run_dir(run_id) / "evaluation_summary_v2.json")
    bucket = summary["primary22"] if scope == "primary22" else summary["all127"]
    if canary:
        passed = bucket["coverage"]["runtime_failure_count"] == 0 and bucket["coverage"]["definite_decision_rate"] >= MIN_COVERAGE
        threshold_name = "canary_runtime_only"
    elif scope == "primary22":
        passed = (
            float(bucket["auto_decidable_f1"]["f1"]) > PROMOTION_AUTO_F1_STRICT_MIN
            and float(bucket["coverage"]["definite_decision_rate"]) >= MIN_COVERAGE
            and int(bucket["coverage"]["runtime_failure_count"]) == 0
        )
        threshold_name = "primary22_smoke_v3"
    else:
        passed = (
            float(bucket["auto_decidable_f1"]["f1"]) > PROMOTION_AUTO_F1_STRICT_MIN
            and float(bucket["coverage"]["definite_decision_rate"]) >= MIN_COVERAGE
            and int(bucket["coverage"]["runtime_failure_count"]) == 0
        )
        threshold_name = "pure_model_full127_v3"
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
            "auto_f1_must_be_greater_than": PROMOTION_AUTO_F1_STRICT_MIN,
            "coverage_min": MIN_COVERAGE,
            "runtime_failure_max": 0,
            "hybrid_or_reused_baseline_runs_promotable": False,
        },
    }
    write_json(run_dir(run_id) / "guardrail_status.json", payload)
    return payload


def decision_counts(run_id: str) -> dict[str, Any]:
    rows = read_json(run_dir(run_id) / "assembled_results.json")
    return {
        "all": dict(Counter(row.get("final_stage_decision") for row in rows)),
        "primary22": dict(Counter(row.get("final_stage_decision") for row in rows if row.get("slice_type") == "non_tension_primary")),
        "secondary105": dict(Counter(row.get("final_stage_decision") for row in rows if row.get("slice_type") == "criteria_gold_tension_secondary")),
    }


def threshold_math(*, positives: int = 114, negatives: int = 13) -> dict[str, Any]:
    rows = []
    for fp in range(0, negatives + 1):
        min_tp = None
        for tp in range(positives + 1):
            f1 = 2 * tp / (2 * tp + fp + (positives - tp)) if tp or fp or positives - tp else 0.0
            if f1 > PROMOTION_AUTO_F1_STRICT_MIN:
                min_tp = tp
                break
        rows.append({"fp": fp, "min_tp_for_f1_gt_0.8": min_tp, "min_recall": min_tp / positives if min_tp is not None else None})
    return {"positive_count": positives, "negative_count": negatives, "rows": rows, "all_positive_f1_ceiling": 2 * positives / (2 * positives + negatives)}


def run_one(*, run_id: str, scope: Literal["primary22", "full127"], profile: RecallProfile, cost_cap_usd: float, concurrency: int, retry_attempts: int, limit: int | None = None, canary: bool = False, dry_run: bool = False) -> dict[str, Any]:
    init_recall_run(run_id=run_id, scope=scope, profile=profile, cost_cap_usd=cost_cap_usd, limit=limit)
    direct.write_synthetic_stage1(run_id=run_id)
    parsed = run_direct_phase(run_id=run_id, profile=profile, cost_cap_usd=cost_cap_usd, concurrency=concurrency, retry_attempts=retry_attempts, dry_run=dry_run)
    if dry_run or parsed.get("status") == "stopped_cost_cap_before_direct_calls":
        return {"run_id": run_id, "status": parsed.get("status"), "parsed": parsed}
    result = evaluate_validate_analyze(run_id=run_id)
    guard = guardrail_status(run_id=run_id, scope=scope, canary=canary)
    manifest = read_json(run_dir(run_id) / "run_manifest.json")
    manifest["guardrail_status_path"] = repo_rel(run_dir(run_id) / "guardrail_status.json")
    manifest["status"] = "guardrail_passed" if guard["passed"] else "guardrail_failed"
    if canary:
        manifest["status"] = "canary_passed" if guard["passed"] else "canary_failed"
    manifest["decision_counts"] = decision_counts(run_id)
    manifest["updated_at"] = utc_now_iso()
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    return {"run_id": run_id, "status": manifest["status"], "guardrail": guard, "parsed": parsed, **result}


def rebuild_one(*, run_id: str, source_run_id: str, scope: Literal["primary22", "full127"], profile: RecallProfile, cost_cap_usd: float) -> dict[str, Any]:
    init_recall_run(run_id=run_id, scope=scope, profile=profile, cost_cap_usd=cost_cap_usd)
    direct.write_synthetic_stage1(run_id=run_id)
    parsed = rebuild_direct_phase_from_source(run_id=run_id, source_run_id=source_run_id, profile=profile)
    result = evaluate_validate_analyze(run_id=run_id)
    guard = guardrail_status(run_id=run_id, scope=scope, canary=False)
    manifest = read_json(run_dir(run_id) / "run_manifest.json")
    manifest["guardrail_status_path"] = repo_rel(run_dir(run_id) / "guardrail_status.json")
    manifest["status"] = "guardrail_passed" if guard["passed"] else "guardrail_failed"
    manifest["decision_counts"] = decision_counts(run_id)
    manifest["reused_direct_outputs_from_run_id"] = source_run_id
    manifest["updated_at"] = utc_now_iso()
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    return {"run_id": run_id, "status": manifest["status"], "guardrail": guard, "parsed": parsed, **result}


def write_recall_report(*, queue_status: dict[str, Any], run_ids: list[str]) -> None:
    lines = [
        "# BCPCS Recall Repair V3 Report",
        "",
        "這是 failure-slice dev diagnostic，不是 full benchmark，也不是 production workflow replacement。",
        "",
        "## Promotion Requirements",
        "",
        "- `gpt-5-nano` pure full127 auto F1 must be > `0.8000`.",
        "- `gpt-5.4-nano` pure full127 auto F1 must be > `0.8000`.",
        "- coverage must be >= `98.00%`; runtime failures must be `0`.",
        "- primary22 is smoke-only; hybrid / reused-baseline / sentinel rows are not promotable.",
        "",
        "## Results",
        "",
        "| run_id | model | scope | auto F1 | precision | recall | TP/FP/TN/FN | coverage | decisions | status | cost |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | --- | ---: |",
    ]
    total_cost = 0.0
    for rid in run_ids:
        rd = run_dir(rid)
        if not (rd / "evaluation_summary_v2.json").exists():
            continue
        summary = read_json(rd / "evaluation_summary_v2.json")
        manifest = read_json(rd / "run_manifest.json")
        scope = summary.get("scope")
        bucket = summary["primary22"] if scope == "primary22" else summary["all127"]
        cost_summary = read_json(rd / "cost" / "cost_summary.json") if (rd / "cost" / "cost_summary.json").exists() else {}
        cost = float(cost_summary.get("total_cost_usd") or 0.0)
        total_cost += cost
        decisions = manifest.get("decision_counts", {}).get("all", {})
        m = bucket["auto_decidable_f1"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{rid}`",
                    f"`{manifest.get('model')}`",
                    str(scope),
                    f"{m['f1']:.4f}",
                    f"{m['precision']:.4f}",
                    f"{m['recall']:.4f}",
                    f"{m['tp']}/{m['fp']}/{m['tn']}/{m['fn']}",
                    f"{bucket['coverage']['definite_decision_rate']:.2%}",
                    "`" + json.dumps(decisions, ensure_ascii=False, sort_keys=True) + "`",
                    str(manifest.get("status")),
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
            "## Threshold Math",
            "",
            "```json",
            json.dumps(threshold_math(), ensure_ascii=False, indent=2),
            "```",
            "",
            "## Interpretation",
            "",
            f"- Direct API cost for this V3 recall repair queue: `${total_cost:.6f}`.",
            "- The V3 profile is recall-biased by design: boundary/incomplete cases are compiled to `maybe` rather than `exclude`.",
            "- `maybe` is positive under repo default `include_or_maybe`; maybe counts are therefore reported explicitly as regression-risk context.",
            "- Gold/prior verdict/error taxonomy did not enter reviewer prompts; gold is only used after completion for evaluation and taxonomy.",
        ]
    )
    write_json(REPORTS_ROOT / "failure_slice_recall_repair_queue_status.json", queue_status)
    (REPORTS_ROOT / "failure_slice_recall_repair_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_queue(*, cost_cap_usd: float, concurrency: int, retry_attempts: int) -> dict[str, Any]:
    queue_status: dict[str, Any] = {
        "created_at": utc_now_iso(),
        "policy_version": "pure_model_full127_gt_0p8_v3_recall_repair",
        "statuses": [],
        "promoted_run_ids_by_model": {},
        "overall_passed": False,
    }
    run_ids: list[str] = []
    for profile in [PROFILES["recall_boundary_maybe_v1_gpt5nano"], PROFILES["recall_boundary_maybe_v1_gpt54nano"]]:
        model_tag = profile.model.replace(".", "")
        canary_id = f"bcpcs_recall_v3_canary5_{model_tag}_{profile.profile_id}_{TODAY}_v1"
        canary = run_one(run_id=canary_id, scope="primary22", profile=profile, cost_cap_usd=cost_cap_usd, concurrency=concurrency, retry_attempts=retry_attempts, limit=CANARY_SIZE, canary=True)
        run_ids.append(canary_id)
        queue_status["statuses"].append({"run_id": canary_id, "model": profile.model, "kind": "canary5", "status": canary["status"], "guardrail": canary.get("guardrail")})
        if canary["status"] != "canary_passed":
            continue
        primary_id = f"bcpcs_recall_v3_primary22_{model_tag}_{profile.profile_id}_{TODAY}_v1"
        primary = run_one(run_id=primary_id, scope="primary22", profile=profile, cost_cap_usd=cost_cap_usd, concurrency=concurrency, retry_attempts=retry_attempts)
        run_ids.append(primary_id)
        queue_status["statuses"].append({"run_id": primary_id, "model": profile.model, "kind": "primary22", "status": primary["status"], "guardrail": primary.get("guardrail")})
        if primary["status"] != "guardrail_passed":
            continue
        full_id = f"bcpcs_recall_v3_full127_{model_tag}_{profile.profile_id}_{TODAY}_v1"
        full = run_one(run_id=full_id, scope="full127", profile=profile, cost_cap_usd=cost_cap_usd, concurrency=concurrency, retry_attempts=retry_attempts)
        run_ids.append(full_id)
        queue_status["statuses"].append({"run_id": full_id, "model": profile.model, "kind": "full127", "status": full["status"], "guardrail": full.get("guardrail")})
        if full["status"] == "guardrail_passed":
            queue_status["promoted_run_ids_by_model"][profile.model] = full_id
    queue_status["completed_at"] = utc_now_iso()
    queue_status["run_ids"] = run_ids
    queue_status["overall_passed"] = all(model in queue_status["promoted_run_ids_by_model"] for model in REQUIRED_MODELS)
    queue_status["stop_reason"] = "all_required_pure_models_passed_v3" if queue_status["overall_passed"] else "pure_model_full127_gt_0p8_requirement_not_met"
    write_recall_report(queue_status=queue_status, run_ids=run_ids)
    return queue_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BCPCS failure-slice recall repair V3.")
    parser.add_argument("--command", choices=["queue", "run-one", "rebuild-one"], default="queue")
    parser.add_argument("--run-id")
    parser.add_argument("--source-run-id")
    parser.add_argument("--profile-key", choices=sorted(PROFILES), default="recall_boundary_maybe_v1_gpt5nano")
    parser.add_argument("--scope", choices=["primary22", "full127"], default="primary22")
    parser.add_argument("--cost-cap-usd", type=float, default=DEFAULT_COST_CAP_USD)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--retry-attempts", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.command == "queue":
        payload = run_queue(cost_cap_usd=args.cost_cap_usd, concurrency=args.concurrency, retry_attempts=args.retry_attempts)
    elif args.command == "run-one":
        if not args.run_id:
            raise SystemExit("--run-id is required for run-one")
        payload = run_one(
            run_id=args.run_id,
            scope=args.scope,
            profile=PROFILES[args.profile_key],
            cost_cap_usd=args.cost_cap_usd,
            concurrency=args.concurrency,
            retry_attempts=args.retry_attempts,
            dry_run=args.dry_run,
        )
    else:
        if not args.run_id or not args.source_run_id:
            raise SystemExit("--run-id and --source-run-id are required for rebuild-one")
        payload = rebuild_one(
            run_id=args.run_id,
            source_run_id=args.source_run_id,
            scope=args.scope,
            profile=PROFILES[args.profile_key],
            cost_cap_usd=args.cost_cap_usd,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
