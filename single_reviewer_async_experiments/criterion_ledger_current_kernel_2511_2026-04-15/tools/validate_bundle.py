#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openai import AsyncOpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

from experiment_lib import read_json  # noqa: E402
from ledger_kernel_lib import build_dynamic_senior_response_model  # noqa: E402
from experiment_workflows import build_dynamic_stage_response_model, load_criterion_asset  # noqa: E402
from vendor.src.utils.llm import ensure_env_loaded  # noqa: E402


CONFIG_PATH = BUNDLE_DIR / "config" / "experiment.json"


def _must_exist(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def validate_files() -> None:
    config = read_json(CONFIG_PATH)
    _must_exist(CONFIG_PATH)
    _must_exist(BUNDLE_DIR / "config" / "smoke_candidates.json")
    for template_name in (
        "01_stage1_junior_ledger_review_TEMPLATE.md",
        "02_stage2_junior_ledger_review_TEMPLATE.md",
        "03_stage1_senior_adjudication_TEMPLATE.md",
        "04_stage2_senior_adjudication_TEMPLATE.md",
    ):
        _must_exist(BUNDLE_DIR / "templates" / template_name)
    for sample_name in (
        "junior_stage1_review_output.sample.json",
        "junior_stage2_review_output.sample.json",
        "senior_stage1_review_output.sample.json",
        "senior_stage2_review_output.sample.json",
    ):
        _must_exist(BUNDLE_DIR / "samples" / sample_name)
        read_json(BUNDLE_DIR / "samples" / sample_name)
    paper_id = config["paper_id"]
    _must_exist(REPO_ROOT / "criteria_stage1" / f"{paper_id}.json")
    _must_exist(REPO_ROOT / "criteria_stage2" / f"{paper_id}.json")
    _must_exist(REPO_ROOT / "cutoff_jsons" / f"{paper_id}.json")
    _must_exist(REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl")
    _must_exist(REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl")
    _must_exist(REPO_ROOT / "refs" / paper_id / "mds")
    _must_exist(BUNDLE_DIR / "assets" / "merged" / f"{paper_id}.stage1.json")
    _must_exist(BUNDLE_DIR / "assets" / "merged" / f"{paper_id}.stage2.json")


def validate_schemas() -> None:
    config = read_json(CONFIG_PATH)
    paper_id = config["paper_id"]
    asset1 = load_criterion_asset(BUNDLE_DIR / "assets" / "merged" / f"{paper_id}.stage1.json")
    asset2 = load_criterion_asset(BUNDLE_DIR / "assets" / "merged" / f"{paper_id}.stage2.json")
    stage1_ids = [item.criterion_id for item in asset1.criteria]
    stage2_ids = [item.criterion_id for item in asset2.criteria]
    build_dynamic_stage_response_model("Stage1JuniorSchema", criterion_ids=stage1_ids)
    build_dynamic_stage_response_model("Stage2JuniorSchema", criterion_ids=stage2_ids)
    build_dynamic_senior_response_model("Stage1SeniorSchema", criterion_ids=stage1_ids)
    build_dynamic_senior_response_model("Stage2SeniorSchema", criterion_ids=stage2_ids)


def validate_async_client() -> None:
    ensure_env_loaded()
    client = AsyncOpenAI()
    if client is None:
        raise RuntimeError("failed to create AsyncOpenAI client")


def validate_results_root() -> None:
    runs_dir = BUNDLE_DIR / "runs"
    if runs_dir.resolve().parents[0] != BUNDLE_DIR.resolve():
        raise RuntimeError("runs dir escaped bundle root")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the isolated criterion-ledger current-kernel experiment tree.")
    parser.add_argument("--check-client", action="store_true")
    args = parser.parse_args()

    validate_files()
    validate_schemas()
    validate_results_root()
    if args.check_client:
        validate_async_client()
    print("bundle_validation: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
