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
    load_jsonl,
    parse_json_response_text,
    read_json,
    render_template,
    safe_text,
    write_json,
)
from ledger_kernel_lib import (  # noqa: E402
    SeniorMergedStageModelOutput,
    build_adjudication_decision,
    build_dynamic_senior_response_model,
    effective_stage_review,
    role_model_settings,
)
from render_summary import build_run_summary_payload, render_summary_zh  # noqa: E402
from experiment_workflows import (  # noqa: E402
    build_cutoff_review_row,
    build_dynamic_stage_response_model,
    build_fulltext_resolution_audit,
    build_source_record_provenance,
    build_stage_prompt_context,
    build_stage_review_record,
    build_stage_validator,
    criteria_text_for_stage,
    decision_from_score,
    fulltext_payload_from_resolution,
    load_candidates,
    load_cutoff_result,
    load_criterion_asset,
    metadata_payload,
    now_run_id,
    relative_path,
    stage_verdict,
)
from openai_batch_runner import build_json_schema_response_format  # noqa: E402
from vendor.src.utils.llm import OpenAIProvider  # noqa: E402


CONFIG_PATH = BUNDLE_DIR / "config" / "experiment.json"
SMOKE_KEYS_PATH = BUNDLE_DIR / "config" / "smoke_candidates.json"
TEMPLATE_DIR = BUNDLE_DIR / "templates"
SAMPLE_DIR = BUNDLE_DIR / "samples"
PAPER_ID = "2511.13936"


@dataclass
class PromptAssets:
    junior_stage1_template: str
    junior_stage2_template: str
    senior_stage1_template: str
    senior_stage2_template: str
    junior_stage1_hint: str
    junior_stage2_hint: str
    senior_stage1_hint: str
    senior_stage2_hint: str


@dataclass
class RequestSpec:
    request_id: str
    role: str
    phase_id: str
    stage: str
    candidate_key: str
    candidate_title: str
    prompt: str
    model: str
    reasoning_effort: str | None
    response_model: type[BaseModel]
    text_format: dict[str, Any]
    validator: Callable[[BaseModel], None] | None
    record_builder: Callable[[dict[str, Any]], dict[str, Any]]
    request_context: dict[str, Any]


def _load_config() -> dict[str, Any]:
    return read_json(CONFIG_PATH)


def _load_prompt_assets() -> PromptAssets:
    return PromptAssets(
        junior_stage1_template=(TEMPLATE_DIR / "01_stage1_junior_ledger_review_TEMPLATE.md").read_text(encoding="utf-8"),
        junior_stage2_template=(TEMPLATE_DIR / "02_stage2_junior_ledger_review_TEMPLATE.md").read_text(encoding="utf-8"),
        senior_stage1_template=(TEMPLATE_DIR / "03_stage1_senior_adjudication_TEMPLATE.md").read_text(encoding="utf-8"),
        senior_stage2_template=(TEMPLATE_DIR / "04_stage2_senior_adjudication_TEMPLATE.md").read_text(encoding="utf-8"),
        junior_stage1_hint=(SAMPLE_DIR / "junior_stage1_review_output.sample.json").read_text(encoding="utf-8"),
        junior_stage2_hint=(SAMPLE_DIR / "junior_stage2_review_output.sample.json").read_text(encoding="utf-8"),
        senior_stage1_hint=(SAMPLE_DIR / "senior_stage1_review_output.sample.json").read_text(encoding="utf-8"),
        senior_stage2_hint=(SAMPLE_DIR / "senior_stage2_review_output.sample.json").read_text(encoding="utf-8"),
    )


def _run_dir(run_id: str) -> Path:
    return BUNDLE_DIR / "runs" / run_id


def _paper_dir(run_id: str) -> Path:
    return _run_dir(run_id) / "papers" / PAPER_ID


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


def _paper_summary_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "SUMMARY_zh.md"


def _cutoff_audit_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "cutoff_audit.json"


def _fulltext_resolution_audit_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "fulltext_resolution_audit.json"


def _junior_nano_stage1_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "junior_nano_stage1_review.json"


def _junior_mini_stage1_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "junior_mini_stage1_review.json"


def _senior_stage1_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "senior_stage1_review.json"


def _stage1_final_results_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "stage1_final_results.json"


def _stage1_metrics_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "stage1_metrics.json"


def _junior_nano_stage2_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "junior_nano_stage2_review.json"


def _junior_mini_stage2_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "junior_mini_stage2_review.json"


def _senior_stage2_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "senior_stage2_review.json"


def _combined_final_results_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "combined_final_results.json"


def _combined_metrics_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "combined_metrics.json"


def _selected_for_stage2_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "selected_for_stage2.keys.txt"


def _disagreement_audit_path(run_id: str) -> Path:
    return _paper_dir(run_id) / "disagreement_audit.json"


def _criteria_path(stage: str) -> Path:
    if stage == "stage1":
        return REPO_ROOT / "criteria_stage1" / f"{PAPER_ID}.json"
    return REPO_ROOT / "criteria_stage2" / f"{PAPER_ID}.json"


def _asset_path(stage: str) -> Path:
    return BUNDLE_DIR / "assets" / "merged" / f"{PAPER_ID}.{stage}.json"


def _metadata_path() -> Path:
    return REPO_ROOT / "refs" / PAPER_ID / "metadata" / "title_abstracts_metadata.jsonl"


def _gold_path() -> Path:
    return REPO_ROOT / "refs" / PAPER_ID / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _fulltext_root() -> Path:
    return REPO_ROOT / "refs" / PAPER_ID / "mds"


def _cutoff_path() -> Path:
    return REPO_ROOT / "cutoff_jsons" / f"{PAPER_ID}.json"


def _runtime_prompts_path() -> Path:
    return REPO_ROOT / "scripts" / "screening" / "runtime_prompts" / "runtime_prompts.json"


def _load_smoke_key_map() -> dict[str, set[str]]:
    payload = read_json(SMOKE_KEYS_PATH)
    return {paper_id: {safe_text(item) for item in values} for paper_id, values in payload.items()}


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


def _load_or_init_run_manifest(run_id: str, *, selection_mode: str, key_map: dict[str, set[str]] | None) -> dict[str, Any]:
    path = _run_manifest_path(run_id)
    if path.exists():
        payload = read_json(path)
        if "selection_mode" not in payload:
            payload["selection_mode"] = selection_mode
        if key_map is not None and "candidate_key_map" not in payload:
            payload["candidate_key_map"] = _serialize_key_map(key_map)
        write_json(path, payload)
        return payload
    config = _load_config()
    payload = {
        "run_id": run_id,
        "bundle_dir": str(BUNDLE_DIR),
        "results_root": str(_run_dir(run_id)),
        "paper_id": config["paper_id"],
        "workflow_arm": config["workflow_arm"],
        "selection_mode": selection_mode,
        "candidate_key_map": _serialize_key_map(key_map),
        "roles": config["roles"],
        "phase_status": {},
    }
    write_json(path, payload)
    return payload


def _mark_phase_completed(run_id: str, phase_id: str) -> None:
    manifest = read_json(_run_manifest_path(run_id))
    manifest.setdefault("phase_status", {})[phase_id] = "completed"
    write_json(_run_manifest_path(run_id), manifest)


def _request_id(role: str, phase_id: str, candidate_key: str) -> str:
    return f"{role}::{phase_id}::{PAPER_ID}::{candidate_key}"


def _load_existing_response_rows(run_id: str) -> list[dict[str, Any]]:
    return load_jsonl(_response_log_path(run_id))


def _load_existing_failure_rows(run_id: str) -> list[dict[str, Any]]:
    return load_jsonl(_failure_log_path(run_id))


def _completed_request_ids(run_id: str) -> set[str]:
    return {safe_text(row.get("request_id")) for row in _load_existing_response_rows(run_id)}


def _terminal_failure_ids(run_id: str) -> set[str]:
    return {safe_text(row.get("request_id")) for row in _load_existing_failure_rows(run_id)}


def _rows_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {safe_text(row.get("candidate_key")): row for row in rows if safe_text(row.get("candidate_key"))}


def _load_phase_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = read_json(path)
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _materialize_phase_output(run_id: str, phase_id: str, role: str, output_path: Path) -> None:
    rows = [
        row["record"]
        for row in _load_existing_response_rows(run_id)
        if safe_text(row.get("phase_id")) == phase_id and safe_text(row.get("role")) == role
    ]
    rows = sorted(rows, key=lambda item: safe_text(item.get("candidate_key")))
    write_json(output_path, rows)


def _materialize_phase_outputs(run_id: str) -> None:
    _materialize_phase_output(run_id, "stage1_review", "junior_nano", _junior_nano_stage1_path(run_id))
    _materialize_phase_output(run_id, "stage1_review", "junior_mini", _junior_mini_stage1_path(run_id))
    _materialize_phase_output(run_id, "stage1_review", "senior", _senior_stage1_path(run_id))
    _materialize_phase_output(run_id, "stage2_review", "junior_nano", _junior_nano_stage2_path(run_id))
    _materialize_phase_output(run_id, "stage2_review", "junior_mini", _junior_mini_stage2_path(run_id))
    _materialize_phase_output(run_id, "stage2_review", "senior", _senior_stage2_path(run_id))


def _paper_runtime_inputs(run_id: str, *, key_allowlist: set[str] | None) -> dict[str, Any]:
    records = load_candidates(_metadata_path(), key_allowlist=key_allowlist)
    resolution_by_key, resolution_audit = build_fulltext_resolution_audit(
        paper_id=PAPER_ID,
        records=records,
        fulltext_root=_fulltext_root(),
        repo_root=REPO_ROOT,
    )
    cutoff_result = load_cutoff_result(records=records, cutoff_path=_cutoff_path())
    write_json(_cutoff_audit_path(run_id), cutoff_result["audit_payload"])
    write_json(_fulltext_resolution_audit_path(run_id), resolution_audit)
    return {
        "records": records,
        "resolution_by_key": resolution_by_key,
        "cutoff_result": cutoff_result,
    }


def _responses_text_format(*, response_model: type[BaseModel], schema_name: str) -> dict[str, Any]:
    response_format = build_json_schema_response_format(response_model, schema_name=schema_name)
    json_schema = response_format["json_schema"]
    return {
        "type": "json_schema",
        "name": json_schema["name"],
        "strict": True,
        "schema": json_schema["schema"],
    }


def _schema_name(base: str) -> str:
    return f"{base}_{PAPER_ID.replace('.', '_')}"


def _build_junior_record(
    *,
    parsed: dict[str, Any],
    stage: str,
    role: str,
    candidate_key: str,
    candidate_title: str,
    asset_path: Path,
    criteria_path: Path,
    provenance: Any,
) -> dict[str, Any]:
    record = build_stage_review_record(
        model_output=parsed,
        paper_id=PAPER_ID,
        candidate_key=candidate_key,
        candidate_title=candidate_title,
        stage=stage,
        workflow_arm=_load_config()["workflow_arm"],
        qa_asset_path=str(asset_path.relative_to(REPO_ROOT)),
        criteria_path=str(criteria_path.relative_to(REPO_ROOT)),
        provenance=provenance,
    ).model_dump(mode="json")
    record["role"] = role
    return record


def _build_senior_record(
    *,
    parsed: dict[str, Any],
    stage: str,
    candidate_key: str,
    candidate_title: str,
    asset_path: Path,
    criteria_path: Path,
    provenance: Any,
    disagreement_summary: dict[str, Any],
) -> dict[str, Any]:
    senior_payload = SeniorMergedStageModelOutput.model_validate(parsed).model_dump(mode="json")
    senior_payload.update(
        {
            "paper_id": PAPER_ID,
            "candidate_key": candidate_key,
            "candidate_title": candidate_title,
            "stage": stage,
            "workflow_arm": _load_config()["workflow_arm"],
            "qa_asset_path": str(asset_path.relative_to(REPO_ROOT)),
            "criteria_path": str(criteria_path.relative_to(REPO_ROOT)),
            "source_record_provenance": provenance.model_dump(mode="json"),
            "role": "senior",
            "disagreement_summary": disagreement_summary,
        }
    )
    return senior_payload


def _build_senior_validator(*, expected_criterion_ids: list[str]) -> Callable[[BaseModel], None]:
    expected = set(expected_criterion_ids)

    def validate(payload: BaseModel) -> None:
        parsed = SeniorMergedStageModelOutput.model_validate(payload)
        observed = [item.criterion_id for item in parsed.criterion_assessments]
        if len(observed) != len(expected_criterion_ids):
            raise ValueError("criterion_assessments length mismatch")
        if set(observed) != expected:
            raise ValueError(f"criterion_id mismatch: expected={sorted(expected)} observed={sorted(set(observed))}")
        if len(observed) != len(set(observed)):
            raise ValueError("criterion_id must be unique within criterion_assessments")

    return validate


def _prepare_stage1_junior_requests(
    *,
    run_id: str,
    role: str,
    runtime: dict[str, Any],
    prompt_assets: PromptAssets,
) -> list[RequestSpec]:
    criteria_path = _criteria_path("stage1")
    asset_path = _asset_path("stage1")
    asset = load_criterion_asset(asset_path)
    criteria_payload = criteria_text_for_stage(criteria_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_stage_response_model(_schema_name(f"Stage1Junior{role.title()}"), criterion_ids=expected_ids)
    response_hint = prompt_assets.junior_stage1_hint
    model_cfg = role_model_settings(role)
    specs: list[RequestSpec] = []
    for record in runtime["cutoff_result"]["kept_records"]:
        key = safe_text(record.get("key"))
        title = safe_text(record.get("title") or record.get("query_title"))
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=PAPER_ID,
            resolution=resolution,
            metadata_path=_metadata_path(),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        context = build_stage_prompt_context(
            stage="stage1",
            workflow_arm=_load_config()["workflow_arm"],
            paper_id=PAPER_ID,
            candidate_key=key,
            candidate_title=title,
            asset=asset,
            criteria_payload=criteria_payload,
            metadata=metadata_payload(record),
            response_schema_hint=response_hint,
            provenance=provenance,
        )
        context["REVIEWER_ROLE"] = role
        prompt = render_template(prompt_assets.junior_stage1_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id(role, "stage1_review", key),
                role=role,
                phase_id="stage1_review",
                stage="stage1",
                candidate_key=key,
                candidate_title=title,
                prompt=prompt,
                model=model_cfg["model"],
                reasoning_effort=model_cfg["reasoning_effort"],
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name(f"Stage1Junior{role.title()}")),
                validator=build_stage_validator(
                    paper_id=PAPER_ID,
                    stage="stage1",
                    candidate_key=key,
                    candidate_title=title,
                    expected_criterion_ids=expected_ids,
                ),
                record_builder=lambda parsed, stage="stage1", role=role, key=key, title=title, asset_path=asset_path, criteria_path=criteria_path, provenance=provenance: _build_junior_record(
                    parsed=parsed,
                    stage=stage,
                    role=role,
                    candidate_key=key,
                    candidate_title=title,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                ),
                request_context={"phase": "stage1_review", "role": role, "paper_id": PAPER_ID, "candidate_title": title},
            )
        )
    return specs


def _stage_maps(run_id: str, stage: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if stage == "stage1":
        return (
            _rows_by_key(_load_phase_rows(_junior_nano_stage1_path(run_id))),
            _rows_by_key(_load_phase_rows(_junior_mini_stage1_path(run_id))),
            _rows_by_key(_load_phase_rows(_senior_stage1_path(run_id))),
        )
    return (
        _rows_by_key(_load_phase_rows(_junior_nano_stage2_path(run_id))),
        _rows_by_key(_load_phase_rows(_junior_mini_stage2_path(run_id))),
        _rows_by_key(_load_phase_rows(_senior_stage2_path(run_id))),
    )


def _adjudication_rows(run_id: str, stage: str) -> dict[str, dict[str, Any]]:
    junior_nano_map, junior_mini_map, senior_map = _stage_maps(run_id, stage)
    out: dict[str, dict[str, Any]] = {}
    for key in sorted(set(junior_nano_map) & set(junior_mini_map)):
        adjudication = build_adjudication_decision(
            stage=stage,
            junior_nano=junior_nano_map[key],
            junior_mini=junior_mini_map[key],
        )
        senior_row = senior_map.get(key)
        effective = None
        senior_decision = None
        senior_overturn = False
        if not adjudication["route_to_senior"]:
            effective = effective_stage_review(
                junior_nano=junior_nano_map[key],
                junior_mini=junior_mini_map[key],
                senior=None,
                adjudication=adjudication,
            )
        elif senior_row is not None:
            effective = effective_stage_review(
                junior_nano=junior_nano_map[key],
                junior_mini=junior_mini_map[key],
                senior=senior_row,
                adjudication=adjudication,
            )
            senior_decision = decision_from_score(int(senior_row["stage_score"]))
            if adjudication["junior_nano_decision"] == adjudication["junior_mini_decision"]:
                senior_overturn = senior_decision != adjudication["junior_nano_decision"]
            else:
                senior_overturn = senior_decision not in {
                    adjudication["junior_nano_decision"],
                    adjudication["junior_mini_decision"],
                }
        out[key] = {
            "candidate_key": key,
            "stage": stage,
            "adjudication": adjudication,
            "effective_review": effective,
            "senior_present": senior_row is not None,
            "senior_decision": senior_decision,
            "senior_overturn": senior_overturn,
        }
    return out


def _prepare_stage1_senior_requests(
    *,
    run_id: str,
    runtime: dict[str, Any],
    prompt_assets: PromptAssets,
) -> list[RequestSpec]:
    junior_nano_map, junior_mini_map, senior_map = _stage_maps(run_id, "stage1")
    criteria_path = _criteria_path("stage1")
    asset_path = _asset_path("stage1")
    asset = load_criterion_asset(asset_path)
    criteria_payload = criteria_text_for_stage(criteria_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_senior_response_model(_schema_name("Stage1Senior"), criterion_ids=expected_ids)
    model_cfg = role_model_settings("senior")
    specs: list[RequestSpec] = []
    for record in runtime["cutoff_result"]["kept_records"]:
        key = safe_text(record.get("key"))
        if key not in junior_nano_map or key not in junior_mini_map or key in senior_map:
            continue
        disagreement_summary = build_adjudication_decision(
            stage="stage1",
            junior_nano=junior_nano_map[key],
            junior_mini=junior_mini_map[key],
        )
        if not disagreement_summary["route_to_senior"]:
            continue
        title = safe_text(record.get("title") or record.get("query_title"))
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=PAPER_ID,
            resolution=resolution,
            metadata_path=_metadata_path(),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        context = {
            "WORKFLOW_ARM": _load_config()["workflow_arm"],
            "PAPER_ID": PAPER_ID,
            "CANDIDATE_KEY": key,
            "TOPIC_DEFINITION": asset.topic_definition,
            "DECISION_POLICY": asset.decision_policy,
            "QA_ASSET_JSON": json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "STAGE_CRITERIA_JSON_CONTENT": criteria_payload,
            "METADATA_JSON": json.dumps(metadata_payload(record), ensure_ascii=False, indent=2),
            "SOURCE_RECORD_PROVENANCE_JSON": json.dumps(provenance.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "JUNIOR_NANO_REVIEW_JSON": json.dumps(junior_nano_map[key], ensure_ascii=False, indent=2),
            "JUNIOR_MINI_REVIEW_JSON": json.dumps(junior_mini_map[key], ensure_ascii=False, indent=2),
            "DISAGREEMENT_SUMMARY_JSON": json.dumps(disagreement_summary, ensure_ascii=False, indent=2),
            "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.senior_stage1_hint,
        }
        prompt = render_template(prompt_assets.senior_stage1_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id("senior", "stage1_review", key),
                role="senior",
                phase_id="stage1_review",
                stage="stage1",
                candidate_key=key,
                candidate_title=title,
                prompt=prompt,
                model=model_cfg["model"],
                reasoning_effort=model_cfg["reasoning_effort"],
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("Stage1Senior")),
                validator=_build_senior_validator(expected_criterion_ids=expected_ids),
                record_builder=lambda parsed, key=key, title=title, asset_path=asset_path, criteria_path=criteria_path, provenance=provenance, disagreement_summary=disagreement_summary: _build_senior_record(
                    parsed=parsed,
                    stage="stage1",
                    candidate_key=key,
                    candidate_title=title,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                    disagreement_summary=disagreement_summary,
                ),
                request_context={"phase": "stage1_review", "role": "senior", "paper_id": PAPER_ID, "candidate_title": title},
            )
        )
    return specs


def _selected_stage2_keys(run_id: str) -> list[str]:
    rows = _load_phase_rows(_stage1_final_results_path(run_id))
    selected: list[str] = []
    for row in rows:
        if safe_text(row.get("review_state")) != "reviewed":
            continue
        if decision_from_score(int(row.get("stage1_stage_score") or 3)) in {"include", "maybe"}:
            selected.append(safe_text(row.get("key")))
    return selected


def _prepare_stage2_junior_requests(
    *,
    run_id: str,
    role: str,
    runtime: dict[str, Any],
    prompt_assets: PromptAssets,
) -> list[RequestSpec]:
    selected = set(_selected_stage2_keys(run_id))
    _selected_for_stage2_path(run_id).write_text("\n".join(sorted(selected)) + ("\n" if selected else ""), encoding="utf-8")
    criteria_path = _criteria_path("stage2")
    asset_path = _asset_path("stage2")
    asset = load_criterion_asset(asset_path)
    criteria_payload = criteria_text_for_stage(criteria_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_stage_response_model(_schema_name(f"Stage2Junior{role.title()}"), criterion_ids=expected_ids)
    model_cfg = role_model_settings(role)
    stage1_rows = _adjudication_rows(run_id, "stage1")
    specs: list[RequestSpec] = []
    for record in runtime["cutoff_result"]["kept_records"]:
        key = safe_text(record.get("key"))
        if key not in selected:
            continue
        resolution = runtime["resolution_by_key"][key]
        if resolution["resolution_status"] not in {"exact", "normalized"}:
            continue
        title = safe_text(record.get("title") or record.get("query_title"))
        provenance = build_source_record_provenance(
            record=record,
            paper_id=PAPER_ID,
            resolution=resolution,
            metadata_path=_metadata_path(),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        fulltext_text, fulltext_meta = fulltext_payload_from_resolution(
            resolution,
            repo_root=REPO_ROOT,
            head_chars=int(_load_config()["fulltext_inline_head_chars"]),
            tail_chars=int(_load_config()["fulltext_inline_tail_chars"]),
        )
        prior_stage_review = {
            "effective_review": stage1_rows[key]["effective_review"],
            "adjudication": stage1_rows[key]["adjudication"],
        }
        context = build_stage_prompt_context(
            stage="stage2",
            workflow_arm=_load_config()["workflow_arm"],
            paper_id=PAPER_ID,
            candidate_key=key,
            candidate_title=title,
            asset=asset,
            criteria_payload=criteria_payload,
            metadata=metadata_payload(record),
            response_schema_hint=prompt_assets.junior_stage2_hint,
            provenance=provenance,
            prior_stage_review=prior_stage_review,
            fulltext_resolution={**resolution, **fulltext_meta},
            fulltext_text=fulltext_text,
        )
        context["REVIEWER_ROLE"] = role
        prompt = render_template(prompt_assets.junior_stage2_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id(role, "stage2_review", key),
                role=role,
                phase_id="stage2_review",
                stage="stage2",
                candidate_key=key,
                candidate_title=title,
                prompt=prompt,
                model=model_cfg["model"],
                reasoning_effort=model_cfg["reasoning_effort"],
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name(f"Stage2Junior{role.title()}")),
                validator=build_stage_validator(
                    paper_id=PAPER_ID,
                    stage="stage2",
                    candidate_key=key,
                    candidate_title=title,
                    expected_criterion_ids=expected_ids,
                ),
                record_builder=lambda parsed, key=key, title=title, asset_path=asset_path, criteria_path=criteria_path, provenance=provenance: _build_junior_record(
                    parsed=parsed,
                    stage="stage2",
                    role=role,
                    candidate_key=key,
                    candidate_title=title,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                ),
                request_context={"phase": "stage2_review", "role": role, "paper_id": PAPER_ID, "candidate_title": title},
            )
        )
    return specs


def _prepare_stage2_senior_requests(
    *,
    run_id: str,
    runtime: dict[str, Any],
    prompt_assets: PromptAssets,
) -> list[RequestSpec]:
    junior_nano_map, junior_mini_map, senior_map = _stage_maps(run_id, "stage2")
    stage1_rows = _adjudication_rows(run_id, "stage1")
    criteria_path = _criteria_path("stage2")
    asset_path = _asset_path("stage2")
    asset = load_criterion_asset(asset_path)
    criteria_payload = criteria_text_for_stage(criteria_path)
    expected_ids = [item.criterion_id for item in asset.criteria]
    response_model = build_dynamic_senior_response_model(_schema_name("Stage2Senior"), criterion_ids=expected_ids)
    model_cfg = role_model_settings("senior")
    specs: list[RequestSpec] = []
    for record in runtime["cutoff_result"]["kept_records"]:
        key = safe_text(record.get("key"))
        if key not in junior_nano_map or key not in junior_mini_map or key in senior_map:
            continue
        disagreement_summary = build_adjudication_decision(
            stage="stage2",
            junior_nano=junior_nano_map[key],
            junior_mini=junior_mini_map[key],
        )
        if not disagreement_summary["route_to_senior"]:
            continue
        title = safe_text(record.get("title") or record.get("query_title"))
        resolution = runtime["resolution_by_key"][key]
        if resolution["resolution_status"] not in {"exact", "normalized"}:
            continue
        provenance = build_source_record_provenance(
            record=record,
            paper_id=PAPER_ID,
            resolution=resolution,
            metadata_path=_metadata_path(),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=criteria_path,
            repo_root=REPO_ROOT,
        )
        fulltext_text, fulltext_meta = fulltext_payload_from_resolution(
            resolution,
            repo_root=REPO_ROOT,
            head_chars=int(_load_config()["fulltext_inline_head_chars"]),
            tail_chars=int(_load_config()["fulltext_inline_tail_chars"]),
        )
        context = {
            "WORKFLOW_ARM": _load_config()["workflow_arm"],
            "PAPER_ID": PAPER_ID,
            "CANDIDATE_KEY": key,
            "TOPIC_DEFINITION": asset.topic_definition,
            "DECISION_POLICY": asset.decision_policy,
            "QA_ASSET_JSON": json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "STAGE_CRITERIA_JSON_CONTENT": criteria_payload,
            "METADATA_JSON": json.dumps(metadata_payload(record), ensure_ascii=False, indent=2),
            "PRIOR_STAGE_REVIEW_JSON": json.dumps(
                {
                    "effective_review": stage1_rows[key]["effective_review"],
                    "adjudication": stage1_rows[key]["adjudication"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "FULLTEXT_RESOLUTION_JSON": json.dumps({**resolution, **fulltext_meta}, ensure_ascii=False, indent=2),
            "FULLTEXT_TEXT": fulltext_text,
            "JUNIOR_NANO_REVIEW_JSON": json.dumps(junior_nano_map[key], ensure_ascii=False, indent=2),
            "JUNIOR_MINI_REVIEW_JSON": json.dumps(junior_mini_map[key], ensure_ascii=False, indent=2),
            "DISAGREEMENT_SUMMARY_JSON": json.dumps(disagreement_summary, ensure_ascii=False, indent=2),
            "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.senior_stage2_hint,
        }
        prompt = render_template(prompt_assets.senior_stage2_template, context)
        specs.append(
            RequestSpec(
                request_id=_request_id("senior", "stage2_review", key),
                role="senior",
                phase_id="stage2_review",
                stage="stage2",
                candidate_key=key,
                candidate_title=title,
                prompt=prompt,
                model=model_cfg["model"],
                reasoning_effort=model_cfg["reasoning_effort"],
                response_model=response_model,
                text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("Stage2Senior")),
                validator=_build_senior_validator(expected_criterion_ids=expected_ids),
                record_builder=lambda parsed, key=key, title=title, asset_path=asset_path, criteria_path=criteria_path, provenance=provenance, disagreement_summary=disagreement_summary: _build_senior_record(
                    parsed=parsed,
                    stage="stage2",
                    candidate_key=key,
                    candidate_title=title,
                    asset_path=asset_path,
                    criteria_path=criteria_path,
                    provenance=provenance,
                    disagreement_summary=disagreement_summary,
                ),
                request_context={"phase": "stage2_review", "role": "senior", "paper_id": PAPER_ID, "candidate_title": title},
            )
        )
    return specs


async def _run_request(
    *,
    provider: OpenAIProvider,
    spec: RequestSpec,
    run_id: str,
    max_attempts: int,
) -> None:
    for attempt in range(1, max_attempts + 1):
        append_jsonl(
            _request_log_path(run_id),
            {
                "request_id": spec.request_id,
                "role": spec.role,
                "phase_id": spec.phase_id,
                "stage": spec.stage,
                "paper_id": PAPER_ID,
                "candidate_key": spec.candidate_key,
                "attempt": attempt,
                "model": spec.model,
                "prompt_chars": len(spec.prompt),
            },
        )
        try:
            normalized_messages = provider._normalize_messages([{"role": "user", "content": spec.prompt}])  # noqa: SLF001

            async def _call() -> Any:
                kwargs: dict[str, Any] = {
                    "model": spec.model,
                    "input": normalized_messages,
                    "text": {"format": spec.text_format},
                    "metadata": {
                        "request_id": spec.request_id,
                        "role": spec.role,
                        "phase_id": spec.phase_id,
                        "paper_id": PAPER_ID,
                    },
                }
                if spec.reasoning_effort:
                    kwargs["reasoning"] = {"effort": spec.reasoning_effort}
                return await provider._async_client.responses.create(**kwargs)  # noqa: SLF001

            result = await provider._execute_with_retry_async(  # noqa: SLF001
                _call,
                model=spec.model,
                mode="async",
                metadata={
                    "request_id": spec.request_id,
                    "role": spec.role,
                    "phase_id": spec.phase_id,
                    "paper_id": PAPER_ID,
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
                    "role": spec.role,
                    "phase_id": spec.phase_id,
                    "stage": spec.stage,
                    "paper_id": PAPER_ID,
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
                        "role": spec.role,
                        "phase_id": spec.phase_id,
                        "stage": spec.stage,
                        "paper_id": PAPER_ID,
                        "candidate_key": spec.candidate_key,
                        "status": "terminal_failure",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "attempts": attempt,
                        "context": spec.request_context,
                    },
                )


async def _execute_specs(run_id: str, specs: list[RequestSpec]) -> None:
    config = _load_config()
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
                max_attempts=int(config["max_attempts_per_request"]),
            )

    await asyncio.gather(*(worker(spec) for spec in pending))


def _failure_lookup(run_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in _load_existing_failure_rows(run_id):
        lookup[(safe_text(row.get("phase_id")), safe_text(row.get("candidate_key")))] = row
    return lookup


def _build_disagreement_audit(run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage in ("stage1", "stage2"):
        junior_nano_map, junior_mini_map, senior_map = _stage_maps(run_id, stage)
        for key in sorted(set(junior_nano_map) & set(junior_mini_map)):
            adjudication = build_adjudication_decision(
                stage=stage,
                junior_nano=junior_nano_map[key],
                junior_mini=junior_mini_map[key],
            )
            senior_row = senior_map.get(key)
            senior_decision = decision_from_score(int(senior_row["stage_score"])) if senior_row is not None else None
            senior_overturn = False
            if adjudication["route_to_senior"] and senior_decision is not None:
                if adjudication["junior_nano_decision"] == adjudication["junior_mini_decision"]:
                    senior_overturn = senior_decision != adjudication["junior_nano_decision"]
                else:
                    senior_overturn = senior_decision not in {
                        adjudication["junior_nano_decision"],
                        adjudication["junior_mini_decision"],
                    }
            rows.append(
                {
                    "candidate_key": key,
                    "stage": stage,
                    "junior_nano_decision": adjudication["junior_nano_decision"],
                    "junior_mini_decision": adjudication["junior_mini_decision"],
                    "route_to_senior": adjudication["route_to_senior"],
                    "reasons": adjudication["reasons"],
                    "criterion_conflicts": adjudication["criterion_conflicts"],
                    "unclear_criterion_ids": adjudication["unclear_criterion_ids"],
                    "auto_final_decision": adjudication["auto_final_decision"],
                    "senior_present": senior_row is not None,
                    "senior_decision": senior_decision,
                    "senior_overturn": senior_overturn,
                    "final_source": "senior" if adjudication["route_to_senior"] else "auto",
                }
            )
    write_json(_disagreement_audit_path(run_id), rows)
    return rows


def _build_terminal_failure_row(
    *,
    record: dict[str, Any],
    provenance: Any,
    failed_phase: str,
    review_output: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "key": safe_text(record.get("key")),
        "title": safe_text(record.get("title") or record.get("query_title")),
        "paper_id": PAPER_ID,
        "workflow_arm": _load_config()["workflow_arm"],
        "review_state": "terminal_failure",
        "review_skipped": False,
        "failed_phase": failed_phase,
        "discard_reason": "terminal_failure",
        "final_verdict": "maybe (review_state:terminal_failure)",
        "source_record_provenance": provenance.model_dump(mode="json"),
        "review_output": review_output,
    }


def _stage1_effective_map(run_id: str) -> dict[str, dict[str, Any]]:
    return _adjudication_rows(run_id, "stage1")


def _stage2_effective_map(run_id: str) -> dict[str, dict[str, Any]]:
    return _adjudication_rows(run_id, "stage2")


def _build_stage1_outputs(run_id: str, *, key_allowlist: set[str] | None) -> dict[str, Any]:
    runtime = _paper_runtime_inputs(run_id, key_allowlist=key_allowlist)
    failures = _failure_lookup(run_id)
    stage1_map = _stage1_effective_map(run_id)
    disagreement_rows = _build_disagreement_audit(run_id)
    rows: list[dict[str, Any]] = []
    cutoff_after = int(runtime["cutoff_result"]["audit_payload"].get("candidate_total_after_cutoff") or 0)
    route_rows = [row for row in disagreement_rows if row["stage"] == "stage1" and row["route_to_senior"]]
    senior_overturn_count = sum(1 for row in route_rows if row["senior_overturn"])

    for record in runtime["records"]:
        key = safe_text(record.get("key"))
        decision = runtime["cutoff_result"]["decisions_by_key"][key]
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=PAPER_ID,
            resolution=resolution,
            metadata_path=_metadata_path(),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=_criteria_path("stage1"),
            repo_root=REPO_ROOT,
        )
        if not decision["cutoff_pass"]:
            rows.append(
                build_cutoff_review_row(
                    paper_id=PAPER_ID,
                    workflow_arm=_load_config()["workflow_arm"],
                    stage_model=_load_config()["workflow_arm"],
                    record=record,
                    decision=decision,
                ).model_dump(mode="json")
            )
            continue
        if key not in stage1_map or stage1_map[key]["effective_review"] is None:
            failure = failures.get(("stage1_review", key))
            rows.append(
                _build_terminal_failure_row(
                    record=record,
                    provenance=provenance,
                    failed_phase=safe_text((failure or {}).get("phase_id")) or "stage1_review",
                    review_output=failure,
                )
            )
            continue
        effective = stage1_map[key]["effective_review"]
        adjudication = stage1_map[key]["adjudication"]
        source_label = "stage1_senior" if adjudication["route_to_senior"] else "stage1_auto"
        rows.append(
            {
                "key": key,
                "title": safe_text(record.get("title") or record.get("query_title")),
                "paper_id": PAPER_ID,
                "workflow_arm": _load_config()["workflow_arm"],
                "review_state": "reviewed",
                "review_skipped": False,
                "final_verdict": stage_verdict(source_label, int(effective["stage_score"])),
                "stage1_stage_score": int(effective["stage_score"]),
                "stage1_decision_recommendation": decision_from_score(int(effective["stage_score"])),
                "decision_source": "senior" if adjudication["route_to_senior"] else "auto",
                "stage1_paths": {
                    "junior_nano": relative_path(_junior_nano_stage1_path(run_id), REPO_ROOT),
                    "junior_mini": relative_path(_junior_mini_stage1_path(run_id), REPO_ROOT),
                    "senior": relative_path(_senior_stage1_path(run_id), REPO_ROOT),
                },
                "source_record_provenance": effective["source_record_provenance"],
                "review_output": {
                    "junior_nano": _rows_by_key(_load_phase_rows(_junior_nano_stage1_path(run_id))).get(key),
                    "junior_mini": _rows_by_key(_load_phase_rows(_junior_mini_stage1_path(run_id))).get(key),
                    "senior": _rows_by_key(_load_phase_rows(_senior_stage1_path(run_id))).get(key),
                    "adjudication": adjudication,
                },
                "fulltext_source_path": resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                "fulltext_resolution_status": resolution["resolution_status"],
            }
        )

    write_json(_stage1_final_results_path(run_id), rows)
    metrics = compute_metrics_from_rows(results=rows, gold_records=load_jsonl(_gold_path()))
    payload = {
        "paper_id": PAPER_ID,
        "workflow_arm": _load_config()["workflow_arm"],
        "stage": "stage1",
        "metrics": metrics,
        "auto_resolution_coverage": compute_auto_resolution_coverage(total_rows=cutoff_after, verification_rows=len(route_rows)),
        "senior_route_rate": (len(route_rows) / cutoff_after) if cutoff_after else 0.0,
        "senior_overturn_rate": (senior_overturn_count / len(route_rows)) if route_rows else 0.0,
    }
    write_json(_stage1_metrics_path(run_id), payload)
    return payload


def _build_combined_outputs(run_id: str, *, key_allowlist: set[str] | None) -> dict[str, Any]:
    runtime = _paper_runtime_inputs(run_id, key_allowlist=key_allowlist)
    failures = _failure_lookup(run_id)
    stage1_map = _stage1_effective_map(run_id)
    stage2_map = _stage2_effective_map(run_id)
    disagreement_rows = _build_disagreement_audit(run_id)
    stage1_junior_nano = _rows_by_key(_load_phase_rows(_junior_nano_stage1_path(run_id)))
    stage1_junior_mini = _rows_by_key(_load_phase_rows(_junior_mini_stage1_path(run_id)))
    stage1_senior = _rows_by_key(_load_phase_rows(_senior_stage1_path(run_id)))
    stage2_junior_nano = _rows_by_key(_load_phase_rows(_junior_nano_stage2_path(run_id)))
    stage2_junior_mini = _rows_by_key(_load_phase_rows(_junior_mini_stage2_path(run_id)))
    stage2_senior = _rows_by_key(_load_phase_rows(_senior_stage2_path(run_id)))

    rows: list[dict[str, Any]] = []
    cutoff_after = int(runtime["cutoff_result"]["audit_payload"].get("candidate_total_after_cutoff") or 0)
    route_events = [row for row in disagreement_rows if row["route_to_senior"]]
    routed_keys = {row["candidate_key"] for row in route_events}
    senior_overturn_count = sum(1 for row in route_events if row["senior_overturn"])
    reviewed_count = 0
    missing_count = 0

    for record in runtime["records"]:
        key = safe_text(record.get("key"))
        decision = runtime["cutoff_result"]["decisions_by_key"][key]
        resolution = runtime["resolution_by_key"][key]
        provenance = build_source_record_provenance(
            record=record,
            paper_id=PAPER_ID,
            resolution=resolution,
            metadata_path=_metadata_path(),
            runtime_prompts_path=_runtime_prompts_path(),
            criteria_path=_criteria_path("stage1"),
            repo_root=REPO_ROOT,
        )
        if not decision["cutoff_pass"]:
            rows.append(
                build_cutoff_review_row(
                    paper_id=PAPER_ID,
                    workflow_arm=_load_config()["workflow_arm"],
                    stage_model=_load_config()["workflow_arm"],
                    record=record,
                    decision=decision,
                ).model_dump(mode="json")
            )
            continue
        if key not in stage1_map or stage1_map[key]["effective_review"] is None:
            failure = failures.get(("stage1_review", key))
            rows.append(
                _build_terminal_failure_row(
                    record=record,
                    provenance=provenance,
                    failed_phase=safe_text((failure or {}).get("phase_id")) or "stage1_review",
                    review_output=failure,
                )
            )
            continue
        effective_stage1 = stage1_map[key]["effective_review"]
        stage1_decision = decision_from_score(int(effective_stage1["stage_score"]))
        if stage1_decision == "exclude":
            reviewed_count += 1
            rows.append(
                {
                    "key": key,
                    "title": safe_text(record.get("title") or record.get("query_title")),
                    "paper_id": PAPER_ID,
                    "workflow_arm": _load_config()["workflow_arm"],
                    "review_state": "reviewed",
                    "review_skipped": False,
                    "final_verdict": stage_verdict(
                        "stage1_senior" if stage1_map[key]["adjudication"]["route_to_senior"] else "stage1_auto",
                        int(effective_stage1["stage_score"]),
                    ),
                    "stage1_stage_score": int(effective_stage1["stage_score"]),
                    "stage1_decision_recommendation": stage1_decision,
                    "source_record_provenance": effective_stage1["source_record_provenance"],
                    "review_output": {
                        "stage1": {
                            "junior_nano": stage1_junior_nano.get(key),
                            "junior_mini": stage1_junior_mini.get(key),
                            "senior": stage1_senior.get(key),
                            "adjudication": stage1_map[key]["adjudication"],
                        }
                    },
                    "fulltext_source_path": resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    "fulltext_resolution_status": resolution["resolution_status"],
                }
            )
            continue
        if resolution["resolution_status"] not in {"exact", "normalized"}:
            missing_count += 1
            rows.append(
                {
                    "key": key,
                    "title": safe_text(record.get("title") or record.get("query_title")),
                    "paper_id": PAPER_ID,
                    "workflow_arm": _load_config()["workflow_arm"],
                    "review_state": "missing",
                    "review_skipped": True,
                    "discard_reason": "fulltext_missing",
                    "final_verdict": stage_verdict(
                        "stage1_senior" if stage1_map[key]["adjudication"]["route_to_senior"] else "stage1_auto",
                        int(effective_stage1["stage_score"]),
                    ),
                    "stage1_stage_score": int(effective_stage1["stage_score"]),
                    "stage1_decision_recommendation": stage1_decision,
                    "source_record_provenance": effective_stage1["source_record_provenance"],
                    "review_output": {
                        "stage1": {
                            "junior_nano": stage1_junior_nano.get(key),
                            "junior_mini": stage1_junior_mini.get(key),
                            "senior": stage1_senior.get(key),
                            "adjudication": stage1_map[key]["adjudication"],
                        }
                    },
                    "fulltext_source_path": resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    "fulltext_resolution_status": resolution["resolution_status"],
                }
            )
            continue
        if key not in stage2_map or stage2_map[key]["effective_review"] is None:
            failure = failures.get(("stage2_review", key))
            rows.append(
                _build_terminal_failure_row(
                    record=record,
                    provenance=provenance,
                    failed_phase=safe_text((failure or {}).get("phase_id")) or "stage2_review",
                    review_output=failure,
                )
            )
            continue
        effective_stage2 = stage2_map[key]["effective_review"]
        reviewed_count += 1
        rows.append(
            {
                "key": key,
                "title": safe_text(record.get("title") or record.get("query_title")),
                "paper_id": PAPER_ID,
                "workflow_arm": _load_config()["workflow_arm"],
                "review_state": "reviewed",
                "review_skipped": False,
                "final_verdict": stage_verdict(
                    "stage2_senior" if stage2_map[key]["adjudication"]["route_to_senior"] else "stage2_auto",
                    int(effective_stage2["stage_score"]),
                ),
                "stage1_stage_score": int(effective_stage1["stage_score"]),
                "stage1_decision_recommendation": stage1_decision,
                "stage2_stage_score": int(effective_stage2["stage_score"]),
                "stage2_decision_recommendation": decision_from_score(int(effective_stage2["stage_score"])),
                "source_record_provenance": effective_stage2["source_record_provenance"],
                "review_output": {
                    "stage1": {
                        "junior_nano": stage1_junior_nano.get(key),
                        "junior_mini": stage1_junior_mini.get(key),
                        "senior": stage1_senior.get(key),
                        "adjudication": stage1_map[key]["adjudication"],
                    },
                    "stage2": {
                        "junior_nano": stage2_junior_nano.get(key),
                        "junior_mini": stage2_junior_mini.get(key),
                        "senior": stage2_senior.get(key),
                        "adjudication": stage2_map[key]["adjudication"],
                    },
                },
                "fulltext_source_path": resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                "fulltext_resolution_status": resolution["resolution_status"],
            }
        )

    write_json(_combined_final_results_path(run_id), rows)
    metrics = compute_metrics_from_rows(results=rows, gold_records=load_jsonl(_gold_path()))
    payload = {
        "paper_id": PAPER_ID,
        "workflow_arm": _load_config()["workflow_arm"],
        "stage": "combined",
        "reviewed_count": reviewed_count,
        "missing_count": missing_count,
        "metrics": metrics,
        "auto_resolution_coverage": compute_auto_resolution_coverage(total_rows=cutoff_after, verification_rows=len(routed_keys)),
        "senior_route_rate": (len(routed_keys) / cutoff_after) if cutoff_after else 0.0,
        "senior_overturn_rate": (senior_overturn_count / len(route_events)) if route_events else 0.0,
    }
    write_json(_combined_metrics_path(run_id), payload)
    return payload


async def _run_pipeline(run_id: str, *, selection_mode: str, key_map: dict[str, set[str]] | None) -> None:
    _run_dir(run_id).mkdir(parents=True, exist_ok=True)
    _paper_dir(run_id).mkdir(parents=True, exist_ok=True)
    _request_log_path(run_id).touch(exist_ok=True)
    _response_log_path(run_id).touch(exist_ok=True)
    _failure_log_path(run_id).touch(exist_ok=True)
    _load_or_init_run_manifest(run_id, selection_mode=selection_mode, key_map=key_map)
    allowlist = (key_map or {}).get(PAPER_ID)
    runtime = _paper_runtime_inputs(run_id, key_allowlist=allowlist)
    prompt_assets = _load_prompt_assets()

    await _execute_specs(run_id, _prepare_stage1_junior_requests(run_id=run_id, role="junior_nano", runtime=runtime, prompt_assets=prompt_assets))
    await _execute_specs(run_id, _prepare_stage1_junior_requests(run_id=run_id, role="junior_mini", runtime=runtime, prompt_assets=prompt_assets))
    _materialize_phase_outputs(run_id)
    _mark_phase_completed(run_id, "stage1_juniors")

    await _execute_specs(run_id, _prepare_stage1_senior_requests(run_id=run_id, runtime=runtime, prompt_assets=prompt_assets))
    _materialize_phase_outputs(run_id)
    _build_stage1_outputs(run_id, key_allowlist=allowlist)
    _mark_phase_completed(run_id, "stage1_finalize")

    await _execute_specs(run_id, _prepare_stage2_junior_requests(run_id=run_id, role="junior_nano", runtime=runtime, prompt_assets=prompt_assets))
    await _execute_specs(run_id, _prepare_stage2_junior_requests(run_id=run_id, role="junior_mini", runtime=runtime, prompt_assets=prompt_assets))
    _materialize_phase_outputs(run_id)
    _mark_phase_completed(run_id, "stage2_juniors")

    await _execute_specs(run_id, _prepare_stage2_senior_requests(run_id=run_id, runtime=runtime, prompt_assets=prompt_assets))
    _materialize_phase_outputs(run_id)
    _build_combined_outputs(run_id, key_allowlist=allowlist)
    _build_disagreement_audit(run_id)
    summary_payload = build_run_summary_payload(_run_dir(run_id))
    write_json(_run_dir(run_id) / "matrix_summary.json", summary_payload)
    rendered_summary = render_summary_zh(summary_payload)
    (_run_dir(run_id) / "matrix_summary_zh.md").write_text(rendered_summary, encoding="utf-8")
    _summary_path(run_id).write_text(rendered_summary, encoding="utf-8")
    _paper_summary_path(run_id).write_text(rendered_summary, encoding="utf-8")
    _mark_phase_completed(run_id, "combined_finalize")


def _latest_run_id() -> str | None:
    runs_dir = BUNDLE_DIR / "runs"
    if not runs_dir.exists():
        return None
    candidates = sorted([path.name for path in runs_dir.iterdir() if path.is_dir()])
    return candidates[-1] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated criterion-ledger current-kernel experiment.")
    parser.add_argument("--mode", choices=["validate", "smoke", "run-all", "resume"], required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    if args.mode == "validate":
        import subprocess

        subprocess.run([sys.executable, str(BUNDLE_DIR / "tools" / "validate_bundle.py"), "--check-client"], check=True, cwd=str(REPO_ROOT))
        return 0

    if args.mode == "smoke":
        run_id = args.run_id or f"smoke_{now_run_id()}"
        key_map = _load_smoke_key_map()
        selection_mode = "smoke"
    elif args.mode == "resume":
        run_id = args.run_id or _latest_run_id()
        if not run_id:
            raise SystemExit("resume requires an existing run directory")
        manifest = read_json(_run_manifest_path(run_id))
        selection_mode = _selection_mode_for_resume(manifest, run_id)
        key_map = _key_map_for_resume(manifest, run_id)
    else:
        run_id = args.run_id or f"full_{now_run_id()}"
        key_map = None
        selection_mode = "full"

    asyncio.run(_run_pipeline(run_id, selection_mode=selection_mode, key_map=key_map))
    print(json.dumps({"run_dir": str(_run_dir(run_id))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
