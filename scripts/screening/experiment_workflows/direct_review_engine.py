from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .common import (
    decision_from_score,
    json_text,
    read_json,
    read_jsonl,
    safe_text,
    write_json,
    write_jsonl,
)
from .direct_review_types import DirectReviewModelOutput, DirectWorkflowSpec, SourceRecordProvenance, StageDirectReviewRecord
from .merged_batch_engine import (
    apply_head_tail_limit,
    build_cutoff_review_row,
    build_fulltext_resolution_audit,
    build_source_record_provenance,
    collect_phase_issues_by_key,
    criteria_text_for_stage,
    custom_id,
    fulltext_payload_from_resolution,
    load_candidates,
    load_cutoff_result,
    metadata_payload,
    now_run_id,
    relative_path,
    stage_verdict,
)


def load_direct_workflow_spec(path: Path) -> DirectWorkflowSpec:
    return DirectWorkflowSpec.model_validate(read_json(path))


def build_direct_stage_response_model(_schema_name: str) -> type[BaseModel]:
    return DirectReviewModelOutput


def build_direct_stage_validator(
    *,
    paper_id: str,
    stage: str,
    candidate_key: str,
    candidate_title: str,
) -> Any:
    def validate(payload: BaseModel) -> None:
        try:
            DirectReviewModelOutput.model_validate(payload)
        except Exception as exc:  # pragma: no cover
            raise ValueError(
                f"invalid direct-review payload for {paper_id}/{stage}/{candidate_key} ({candidate_title}): {exc}"
            ) from exc

    return validate


def build_direct_stage_review_record(
    *,
    model_output: dict[str, Any],
    paper_id: str,
    candidate_key: str,
    candidate_title: str,
    stage: str,
    workflow_arm: str,
    criteria_path: str,
    provenance: SourceRecordProvenance,
) -> StageDirectReviewRecord:
    payload = dict(model_output)
    payload["decision_recommendation"] = decision_from_score(int(payload["stage_score"]))
    payload.update(
        {
            "paper_id": paper_id,
            "candidate_key": candidate_key,
            "candidate_title": candidate_title,
            "stage": stage,
            "workflow_arm": workflow_arm,
            "criteria_path": criteria_path,
            "source_record_provenance": provenance.model_dump(mode="json"),
        }
    )
    return StageDirectReviewRecord.model_validate(payload)


def build_direct_stage_prompt_context(
    *,
    stage: str,
    workflow_arm: str,
    paper_id: str,
    candidate_key: str,
    candidate_title: str,
    criteria_payload: str,
    metadata: dict[str, Any],
    response_schema_hint: str,
    provenance: SourceRecordProvenance,
    prior_stage_review: dict[str, Any] | None = None,
    fulltext_resolution: dict[str, Any] | None = None,
    fulltext_text: str | None = None,
) -> dict[str, Any]:
    context = {
        "WORKFLOW_ARM": workflow_arm,
        "PAPER_ID": paper_id,
        "CANDIDATE_KEY": candidate_key,
        "CANDIDATE_TITLE": candidate_title,
        "STAGE_CRITERIA_JSON_CONTENT": criteria_payload,
        "METADATA_JSON": json_text(metadata),
        "TITLE": safe_text(metadata.get("title") or metadata.get("query_title")),
        "ABSTRACT": safe_text(metadata.get("abstract")),
        "SOURCE_RECORD_PROVENANCE_JSON": json_text(provenance.model_dump(mode="json")),
        "REVIEW_OUTPUT_JSON_SCHEMA_HINT": response_schema_hint,
    }
    if stage == "stage2":
        context["PRIOR_STAGE_REVIEW_JSON"] = json_text(prior_stage_review or {})
        context["FULLTEXT_RESOLUTION_JSON"] = json_text(fulltext_resolution or {})
        context["FULLTEXT_TEXT"] = fulltext_text or ""
    return context


def phase_success_rows_by_paper_direct(
    *,
    parsed_payload: dict[str, Any],
    spec_context: dict[str, dict[str, Any]],
    stage: str,
    workflow_arm: str,
) -> dict[str, list[dict[str, Any]]]:
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    success_by_id = {item["custom_id"]: item for item in parsed_payload.get("successes", [])}
    for custom, context in spec_context.items():
        item = success_by_id.get(custom)
        if item is None:
            continue
        record = build_direct_stage_review_record(
            model_output=item["parsed"],
            paper_id=context["paper_id"],
            candidate_key=context["candidate_key"],
            candidate_title=context["candidate_title"],
            stage=stage,
            workflow_arm=workflow_arm,
            criteria_path=context["criteria_path"],
            provenance=SourceRecordProvenance.model_validate(context["provenance"]),
        )
        rows_by_paper[context["paper_id"]].append(record.model_dump(mode="json"))
    return rows_by_paper


__all__ = [
    "DirectReviewModelOutput",
    "DirectWorkflowSpec",
    "StageDirectReviewRecord",
    "apply_head_tail_limit",
    "build_cutoff_review_row",
    "build_direct_stage_prompt_context",
    "build_direct_stage_response_model",
    "build_direct_stage_review_record",
    "build_direct_stage_validator",
    "build_fulltext_resolution_audit",
    "build_source_record_provenance",
    "collect_phase_issues_by_key",
    "criteria_text_for_stage",
    "custom_id",
    "decision_from_score",
    "fulltext_payload_from_resolution",
    "json_text",
    "load_candidates",
    "load_cutoff_result",
    "load_direct_workflow_spec",
    "metadata_payload",
    "now_run_id",
    "phase_success_rows_by_paper_direct",
    "read_json",
    "read_jsonl",
    "relative_path",
    "stage_verdict",
    "write_json",
    "write_jsonl",
]
