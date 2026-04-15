#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

from experiment_lib import (  # noqa: E402
    append_jsonl,
    compute_auto_resolution_coverage,
    compute_metrics_from_rows,
    compute_verification_overturn_rate,
    decision_from_score,
    load_best_observed_single_reviewer,
    load_jsonl,
    parse_json_response_text,
    read_json,
    render_template,
    safe_text,
    select_snippet_pack,
    should_route_verification,
    stage_verdict,
    summarize_terminal_failures,
    write_json,
)
from render_summary import build_matrix_summary, render_matrix_summary_zh  # noqa: E402
from experiment_workflows import (  # noqa: E402
    SingleReviewerMergedFinalRow,
    SourceRecordProvenance,
    build_cutoff_review_row,
    build_direct_stage_prompt_context,
    build_direct_stage_response_model,
    build_direct_stage_review_record,
    build_direct_stage_validator,
    build_dynamic_stage_response_model,
    build_fulltext_resolution_audit,
    build_source_record_provenance,
    build_stage_prompt_context,
    build_stage_review_record,
    build_stage_validator,
    criteria_text_for_stage,
    custom_id,
    fulltext_payload_from_resolution,
    load_candidates,
    load_cutoff_result,
    load_criterion_asset,
    metadata_payload,
    now_run_id,
    relative_path,
)
from openai_batch_runner import build_json_schema_response_format  # noqa: E402
from vendor.src.utils.llm import OpenAIProvider  # noqa: E402


CONFIG_PATH = BUNDLE_DIR / "config" / "experiment_matrix.json"
SMOKE_KEYS_PATH = BUNDLE_DIR / "config" / "smoke_candidates.json"
TEMPLATE_DIR = BUNDLE_DIR / "templates"
SAMPLE_DIR = BUNDLE_DIR / "samples"


@dataclass
class PromptAssets:
    direct_stage1_template: str
    direct_stage2_template: str
    merged_stage1_template: str
    merged_stage2_template: str
    verification_template: str
    direct_stage1_hint: str
    direct_stage2_hint: str
    merged_stage1_hint: str
    merged_stage2_hint: str
    verification_hint: str


@dataclass
class RequestSpec:
    request_id: str
    arm_id: str
    phase_id: str
    phase_stage: str
    paper_id: str
    candidate_key: str
    prompt: str
    response_model: type[BaseModel]
    text_format: dict[str, Any]
    validator: Callable[[BaseModel], None] | None
    record_builder: Callable[[dict[str, Any]], dict[str, Any]]
    request_context: dict[str, Any]


def _load_config() -> dict[str, Any]:
    return read_json(CONFIG_PATH)


def _load_prompt_assets() -> PromptAssets:
    return PromptAssets(
        direct_stage1_template=(TEMPLATE_DIR / "01_stage1_direct_review_TEMPLATE.md").read_text(encoding="utf-8"),
        direct_stage2_template=(TEMPLATE_DIR / "02_stage2_direct_review_TEMPLATE.md").read_text(encoding="utf-8"),
        merged_stage1_template=(TEMPLATE_DIR / "01_stage1_merged_review_TEMPLATE.md").read_text(encoding="utf-8"),
        merged_stage2_template=(TEMPLATE_DIR / "02_stage2_merged_review_TEMPLATE.md").read_text(encoding="utf-8"),
        verification_template=(TEMPLATE_DIR / "03_verification_merged_review_TEMPLATE.md").read_text(encoding="utf-8"),
        direct_stage1_hint=(SAMPLE_DIR / "direct_stage1_review_output.sample.json").read_text(encoding="utf-8"),
        direct_stage2_hint=(SAMPLE_DIR / "direct_stage2_review_output.sample.json").read_text(encoding="utf-8"),
        merged_stage1_hint=(SAMPLE_DIR / "merged_stage1_review_output.sample.json").read_text(encoding="utf-8"),
        merged_stage2_hint=(SAMPLE_DIR / "merged_stage2_review_output.sample.json").read_text(encoding="utf-8"),
        verification_hint=(SAMPLE_DIR / "verification_review_output.sample.json").read_text(encoding="utf-8"),
    )


def _run_dir(run_id: str) -> Path:
    return BUNDLE_DIR / "runs" / run_id


def _arm_dir(run_id: str, arm_id: str) -> Path:
    return _run_dir(run_id) / "arms" / arm_id


def _paper_dir(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _arm_dir(run_id, arm_id) / "papers" / paper_id


def _run_manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / "run_manifest.json"


def _request_log_path(run_id: str) -> Path:
    return _run_dir(run_id) / "request_log.jsonl"


def _response_log_path(run_id: str) -> Path:
    return _run_dir(run_id) / "response_log.jsonl"


def _failure_log_path(run_id: str) -> Path:
    return _run_dir(run_id) / "failure_log.jsonl"


def _summary_path(run_id: str) -> Path:
    return _run_dir(run_id) / "SUMMARY_zh.md"


def _paper_stage1_review_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "stage1_review.json"


def _paper_stage2_review_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "stage2_review.json"


def _paper_verification_review_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "verification_review.json"


def _paper_cutoff_audit_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "cutoff_audit.json"


def _paper_fulltext_resolution_audit_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "fulltext_resolution_audit.json"


def _paper_stage1_results_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "stage1_results.json"


def _paper_final_results_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "final_results.json"


def _paper_stage1_metrics_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "stage1_metrics.json"


def _paper_combined_metrics_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "combined_metrics.json"


def _paper_stage2_selection_path(run_id: str, arm_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, arm_id, paper_id) / "selected_for_stage2.keys.txt"


def _serialize_key_map(key_map: dict[str, set[str]] | None) -> dict[str, list[str]] | None:
    if key_map is None:
        return None
    return {paper_id: sorted(keys) for paper_id, keys in key_map.items()}


def _selection_mode_for_resume(manifest: dict[str, Any], run_id: str) -> str:
    selection_mode = safe_text(manifest.get("selection_mode")).lower()
    if selection_mode in {"smoke", "full"}:
        return selection_mode
    return "smoke" if "smoke" in run_id.lower() else "full"


def _key_map_for_resume(manifest: dict[str, Any], run_id: str) -> dict[str, set[str]] | None:
    selection_mode = _selection_mode_for_resume(manifest, run_id)
    if selection_mode != "smoke":
        return None
    candidate_key_map = manifest.get("candidate_key_map")
    if isinstance(candidate_key_map, dict):
        return {
            safe_text(paper_id): {safe_text(key) for key in keys if safe_text(key)}
            for paper_id, keys in candidate_key_map.items()
            if safe_text(paper_id)
        }
    return _load_smoke_key_map()


def _should_skip_arm(manifest: dict[str, Any], arm_id: str, *, resume_mode: bool) -> bool:
    return resume_mode and safe_text(manifest.get("arm_status", {}).get(arm_id)) == "completed"


def _load_or_init_run_manifest(
    run_id: str,
    config: dict[str, Any],
    *,
    selection_mode: str,
    key_map: dict[str, set[str]] | None,
) -> dict[str, Any]:
    path = _run_manifest_path(run_id)
    if path.exists():
        payload = read_json(path)
        changed = False
        if "selection_mode" not in payload:
            payload["selection_mode"] = selection_mode
            changed = True
        if key_map is not None and "candidate_key_map" not in payload:
            payload["candidate_key_map"] = _serialize_key_map(key_map)
            changed = True
        if changed:
            write_json(path, payload)
        return payload
    payload = {
        "run_id": run_id,
        "bundle_dir": str(BUNDLE_DIR),
        "results_root": str(_run_dir(run_id)),
        "model": config["model"],
        "reasoning_effort": config["reasoning_effort"],
        "concurrency": config["concurrency"],
        "papers": config["papers"],
        "arms": [arm["id"] for arm in config["arms"]],
        "selection_mode": selection_mode,
        "candidate_key_map": _serialize_key_map(key_map),
        "arm_status": {},
    }
    write_json(path, payload)
    return payload


def _request_id(arm_id: str, phase_id: str, paper_id: str, candidate_key: str, *, source_phase: str | None = None) -> str:
    if source_phase:
        return f"{arm_id}::{phase_id}::{source_phase}::{paper_id}::{candidate_key}"
    return f"{arm_id}::{phase_id}::{paper_id}::{candidate_key}"


def _load_existing_response_rows(run_id: str) -> list[dict[str, Any]]:
    return load_jsonl(_response_log_path(run_id))


def _load_existing_failure_rows(run_id: str) -> list[dict[str, Any]]:
    return load_jsonl(_failure_log_path(run_id))


def _completed_request_ids(run_id: str) -> set[str]:
    return {safe_text(row.get("request_id")) for row in _load_existing_response_rows(run_id)}


def _terminal_failure_ids(run_id: str) -> set[str]:
    return {safe_text(row.get("request_id")) for row in _load_existing_failure_rows(run_id)}


def _load_paper_profile(paper_id: str) -> dict[str, Any]:
    return read_json(BUNDLE_DIR / "assets" / "paper_profiles" / f"{paper_id}.json")


def _criterion_asset_path(paper_id: str, stage: str) -> Path:
    return BUNDLE_DIR / "assets" / "merged" / f"{paper_id}.{stage}.json"


def _criteria_path(paper_id: str, stage: str) -> Path:
    if stage == "stage1":
        return REPO_ROOT / "criteria_stage1" / f"{paper_id}.json"
    return REPO_ROOT / "criteria_stage2" / f"{paper_id}.json"


def _metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _fulltext_root(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "mds"


def _cutoff_path(paper_id: str) -> Path:
    return REPO_ROOT / "cutoff_jsons" / f"{paper_id}.json"


def _runtime_prompts_path() -> Path:
    return REPO_ROOT / "scripts" / "screening" / "runtime_prompts" / "runtime_prompts.json"


def _load_smoke_key_map() -> dict[str, set[str]]:
    payload = read_json(SMOKE_KEYS_PATH)
    return {paper_id: {safe_text(item) for item in values} for paper_id, values in payload.items()}


def _load_gold_records(paper_id: str) -> list[dict[str, Any]]:
    return load_jsonl(_gold_path(paper_id))


def _load_stage_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = read_json(path)
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _rows_by_candidate_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {safe_text(row.get("candidate_key")): row for row in rows if safe_text(row.get("candidate_key"))}


def _verification_rows_by_source_phase(rows: list[dict[str, Any]], source_phase: str) -> dict[str, dict[str, Any]]:
    return {
        safe_text(row.get("candidate_key")): row
        for row in rows
        if safe_text(row.get("candidate_key")) and safe_text(row.get("verification_source_phase")) == source_phase
    }


def _paper_runtime_inputs(
    *,
    run_id: str,
    arm_id: str,
    paper_id: str,
    key_allowlist: set[str] | None,
) -> dict[str, Any]:
    records = load_candidates(_metadata_path(paper_id), key_allowlist=key_allowlist)
    resolution_by_key, resolution_audit = build_fulltext_resolution_audit(
        paper_id=paper_id,
        records=records,
        fulltext_root=_fulltext_root(paper_id),
        repo_root=REPO_ROOT,
    )
    cutoff_result = load_cutoff_result(records=records, cutoff_path=_cutoff_path(paper_id))
    write_json(_paper_cutoff_audit_path(run_id, arm_id, paper_id), cutoff_result["audit_payload"])
    write_json(_paper_fulltext_resolution_audit_path(run_id, arm_id, paper_id), resolution_audit)
    return {
        "records": records,
        "cutoff_result": cutoff_result,
        "resolution_by_key": resolution_by_key,
    }


def _build_body(
    *,
    model: str,
    prompt: str,
    response_model: type[BaseModel],
    schema_name: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(response_model, schema_name=schema_name),
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    return body


def _responses_text_format(*, response_model: type[BaseModel], schema_name: str) -> dict[str, Any]:
    response_format = build_json_schema_response_format(response_model, schema_name=schema_name)
    json_schema = response_format["json_schema"]
    return {
        "type": "json_schema",
        "name": json_schema["name"],
        "strict": True,
        "schema": json_schema["schema"],
    }


def _schema_name(base: str, paper_id: str) -> str:
    return f"{base}_{paper_id.replace('.', '_')}"


def _direct_record_builder(
    *,
    paper_id: str,
    candidate_key: str,
    candidate_title: str,
    stage: str,
    arm_id: str,
    criteria_path: Path,
    provenance: SourceRecordProvenance,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def build(parsed: dict[str, Any]) -> dict[str, Any]:
        record = build_direct_stage_review_record(
            model_output=parsed,
            paper_id=paper_id,
            candidate_key=candidate_key,
            candidate_title=candidate_title,
            stage=stage,
            workflow_arm=arm_id,
            criteria_path=str(criteria_path.relative_to(REPO_ROOT)),
            provenance=provenance,
        )
        return record.model_dump(mode="json")

    return build


def _merged_record_builder(
    *,
    paper_id: str,
    candidate_key: str,
    candidate_title: str,
    stage: str,
    arm_id: str,
    asset_path: Path,
    criteria_path: Path,
    provenance: SourceRecordProvenance,
    verification_source_phase: str | None = None,
    verification_input_kind: str | None = None,
    routing_decision: dict[str, Any] | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def build(parsed: dict[str, Any]) -> dict[str, Any]:
        record = build_stage_review_record(
            model_output=parsed,
            paper_id=paper_id,
            candidate_key=candidate_key,
            candidate_title=candidate_title,
            stage=stage,
            workflow_arm=arm_id,
            qa_asset_path=str(asset_path.relative_to(REPO_ROOT)),
            criteria_path=str(criteria_path.relative_to(REPO_ROOT)),
            provenance=provenance,
        ).model_dump(mode="json")
        if verification_source_phase:
            record["verification_source_phase"] = verification_source_phase
        if verification_input_kind:
            record["verification_input_kind"] = verification_input_kind
        if routing_decision is not None:
            record["routing_decision"] = routing_decision
        return record

    return build


def _load_effective_stage1_map(run_id: str, arm_id: str, paper_id: str) -> dict[str, dict[str, Any]]:
    stage1 = _rows_by_candidate_key(_load_stage_rows(_paper_stage1_review_path(run_id, arm_id, paper_id)))
    verification = _verification_rows_by_source_phase(_load_stage_rows(_paper_verification_review_path(run_id, arm_id, paper_id)), "stage1_review")
    merged = dict(stage1)
    merged.update(verification)
    return merged


def _load_effective_stage2_map(run_id: str, arm_id: str, paper_id: str) -> dict[str, dict[str, Any]]:
    stage2 = _rows_by_candidate_key(_load_stage_rows(_paper_stage2_review_path(run_id, arm_id, paper_id)))
    verification = _verification_rows_by_source_phase(_load_stage_rows(_paper_verification_review_path(run_id, arm_id, paper_id)), "stage2_review")
    merged = dict(stage2)
    merged.update(verification)
    return merged


def _load_original_stage_maps(run_id: str, arm_id: str, paper_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    return (
        _rows_by_candidate_key(_load_stage_rows(_paper_stage1_review_path(run_id, arm_id, paper_id))),
        _rows_by_candidate_key(_load_stage_rows(_paper_stage2_review_path(run_id, arm_id, paper_id))),
    )


def _prepare_stage1_direct_requests(
    *,
    run_id: str,
    arm_id: str,
    paper_id: str,
    key_allowlist: set[str] | None,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
) -> list[RequestSpec]:
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    criteria_path = _criteria_path(paper_id, "stage1")
    criteria_payload = criteria_text_for_stage(criteria_path)
    response_model = build_direct_stage_response_model(_schema_name("DirectStage1", paper_id))
    specs: list[RequestSpec] = []
    for record in runtime["cutoff_result"]["kept_records"]:
        key = safe_text(record.get("key"))
        title = safe_text(record.get("title") or record.get("query_title"))
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        context = build_direct_stage_prompt_context(
            stage="stage1",
            workflow_arm=arm_id,
            paper_id=paper_id,
            candidate_key=key,
            candidate_title=title,
            criteria_payload=criteria_payload,
            metadata=metadata_payload(record),
            response_schema_hint=prompt_assets.direct_stage1_hint,
            provenance=provenance,
        )
        prompt = render_template(prompt_assets.direct_stage1_template, context)
        request_id = _request_id(arm_id, "stage1_review", paper_id, key)
        specs.append(
            RequestSpec(
                request_id=request_id,
                arm_id=arm_id,
                phase_id="stage1_review",
                phase_stage="stage1",
                paper_id=paper_id,
                candidate_key=key,
                prompt=prompt,
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("DirectStage1", paper_id)),
                validator=build_direct_stage_validator(paper_id=paper_id, stage="stage1", candidate_key=key, candidate_title=title),
                record_builder=_direct_record_builder(
                    paper_id=paper_id,
                    candidate_key=key,
                    candidate_title=title,
                    stage="stage1",
                    arm_id=arm_id,
                    criteria_path=criteria_path,
                    provenance=provenance,
                ),
                request_context={
                    "candidate_title": title,
                    "paper_id": paper_id,
                    "phase": "stage1_review",
                },
            )
        )
    return specs


def _prepare_stage1_merged_requests(
    *,
    run_id: str,
    arm_id: str,
    paper_id: str,
    key_allowlist: set[str] | None,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
) -> list[RequestSpec]:
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    criteria_path = _criteria_path(paper_id, "stage1")
    asset_path = _criterion_asset_path(paper_id, "stage1")
    asset = load_criterion_asset(asset_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_stage_response_model(_schema_name("MergedStage1", paper_id), criterion_ids=expected_ids)
    criteria_payload = criteria_text_for_stage(criteria_path)
    specs: list[RequestSpec] = []
    for record in runtime["cutoff_result"]["kept_records"]:
        key = safe_text(record.get("key"))
        title = safe_text(record.get("title") or record.get("query_title"))
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        context = build_stage_prompt_context(
            stage="stage1",
            workflow_arm=arm_id,
            paper_id=paper_id,
            candidate_key=key,
            candidate_title=title,
            asset=asset,
            criteria_payload=criteria_payload,
            metadata=metadata_payload(record),
            response_schema_hint=prompt_assets.merged_stage1_hint,
            provenance=provenance,
        )
        prompt = render_template(prompt_assets.merged_stage1_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id(arm_id, "stage1_review", paper_id, key),
                arm_id=arm_id,
                phase_id="stage1_review",
                phase_stage="stage1",
                paper_id=paper_id,
                candidate_key=key,
                prompt=prompt,
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("MergedStage1", paper_id)),
                validator=build_stage_validator(
                    paper_id=paper_id,
                    stage="stage1",
                    candidate_key=key,
                    candidate_title=title,
                    expected_criterion_ids=expected_ids,
                ),
                record_builder=_merged_record_builder(
                    paper_id=paper_id,
                    candidate_key=key,
                    candidate_title=title,
                    stage="stage1",
                    arm_id=arm_id,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                ),
                request_context={"candidate_title": title, "paper_id": paper_id, "phase": "stage1_review"},
            )
        )
    return specs


def _prepare_stage1_verification_requests(
    *,
    run_id: str,
    arm_id: str,
    paper_id: str,
    key_allowlist: set[str] | None,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
) -> list[RequestSpec]:
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    original_stage1 = _rows_by_candidate_key(_load_stage_rows(_paper_stage1_review_path(run_id, arm_id, paper_id)))
    existing_verification = _verification_rows_by_source_phase(_load_stage_rows(_paper_verification_review_path(run_id, arm_id, paper_id)), "stage1_review")
    criteria_path = _criteria_path(paper_id, "stage1")
    asset_path = _criterion_asset_path(paper_id, "stage1")
    asset = load_criterion_asset(asset_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_stage_response_model(_schema_name("VerificationStage1", paper_id), criterion_ids=expected_ids)
    criteria_payload = criteria_text_for_stage(criteria_path)
    paper_profile = _load_paper_profile(paper_id)
    specs: list[RequestSpec] = []
    for record in runtime["cutoff_result"]["kept_records"]:
        key = safe_text(record.get("key"))
        if key not in original_stage1 or key in existing_verification:
            continue
        stage1_record = original_stage1[key]
        routing_decision = should_route_verification(
            paper_id=paper_id,
            stage="stage1",
            review_output=stage1_record,
            paper_profile=paper_profile,
        )
        if not routing_decision["should_route"]:
            continue
        resolution = runtime["resolution_by_key"][key]
        title = safe_text(record.get("title") or record.get("query_title"))
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        context = {
            "WORKFLOW_ARM": arm_id,
            "PAPER_ID": paper_id,
            "CANDIDATE_KEY": key,
            "VERIFICATION_SOURCE_PHASE": "stage1_review",
            "VERIFICATION_INPUT_KIND": "title_abstract",
            "TOPIC_DEFINITION": asset.topic_definition,
            "DECISION_POLICY": asset.decision_policy,
            "PAPER_PROFILE_JSON": json.dumps(paper_profile, ensure_ascii=False, indent=2),
            "ROUTING_DECISION_JSON": json.dumps(routing_decision, ensure_ascii=False, indent=2),
            "QA_ASSET_JSON": json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "STAGE_CRITERIA_JSON_CONTENT": criteria_payload,
            "METADATA_JSON": json.dumps(metadata_payload(record), ensure_ascii=False, indent=2),
            "PRIOR_REVIEW_JSON": json.dumps(stage1_record, ensure_ascii=False, indent=2),
            "SOURCE_RECORD_PROVENANCE_JSON": json.dumps(provenance.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "VERIFICATION_EVIDENCE_TEXT": f"Title: {title}\n\nAbstract:\n{safe_text(record.get('abstract'))}",
            "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.verification_hint,
        }
        prompt = render_template(prompt_assets.verification_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id(arm_id, "verification_review", paper_id, key, source_phase="stage1_review"),
                arm_id=arm_id,
                phase_id="verification_review",
                phase_stage="stage1",
                paper_id=paper_id,
                candidate_key=key,
                prompt=prompt,
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("VerificationStage1", paper_id)),
                validator=build_stage_validator(
                    paper_id=paper_id,
                    stage="stage1",
                    candidate_key=key,
                    candidate_title=title,
                    expected_criterion_ids=expected_ids,
                ),
                record_builder=_merged_record_builder(
                    paper_id=paper_id,
                    candidate_key=key,
                    candidate_title=title,
                    stage="stage1",
                    arm_id=arm_id,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                    verification_source_phase="stage1_review",
                    verification_input_kind="title_abstract",
                    routing_decision=routing_decision,
                ),
                request_context={"candidate_title": title, "paper_id": paper_id, "phase": "verification_review", "verification_source_phase": "stage1_review"},
            )
        )
    return specs


def _effective_stage1_decision_map(run_id: str, arm_id: str, paper_id: str) -> dict[str, str]:
    return {
        key: decision_from_score(int(row["stage_score"]))
        for key, row in _load_effective_stage1_map(run_id, arm_id, paper_id).items()
    }


def _prepare_stage2_direct_requests(
    *,
    run_id: str,
    arm_id: str,
    paper_id: str,
    key_allowlist: set[str] | None,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
) -> list[RequestSpec]:
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    stage1_decisions = _effective_stage1_decision_map(run_id, arm_id, paper_id)
    stage1_rows = _load_effective_stage1_map(run_id, arm_id, paper_id)
    criteria_path = _criteria_path(paper_id, "stage2")
    criteria_payload = criteria_text_for_stage(criteria_path)
    response_model = build_direct_stage_response_model(_schema_name("DirectStage2", paper_id))
    selected_keys: list[str] = []
    specs: list[RequestSpec] = []
    for record in runtime["records"]:
        key = safe_text(record.get("key"))
        if stage1_decisions.get(key) not in {"include", "maybe"}:
            continue
        resolution = runtime["resolution_by_key"][key]
        if resolution["resolution_status"] not in {"exact", "normalized"}:
            continue
        selected_keys.append(key)
        fulltext_text, _ = fulltext_payload_from_resolution(
            resolution,
            repo_root=REPO_ROOT,
            head_chars=int(config["fulltext_inline_head_chars"]),
            tail_chars=int(config["fulltext_inline_tail_chars"]),
        )
        title = safe_text(record.get("title") or record.get("query_title"))
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        context = build_direct_stage_prompt_context(
            stage="stage2",
            workflow_arm=arm_id,
            paper_id=paper_id,
            candidate_key=key,
            candidate_title=title,
            criteria_payload=criteria_payload,
            metadata=metadata_payload(record),
            response_schema_hint=prompt_assets.direct_stage2_hint,
            provenance=provenance,
            prior_stage_review=stage1_rows[key],
            fulltext_resolution=resolution,
            fulltext_text=fulltext_text,
        )
        prompt = render_template(prompt_assets.direct_stage2_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id(arm_id, "stage2_review", paper_id, key),
                arm_id=arm_id,
                phase_id="stage2_review",
                phase_stage="stage2",
                paper_id=paper_id,
                candidate_key=key,
                prompt=prompt,
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("DirectStage2", paper_id)),
                validator=build_direct_stage_validator(paper_id=paper_id, stage="stage2", candidate_key=key, candidate_title=title),
                record_builder=_direct_record_builder(
                    paper_id=paper_id,
                    candidate_key=key,
                    candidate_title=title,
                    stage="stage2",
                    arm_id=arm_id,
                    criteria_path=criteria_path,
                    provenance=provenance,
                ),
                request_context={"candidate_title": title, "paper_id": paper_id, "phase": "stage2_review"},
            )
        )
    _paper_stage2_selection_path(run_id, arm_id, paper_id).write_text("\n".join(selected_keys) + ("\n" if selected_keys else ""), encoding="utf-8")
    return specs


def _prepare_stage2_merged_requests(
    *,
    run_id: str,
    arm_id: str,
    paper_id: str,
    key_allowlist: set[str] | None,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
) -> list[RequestSpec]:
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    stage1_decisions = _effective_stage1_decision_map(run_id, arm_id, paper_id)
    stage1_rows = _load_effective_stage1_map(run_id, arm_id, paper_id)
    criteria_path = _criteria_path(paper_id, "stage2")
    asset_path = _criterion_asset_path(paper_id, "stage2")
    asset = load_criterion_asset(asset_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_stage_response_model(_schema_name("MergedStage2", paper_id), criterion_ids=expected_ids)
    criteria_payload = criteria_text_for_stage(criteria_path)
    selected_keys: list[str] = []
    specs: list[RequestSpec] = []
    for record in runtime["records"]:
        key = safe_text(record.get("key"))
        if stage1_decisions.get(key) not in {"include", "maybe"}:
            continue
        resolution = runtime["resolution_by_key"][key]
        if resolution["resolution_status"] not in {"exact", "normalized"}:
            continue
        selected_keys.append(key)
        fulltext_text, _ = fulltext_payload_from_resolution(
            resolution,
            repo_root=REPO_ROOT,
            head_chars=int(config["fulltext_inline_head_chars"]),
            tail_chars=int(config["fulltext_inline_tail_chars"]),
        )
        title = safe_text(record.get("title") or record.get("query_title"))
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        context = build_stage_prompt_context(
            stage="stage2",
            workflow_arm=arm_id,
            paper_id=paper_id,
            candidate_key=key,
            candidate_title=title,
            asset=asset,
            criteria_payload=criteria_payload,
            metadata=metadata_payload(record),
            response_schema_hint=prompt_assets.merged_stage2_hint,
            provenance=provenance,
            prior_stage_review=stage1_rows[key],
            fulltext_resolution=resolution,
            fulltext_text=fulltext_text,
        )
        prompt = render_template(prompt_assets.merged_stage2_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id(arm_id, "stage2_review", paper_id, key),
                arm_id=arm_id,
                phase_id="stage2_review",
                phase_stage="stage2",
                paper_id=paper_id,
                candidate_key=key,
                prompt=prompt,
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("MergedStage2", paper_id)),
                validator=build_stage_validator(
                    paper_id=paper_id,
                    stage="stage2",
                    candidate_key=key,
                    candidate_title=title,
                    expected_criterion_ids=expected_ids,
                ),
                record_builder=_merged_record_builder(
                    paper_id=paper_id,
                    candidate_key=key,
                    candidate_title=title,
                    stage="stage2",
                    arm_id=arm_id,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                ),
                request_context={"candidate_title": title, "paper_id": paper_id, "phase": "stage2_review"},
            )
        )
    _paper_stage2_selection_path(run_id, arm_id, paper_id).write_text("\n".join(selected_keys) + ("\n" if selected_keys else ""), encoding="utf-8")
    return specs


def _verification_evidence_text(
    *,
    arm_id: str,
    paper_id: str,
    record: dict[str, Any],
    stage2_review: dict[str, Any],
    resolution: dict[str, Any],
    paper_profile: dict[str, Any],
    config: dict[str, Any],
    use_targeted_retrieval: bool,
) -> tuple[str, str]:
    title = safe_text(record.get("title") or record.get("query_title"))
    abstract = safe_text(record.get("abstract"))
    if not use_targeted_retrieval:
        fulltext_text, _ = fulltext_payload_from_resolution(
            resolution,
            repo_root=REPO_ROOT,
            head_chars=int(config["fulltext_inline_head_chars"]),
            tail_chars=int(config["fulltext_inline_tail_chars"]),
        )
        return f"Title: {title}\n\nAbstract:\n{abstract}\n\nFull text:\n{fulltext_text}", "head_tail"
    resolved_path = resolution.get("resolved_path")
    if not resolved_path:
        fulltext_text, _ = fulltext_payload_from_resolution(
            resolution,
            repo_root=REPO_ROOT,
            head_chars=int(config["fulltext_inline_head_chars"]),
            tail_chars=int(config["fulltext_inline_tail_chars"]),
        )
        return f"Title: {title}\n\nAbstract:\n{abstract}\n\nFull text:\n{fulltext_text}", "head_tail"
    raw_text = (REPO_ROOT / str(resolved_path)).read_text(encoding="utf-8", errors="ignore")
    snippet_text, _meta = select_snippet_pack(
        fulltext_text=raw_text,
        prior_review_output=stage2_review,
        paper_profile=paper_profile,
        max_chars=int(config["retrieval_snippet_max_chars"]),
    )
    return f"Title: {title}\n\nAbstract:\n{abstract}\n\nSnippet pack:\n{snippet_text}", "snippet_pack"


def _prepare_stage2_verification_requests(
    *,
    run_id: str,
    arm_id: str,
    paper_id: str,
    key_allowlist: set[str] | None,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    use_targeted_retrieval: bool,
) -> list[RequestSpec]:
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    original_stage2 = _rows_by_candidate_key(_load_stage_rows(_paper_stage2_review_path(run_id, arm_id, paper_id)))
    existing_verification = _verification_rows_by_source_phase(_load_stage_rows(_paper_verification_review_path(run_id, arm_id, paper_id)), "stage2_review")
    criteria_path = _criteria_path(paper_id, "stage2")
    asset_path = _criterion_asset_path(paper_id, "stage2")
    asset = load_criterion_asset(asset_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_stage_response_model(_schema_name("VerificationStage2", paper_id), criterion_ids=expected_ids)
    criteria_payload = criteria_text_for_stage(criteria_path)
    paper_profile = _load_paper_profile(paper_id)
    specs: list[RequestSpec] = []
    for record in runtime["records"]:
        key = safe_text(record.get("key"))
        if key not in original_stage2 or key in existing_verification:
            continue
        stage2_record = original_stage2[key]
        routing_decision = should_route_verification(
            paper_id=paper_id,
            stage="stage2",
            review_output=stage2_record,
            paper_profile=paper_profile,
        )
        if not routing_decision["should_route"]:
            continue
        resolution = runtime["resolution_by_key"][key]
        title = safe_text(record.get("title") or record.get("query_title"))
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        evidence_text, input_kind = _verification_evidence_text(
            arm_id=arm_id,
            paper_id=paper_id,
            record=record,
            stage2_review=stage2_record,
            resolution=resolution,
            paper_profile=paper_profile,
            config=config,
            use_targeted_retrieval=use_targeted_retrieval,
        )
        context = {
            "WORKFLOW_ARM": arm_id,
            "PAPER_ID": paper_id,
            "CANDIDATE_KEY": key,
            "VERIFICATION_SOURCE_PHASE": "stage2_review",
            "VERIFICATION_INPUT_KIND": input_kind,
            "TOPIC_DEFINITION": asset.topic_definition,
            "DECISION_POLICY": asset.decision_policy,
            "PAPER_PROFILE_JSON": json.dumps(paper_profile, ensure_ascii=False, indent=2),
            "ROUTING_DECISION_JSON": json.dumps(routing_decision, ensure_ascii=False, indent=2),
            "QA_ASSET_JSON": json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "STAGE_CRITERIA_JSON_CONTENT": criteria_payload,
            "METADATA_JSON": json.dumps(metadata_payload(record), ensure_ascii=False, indent=2),
            "PRIOR_REVIEW_JSON": json.dumps(stage2_record, ensure_ascii=False, indent=2),
            "SOURCE_RECORD_PROVENANCE_JSON": json.dumps(provenance.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "VERIFICATION_EVIDENCE_TEXT": evidence_text,
            "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.verification_hint,
        }
        prompt = render_template(prompt_assets.verification_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id(arm_id, "verification_review", paper_id, key, source_phase="stage2_review"),
                arm_id=arm_id,
                phase_id="verification_review",
                phase_stage="stage2",
                paper_id=paper_id,
                candidate_key=key,
                prompt=prompt,
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("VerificationStage2", paper_id)),
                validator=build_stage_validator(
                    paper_id=paper_id,
                    stage="stage2",
                    candidate_key=key,
                    candidate_title=title,
                    expected_criterion_ids=expected_ids,
                ),
                record_builder=_merged_record_builder(
                    paper_id=paper_id,
                    candidate_key=key,
                    candidate_title=title,
                    stage="stage2",
                    arm_id=arm_id,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                    verification_source_phase="stage2_review",
                    verification_input_kind=input_kind,
                    routing_decision=routing_decision,
                ),
                request_context={"candidate_title": title, "paper_id": paper_id, "phase": "verification_review", "verification_source_phase": "stage2_review"},
            )
        )
    return specs


async def _run_request(
    *,
    provider: OpenAIProvider,
    spec: RequestSpec,
    run_id: str,
    model: str,
    reasoning_effort: str,
    max_attempts: int,
) -> None:
    for attempt in range(1, max_attempts + 1):
        append_jsonl(
            _request_log_path(run_id),
            {
                "request_id": spec.request_id,
                "arm_id": spec.arm_id,
                "phase_id": spec.phase_id,
                "paper_id": spec.paper_id,
                "candidate_key": spec.candidate_key,
                "attempt": attempt,
                "prompt_chars": len(spec.prompt),
            },
        )
        try:
            normalized_messages = provider._normalize_messages([{"role": "user", "content": spec.prompt}])  # noqa: SLF001

            async def _call() -> Any:
                return await provider._async_client.responses.create(  # noqa: SLF001
                    model=model,
                    input=normalized_messages,
                    text={"format": spec.text_format},
                    reasoning={"effort": reasoning_effort},
                    metadata={
                        "request_id": spec.request_id,
                        "arm_id": spec.arm_id,
                        "phase_id": spec.phase_id,
                        "paper_id": spec.paper_id,
                    },
                )

            result = await provider._execute_with_retry_async(  # noqa: SLF001
                _call,
                model=model,
                mode="async",
                metadata={
                    "request_id": spec.request_id,
                    "arm_id": spec.arm_id,
                    "phase_id": spec.phase_id,
                    "paper_id": spec.paper_id,
                },
            )
            parsed_payload = parse_json_response_text(result.content)
            parsed_model = spec.response_model.model_validate(parsed_payload)
            if spec.validator is not None:
                spec.validator(parsed_model)
            record = spec.record_builder(parsed_model.model_dump(mode="json"))
            append_jsonl(
                _response_log_path(run_id),
                {
                    "request_id": spec.request_id,
                    "arm_id": spec.arm_id,
                    "phase_id": spec.phase_id,
                    "phase_stage": spec.phase_stage,
                    "paper_id": spec.paper_id,
                    "candidate_key": spec.candidate_key,
                    "parsed": parsed_model.model_dump(mode="json"),
                    "assistant_text": result.content,
                    "record": record,
                    "usage": {
                        "provider": result.usage.provider,
                        "model": result.usage.model,
                        "mode": result.usage.mode,
                        "input_tokens": result.usage.input_tokens,
                        "output_tokens": result.usage.output_tokens,
                        "cost": result.usage.cost,
                    },
                    "context": spec.request_context,
                },
            )
            return
        except Exception as exc:  # noqa: BLE001
            if attempt >= max_attempts:
                append_jsonl(
                    _failure_log_path(run_id),
                    {
                        "request_id": spec.request_id,
                        "arm_id": spec.arm_id,
                        "phase_id": spec.phase_id,
                        "phase_stage": spec.phase_stage,
                        "paper_id": spec.paper_id,
                        "candidate_key": spec.candidate_key,
                        "status": "terminal_failure",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "attempts": attempt,
                        "context": spec.request_context,
                    },
                )


async def _execute_specs(
    *,
    run_id: str,
    specs: list[RequestSpec],
    config: dict[str, Any],
) -> None:
    completed = _completed_request_ids(run_id)
    failed = _terminal_failure_ids(run_id)
    pending = [spec for spec in specs if spec.request_id not in completed and spec.request_id not in failed]
    if not pending:
        return
    provider = OpenAIProvider()
    semaphore = asyncio.Semaphore(int(config["concurrency"]))

    async def worker(spec: RequestSpec) -> None:
        async with semaphore:
            await _run_request(
                provider=provider,
                spec=spec,
                run_id=run_id,
                model=str(config["model"]),
                reasoning_effort=str(config["reasoning_effort"]),
                max_attempts=int(config["max_attempts_per_request"]),
            )

    await asyncio.gather(*(worker(spec) for spec in pending))


def _materialize_phase_outputs(run_id: str, arm_id: str, papers: list[str]) -> None:
    rows = _load_existing_response_rows(run_id)
    for paper_id in papers:
        stage1 = sorted(
            [row["record"] for row in rows if safe_text(row.get("arm_id")) == arm_id and safe_text(row.get("paper_id")) == paper_id and safe_text(row.get("phase_id")) == "stage1_review"],
            key=lambda item: safe_text(item.get("candidate_key")),
        )
        stage2 = sorted(
            [row["record"] for row in rows if safe_text(row.get("arm_id")) == arm_id and safe_text(row.get("paper_id")) == paper_id and safe_text(row.get("phase_id")) == "stage2_review"],
            key=lambda item: safe_text(item.get("candidate_key")),
        )
        verification = sorted(
            [row["record"] for row in rows if safe_text(row.get("arm_id")) == arm_id and safe_text(row.get("paper_id")) == paper_id and safe_text(row.get("phase_id")) == "verification_review"],
            key=lambda item: (safe_text(item.get("verification_source_phase")), safe_text(item.get("candidate_key"))),
        )
        write_json(_paper_stage1_review_path(run_id, arm_id, paper_id), stage1)
        write_json(_paper_stage2_review_path(run_id, arm_id, paper_id), stage2)
        write_json(_paper_verification_review_path(run_id, arm_id, paper_id), verification)


def _failure_lookup(run_id: str, arm_id: str, paper_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in _load_existing_failure_rows(run_id):
        if safe_text(row.get("arm_id")) != arm_id or safe_text(row.get("paper_id")) != paper_id:
            continue
        lookup[(safe_text(row.get("phase_id")), safe_text(row.get("candidate_key")))] = row
    return lookup


def _build_error_row(
    *,
    paper_id: str,
    arm_id: str,
    record: dict[str, Any],
    provenance: SourceRecordProvenance,
    review_state: str,
    failed_phase: str,
    review_output: dict[str, Any] | None,
) -> dict[str, Any]:
    row = SingleReviewerMergedFinalRow(
        key=safe_text(record.get("key")),
        title=safe_text(record.get("title") or record.get("query_title")),
        paper_id=paper_id,
        workflow_arm=arm_id,
        stage_model=arm_id,
        review_state=review_state,
        review_skipped=False,
        failed_phase=failed_phase,
        discard_reason=review_state,
        final_verdict=f"maybe (review_state:{review_state})",
        source_record_provenance=provenance,
        review_output=review_output,
    )
    return row.model_dump(mode="json")


def _build_stage1_rows_and_metrics(run_id: str, arm_id: str, paper_id: str) -> dict[str, Any]:
    key_allowlist = None
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    failures = _failure_lookup(run_id, arm_id, paper_id)
    stage1_rows = _load_effective_stage1_map(run_id, arm_id, paper_id)
    original_stage1, _ = _load_original_stage_maps(run_id, arm_id, paper_id)
    verification_rows = _verification_rows_by_source_phase(_load_stage_rows(_paper_verification_review_path(run_id, arm_id, paper_id)), "stage1_review")

    rows: list[dict[str, Any]] = []
    for record in runtime["records"]:
        key = safe_text(record.get("key"))
        decision = runtime["cutoff_result"]["decisions_by_key"][key]
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=_criteria_path(paper_id, "stage1"),
            repo_root=REPO_ROOT,
        )
        if not decision["cutoff_pass"]:
            rows.append(
                build_cutoff_review_row(
                    paper_id=paper_id,
                    workflow_arm=arm_id,
                    stage_model=arm_id,
                    record=record,
                    decision=decision,
                ).model_dump(mode="json")
            )
            continue
        if key not in stage1_rows:
            failure = failures.get(("stage1_review", key)) or failures.get(("verification_review", key))
            rows.append(
                _build_error_row(
                    paper_id=paper_id,
                    arm_id=arm_id,
                    record=record,
                    provenance=provenance,
                    review_state="terminal_failure",
                    failed_phase=safe_text((failure or {}).get("phase_id")) or "stage1_review",
                    review_output=failure,
                )
            )
            continue
        effective = stage1_rows[key]
        original = original_stage1.get(key)
        final_stage_name = "stage1_verification" if key in verification_rows and original and decision_from_score(int(original["stage_score"])) != decision_from_score(int(effective["stage_score"])) else "stage1"
        rows.append(
            SingleReviewerMergedFinalRow(
                key=key,
                title=safe_text(record.get("title") or record.get("query_title")),
                paper_id=paper_id,
                workflow_arm=arm_id,
                stage_model=arm_id,
                review_state="reviewed",
                review_skipped=False,
                final_verdict=stage_verdict(final_stage_name, int(effective["stage_score"])),
                stage1_stage_score=int(effective["stage_score"]),
                stage1_decision_recommendation=decision_from_score(int(effective["stage_score"])),
                stage1_review_path=relative_path(_paper_stage1_review_path(run_id, arm_id, paper_id), REPO_ROOT),
                source_record_provenance=SourceRecordProvenance.model_validate(effective["source_record_provenance"]),
                review_output={
                    "stage1_review": original or effective,
                    "stage1_verification": verification_rows.get(key),
                },
                fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                fulltext_resolution_status=resolution["resolution_status"],
            ).model_dump(mode="json")
        )
    write_json(_paper_stage1_results_path(run_id, arm_id, paper_id), rows)
    metrics = compute_metrics_from_rows(results=rows, gold_records=_load_gold_records(paper_id))
    route_keys = set(verification_rows.keys())
    overturn_keys = {
        key
        for key in route_keys
        if key in original_stage1 and key in stage1_rows and decision_from_score(int(original_stage1[key]["stage_score"])) != decision_from_score(int(stage1_rows[key]["stage_score"]))
    }
    metrics_payload = {
        "paper_id": paper_id,
        "arm_id": arm_id,
        "stage": "stage1",
        "metrics": metrics,
        "auto_resolution_coverage": compute_auto_resolution_coverage(total_rows=runtime["cutoff_result"]["audit_payload"]["candidate_total_after_cutoff"], verification_rows=len(route_keys)),
        "verification_route_rate": (len(route_keys) / runtime["cutoff_result"]["audit_payload"]["candidate_total_after_cutoff"]) if runtime["cutoff_result"]["audit_payload"]["candidate_total_after_cutoff"] else 0.0,
        "verification_overturn_rate": compute_verification_overturn_rate(verification_rows=len(route_keys), overturned_rows=len(overturn_keys)),
    }
    write_json(_paper_stage1_metrics_path(run_id, arm_id, paper_id), metrics_payload)
    return metrics_payload


def _build_combined_rows_and_metrics(run_id: str, arm_id: str, paper_id: str) -> dict[str, Any]:
    key_allowlist = None
    runtime = _paper_runtime_inputs(run_id=run_id, arm_id=arm_id, paper_id=paper_id, key_allowlist=key_allowlist)
    failures = _failure_lookup(run_id, arm_id, paper_id)
    stage1_rows = _load_effective_stage1_map(run_id, arm_id, paper_id)
    stage2_rows = _load_effective_stage2_map(run_id, arm_id, paper_id)
    original_stage1, original_stage2 = _load_original_stage_maps(run_id, arm_id, paper_id)
    verification_rows = _load_stage_rows(_paper_verification_review_path(run_id, arm_id, paper_id))
    verification_stage1 = _verification_rows_by_source_phase(verification_rows, "stage1_review")
    verification_stage2 = _verification_rows_by_source_phase(verification_rows, "stage2_review")

    rows: list[dict[str, Any]] = []
    reviewed_count = 0
    missing_count = 0
    for record in runtime["records"]:
        key = safe_text(record.get("key"))
        decision = runtime["cutoff_result"]["decisions_by_key"][key]
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=paper_id,
            resolution=resolution,
            metadata_path=_metadata_path(paper_id),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=_criteria_path(paper_id, "stage1"),
            repo_root=REPO_ROOT,
        )
        if not decision["cutoff_pass"]:
            rows.append(
                build_cutoff_review_row(
                    paper_id=paper_id,
                    workflow_arm=arm_id,
                    stage_model=arm_id,
                    record=record,
                    decision=decision,
                ).model_dump(mode="json")
            )
            continue
        if key not in stage1_rows:
            failure = failures.get(("stage1_review", key)) or failures.get(("verification_review", key))
            rows.append(
                _build_error_row(
                    paper_id=paper_id,
                    arm_id=arm_id,
                    record=record,
                    provenance=provenance,
                    review_state="terminal_failure",
                    failed_phase=safe_text((failure or {}).get("phase_id")) or "stage1_review",
                    review_output=failure,
                )
            )
            continue
        effective_stage1 = stage1_rows[key]
        stage1_decision = decision_from_score(int(effective_stage1["stage_score"]))
        if stage1_decision == "exclude":
            reviewed_count += 1
            rows.append(
                SingleReviewerMergedFinalRow(
                    key=key,
                    title=safe_text(record.get("title") or record.get("query_title")),
                    paper_id=paper_id,
                    workflow_arm=arm_id,
                    stage_model=arm_id,
                    review_state="reviewed",
                    review_skipped=False,
                    final_verdict=stage_verdict("stage1", int(effective_stage1["stage_score"])),
                    stage1_stage_score=int(effective_stage1["stage_score"]),
                    stage1_decision_recommendation=stage1_decision,
                    stage1_review_path=relative_path(_paper_stage1_review_path(run_id, arm_id, paper_id), REPO_ROOT),
                    source_record_provenance=SourceRecordProvenance.model_validate(effective_stage1["source_record_provenance"]),
                    review_output={"stage1_review": original_stage1.get(key), "stage1_verification": verification_stage1.get(key)},
                    fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    fulltext_resolution_status=resolution["resolution_status"],
                ).model_dump(mode="json")
            )
            continue
        if resolution["resolution_status"] not in {"exact", "normalized"}:
            missing_count += 1
            rows.append(
                SingleReviewerMergedFinalRow(
                    key=key,
                    title=safe_text(record.get("title") or record.get("query_title")),
                    paper_id=paper_id,
                    workflow_arm=arm_id,
                    stage_model=arm_id,
                    review_state="missing",
                    review_skipped=True,
                    discard_reason="fulltext_missing",
                    final_verdict=stage_verdict("stage1", int(effective_stage1["stage_score"])),
                    stage1_stage_score=int(effective_stage1["stage_score"]),
                    stage1_decision_recommendation=stage1_decision,
                    stage1_review_path=relative_path(_paper_stage1_review_path(run_id, arm_id, paper_id), REPO_ROOT),
                    source_record_provenance=SourceRecordProvenance.model_validate(effective_stage1["source_record_provenance"]),
                    review_output={"stage1_review": original_stage1.get(key), "stage1_verification": verification_stage1.get(key), "resolution": resolution},
                    fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    fulltext_resolution_status=resolution["resolution_status"],
                ).model_dump(mode="json")
            )
            continue
        if key not in stage2_rows:
            failure = failures.get(("stage2_review", key)) or failures.get(("verification_review", key))
            rows.append(
                _build_error_row(
                    paper_id=paper_id,
                    arm_id=arm_id,
                    record=record,
                    provenance=provenance,
                    review_state="terminal_failure",
                    failed_phase=safe_text((failure or {}).get("phase_id")) or "stage2_review",
                    review_output=failure,
                )
            )
            continue
        effective_stage2 = stage2_rows[key]
        final_stage_name = "stage2_verification" if key in verification_stage2 and key in original_stage2 and decision_from_score(int(original_stage2[key]["stage_score"])) != decision_from_score(int(effective_stage2["stage_score"])) else "stage2"
        reviewed_count += 1
        rows.append(
            SingleReviewerMergedFinalRow(
                key=key,
                title=safe_text(record.get("title") or record.get("query_title")),
                paper_id=paper_id,
                workflow_arm=arm_id,
                stage_model=arm_id,
                review_state="reviewed",
                review_skipped=False,
                final_verdict=stage_verdict(final_stage_name, int(effective_stage2["stage_score"])),
                stage1_stage_score=int(effective_stage1["stage_score"]),
                stage1_decision_recommendation=stage1_decision,
                stage2_stage_score=int(effective_stage2["stage_score"]),
                stage2_decision_recommendation=decision_from_score(int(effective_stage2["stage_score"])),
                stage1_review_path=relative_path(_paper_stage1_review_path(run_id, arm_id, paper_id), REPO_ROOT),
                stage2_review_path=relative_path(_paper_stage2_review_path(run_id, arm_id, paper_id), REPO_ROOT),
                source_record_provenance=SourceRecordProvenance.model_validate(effective_stage2["source_record_provenance"]),
                review_output={
                    "stage1_review": original_stage1.get(key),
                    "stage1_verification": verification_stage1.get(key),
                    "stage2_review": original_stage2.get(key),
                    "stage2_verification": verification_stage2.get(key),
                },
                fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                fulltext_resolution_status=resolution["resolution_status"],
            ).model_dump(mode="json")
        )
    write_json(_paper_final_results_path(run_id, arm_id, paper_id), rows)
    metrics = compute_metrics_from_rows(results=rows, gold_records=_load_gold_records(paper_id))
    route_keys = {safe_text(row.get("candidate_key")) for row in verification_rows if safe_text(row.get("candidate_key"))}
    overturn_keys = set()
    for key in route_keys:
        if key in verification_stage1 and key in original_stage1 and decision_from_score(int(verification_stage1[key]["stage_score"])) != decision_from_score(int(original_stage1[key]["stage_score"])):
            overturn_keys.add(key)
        if key in verification_stage2 and key in original_stage2 and decision_from_score(int(verification_stage2[key]["stage_score"])) != decision_from_score(int(original_stage2[key]["stage_score"])):
            overturn_keys.add(key)
    metrics_payload = {
        "paper_id": paper_id,
        "arm_id": arm_id,
        "stage": "combined",
        "reviewed_count": reviewed_count,
        "missing_count": missing_count,
        "metrics": metrics,
        "auto_resolution_coverage": compute_auto_resolution_coverage(total_rows=runtime["cutoff_result"]["audit_payload"]["candidate_total_after_cutoff"], verification_rows=len(route_keys)),
        "verification_route_rate": (len(route_keys) / runtime["cutoff_result"]["audit_payload"]["candidate_total_after_cutoff"]) if runtime["cutoff_result"]["audit_payload"]["candidate_total_after_cutoff"] else 0.0,
        "verification_overturn_rate": compute_verification_overturn_rate(verification_rows=len(route_keys), overturned_rows=len(overturn_keys)),
    }
    write_json(_paper_combined_metrics_path(run_id, arm_id, paper_id), metrics_payload)
    return metrics_payload


def _build_run_summary(run_id: str, config: dict[str, Any]) -> str:
    lines = ["# gpt-5-nano Async 四篇全矩陣", ""]
    failure_summary = summarize_terminal_failures(_load_existing_failure_rows(run_id))
    lines.append(f"- `run_id`: `{run_id}`")
    lines.append(f"- model: `{config['model']}`")
    lines.append(f"- reasoning_effort: `{config['reasoning_effort']}`")
    lines.append(f"- terminal_failures: `{failure_summary['terminal_failure_count']}`")
    lines.append("")
    for arm in config["arms"]:
        arm_id = arm["id"]
        lines.append(f"## `{arm_id}`")
        lines.append("")
        lines.append("| Paper | Stage1 F1 | Combined F1 | Combined F2 | Combined F3 | Route rate | Overturn rate |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for paper_id in config["papers"]:
            stage1_path = _paper_stage1_metrics_path(run_id, arm_id, paper_id)
            combined_path = _paper_combined_metrics_path(run_id, arm_id, paper_id)
            if not stage1_path.exists() or not combined_path.exists():
                lines.append(f"| `{paper_id}` | - | - | - | - | - | - |")
                continue
            stage1_metrics = read_json(stage1_path)
            combined_metrics = read_json(combined_path)
            lines.append(
                f"| `{paper_id}` | {stage1_metrics['metrics']['f1']:.4f} | {combined_metrics['metrics']['f1']:.4f} | "
                f"{combined_metrics['metrics']['f2']:.4f} | {combined_metrics['metrics']['f3']:.4f} | "
                f"{combined_metrics['verification_route_rate']:.4f} | {combined_metrics['verification_overturn_rate']:.4f} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


async def _run_arm(run_id: str, arm: dict[str, Any], config: dict[str, Any], key_map: dict[str, set[str]] | None) -> None:
    prompt_assets = _load_prompt_assets()
    arm_id = arm["id"]
    papers: list[str] = list(config["papers"])
    for paper_id in papers:
        _paper_dir(run_id, arm_id, paper_id).mkdir(parents=True, exist_ok=True)

    for paper_id in papers:
        allowlist = key_map.get(paper_id) if key_map is not None else None
        if arm["kind"] == "direct":
            specs = _prepare_stage1_direct_requests(
                run_id=run_id,
                arm_id=arm_id,
                paper_id=paper_id,
                key_allowlist=allowlist,
                prompt_assets=prompt_assets,
                config=config,
            )
        else:
            specs = _prepare_stage1_merged_requests(
                run_id=run_id,
                arm_id=arm_id,
                paper_id=paper_id,
                key_allowlist=allowlist,
                prompt_assets=prompt_assets,
                config=config,
            )
        await _execute_specs(run_id=run_id, specs=specs, config=config)
    _materialize_phase_outputs(run_id, arm_id, papers)

    if arm.get("uses_verification"):
        for paper_id in papers:
            allowlist = key_map.get(paper_id) if key_map is not None else None
            specs = _prepare_stage1_verification_requests(
                run_id=run_id,
                arm_id=arm_id,
                paper_id=paper_id,
                key_allowlist=allowlist,
                prompt_assets=prompt_assets,
                config=config,
            )
            await _execute_specs(run_id=run_id, specs=specs, config=config)
        _materialize_phase_outputs(run_id, arm_id, papers)

    for paper_id in papers:
        allowlist = key_map.get(paper_id) if key_map is not None else None
        if arm["kind"] == "direct":
            specs = _prepare_stage2_direct_requests(
                run_id=run_id,
                arm_id=arm_id,
                paper_id=paper_id,
                key_allowlist=allowlist,
                prompt_assets=prompt_assets,
                config=config,
            )
        else:
            specs = _prepare_stage2_merged_requests(
                run_id=run_id,
                arm_id=arm_id,
                paper_id=paper_id,
                key_allowlist=allowlist,
                prompt_assets=prompt_assets,
                config=config,
            )
        await _execute_specs(run_id=run_id, specs=specs, config=config)
    _materialize_phase_outputs(run_id, arm_id, papers)

    if arm.get("uses_verification"):
        for paper_id in papers:
            allowlist = key_map.get(paper_id) if key_map is not None else None
            specs = _prepare_stage2_verification_requests(
                run_id=run_id,
                arm_id=arm_id,
                paper_id=paper_id,
                key_allowlist=allowlist,
                prompt_assets=prompt_assets,
                config=config,
                use_targeted_retrieval=bool(arm.get("uses_targeted_retrieval")),
            )
            await _execute_specs(run_id=run_id, specs=specs, config=config)
        _materialize_phase_outputs(run_id, arm_id, papers)

    for paper_id in papers:
        _build_stage1_rows_and_metrics(run_id, arm_id, paper_id)
        _build_combined_rows_and_metrics(run_id, arm_id, paper_id)


async def _run_matrix(
    run_id: str,
    config: dict[str, Any],
    *,
    key_map: dict[str, set[str]] | None,
    selection_mode: str,
    resume_mode: bool,
) -> None:
    _run_dir(run_id).mkdir(parents=True, exist_ok=True)
    _load_or_init_run_manifest(run_id, config, selection_mode=selection_mode, key_map=key_map)
    for arm in config["arms"]:
        manifest = read_json(_run_manifest_path(run_id))
        if _should_skip_arm(manifest, arm["id"], resume_mode=resume_mode):
            continue
        await _run_arm(run_id, arm, config, key_map)
        manifest = read_json(_run_manifest_path(run_id))
        manifest["arm_status"][arm["id"]] = "completed"
        write_json(_run_manifest_path(run_id), manifest)
        _summary_path(run_id).write_text(_build_run_summary(run_id, config), encoding="utf-8")
    summary = build_matrix_summary(_run_dir(run_id))
    write_json(_run_dir(run_id) / "matrix_summary.json", summary)
    (_run_dir(run_id) / "matrix_summary_zh.md").write_text(render_matrix_summary_zh(summary), encoding="utf-8")
    _summary_path(run_id).write_text(_build_run_summary(run_id, config), encoding="utf-8")


def _latest_run_id() -> str | None:
    runs_dir = BUNDLE_DIR / "runs"
    if not runs_dir.exists():
        return None
    candidates = sorted([path.name for path in runs_dir.iterdir() if path.is_dir()])
    return candidates[-1] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated async gpt-5-nano single-reviewer experiments.")
    parser.add_argument("--mode", choices=["validate", "smoke", "run-all", "resume"], required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    config = _load_config()
    if args.mode == "validate":
        import subprocess

        subprocess.run([sys.executable, str(BUNDLE_DIR / "tools" / "validate_bundle.py"), "--check-client"], check=True, cwd=str(REPO_ROOT))
        return 0

    if args.mode == "smoke":
        run_id = args.run_id or f"smoke_{now_run_id()}"
        key_map = _load_smoke_key_map()
        selection_mode = "smoke"
        resume_mode = False
    elif args.mode == "resume":
        run_id = args.run_id or _latest_run_id()
        if not run_id:
            raise SystemExit("resume requires an existing run directory")
        manifest = read_json(_run_manifest_path(run_id))
        selection_mode = _selection_mode_for_resume(manifest, run_id)
        key_map = _key_map_for_resume(manifest, run_id)
        resume_mode = True
    else:
        run_id = args.run_id or now_run_id()
        key_map = None
        selection_mode = "full"
        resume_mode = False

    asyncio.run(_run_matrix(run_id, config, key_map=key_map, selection_mode=selection_mode, resume_mode=resume_mode))
    print(json.dumps({"run_dir": str(_run_dir(run_id))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
