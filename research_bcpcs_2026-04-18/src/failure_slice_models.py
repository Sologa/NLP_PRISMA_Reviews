#!/usr/bin/env python3
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSpan(StrictModel):
    quote: str = Field(min_length=1)
    location: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    source_field: Literal["title", "abstract", "metadata", "full_text", "criteria", "other"]


MissingnessReason = Literal[
    "none",
    "not_observed_stage1",
    "deferred_to_stage2",
    "semantic_non_fit",
    "retrieval_failure",
    "metadata_ambiguity",
    "source_gold_tension",
    "evidence_incomplete",
    "not_applicable",
]


class EvidenceLedgerRow(StrictModel):
    candidate_key: str = Field(min_length=1)
    stage: Literal["stage1", "stage2"]
    claim_id: str = Field(min_length=1)
    evidence_status: Literal["support", "refute", "unknown", "not_applicable"]
    support_spans: list[EvidenceSpan] = Field(default_factory=list)
    refute_spans: list[EvidenceSpan] = Field(default_factory=list)
    missingness_reason: MissingnessReason
    confidence: float = Field(ge=0, le=1)
    verifier_model: str = Field(min_length=1)
    quote: str
    location: str
    source_path: str = Field(min_length=1)
    span_validated: bool


class StageReviewOutput(StrictModel):
    candidate_key: str = Field(min_length=1)
    stage: Literal["stage1", "stage2"]
    final_stage_decision: Literal["include", "exclude", "maybe", "route_to_stage2", "unknown"]
    decision_rationale: str = Field(min_length=1)
    route_reason: str
    unknown_reason: str
    missingness_reason: MissingnessReason
    confidence: float = Field(ge=0, le=1)
    evidence_ledger: list[EvidenceLedgerRow] = Field(min_length=1)

    @model_validator(mode="after")
    def _ledger_matches_header(self) -> "StageReviewOutput":
        for row in self.evidence_ledger:
            if row.candidate_key != self.candidate_key:
                raise ValueError("ledger candidate_key mismatch")
            if row.stage != self.stage:
                raise ValueError("ledger stage mismatch")
        return self


def validate_stage_output(payload: StageReviewOutput, *, stage: str, candidate_key: str) -> None:
    if payload.stage != stage:
        raise ValueError(f"Expected stage={stage}, observed={payload.stage}")
    if payload.candidate_key != candidate_key:
        raise ValueError(f"Expected candidate_key={candidate_key}, observed={payload.candidate_key}")
