#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_experiment as base_run


RETRYABLE_SERVER_ERROR_MESSAGE = "The server had an error while processing your request. Sorry about that!"
TOKEN_COST_SUMMARY_NAME = "TOKEN_COST_SUMMARY_zh.md"
RETRY_AUDIT_NAME = "RETRY_AUDIT_zh.md"
STAGE1_SOURCE_MAP_NAME = "stage1_source_attempts.json"
STAGE2_SOURCE_MAP_NAME = "stage2_source_attempts.json"

MODEL_BATCH_PRICING = {
    "gpt-5.4": {
        "input_per_million": Decimal("1.25"),
        "cached_input_per_million": Decimal("0.125"),
        "output_per_million": Decimal("7.5"),
    }
}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _read_json_if_exists(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return base_run.read_json(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        rows.append(json.loads(stripped))
    return rows


def _error_message(error_row: dict[str, Any]) -> str:
    response = error_row.get("response") or {}
    body = response.get("body") or {}
    error = body.get("error") or {}
    return str(error.get("message") or "unknown_error")


def summarize_error_messages(error_rows: list[dict[str, Any]]) -> list[tuple[str, int]]:
    counter = Counter(_error_message(row) for row in error_rows)
    return counter.most_common()


def _all_errors_retryable(error_rows: list[dict[str, Any]]) -> bool:
    if not error_rows:
        return True
    return all(_error_message(row) == RETRYABLE_SERVER_ERROR_MESSAGE for row in error_rows)


def merge_stage_rows(attempt_rows_by_run: list[tuple[str, list[dict[str, Any]]]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    merged: list[dict[str, Any]] = []
    source_runs: dict[str, str] = {}
    seen: set[str] = set()
    for run_id, rows in attempt_rows_by_run:
        for row in rows:
            candidate_key = _safe_text(row.get("candidate_key"))
            if not candidate_key or candidate_key in seen:
                continue
            merged.append(row)
            source_runs[candidate_key] = run_id
            seen.add(candidate_key)
    return merged, source_runs


def aggregate_attempt_usage(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    total = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }
    for attempt in attempts:
        usage = attempt.get("usage") or {}
        total["input_tokens"] += int(usage.get("input_tokens") or 0)
        total["cached_input_tokens"] += int(usage.get("cached_input_tokens") or 0)
        total["output_tokens"] += int(usage.get("output_tokens") or 0)
        total["reasoning_tokens"] += int(usage.get("reasoning_tokens") or 0)
        total["total_tokens"] += int(usage.get("total_tokens") or 0)
        total["cost_usd"] += float(attempt.get("cost_usd") or 0.0)
    total["cost_usd"] = round(total["cost_usd"], 6)
    return total


def _usage_from_batch_payload(batch_payload: dict[str, Any]) -> dict[str, int]:
    usage = batch_payload.get("usage") or {}
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "cached_input_tokens": int(input_details.get("cached_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "reasoning_tokens": int(output_details.get("reasoning_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def _cost_for_usage(model: str, usage: dict[str, int]) -> float:
    pricing = MODEL_BATCH_PRICING[model]
    uncached_input = Decimal(str(int(usage["input_tokens"]) - int(usage["cached_input_tokens"])))
    cached_input = Decimal(str(int(usage["cached_input_tokens"])))
    output = Decimal(str(int(usage["output_tokens"])))
    cost = (
        (uncached_input * pricing["input_per_million"] / Decimal("1000000"))
        + (cached_input * pricing["cached_input_per_million"] / Decimal("1000000"))
        + (output * pricing["output_per_million"] / Decimal("1000000"))
    )
    return float(cost)


def _candidate_keys_file(run_id: str, phase: str) -> Path:
    return base_run._run_dir(run_id) / f"{phase}.candidate_keys.json"


def _write_candidate_keys_file(path: Path, paper_id: str, keys: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dumps({paper_id: keys}), encoding="utf-8")


def _phase_rows(run_id: str, paper_id: str, phase: str) -> list[dict[str, Any]]:
    return _read_json_if_exists(base_run._phase_output_path(run_id, paper_id, phase), [])


def _parsed_results(run_id: str, phase: str, model: str) -> dict[str, Any]:
    return _read_json_if_exists(
        base_run._batch_artifact_dir(run_id, phase, model) / "parsed_results.json",
        {"successes": [], "failures": [], "missing": [], "batch_status": None},
    )


def _batch_payload(run_id: str, phase: str, model: str) -> dict[str, Any]:
    path = base_run._batch_artifact_dir(run_id, phase, model) / "batch_latest.json"
    return _read_json_if_exists(path, {})


def _error_rows(run_id: str, phase: str, model: str) -> list[dict[str, Any]]:
    return _read_jsonl(base_run._batch_artifact_dir(run_id, phase, model) / "error.jsonl")


def _stage_issue_keys(run_id: str, phase: str, model: str) -> list[str]:
    parsed = _parsed_results(run_id, phase, model)
    keys: list[str] = []
    for status_name in ("failures", "missing"):
        for row in parsed.get(status_name, []):
            context = row.get("context") or {}
            candidate_key = _safe_text(context.get("candidate_key"))
            if candidate_key:
                keys.append(candidate_key)
    return sorted(set(keys))


def _stage_success_keys(rows: list[dict[str, Any]]) -> set[str]:
    return {_safe_text(row.get("candidate_key")) for row in rows if _safe_text(row.get("candidate_key"))}


def _cutoff_pass_keys(paper_id: str) -> list[str]:
    records = base_run.load_candidates(base_run._paper_metadata_path(paper_id))
    cutoff_result = base_run.load_cutoff_result(records=records, cutoff_path=base_run._paper_cutoff_path(paper_id))
    return [_safe_text(row.get("key")) for row in cutoff_result["kept_records"]]


def _ensure_run_dir(run_id: str) -> None:
    base_run._run_dir(run_id).mkdir(parents=True, exist_ok=True)


def _seed_phase_rows(run_id: str, paper_id: str, phase: str, rows: list[dict[str, Any]]) -> None:
    path = base_run._phase_output_path(run_id, paper_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    base_run.write_json(path, rows)


def _seed_source_map(run_id: str, filename: str, source_map: dict[str, str]) -> None:
    path = base_run._run_dir(run_id) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    base_run.write_json(path, source_map)


def _collect_attempt_metadata(run_id: str, phase: str, model: str, request_count: int | None = None) -> dict[str, Any]:
    batch_payload = _batch_payload(run_id, phase, model)
    parsed = _parsed_results(run_id, phase, model)
    error_rows = _error_rows(run_id, phase, model)
    usage = _usage_from_batch_payload(batch_payload)
    cost_usd = _cost_for_usage(model, usage)
    request_counts = batch_payload.get("request_counts") or {}
    return {
        "run_id": run_id,
        "phase": phase,
        "batch_id": batch_payload.get("id"),
        "batch_status": batch_payload.get("status"),
        "request_count": int(request_count if request_count is not None else (request_counts.get("total") or 0)),
        "success_count": len(parsed.get("successes", [])),
        "failure_count": len(parsed.get("failures", [])),
        "missing_count": len(parsed.get("missing", [])),
        "usage": usage,
        "cost_usd": cost_usd,
        "error_messages": summarize_error_messages(error_rows),
    }


def _load_config_for_model(model: str) -> dict[str, Any]:
    config = base_run._load_config()
    return base_run._config_with_model_override(config, model)


def _prompt_assets() -> Any:
    return base_run.PromptAssets(base_run._load_workflow_spec())


def _ensure_phase_attempt(
    *,
    phase: str,
    run_id: str,
    paper_id: str,
    model: str,
    reasoning_effort: str,
    candidate_keys: list[str],
    stage1_seed_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = _load_config_for_model(model)
    prompt_assets = _prompt_assets()
    _ensure_run_dir(run_id)
    key_map_path = _candidate_keys_file(run_id, phase)
    _write_candidate_keys_file(key_map_path, paper_id, candidate_keys)
    key_map = base_run._load_candidate_key_map(key_map_path, selected_papers=[paper_id])

    if stage1_seed_rows is not None:
        _seed_phase_rows(run_id, paper_id, "stage1_review", stage1_seed_rows)

    run_manifest_path = base_run._run_manifest_path(run_id)
    run_manifest = _read_json_if_exists(run_manifest_path, {})
    phase_job = (run_manifest.get("phase_jobs") or {}).get(phase) or {}
    batch_status = phase_job.get("batch_status")
    if not batch_status:
        base_run._submit_phase(
            phase=phase,
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=[paper_id],
            key_map=key_map,
            key_map_path=key_map_path,
            max_records=None,
            reasoning_effort=reasoning_effort,
        )

    parsed = base_run._collect_phase(
        phase=phase,
        run_id=run_id,
        prompt_assets=prompt_assets,
        config=config,
        selected_papers=[paper_id],
        key_map=key_map,
        max_records=None,
        reasoning_effort=reasoning_effort,
        batch_poll_interval_sec=None,
        batch_max_wait_minutes=None,
    )
    return parsed


def _init_final_run_manifest(run_id: str, model: str, reasoning_effort: str, paper_id: str) -> dict[str, Any]:
    config = _load_config_for_model(model)
    manifest = base_run._load_or_init_run_manifest(
        run_id=run_id,
        config=config,
        selected_papers=[paper_id],
        key_map_path=None,
        max_records=None,
        reasoning_effort=reasoning_effort,
    )
    manifest["model_preflight_id"] = model
    base_run.write_json(base_run._run_manifest_path(run_id), manifest)
    return manifest


def _retry_run_id(prefix: str, phase: str, retry_index: int) -> str:
    suffix = "stage1" if phase == "stage1_review" else "stage2"
    return f"{prefix}{retry_index}_gpt54_xhigh_{suffix}_2409"


def _remaining_keys(all_keys: list[str], source_map: dict[str, str]) -> list[str]:
    return [key for key in all_keys if key not in source_map]


def _compute_stage2_selected_keys(final_run_id: str, paper_id: str, model: str, reasoning_effort: str) -> list[str]:
    config = _load_config_for_model(model)
    prep = base_run._phase_preparation(
        phase="stage2_review",
        run_id=final_run_id,
        prompt_assets=_prompt_assets(),
        config=config,
        selected_papers=[paper_id],
        key_map=None,
        max_records=None,
        reasoning_effort=reasoning_effort,
        write_audits=True,
    )
    return sorted({_safe_text(spec.context.get("candidate_key")) for spec in prep["specs"]})


def _build_consolidated_phase_job(
    *,
    phase: str,
    final_run_id: str,
    model: str,
    request_count: int,
    paper_preparation: dict[str, Any],
    source_attempt_run_ids: list[str],
) -> dict[str, Any]:
    return {
        "phase": phase,
        "batch_artifact_dir": str(base_run._batch_artifact_dir(final_run_id, phase, model)),
        "batch_id": None,
        "batch_status": "consolidated_success",
        "request_count": request_count,
        "paper_preparation": paper_preparation,
        "source_attempt_run_ids": source_attempt_run_ids,
        "parsed_summary": {
            "success_count": request_count,
            "failure_count": 0,
            "missing_count": 0,
        },
    }


def _write_token_cost_summary(
    *,
    final_run_id: str,
    model: str,
    reasoning_effort: str,
    attempts: list[dict[str, Any]],
) -> None:
    phase_totals: dict[str, dict[str, Any]] = {}
    for phase in ("stage1_review", "stage2_review"):
        phase_totals[phase] = aggregate_attempt_usage([item for item in attempts if item["phase"] == phase])

    total = aggregate_attempt_usage(attempts)
    lines = [
        "# Token / Cost Summary",
        "",
        f"- run_id: `{final_run_id}`",
        f"- model: `{model}`",
        f"- reasoning_effort: `{reasoning_effort}`",
        f"- scope: `2409.13738`",
        "",
        "## Attempt Totals By Phase",
        "",
    ]
    for phase in ("stage1_review", "stage2_review"):
        usage = phase_totals[phase]
        lines.extend(
            [
                f"### {phase}",
                "",
                f"- input_tokens: `{usage['input_tokens']}`",
                f"- cached_input_tokens: `{usage['cached_input_tokens']}`",
                f"- output_tokens: `{usage['output_tokens']}`",
                f"- reasoning_tokens: `{usage['reasoning_tokens']}`",
                f"- total_tokens: `{usage['total_tokens']}`",
                f"- estimated_batch_cost_usd: `{usage['cost_usd']:.6f}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Total Across All Attempts",
            "",
            f"- input_tokens: `{total['input_tokens']}`",
            f"- cached_input_tokens: `{total['cached_input_tokens']}`",
            f"- output_tokens: `{total['output_tokens']}`",
            f"- reasoning_tokens: `{total['reasoning_tokens']}`",
            f"- total_tokens: `{total['total_tokens']}`",
            f"- estimated_batch_cost_usd: `{total['cost_usd']:.6f}`",
            "",
            "## Attempt Breakdown",
            "",
            "| Phase | Run ID | Request count | Success | Failure | Cost (USD) |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for attempt in attempts:
        lines.append(
            f"| `{attempt['phase']}` | `{attempt['run_id']}` | {attempt['request_count']} | "
            f"{attempt['success_count']} | {attempt['failure_count']} | {attempt['cost_usd']:.6f} |"
        )

    (base_run._run_dir(final_run_id) / TOKEN_COST_SUMMARY_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_retry_audit(
    *,
    final_run_id: str,
    attempts: list[dict[str, Any]],
) -> None:
    lines = [
        "# Retry Audit",
        "",
        "| Phase | Run ID | Batch status | Request count | Success | Failure | Missing | Batch ID | Top errors |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for attempt in attempts:
        top_errors = "; ".join(f"{msg} ({count})" for msg, count in attempt["error_messages"][:3]) or "-"
        lines.append(
            f"| `{attempt['phase']}` | `{attempt['run_id']}` | `{attempt['batch_status']}` | "
            f"{attempt['request_count']} | {attempt['success_count']} | {attempt['failure_count']} | "
            f"{attempt['missing_count']} | `{attempt['batch_id']}` | {top_errors} |"
        )
    (base_run._run_dir(final_run_id) / RETRY_AUDIT_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _recover_stage1(
    *,
    paper_id: str,
    model: str,
    reasoning_effort: str,
    initial_run_id: str,
    retry_prefix: str,
) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]], list[str]]:
    cutoff_keys = _cutoff_pass_keys(paper_id)
    stage1_attempts = [_collect_attempt_metadata(initial_run_id, "stage1_review", model, request_count=len(cutoff_keys))]
    if stage1_attempts[0]["failure_count"] and not _all_errors_retryable(_error_rows(initial_run_id, "stage1_review", model)):
        raise RuntimeError(f"non-retryable stage1 error in {initial_run_id}")

    merged_rows, source_map = merge_stage_rows([(initial_run_id, _phase_rows(initial_run_id, paper_id, "stage1_review"))])
    retry_index = 1
    remaining = _remaining_keys(cutoff_keys, source_map)

    while remaining:
        retry_run_id = _retry_run_id(retry_prefix, "stage1_review", retry_index)
        print(f"[stage1] retry={retry_index} remaining={len(remaining)} run_id={retry_run_id}", flush=True)
        _ensure_phase_attempt(
            phase="stage1_review",
            run_id=retry_run_id,
            paper_id=paper_id,
            model=model,
            reasoning_effort=reasoning_effort,
            candidate_keys=remaining,
        )
        stage1_attempts.append(_collect_attempt_metadata(retry_run_id, "stage1_review", model, request_count=len(remaining)))
        if stage1_attempts[-1]["failure_count"] and not _all_errors_retryable(_error_rows(retry_run_id, "stage1_review", model)):
            raise RuntimeError(f"non-retryable stage1 error in {retry_run_id}")
        merged_rows, source_map = merge_stage_rows(
            [(attempt["run_id"], _phase_rows(attempt["run_id"], paper_id, "stage1_review")) for attempt in stage1_attempts]
        )
        remaining = _remaining_keys(cutoff_keys, source_map)
        retry_index += 1

    return merged_rows, source_map, stage1_attempts, cutoff_keys


def _recover_stage2(
    *,
    paper_id: str,
    model: str,
    reasoning_effort: str,
    final_run_id: str,
    merged_stage1_rows: list[dict[str, Any]],
    retry_prefix: str,
) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]], list[str]]:
    _seed_phase_rows(final_run_id, paper_id, "stage1_review", merged_stage1_rows)
    selected_keys = _compute_stage2_selected_keys(final_run_id, paper_id, model, reasoning_effort)
    if not selected_keys:
        return [], {}, [], []

    stage2_attempts: list[dict[str, Any]] = []
    merged_rows: list[dict[str, Any]] = []
    source_map: dict[str, str] = {}
    retry_index = 1
    remaining = list(selected_keys)

    while remaining:
        retry_run_id = _retry_run_id(retry_prefix, "stage2_review", retry_index)
        print(f"[stage2] retry={retry_index} remaining={len(remaining)} run_id={retry_run_id}", flush=True)
        _ensure_phase_attempt(
            phase="stage2_review",
            run_id=retry_run_id,
            paper_id=paper_id,
            model=model,
            reasoning_effort=reasoning_effort,
            candidate_keys=remaining,
            stage1_seed_rows=merged_stage1_rows,
        )
        stage2_attempts.append(_collect_attempt_metadata(retry_run_id, "stage2_review", model, request_count=len(remaining)))
        if stage2_attempts[-1]["failure_count"] and not _all_errors_retryable(_error_rows(retry_run_id, "stage2_review", model)):
            raise RuntimeError(f"non-retryable stage2 error in {retry_run_id}")
        merged_rows, source_map = merge_stage_rows(
            [(attempt["run_id"], _phase_rows(attempt["run_id"], paper_id, "stage2_review")) for attempt in stage2_attempts]
        )
        remaining = _remaining_keys(selected_keys, source_map)
        retry_index += 1

    return merged_rows, source_map, stage2_attempts, selected_keys


def _finalize_consolidated_run(
    *,
    paper_id: str,
    model: str,
    reasoning_effort: str,
    final_run_id: str,
    merged_stage1_rows: list[dict[str, Any]],
    stage1_source_map: dict[str, str],
    stage1_attempts: list[dict[str, Any]],
    cutoff_keys: list[str],
    merged_stage2_rows: list[dict[str, Any]],
    stage2_source_map: dict[str, str],
    stage2_attempts: list[dict[str, Any]],
    stage2_selected_keys: list[str],
) -> Path:
    manifest = _init_final_run_manifest(final_run_id, model, reasoning_effort, paper_id)
    _seed_phase_rows(final_run_id, paper_id, "stage1_review", merged_stage1_rows)
    _seed_source_map(final_run_id, STAGE1_SOURCE_MAP_NAME, stage1_source_map)
    if stage2_selected_keys:
        _seed_phase_rows(final_run_id, paper_id, "stage2_review", merged_stage2_rows)
        _seed_source_map(final_run_id, STAGE2_SOURCE_MAP_NAME, stage2_source_map)
        selection_path = base_run._paper_stage2_selection_keys_path(final_run_id, paper_id)
        selection_path.parent.mkdir(parents=True, exist_ok=True)
        selection_path.write_text("\n".join(stage2_selected_keys) + "\n", encoding="utf-8")

    manifest["phase_jobs"]["stage1_review"] = _build_consolidated_phase_job(
        phase="stage1_review",
        final_run_id=final_run_id,
        model=model,
        request_count=len(cutoff_keys),
        paper_preparation={
            paper_id: {
                "candidate_total": 84,
                "cutoff_pass_count": len(cutoff_keys),
                "cutoff_excluded_count": 84 - len(cutoff_keys),
                "request_count": len(cutoff_keys),
            }
        },
        source_attempt_run_ids=[attempt["run_id"] for attempt in stage1_attempts],
    )
    manifest["phase_jobs"]["stage2_review"] = _build_consolidated_phase_job(
        phase="stage2_review",
        final_run_id=final_run_id,
        model=model,
        request_count=len(stage2_selected_keys),
        paper_preparation={
            paper_id: {
                "selected_for_stage2_count": len(stage2_selected_keys),
                "request_count": len(stage2_selected_keys),
            }
        },
        source_attempt_run_ids=[attempt["run_id"] for attempt in stage2_attempts],
    )
    manifest["mode"] = "collect"
    base_run.write_json(base_run._run_manifest_path(final_run_id), manifest)

    config = _load_config_for_model(model)
    base_run._assemble_results_and_metrics(
        run_id=final_run_id,
        config=config,
        selected_papers=[paper_id],
        key_map=None,
        max_records=None,
        report_reasoning_effort=reasoning_effort,
    )

    attempts = [*stage1_attempts, *stage2_attempts]
    _write_token_cost_summary(final_run_id=final_run_id, model=model, reasoning_effort=reasoning_effort, attempts=attempts)
    _write_retry_audit(final_run_id=final_run_id, attempts=attempts)
    return base_run._run_dir(final_run_id)


def run_full_success_two_stage(
    *,
    paper_id: str,
    model: str,
    reasoning_effort: str,
    initial_stage1_run_id: str,
    final_run_id: str,
    retry_prefix: str,
) -> Path:
    if model not in MODEL_BATCH_PRICING:
        raise SystemExit(f"unsupported model for cost summary: {model}")

    merged_stage1_rows, stage1_source_map, stage1_attempts, cutoff_keys = _recover_stage1(
        paper_id=paper_id,
        model=model,
        reasoning_effort=reasoning_effort,
        initial_run_id=initial_stage1_run_id,
        retry_prefix=retry_prefix,
    )
    merged_stage2_rows, stage2_source_map, stage2_attempts, stage2_selected_keys = _recover_stage2(
        paper_id=paper_id,
        model=model,
        reasoning_effort=reasoning_effort,
        final_run_id=final_run_id,
        merged_stage1_rows=merged_stage1_rows,
        retry_prefix=retry_prefix,
    )
    return _finalize_consolidated_run(
        paper_id=paper_id,
        model=model,
        reasoning_effort=reasoning_effort,
        final_run_id=final_run_id,
        merged_stage1_rows=merged_stage1_rows,
        stage1_source_map=stage1_source_map,
        stage1_attempts=stage1_attempts,
        cutoff_keys=cutoff_keys,
        merged_stage2_rows=merged_stage2_rows,
        stage2_source_map=stage2_source_map,
        stage2_attempts=stage2_attempts,
        stage2_selected_keys=stage2_selected_keys,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover single-reviewer two-stage run to full success for one paper.")
    parser.add_argument("--paper-id", default="2409.13738")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--reasoning-effort", default="xhigh")
    parser.add_argument("--initial-stage1-run-id", default="20260409_probe_2409_gpt54_xhigh_stage1")
    parser.add_argument("--final-run-id", default="20260410_full_gpt54_xhigh_2stagedirect_2409_consolidated")
    parser.add_argument("--retry-prefix", default="20260410_retry")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    final_run_dir = run_full_success_two_stage(
        paper_id=args.paper_id,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        initial_stage1_run_id=args.initial_stage1_run_id,
        final_run_id=args.final_run_id,
        retry_prefix=args.retry_prefix,
    )
    print(f"[final] {final_run_dir}", flush=True)
    print(f"[report] {final_run_dir / 'REPORT_zh.md'}", flush=True)
    print(f"[cost] {final_run_dir / TOKEN_COST_SUMMARY_NAME}", flush=True)
    print(f"[audit] {final_run_dir / RETRY_AUDIT_NAME}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
