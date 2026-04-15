from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

from experiment_workflows import CriterionAssessment, MergedStageModelOutput, decision_from_score


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ROLE_MODEL_SETTINGS: dict[str, dict[str, Any]] = {
    "junior_nano": {"model": "gpt-5-nano", "reasoning_effort": "medium"},
    "junior_mini": {"model": "gpt-4.1-mini", "reasoning_effort": None},
    "senior": {"model": "gpt-5-mini", "reasoning_effort": "medium"},
}


class SeniorMergedStageModelOutput(MergedStageModelOutput):
    adjudication_source: Literal["junior_nano", "junior_mini", "senior_reassessment", "hybrid"]
    disagreement_resolution: str
    overridden_fields: list[str] = Field(default_factory=list)


def role_model_settings(role: str) -> dict[str, Any]:
    if role not in ROLE_MODEL_SETTINGS:
        raise KeyError(role)
    return dict(ROLE_MODEL_SETTINGS[role])


def build_dynamic_senior_response_model(schema_name: str, *, criterion_ids: list[str]) -> type[BaseModel]:
    ordered_ids = tuple(dict.fromkeys(criterion_ids))
    if not ordered_ids:
        raise ValueError(f"{schema_name} requires at least one criterion id")
    criterion_id_literal = Literal.__getitem__(ordered_ids)
    criterion_assessment_model = create_model(
        f"{schema_name}CriterionAssessment",
        __base__=CriterionAssessment,
        criterion_id=(criterion_id_literal, ...),
    )
    return create_model(
        schema_name,
        __base__=SeniorMergedStageModelOutput,
        criterion_assessments=(list[criterion_assessment_model], ...),  # type: ignore[valid-type]
    )


def _status_map(review: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in review.get("criterion_assessments", []):
        criterion_id = str(item.get("criterion_id") or "").strip()
        if criterion_id:
            out[criterion_id] = str(item.get("status") or "").strip().upper()
    return out


def _decision(review: dict[str, Any]) -> str:
    return decision_from_score(int(review.get("stage_score") or 3))


def _criterion_conflicts(nano_map: dict[str, str], mini_map: dict[str, str]) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    for criterion_id in sorted(set(nano_map) | set(mini_map)):
        nano_status = nano_map.get(criterion_id, "")
        mini_status = mini_map.get(criterion_id, "")
        if nano_status != mini_status:
            conflicts.append(
                {
                    "criterion_id": criterion_id,
                    "junior_nano_status": nano_status,
                    "junior_mini_status": mini_status,
                }
            )
    return conflicts


def _unclear_criterion_ids(nano_map: dict[str, str], mini_map: dict[str, str]) -> list[str]:
    out: list[str] = []
    for criterion_id in sorted(set(nano_map) | set(mini_map)):
        if nano_map.get(criterion_id) == "UNCLEAR" or mini_map.get(criterion_id) == "UNCLEAR":
            out.append(criterion_id)
    return out


def _any_inclusion_not_no(nano_map: dict[str, str], mini_map: dict[str, str]) -> bool:
    for criterion_id in sorted(set(nano_map) | set(mini_map)):
        if not criterion_id.upper().startswith("I"):
            continue
        nano_status = nano_map.get(criterion_id, "")
        mini_status = mini_map.get(criterion_id, "")
        if nano_status != "NO" or mini_status != "NO":
            return True
    return False


def _auto_stage_score(decision: str, junior_nano: dict[str, Any], junior_mini: dict[str, Any]) -> int:
    nano_score = int(junior_nano.get("stage_score") or 3)
    mini_score = int(junior_mini.get("stage_score") or 3)
    if decision == "include":
        return min(nano_score, mini_score)
    if decision == "exclude":
        return max(nano_score, mini_score)
    return 3


def build_adjudication_decision(*, stage: str, junior_nano: dict[str, Any], junior_mini: dict[str, Any]) -> dict[str, Any]:
    nano_map = _status_map(junior_nano)
    mini_map = _status_map(junior_mini)
    nano_decision = _decision(junior_nano)
    mini_decision = _decision(junior_mini)
    conflicts = _criterion_conflicts(nano_map, mini_map)
    unclear_ids = _unclear_criterion_ids(nano_map, mini_map)
    reasons: list[str] = []
    auto_final_decision: str | None = None

    if stage == "stage1":
        if nano_decision == mini_decision == "include":
            if conflicts:
                reasons.append("criterion_conflict")
            if unclear_ids:
                reasons.append("criterion_unclear")
            if any(status == "YES" for status in [value for key, value in nano_map.items() if key.upper().startswith("E")]):
                reasons.append("stage1_include_with_exclusion_signal")
            if any(status == "YES" for status in [value for key, value in mini_map.items() if key.upper().startswith("E")]):
                if "stage1_include_with_exclusion_signal" not in reasons:
                    reasons.append("stage1_include_with_exclusion_signal")
            if not reasons:
                auto_final_decision = "include"
        elif nano_decision == mini_decision == "exclude":
            if _any_inclusion_not_no(nano_map, mini_map):
                reasons.append("stage1_exclude_with_positive_or_unclear_inclusion")
            if conflicts:
                reasons.append("criterion_conflict")
            if not reasons:
                auto_final_decision = "exclude"
        else:
            reasons.append("decision_disagreement")
            if conflicts:
                reasons.append("criterion_conflict")
            if unclear_ids:
                reasons.append("criterion_unclear")
    else:
        if nano_decision != mini_decision:
            reasons.append("decision_disagreement")
        if conflicts:
            reasons.append("criterion_conflict")
        if unclear_ids:
            reasons.append("criterion_unclear")
        if not reasons:
            auto_final_decision = nano_decision

    route_to_senior = auto_final_decision is None
    return {
        "stage": stage,
        "junior_nano_decision": nano_decision,
        "junior_mini_decision": mini_decision,
        "criterion_conflicts": conflicts,
        "unclear_criterion_ids": unclear_ids,
        "route_to_senior": route_to_senior,
        "reasons": reasons,
        "auto_final_decision": auto_final_decision,
        "auto_resolution_stage_score": _auto_stage_score(auto_final_decision, junior_nano, junior_mini)
        if auto_final_decision is not None
        else None,
        "final_source": "senior" if route_to_senior else "auto",
    }


def effective_stage_review(
    *,
    junior_nano: dict[str, Any],
    junior_mini: dict[str, Any],
    senior: dict[str, Any] | None,
    adjudication: dict[str, Any],
) -> dict[str, Any]:
    if adjudication.get("route_to_senior"):
        if senior is None:
            raise ValueError("senior review required but missing")
        return senior
    auto_decision = str(adjudication.get("auto_final_decision") or "")
    stage_score = int(adjudication.get("auto_resolution_stage_score") or 3)
    source = junior_nano if _decision(junior_nano) == auto_decision else junior_mini
    payload = dict(source)
    payload["stage_score"] = stage_score
    return payload
