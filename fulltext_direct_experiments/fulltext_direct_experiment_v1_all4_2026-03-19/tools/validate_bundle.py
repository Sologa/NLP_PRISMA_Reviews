#!/usr/bin/env python3
"""Validate the fulltext-direct experiment bundle."""

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


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _ensure_required(obj: Dict[str, Any], required: list[str], label: str) -> None:
    missing = [key for key in required if key not in obj]
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(missing)}")


def validate_assets() -> None:
    for path in BUNDLE_DIR.rglob("*.json"):
        _load_json(path)
    for path in list(BUNDLE_DIR.rglob("*.yaml")) + list(BUNDLE_DIR.rglob("*.yml")):
        _load_yaml(path)


def validate_manifest() -> None:
    manifest = _load_json(BUNDLE_DIR / "manifest.json")
    template_manifest = _load_yaml(BUNDLE_DIR / "templates" / "prompt_manifest.yaml")
    context = render_prompt._load_context(BUNDLE_DIR / "samples" / "dummy_render_context.yaml")

    required_placeholders = set(template_manifest["required_placeholders"])
    missing = sorted(required_placeholders.difference(context.keys()))
    if missing:
        raise ValueError(f"dummy_render_context missing placeholders: {', '.join(missing)}")

    for relative_path in manifest.get("policy_files", []):
        path = BUNDLE_DIR / relative_path
        if not path.exists():
            raise ValueError(f"missing policy file: {relative_path}")


def validate_templates() -> None:
    context = render_prompt._load_context(BUNDLE_DIR / "samples" / "dummy_render_context.yaml")
    for path in sorted((BUNDLE_DIR / "templates").glob("*_TEMPLATE.md")):
        text = path.read_text(encoding="utf-8")
        render_prompt._render(text, context, strict=True)


def validate_samples() -> None:
    junior_contract = _load_yaml(BUNDLE_DIR / "schemas" / "junior_output_contract.yaml")
    senior_contract = _load_yaml(BUNDLE_DIR / "schemas" / "senior_output_contract.yaml")

    junior_sample = _load_json(BUNDLE_DIR / "samples" / "sample_junior_output.json")
    _ensure_required(junior_sample, junior_contract["required"], "sample_junior_output")
    if junior_sample["stage_score"] not in junior_contract["allowed_stage_score"]:
        raise ValueError("sample_junior_output.stage_score is invalid")
    if junior_sample["decision_recommendation"] not in junior_contract["allowed_recommendation"]:
        raise ValueError("sample_junior_output.decision_recommendation is invalid")

    senior_sample = _load_json(BUNDLE_DIR / "samples" / "sample_senior_output.json")
    _ensure_required(senior_sample, senior_contract["required"], "sample_senior_output")
    if senior_sample["senior_stage_score"] not in senior_contract["allowed_stage_score"]:
        raise ValueError("sample_senior_output.senior_stage_score is invalid")
    if senior_sample["decision_recommendation"] not in senior_contract["allowed_recommendation"]:
        raise ValueError("sample_senior_output.decision_recommendation is invalid")


def main() -> int:
    validate_assets()
    validate_manifest()
    validate_templates()
    validate_samples()
    print("bundle_validation: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
