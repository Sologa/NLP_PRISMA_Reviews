#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import failure_slice_common as common
import failure_slice_runner as base
from failure_slice_prompts import build_stage2_prompt as build_original_stage2_prompt
from failure_slice_common import CostRates, cost_dir, read_json, repo_rel, run_dir, utc_now_iso, write_json
from failure_slice_cost_audit import audit_cost_ledger
from failure_slice_eval_v2 import evaluate_results_v2
from failure_slice_reports import write_leakage_audit
from failure_slice_validate import validate_run_artifacts


GPT5_NANO_RATES = CostRates(input_per_million=0.05, cached_input_per_million=0.005, output_per_million=0.40, batch_discount=0.5)
GPT54_NANO_RATES = CostRates(input_per_million=0.20, cached_input_per_million=0.02, output_per_million=1.25, batch_discount=0.5)


@dataclass(frozen=True)
class MethodProfile:
    model: str
    stage1_effort: str
    stage2_effort: str
    max_completion_tokens: int
    fulltext_head_chars: int
    fulltext_tail_chars: int
    stage2_prompt_profile: str
    rates: CostRates


PROFILES = {
    "gpt-5-nano": MethodProfile(
        model="gpt-5-nano",
        stage1_effort="high",
        stage2_effort="high",
        max_completion_tokens=32768,
        fulltext_head_chars=90_000,
        fulltext_tail_chars=30_000,
        stage2_prompt_profile="original_high_effort",
        rates=GPT5_NANO_RATES,
    ),
    "gpt-5.4-nano": MethodProfile(
        model="gpt-5.4-nano",
        stage1_effort="high",
        stage2_effort="high",
        max_completion_tokens=32768,
        fulltext_head_chars=90_000,
        fulltext_tail_chars=30_000,
        stage2_prompt_profile="original_high_effort",
        rates=GPT54_NANO_RATES,
    ),
}


def _json_block(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _compact_stage1_handoff(stage1_output: dict[str, Any]) -> dict[str, Any]:
    ledger = []
    for row in stage1_output.get("evidence_ledger") or []:
        if not isinstance(row, dict):
            continue
        ledger.append(
            {
                "claim_id": row.get("claim_id"),
                "evidence_status": row.get("evidence_status"),
                "missingness_reason": row.get("missingness_reason"),
                "confidence": row.get("confidence"),
            }
        )
    return {
        "final_stage_decision": stage1_output.get("final_stage_decision"),
        "missingness_reason": stage1_output.get("missingness_reason"),
        "confidence": stage1_output.get("confidence"),
        "route_reason": stage1_output.get("route_reason"),
        "unknown_reason": stage1_output.get("unknown_reason"),
        "ledger_summary": ledger[:4],
    }


def build_compact_stage2_prompt(
    *,
    paper_id: str,
    candidate_key: str,
    criteria: dict[str, Any],
    metadata: dict[str, Any],
    fulltext_text: str,
    fulltext_meta: dict[str, Any],
    stage1_handoff: dict[str, Any],
    criteria_path: str,
    metadata_path: str,
) -> str:
    visible_payload = {
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
        "source_paths": {
            "criteria_path": criteria_path,
            "metadata_path": metadata_path,
            "fulltext_source_path": fulltext_meta.get("fulltext_source_path"),
        },
        "fulltext_meta": fulltext_meta,
        "stage1_bcpcs_handoff_compact": _compact_stage1_handoff(stage1_handoff),
    }
    output_contract = {
        "decision_rationale": "Keep under 60 words.",
        "evidence_ledger": "Use 1-3 decisive rows. Prefer short exact quotes under 180 characters.",
        "missingness": "Use retrieval_failure or metadata_ambiguity for source problems; do not turn retrieval problems into semantic_non_fit.",
        "format": "Return only valid JSON matching the schema. No markdown fences.",
    }
    return "\n\n".join(
        [
            "You are a single screening reviewer running a BCPCS failure-slice diagnostic.",
            "Use only the supplied criteria, metadata, Stage 1 handoff, and full-text excerpt. Do not use prior benchmarks or external knowledge.",
            "Stage 2 task: make the final full-text decision with a compact claim-level evidence ledger.",
            "Allowed final_stage_decision values: include, exclude, maybe, unknown.",
            "If the excerpt is insufficient for a semantic decision, return unknown with evidence_incomplete; do not fabricate evidence.",
            "Output contract:",
            _json_block(output_contract),
            "Stage 2 criteria JSON:",
            _json_block(criteria),
            "Candidate visible record:",
            _json_block(visible_payload),
            "Full-text excerpt:",
            fulltext_text,
        ]
    )


def _apply_profile(profile: MethodProfile) -> None:
    common.DEFAULT_MODEL = profile.model
    base.DEFAULT_MODEL = profile.model
    base.MAX_COMPLETION_TOKENS = profile.max_completion_tokens
    common.estimate_batch_cost = lambda *, input_tokens, output_tokens, rates=None: (
        (input_tokens / 1_000_000) * (rates or profile.rates).effective_input_per_million()
        + (output_tokens / 1_000_000) * (rates or profile.rates).effective_output_per_million()
    )
    base.estimate_batch_cost = common.estimate_batch_cost
    original_fulltext = base.fulltext_payload_from_resolution

    def _profiled_fulltext(resolution: dict[str, Any], *, repo_root: Path, head_chars: int, tail_chars: int) -> tuple[str, dict[str, Any]]:
        return original_fulltext(
            resolution,
            repo_root=repo_root,
            head_chars=profile.fulltext_head_chars,
            tail_chars=profile.fulltext_tail_chars,
        )

    base.fulltext_payload_from_resolution = _profiled_fulltext
    if profile.stage2_prompt_profile == "compact_ledger_decision_first":
        base.build_stage2_prompt = build_compact_stage2_prompt
    else:
        base.build_stage2_prompt = build_original_stage2_prompt


def _pricing_snapshot(profile: MethodProfile) -> dict[str, Any]:
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
            "https://developers.openai.com/api/docs/models/gpt-5-nano",
            "https://developers.openai.com/api/docs/models/gpt-5.4-nano",
            "https://openai.com/api/pricing/",
        ],
    }


def init_method_run(*, run_id: str, scope: str, profile: MethodProfile, cost_cap_usd: float) -> dict[str, Any]:
    _apply_profile(profile)
    manifest = base.init_run(run_id=run_id, scope=scope, reasoning_effort=profile.stage1_effort, cost_cap_usd=cost_cap_usd)
    manifest["experiment_name"] = "bcpcs_failure_slice_methodfix"
    manifest["model"] = profile.model
    manifest["stage_efforts"] = {"stage1_review": profile.stage1_effort, "stage2_review": profile.stage2_effort}
    manifest["methodfix_profile"] = {
        "max_completion_tokens": profile.max_completion_tokens,
        "fulltext_head_chars": profile.fulltext_head_chars,
        "fulltext_tail_chars": profile.fulltext_tail_chars,
        "stage2_prompt": profile.stage2_prompt_profile,
        "eval": "v2_auto_decidable_plus_coverage",
    }
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    write_json(cost_dir(run_id) / "pricing_snapshot.json", _pricing_snapshot(profile))
    return manifest


def _collect_and_audit(*, run_id: str, phase: str, effort: str, poll_interval_sec: float, max_wait_minutes: float) -> dict[str, Any]:
    payload = base.collect_phase(
        run_id=run_id,
        phase=phase,
        reasoning_effort=effort,
        poll_interval_sec=poll_interval_sec,
        max_wait_minutes=max_wait_minutes,
    )
    audit_cost_ledger(run_path=run_dir(run_id), rewrite_summary=True)
    return payload


def evaluate_v2_and_report(*, run_id: str) -> dict[str, Any]:
    rd = run_dir(run_id)
    base.assemble_results(run_id=run_id)
    evaluation = evaluate_results_v2(run_dir=rd)
    validation = validate_run_artifacts(rd)
    write_leakage_audit(run_id=run_id, run_dir=rd, validation=validation)
    manifest = read_json(rd / "run_manifest.json")
    manifest["status"] = "reported_v2"
    manifest["evaluation_summary_v2_path"] = repo_rel(rd / "evaluation_summary_v2.json")
    manifest["validation_summary_path"] = repo_rel(rd / "validation_summary.json")
    write_json(rd / "run_manifest.json", manifest)
    return {"evaluation_v2": evaluation, "validation": validation}


def _has_failures(parsed_payload: dict[str, Any]) -> bool:
    return bool(parsed_payload.get("failures") or parsed_payload.get("missing"))


def run_flow(
    *,
    run_id: str,
    scope: str,
    model: str,
    cost_cap_usd: float,
    poll_interval_sec: float,
    max_wait_minutes: float,
) -> dict[str, Any]:
    profile = PROFILES[model]
    init_method_run(run_id=run_id, scope=scope, profile=profile, cost_cap_usd=cost_cap_usd)
    base.dry_run_loader_validation(run_id=run_id, reasoning_effort=profile.stage1_effort)
    base.submit_phase(
        run_id=run_id,
        phase="stage1_review",
        reasoning_effort=profile.stage1_effort,
        cost_cap_usd=cost_cap_usd,
        dry_run=False,
    )
    stage1 = _collect_and_audit(
        run_id=run_id,
        phase="stage1_review",
        effort=profile.stage1_effort,
        poll_interval_sec=poll_interval_sec,
        max_wait_minutes=max_wait_minutes,
    )
    if _has_failures(stage1):
        return {"run_id": run_id, "status": "stopped_stage1_parse_failure", **evaluate_v2_and_report(run_id=run_id)}
    if read_json(cost_dir(run_id) / "cost_summary.json")["total_cost_usd"] > cost_cap_usd:
        return {"run_id": run_id, "status": "stopped_cost_after_stage1", **evaluate_v2_and_report(run_id=run_id)}
    base.submit_phase(
        run_id=run_id,
        phase="stage2_review",
        reasoning_effort=profile.stage2_effort,
        cost_cap_usd=cost_cap_usd,
        dry_run=False,
    )
    stage2 = _collect_and_audit(
        run_id=run_id,
        phase="stage2_review",
        effort=profile.stage2_effort,
        poll_interval_sec=poll_interval_sec,
        max_wait_minutes=max_wait_minutes,
    )
    result = evaluate_v2_and_report(run_id=run_id)
    status = "completed_clean" if not _has_failures(stage2) else "completed_with_stage2_failures"
    manifest = read_json(run_dir(run_id) / "run_manifest.json")
    manifest["status"] = status
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    return {"run_id": run_id, "status": status, **result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scope", choices=["primary22", "full127"], required=True)
    parser.add_argument("--model", choices=sorted(PROFILES), required=True)
    parser.add_argument("--cost-cap-usd", type=float, default=10.0)
    parser.add_argument("--poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--max-wait-minutes", type=float, default=240.0)
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        common.load_dotenv_if_present()
    payload = run_flow(
        run_id=args.run_id,
        scope=args.scope,
        model=args.model,
        cost_cap_usd=args.cost_cap_usd,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:12000])
    return 0 if payload["status"] in {"completed_clean", "completed_with_stage2_failures"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
