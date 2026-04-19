#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from failure_slice_common import read_json, safe_text, write_json
from failure_slice_eval import decision_to_prediction, evidence_validity, load_gold_labels
from failure_slice_runtime_taxonomy import load_runtime_failures, runtime_category_for_row


DEFINITE_DECISIONS = {"include", "exclude", "maybe"}
ADVANCE_DECISIONS = {"include", "maybe", "route_to_stage2", "unknown"}


def _binary_metrics(rows: list[dict[str, Any]], *, unknown_as_negative: bool) -> dict[str, Any]:
    tp = fp = tn = fn = skipped = 0
    for row in rows:
        pred = row.get("prediction")
        if pred is None:
            if not unknown_as_negative:
                skipped += 1
                continue
            pred = 0
        gold = bool(row["gold_label"])
        if pred == 1 and gold:
            tp += 1
        elif pred == 1 and not gold:
            fp += 1
        elif pred == 0 and not gold:
            tn += 1
        elif pred == 0 and gold:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "evaluated_count": tp + fp + tn + fn,
        "skipped_unknown_or_runtime_count": skipped,
    }


def _coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    counts = Counter(row["decision_category"] for row in rows)
    runtime = Counter(row["runtime_failure_category"] for row in rows if row["runtime_failure_category"] != "none")
    definite = counts["definite"]
    return {
        "row_count": total,
        "definite_decision_count": definite,
        "definite_decision_rate": definite / total if total else 0.0,
        "unknown_or_routed_count": counts["unknown_or_routed"],
        "runtime_failure_count": sum(runtime.values()),
        "decision_category_counts": dict(counts),
        "runtime_failure_counts": dict(runtime),
    }


def _stage1_gate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = tn = fn = missing = 0
    positive_advanced = positive_blocked = 0
    negative_advanced = negative_blocked = 0
    for row in rows:
        stage1 = row.get("stage1_output")
        gold = bool(row["gold_label"])
        if not isinstance(stage1, dict):
            missing += 1
            advanced = False
        else:
            advanced = safe_text(stage1.get("final_stage_decision")) in ADVANCE_DECISIONS
        if advanced and gold:
            tp += 1
            positive_advanced += 1
        elif advanced and not gold:
            fp += 1
            negative_advanced += 1
        elif not advanced and not gold:
            tn += 1
            negative_blocked += 1
        elif not advanced and gold:
            fn += 1
            positive_blocked += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "stage1_gate_precision": precision,
        "stage1_gate_recall": recall,
        "stage1_gate_f1": f1,
        "positive_advanced_count": positive_advanced,
        "positive_blocked_count": positive_blocked,
        "negative_advanced_count": negative_advanced,
        "negative_blocked_count": negative_blocked,
        "stage1_missing_count": missing,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def evaluate_results_v2(*, run_dir: Path) -> dict[str, Any]:
    private_inventory = read_json(run_dir / "evaluation_inventory_private.json")
    final_rows = read_json(run_dir / "assembled_results.json")
    paper_ids = sorted({row["paper_id"] for row in private_inventory["cases"]})
    gold = load_gold_labels(paper_ids)
    private_by_key = {(row["paper_id"], row["candidate_key"]): row for row in private_inventory["cases"]}
    runtime_failures = load_runtime_failures(run_dir)

    eval_rows: list[dict[str, Any]] = []
    by_slice: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in final_rows:
        key = (row["paper_id"], row["candidate_key"])
        source = private_by_key[key]
        decision = safe_text(row.get("final_stage_decision"))
        prediction = decision_to_prediction(decision)
        runtime_category = runtime_category_for_row(row, runtime_failures)
        decision_category = "definite" if decision in DEFINITE_DECISIONS and runtime_category == "none" else "unknown_or_routed"
        eval_row = {
            "paper_id": row["paper_id"],
            "candidate_key": row["candidate_key"],
            "slice_type": source["slice_type"],
            "allowed_for_unbiased_eval": source["allowed_for_unbiased_eval"],
            "prior_error_type": safe_text(source.get("error_type")),
            "gold_label": bool(gold[key]),
            "final_stage_decision": decision,
            "prediction": prediction if decision_category == "definite" else None,
            "decision_category": decision_category,
            "runtime_failure_category": runtime_category,
            "review_state": row.get("review_state"),
            "stage1_output": row.get("stage1_output"),
            "stage2_output": row.get("stage2_output"),
            "final_row": row,
        }
        eval_rows.append(eval_row)
        by_slice[source["slice_type"]].append(eval_row)

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "auto_decidable_f1": _binary_metrics(rows, unknown_as_negative=False),
            "conservative_f1": _binary_metrics(rows, unknown_as_negative=True),
            "coverage": _coverage(rows),
            "stage1_gate": _stage1_gate_metrics(rows),
            "evidence_validity": evidence_validity(rows),
        }

    primary_rows = by_slice.get("non_tension_primary", [])
    secondary_rows = by_slice.get("criteria_gold_tension_secondary", [])
    summary = {
        "scope": private_inventory.get("scope"),
        "row_count": len(eval_rows),
        "primary_count": len(primary_rows),
        "secondary_count": len(secondary_rows),
        "primary22": summarize(primary_rows),
        "secondary105": summarize(secondary_rows),
        "all127": summarize(eval_rows),
        "runtime_failures": {
            f"{paper_id}::{candidate_key}": payload
            for (paper_id, candidate_key), payload in sorted(runtime_failures.items())
        },
        "rows": [
            {key: value for key, value in row.items() if key not in {"stage1_output", "stage2_output", "final_row"}}
            for row in eval_rows
        ],
    }
    write_json(run_dir / "evaluation_summary_v2.json", summary)
    return summary
