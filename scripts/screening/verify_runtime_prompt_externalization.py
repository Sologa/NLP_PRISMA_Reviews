#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get(node: Dict[str, Any], *keys: str) -> Any:
    cur: Any = node
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify runtime prompt externalization equivalence.")
    parser.add_argument(
        "--runtime-prompts",
        type=Path,
        default=Path("scripts/screening/runtime_prompts/runtime_prompts.json"),
        help="Externalized runtime prompts JSON",
    )
    parser.add_argument(
        "--baseline-current",
        type=Path,
        default=Path("screening/results/runtime_prompt_externalization/original_runtime_prompts.from_topic_pipeline.json"),
        help="Snapshot extracted from pre-refactor topic_pipeline.py",
    )
    parser.add_argument(
        "--baseline-no-marker",
        type=Path,
        default=Path(
            "screening/results/runtime_prompt_externalization/historical_stage1_senior_no_marker.from_git_229e5e1.json"
        ),
        help="Historical no-marker stage1 senior prompt extracted from git",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("screening/results/runtime_prompt_externalization/prompt_equivalence_check.json"),
        help="Where to write the verification JSON report",
    )
    args = parser.parse_args()

    runtime = json.loads(args.runtime_prompts.read_text(encoding="utf-8"))
    baseline_current = json.loads(args.baseline_current.read_text(encoding="utf-8"))
    baseline_no_marker = json.loads(args.baseline_no_marker.read_text(encoding="utf-8"))

    checks = [
        {
            "name": "stage1_junior.junior_nano.backstory",
            "expected": _as_text(_get(baseline_current, "run_latte_review", "JuniorNano", "backstory")),
            "actual": _as_text(_get(runtime, "stage1_junior", "junior_nano", "backstory")),
        },
        {
            "name": "stage1_junior.junior_mini.backstory",
            "expected": _as_text(_get(baseline_current, "run_latte_review", "JuniorMini", "backstory")),
            "actual": _as_text(_get(runtime, "stage1_junior", "junior_mini", "backstory")),
        },
        {
            "name": "stage1_senior_prompt_tuned.backstory",
            "expected": _as_text(_get(baseline_current, "run_latte_review", "SeniorLead", "backstory")),
            "actual": _as_text(_get(runtime, "stage1_senior_prompt_tuned", "backstory")),
        },
        {
            "name": "stage1_senior_prompt_tuned.additional_context",
            "expected": _as_text(_get(baseline_current, "run_latte_review", "SeniorLead", "additional_context")),
            "actual": _as_text(_get(runtime, "stage1_senior_prompt_tuned", "additional_context")),
        },
        {
            "name": "stage2_fulltext.junior_nano.backstory",
            "expected": _as_text(_get(baseline_current, "run_latte_fulltext_review", "JuniorNano", "backstory")),
            "actual": _as_text(_get(runtime, "stage2_fulltext", "junior_nano", "backstory")),
        },
        {
            "name": "stage2_fulltext.junior_mini.backstory",
            "expected": _as_text(_get(baseline_current, "run_latte_fulltext_review", "JuniorMini", "backstory")),
            "actual": _as_text(_get(runtime, "stage2_fulltext", "junior_mini", "backstory")),
        },
        {
            "name": "stage2_fulltext.senior.backstory",
            "expected": _as_text(_get(baseline_current, "run_latte_fulltext_review", "SeniorLead", "backstory")),
            "actual": _as_text(_get(runtime, "stage2_fulltext", "senior", "backstory")),
        },
        {
            "name": "stage2_fulltext.senior.additional_context",
            "expected": _as_text(_get(baseline_current, "run_latte_fulltext_review", "SeniorLead", "additional_context")),
            "actual": _as_text(_get(runtime, "stage2_fulltext", "senior", "additional_context")),
        },
        {
            "name": "stage1_senior_no_marker.backstory",
            "expected": _as_text(_get(baseline_no_marker, "backstory")),
            "actual": _as_text(_get(runtime, "stage1_senior_no_marker", "backstory")),
        },
        {
            "name": "stage1_senior_no_marker.additional_context",
            "expected": _as_text(_get(baseline_no_marker, "additional_context")),
            "actual": _as_text(_get(runtime, "stage1_senior_no_marker", "additional_context")),
        },
    ]

    mismatches = []
    for item in checks:
        item["expected_sha256"] = _sha(item["expected"])
        item["actual_sha256"] = _sha(item["actual"])
        item["match"] = item["expected"] == item["actual"]
        if not item["match"]:
            mismatches.append(item["name"])

    report = {
        "all_match": len(mismatches) == 0,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "checks": checks,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"all_match": report["all_match"], "mismatch_count": report["mismatch_count"]}, ensure_ascii=False))
    return 0 if report["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
