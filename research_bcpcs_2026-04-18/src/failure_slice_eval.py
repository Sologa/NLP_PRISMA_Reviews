#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from failure_slice_common import REPO_ROOT, read_json, read_jsonl, safe_text, write_json


POSITIVE_DECISIONS = {"include", "maybe"}
UNKNOWN_DECISIONS = {"unknown", "route_to_stage2"}


def _gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def load_gold_labels(paper_ids: list[str]) -> dict[tuple[str, str], bool]:
    labels: dict[tuple[str, str], bool] = {}
    for paper_id in paper_ids:
        for row in read_jsonl(_gold_path(paper_id)):
            key = safe_text(row.get("key"))
            if not key:
                continue
            value = row.get("is_evidence_base")
            if isinstance(value, bool):
                labels[(paper_id, key)] = value
            elif isinstance(value, str):
                labels[(paper_id, key)] = value.strip().lower() in {"true", "1", "yes", "include"}
    return labels


def decision_to_prediction(decision: str) -> int | None:
    normalized = decision.strip().lower()
    if normalized in POSITIVE_DECISIONS:
        return 1
    if normalized == "exclude":
        return 0
    if normalized in UNKNOWN_DECISIONS:
        return None
    return 0


def compute_binary_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    skipped_unknown = 0
    for row in rows:
        gold = bool(row["gold_label"])
        pred = row.get("prediction")
        if pred is None:
            skipped_unknown += 1
            pred = 0
        if pred == 1 and gold:
            tp += 1
        elif pred == 1 and not gold:
            fp += 1
        elif pred == 0 and not gold:
            tn += 1
        elif pred == 0 and gold:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "unknown_mapped_negative_count": skipped_unknown,
    }


def evidence_validity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ledger_count = 0
    output_count = 0
    with_ledger = 0
    span_validated_count = 0
    complete_span_count = 0
    for row in rows:
        for stage_name in ("stage1_output", "stage2_output"):
            output = row.get(stage_name)
            if not isinstance(output, dict):
                continue
            output_count += 1
            ledger = output.get("evidence_ledger")
            if isinstance(ledger, list) and ledger:
                with_ledger += 1
                ledger_count += len(ledger)
                for item in ledger:
                    if not isinstance(item, dict):
                        continue
                    if item.get("span_validated") is True:
                        span_validated_count += 1
                    if item.get("source_path") and (item.get("support_spans") or item.get("refute_spans") or item.get("quote") is not None):
                        complete_span_count += 1
    return {
        "stage_outputs": output_count,
        "stage_outputs_with_ledger": with_ledger,
        "ledger_rows": ledger_count,
        "span_validated_rows": span_validated_count,
        "span_complete_rows": complete_span_count,
        "stage_output_ledger_coverage": with_ledger / output_count if output_count else 0.0,
        "span_validated_rate": span_validated_count / ledger_count if ledger_count else 0.0,
        "span_completeness_rate": complete_span_count / ledger_count if ledger_count else 0.0,
    }


def evaluate_results(*, run_dir: Path) -> dict[str, Any]:
    private_inventory = read_json(run_dir / "evaluation_inventory_private.json")
    final_rows = read_json(run_dir / "assembled_results.json")
    paper_ids = sorted({row["paper_id"] for row in private_inventory["cases"]})
    gold = load_gold_labels(paper_ids)
    private_by_key = {(row["paper_id"], row["candidate_key"]): row for row in private_inventory["cases"]}

    eval_rows: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    by_slice: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in final_rows:
        paper_id = row["paper_id"]
        key = row["candidate_key"]
        source = private_by_key[(paper_id, key)]
        gold_label = gold[(paper_id, key)]
        decision = safe_text(row.get("final_stage_decision"))
        pred = decision_to_prediction(decision)
        if pred is None:
            counters["newly_unknown_or_routed"] += 1
        prior_error_type = safe_text(source.get("error_type"))
        recovered = False
        still_wrong = False
        if pred is None:
            outcome = "unknown_or_routed"
        elif bool(pred) == gold_label:
            recovered = True
            outcome = "recovered"
            if prior_error_type == "FP":
                counters["prior_fp_recovered"] += 1
            elif prior_error_type == "FN":
                counters["prior_fn_recovered"] += 1
        else:
            still_wrong = True
            outcome = "still_wrong"
            counters["still_wrong"] += 1
        eval_row = {
            "paper_id": paper_id,
            "candidate_key": key,
            "slice_type": source["slice_type"],
            "allowed_for_unbiased_eval": source["allowed_for_unbiased_eval"],
            "prior_error_type": prior_error_type,
            "gold_label": gold_label,
            "final_stage_decision": decision,
            "prediction": pred,
            "outcome": outcome,
            "recovered": recovered,
            "still_wrong": still_wrong,
            "stage1_output": row.get("stage1_output"),
            "stage2_output": row.get("stage2_output"),
            "final_row": row,
        }
        eval_rows.append(eval_row)
        by_slice[source["slice_type"]].append(eval_row)

    primary_rows = by_slice.get("non_tension_primary", [])
    secondary_rows = by_slice.get("criteria_gold_tension_secondary", [])
    summary = {
        "scope": private_inventory.get("scope"),
        "row_count": len(eval_rows),
        "primary_count": len(primary_rows),
        "secondary_count": len(secondary_rows),
        "metrics_primary22": compute_binary_metrics(primary_rows),
        "metrics_secondary": compute_binary_metrics(secondary_rows) if secondary_rows else None,
        "metrics_all_selected": compute_binary_metrics(eval_rows),
        "recovery": {
            "prior_fp_recovered": counters["prior_fp_recovered"],
            "prior_fn_recovered": counters["prior_fn_recovered"],
            "still_wrong": counters["still_wrong"],
            "newly_unknown_or_routed": counters["newly_unknown_or_routed"],
            "recovery_rate_definite_or_unknown_as_not_recovered": (
                sum(1 for row in eval_rows if row["recovered"]) / len(eval_rows) if eval_rows else 0.0
            ),
        },
        "decision_counts": dict(Counter(row["final_stage_decision"] for row in eval_rows)),
        "evidence_validity": evidence_validity(eval_rows),
        "rows": [
            {
                key: value
                for key, value in row.items()
                if key not in {"stage1_output", "stage2_output", "final_row"}
            }
            for row in eval_rows
        ],
    }
    write_json(run_dir / "evaluation_summary.json", summary)
    return summary

