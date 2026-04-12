from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .merged_batch_types import SingleReviewerMergedFinalRow, SourceRecordProvenance, WorkflowGatePolicy


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectWorkflowPhaseSpec(_StrictModel):
    phase_id: str
    stage: Literal["stage1", "stage2"]
    template: str
    output_filename: str
    uses_fulltext: bool = False
    requires_prior_stage: bool = False


class DirectWorkflowSpec(_StrictModel):
    workflow_id: str
    aliases: list[str] = Field(default_factory=list)
    workflow_arm: str
    stage_model: str
    supported_phases: list[DirectWorkflowPhaseSpec]
    gate_policy: WorkflowGatePolicy
    result_mapping: dict[str, Any] = Field(default_factory=dict)


class DirectReviewModelOutput(_StrictModel):
    stage_score: int = Field(ge=1, le=5)
    decision_recommendation: Literal["include", "exclude", "maybe"]
    satisfied_inclusion_points: list[str] = Field(default_factory=list)
    triggered_exclusion_points: list[str] = Field(default_factory=list)
    uncertain_points: list[str] = Field(default_factory=list)
    evidence_highlights: list[str] = Field(default_factory=list)
    decision_rationale: str


class StageDirectReviewRecord(DirectReviewModelOutput):
    paper_id: str
    candidate_key: str
    candidate_title: str
    stage: Literal["stage1", "stage2"]
    workflow_arm: str
    criteria_path: str
    source_record_provenance: SourceRecordProvenance


__all__ = [
    "DirectReviewModelOutput",
    "DirectWorkflowPhaseSpec",
    "DirectWorkflowSpec",
    "SingleReviewerMergedFinalRow",
    "SourceRecordProvenance",
    "StageDirectReviewRecord",
    "WorkflowGatePolicy",
]
