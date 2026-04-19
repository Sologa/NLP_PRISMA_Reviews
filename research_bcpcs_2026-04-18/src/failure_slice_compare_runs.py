#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from failure_slice_common import read_json, run_dir, write_json


def _rows_by_key(eval_summary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("paper_id")), str(row.get("candidate_key"))): row
        for row in (eval_summary.get("rows") or [])
    }


def compare_runs(*, baseline_run_id: str, target_run_id: str) -> dict[str, Any]:
    baseline_dir = run_dir(baseline_run_id)
    target_dir = run_dir(target_run_id)
    baseline_eval = read_json(baseline_dir / "evaluation_summary.json")
    target_eval = read_json(target_dir / "evaluation_summary.json")

    baseline_rows = _rows_by_key(baseline_eval)
    target_rows = _rows_by_key(target_eval)
    keys = sorted(set(baseline_rows) & set(target_rows))

    changed: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    by_paper: dict[str, Counter[str]] = defaultdict(Counter)
    by_slice: dict[str, Counter[str]] = defaultdict(Counter)

    for key in keys:
        b = baseline_rows[key]
        t = target_rows[key]
        baseline_outcome = str(b.get("outcome"))
        target_outcome = str(t.get("outcome"))
        baseline_decision = str(b.get("final_stage_decision"))
        target_decision = str(t.get("final_stage_decision"))
        if baseline_outcome == target_outcome and baseline_decision == target_decision:
            continue
        paper_id, candidate_key = key
        slice_type = str(t.get("slice_type"))

        if baseline_outcome != "recovered" and target_outcome == "recovered":
            transition = "improved_to_recovered"
        elif baseline_outcome == "recovered" and target_outcome != "recovered":
            transition = "regressed_from_recovered"
        elif baseline_outcome == "still_wrong" and target_outcome == "unknown_or_routed":
            transition = "deferred_unknown"
        elif baseline_outcome == "unknown_or_routed" and target_outcome == "still_wrong":
            transition = "unknown_to_wrong"
        else:
            transition = f"{baseline_outcome}_to_{target_outcome}"

        row = {
            "paper_id": paper_id,
            "candidate_key": candidate_key,
            "slice_type": slice_type,
            "gold_label": t.get("gold_label"),
            "prior_error_type": t.get("prior_error_type"),
            "baseline_decision": baseline_decision,
            "target_decision": target_decision,
            "baseline_outcome": baseline_outcome,
            "target_outcome": target_outcome,
            "transition": transition,
        }
        changed.append(row)
        counters[transition] += 1
        by_paper[paper_id][transition] += 1
        by_slice[slice_type][transition] += 1

    summary = {
        "baseline_run_id": baseline_run_id,
        "target_run_id": target_run_id,
        "compared_row_count": len(keys),
        "changed_row_count": len(changed),
        "transition_counts": dict(counters),
        "by_paper": {paper_id: dict(counter) for paper_id, counter in sorted(by_paper.items())},
        "by_slice": {slice_type: dict(counter) for slice_type, counter in sorted(by_slice.items())},
        "changed_rows": changed,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-run-id", required=True)
    parser.add_argument("--target-run-id", required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    args = parser.parse_args()

    payload = compare_runs(
        baseline_run_id=args.baseline_run_id,
        target_run_id=args.target_run_id,
    )
    write_json(args.output_path, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
