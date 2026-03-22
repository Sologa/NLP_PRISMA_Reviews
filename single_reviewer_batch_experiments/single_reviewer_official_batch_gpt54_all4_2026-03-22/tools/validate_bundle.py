#!/usr/bin/env python3
"""驗證單審查者官方批次 bundle。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

import run_experiment  # noqa: E402
import openai_batch_runner  # noqa: E402


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_assets() -> None:
    for path in sorted(BUNDLE_DIR.rglob("*.json")):
        _load_json(path)


def validate_manifest() -> None:
    manifest = _load_json(BUNDLE_DIR / "manifest.json")
    required = {
        "asset_bundle",
        "status",
        "scope",
        "workflow",
        "configured_model",
        "results_root",
        "current_production_inputs",
        "candidate_inputs",
        "tooling",
        "framing_document",
    }
    missing = sorted(required.difference(manifest.keys()))
    if missing:
        raise ValueError("manifest 缺少欄位: " + ", ".join(missing))


def validate_required_inputs() -> None:
    config = run_experiment._load_config()
    runtime_prompts_path = run_experiment._runtime_prompts_path()
    if not runtime_prompts_path.exists():
        raise ValueError(f"缺少 runtime prompts: {runtime_prompts_path}")
    for paper_id in config["papers"]:
        for path in (
            run_experiment._paper_metadata_path(paper_id),
            run_experiment._paper_gold_path(paper_id),
            run_experiment._paper_fulltext_root(paper_id),
            run_experiment._paper_stage2_criteria_path(paper_id),
        ):
            if not path.exists():
                raise ValueError(f"缺少必要輸入: {path}")


def validate_python_imports() -> None:
    try:
        import openai  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ValueError("缺少 openai 套件") from exc
    if not hasattr(openai_batch_runner, "OpenAIBatchRunner"):
        raise ValueError("openai_batch_runner 沒有暴露 OpenAIBatchRunner")


def main() -> int:
    parser = argparse.ArgumentParser(description="驗證單審查者官方批次 bundle。")
    parser.add_argument("--check-model", action="store_true")
    parser.add_argument("--check-serialization", action="store_true")
    args = parser.parse_args()

    validate_assets()
    validate_manifest()
    validate_required_inputs()
    validate_python_imports()

    if args.check_model:
        model_id = run_experiment._model_preflight(run_experiment._load_config()["model"])
        print(f"model_preflight id={model_id}", flush=True)

    if args.check_serialization:
        probe = run_experiment.build_serialization_probe()
        required_keys = {"custom_id", "method", "url", "body"}
        missing = sorted(required_keys.difference(probe.keys()))
        if missing:
            raise ValueError("serialization probe 缺少欄位: " + ", ".join(missing))
        body = probe["body"]
        if not isinstance(body, dict):
            raise ValueError("serialization probe body 不是 dict")
        if "response_format" not in body:
            raise ValueError("serialization probe 缺少 response_format")
        print(f"serialization_probe custom_id={probe['custom_id']} model={body.get('model')}", flush=True)

    print("bundle_validation: ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
