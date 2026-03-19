#!/usr/bin/env python3
"""Validate the QA-first experiment v1 global-repair bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import render_prompt  # noqa: E402


FORBIDDEN_SAMPLE_LITERALS = (
    "2409.13738",
    "2511.13936",
    '"workflow_arm": "qa-only"',
    '"workflow_arm": "qa+synthesis"',
    '"arm": "qa-only"',
    '"arm": "qa+synthesis"',
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _ensure_required(obj: Dict[str, Any], required: list[str], label: str) -> None:
    missing = [key for key in required if key not in obj]
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(missing)}")


def _build_qa_prompt_payload(qa_asset: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "paper_id": qa_asset.get("paper_id"),
        "stage": qa_asset.get("stage"),
        "reviewer_guardrails": qa_asset.get("reviewer_guardrails", []),
        "question_groups": qa_asset.get("question_groups", []),
    }
    for optional_key in ("handoff_policy", "conflict_handling_policy", "non_goals"):
        if optional_key in qa_asset:
            payload[optional_key] = qa_asset.get(optional_key)
    return payload


def validate_assets() -> None:
    for path in BUNDLE_DIR.rglob("*.json"):
        _load_json(path)
    for path in list(BUNDLE_DIR.rglob("*.yaml")) + list(BUNDLE_DIR.rglob("*.yml")):
        _load_yaml(path)


def validate_templates() -> None:
    context = render_prompt._load_context(BUNDLE_DIR / "samples" / "dummy_render_context.yaml")
    for path in sorted((BUNDLE_DIR / "templates").glob("*_TEMPLATE.md")):
        text = path.read_text(encoding="utf-8")
        render_prompt._render(text, context, strict=True)


def validate_manifest() -> None:
    manifest = _load_yaml(BUNDLE_DIR / "templates" / "prompt_manifest.yaml")
    required_placeholders = set(manifest["required_placeholders"])
    context = render_prompt._load_context(BUNDLE_DIR / "samples" / "dummy_render_context.yaml")
    missing = sorted(required_placeholders.difference(context.keys()))
    if missing:
        raise ValueError(f"dummy_render_context missing placeholders: {', '.join(missing)}")
    bundle_manifest = _load_json(BUNDLE_DIR / "manifest.json")
    for relative_path in bundle_manifest.get("policy_files", []):
        path = BUNDLE_DIR / Path(relative_path).relative_to(BUNDLE_DIR.name) if relative_path.startswith(BUNDLE_DIR.name) else REBASE(relative_path)
        if not path.exists():
            raise ValueError(f"missing policy file: {relative_path}")
    stage_specific_manifest = _load_yaml(BUNDLE_DIR / "templates" / "policies" / "stage_specific_policy_manifest.yaml") or {}
    for entry in stage_specific_manifest.get("policies", []):
        file_name = str(entry.get("file", "")).strip()
        if not file_name:
            raise ValueError("stage_specific_policy_manifest entry is missing file")
        policy_path = BUNDLE_DIR / "templates" / "policies" / file_name
        if not policy_path.exists():
            raise ValueError(f"missing stage-specific policy file: {file_name}")


def REBASE(relative_path: str) -> Path:
    return BUNDLE_DIR / relative_path


def validate_qa_assets() -> None:
    payload_contract = _load_yaml(BUNDLE_DIR / "schemas" / "qa_prompt_payload_contract.yaml")
    forbidden_keys = set(payload_contract["forbidden_keys"])
    for path in sorted((BUNDLE_DIR / "qa").glob("*.json")):
        payload = _load_json(path)
        sanitized = _build_qa_prompt_payload(payload)
        _ensure_required(sanitized, payload_contract["required"], f"{path.name}.sanitized")
        leaked_forbidden = forbidden_keys.intersection(sanitized.keys())
        if leaked_forbidden:
            raise ValueError(f"{path.name} sanitized payload leaked forbidden keys: {', '.join(sorted(leaked_forbidden))}")
        if "review" in sanitized or "source_basis" in sanitized or "source_markdown" in sanitized:
            raise ValueError(f"{path.name} sanitized payload retained review-level metadata")


def validate_2511_patch() -> None:
    for name in ("2511.13936.stage1.seed_qa.json", "2511.13936.stage2.seed_qa.json"):
        payload = _load_json(BUNDLE_DIR / "qa" / name)
        qids = []
        for group in payload.get("question_groups", []):
            for question in group.get("questions", []):
                qids.append(question.get("qid"))
        if "M1" in qids:
            raise ValueError(f"{name} still contains answerable M1")
        guardrails = payload.get("reviewer_guardrails", [])
        if not guardrails:
            raise ValueError(f"{name} is missing reviewer_guardrails")


def validate_samples() -> None:
    qa_contract = _load_yaml(BUNDLE_DIR / "schemas" / "qa_output_contract.yaml")
    syn_contract = _load_yaml(BUNDLE_DIR / "schemas" / "synthesis_output_contract.yaml")
    eval_contract = _load_yaml(BUNDLE_DIR / "schemas" / "criteria_evaluation_output_contract.yaml")
    senior_contract = _load_yaml(BUNDLE_DIR / "schemas" / "senior_output_contract.yaml")

    qa_sample = _load_json(BUNDLE_DIR / "samples" / "sample_reviewer_qa_output.json")
    _ensure_required(qa_sample, qa_contract["required"], "sample_reviewer_qa_output")
    for answer in qa_sample["answers"]:
        _ensure_required(answer, qa_contract["answer_record"]["required"], "sample_reviewer_qa_output.answer")
        if answer["answer_state"] not in qa_contract["allowed_answer_state"]:
            raise ValueError("sample_reviewer_qa_output.answer_state is invalid")
        if answer["state_basis"] not in qa_contract["allowed_state_basis"]:
            raise ValueError("sample_reviewer_qa_output.state_basis is invalid")

    syn_sample = _load_json(BUNDLE_DIR / "samples" / "sample_synthesis_output.json")
    _ensure_required(syn_sample, syn_contract["required"], "sample_synthesis_output")
    for field in syn_sample["field_records"]:
        _ensure_required(field, syn_contract["field_record"]["required"], "sample_synthesis_output.field_record")

    eval_sample = _load_json(BUNDLE_DIR / "samples" / "sample_criteria_evaluation_output.json")
    _ensure_required(eval_sample, eval_contract["required"], "sample_criteria_evaluation_output")
    if eval_sample["stage_score"] not in eval_contract["allowed_stage_score"]:
        raise ValueError("sample_criteria_evaluation_output.stage_score is invalid")
    if eval_sample["scoring_basis"] not in eval_contract["allowed_scoring_basis"]:
        raise ValueError("sample_criteria_evaluation_output.scoring_basis is invalid")

    senior_sample = _load_json(BUNDLE_DIR / "samples" / "sample_senior_output.json")
    _ensure_required(senior_sample, senior_contract["required"], "sample_senior_output")
    if senior_sample["senior_stage_score"] not in senior_contract["allowed_stage_score"]:
        raise ValueError("sample_senior_output.senior_stage_score is invalid")
    if senior_sample["scoring_basis"] not in senior_contract["allowed_scoring_basis"]:
        raise ValueError("sample_senior_output.scoring_basis is invalid")


def validate_generic_samples() -> None:
    for path in (
        BUNDLE_DIR / "samples" / "sample_reviewer_qa_output.json",
        BUNDLE_DIR / "samples" / "sample_synthesis_output.json",
        BUNDLE_DIR / "samples" / "sample_criteria_evaluation_output.json",
        BUNDLE_DIR / "samples" / "sample_senior_output.json",
        BUNDLE_DIR / "samples" / "dummy_render_context.yaml",
    ):
        text = path.read_text(encoding="utf-8")
        for literal in FORBIDDEN_SAMPLE_LITERALS:
            if literal in text:
                raise ValueError(f"{path.name} still contains forbidden live literal: {literal}")


def main() -> int:
    validate_assets()
    validate_manifest()
    validate_templates()
    validate_qa_assets()
    validate_2511_patch()
    validate_samples()
    validate_generic_samples()
    print("bundle_validation: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
