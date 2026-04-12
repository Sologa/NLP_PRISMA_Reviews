from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowPhaseSpec(_StrictModel):
    phase_id: str
    stage: Literal["stage1", "stage2"]
    template: str
    asset_pattern: str
    output_filename: str
    uses_fulltext: bool = False
    requires_prior_stage: bool = False


class WorkflowGatePolicy(_StrictModel):
    selection_phase: str
    advance_decisions: list[Literal["include", "exclude", "maybe"]] = Field(default_factory=list)
    stop_decisions: list[Literal["include", "exclude", "maybe"]] = Field(default_factory=list)


class MergedWorkflowSpec(_StrictModel):
    workflow_id: str
    aliases: list[str] = Field(default_factory=list)
    workflow_arm: str
    stage_model: str
    supported_phases: list[WorkflowPhaseSpec]
    gate_policy: WorkflowGatePolicy
    result_mapping: dict[str, Any] = Field(default_factory=dict)


class MergedCriterionItem(_StrictModel):
    criterion_id: str
    criterion_type: Literal["inclusion", "exclusion"]
    criterion_text: str
    criterion_question: str
    assessment_policy: str | None = None


class MergedCriterionAsset(_StrictModel):
    paper_id: str
    stage: Literal["stage1", "stage2"]
    topic: str
    topic_definition: str
    decision_policy: str
    criteria: list[MergedCriterionItem]


class SourceRecordProvenance(_StrictModel):
    record_key: str
    record_title: str | None = None
    source: str | None = None
    source_id: str | None = None
    metadata_path: str
    runtime_prompts_path: str
    criteria_path: str
    fulltext_candidate_path: str
    fulltext_available: bool


class CriterionAssessment(_StrictModel):
    criterion_id: str
    status: Literal["YES", "NO", "UNCLEAR"]
    supporting_quotes: list[str] = Field(default_factory=list)
    counter_quotes: list[str] = Field(default_factory=list)
    missingness_reason: str | None = None
    notes: str = ""


class MergedStageModelOutput(_StrictModel):
    criterion_assessments: list[CriterionAssessment]
    stage_score: int = Field(ge=1, le=5)
    decision_rationale: str
    manual_review_needed: bool
    routing_note: str
    short_summary: str


class StageMergedReviewRecord(MergedStageModelOutput):
    paper_id: str
    candidate_key: str
    candidate_title: str
    stage: Literal["stage1", "stage2"]
    workflow_arm: str
    qa_asset_path: str
    criteria_path: str
    source_record_provenance: SourceRecordProvenance


class SingleReviewerMergedFinalRow(_StrictModel):
    key: str
    title: str
    paper_id: str
    workflow_arm: str
    stage_model: str
    review_state: str
    review_skipped: bool
    failed_phase: str | None = None
    discard_reason: str | None = None
    final_verdict: str
    stage1_stage_score: int | None = None
    stage1_decision_recommendation: Literal["include", "exclude", "maybe"] | None = None
    stage2_stage_score: int | None = None
    stage2_decision_recommendation: Literal["include", "exclude", "maybe"] | None = None
    stage1_review_path: str | None = None
    stage2_review_path: str | None = None
    source_record_provenance: SourceRecordProvenance | None = None
    review_output: dict[str, Any] | None = None
    fulltext_source_path: str | None = None
    fulltext_resolution_status: str | None = None
