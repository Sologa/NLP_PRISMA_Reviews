#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

import failure_slice_common as common
import failure_slice_runner as runner
from failure_slice_common import (
    CostRates,
    append_jsonl,
    ensure_dir,
    load_dotenv_if_present,
    read_json,
    read_jsonl,
    request_rows_token_estimate,
    run_dir,
    utc_now_iso,
    write_json,
)
from failure_slice_cost_audit import audit_cost_ledger
from failure_slice_validate import find_forbidden_prompt_terms
from scripts.screening.openai_batch_runner import OpenAIBatchRunner


def _model_rates(model: str) -> CostRates:
    if model == "gpt-5.4-nano":
        return CostRates(
            input_per_million=0.20,
            cached_input_per_million=0.05,
            output_per_million=1.25,
            batch_discount=0.5,
            source="https://openai.com/api/pricing/",
        )
    return CostRates.gpt5_nano_batch()


def _patch_model(model: str) -> None:
    common.DEFAULT_MODEL = model
    runner.DEFAULT_MODEL = model


def _load_failed_ids(parsed_path: Path) -> list[str]:
    parsed = read_json(parsed_path)
    failures = parsed.get("failures") or []
    return [str(row.get("custom_id")) for row in failures if row.get("custom_id")]


def _prompt_hits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in rows:
        text = json.dumps(row.get("body", {}), ensure_ascii=False)
        terms = find_forbidden_prompt_terms(text)
        if terms:
            hits.append({"custom_id": row.get("custom_id"), "terms": terms})
    return hits


def _estimate_cost(*, rows: list[dict[str, Any]], rates: CostRates) -> dict[str, Any]:
    input_tokens = request_rows_token_estimate(rows)
    output_tokens = len(rows) * runner.MAX_COMPLETION_TOKENS
    estimated_cost = common.estimate_batch_cost(input_tokens=input_tokens, output_tokens=output_tokens, rates=rates)
    return {
        "created_at": utc_now_iso(),
        "request_count": len(rows),
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost,
        "estimate_policy": "input tokenizer_or_char_overestimate; output max_completion_tokens per request",
    }


def _append_retry_cost(
    *,
    run_path: Path,
    phase: str,
    batch_id: str | None,
    specs: list[Any],
    parsed_payload: dict[str, Any],
    artifact_dir: Path,
    rates: CostRates,
) -> dict[str, Any]:
    spec_by_id = {spec.custom_id: spec for spec in specs}
    output_path = artifact_dir / "output.jsonl"
    output_rows = read_jsonl(output_path) if output_path.exists() else []
    output_by_id = {str(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
    success_by_id = {row["custom_id"]: row for row in parsed_payload.get("successes", [])}

    phase_input = 0
    phase_output = 0
    phase_cost = 0.0
    actual_usage_rows = 0
    estimated_rows = 0
    for custom_id, spec in spec_by_id.items():
        usage = common.usage_from_batch_output_row(output_by_id.get(custom_id, {}))
        assistant_text = str(success_by_id.get(custom_id, {}).get("assistant_text") or "")
        if usage and "input_tokens" in usage and "output_tokens" in usage:
            input_tokens = int(usage["input_tokens"])
            output_tokens = int(usage["output_tokens"])
            cost_source = "batch_usage"
            actual_usage_rows += 1
        else:
            input_tokens = common.estimate_text_tokens(json.dumps(spec.body, ensure_ascii=False))
            output_tokens = common.estimate_text_tokens(assistant_text) if assistant_text else runner.MAX_COMPLETION_TOKENS
            cost_source = "estimated"
            estimated_rows += 1
        cost_usd = common.estimate_batch_cost(input_tokens=input_tokens, output_tokens=output_tokens, rates=rates)
        append_jsonl(
            run_path / "cost" / "cost_ledger.jsonl",
            {
                "created_at": utc_now_iso(),
                "phase": phase,
                "custom_id": custom_id,
                "batch_id": batch_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "cost_source": cost_source,
            },
        )
        phase_input += input_tokens
        phase_output += output_tokens
        phase_cost += cost_usd
    return {
        "input_tokens": phase_input,
        "output_tokens": phase_output,
        "total_cost_usd": phase_cost,
        "actual_usage_rows": actual_usage_rows,
        "estimated_rows": estimated_rows,
    }


def _merge_retry_successes(
    *,
    run_path: Path,
    phase: str,
    retry_artifact_dir: Path,
    retry_payload: dict[str, Any],
) -> dict[str, Any]:
    canonical_artifact_dir = run_path / "batch_jobs" / phase / common.DEFAULT_MODEL
    canonical_parsed_path = canonical_artifact_dir / "parsed_results.json"
    original_parsed = read_json(canonical_parsed_path)
    before_path = canonical_artifact_dir / "parsed_results_before_retry1.json"
    if not before_path.exists():
        write_json(before_path, original_parsed)

    retry_success_by_id = {row["custom_id"]: row for row in retry_payload.get("successes", [])}
    remaining_failures = []
    for row in original_parsed.get("failures", []):
        if row.get("custom_id") not in retry_success_by_id:
            remaining_failures.append(row)
    remaining_missing = []
    for row in original_parsed.get("missing", []):
        if row.get("custom_id") not in retry_success_by_id:
            remaining_missing.append(row)

    merged_successes = list(original_parsed.get("successes", []))
    existing_ids = {row.get("custom_id") for row in merged_successes}
    for row in retry_payload.get("successes", []):
        if row.get("custom_id") not in existing_ids:
            merged_successes.append(row)
    for row in retry_payload.get("failures", []):
        if row.get("custom_id") not in {item.get("custom_id") for item in remaining_failures}:
            remaining_failures.append(row)
    for row in retry_payload.get("missing", []):
        if row.get("custom_id") not in {item.get("custom_id") for item in remaining_missing}:
            remaining_missing.append(row)

    merged = {
        "batch_id": original_parsed.get("batch_id"),
        "batch_status": original_parsed.get("batch_status"),
        "successes": sorted(merged_successes, key=lambda row: str(row.get("custom_id") or "")),
        "failures": sorted(remaining_failures, key=lambda row: str(row.get("custom_id") or "")),
        "missing": sorted(remaining_missing, key=lambda row: str(row.get("custom_id") or "")),
        "output_row_count": int(original_parsed.get("output_row_count") or 0) + int(retry_payload.get("output_row_count") or 0),
        "error_row_count": int(original_parsed.get("error_row_count") or 0) + int(retry_payload.get("error_row_count") or 0),
        "retry_merged_from": str(retry_artifact_dir),
        "merged_at": utc_now_iso(),
    }
    write_json(canonical_artifact_dir / "parsed_results.json", merged)
    runner._write_phase_review_outputs(run_id=run_path.name, phase=phase, parsed_payload=merged)
    return merged


def run_retry(
    *,
    run_id: str,
    phase: str,
    retry_phase: str,
    model: str,
    reasoning_effort: str,
    poll_interval_sec: float,
    max_wait_minutes: float,
    cost_cap_usd: float,
) -> dict[str, Any]:
    run_path = run_dir(run_id)
    _patch_model(model)
    rates = _model_rates(model)

    source_parsed_path = run_path / "batch_jobs" / phase / model / "parsed_results.json"
    failed_ids = _load_failed_ids(source_parsed_path)
    if not failed_ids:
        payload = {"status": "skipped_no_failures", "run_id": run_id, "phase": phase, "retry_phase": retry_phase}
        write_json(run_path / "batch_jobs" / retry_phase / model / "retry_summary.json", payload)
        return payload

    all_specs = runner.prepare_specs(run_path=run_path, phase=phase, reasoning_effort=reasoning_effort)
    specs = [spec for spec in all_specs if spec.custom_id in set(failed_ids)]
    artifact_dir = ensure_dir(run_path / "batch_jobs" / retry_phase / model)
    rows = OpenAIBatchRunner(client=None, poll_interval_sec=poll_interval_sec).serialize_requests(
        specs,
        endpoint=common.DEFAULT_ENDPOINT,
    )
    common.write_jsonl(artifact_dir / "input.jsonl", rows)

    audited_cost = audit_cost_ledger(run_path=run_path, rewrite_summary=True)["deduped_summary"]["total_cost_usd"]
    estimate = {
        **_estimate_cost(rows=rows, rates=rates),
        "phase": retry_phase,
        "prior_actual_or_estimated_cost_usd": audited_cost,
        "projected_total_cost_usd": audited_cost + _estimate_cost(rows=rows, rates=rates)["estimated_cost_usd"],
        "cost_cap_usd": cost_cap_usd,
        "would_exceed_cost_cap": audited_cost + _estimate_cost(rows=rows, rates=rates)["estimated_cost_usd"] > cost_cap_usd,
    }
    write_json(run_path / "cost" / f"pre_submit_estimate.{retry_phase}.json", estimate)

    prompt_hits = _prompt_hits(rows)
    if prompt_hits:
        payload = {"status": "stopped_forbidden_prompt_terms", "hits": prompt_hits}
        write_json(artifact_dir / "leakage_stop.json", payload)
        raise RuntimeError(f"Forbidden prompt terms detected: {prompt_hits[:3]}")
    if estimate["would_exceed_cost_cap"]:
        payload = {"status": "stopped_cost_cap", "estimate": estimate}
        write_json(run_path / "cost" / "cost_stop.json", payload)
        return payload

    load_dotenv_if_present()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    client = OpenAI()
    batch_runner = OpenAIBatchRunner(client=client, poll_interval_sec=poll_interval_sec)
    submit_payload = batch_runner.submit_requests(
        specs=specs,
        endpoint=common.DEFAULT_ENDPOINT,
        artifact_dir=artifact_dir,
        metadata={
            "experiment": "bcpcs_failure_slice",
            "run_id": run_id,
            "phase": retry_phase,
            "model": model,
        },
    )
    batch_payload = batch_runner.wait_until_terminal(
        submit_payload["batch_create"]["id"],
        artifact_dir=artifact_dir,
        max_wait_minutes=max_wait_minutes,
    )
    parsed_payload = batch_runner.collect_results(specs=specs, batch_payload=batch_payload, artifact_dir=artifact_dir)
    phase_cost = _append_retry_cost(
        run_path=run_path,
        phase=retry_phase,
        batch_id=str(batch_payload.get("id") or ""),
        specs=specs,
        parsed_payload=parsed_payload,
        artifact_dir=artifact_dir,
        rates=rates,
    )
    audited = audit_cost_ledger(run_path=run_path, rewrite_summary=True)
    merged = _merge_retry_successes(
        run_path=run_path,
        phase=phase,
        retry_artifact_dir=artifact_dir,
        retry_payload=parsed_payload,
    )

    manifest_path = run_path / "run_manifest.json"
    manifest = read_json(manifest_path)
    manifest["phase_jobs"][retry_phase] = {
        "phase": retry_phase,
        "batch_artifact_dir": str(artifact_dir.relative_to(common.REPO_ROOT)),
        "batch_id": batch_payload.get("id"),
        "batch_status": batch_payload.get("status"),
        "request_count": len(specs),
        "pre_submit_estimate": estimate,
        "upload_file_id": submit_payload["upload_file"]["id"],
        "batch_completed_at": batch_payload.get("completed_at"),
        "batch_output_file_id": batch_payload.get("output_file_id"),
        "batch_error_file_id": batch_payload.get("error_file_id"),
        "parsed_summary": {
            "success_count": len(parsed_payload.get("successes", [])),
            "failure_count": len(parsed_payload.get("failures", [])),
            "missing_count": len(parsed_payload.get("missing", [])),
        },
        "cost_summary": phase_cost,
    }
    manifest["phase_jobs"].setdefault(phase, {})["post_retry_summary"] = {
        "success_count": len(merged.get("successes", [])),
        "failure_count": len(merged.get("failures", [])),
        "missing_count": len(merged.get("missing", [])),
    }
    manifest["status"] = f"collected_{retry_phase}"
    write_json(manifest_path, manifest)

    summary = {
        "status": batch_payload.get("status"),
        "retry_phase": retry_phase,
        "failed_input_count": len(failed_ids),
        "retry_success_count": len(parsed_payload.get("successes", [])),
        "retry_failure_count": len(parsed_payload.get("failures", [])),
        "retry_missing_count": len(parsed_payload.get("missing", [])),
        "merged_failure_count": len(merged.get("failures", [])),
        "merged_missing_count": len(merged.get("missing", [])),
        "audited_total_cost_usd": audited["deduped_summary"]["total_cost_usd"],
    }
    write_json(artifact_dir / "retry_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", default="stage2_review")
    parser.add_argument("--retry-phase", default="stage2_review_retry1")
    parser.add_argument("--model", default="gpt-5.4-nano")
    parser.add_argument("--reasoning-effort", default="xhigh")
    parser.add_argument("--poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--max-wait-minutes", type=float, default=240.0)
    parser.add_argument("--cost-cap-usd", type=float, default=10.0)
    args = parser.parse_args()
    payload = run_retry(
        run_id=args.run_id,
        phase=args.phase,
        retry_phase=args.retry_phase,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
        cost_cap_usd=args.cost_cap_usd,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("retry_failure_count", 0) == 0 and payload.get("retry_missing_count", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
