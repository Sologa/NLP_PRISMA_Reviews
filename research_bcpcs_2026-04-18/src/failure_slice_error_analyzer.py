#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from failure_slice_common import read_json, repo_rel, run_dir, utc_now_iso, write_json


def _row_map(summary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row["paper_id"]), str(row["candidate_key"])): row
        for row in summary.get("rows", [])
    }


def _is_recovered(row: dict[str, Any]) -> bool:
    pred = row.get("prediction")
    if pred is None:
        return False
    gold = bool(row.get("gold_label"))
    return (pred == 1 and gold) or (pred == 0 and not gold)


def _outcome(row: dict[str, Any]) -> str:
    if row.get("prediction") is None:
        return "unknown_or_runtime"
    return "recovered" if _is_recovered(row) else "wrong"


def recovery_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prior_fn = [row for row in rows if row.get("prior_error_type") == "FN"]
    prior_fp = [row for row in rows if row.get("prior_error_type") == "FP"]
    unknown = sum(1 for row in rows if row.get("prediction") is None)
    recovered = sum(1 for row in rows if _is_recovered(row))
    return {
        "row_count": len(rows),
        "prior_fn_count": len(prior_fn),
        "prior_fp_count": len(prior_fp),
        "prior_fn_recovered": sum(1 for row in prior_fn if _is_recovered(row)),
        "prior_fp_recovered": sum(1 for row in prior_fp if _is_recovered(row)),
        "recovered_total": recovered,
        "unknown_or_runtime_count": unknown,
        "still_wrong_count": len(rows) - recovered - unknown,
    }


def compare_to_baseline(*, candidate_summary: dict[str, Any], baseline_summary: dict[str, Any] | None) -> dict[str, Any]:
    candidate_rows = _row_map(candidate_summary)
    if baseline_summary is None:
        return {
            "baseline_available": False,
            "transitions": {},
            "mcnemar_style": {},
            "changed_rows": [],
        }
    baseline_rows = _row_map(baseline_summary)
    transitions: Counter[str] = Counter()
    changed_rows: list[dict[str, Any]] = []
    b_correct_c_wrong = 0
    b_wrong_c_correct = 0
    for key, cand in sorted(candidate_rows.items()):
        base = baseline_rows.get(key)
        if base is None:
            continue
        b_out = _outcome(base)
        c_out = _outcome(cand)
        transitions[f"{b_out}->{c_out}"] += 1
        if b_out == "recovered" and c_out != "recovered":
            b_correct_c_wrong += 1
        if b_out != "recovered" and c_out == "recovered":
            b_wrong_c_correct += 1
        if b_out != c_out or base.get("prediction") != cand.get("prediction"):
            changed_rows.append(
                {
                    "paper_id": key[0],
                    "candidate_key": key[1],
                    "baseline_prediction": base.get("prediction"),
                    "candidate_prediction": cand.get("prediction"),
                    "baseline_decision": base.get("final_stage_decision"),
                    "candidate_decision": cand.get("final_stage_decision"),
                    "gold_label": cand.get("gold_label"),
                    "prior_error_type": cand.get("prior_error_type"),
                    "slice_type": cand.get("slice_type"),
                    "transition": f"{b_out}->{c_out}",
                }
            )
    return {
        "baseline_available": True,
        "transitions": dict(sorted(transitions.items())),
        "mcnemar_style": {
            "baseline_correct_candidate_wrong": b_correct_c_wrong,
            "baseline_wrong_candidate_correct": b_wrong_c_correct,
            "net_recovered_change": b_wrong_c_correct - b_correct_c_wrong,
            "interpretation": "Diagnostic paired transition counts only; this failure-slice dev run is not full-corpus inference.",
        },
        "changed_rows": changed_rows,
    }


def analyze_run(*, candidate_run_dir: Path, baseline_run_dir: Path | None = None) -> dict[str, Any]:
    candidate_summary = read_json(candidate_run_dir / "evaluation_summary_v2.json")
    baseline_summary = None
    if baseline_run_dir is not None and (baseline_run_dir / "evaluation_summary_v2.json").exists():
        baseline_summary = read_json(baseline_run_dir / "evaluation_summary_v2.json")
    rows = list(candidate_summary.get("rows", []))
    primary = [row for row in rows if row.get("slice_type") == "non_tension_primary"]
    secondary = [row for row in rows if row.get("slice_type") == "criteria_gold_tension_secondary"]
    payload = {
        "created_at": utc_now_iso(),
        "candidate_run_dir": repo_rel(candidate_run_dir),
        "baseline_run_dir": repo_rel(baseline_run_dir) if baseline_run_dir else None,
        "is_failure_slice_dev_diagnostic": True,
        "not_unbiased_evaluation": True,
        "recovery": {
            "primary22": recovery_counts(primary),
            "secondary105": recovery_counts(secondary),
            "all": recovery_counts(rows),
        },
        "comparison_to_baseline": compare_to_baseline(
            candidate_summary=candidate_summary,
            baseline_summary=baseline_summary,
        ),
    }
    write_json(candidate_run_dir / "error_analysis.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--baseline-run-id")
    args = parser.parse_args()
    baseline = run_dir(args.baseline_run_id) if args.baseline_run_id else None
    payload = analyze_run(candidate_run_dir=run_dir(args.run_id), baseline_run_dir=baseline)
    print(payload["recovery"]["all"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
