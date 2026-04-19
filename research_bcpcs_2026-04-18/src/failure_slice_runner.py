#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from failure_slice_common import (
    DEFAULT_COST_CAP_USD,
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    REPO_ROOT,
    batch_dir,
    cost_dir,
    ensure_dir,
    estimate_batch_cost,
    estimate_text_tokens,
    load_dotenv_if_present,
    paper_dir,
    pricing_snapshot_payload,
    read_json,
    read_jsonl,
    repo_rel,
    request_rows_token_estimate,
    run_dir,
    safe_text,
    sha256_file,
    usage_from_batch_output_row,
    utc_now_iso,
    write_json,
    write_jsonl,
)
from failure_slice_eval import evaluate_results
from failure_slice_inventory import freeze_inventory_files
from failure_slice_models import StageReviewOutput, validate_stage_output
from failure_slice_prompts import build_stage1_prompt, build_stage2_prompt
from failure_slice_reports import write_execution_charter, write_leakage_audit, write_results_report
from failure_slice_validate import find_forbidden_prompt_terms, validate_run_artifacts

from scripts.screening import cutoff_time_filter
from scripts.screening.experiment_workflows import (
    build_fulltext_resolution_audit,
    fulltext_payload_from_resolution,
    load_artifact_gate_result,
    load_candidates,
    load_cutoff_result,
    metadata_payload,
)
from scripts.screening.openai_batch_runner import (
    BatchRequestSpec,
    OpenAIBatchRunner,
    build_json_schema_response_format,
)


PRIMARY_RUN_ID = "bcpcs_failure_slice_gpt5nano_2stage_async_2026-04-18_primary22_v1"
FULL_RUN_ID = "bcpcs_failure_slice_gpt5nano_2stage_async_2026-04-18_full127_v1"
PHASES = ("stage1_review", "stage2_review")
ADVANCE_TO_STAGE2 = {"include", "maybe", "route_to_stage2", "unknown"}
MAX_COMPLETION_TOKENS = 32768


def _metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _full_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_full_metadata.jsonl"


def _criteria_path(paper_id: str, stage: Literal["stage1", "stage2"]) -> Path:
    return REPO_ROOT / f"criteria_{stage}" / f"{paper_id}.json"


def _cutoff_path(paper_id: str) -> Path:
    return REPO_ROOT / "cutoff_jsons" / f"{paper_id}.json"


def _fulltext_root(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "mds"


def _load_jsonl_any(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _load_records_for_paper(paper_id: str, key_allowlist: set[str]) -> list[dict[str, Any]]:
    records = load_candidates(_metadata_path(paper_id), key_allowlist=key_allowlist)
    if paper_id != "2307.05527":
        return records
    full_rows_by_key = {
        safe_text(row.get("key")): row
        for row in _load_jsonl_any(_full_metadata_path(paper_id))
        if safe_text(row.get("key"))
    }
    merged: list[dict[str, Any]] = []
    for record in records:
        key = safe_text(record.get("key"))
        out = dict(record)
        full_row = full_rows_by_key.get(key)
        if full_row:
            for field in ("comment", "journal_ref", "doi", "source", "source_id", "source_metadata"):
                value = full_row.get(field)
                if value not in (None, ""):
                    out[field] = value
        merged.append(out)
    return merged


def _load_cutoff_for_paper(paper_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    if paper_id != "2307.05527":
        return load_cutoff_result(records=records, cutoff_path=_cutoff_path(paper_id))
    payload, policy = cutoff_time_filter.load_time_policy(_cutoff_path(paper_id))
    payload = dict(payload)
    payload["_cutoff_json_path"] = repo_rel(_cutoff_path(paper_id))
    payload["time_policy"] = dict(payload.get("time_policy") or {})
    payload["time_policy"]["preprint_split_submitted_date"] = True
    return cutoff_time_filter.apply_cutoff(
        records,
        payload=payload,
        policy=replace(policy, preprint_split_submitted_date=True),
    )


def _default_run_id(scope: str) -> str:
    return PRIMARY_RUN_ID if scope == "primary22" else FULL_RUN_ID


def _cases_by_paper(run_path: Path) -> dict[str, list[str]]:
    payload = read_json(run_path / "failure_slice_keys.json")
    out: dict[str, list[str]] = defaultdict(list)
    for row in payload["cases"]:
        out[row["paper_id"]].append(row["candidate_key"])
    return {paper_id: sorted(keys) for paper_id, keys in sorted(out.items())}


def _load_run_manifest(run_path: Path) -> dict[str, Any]:
    return read_json(run_path / "run_manifest.json")


def _write_run_manifest(run_path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = utc_now_iso()
    write_json(run_path / "run_manifest.json", manifest)


def init_run(*, run_id: str, scope: Literal["primary22", "full127"], reasoning_effort: str, cost_cap_usd: float) -> dict[str, Any]:
    rd = ensure_dir(run_dir(run_id))
    ensure_dir(cost_dir(run_id))
    ensure_dir(rd / "batch_jobs")
    ensure_dir(rd / "papers")
    ensure_dir(rd / "logs")
    slice_payload = freeze_inventory_files(run_dir=rd, scope=scope)
    pricing = pricing_snapshot_payload()
    write_json(cost_dir(run_id) / "pricing_snapshot.json", pricing)
    manifest = {
        "run_id": run_id,
        "experiment_name": "bcpcs_failure_slice_gpt5nano_2stage_async",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "scope": scope,
        "model": DEFAULT_MODEL,
        "endpoint": DEFAULT_ENDPOINT,
        "reviewer": "single_reviewer",
        "workflow": "two_stage_async_batch",
        "reasoning_effort_requested": reasoning_effort,
        "reasoning_effort_effective": reasoning_effort,
        "reasoning_effort_fallback": None,
        "cost_cap_usd": cost_cap_usd,
        "status": "initialized",
        "run_dir": repo_rel(rd),
        "failure_slice_keys_path": repo_rel(rd / "failure_slice_keys.json"),
        "evaluation_inventory_private_path": repo_rel(rd / "evaluation_inventory_private.json"),
        "pricing_snapshot_path": repo_rel(cost_dir(run_id) / "pricing_snapshot.json"),
        "source_counts": slice_payload["summary"],
        "phase_jobs": {},
        "is_failure_slice_diagnostic": True,
        "not_full_benchmark_evidence": True,
        "write_scope": "research_bcpcs_2026-04-18 only",
    }
    _write_run_manifest(rd, manifest)
    write_execution_charter(run_id=run_id, run_dir=rd)
    return manifest


def _build_body(*, model: str, prompt: str, reasoning_effort: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(StageReviewOutput, schema_name="BCPCSStageReviewOutput"),
        "reasoning_effort": reasoning_effort,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
    }


def _build_validator(stage: str, candidate_key: str) -> Any:
    def _validate(payload: StageReviewOutput) -> None:
        validate_stage_output(payload, stage=stage, candidate_key=candidate_key)

    return _validate


def _write_static_audits(
    *,
    run_path: Path,
    paper_id: str,
    records: list[dict[str, Any]],
    cutoff_result: dict[str, Any],
    artifact_result: dict[str, Any],
    resolution_audit: dict[str, Any],
) -> None:
    pd = ensure_dir(paper_dir(run_path.name, paper_id))
    write_json(pd / "cutoff_audit.json", cutoff_result["audit_payload"])
    artifact_audit = dict(artifact_result["audit_payload"])
    artifact_audit["paper_id"] = paper_id
    write_json(pd / "artifact_gate_audit.json", artifact_audit)
    write_json(pd / "fulltext_resolution_audit.json", resolution_audit)
    write_json(
        pd / "source_records_loaded.json",
        [{"key": row.get("key"), "title": row.get("title") or row.get("query_title")} for row in records],
    )


def _prepare_common(run_path: Path) -> dict[str, Any]:
    cases_by_paper = _cases_by_paper(run_path)
    paper_data: dict[str, Any] = {}
    for paper_id, keys in cases_by_paper.items():
        records = _load_records_for_paper(paper_id, set(keys))
        record_by_key = {safe_text(row.get("key")): row for row in records}
        missing_keys = sorted(set(keys) - set(record_by_key))
        if missing_keys:
            raise RuntimeError(f"Missing metadata records for {paper_id}: {missing_keys}")
        cutoff_result = _load_cutoff_for_paper(paper_id, records)
        artifact_result = load_artifact_gate_result(records=records)
        resolution_by_key, resolution_audit = build_fulltext_resolution_audit(
            paper_id=paper_id,
            records=records,
            fulltext_root=_fulltext_root(paper_id),
            repo_root=REPO_ROOT,
        )
        _write_static_audits(
            run_path=run_path,
            paper_id=paper_id,
            records=records,
            cutoff_result=cutoff_result,
            artifact_result=artifact_result,
            resolution_audit=resolution_audit,
        )
        paper_data[paper_id] = {
            "keys": keys,
            "records": records,
            "record_by_key": record_by_key,
            "cutoff_result": cutoff_result,
            "artifact_result": artifact_result,
            "resolution_by_key": resolution_by_key,
            "resolution_audit": resolution_audit,
        }
    return paper_data


def prepare_stage1_specs(*, run_path: Path, reasoning_effort: str) -> list[BatchRequestSpec]:
    specs: list[BatchRequestSpec] = []
    paper_data = _prepare_common(run_path)
    for paper_id, data in paper_data.items():
        criteria_path = _criteria_path(paper_id, "stage1")
        criteria = read_json(criteria_path)
        metadata_path = _metadata_path(paper_id)
        for record in data["records"]:
            key = safe_text(record.get("key"))
            cutoff_decision = data["cutoff_result"]["decisions_by_key"][key]
            artifact_decision = data["artifact_result"]["decisions_by_key"][key]
            if not cutoff_decision["cutoff_pass"] or not artifact_decision["gate_pass"]:
                continue
            prompt = build_stage1_prompt(
                paper_id=paper_id,
                candidate_key=key,
                criteria=criteria,
                metadata=metadata_payload(record),
                criteria_path=repo_rel(criteria_path),
                metadata_path=repo_rel(metadata_path),
            )
            specs.append(
                BatchRequestSpec(
                    custom_id=f"stage1_review__{paper_id}__{key}",
                    model=DEFAULT_MODEL,
                    body=_build_body(model=DEFAULT_MODEL, prompt=prompt, reasoning_effort=reasoning_effort),
                    response_model=StageReviewOutput,
                    validator=_build_validator("stage1", key),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                        "phase": "stage1_review",
                        "stage": "stage1",
                        "criteria_path": repo_rel(criteria_path),
                        "metadata_path": repo_rel(metadata_path),
                    },
                )
            )
    return specs


def _load_stage_records_by_key(run_path: Path, phase: str) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted((run_path / "papers").glob(f"*/{phase}.json")):
        paper_id = path.parent.name
        payload = read_json(path)
        if not isinstance(payload, list):
            continue
        for row in payload:
            key = safe_text(row.get("candidate_key"))
            if key:
                out[(paper_id, key)] = row
    return out


def prepare_stage2_specs(*, run_path: Path, reasoning_effort: str) -> list[BatchRequestSpec]:
    specs: list[BatchRequestSpec] = []
    stage1_by_key = _load_stage_records_by_key(run_path, "stage1_review")
    paper_data = _prepare_common(run_path)
    for paper_id, data in paper_data.items():
        criteria_path = _criteria_path(paper_id, "stage2")
        criteria = read_json(criteria_path)
        metadata_path = _metadata_path(paper_id)
        selected: list[str] = []
        for record in data["records"]:
            key = safe_text(record.get("key"))
            cutoff_decision = data["cutoff_result"]["decisions_by_key"][key]
            artifact_decision = data["artifact_result"]["decisions_by_key"][key]
            if not cutoff_decision["cutoff_pass"] or not artifact_decision["gate_pass"]:
                continue
            stage1_record = stage1_by_key.get((paper_id, key))
            if not stage1_record:
                continue
            stage1_output = stage1_record["review_output"]
            if safe_text(stage1_output.get("final_stage_decision")) not in ADVANCE_TO_STAGE2:
                continue
            resolution = data["resolution_by_key"][key]
            if resolution["resolution_status"] not in {"exact", "normalized"} or not resolution.get("fulltext_gate_pass", True):
                continue
            selected.append(key)
            fulltext_text, fulltext_meta = fulltext_payload_from_resolution(
                resolution,
                repo_root=REPO_ROOT,
                head_chars=90_000,
                tail_chars=30_000,
            )
            prompt = build_stage2_prompt(
                paper_id=paper_id,
                candidate_key=key,
                criteria=criteria,
                metadata=metadata_payload(record),
                fulltext_text=fulltext_text,
                fulltext_meta=fulltext_meta,
                stage1_handoff=stage1_output,
                criteria_path=repo_rel(criteria_path),
                metadata_path=repo_rel(metadata_path),
            )
            specs.append(
                BatchRequestSpec(
                    custom_id=f"stage2_review__{paper_id}__{key}",
                    model=DEFAULT_MODEL,
                    body=_build_body(model=DEFAULT_MODEL, prompt=prompt, reasoning_effort=reasoning_effort),
                    response_model=StageReviewOutput,
                    validator=_build_validator("stage2", key),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                        "phase": "stage2_review",
                        "stage": "stage2",
                        "criteria_path": repo_rel(criteria_path),
                        "metadata_path": repo_rel(metadata_path),
                        "fulltext_resolution": resolution,
                    },
                )
            )
        selection_path = paper_dir(run_path.name, paper_id) / "selected_for_stage2.keys.txt"
        selection_path.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")
    return specs


def prepare_specs(*, run_path: Path, phase: str, reasoning_effort: str) -> list[BatchRequestSpec]:
    if phase == "stage1_review":
        return prepare_stage1_specs(run_path=run_path, reasoning_effort=reasoning_effort)
    if phase == "stage2_review":
        return prepare_stage2_specs(run_path=run_path, reasoning_effort=reasoning_effort)
    raise ValueError(f"Unsupported phase: {phase}")


def _serialize_requests(specs: list[BatchRequestSpec]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in specs:
        rows.append({"custom_id": spec.custom_id, "method": "POST", "url": DEFAULT_ENDPOINT, "body": spec.body})
    return rows


def _current_cost_total(run_path: Path) -> float:
    summary = run_path / "cost" / "cost_summary.json"
    if not summary.exists():
        return 0.0
    payload = read_json(summary)
    return float(payload.get("total_cost_usd") or 0.0)


def _write_pre_submit_estimate(
    *,
    run_path: Path,
    phase: str,
    rows: list[dict[str, Any]],
    cost_cap_usd: float,
) -> dict[str, Any]:
    input_tokens = request_rows_token_estimate(rows)
    output_tokens = len(rows) * MAX_COMPLETION_TOKENS
    estimated_cost = estimate_batch_cost(input_tokens=input_tokens, output_tokens=output_tokens)
    prior = _current_cost_total(run_path)
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
        "estimate_policy": "input tokenizer_or_char_overestimate; output max_completion_tokens per request",
    }
    write_json(run_path / "cost" / f"pre_submit_estimate.{phase}.json", payload)
    return payload


def _prompt_leakage_check(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in rows:
        text = json.dumps(row.get("body", {}), ensure_ascii=False)
        terms = find_forbidden_prompt_terms(text)
        if terms:
            hits.append({"custom_id": row.get("custom_id"), "terms": terms})
    return hits


def submit_phase(
    *,
    run_id: str,
    phase: str,
    reasoning_effort: str,
    cost_cap_usd: float,
    dry_run: bool = False,
) -> dict[str, Any]:
    rd = run_dir(run_id)
    manifest = _load_run_manifest(rd)
    requested_effort = safe_text(manifest.get("reasoning_effort_requested")) or reasoning_effort
    manifest["reasoning_effort_effective"] = reasoning_effort
    if reasoning_effort != requested_effort:
        manifest["reasoning_effort_fallback"] = {
            "from": requested_effort,
            "to": reasoning_effort,
            "reason": "gpt-5-nano Batch API reported xhigh unsupported; highest listed supported value was high.",
            "recorded_at": utc_now_iso(),
        }
    specs = prepare_specs(run_path=rd, phase=phase, reasoning_effort=reasoning_effort)
    artifact_dir = ensure_dir(batch_dir(run_id, phase, DEFAULT_MODEL))
    rows = _serialize_requests(specs)
    write_jsonl(artifact_dir / "input.jsonl", rows)
    estimate = _write_pre_submit_estimate(run_path=rd, phase=phase, rows=rows, cost_cap_usd=cost_cap_usd)
    prompt_hits = _prompt_leakage_check(rows)
    if prompt_hits:
        stop_payload = {
            "created_at": utc_now_iso(),
            "phase": phase,
            "reason": "forbidden_prompt_terms",
            "hits": prompt_hits,
        }
        write_json(artifact_dir / "leakage_stop.json", stop_payload)
        raise RuntimeError(f"Forbidden prompt fields detected for {phase}: {prompt_hits[:3]}")
    if estimate["would_exceed_cost_cap"]:
        stop_payload = {
            "created_at": utc_now_iso(),
            "phase": phase,
            "reason": "cost_cap_projected_exceeded",
            "estimate": estimate,
        }
        write_json(run_dir(run_id) / "cost" / "cost_stop.json", stop_payload)
        manifest["status"] = "paused_cost_cap_before_submit"
        manifest["phase_jobs"].setdefault(phase, {}).update(stop_payload)
        _write_run_manifest(rd, manifest)
        return stop_payload
    if dry_run:
        parsed_payload = {
            "batch_id": None,
            "batch_status": "dry_run_not_submitted",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
        write_json(artifact_dir / "parsed_results.json", parsed_payload)
        manifest["phase_jobs"][phase] = {
            "phase": phase,
            "batch_artifact_dir": repo_rel(artifact_dir),
            "batch_id": None,
            "batch_status": "dry_run_not_submitted",
            "request_count": len(specs),
            "pre_submit_estimate": estimate,
        }
        manifest["status"] = f"dry_run_{phase}"
        _write_run_manifest(rd, manifest)
        return manifest["phase_jobs"][phase]
    if not specs:
        parsed_payload = {
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
        write_json(artifact_dir / "parsed_results.json", parsed_payload)
        manifest["phase_jobs"][phase] = {
            "phase": phase,
            "batch_artifact_dir": repo_rel(artifact_dir),
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "request_count": 0,
            "pre_submit_estimate": estimate,
        }
        _write_run_manifest(rd, manifest)
        return manifest["phase_jobs"][phase]
    load_dotenv_if_present()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; cannot submit Batch job.")
    from openai import OpenAI

    client = OpenAI()
    model_preflight = client.models.retrieve(DEFAULT_MODEL)
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=30.0)
    submit_payload = runner.submit_requests(
        specs=specs,
        endpoint=DEFAULT_ENDPOINT,
        artifact_dir=artifact_dir,
        metadata={
            "experiment": "bcpcs_failure_slice",
            "run_id": run_id,
            "phase": phase,
            "model": DEFAULT_MODEL,
        },
    )
    manifest["model_preflight_id"] = getattr(model_preflight, "id", DEFAULT_MODEL)
    manifest["phase_jobs"][phase] = {
        "phase": phase,
        "batch_artifact_dir": repo_rel(artifact_dir),
        "batch_id": submit_payload["batch_create"]["id"],
        "batch_status": submit_payload["batch_create"]["status"],
        "request_count": len(specs),
        "pre_submit_estimate": estimate,
        "upload_file_id": submit_payload["upload_file"]["id"],
    }
    manifest["status"] = f"submitted_{phase}"
    _write_run_manifest(rd, manifest)
    return manifest["phase_jobs"][phase]


def _load_batch_payload(artifact_dir: Path) -> dict[str, Any] | None:
    for name in ("batch_latest.json", "batch_create.json"):
        path = artifact_dir / name
        if path.exists():
            return read_json(path)
    return None


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


def _assistant_content_from_output_row(row: dict[str, Any]) -> str:
    response = row.get("response")
    if not isinstance(response, dict):
        raise ValueError("output row missing response")
    body = response.get("body")
    if not isinstance(body, dict):
        raise ValueError("output row missing response.body")
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response.body missing choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("choice missing message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    raise ValueError("message.content is not a string")


def _normalized_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _repair_candidate_key_if_safe(payload: dict[str, Any], expected_key: str) -> dict[str, Any]:
    observed = safe_text(payload.get("candidate_key"))
    if observed == expected_key:
        return payload
    if _normalized_key(observed) != _normalized_key(expected_key):
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


def reparse_phase(
    *,
    run_id: str,
    phase: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    rd = run_dir(run_id)
    specs = prepare_specs(run_path=rd, phase=phase, reasoning_effort=reasoning_effort)
    artifact_dir = batch_dir(run_id, phase, DEFAULT_MODEL)
    output_rows = read_jsonl(artifact_dir / "output.jsonl") if (artifact_dir / "output.jsonl").exists() else []
    error_rows = read_jsonl(artifact_dir / "error.jsonl") if (artifact_dir / "error.jsonl").exists() else []
    output_by_id = {str(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
    error_by_id = {str(row.get("custom_id")): row for row in error_rows if row.get("custom_id")}
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for spec in specs:
        if spec.custom_id in error_by_id:
            failures.append(
                {
                    "custom_id": spec.custom_id,
                    "status": "error_file",
                    "context": spec.context,
                    "error": error_by_id[spec.custom_id],
                }
            )
            continue
        row = output_by_id.get(spec.custom_id)
        if row is None:
            missing.append({"custom_id": spec.custom_id, "status": "missing", "context": spec.context})
            continue
        try:
            response = row.get("response")
            if not isinstance(response, dict) or int(response.get("status_code") or 0) != 200:
                raise ValueError(f"status_code={response.get('status_code') if isinstance(response, dict) else None}")
            assistant_text = _assistant_content_from_output_row(row)
            raw_payload = json.loads(_strip_json_fence(assistant_text))
            if isinstance(raw_payload, dict):
                raw_payload = _repair_candidate_key_if_safe(raw_payload, str(spec.context.get("candidate_key") or ""))
            parsed = spec.response_model.model_validate(raw_payload)
            if spec.validator is not None:
                spec.validator(parsed)
            successes.append(
                {
                    "custom_id": spec.custom_id,
                    "status": "ok",
                    "context": spec.context,
                    "assistant_text": assistant_text,
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
                    "raw_output": row,
                }
            )
    batch_payload = _load_batch_payload(artifact_dir) or {}
    parsed_payload = {
        "batch_id": batch_payload.get("id"),
        "batch_status": batch_payload.get("status"),
        "successes": successes,
        "failures": failures,
        "missing": missing,
        "output_row_count": len(output_rows),
        "error_row_count": len(error_rows),
        "reparse_only": True,
        "reparse_at": utc_now_iso(),
    }
    write_json(artifact_dir / "parsed_results.json", parsed_payload)
    _write_phase_review_outputs(run_id=run_id, phase=phase, parsed_payload=parsed_payload)
    manifest = _load_run_manifest(rd)
    manifest["phase_jobs"].setdefault(phase, {}).update(
        {
            "parsed_summary": {
                "success_count": len(successes),
                "failure_count": len(failures),
                "missing_count": len(missing),
            },
            "reparse_only": True,
        }
    )
    _write_run_manifest(rd, manifest)
    return parsed_payload


def _write_phase_review_outputs(*, run_id: str, phase: str, parsed_payload: dict[str, Any]) -> None:
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in parsed_payload.get("successes", []):
        context = item["context"]
        parsed = item["parsed"]
        rows_by_paper[context["paper_id"]].append(
            {
                "paper_id": context["paper_id"],
                "candidate_key": context["candidate_key"],
                "candidate_title": context["candidate_title"],
                "phase": phase,
                "stage": context["stage"],
                "model": DEFAULT_MODEL,
                "criteria_path": context["criteria_path"],
                "metadata_path": context["metadata_path"],
                "review_output": parsed,
            }
        )
    for paper_id, rows in rows_by_paper.items():
        rows.sort(key=lambda row: row["candidate_key"])
        write_json(paper_dir(run_id, paper_id) / f"{phase}.json", rows)
    for paper_id in _cases_by_paper(run_dir(run_id)):
        path = paper_dir(run_id, paper_id) / f"{phase}.json"
        if not path.exists():
            write_json(path, [])


def _update_cost_from_output(
    *,
    run_id: str,
    phase: str,
    artifact_dir: Path,
    specs: list[BatchRequestSpec],
    parsed_payload: dict[str, Any],
) -> dict[str, Any]:
    spec_by_id = {spec.custom_id: spec for spec in specs}
    output_path = artifact_dir / "output.jsonl"
    output_rows = read_jsonl(output_path) if output_path.exists() else []
    output_by_id = {str(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
    prior_summary_path = cost_dir(run_id) / "cost_summary.json"
    prior = read_json(prior_summary_path) if prior_summary_path.exists() else {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost_usd": 0.0,
        "phases": {},
    }
    phase_input = 0
    phase_output = 0
    phase_cost = 0.0
    estimated_count = 0
    actual_count = 0
    success_by_id = {row["custom_id"]: row for row in parsed_payload.get("successes", [])}
    for custom_id, spec in spec_by_id.items():
        usage = usage_from_batch_output_row(output_by_id.get(custom_id, {}))
        assistant_text = safe_text(success_by_id.get(custom_id, {}).get("assistant_text"))
        if usage and "input_tokens" in usage and "output_tokens" in usage:
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
            source = "batch_usage"
            actual_count += 1
        else:
            input_tokens = estimate_text_tokens(json.dumps(spec.body, ensure_ascii=False))
            output_tokens = estimate_text_tokens(assistant_text) if assistant_text else MAX_COMPLETION_TOKENS
            source = "estimated"
            estimated_count += 1
        cost = estimate_batch_cost(input_tokens=input_tokens, output_tokens=output_tokens)
        phase_input += input_tokens
        phase_output += output_tokens
        phase_cost += cost
        from failure_slice_common import append_jsonl

        append_jsonl(
            cost_dir(run_id) / "cost_ledger.jsonl",
            {
                "created_at": utc_now_iso(),
                "phase": phase,
                "custom_id": custom_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "cost_source": source,
            },
        )
    summary = {
        "created_at": utc_now_iso(),
        "cost_source": "mixed_batch_usage_and_estimated" if estimated_count and actual_count else (
            "batch_usage" if actual_count else "estimated"
        ),
        "input_tokens": int(prior.get("input_tokens", 0)) + phase_input,
        "output_tokens": int(prior.get("output_tokens", 0)) + phase_output,
        "total_cost_usd": float(prior.get("total_cost_usd", 0.0)) + phase_cost,
        "phases": {
            **dict(prior.get("phases") or {}),
            phase: {
                "input_tokens": phase_input,
                "output_tokens": phase_output,
                "total_cost_usd": phase_cost,
                "actual_usage_rows": actual_count,
                "estimated_rows": estimated_count,
            },
        },
    }
    write_json(cost_dir(run_id) / "cost_summary.json", summary)
    return summary


def collect_phase(
    *,
    run_id: str,
    phase: str,
    reasoning_effort: str,
    poll_interval_sec: float,
    max_wait_minutes: float,
) -> dict[str, Any]:
    rd = run_dir(run_id)
    manifest = _load_run_manifest(rd)
    specs = prepare_specs(run_path=rd, phase=phase, reasoning_effort=reasoning_effort)
    artifact_dir = batch_dir(run_id, phase, DEFAULT_MODEL)
    batch_payload = _load_batch_payload(artifact_dir)
    if batch_payload is None or not batch_payload.get("id"):
        parsed_path = artifact_dir / "parsed_results.json"
        parsed_payload = read_json(parsed_path) if parsed_path.exists() else {
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
        batch_payload = runner.wait_until_terminal(
            str(batch_payload["id"]),
            artifact_dir=artifact_dir,
            max_wait_minutes=max_wait_minutes,
        )
        parsed_payload = runner.collect_results(specs=specs, batch_payload=batch_payload, artifact_dir=artifact_dir)
        manifest["phase_jobs"].setdefault(phase, {}).update(
            {
                "batch_status": batch_payload.get("status"),
                "batch_completed_at": batch_payload.get("completed_at"),
                "batch_output_file_id": batch_payload.get("output_file_id"),
                "batch_error_file_id": batch_payload.get("error_file_id"),
            }
        )
    _write_phase_review_outputs(run_id=run_id, phase=phase, parsed_payload=parsed_payload)
    cost_summary = _update_cost_from_output(
        run_id=run_id,
        phase=phase,
        artifact_dir=artifact_dir,
        specs=specs,
        parsed_payload=parsed_payload,
    )
    manifest["phase_jobs"].setdefault(phase, {}).update(
        {
            "parsed_summary": {
                "success_count": len(parsed_payload.get("successes", [])),
                "failure_count": len(parsed_payload.get("failures", [])),
                "missing_count": len(parsed_payload.get("missing", [])),
            },
            "cost_summary": cost_summary["phases"].get(phase),
        }
    )
    manifest["status"] = f"collected_{phase}"
    _write_run_manifest(rd, manifest)
    return parsed_payload


def assemble_results(*, run_id: str) -> list[dict[str, Any]]:
    rd = run_dir(run_id)
    cases = read_json(rd / "failure_slice_keys.json")["cases"]
    paper_data = _prepare_common(rd)
    stage1_by_key = _load_stage_records_by_key(rd, "stage1_review")
    stage2_by_key = _load_stage_records_by_key(rd, "stage2_review")
    rows: list[dict[str, Any]] = []
    for case in cases:
        paper_id = case["paper_id"]
        key = case["candidate_key"]
        data = paper_data[paper_id]
        record = data["record_by_key"][key]
        title = safe_text(record.get("title") or record.get("query_title"))
        cutoff_decision = data["cutoff_result"]["decisions_by_key"][key]
        artifact_decision = data["artifact_result"]["decisions_by_key"][key]
        resolution = data["resolution_by_key"][key]
        stage1 = stage1_by_key.get((paper_id, key))
        stage2 = stage2_by_key.get((paper_id, key))
        review_state = "reviewed"
        discard_reason = None
        final_stage = "stage1"
        final_decision = "unknown"
        if not cutoff_decision["cutoff_pass"]:
            review_state = "cutoff_filtered"
            discard_reason = "cutoff_time_window"
            final_decision = "exclude"
        elif not artifact_decision["gate_pass"]:
            review_state = "artifact_filtered"
            discard_reason = f"artifact_gate:{artifact_decision.get('gate_reason')}"
            final_decision = "exclude"
        elif stage2:
            final_stage = "stage2"
            final_decision = safe_text(stage2["review_output"].get("final_stage_decision")) or "unknown"
        elif stage1:
            stage1_decision = safe_text(stage1["review_output"].get("final_stage_decision")) or "unknown"
            if stage1_decision == "exclude":
                final_decision = "exclude"
            elif resolution["resolution_status"] not in {"exact", "normalized"}:
                review_state = "fulltext_unresolved"
                discard_reason = resolution["resolution_status"]
                final_decision = "unknown"
            else:
                review_state = "stage2_not_available"
                final_decision = "unknown"
        else:
            review_state = "stage1_not_available"
            final_decision = "unknown"
        rows.append(
            {
                "paper_id": paper_id,
                "candidate_key": key,
                "candidate_title": title,
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
            }
        )
    rows.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    write_json(rd / "assembled_results.json", rows)
    for paper_id in sorted({row["paper_id"] for row in rows}):
        paper_rows = [row for row in rows if row["paper_id"] == paper_id]
        write_json(paper_dir(run_id, paper_id) / "single_reviewer_batch_results.json", paper_rows)
    return rows


def evaluate_and_report(*, run_id: str) -> dict[str, Any]:
    rd = run_dir(run_id)
    assemble_results(run_id=run_id)
    evaluation = evaluate_results(run_dir=rd)
    cost_summary_path = cost_dir(run_id) / "cost_summary.json"
    cost_summary = read_json(cost_summary_path) if cost_summary_path.exists() else None
    validation = validate_run_artifacts(rd)
    write_results_report(run_id=run_id, run_dir=rd, evaluation=evaluation, cost_summary=cost_summary)
    write_leakage_audit(run_id=run_id, run_dir=rd, validation=validation)
    manifest = _load_run_manifest(rd)
    manifest["status"] = "reported"
    manifest["evaluation_summary_path"] = repo_rel(rd / "evaluation_summary.json")
    manifest["validation_summary_path"] = repo_rel(rd / "validation_summary.json")
    manifest["cost_summary_path"] = repo_rel(cost_summary_path) if cost_summary_path.exists() else None
    _write_run_manifest(rd, manifest)
    return {"evaluation": evaluation, "validation": validation, "cost_summary": cost_summary}


def dry_run_loader_validation(*, run_id: str, reasoning_effort: str) -> dict[str, Any]:
    rd = run_dir(run_id)
    stage1_specs = prepare_stage1_specs(run_path=rd, reasoning_effort=reasoning_effort)
    rows = _serialize_requests(stage1_specs)
    write_jsonl(batch_dir(run_id, "stage1_review", DEFAULT_MODEL) / "input.jsonl", rows)
    prompt_hits = _prompt_leakage_check(rows)
    payload = {
        "stage1_request_count": len(stage1_specs),
        "stage1_prompt_forbidden_hit_count": len(prompt_hits),
        "stage1_input_sha256": sha256_file(batch_dir(run_id, "stage1_review", DEFAULT_MODEL) / "input.jsonl")
        if rows
        else None,
        "ok": len(stage1_specs) > 0 and not prompt_hits,
        "prompt_hits": prompt_hits,
    }
    write_json(rd / "dry_run_loader_validation.json", payload)
    return payload


def run_primary_flow(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or PRIMARY_RUN_ID
    init_run(run_id=run_id, scope="primary22", reasoning_effort=args.reasoning_effort, cost_cap_usd=args.cost_cap_usd)
    dry = dry_run_loader_validation(run_id=run_id, reasoning_effort=args.reasoning_effort)
    if not dry["ok"]:
        raise RuntimeError(f"Dry-run validation failed: {dry}")
    submit_phase(
        run_id=run_id,
        phase="stage1_review",
        reasoning_effort=args.reasoning_effort,
        cost_cap_usd=args.cost_cap_usd,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return {"run_id": run_id, "status": "dry_run_done"}
    collect_phase(
        run_id=run_id,
        phase="stage1_review",
        reasoning_effort=args.reasoning_effort,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
    )
    cost_summary = read_json(cost_dir(run_id) / "cost_summary.json")
    if float(cost_summary.get("total_cost_usd") or 0.0) > args.cost_cap_usd:
        result = evaluate_and_report(run_id=run_id)
        return {"run_id": run_id, "status": "paused_cost_cap_after_stage1", **result}
    submit_phase(
        run_id=run_id,
        phase="stage2_review",
        reasoning_effort=args.reasoning_effort,
        cost_cap_usd=args.cost_cap_usd,
        dry_run=False,
    )
    collect_phase(
        run_id=run_id,
        phase="stage2_review",
        reasoning_effort=args.reasoning_effort,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
    )
    return evaluate_and_report(run_id=run_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Isolated BCPCS failure-slice Batch wrapper.")
    parser.add_argument("--mode", choices=["init", "dry-run", "submit", "collect", "reparse", "assemble", "evaluate", "report", "validate", "run-primary"], required=True)
    parser.add_argument("--scope", choices=["primary22", "full127"], default="primary22")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--phase", choices=PHASES, default="stage1_review")
    parser.add_argument("--reasoning-effort", default="xhigh")
    parser.add_argument("--cost-cap-usd", type=float, default=DEFAULT_COST_CAP_USD)
    parser.add_argument("--poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--max-wait-minutes", type=float, default=24 * 60.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_id = args.run_id or _default_run_id(args.scope)
    if args.mode == "init":
        payload = init_run(
            run_id=run_id,
            scope=args.scope,
            reasoning_effort=args.reasoning_effort,
            cost_cap_usd=args.cost_cap_usd,
        )
    elif args.mode == "dry-run":
        payload = dry_run_loader_validation(run_id=run_id, reasoning_effort=args.reasoning_effort)
    elif args.mode == "submit":
        payload = submit_phase(
            run_id=run_id,
            phase=args.phase,
            reasoning_effort=args.reasoning_effort,
            cost_cap_usd=args.cost_cap_usd,
            dry_run=args.dry_run,
        )
    elif args.mode == "collect":
        payload = collect_phase(
            run_id=run_id,
            phase=args.phase,
            reasoning_effort=args.reasoning_effort,
            poll_interval_sec=args.poll_interval_sec,
            max_wait_minutes=args.max_wait_minutes,
        )
    elif args.mode == "reparse":
        payload = reparse_phase(run_id=run_id, phase=args.phase, reasoning_effort=args.reasoning_effort)
    elif args.mode == "assemble":
        payload = {"assembled_count": len(assemble_results(run_id=run_id))}
    elif args.mode in {"evaluate", "report"}:
        payload = evaluate_and_report(run_id=run_id)
    elif args.mode == "validate":
        payload = validate_run_artifacts(run_dir(run_id))
    elif args.mode == "run-primary":
        payload = run_primary_flow(args)
    else:
        raise AssertionError(args.mode)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
