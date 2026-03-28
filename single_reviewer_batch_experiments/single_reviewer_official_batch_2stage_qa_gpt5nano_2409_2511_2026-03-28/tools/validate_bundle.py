#!/usr/bin/env python3
"""驗證 single reviewer official-batch 2-stage QA bundle。"""

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


def validate_manifest() -> dict[str, Any]:
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
        "helper_files",
        "policy_files",
        "qa_assets",
        "framing_document",
    }
    missing = sorted(required.difference(manifest.keys()))
    if missing:
        raise ValueError("manifest 缺少欄位: " + ", ".join(missing))
    if manifest["asset_bundle"] != BUNDLE_DIR.name:
        raise ValueError("manifest.asset_bundle 與 bundle 目錄名稱不一致")
    return manifest


def validate_required_inputs() -> None:
    config = run_experiment._load_config()
    runtime_prompts_path = run_experiment._runtime_prompts_path()
    if not runtime_prompts_path.exists():
        raise ValueError(f"缺少 runtime prompts: {runtime_prompts_path}")

    smoke_path = BUNDLE_DIR / "smoke" / "smoke_candidates.json"
    if not smoke_path.exists():
        raise ValueError(f"缺少 smoke 候選清單: {smoke_path}")

    for template_name in (
        "01_stage1_qa_TEMPLATE.md",
        "02_stage1_eval_TEMPLATE.md",
        "03_stage2_qa_TEMPLATE.md",
        "04_stage2_eval_TEMPLATE.md",
        "validation_retry_repair_policy.md",
    ):
        path = BUNDLE_DIR / "templates" / template_name
        if not path.exists():
            raise ValueError(f"缺少 template: {path}")

    for paper_id in config["papers"]:
        for path in (
            run_experiment._paper_metadata_path(paper_id),
            run_experiment._paper_gold_path(paper_id),
            run_experiment._paper_fulltext_root(paper_id),
            run_experiment._paper_stage1_criteria_path(paper_id),
            run_experiment._paper_stage2_criteria_path(paper_id),
            run_experiment._paper_cutoff_path(paper_id),
            run_experiment._qa_asset_path(paper_id, "stage1"),
            run_experiment._qa_asset_path(paper_id, "stage2"),
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
    if not hasattr(run_experiment, "build_serialization_probe"):
        raise ValueError("run_experiment 沒有暴露 build_serialization_probe")


def _assert_probe_shape(phase: str, probe: dict[str, Any]) -> None:
    required_keys = {"custom_id", "method", "url", "body"}
    missing = sorted(required_keys.difference(probe.keys()))
    if missing:
        raise ValueError(f"{phase} probe 缺少欄位: " + ", ".join(missing))
    body = probe["body"]
    if not isinstance(body, dict):
        raise ValueError(f"{phase} probe body 不是 dict")
    if "response_format" not in body:
        raise ValueError(f"{phase} probe 缺少 response_format")
    if body.get("model") != run_experiment._load_config()["model"]:
        raise ValueError(f"{phase} probe model 不等於 configured model")


def main() -> int:
    parser = argparse.ArgumentParser(description="驗證 single reviewer official-batch 2-stage QA bundle。")
    parser.add_argument("--check-model", action="store_true")
    parser.add_argument("--check-serialization", action="store_true")
    args = parser.parse_args()

    validate_assets()
    manifest = validate_manifest()
    validate_required_inputs()
    validate_python_imports()

    if args.check_model:
        model_id = run_experiment._model_preflight(run_experiment._load_config()["model"])
        print(f"model_preflight id={model_id}", flush=True)

    if args.check_serialization:
        for phase in run_experiment.PHASES:
            probe = run_experiment.build_serialization_probe(phase)
            _assert_probe_shape(phase, probe)
            print(
                f"serialization_probe phase={phase} custom_id={probe['custom_id']} model={probe['body'].get('model')}",
                flush=True,
            )

    print(
        "bundle_validation: ok "
        f"asset_bundle={manifest['asset_bundle']} "
        f"papers={','.join(run_experiment._load_config()['papers'])}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
