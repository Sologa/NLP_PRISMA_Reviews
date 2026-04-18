from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


QUESTION_IDS = ("Q1", "Q2", "Q3", "Q4", "Q5")
PRIMARY_REVIEWER_ROLES = ("qa_gpt54nano", "qa_gpt41mini", "qa_gpt5mini")


class ScreeningQuestion(BaseModel):
    question_id: str
    question_text: str
    observable_only: bool = True
    coverage_note: str


class QuestionBundle(BaseModel):
    paper_id: str
    stage_id: str
    review_title: str
    generation_note: str
    questions: list[ScreeningQuestion]

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, value: list[ScreeningQuestion]) -> list[ScreeningQuestion]:
        if len(value) != len(QUESTION_IDS):
            raise ValueError("question bundle must contain exactly 5 questions")
        observed = [item.question_id for item in value]
        if tuple(observed) != QUESTION_IDS:
            raise ValueError(f"question ids must be {QUESTION_IDS}")
        return value


class QAAnswer(BaseModel):
    question_id: str
    answer_label: Literal["positive", "neutral", "negative"]
    reasoning_path: str
    confidence: float = Field(ge=0.0, le=1.0)
    extra_information: str


class ReviewerRating(BaseModel):
    reviewer_role: Literal["qa_gpt54nano", "qa_gpt41mini", "qa_gpt5mini"]
    rating: float = Field(ge=0.0, le=1.0)


class PrimaryReviewOutput(BaseModel):
    candidate_key: str
    reviewer_role: Literal["qa_gpt54nano", "qa_gpt41mini", "qa_gpt5mini"]
    answers: list[QAAnswer]
    overall_note: str

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: list[QAAnswer]) -> list[QAAnswer]:
        if len(value) != len(QUESTION_IDS):
            raise ValueError("primary review must contain exactly 5 answers")
        observed = [item.question_id for item in value]
        if tuple(observed) != QUESTION_IDS:
            raise ValueError(f"answer ids must be {QUESTION_IDS}")
        return value


class DebateAnswer(QAAnswer):
    does_previous_answer_change: Literal["yes", "no"]
    why_change_or_not: str


class DebateReviewOutput(BaseModel):
    candidate_key: str
    reviewer_role: Literal["qa_gpt54nano", "qa_gpt41mini", "qa_gpt5mini"]
    answers: list[DebateAnswer]
    overall_note: str

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: list[DebateAnswer]) -> list[DebateAnswer]:
        if len(value) != len(QUESTION_IDS):
            raise ValueError("debate review must contain exactly 5 answers")
        observed = [item.question_id for item in value]
        if tuple(observed) != QUESTION_IDS:
            raise ValueError(f"answer ids must be {QUESTION_IDS}")
        return value


class JudgeAnswer(QAAnswer):
    reviewer_ratings: list[ReviewerRating]
    best_reviewer: Literal["qa_gpt54nano", "qa_gpt41mini", "qa_gpt5mini"]
    best_answer_reason: str
    worst_reviewer: Literal["qa_gpt54nano", "qa_gpt41mini", "qa_gpt5mini"]
    worst_answer_reason: str

    @field_validator("reviewer_ratings")
    @classmethod
    def validate_ratings(cls, value: list[ReviewerRating]) -> list[ReviewerRating]:
        keys = tuple(sorted(item.reviewer_role for item in value))
        if keys != tuple(sorted(PRIMARY_REVIEWER_ROLES)):
            raise ValueError("judge ratings must include all three primary reviewers")
        return value


class JudgeReviewOutput(BaseModel):
    candidate_key: str
    reviewer_role: Literal["judge_gpt5mini"]
    answers: list[JudgeAnswer]
    adjudication_rationale: str

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: list[JudgeAnswer]) -> list[JudgeAnswer]:
        if len(value) != len(QUESTION_IDS):
            raise ValueError("judge review must contain exactly 5 answers")
        observed = [item.question_id for item in value]
        if tuple(observed) != QUESTION_IDS:
            raise ValueError(f"answer ids must be {QUESTION_IDS}")
        return value

    @model_validator(mode="after")
    def validate_best_worst_not_same(self) -> "JudgeReviewOutput":
        for answer in self.answers:
            if answer.best_reviewer == answer.worst_reviewer:
                raise ValueError("best_reviewer and worst_reviewer must differ")
        return self
