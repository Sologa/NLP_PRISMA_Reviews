#!/usr/bin/env python3
"""Run QA-first experiment v0 arms and write experiment-only results."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]

sys.path.insert(0, str(SCRIPT_DIR))
import render_prompt  # noqa: E402


RESULTS_ROOT = REPO_ROOT / "screening" / "results" / "qa_first_v0_2409_2511_2026-03-18"
PAPERS = ("2409.13738", "2511.13936")
ARMS = ("qa-only", "qa+synthesis")
JUNIOR_MODELS = (
    ("JuniorNano", "gpt-5-nano"),
    ("JuniorMini", "gpt-4.1-mini"),
)
WORKFLOW_MODEL = "gpt-4.1-mini"
SENIOR_MODEL = "gpt-4.1-mini"
FULLTEXT_CHAR_LIMIT = 32000


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class QAAnswer(_StrictModel):
    qid: str
    criterion_family: str
    answer_state: Literal["present", "absent", "unclear"]
    answer_rationale: str
    supporting_quotes: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    missingness_reason: str | None = None
    stage2_handoff_note: str | None = None
    conflict_note: str | None = None
    resolves_stage1: str | bool | None = None
    candidate_synthesis_fields: list[str] | None = None


class QAReviewOutput(_StrictModel):
    paper_id: str
    stage: Literal["stage1", "stage2"]
    workflow_arm: str
    qa_source_path: str
    reviewer_guardrails_applied: list[str] = Field(default_factory=list)
    answers: list[QAAnswer]


class FieldRecord(_StrictModel):
    field_name: str
    state: str
    normalized_value: str | list[str] | dict[str, str] | None = None
    supporting_quotes: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    missingness_reason: str | None = None
    conflict_note: str | None = None
    derived_from_qids: list[str] = Field(default_factory=list)
    stage_handoff_status: str


class SynthesisOutput(_StrictModel):
    paper_id: str
    paper_title: str
    stage: Literal["stage1", "stage2"]
    arm: str
    field_records: list[FieldRecord]


class CriterionMappingItem(_StrictModel):
    criterion_text: str
    status: str
    support_ids: list[str] = Field(default_factory=list)


class CriteriaEvaluationOutput(_StrictModel):
    paper_id: str
    stage: Literal["stage1", "stage2"]
    arm: str
    stage_score: int = Field(ge=1, le=5)
    decision_recommendation: str
    criterion_mapping: list[CriterionMappingItem] = Field(default_factory=list)
    criterion_conflicts: list[str] = Field(default_factory=list)
    decision_rationale: str
    manual_review_needed: bool
    routing_note: str


class SeniorOutput(_StrictModel):
    paper_id: str
    stage: Literal["stage1", "stage2"]
    arm: str
    senior_stage_score: int = Field(ge=1, le=5)
    decision_recommendation: str
    decision_rationale: str
    criterion_conflicts: list[str] = Field(default_factory=list)
    routing_note: str
    manual_review_needed: bool


def _load_env_file() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_verdict_label(verdict: str | None) -> str:
    text = str(verdict or "").strip().lower()
    m = re.match(r"^\s*([a-z]+)", text)
    return m.group(1) if m else "unknown"


def _derive_final_verdict(row: dict[str, Any]) -> str:
    senior_eval = row.get("round-B_SeniorLead_evaluation")
    if senior_eval is not None:
        senior_eval = int(senior_eval)
        if senior_eval >= 4:
            return f"include (senior:{senior_eval})"
        if senior_eval <= 2:
            return f"exclude (senior:{senior_eval})"
        return f"maybe (senior:{senior_eval})"

    scores = []
    for field in ("round-A_JuniorNano_evaluation", "round-A_JuniorMini_evaluation"):
        value = row.get(field)
        if value is None:
            continue
        scores.append(int(value))
    if len(scores) == 2:
        if all(score >= 4 for score in scores):
            return f"include (junior:{scores[0]},{scores[1]})"
        if all(score <= 2 for score in scores):
            return f"exclude (junior:{scores[0]},{scores[1]})"
        return f"maybe (junior:{scores[0]},{scores[1]})"
    if len(scores) == 1:
        score = scores[0]
        if score >= 4:
            return f"include (junior:{score})"
        if score <= 2:
            return f"exclude (junior:{score})"
        return f"maybe (junior:{score})"
    return "需再評估 (no_score)"


def _load_stage1_records(paper_id: str) -> list[dict[str, Any]]:
    return _read_json(REPO_ROOT / "screening" / "data" / f"{paper_id}_full" / "arxiv_metadata.full.json")


def _criteria_paths(paper_id: str) -> tuple[Path, Path]:
    return (
        REPO_ROOT / "criteria_stage1" / f"{paper_id}.json",
        REPO_ROOT / "criteria_stage2" / f"{paper_id}.json",
    )


def _qa_asset_path(paper_id: str, stage: str) -> Path:
    return BUNDLE_DIR / "qa" / f"{paper_id}.{stage}.seed_qa.json"


def _template_path(filename: str) -> Path:
    return BUNDLE_DIR / "templates" / filename


def _sample_path(filename: str) -> Path:
    return BUNDLE_DIR / "samples" / filename


def _arm_dir(paper_id: str, arm: str) -> Path:
    return RESULTS_ROOT / f"{paper_id}__{arm}"


def _safe_title(value: Any) -> str:
    return str(value or "").strip()


def _fulltext_path(paper_id: str, key: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "mds" / f"{key}.md"


def _cut_fulltext(text: str) -> tuple[str, dict[str, Any]]:
    lines = text.splitlines()
    marker = None
    line_no = None
    for idx, line in enumerate(lines, start=1):
        normalized = line.strip().lower().rstrip(":")
        if normalized in {"references", "bibliography"}:
            marker = line.strip()
            line_no = idx
            text = "\n".join(lines[: idx - 1])
            break
    total_chars = len("\n".join(lines))
    used_text = text[:FULLTEXT_CHAR_LIMIT]
    return used_text, {
        "fulltext_chars_total": total_chars,
        "fulltext_chars_used": len(used_text),
        "reference_cut_applied": marker is not None,
        "reference_cut_method": "heading" if marker is not None else None,
        "reference_cut_marker": marker,
        "reference_cut_line_no": line_no,
    }


class PromptAssets:
    def __init__(self) -> None:
        self.templates = {
            "stage1_qa_only_reviewer": _load_text(_template_path("01_stage1_qa_only_reviewer_TEMPLATE.md")),
            "stage2_qa_only_reviewer": _load_text(_template_path("02_stage2_qa_only_reviewer_TEMPLATE.md")),
            "stage1_qa_synthesis_reviewer": _load_text(_template_path("03_stage1_qa_synthesis_reviewer_TEMPLATE.md")),
            "stage2_qa_synthesis_reviewer": _load_text(_template_path("04_stage2_qa_synthesis_reviewer_TEMPLATE.md")),
            "synthesis_builder": _load_text(_template_path("05_synthesis_builder_TEMPLATE.md")),
            "criteria_evaluator_from_qa_only": _load_text(_template_path("06_criteria_evaluator_from_qa_only_TEMPLATE.md")),
            "criteria_evaluator_from_synthesis": _load_text(_template_path("07_criteria_evaluator_from_synthesis_TEMPLATE.md")),
            "stage1_senior_from_qa_only": _load_text(_template_path("08_stage1_senior_from_qa_only_TEMPLATE.md")),
            "stage1_senior_from_synthesis": _load_text(_template_path("09_stage1_senior_from_synthesis_TEMPLATE.md")),
            "stage2_senior_from_qa_only": _load_text(_template_path("10_stage2_senior_from_qa_only_TEMPLATE.md")),
            "stage2_senior_from_synthesis": _load_text(_template_path("11_stage2_senior_from_synthesis_TEMPLATE.md")),
        }
        self.schema_hints = {
            "qa_output": _load_text(_sample_path("sample_reviewer_qa_output.json")),
            "synthesis_output": _load_text(_sample_path("sample_synthesis_output.json")),
            "criteria_eval_output": _load_text(_sample_path("sample_criteria_evaluation_output.json")),
            "senior_output": _load_text(_sample_path("sample_senior_output.json")),
        }
        self.synthesis_schema_text = _load_text(BUNDLE_DIR / "schemas" / "minimal_synthesis_schema.yaml")


class BundleContext:
    def __init__(self, assets: PromptAssets) -> None:
        self.assets = assets
        self.qa_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self.criteria_text_cache: dict[tuple[str, str], str] = {}

    def qa_asset(self, paper_id: str, stage: str) -> dict[str, Any]:
        key = (paper_id, stage)
        if key not in self.qa_cache:
            self.qa_cache[key] = _read_json(_qa_asset_path(paper_id, stage))
        return self.qa_cache[key]

    def criteria_text(self, paper_id: str, stage: str) -> str:
        key = (paper_id, stage)
        if key not in self.criteria_text_cache:
            stage1_path, stage2_path = _criteria_paths(paper_id)
            path = stage1_path if stage == "stage1" else stage2_path
            self.criteria_text_cache[key] = _load_text(path)
        return self.criteria_text_cache[key]

    def render(self, template_key: str, context: dict[str, Any]) -> str:
        return render_prompt._render(self.assets.templates[template_key], context, strict=True)


class LLMRunner:
    def __init__(self, client: AsyncOpenAI, concurrency: int) -> None:
        self.client = client
        self.semaphore = asyncio.Semaphore(concurrency)

    async def call(self, *, model: str, prompt: str, response_model: type[BaseModel]) -> BaseModel:
        delay = 2.0
        last_error: Exception | None = None
        for attempt in range(1, 6):
            try:
                async with self.semaphore:
                    response = await self.client.beta.chat.completions.parse(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format=response_model,
                        timeout=90,
                    )
                parsed = response.choices[0].message.parsed
                if parsed is None:
                    raise RuntimeError("Structured response was empty.")
                return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                print(
                    f"[retry] model={model} attempt={attempt} error={type(exc).__name__}: {exc}",
                    flush=True,
                )
                if attempt == 5:
                    break
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError(f"Model call failed after retries: {last_error}") from last_error


def _base_context(
    *,
    paper_id: str,
    record: dict[str, Any],
    stage: str,
    arm: str,
    bundle: BundleContext,
) -> dict[str, Any]:
    stage1_path, stage2_path = _criteria_paths(paper_id)
    qa_asset_path = _qa_asset_path(paper_id, stage)
    qa_asset = bundle.qa_asset(paper_id, stage)
    metadata = {
        "key": record.get("key"),
        "source": record.get("source"),
        "source_id": record.get("source_id"),
        "match_status": record.get("match_status"),
        "missing_reason": record.get("missing_reason"),
        "published_date": record.get("published_date"),
        "fulltext_candidate_path": str(_fulltext_path(paper_id, str(record.get("key") or ""))),
        "fulltext_available": _fulltext_path(paper_id, str(record.get("key") or "")).exists(),
    }
    return {
        "PAPER_ID": paper_id,
        "PAPER_TITLE": _safe_title(record.get("title") or record.get("query_title")),
        "STAGE": stage,
        "TARGET_STAGE": stage,
        "WORKFLOW_ARM": arm,
        "CURRENT_STAGE1_CRITERIA_JSON_PATH": str(stage1_path.relative_to(REPO_ROOT)),
        "CURRENT_STAGE2_CRITERIA_JSON_PATH": str(stage2_path.relative_to(REPO_ROOT)),
        "CURRENT_STAGE1_CRITERIA_JSON_CONTENT": bundle.criteria_text(paper_id, "stage1"),
        "CURRENT_STAGE2_CRITERIA_JSON_CONTENT": bundle.criteria_text(paper_id, "stage2"),
        "QA_JSON_PATH": str(qa_asset_path.relative_to(REPO_ROOT)),
        "QA_JSON_CONTENT": _json_text(qa_asset),
        "REVIEWER_GUARDRAILS_JSON": _json_text(qa_asset.get("reviewer_guardrails", [])),
        "TITLE": _safe_title(record.get("title") or record.get("query_title")),
        "ABSTRACT": _safe_title(record.get("abstract")),
        "FULLTEXT_TEXT": "",
        "METADATA_JSON": _json_text(metadata),
        "PRIOR_STAGE_OUTPUT_JSON": "{}",
        "CURRENT_QA_OUTPUT_JSON": "{}",
        "SYNTHESIS_OBJECT_JSON": "{}",
        "JUNIOR_QA_OUTPUTS_JSON": "[]",
        "JUNIOR_SYNTHESIS_OUTPUTS_JSON": "[]",
        "JUNIOR_DECISION_OUTPUTS_JSON": "[]",
        "SYNTHESIS_SCHEMA_PATH": str((BUNDLE_DIR / "schemas" / "minimal_synthesis_schema.yaml").relative_to(REPO_ROOT)),
        "SYNTHESIS_SCHEMA_CONTENT": bundle.assets.synthesis_schema_text,
        "QA_OUTPUT_JSON_SCHEMA_HINT": bundle.assets.schema_hints["qa_output"],
        "SYNTHESIS_OUTPUT_JSON_SCHEMA_HINT": bundle.assets.schema_hints["synthesis_output"],
        "CRITERIA_EVAL_OUTPUT_JSON_SCHEMA_HINT": bundle.assets.schema_hints["criteria_eval_output"],
        "SENIOR_OUTPUT_JSON_SCHEMA_HINT": bundle.assets.schema_hints["senior_output"],
    }


async def _run_stage1_junior(
    *,
    llm: LLMRunner,
    bundle: BundleContext,
    paper_id: str,
    arm: str,
    record: dict[str, Any],
    reviewer_name: str,
    model: str,
) -> dict[str, Any]:
    context = _base_context(paper_id=paper_id, record=record, stage="stage1", arm=arm, bundle=bundle)
    reviewer_template = "stage1_qa_only_reviewer" if arm == "qa-only" else "stage1_qa_synthesis_reviewer"
    reviewer_prompt = bundle.render(reviewer_template, context)
    qa_output = await llm.call(model=model, prompt=reviewer_prompt, response_model=QAReviewOutput)

    synthesis_output: SynthesisOutput | None = None
    if arm == "qa+synthesis":
        synth_context = dict(context)
        synth_context["PRIOR_STAGE_OUTPUT_JSON"] = "{}"
        synth_context["CURRENT_QA_OUTPUT_JSON"] = _json_text(qa_output.model_dump())
        synth_prompt = bundle.render("synthesis_builder", synth_context)
        synthesis_output = await llm.call(model=WORKFLOW_MODEL, prompt=synth_prompt, response_model=SynthesisOutput)

    eval_context = dict(context)
    if arm == "qa-only":
        eval_context["PRIOR_STAGE_OUTPUT_JSON"] = _json_text(qa_output.model_dump())
        eval_template = "criteria_evaluator_from_qa_only"
    else:
        eval_context["SYNTHESIS_OBJECT_JSON"] = _json_text(synthesis_output.model_dump())
        eval_template = "criteria_evaluator_from_synthesis"
    eval_prompt = bundle.render(eval_template, eval_context)
    eval_output = await llm.call(model=WORKFLOW_MODEL, prompt=eval_prompt, response_model=CriteriaEvaluationOutput)

    return {
        "reviewer": reviewer_name,
        "model": model,
        "reviewer_output": qa_output.model_dump(),
        "synthesis_output": synthesis_output.model_dump() if synthesis_output else None,
        "evaluator_output": eval_output.model_dump(),
    }


async def _run_stage2_junior(
    *,
    llm: LLMRunner,
    bundle: BundleContext,
    paper_id: str,
    arm: str,
    record: dict[str, Any],
    reviewer_name: str,
    model: str,
    prior_stage_output: dict[str, Any],
    fulltext_text: str,
) -> dict[str, Any]:
    context = _base_context(paper_id=paper_id, record=record, stage="stage2", arm=arm, bundle=bundle)
    context["PRIOR_STAGE_OUTPUT_JSON"] = _json_text(prior_stage_output)
    context["FULLTEXT_TEXT"] = fulltext_text
    reviewer_template = "stage2_qa_only_reviewer" if arm == "qa-only" else "stage2_qa_synthesis_reviewer"
    reviewer_prompt = bundle.render(reviewer_template, context)
    qa_output = await llm.call(model=model, prompt=reviewer_prompt, response_model=QAReviewOutput)

    synthesis_output: SynthesisOutput | None = None
    if arm == "qa+synthesis":
        synth_context = dict(context)
        synth_context["PRIOR_STAGE_OUTPUT_JSON"] = _json_text(prior_stage_output)
        synth_context["CURRENT_QA_OUTPUT_JSON"] = _json_text(qa_output.model_dump())
        synth_prompt = bundle.render("synthesis_builder", synth_context)
        synthesis_output = await llm.call(model=WORKFLOW_MODEL, prompt=synth_prompt, response_model=SynthesisOutput)

    eval_context = dict(context)
    if arm == "qa-only":
        eval_context["PRIOR_STAGE_OUTPUT_JSON"] = _json_text(qa_output.model_dump())
        eval_template = "criteria_evaluator_from_qa_only"
    else:
        eval_context["SYNTHESIS_OBJECT_JSON"] = _json_text(synthesis_output.model_dump())
        eval_template = "criteria_evaluator_from_synthesis"
    eval_prompt = bundle.render(eval_template, eval_context)
    eval_output = await llm.call(model=WORKFLOW_MODEL, prompt=eval_prompt, response_model=CriteriaEvaluationOutput)

    return {
        "reviewer": reviewer_name,
        "model": model,
        "reviewer_output": qa_output.model_dump(),
        "synthesis_output": synthesis_output.model_dump() if synthesis_output else None,
        "evaluator_output": eval_output.model_dump(),
    }


async def _run_stage1_record(
    *,
    llm: LLMRunner,
    bundle: BundleContext,
    paper_id: str,
    arm: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    junior_results = await asyncio.gather(
        *[
            _run_stage1_junior(
                llm=llm,
                bundle=bundle,
                paper_id=paper_id,
                arm=arm,
                record=record,
                reviewer_name=reviewer_name,
                model=model,
            )
            for reviewer_name, model in JUNIOR_MODELS
        ]
    )
    junior_by_name = {item["reviewer"]: item for item in junior_results}
    nano_eval = junior_by_name["JuniorNano"]["evaluator_output"]["stage_score"]
    mini_eval = junior_by_name["JuniorMini"]["evaluator_output"]["stage_score"]

    senior_output = None
    if not ((nano_eval >= 4 and mini_eval >= 4) or (nano_eval <= 2 and mini_eval <= 2)):
        context = _base_context(paper_id=paper_id, record=record, stage="stage1", arm=arm, bundle=bundle)
        if arm == "qa-only":
            context["JUNIOR_QA_OUTPUTS_JSON"] = _json_text(
                [junior_by_name["JuniorNano"]["reviewer_output"], junior_by_name["JuniorMini"]["reviewer_output"]]
            )
            template_key = "stage1_senior_from_qa_only"
        else:
            context["JUNIOR_SYNTHESIS_OUTPUTS_JSON"] = _json_text(
                [junior_by_name["JuniorNano"]["synthesis_output"], junior_by_name["JuniorMini"]["synthesis_output"]]
            )
            template_key = "stage1_senior_from_synthesis"
        context["JUNIOR_DECISION_OUTPUTS_JSON"] = _json_text(
            [junior_by_name["JuniorNano"]["evaluator_output"], junior_by_name["JuniorMini"]["evaluator_output"]]
        )
        senior_prompt = bundle.render(template_key, context)
        senior_output = await llm.call(model=SENIOR_MODEL, prompt=senior_prompt, response_model=SeniorOutput)

    row = {
        "title": _safe_title(record.get("title") or record.get("query_title")),
        "abstract": _safe_title(record.get("abstract")),
        "key": record.get("key"),
        "workflow_arm": arm,
        "round-A_JuniorNano_output": junior_by_name["JuniorNano"],
        "round-A_JuniorNano_reasoning": junior_by_name["JuniorNano"]["evaluator_output"]["decision_rationale"],
        "round-A_JuniorNano_evaluation": junior_by_name["JuniorNano"]["evaluator_output"]["stage_score"],
        "round-A_JuniorMini_output": junior_by_name["JuniorMini"],
        "round-A_JuniorMini_reasoning": junior_by_name["JuniorMini"]["evaluator_output"]["decision_rationale"],
        "round-A_JuniorMini_evaluation": junior_by_name["JuniorMini"]["evaluator_output"]["stage_score"],
        "round-B_SeniorLead_output": senior_output.model_dump() if senior_output else None,
        "round-B_SeniorLead_reasoning": senior_output.decision_rationale if senior_output else None,
        "round-B_SeniorLead_evaluation": senior_output.senior_stage_score if senior_output else None,
        "review_skipped": False,
        "discard_reason": None,
    }
    row["final_verdict"] = _derive_final_verdict(row)
    row["discard_reason"] = row["final_verdict"]
    return row


async def _run_stage2_record(
    *,
    llm: LLMRunner,
    bundle: BundleContext,
    paper_id: str,
    arm: str,
    record: dict[str, Any],
    stage1_row: dict[str, Any],
) -> dict[str, Any]:
    fulltext_path = _fulltext_path(paper_id, str(record.get("key") or ""))
    if not fulltext_path.exists():
        return {
            "key": record.get("key"),
            "title": _safe_title(record.get("title") or record.get("query_title")),
            "base_final_verdict": stage1_row.get("final_verdict"),
            "fulltext_review_mode": "inline",
            "fulltext_source_path": str(fulltext_path),
            "fulltext_chars_total": 0,
            "fulltext_chars_used": 0,
            "reference_cut_applied": False,
            "reference_cut_method": None,
            "reference_cut_marker": None,
            "reference_cut_line_no": None,
            "review_state": "missing",
            "fulltext_missing_or_unmatched": True,
            "round-A_JuniorNano_output": None,
            "round-A_JuniorNano_reasoning": None,
            "round-A_JuniorNano_evaluation": None,
            "round-A_JuniorMini_output": None,
            "round-A_JuniorMini_reasoning": None,
            "round-A_JuniorMini_evaluation": None,
            "round-B_SeniorLead_output": None,
            "round-B_SeniorLead_reasoning": None,
            "round-B_SeniorLead_evaluation": None,
            "final_verdict": stage1_row.get("final_verdict"),
            "review_skipped": True,
            "discard_reason": "fulltext_missing",
        }

    raw_text = _load_text(fulltext_path)
    fulltext_text, fulltext_meta = _cut_fulltext(raw_text)
    prior_nano = stage1_row["round-A_JuniorNano_output"]["reviewer_output"]
    prior_mini = stage1_row["round-A_JuniorMini_output"]["reviewer_output"]
    if arm == "qa+synthesis":
        prior_nano = stage1_row["round-A_JuniorNano_output"]["synthesis_output"]
        prior_mini = stage1_row["round-A_JuniorMini_output"]["synthesis_output"]

    junior_results = await asyncio.gather(
        _run_stage2_junior(
            llm=llm,
            bundle=bundle,
            paper_id=paper_id,
            arm=arm,
            record=record,
            reviewer_name="JuniorNano",
            model=JUNIOR_MODELS[0][1],
            prior_stage_output=prior_nano,
            fulltext_text=fulltext_text,
        ),
        _run_stage2_junior(
            llm=llm,
            bundle=bundle,
            paper_id=paper_id,
            arm=arm,
            record=record,
            reviewer_name="JuniorMini",
            model=JUNIOR_MODELS[1][1],
            prior_stage_output=prior_mini,
            fulltext_text=fulltext_text,
        ),
    )
    junior_by_name = {item["reviewer"]: item for item in junior_results}
    nano_eval = junior_by_name["JuniorNano"]["evaluator_output"]["stage_score"]
    mini_eval = junior_by_name["JuniorMini"]["evaluator_output"]["stage_score"]

    senior_output = None
    if not ((nano_eval >= 4 and mini_eval >= 4) or (nano_eval <= 2 and mini_eval <= 2)):
        context = _base_context(paper_id=paper_id, record=record, stage="stage2", arm=arm, bundle=bundle)
        context["FULLTEXT_TEXT"] = fulltext_text
        if arm == "qa-only":
            context["JUNIOR_QA_OUTPUTS_JSON"] = _json_text(
                [junior_by_name["JuniorNano"]["reviewer_output"], junior_by_name["JuniorMini"]["reviewer_output"]]
            )
            template_key = "stage2_senior_from_qa_only"
        else:
            context["JUNIOR_SYNTHESIS_OUTPUTS_JSON"] = _json_text(
                [junior_by_name["JuniorNano"]["synthesis_output"], junior_by_name["JuniorMini"]["synthesis_output"]]
            )
            template_key = "stage2_senior_from_synthesis"
        context["JUNIOR_DECISION_OUTPUTS_JSON"] = _json_text(
            [junior_by_name["JuniorNano"]["evaluator_output"], junior_by_name["JuniorMini"]["evaluator_output"]]
        )
        senior_prompt = bundle.render(template_key, context)
        senior_output = await llm.call(model=SENIOR_MODEL, prompt=senior_prompt, response_model=SeniorOutput)

    row = {
        "key": record.get("key"),
        "title": _safe_title(record.get("title") or record.get("query_title")),
        "base_final_verdict": stage1_row.get("final_verdict"),
        "workflow_arm": arm,
        "fulltext_review_mode": "inline",
        "fulltext_source_path": str(fulltext_path),
        **fulltext_meta,
        "review_state": "reviewed",
        "fulltext_missing_or_unmatched": False,
        "round-A_JuniorNano_output": junior_by_name["JuniorNano"],
        "round-A_JuniorNano_reasoning": junior_by_name["JuniorNano"]["evaluator_output"]["decision_rationale"],
        "round-A_JuniorNano_evaluation": junior_by_name["JuniorNano"]["evaluator_output"]["stage_score"],
        "round-A_JuniorMini_output": junior_by_name["JuniorMini"],
        "round-A_JuniorMini_reasoning": junior_by_name["JuniorMini"]["evaluator_output"]["decision_rationale"],
        "round-A_JuniorMini_evaluation": junior_by_name["JuniorMini"]["evaluator_output"]["stage_score"],
        "round-B_SeniorLead_output": senior_output.model_dump() if senior_output else None,
        "round-B_SeniorLead_reasoning": senior_output.decision_rationale if senior_output else None,
        "round-B_SeniorLead_evaluation": senior_output.senior_stage_score if senior_output else None,
        "review_skipped": False,
        "discard_reason": None,
    }
    row["final_verdict"] = _derive_final_verdict(row)
    return row


def _load_existing_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {str(row.get("key")): row for row in _read_json(path) if isinstance(row, dict) and row.get("key")}


def _ordered_rows(records: list[dict[str, Any]], keyed_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        key = str(record.get("key") or "")
        if key in keyed_rows:
            rows.append(keyed_rows[key])
    return rows


def _batched(records: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    return [records[idx : idx + batch_size] for idx in range(0, len(records), batch_size)]


async def _run_stage1(
    *,
    llm: LLMRunner,
    bundle: BundleContext,
    paper_id: str,
    arm: str,
    max_records: int | None,
    record_batch_size: int,
) -> list[dict[str, Any]]:
    arm_dir = _arm_dir(paper_id, arm)
    stage1_path = arm_dir / "latte_review_results.json"
    records = _load_stage1_records(paper_id)
    if max_records is not None:
        records = records[:max_records]
    keyed_rows = _load_existing_rows(stage1_path)
    pending = [record for record in records if str(record.get("key") or "") not in keyed_rows]
    print(f"[stage1] {paper_id} {arm} | total={len(records)} pending={len(pending)}")
    batches = _batched(pending, record_batch_size)
    for batch_index, batch in enumerate(batches, start=1):
        print(f"[stage1] batch {batch_index}/{len(batches)} size={len(batch)}", flush=True)
        tasks = [
            asyncio.create_task(_run_stage1_record(llm=llm, bundle=bundle, paper_id=paper_id, arm=arm, record=record))
            for record in batch
        ]
        for task in asyncio.as_completed(tasks):
            row = await task
            keyed_rows[str(row["key"])] = row
            _write_json(stage1_path, _ordered_rows(records, keyed_rows))
            print(f"[stage1] wrote {paper_id} {arm} {row['key']} -> {row['final_verdict']}", flush=True)
    rows = _ordered_rows(records, keyed_rows)
    _write_json(stage1_path, rows)
    return rows


async def _run_stage2(
    *,
    llm: LLMRunner,
    bundle: BundleContext,
    paper_id: str,
    arm: str,
    stage1_rows: list[dict[str, Any]],
    max_records: int | None,
    record_batch_size: int,
) -> list[dict[str, Any]]:
    arm_dir = _arm_dir(paper_id, arm)
    stage2_path = arm_dir / "latte_fulltext_review_results.json"
    base_index = {str(row.get("key")): row for row in stage1_rows if row.get("key")}
    records = [record for record in _load_stage1_records(paper_id) if str(record.get("key") or "") in base_index]
    records = [
        record
        for record in records
        if _extract_verdict_label(base_index[str(record.get("key") or "")].get("final_verdict")) in {"include", "maybe"}
    ]
    if max_records is not None:
        records = records[:max_records]
    selected_keys = [str(record.get("key")) for record in records]
    (arm_dir / "selected_for_stage2.keys.txt").write_text("\n".join(selected_keys) + ("\n" if selected_keys else ""), encoding="utf-8")

    keyed_rows = _load_existing_rows(stage2_path)
    pending = [record for record in records if str(record.get("key") or "") not in keyed_rows]
    print(f"[stage2] {paper_id} {arm} | selected={len(records)} pending={len(pending)}")
    batches = _batched(pending, record_batch_size)
    for batch_index, batch in enumerate(batches, start=1):
        print(f"[stage2] batch {batch_index}/{len(batches)} size={len(batch)}", flush=True)
        tasks = [
            asyncio.create_task(
                _run_stage2_record(
                    llm=llm,
                    bundle=bundle,
                    paper_id=paper_id,
                    arm=arm,
                    record=record,
                    stage1_row=base_index[str(record.get("key") or "")],
                )
            )
            for record in batch
        ]
        for task in asyncio.as_completed(tasks):
            row = await task
            keyed_rows[str(row["key"])] = row
            _write_json(stage2_path, _ordered_rows(records, keyed_rows))
            print(f"[stage2] wrote {paper_id} {arm} {row['key']} -> {row['final_verdict']}", flush=True)
    rows = _ordered_rows(records, keyed_rows)
    _write_json(stage2_path, rows)
    return rows


def _run_eval(*, paper_id: str, results_path: Path, gold_path: Path, save_report: Path, combine_with_base: bool = False, base_review_results: Path | None = None) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        paper_id,
        "--results",
        str(results_path),
        "--gold-metadata",
        str(gold_path),
        "--positive-mode",
        "include_or_maybe",
        "--save-report",
        str(save_report),
    ]
    if combine_with_base:
        cmd.append("--combine-with-base")
        if base_review_results is None:
            raise ValueError("base_review_results is required when combine_with_base=True")
        cmd.extend(["--base-review-results", str(base_review_results)])
    completed = subprocess.run(cmd, check=True, cwd=str(REPO_ROOT), capture_output=True, text=True)
    print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip())
    return _read_json(save_report)


def _baseline_report(paper_id: str, kind: str) -> dict[str, Any]:
    suffix = "stage1_f1.stage_split_criteria_migration.json" if kind == "stage1" else "combined_f1.stage_split_criteria_migration.json"
    return _read_json(REPO_ROOT / "screening" / "results" / f"{paper_id}_full" / suffix)


def _summarize_arm(paper_id: str, arm: str, stage1_report: dict[str, Any], combined_report: dict[str, Any], stage2_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "paper_id": paper_id,
        "arm": arm,
        "stage1_f1": stage1_report["metrics"]["f1"],
        "combined_f1": combined_report["metrics"]["f1"],
        "stage1_precision": stage1_report["metrics"]["precision"],
        "stage1_recall": stage1_report["metrics"]["recall"],
        "combined_precision": combined_report["metrics"]["precision"],
        "combined_recall": combined_report["metrics"]["recall"],
        "stage2_selected": len(stage2_rows),
        "stage2_reviewed": sum(1 for row in stage2_rows if row.get("review_state") == "reviewed"),
        "stage2_missing": sum(1 for row in stage2_rows if row.get("review_state") == "missing"),
        "stage1_verdict_counts": stage1_report.get("verdict_counts", {}),
        "combined_verdict_counts": combined_report.get("verdict_counts", {}),
    }


def _build_report_zh(run_manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# QA-first experiment v0 實驗結果報告")
    lines.append("")
    lines.append("## Current-State Recap")
    lines.append("")
    lines.append("- current runtime prompt authority：`scripts/screening/runtime_prompts/runtime_prompts.json`。")
    lines.append("- current production criteria authority：`criteria_stage1/<paper_id>.json` 與 `criteria_stage2/<paper_id>.json`。")
    lines.append("- 本次 `seed QA` 只用於 experiment workflow，不是 production criteria。")
    lines.append("- current metrics authority 仍維持 production baseline：`2409` Stage 1 `0.7500` / Combined `0.7843`；`2511` Stage 1 `0.8657` / Combined `0.8814`。")
    lines.append("")
    lines.append("## Run Setup")
    lines.append("")
    lines.append(f"- 執行日期：`{run_manifest['run_date']}`")
    lines.append(f"- junior models：`{JUNIOR_MODELS[0][1]}` + `{JUNIOR_MODELS[1][1]}`")
    lines.append(f"- synthesis / evaluator model：`{WORKFLOW_MODEL}`")
    lines.append(f"- senior model：`{SENIOR_MODEL}`")
    lines.append("- 所有 experiment prompts 皆由外部 `.md` 模板渲染，未寫死在 `.py`。")
    lines.append("")
    lines.append("## Metrics Summary")
    lines.append("")
    lines.append("| Paper | Arm | Stage 1 F1 | Delta vs current | Combined F1 | Delta vs current | Stage 2 reviewed |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for summary in run_manifest["summaries"]:
        paper_id = summary["paper_id"]
        baseline_stage1 = run_manifest["baseline"][paper_id]["stage1"]["metrics"]["f1"]
        baseline_combined = run_manifest["baseline"][paper_id]["combined"]["metrics"]["f1"]
        lines.append(
            f"| `{paper_id}` | `{summary['arm']}` | {summary['stage1_f1']:.4f} | {summary['stage1_f1'] - baseline_stage1:+.4f} | "
            f"{summary['combined_f1']:.4f} | {summary['combined_f1'] - baseline_combined:+.4f} | {summary['stage2_reviewed']} |"
        )
    lines.append("")
    lines.append("## Per-Paper Notes")
    lines.append("")
    for paper_id in run_manifest["papers"]:
        lines.append(f"### `{paper_id}`")
        lines.append("")
        stage1_base = run_manifest["baseline"][paper_id]["stage1"]["metrics"]["f1"]
        combined_base = run_manifest["baseline"][paper_id]["combined"]["metrics"]["f1"]
        lines.append(f"- current reference baseline：Stage 1 `{stage1_base:.4f}`，Combined `{combined_base:.4f}`。")
        paper_summaries = [item for item in run_manifest["summaries"] if item["paper_id"] == paper_id]
        for item in paper_summaries:
            lines.append(
                f"- `{item['arm']}`：Stage 1 `{item['stage1_f1']:.4f}`，Combined `{item['combined_f1']:.4f}`，"
                f"Stage 2 reviewed `{item['stage2_reviewed']}` 筆。"
            )
        lines.append("")
    lines.append("## Result Files")
    lines.append("")
    for summary in run_manifest["summaries"]:
        arm_dir = _arm_dir(summary["paper_id"], summary["arm"])
        lines.append(f"- `{summary['paper_id']} + {summary['arm']}`")
        lines.append(f"  stage1 results: `{arm_dir / 'latte_review_results.json'}`")
        lines.append(f"  stage2 results: `{arm_dir / 'latte_fulltext_review_results.json'}`")
        lines.append(f"  stage1 metrics: `{arm_dir / 'stage1_f1.json'}`")
        lines.append(f"  combined metrics: `{arm_dir / 'combined_f1.json'}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- 這些結果是 experiment-only outputs，不覆寫 current production score authority。")
    lines.append("- 若後續同時展開多條實驗線，建議改用 `www.k-dense.ai` 管理 workflow。")
    return "\n".join(lines) + "\n"


async def run_all(args: argparse.Namespace) -> None:
    _load_env_file()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    assets = PromptAssets()
    bundle = BundleContext(assets)
    client = AsyncOpenAI()
    llm = LLMRunner(client=client, concurrency=args.concurrency)

    selected_papers = tuple(args.papers or PAPERS)
    selected_arms = tuple(args.arms or ARMS)
    record_batch_size = max(1, args.record_batch_size or max(1, args.concurrency // 2))

    summaries = []
    baseline = {
        paper_id: {
            "stage1": _baseline_report(paper_id, "stage1"),
            "combined": _baseline_report(paper_id, "combined"),
        }
        for paper_id in selected_papers
    }

    for paper_id in selected_papers:
        gold_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
        for arm in selected_arms:
            arm_dir = _arm_dir(paper_id, arm)
            arm_dir.mkdir(parents=True, exist_ok=True)
            stage1_rows = await _run_stage1(
                llm=llm,
                bundle=bundle,
                paper_id=paper_id,
                arm=arm,
                max_records=args.max_stage1_records,
                record_batch_size=record_batch_size,
            )
            stage2_rows = await _run_stage2(
                llm=llm,
                bundle=bundle,
                paper_id=paper_id,
                arm=arm,
                stage1_rows=stage1_rows,
                max_records=args.max_stage2_records,
                record_batch_size=record_batch_size,
            )

            stage1_results_path = arm_dir / "latte_review_results.json"
            stage2_results_path = arm_dir / "latte_fulltext_review_results.json"
            stage1_report = _run_eval(
                paper_id=paper_id,
                results_path=stage1_results_path,
                gold_path=gold_path,
                save_report=arm_dir / "stage1_f1.json",
            )
            combined_report = _run_eval(
                paper_id=paper_id,
                results_path=stage2_results_path,
                gold_path=gold_path,
                save_report=arm_dir / "combined_f1.json",
                combine_with_base=True,
                base_review_results=stage1_results_path,
            )
            summaries.append(_summarize_arm(paper_id, arm, stage1_report, combined_report, stage2_rows))

    run_manifest = {
        "bundle_dir": str(BUNDLE_DIR),
        "results_root": str(RESULTS_ROOT),
        "run_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "papers": list(selected_papers),
        "arms": list(selected_arms),
        "baseline": baseline,
        "summaries": summaries,
    }
    _write_json(RESULTS_ROOT / "run_manifest.json", run_manifest)
    (RESULTS_ROOT / "REPORT_zh.md").write_text(_build_report_zh(run_manifest), encoding="utf-8")
    print(f"[done] results_root={RESULTS_ROOT}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run QA-first experiment v0 arms.")
    parser.add_argument("--papers", nargs="*", choices=PAPERS, default=list(PAPERS))
    parser.add_argument("--arms", nargs="*", choices=ARMS, default=list(ARMS))
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--record-batch-size", type=int, default=None)
    parser.add_argument("--max-stage1-records", type=int, default=None)
    parser.add_argument("--max-stage2-records", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(run_all(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
