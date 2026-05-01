#!/usr/bin/env python3
"""執行 single reviewer official-batch 2-stage direct-review baseline。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

import render_prompt  # noqa: E402
import cutoff_time_filter  # noqa: E402
from experiment_workflows import (  # noqa: E402
    DirectReviewModelOutput,
    SingleReviewerMergedFinalRow,
    SourceRecordProvenance,
    StageDirectReviewRecord,
    build_artifact_review_row,
    build_cutoff_review_row,
    build_direct_stage_prompt_context,
    build_direct_stage_response_model,
    build_direct_stage_validator,
    build_fulltext_resolution_audit,
    build_source_record_provenance,
    collect_phase_issues_by_key,
    criteria_text_for_stage,
    custom_id,
    decision_from_score,
    fulltext_payload_from_resolution,
    load_candidates,
    load_artifact_gate_result,
    load_cutoff_result,
    load_direct_workflow_spec,
    metadata_payload,
    now_run_id,
    phase_success_rows_by_paper_direct,
    read_json,
    relative_path,
    stage_verdict,
    write_json,
)
from openai_batch_runner import BatchRequestSpec, OpenAIBatchRunner, build_json_schema_response_format  # noqa: E402


CONFIG_PATH = BUNDLE_DIR / "config" / "experiment_config.json"
MANIFEST_PATH = BUNDLE_DIR / "manifest.json"
WORKFLOW_SPEC_PATH = BUNDLE_DIR / "workflow" / "workflow_spec.json"
RESULTS_ROOT = REPO_ROOT / "screening" / "results" / "single_reviewer_official_batch_2stage_direct_review_2307_2601_2026-04-17"
RESULTS_MANIFEST_PATH = REPO_ROOT / "screening" / "results" / "results_manifest.json"


class PromptAssets:
    def __init__(self, workflow_spec: Any) -> None:
        self.templates = {
            phase.phase_id: (BUNDLE_DIR / phase.template).read_text(encoding="utf-8")
            for phase in workflow_spec.supported_phases
        }
        self.schema_hints = {
            "stage1_review": (BUNDLE_DIR / "samples" / "stage1_review_output.sample.json").read_text(encoding="utf-8"),
            "stage2_review": (BUNDLE_DIR / "samples" / "stage2_review_output.sample.json").read_text(encoding="utf-8"),
        }


def _load_env_file() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def _load_config() -> dict[str, Any]:
    payload = read_json(CONFIG_PATH)
    required = {
        "model",
        "papers",
        "supported_phases",
        "endpoint",
        "completion_window",
        "batch_poll_interval_sec",
        "batch_max_wait_minutes",
        "fulltext_inline_head_chars",
        "fulltext_inline_tail_chars",
    }
    missing = sorted(required.difference(payload.keys()))
    if missing:
        raise SystemExit("config 缺少必要欄位: " + ", ".join(missing))
    return payload


def _config_with_model_override(config: dict[str, Any], model_override: str | None) -> dict[str, Any]:
    if not model_override:
        return config
    updated = dict(config)
    updated["model"] = model_override
    return updated


def _load_workflow_spec() -> Any:
    return load_direct_workflow_spec(WORKFLOW_SPEC_PATH)


def _workflow_arm() -> str:
    return _load_workflow_spec().workflow_arm


def _stage_model() -> str:
    return _load_workflow_spec().stage_model


def _phase_ids() -> list[str]:
    return [phase.phase_id for phase in _load_workflow_spec().supported_phases]


def _phase_spec(phase_id: str) -> Any:
    workflow_spec = _load_workflow_spec()
    for phase in workflow_spec.supported_phases:
        if phase.phase_id == phase_id:
            return phase
    raise KeyError(f"unknown phase: {phase_id}")


def _paper_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _paper_full_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_full_metadata.jsonl"


def _paper_gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _paper_fulltext_root(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "mds"


def _paper_stage1_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage1" / f"{paper_id}.json"


def _paper_stage2_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage2" / f"{paper_id}.json"


def _paper_cutoff_path(paper_id: str) -> Path:
    return REPO_ROOT / "cutoff_jsons" / f"{paper_id}.json"


def _runtime_prompts_path() -> Path:
    return REPO_ROOT / "scripts" / "screening" / "runtime_prompts" / "runtime_prompts.json"


def _run_dir(run_id: str) -> Path:
    return RESULTS_ROOT / "runs" / run_id


def _batch_artifact_dir(run_id: str, phase: str, model: str) -> Path:
    return _run_dir(run_id) / "batch_jobs" / phase / model


def _paper_dir(run_id: str, paper_id: str) -> Path:
    return _run_dir(run_id) / "papers" / paper_id


def _paper_cutoff_audit_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "cutoff_audit.json"


def _paper_artifact_gate_audit_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "artifact_gate_audit.json"


def _paper_fulltext_resolution_audit_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "fulltext_resolution_audit.json"


def _phase_output_path(run_id: str, paper_id: str, phase_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / _phase_spec(phase_id).output_filename


def _paper_stage2_selection_keys_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "selected_for_stage2.keys.txt"


def _paper_stage1_results_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage1_results.json"


def _paper_stage1_metrics_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage1_f1.json"


def _paper_results_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "single_reviewer_batch_results.json"


def _paper_metrics_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "single_reviewer_batch_f1.json"


def _paper_eval_keys_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "eval_keys.txt"


def _run_manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / "run_manifest.json"


def _report_path(run_id: str) -> Path:
    return _run_dir(run_id) / "REPORT_zh.md"


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _load_records_for_paper(
    paper_id: str,
    *,
    max_records: int | None,
    key_allowlist: set[str] | None,
) -> list[dict[str, Any]]:
    records = load_candidates(_paper_metadata_path(paper_id), max_records=max_records, key_allowlist=key_allowlist)
    if paper_id != "2307.05527":
        return records

    full_rows_by_key = {
        _safe_text(row.get("key")): row
        for row in _read_jsonl(_paper_full_metadata_path(paper_id))
        if _safe_text(row.get("key"))
    }
    merged_records: list[dict[str, Any]] = []
    for record in records:
        key = _safe_text(record.get("key"))
        merged = dict(record)
        full_row = full_rows_by_key.get(key)
        if full_row is not None:
            for field in ("comment", "journal_ref", "doi", "source", "source_id", "source_metadata"):
                value = full_row.get(field)
                if value not in (None, ""):
                    merged[field] = value
        merged_records.append(merged)
    return merged_records


def _load_cutoff_result_for_paper(*, paper_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    cutoff_path = _paper_cutoff_path(paper_id)
    if paper_id != "2307.05527":
        return load_cutoff_result(records=records, cutoff_path=cutoff_path)

    payload, policy = cutoff_time_filter.load_time_policy(cutoff_path)
    payload = dict(payload)
    payload["_cutoff_json_path"] = str(cutoff_path)
    payload["time_policy"] = dict(payload.get("time_policy") or {})
    payload["time_policy"]["preprint_split_submitted_date"] = True
    policy = replace(policy, preprint_split_submitted_date=True)
    return cutoff_time_filter.apply_cutoff(records, payload=payload, policy=policy)


def _load_candidate_key_map(path: Path | None, *, selected_papers: list[str]) -> dict[str, set[str]] | None:
    if path is None:
        return None
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise SystemExit("--candidate-keys-file 必須是 paper_id -> key list 的 JSON object")
    out: dict[str, set[str]] = {}
    for paper_id in selected_papers:
        values = payload.get(paper_id, [])
        if not isinstance(values, list):
            raise SystemExit(f"candidate keys for {paper_id} 必須是 list")
        out[paper_id] = {str(item).strip() for item in values if str(item).strip()}
    return out


def _build_body(
    *,
    model: str,
    prompt: str,
    response_model: type[Any],
    schema_name: str,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(response_model, schema_name=schema_name),
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    return body


def _load_stage_records(path: Path) -> list[StageDirectReviewRecord]:
    if not path.exists():
        return []
    payload = read_json(path)
    if not isinstance(payload, list):
        return []
    return [StageDirectReviewRecord.model_validate(row) for row in payload]


def _outputs_by_key(outputs: list[StageDirectReviewRecord]) -> dict[str, StageDirectReviewRecord]:
    return {item.candidate_key: item for item in outputs}


def _build_error_final_row(
    *,
    paper_id: str,
    record: dict[str, Any],
    provenance: SourceRecordProvenance,
    review_state: str,
    failed_phase: str,
    review_output: dict[str, Any] | None,
    fulltext_resolution_status: str | None,
    fulltext_source_path: str | None,
    discard_reason: str | None = None,
) -> SingleReviewerMergedFinalRow:
    return SingleReviewerMergedFinalRow(
        key=_safe_text(record.get("key")),
        title=_safe_text(record.get("title") or record.get("query_title")),
        paper_id=paper_id,
        workflow_arm=_workflow_arm(),
        stage_model=_stage_model(),
        review_state=review_state,
        review_skipped=False,
        failed_phase=failed_phase,
        discard_reason=discard_reason or review_state,
        final_verdict=f"maybe (review_state:{review_state})",
        source_record_provenance=provenance,
        review_output=review_output,
        fulltext_source_path=fulltext_source_path,
        fulltext_resolution_status=fulltext_resolution_status,
    )


def _prepare_stage1_review_specs(
    *,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    write_audits: bool,
) -> dict[str, Any]:
    specs: list[BatchRequestSpec] = []
    paper_summaries: dict[str, Any] = {}
    workflow_spec = _load_workflow_spec()
    phase_id = "stage1_review"
    response_model = build_direct_stage_response_model("Stage1DirectReviewOutput")

    for paper_id in selected_papers:
        key_allowlist = key_map.get(paper_id) if key_map is not None else None
        records = _load_records_for_paper(paper_id, max_records=max_records, key_allowlist=key_allowlist)
        if key_allowlist is not None:
            keys_path = _paper_eval_keys_path(run_id, paper_id)
            keys_path.parent.mkdir(parents=True, exist_ok=True)
            keys_path.write_text(
                "\n".join([_safe_text(row.get("key")) for row in records]) + ("\n" if records else ""),
                encoding="utf-8",
            )
        resolution_by_key, resolution_audit = build_fulltext_resolution_audit(
            paper_id=paper_id,
            records=records,
            fulltext_root=_paper_fulltext_root(paper_id),
            repo_root=REPO_ROOT,
        )
        if write_audits:
            write_json(_paper_fulltext_resolution_audit_path(run_id, paper_id), resolution_audit)
        artifact_result = load_artifact_gate_result(records=records)
        artifact_audit = dict(artifact_result["audit_payload"])
        artifact_audit["paper_id"] = paper_id
        if write_audits:
            write_json(_paper_artifact_gate_audit_path(run_id, paper_id), artifact_audit)
        cutoff_result = _load_cutoff_result_for_paper(paper_id=paper_id, records=records)
        if write_audits:
            write_json(_paper_cutoff_audit_path(run_id, paper_id), cutoff_result["audit_payload"])
        stage1_records = [
            record
            for record in cutoff_result["kept_records"]
            if artifact_result["decisions_by_key"][_safe_text(record.get("key"))]["gate_pass"]
        ]

        criteria_path = _paper_stage1_criteria_path(paper_id)
        criteria_payload = criteria_text_for_stage(criteria_path)
        for record in stage1_records:
            key = _safe_text(record.get("key"))
            title = _safe_text(record.get("title") or record.get("query_title"))
            resolution = resolution_by_key[key]
            provenance = build_source_record_provenance(
                record=record,
                paper_id=paper_id,
                resolution=resolution,
                metadata_path=_paper_metadata_path(paper_id),
                runtime_prompts_path=_runtime_prompts_path(),
                criteria_path=criteria_path,
                repo_root=REPO_ROOT,
            )
            context = build_direct_stage_prompt_context(
                stage="stage1",
                workflow_arm=workflow_spec.workflow_arm,
                paper_id=paper_id,
                candidate_key=key,
                candidate_title=title,
                criteria_payload=criteria_payload,
                metadata=metadata_payload(record),
                response_schema_hint=prompt_assets.schema_hints[phase_id],
                provenance=provenance,
            )
            prompt = render_prompt._render(prompt_assets.templates[phase_id], context, strict=True)
            specs.append(
                BatchRequestSpec(
                    custom_id=custom_id(phase_id, paper_id, key),
                    model=str(config["model"]),
                    body=_build_body(
                        model=str(config["model"]),
                        prompt=prompt,
                        response_model=response_model,
                        schema_name=f"Stage1DirectReviewOutput_{paper_id.replace('.', '_')}",
                        reasoning_effort=reasoning_effort,
                    ),
                    response_model=response_model,
                    validator=build_direct_stage_validator(
                        paper_id=paper_id,
                        stage="stage1",
                        candidate_key=key,
                        candidate_title=title,
                    ),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": title,
                        "phase": phase_id,
                        "stage": "stage1",
                        "criteria_path": str(criteria_path.relative_to(REPO_ROOT)),
                        "provenance": provenance.model_dump(mode="json"),
                    },
                )
            )
        paper_summaries[paper_id] = {
            "candidate_total": len(records),
            "cutoff_pass_count": len(cutoff_result["kept_records"]),
            "cutoff_excluded_count": len(cutoff_result["excluded_records"]),
            "artifact_excluded_count": len(cutoff_result["kept_records"]) - len(stage1_records),
            "request_count": len(stage1_records),
        }
    return {"specs": specs, "paper_summaries": paper_summaries}


def _prepare_stage2_review_specs(
    *,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    write_audits: bool,
    stage2_all_cutoff_pass: bool = False,
) -> dict[str, Any]:
    specs: list[BatchRequestSpec] = []
    paper_summaries: dict[str, Any] = {}
    workflow_spec = _load_workflow_spec()
    phase_id = "stage2_review"
    gate_policy = workflow_spec.gate_policy
    response_model = build_direct_stage_response_model("Stage2DirectReviewOutput")

    for paper_id in selected_papers:
        key_allowlist = key_map.get(paper_id) if key_map is not None else None
        records = _load_records_for_paper(paper_id, max_records=max_records, key_allowlist=key_allowlist)
        artifact_result = load_artifact_gate_result(records=records)
        artifact_audit = dict(artifact_result["audit_payload"])
        artifact_audit["paper_id"] = paper_id
        if write_audits:
            write_json(_paper_artifact_gate_audit_path(run_id, paper_id), artifact_audit)
        cutoff_result = _load_cutoff_result_for_paper(paper_id=paper_id, records=records)
        resolution_by_key, resolution_audit = build_fulltext_resolution_audit(
            paper_id=paper_id,
            records=records,
            fulltext_root=_paper_fulltext_root(paper_id),
            repo_root=REPO_ROOT,
        )
        if write_audits:
            write_json(_paper_fulltext_resolution_audit_path(run_id, paper_id), resolution_audit)

        if stage2_all_cutoff_pass:
            stage1_by_key = {}
        else:
            selection_phase_path = _phase_output_path(run_id, paper_id, gate_policy.selection_phase)
            if not selection_phase_path.exists():
                raise SystemExit(f"stage2_review 需要先 collect {gate_policy.selection_phase}: {selection_phase_path}")
            stage1_by_key = _outputs_by_key(_load_stage_records(selection_phase_path))
        criteria_path = _paper_stage2_criteria_path(paper_id)
        criteria_payload = criteria_text_for_stage(criteria_path)
        selected_keys: list[str] = []

        for record in records:
            key = _safe_text(record.get("key"))
            if not cutoff_result["decisions_by_key"][key]["cutoff_pass"]:
                continue
            if not artifact_result["decisions_by_key"][key]["gate_pass"]:
                continue
            stage1_record = stage1_by_key.get(key)
            if not stage2_all_cutoff_pass:
                if stage1_record is None:
                    continue
                if stage1_record.decision_recommendation not in gate_policy.advance_decisions:
                    continue
            resolution = resolution_by_key[key]
            if not bool(resolution.get("fulltext_gate_pass", True)):
                continue
            if resolution["resolution_status"] not in {"exact", "normalized"}:
                continue
            selected_keys.append(key)
            fulltext_text, _fulltext_meta = fulltext_payload_from_resolution(
                resolution,
                repo_root=REPO_ROOT,
                head_chars=int(config["fulltext_inline_head_chars"]),
                tail_chars=int(config["fulltext_inline_tail_chars"]),
            )
            title = _safe_text(record.get("title") or record.get("query_title"))
            provenance = build_source_record_provenance(
                record=record,
                paper_id=paper_id,
                resolution=resolution,
                metadata_path=_paper_metadata_path(paper_id),
                runtime_prompts_path=_runtime_prompts_path(),
                criteria_path=criteria_path,
                repo_root=REPO_ROOT,
            )
            context = build_direct_stage_prompt_context(
                stage="stage2",
                workflow_arm=workflow_spec.workflow_arm,
                paper_id=paper_id,
                candidate_key=key,
                candidate_title=title,
                criteria_payload=criteria_payload,
                metadata=metadata_payload(record),
                response_schema_hint=prompt_assets.schema_hints[phase_id],
                provenance=provenance,
                prior_stage_review=stage1_record.model_dump(mode="json") if stage1_record is not None else None,
                fulltext_resolution=resolution,
                fulltext_text=fulltext_text,
            )
            prompt = render_prompt._render(prompt_assets.templates[phase_id], context, strict=True)
            specs.append(
                BatchRequestSpec(
                    custom_id=custom_id(phase_id, paper_id, key),
                    model=str(config["model"]),
                    body=_build_body(
                        model=str(config["model"]),
                        prompt=prompt,
                        response_model=response_model,
                        schema_name=f"Stage2DirectReviewOutput_{paper_id.replace('.', '_')}",
                        reasoning_effort=reasoning_effort,
                    ),
                    response_model=response_model,
                    validator=build_direct_stage_validator(
                        paper_id=paper_id,
                        stage="stage2",
                        candidate_key=key,
                        candidate_title=title,
                    ),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": title,
                        "phase": phase_id,
                        "stage": "stage2",
                        "criteria_path": str(criteria_path.relative_to(REPO_ROOT)),
                        "provenance": provenance.model_dump(mode="json"),
                    },
                )
            )

        selection_path = _paper_stage2_selection_keys_path(run_id, paper_id)
        selection_path.parent.mkdir(parents=True, exist_ok=True)
        selection_path.write_text("\n".join(selected_keys) + ("\n" if selected_keys else ""), encoding="utf-8")
        paper_summaries[paper_id] = {
            "candidate_total": len(records),
            "cutoff_pass_count": len(cutoff_result["kept_records"]),
            "artifact_excluded_count": sum(
                1
                for record in cutoff_result["kept_records"]
                if not artifact_result["decisions_by_key"][_safe_text(record.get("key"))]["gate_pass"]
            ),
            "fulltext_gate_failed_count": int(resolution_audit.get("fulltext_gate_failed_count") or 0),
            "selected_for_stage2_count": len(selected_keys),
            "request_count": len(selected_keys),
        }
    return {"specs": specs, "paper_summaries": paper_summaries}


PHASE_BUILDERS = {
    "stage1_review": _prepare_stage1_review_specs,
    "stage2_review": _prepare_stage2_review_specs,
}


def _phase_preparation(
    *,
    phase: str,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    write_audits: bool,
    stage2_all_cutoff_pass: bool = False,
) -> dict[str, Any]:
    builder = PHASE_BUILDERS.get(phase)
    if builder is None:
        raise ValueError(f"unsupported phase: {phase}")
    kwargs = dict(
        run_id=run_id,
        prompt_assets=prompt_assets,
        config=config,
        selected_papers=selected_papers,
        key_map=key_map,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
        write_audits=write_audits,
    )
    if phase == "stage2_review":
        kwargs["stage2_all_cutoff_pass"] = stage2_all_cutoff_pass
    return builder(**kwargs)


def _init_run_manifest(
    *,
    run_id: str,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map_path: Path | None,
    max_records: int | None,
    reasoning_effort: str | None,
    stage2_all_cutoff_pass: bool,
) -> dict[str, Any]:
    workflow_spec = _load_workflow_spec()
    return {
        "run_id": run_id,
        "bundle_dir": str(BUNDLE_DIR),
        "manifest_path": str(MANIFEST_PATH),
        "workflow_spec_path": str(WORKFLOW_SPEC_PATH),
        "run_manifest_path": str(_run_manifest_path(run_id)),
        "results_root": str(RESULTS_ROOT),
        "run_dir": str(_run_dir(run_id)),
        "model": str(config["model"]),
        "endpoint": str(config["endpoint"]),
        "workflow_arm": workflow_spec.workflow_arm,
        "stage_model": workflow_spec.stage_model,
        "papers": selected_papers,
        "max_records": max_records,
        "candidate_keys_file": relative_path(key_map_path, REPO_ROOT),
        "reasoning_effort": reasoning_effort,
        "stage2_all_cutoff_pass": stage2_all_cutoff_pass,
        "phase_jobs": {},
    }


def _load_or_init_run_manifest(
    *,
    run_id: str,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map_path: Path | None,
    max_records: int | None,
    reasoning_effort: str | None,
    stage2_all_cutoff_pass: bool,
) -> dict[str, Any]:
    manifest_path = _run_manifest_path(run_id)
    if manifest_path.exists():
        return read_json(manifest_path)
    manifest = _init_run_manifest(
        run_id=run_id,
        config=config,
        selected_papers=selected_papers,
        key_map_path=key_map_path,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
        stage2_all_cutoff_pass=stage2_all_cutoff_pass,
    )
    write_json(manifest_path, manifest)
    return manifest


def _load_batch_payload_for_phase(run_id: str, phase: str, model: str) -> dict[str, Any] | None:
    artifact_dir = _batch_artifact_dir(run_id, phase, model)
    for filename in ("batch_latest.json", "batch_create.json"):
        path = artifact_dir / filename
        if path.exists():
            return read_json(path)
    return None


def _submit_phase(
    *,
    phase: str,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    key_map_path: Path | None,
    max_records: int | None,
    reasoning_effort: str | None,
    stage2_all_cutoff_pass: bool = False,
) -> dict[str, Any]:
    _load_env_file()
    _run_dir(run_id).mkdir(parents=True, exist_ok=True)
    run_manifest = _load_or_init_run_manifest(
        run_id=run_id,
        config=config,
        selected_papers=selected_papers,
        key_map_path=key_map_path,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
        stage2_all_cutoff_pass=stage2_all_cutoff_pass,
    )
    prep = _phase_preparation(
        phase=phase,
        run_id=run_id,
        prompt_assets=prompt_assets,
        config=config,
        selected_papers=selected_papers,
        key_map=key_map,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
        write_audits=True,
        stage2_all_cutoff_pass=stage2_all_cutoff_pass,
    )
    specs: list[BatchRequestSpec] = prep["specs"]
    artifact_dir = _batch_artifact_dir(run_id, phase, str(config["model"]))

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
        run_manifest["phase_jobs"][phase] = {
            "phase": phase,
            "batch_artifact_dir": str(artifact_dir),
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "request_count": 0,
            "paper_preparation": prep["paper_summaries"],
        }
        write_json(_run_manifest_path(run_id), run_manifest)
        print(f"[submit:{phase}] no requests", flush=True)
        return run_manifest["phase_jobs"][phase]

    client = OpenAI()
    model_id = client.models.retrieve(str(config["model"])).id
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=float(config["batch_poll_interval_sec"]))
    submit_payload = runner.submit_requests(
        specs=specs,
        endpoint=str(config["endpoint"]),
        artifact_dir=artifact_dir,
        metadata={
            "experiment": _workflow_arm(),
            "phase": phase,
            "run_id": run_id,
            "paper_count": len(selected_papers),
        },
        completion_window=str(config["completion_window"]),
    )
    run_manifest["model_preflight_id"] = model_id
    run_manifest["phase_jobs"][phase] = {
        "phase": phase,
        "batch_artifact_dir": str(artifact_dir),
        "batch_id": submit_payload["batch_create"]["id"],
        "batch_status": submit_payload["batch_create"]["status"],
        "request_count": len(specs),
        "paper_preparation": prep["paper_summaries"],
        "upload_file_id": submit_payload["upload_file"]["id"],
    }
    write_json(_run_manifest_path(run_id), run_manifest)
    print(f"[submit:{phase}] run_id={run_id}", flush=True)
    print(f"[submit:{phase}] batch_id={submit_payload['batch_create']['id']}", flush=True)
    return run_manifest["phase_jobs"][phase]


def _collect_phase(
    *,
    phase: str,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    batch_poll_interval_sec: float | None,
    batch_max_wait_minutes: float | None,
    stage2_all_cutoff_pass: bool = False,
) -> dict[str, Any]:
    _load_env_file()
    run_manifest = read_json(_run_manifest_path(run_id))
    prep = _phase_preparation(
        phase=phase,
        run_id=run_id,
        prompt_assets=prompt_assets,
        config=config,
        selected_papers=selected_papers,
        key_map=key_map,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
        write_audits=True,
        stage2_all_cutoff_pass=stage2_all_cutoff_pass,
    )
    specs: list[BatchRequestSpec] = prep["specs"]
    artifact_dir = _batch_artifact_dir(run_id, phase, str(config["model"]))
    batch_payload = _load_batch_payload_for_phase(run_id, phase, str(config["model"]))

    if batch_payload is None or batch_payload.get("id") is None:
        parsed_payload = read_json(artifact_dir / "parsed_results.json") if (artifact_dir / "parsed_results.json").exists() else {
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
    else:
        runner = OpenAIBatchRunner(
            client=OpenAI(),
            poll_interval_sec=float(batch_poll_interval_sec or config["batch_poll_interval_sec"]),
        )
        batch_payload = runner.wait_until_terminal(
            str(batch_payload["id"]),
            artifact_dir=artifact_dir,
            max_wait_minutes=float(batch_max_wait_minutes or config["batch_max_wait_minutes"]),
        )
        parsed_payload = runner.collect_results(specs=specs, batch_payload=batch_payload, artifact_dir=artifact_dir)
        run_manifest["phase_jobs"].setdefault(phase, {})
        run_manifest["phase_jobs"][phase].update(
            {
                "batch_status": batch_payload.get("status"),
                "batch_completed_at": batch_payload.get("completed_at"),
                "batch_output_file_id": batch_payload.get("output_file_id"),
                "batch_error_file_id": batch_payload.get("error_file_id"),
            }
        )

    spec_context = {spec.custom_id: spec.context for spec in specs}
    phase_stage = _phase_spec(phase).stage
    rows_by_paper = phase_success_rows_by_paper_direct(
        parsed_payload=parsed_payload,
        spec_context=spec_context,
        stage=phase_stage,
        workflow_arm=_workflow_arm(),
    )
    for paper_id in selected_papers:
        write_json(_phase_output_path(run_id, paper_id, phase), rows_by_paper.get(paper_id, []))

    run_manifest["phase_jobs"].setdefault(phase, {})
    run_manifest["phase_jobs"][phase]["parsed_summary"] = {
        "success_count": len(parsed_payload["successes"]),
        "failure_count": len(parsed_payload["failures"]),
        "missing_count": len(parsed_payload["missing"]),
    }
    write_json(_run_manifest_path(run_id), run_manifest)
    print(f"[collect:{phase}] run_id={run_id}", flush=True)
    print(f"[collect:{phase}] batch_status={parsed_payload.get('batch_status')}", flush=True)
    return parsed_payload


def _write_stage1_results(
    *,
    run_id: str,
    paper_id: str,
    records: list[dict[str, Any]],
    artifact_result: dict[str, Any],
    cutoff_result: dict[str, Any],
    stage1_by_key: dict[str, StageDirectReviewRecord],
    stage1_issue_by_key: dict[str, dict[str, Any]],
    resolution_by_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        key = _safe_text(record.get("key"))
        title = _safe_text(record.get("title") or record.get("query_title"))
        decision = cutoff_result["decisions_by_key"][key]
        if not decision["cutoff_pass"]:
            rows.append(
                build_cutoff_review_row(
                    paper_id=paper_id,
                    workflow_arm=_workflow_arm(),
                    stage_model=_stage_model(),
                    record=record,
                    decision=decision,
                ).model_dump(mode="json")
            )
            continue
        artifact_decision = artifact_result["decisions_by_key"][key]
        if not artifact_decision["gate_pass"]:
            rows.append(
                build_artifact_review_row(
                    paper_id=paper_id,
                    workflow_arm=_workflow_arm(),
                    stage_model=_stage_model(),
                    record=record,
                    decision=artifact_decision,
                ).model_dump(mode="json")
            )
            continue
        resolution = resolution_by_key[key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_paper_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=_paper_stage1_criteria_path(paper_id),
            repo_root=REPO_ROOT,
        )
        stage1_issue = stage1_issue_by_key.get(key)
        if stage1_issue is not None or key not in stage1_by_key:
            rows.append(
                _build_error_final_row(
                    paper_id=paper_id,
                    record=record,
                    provenance=provenance,
                    review_state=(stage1_issue or {}).get("review_state", "batch_unmapped"),
                    failed_phase="stage1_review",
                    review_output=(stage1_issue or {}).get("review_output"),
                    fulltext_resolution_status=resolution["resolution_status"],
                    fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    discard_reason="stage1_review_missing",
                ).model_dump(mode="json")
            )
            continue
        stage1_record = stage1_by_key[key]
        rows.append(
            SingleReviewerMergedFinalRow(
                key=key,
                title=title,
                paper_id=paper_id,
                workflow_arm=_workflow_arm(),
                stage_model=_stage_model(),
                review_state="reviewed",
                review_skipped=False,
                final_verdict=stage_verdict("stage1", stage1_record.stage_score),
                stage1_stage_score=stage1_record.stage_score,
                stage1_decision_recommendation=stage1_record.decision_recommendation,
                stage1_review_path=relative_path(_phase_output_path(run_id, paper_id, "stage1_review"), REPO_ROOT),
                source_record_provenance=stage1_record.source_record_provenance,
                review_output={"stage1_review": stage1_record.model_dump(mode="json")},
                fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                fulltext_resolution_status=resolution["resolution_status"],
            ).model_dump(mode="json")
        )
    write_json(_paper_stage1_results_path(run_id, paper_id), rows)
    return rows


def _evaluate_results(
    *,
    paper_id: str,
    results_path: Path,
    output_path: Path,
    keys_path: Path | None,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        paper_id,
        "--results",
        str(results_path),
        "--gold-metadata",
        str(_paper_gold_path(paper_id)),
        "--positive-mode",
        "include_or_maybe",
        "--save-report",
        str(output_path),
    ]
    if keys_path is not None and keys_path.exists():
        cmd.extend(["--keys-file", str(keys_path)])
    subprocess.run(cmd, check=True, cwd=str(REPO_ROOT))
    return read_json(output_path)


def _assemble_results_and_metrics(
    *,
    run_id: str,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    report_reasoning_effort: str | None,
    stage2_all_cutoff_pass: bool = False,
) -> dict[str, Any]:
    baseline = read_json(RESULTS_MANIFEST_PATH)["papers"]
    stage1_issue_by_paper = (
        {}
        if stage2_all_cutoff_pass
        else collect_phase_issues_by_key(_batch_artifact_dir(run_id, "stage1_review", str(config["model"])) / "parsed_results.json")
    )
    stage2_issue_by_paper = collect_phase_issues_by_key(
        _batch_artifact_dir(run_id, "stage2_review", str(config["model"])) / "parsed_results.json"
    )
    summaries: list[dict[str, Any]] = []

    for paper_id in selected_papers:
        key_allowlist = key_map.get(paper_id) if key_map is not None else None
        records = _load_records_for_paper(paper_id, max_records=max_records, key_allowlist=key_allowlist)
        artifact_result = load_artifact_gate_result(records=records)
        artifact_audit = dict(artifact_result["audit_payload"])
        artifact_audit["paper_id"] = paper_id
        write_json(_paper_artifact_gate_audit_path(run_id, paper_id), artifact_audit)
        cutoff_result = _load_cutoff_result_for_paper(paper_id=paper_id, records=records)
        write_json(_paper_cutoff_audit_path(run_id, paper_id), cutoff_result["audit_payload"])
        resolution_by_key, resolution_audit = build_fulltext_resolution_audit(
            paper_id=paper_id,
            records=records,
            fulltext_root=_paper_fulltext_root(paper_id),
            repo_root=REPO_ROOT,
        )
        write_json(_paper_fulltext_resolution_audit_path(run_id, paper_id), resolution_audit)

        stage1_by_key = _outputs_by_key(_load_stage_records(_phase_output_path(run_id, paper_id, "stage1_review")))
        stage2_by_key = _outputs_by_key(_load_stage_records(_phase_output_path(run_id, paper_id, "stage2_review")))
        stage1_issue_by_key = stage1_issue_by_paper.get(paper_id, {})
        stage2_issue_by_key = stage2_issue_by_paper.get(paper_id, {})

        keys_path = _paper_eval_keys_path(run_id, paper_id)
        stage1_metrics = None
        if not stage2_all_cutoff_pass:
            _write_stage1_results(
                run_id=run_id,
                paper_id=paper_id,
                records=records,
                artifact_result=artifact_result,
                cutoff_result=cutoff_result,
                stage1_by_key=stage1_by_key,
                stage1_issue_by_key=stage1_issue_by_key,
                resolution_by_key=resolution_by_key,
            )
            stage1_metrics = _evaluate_results(
                paper_id=paper_id,
                results_path=_paper_stage1_results_path(run_id, paper_id),
                output_path=_paper_stage1_metrics_path(run_id, paper_id),
                keys_path=keys_path if keys_path.exists() else None,
            )

        final_rows: list[dict[str, Any]] = []
        reviewed_count = 0
        missing_count = 0
        fulltext_gate_failed_count = 0
        for record in records:
            key = _safe_text(record.get("key"))
            title = _safe_text(record.get("title") or record.get("query_title"))
            decision = cutoff_result["decisions_by_key"][key]

            if not decision["cutoff_pass"]:
                final_rows.append(
                    build_cutoff_review_row(
                        paper_id=paper_id,
                        workflow_arm=_workflow_arm(),
                        stage_model=_stage_model(),
                        record=record,
                        decision=decision,
                    ).model_dump(mode="json")
                )
                continue
            artifact_decision = artifact_result["decisions_by_key"][key]
            if not artifact_decision["gate_pass"]:
                final_rows.append(
                    build_artifact_review_row(
                        paper_id=paper_id,
                        workflow_arm=_workflow_arm(),
                        stage_model=_stage_model(),
                        record=record,
                        decision=artifact_decision,
                    ).model_dump(mode="json")
                )
                continue
            resolution = resolution_by_key[key]
            provenance = build_source_record_provenance(
                record=record,
                paper_id=paper_id,
                resolution=resolution,
                metadata_path=_paper_metadata_path(paper_id),
                runtime_prompts_path=_runtime_prompts_path(),
                criteria_path=_paper_stage2_criteria_path(paper_id) if stage2_all_cutoff_pass else _paper_stage1_criteria_path(paper_id),
                repo_root=REPO_ROOT,
            )

            stage1_issue = stage1_issue_by_key.get(key)
            stage1_record = stage1_by_key.get(key)
            if not stage2_all_cutoff_pass:
                if stage1_issue is not None or stage1_record is None:
                    final_rows.append(
                        _build_error_final_row(
                            paper_id=paper_id,
                            record=record,
                            provenance=provenance,
                            review_state=(stage1_issue or {}).get("review_state", "batch_unmapped"),
                            failed_phase="stage1_review",
                            review_output=(stage1_issue or {}).get("review_output"),
                            fulltext_resolution_status=resolution["resolution_status"],
                            fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                        ).model_dump(mode="json")
                    )
                    continue

                if stage1_record.decision_recommendation == "exclude":
                    reviewed_count += 1
                    final_rows.append(
                        SingleReviewerMergedFinalRow(
                            key=key,
                            title=title,
                            paper_id=paper_id,
                            workflow_arm=_workflow_arm(),
                            stage_model=_stage_model(),
                            review_state="reviewed",
                            review_skipped=False,
                            final_verdict=stage_verdict("stage1", stage1_record.stage_score),
                            stage1_stage_score=stage1_record.stage_score,
                            stage1_decision_recommendation=stage1_record.decision_recommendation,
                            stage1_review_path=relative_path(_phase_output_path(run_id, paper_id, "stage1_review"), REPO_ROOT),
                            source_record_provenance=stage1_record.source_record_provenance,
                            review_output={"stage1_review": stage1_record.model_dump(mode="json")},
                            fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                            fulltext_resolution_status=resolution["resolution_status"],
                        ).model_dump(mode="json")
                    )
                    continue

            if not bool(resolution.get("fulltext_gate_pass", True)):
                fulltext_gate_failed_count += 1
                gate_reason = str(resolution.get("fulltext_gate_reason") or "metadata_flag_false")
                review_output = {
                    "fulltext_gate": {
                        "gate_pass": False,
                        "gate_reason": gate_reason,
                        "gate_status": resolution.get("fulltext_gate_status"),
                    },
                    "resolution": resolution,
                }
                if stage1_record is not None:
                    review_output["stage1_review"] = stage1_record.model_dump(mode="json")
                final_rows.append(
                    SingleReviewerMergedFinalRow(
                        key=key,
                        title=title,
                        paper_id=paper_id,
                        workflow_arm=_workflow_arm(),
                        stage_model=_stage_model(),
                        review_state="fulltext_gate_failed",
                        review_skipped=True,
                        discard_reason=f"fulltext_gate:{gate_reason}",
                        final_verdict="exclude (fulltext_gate_failed)" if stage2_all_cutoff_pass else stage_verdict("stage1", stage1_record.stage_score),
                        stage1_stage_score=stage1_record.stage_score if stage1_record is not None else None,
                        stage1_decision_recommendation=stage1_record.decision_recommendation if stage1_record is not None else None,
                        stage1_review_path=relative_path(_phase_output_path(run_id, paper_id, "stage1_review"), REPO_ROOT) if stage1_record is not None else None,
                        source_record_provenance=stage1_record.source_record_provenance if stage1_record is not None else provenance,
                        review_output=review_output,
                        fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                        fulltext_resolution_status=resolution["resolution_status"],
                    ).model_dump(mode="json")
                )
                continue

            if resolution["resolution_status"] not in {"exact", "normalized"}:
                missing_count += 1
                review_output = {
                    "fulltext_missing_or_unmatched": True,
                    "resolution": resolution,
                }
                if stage1_record is not None:
                    review_output["stage1_review"] = stage1_record.model_dump(mode="json")
                final_rows.append(
                    SingleReviewerMergedFinalRow(
                        key=key,
                        title=title,
                        paper_id=paper_id,
                        workflow_arm=_workflow_arm(),
                        stage_model=_stage_model(),
                        review_state="missing",
                        review_skipped=True,
                        discard_reason="fulltext_missing",
                        final_verdict="exclude (fulltext_missing)" if stage2_all_cutoff_pass else stage_verdict("stage1", stage1_record.stage_score),
                        stage1_stage_score=stage1_record.stage_score if stage1_record is not None else None,
                        stage1_decision_recommendation=stage1_record.decision_recommendation if stage1_record is not None else None,
                        stage1_review_path=relative_path(_phase_output_path(run_id, paper_id, "stage1_review"), REPO_ROOT) if stage1_record is not None else None,
                        source_record_provenance=stage1_record.source_record_provenance if stage1_record is not None else provenance,
                        review_output=review_output,
                        fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                        fulltext_resolution_status=resolution["resolution_status"],
                    ).model_dump(mode="json")
                )
                continue

            stage2_issue = stage2_issue_by_key.get(key)
            if stage2_issue is not None or key not in stage2_by_key:
                final_rows.append(
                    _build_error_final_row(
                        paper_id=paper_id,
                        record=record,
                        provenance=provenance,
                        review_state=(stage2_issue or {}).get("review_state", "batch_unmapped"),
                        failed_phase="stage2_review",
                        review_output=(stage2_issue or {}).get("review_output"),
                        fulltext_resolution_status=resolution["resolution_status"],
                        fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    ).model_dump(mode="json")
                )
                continue

            stage2_record = stage2_by_key[key]
            reviewed_count += 1
            final_rows.append(
                SingleReviewerMergedFinalRow(
                    key=key,
                    title=title,
                    paper_id=paper_id,
                    workflow_arm=_workflow_arm(),
                    stage_model=_stage_model(),
                    review_state="reviewed",
                    review_skipped=False,
                    final_verdict=stage_verdict("stage2", stage2_record.stage_score),
                    stage1_stage_score=stage1_record.stage_score if stage1_record is not None else None,
                    stage1_decision_recommendation=stage1_record.decision_recommendation if stage1_record is not None else None,
                    stage2_stage_score=stage2_record.stage_score,
                    stage2_decision_recommendation=stage2_record.decision_recommendation,
                    stage1_review_path=relative_path(_phase_output_path(run_id, paper_id, "stage1_review"), REPO_ROOT) if stage1_record is not None else None,
                    stage2_review_path=relative_path(_phase_output_path(run_id, paper_id, "stage2_review"), REPO_ROOT),
                    source_record_provenance=stage2_record.source_record_provenance,
                    review_output=(
                        {"stage2_review": stage2_record.model_dump(mode="json")}
                        if stage1_record is None
                        else {
                            "stage1_review": stage1_record.model_dump(mode="json"),
                            "stage2_review": stage2_record.model_dump(mode="json"),
                        }
                    ),
                    fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    fulltext_resolution_status=resolution["resolution_status"],
                ).model_dump(mode="json")
            )

        write_json(_paper_results_path(run_id, paper_id), final_rows)
        combined_metrics = _evaluate_results(
            paper_id=paper_id,
            results_path=_paper_results_path(run_id, paper_id),
            output_path=_paper_metrics_path(run_id, paper_id),
            keys_path=keys_path if keys_path.exists() else None,
        )

        current_stage1 = baseline[paper_id]["current_metrics"]["stage1"]
        current_combined = baseline[paper_id]["current_metrics"]["combined"]
        selected_keys_path = _paper_stage2_selection_keys_path(run_id, paper_id)
        selected_count = 0
        if selected_keys_path.exists():
            selected_count = len([line for line in selected_keys_path.read_text(encoding="utf-8").splitlines() if line.strip()])

        summaries.append(
            {
                "paper_id": paper_id,
                "candidate_total": len(records),
                "cutoff_pass_count": cutoff_result["audit_payload"]["candidate_total_after_cutoff"],
                "cutoff_excluded_count": cutoff_result["audit_payload"]["cutoff_excluded_count"],
                "artifact_excluded_count": sum(
                    1
                    for record in cutoff_result["kept_records"]
                    if not artifact_result["decisions_by_key"][_safe_text(record.get("key"))]["gate_pass"]
                ),
                "stage2_selected_count": selected_count,
                "reviewed_count": reviewed_count,
                "missing_count": missing_count,
                "fulltext_gate_failed_count": fulltext_gate_failed_count,
                "stage1_results_path": relative_path(_paper_stage1_results_path(run_id, paper_id), REPO_ROOT) if stage1_metrics is not None else None,
                "stage1_metrics_path": relative_path(_paper_stage1_metrics_path(run_id, paper_id), REPO_ROOT) if stage1_metrics is not None else None,
                "stage1_precision": float(stage1_metrics["metrics"]["precision"]) if stage1_metrics is not None else None,
                "stage1_recall": float(stage1_metrics["metrics"]["recall"]) if stage1_metrics is not None else None,
                "stage1_f1": float(stage1_metrics["metrics"]["f1"]) if stage1_metrics is not None else None,
                "delta_vs_current_stage1": (float(stage1_metrics["metrics"]["f1"]) - float(current_stage1["f1"])) if stage1_metrics is not None else None,
                "results_path": relative_path(_paper_results_path(run_id, paper_id), REPO_ROOT),
                "metrics_path": relative_path(_paper_metrics_path(run_id, paper_id), REPO_ROOT),
                "precision": float(combined_metrics["metrics"]["precision"]),
                "recall": float(combined_metrics["metrics"]["recall"]),
                "f1": float(combined_metrics["metrics"]["f1"]),
                "delta_vs_current_combined": float(combined_metrics["metrics"]["f1"]) - float(current_combined["f1"]),
            }
        )

    run_manifest = read_json(_run_manifest_path(run_id))
    run_manifest["mode"] = "collect"
    run_manifest["reasoning_effort"] = report_reasoning_effort
    run_manifest["stage2_all_cutoff_pass"] = stage2_all_cutoff_pass
    run_manifest["baseline"] = {
        paper_id: {
            "stage1": {
                "path": baseline[paper_id]["current_metrics"]["stage1"]["path"],
                "f1": float(baseline[paper_id]["current_metrics"]["stage1"]["f1"]),
            },
            "combined": {
                "path": baseline[paper_id]["current_metrics"]["combined"]["path"],
                "f1": float(baseline[paper_id]["current_metrics"]["combined"]["f1"]),
            },
        }
        for paper_id in selected_papers
    }
    run_manifest["summaries"] = summaries
    write_json(_run_manifest_path(run_id), run_manifest)
    _report_path(run_id).write_text(_build_report_zh(run_manifest), encoding="utf-8")
    return run_manifest


def _build_report_zh(run_manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    single_stage_mode = bool(run_manifest.get("stage2_all_cutoff_pass"))
    lines.append("# 單審查者官方 Batch single-stage 直審基線" if single_stage_mode else "# 單審查者官方 Batch 兩階段直審基線")
    lines.append("")
    lines.append(f"- `run_id`：`{run_manifest['run_id']}`")
    lines.append(f"- model：`{run_manifest['model']}`")
    lines.append(f"- reasoning_effort：`{run_manifest.get('reasoning_effort') or '未顯式設定'}`")
    lines.append(f"- endpoint：`{run_manifest['endpoint']}`")
    lines.append("")
    if single_stage_mode:
        lines.append("## Stage 1 指標")
        lines.append("")
        lines.append("- 此 run 為 single-stage direct-review；沒有 stage1 batch，也不計 stage1 指標。")
    else:
        lines.append("## Stage 1 指標")
        lines.append("")
        lines.append("| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for summary in run_manifest.get("summaries", []):
            lines.append(
                f"| `{summary['paper_id']}` | {summary['candidate_total']} | {summary['cutoff_pass_count']} | "
                f"{summary['stage2_selected_count']} | {summary['stage1_f1']:.4f} | {summary['delta_vs_current_stage1']:+.4f} | "
                f"{summary['stage1_precision']:.4f} | {summary['stage1_recall']:.4f} |"
            )
    lines.append("")
    lines.append("## Final 指標" if single_stage_mode else "## Combined 指標")
    lines.append("")
    lines.append("| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for summary in run_manifest.get("summaries", []):
        lines.append(
            f"| `{summary['paper_id']}` | {summary['candidate_total']} | {summary['cutoff_pass_count']} | "
            f"{summary['stage2_selected_count']} | {summary['reviewed_count']} | {summary['missing_count']} | "
            f"{summary['f1']:.4f} | {summary['delta_vs_current_combined']:+.4f} | "
            f"{summary['precision']:.4f} | {summary['recall']:.4f} |"
        )
    lines.append("")
    lines.append("## Phase Jobs")
    lines.append("")
    lines.append("| Phase | Request count | Batch status | Success | Failure | Missing |")
    lines.append("| --- | ---: | --- | ---: | ---: | ---: |")
    for phase in _phase_ids():
        job = run_manifest.get("phase_jobs", {}).get(phase, {})
        parsed = job.get("parsed_summary", {})
        lines.append(
            f"| `{phase}` | {int(job.get('request_count') or 0)} | `{job.get('batch_status')}` | "
            f"{int(parsed.get('success_count') or 0)} | {int(parsed.get('failure_count') or 0)} | {int(parsed.get('missing_count') or 0)} |"
        )
    return "\n".join(lines) + "\n"


def _model_preflight(model: str) -> str:
    _load_env_file()
    client = OpenAI()
    model_info = client.models.retrieve(model)
    return getattr(model_info, "id", None) or model


def _build_probe_model_output(*, stage_score: int) -> dict[str, Any]:
    return {
        "stage_score": stage_score,
        "decision_recommendation": decision_from_score(stage_score),
        "satisfied_inclusion_points": ["serialization probe inclusion"],
        "triggered_exclusion_points": [],
        "uncertain_points": [],
        "evidence_highlights": ["serialization probe evidence"],
        "decision_rationale": "serialization probe",
    }


def build_serialization_probe(phase: str) -> dict[str, Any]:
    config = _load_config()
    workflow_spec = _load_workflow_spec()
    prompt_assets = PromptAssets(workflow_spec)
    key_map = _load_candidate_key_map(
        BUNDLE_DIR / "smoke" / "smoke_candidates.json",
        selected_papers=["2307.05527", "2601.19926"],
    )
    response_model = build_direct_stage_response_model("ProbeDirectReviewOutput")
    if phase == "stage1_review":
        prep = _prepare_stage1_review_specs(
            run_id="serialization_probe",
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=["2307.05527"],
            key_map=key_map,
            max_records=None,
            reasoning_effort="low",
            write_audits=False,
        )
        spec = prep["specs"][0]
    elif phase == "stage2_review":
        temp_run_id = "serialization_probe"
        prep1 = _prepare_stage1_review_specs(
            run_id=temp_run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=["2601.19926"],
            key_map=key_map,
            max_records=None,
            reasoning_effort="low",
            write_audits=False,
        )
        spec1 = prep1["specs"][0]
        validator1 = build_direct_stage_validator(
            paper_id="2601.19926",
            stage="stage1",
            candidate_key=spec1.context["candidate_key"],
            candidate_title=spec1.context["candidate_title"],
        )
        sample_stage1 = _build_probe_model_output(stage_score=4)
        validator1(response_model.model_validate(sample_stage1))
        stage1_record = StageDirectReviewRecord.model_validate(
            {
                **sample_stage1,
                "paper_id": "2601.19926",
                "candidate_key": spec1.context["candidate_key"],
                "candidate_title": spec1.context["candidate_title"],
                "stage": "stage1",
                "workflow_arm": _workflow_arm(),
                "criteria_path": spec1.context["criteria_path"],
                "source_record_provenance": spec1.context["provenance"],
            }
        )
        write_json(_phase_output_path(temp_run_id, "2601.19926", "stage1_review"), [stage1_record.model_dump(mode="json")])
        prep = _prepare_stage2_review_specs(
            run_id=temp_run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=["2601.19926"],
            key_map=key_map,
            max_records=None,
            reasoning_effort="low",
            write_audits=False,
        )
        spec = prep["specs"][0]
    else:
        raise ValueError(f"unsupported phase: {phase}")

    runner = OpenAIBatchRunner(client=object(), poll_interval_sec=float(config["batch_poll_interval_sec"]))
    return runner.serialize_requests([spec], endpoint=str(config["endpoint"]))[0]


def main() -> int:
    config = _load_config()
    workflow_spec = _load_workflow_spec()
    parser = argparse.ArgumentParser(description="執行 single reviewer official-batch 2-stage direct-review baseline。")
    parser.add_argument("--mode", choices=["submit", "collect", "run"], required=True)
    parser.add_argument("--phase", choices=[*_phase_ids(), "all"], required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--papers", nargs="*", choices=list(config["papers"]), default=list(config["papers"]))
    parser.add_argument("--candidate-keys-file", type=Path, default=None)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--batch-poll-interval-sec", type=float, default=None)
    parser.add_argument("--batch-max-wait-minutes", type=float, default=None)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default="low")
    parser.add_argument("--stage2-all-cutoff-pass", action="store_true")
    args = parser.parse_args()

    if args.phase == "all" and args.mode in {"submit", "collect"}:
        raise SystemExit("--phase all 僅支援 --mode run；stage2_review 依賴 stage1_review 的 collect 結果。")
    if args.stage2_all_cutoff_pass and args.phase != "stage2_review":
        raise SystemExit("--stage2-all-cutoff-pass 只支援 --phase stage2_review。")

    config = _config_with_model_override(config, args.model)
    run_id = args.run_id or now_run_id()
    phases = _phase_ids() if args.phase == "all" else [args.phase]
    selected_papers = list(args.papers)
    key_map = _load_candidate_key_map(args.candidate_keys_file, selected_papers=selected_papers)
    prompt_assets = PromptAssets(workflow_spec)

    for phase in phases:
        if args.mode in {"submit", "run"}:
            _submit_phase(
                phase=phase,
                run_id=run_id,
                prompt_assets=prompt_assets,
                config=config,
                selected_papers=selected_papers,
                key_map=key_map,
                key_map_path=args.candidate_keys_file,
                max_records=args.max_records,
                reasoning_effort=args.reasoning_effort,
                stage2_all_cutoff_pass=args.stage2_all_cutoff_pass,
            )
        if args.mode in {"collect", "run"}:
            _collect_phase(
                phase=phase,
                run_id=run_id,
                prompt_assets=prompt_assets,
                config=config,
                selected_papers=selected_papers,
                key_map=key_map,
                max_records=args.max_records,
                reasoning_effort=args.reasoning_effort,
                batch_poll_interval_sec=args.batch_poll_interval_sec,
                batch_max_wait_minutes=args.batch_max_wait_minutes,
                stage2_all_cutoff_pass=args.stage2_all_cutoff_pass,
            )

    if args.mode in {"collect", "run"} and (args.phase == "all" or phases[-1] == _phase_ids()[-1]):
        _assemble_results_and_metrics(
            run_id=run_id,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            max_records=args.max_records,
            report_reasoning_effort=args.reasoning_effort,
            stage2_all_cutoff_pass=args.stage2_all_cutoff_pass,
        )
        print(f"[report] {_report_path(run_id)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
