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
from paper_faithful_models import DebateReviewOutput, JudgeReviewOutput, PrimaryReviewOutput, QuestionBundle  # noqa: E402
from vendor.src.utils.llm import ensure_env_loaded  # noqa: E402


def _must_exist(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def validate_files() -> None:
    experiment = read_json(BUNDLE_DIR / "config" / "experiment.json")
    stages = read_json(BUNDLE_DIR / "config" / "stages.json")
    _must_exist(BUNDLE_DIR / "config" / "smoke_candidates.json")
    for template_name in (
        "00_generate_stage_questions_TEMPLATE.md",
        "01_primary_qa_review_TEMPLATE.md",
        "02_peer_review_round_TEMPLATE.md",
        "03_adjudication_review_TEMPLATE.md",
    ):
        _must_exist(BUNDLE_DIR / "templates" / template_name)
    paper_id = experiment["paper_id"]
    _must_exist(REPO_ROOT / stages["stages"]["stage1_abstract"]["criteria_path"])
    _must_exist(REPO_ROOT / stages["stages"]["stage2_fulltext"]["criteria_path"])
    _must_exist(REPO_ROOT / "cutoff_jsons" / f"{paper_id}.json")
    _must_exist(REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl")
    _must_exist(REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl")
    question_asset = REPO_ROOT / stages["stages"]["stage1_abstract"]["question_asset_path"]
    if question_asset.exists():
        QuestionBundle.model_validate(read_json(question_asset))


def validate_schemas() -> None:
    QuestionBundle.model_json_schema()
    PrimaryReviewOutput.model_json_schema()
    DebateReviewOutput.model_json_schema()
    JudgeReviewOutput.model_json_schema()


def validate_async_client() -> None:
    ensure_env_loaded()
    client = AsyncOpenAI()
    if client is None:
        raise RuntimeError("failed to create AsyncOpenAI client")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the isolated paper-faithful 2409 async bundle.")
    parser.add_argument("--check-client", action="store_true")
    args = parser.parse_args()

    validate_files()
    validate_schemas()
    if args.check_client:
        validate_async_client()
    print("bundle_validation: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
