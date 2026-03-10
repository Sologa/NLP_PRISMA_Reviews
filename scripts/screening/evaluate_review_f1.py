#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return None


def _load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows = []
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL in {path}:{idx}: {exc}") from exc
            if isinstance(item, dict):
                rows.append(item)
        return rows

    payload = _load_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("records", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise SystemExit(f"Unsupported JSON format: {path}")


def _to_verdict_bool(value: Any, positive_mode: str) -> int | None:
    verdict = str(value or "").strip().lower()
    if not verdict:
        return None

    m = re.match(r"^\s*([a-z]+)", verdict)
    if m:
        label = m.group(1)
        if label == "include":
            return 1
        if label == "maybe":
            return 1 if positive_mode in {"include_or_maybe", "maybe_only"} else 0
        if label == "exclude":
            return 0
    return None


def _to_verdict_label(value: Any) -> str:
    verdict = str(value or "").strip().lower()
    if not verdict:
        return "unknown"
    m = re.match(r"^\s*([a-z]+)", verdict)
    if not m:
        return "unknown"
    label = m.group(1)
    if label in {"include", "exclude", "maybe", "discard"}:
        return label
    return "unknown"


def _int_to_bool(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and value == int(value):
        score = int(value)
    else:
        try:
            score = int(str(value).strip())
        except ValueError:
            return None
    if score >= 4:
        return 1
    if score <= 2:
        return 0
    return None


def _precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _find_key(item: dict[str, Any]) -> str | None:
    key = item.get("key")
    if key is not None:
        key = str(key).strip()
        if key:
            return key

    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        key = metadata.get("key")
        if key is None:
            return None
        key = str(key).strip()
        return key or None
    return None


def _predict_row(row: dict[str, Any], positive_mode: str) -> int:
    pred = _to_verdict_bool(row.get("final_verdict"), positive_mode)
    if pred is not None:
        return pred
    if row.get("round-B_SeniorLead_evaluation") is not None:
        pred = _int_to_bool(row.get("round-B_SeniorLead_evaluation"))
    elif row.get("round-A_JuniorNano_evaluation") is not None:
        pred = _int_to_bool(row.get("round-A_JuniorNano_evaluation"))
    return 0 if pred is None else pred


def _build_report(
    paper_id: str,
    results_path: Path,
    gold_path: Path,
    positive_mode: str,
    matched: int,
    dropped_no_key: int,
    verdict_counter: dict[str, int],
    gold_map: dict[str, int],
    pred_map: dict[str, int],
    scores: dict[str, float] | None,
    results_count: int,
    tp: int = 0,
    fp: int = 0,
    tn: int = 0,
    fn: int = 0,
) -> dict[str, Any]:
    missing_from_results = sorted(set(gold_map.keys()) - set(pred_map.keys()))
    extra_in_results = sorted(set(pred_map.keys()) - set(gold_map.keys()))
    report: dict[str, Any] = {
        "paper_id": paper_id,
        "results_path": str(results_path),
        "gold_path": str(gold_path),
        "positive_mode": positive_mode,
        "matched": matched,
        "dropped_no_key": dropped_no_key,
        "verdict_counts": verdict_counter,
        "gold_size": len(gold_map),
        "results_size": results_count,
        "gold_only_count": len(missing_from_results),
        "extra_result_only_count": len(extra_in_results),
    }
    if scores is not None:
        report["metrics"] = {
            "precision": scores["precision"],
            "recall": scores["recall"],
            "f1": scores["f1"],
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        }
    else:
        report["metrics"] = {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate screening verdicts against is_evidence_base labels.")
    parser.add_argument("paper_id", help="Paper ID used for matching and logging.")
    parser.add_argument("--results", type=Path, required=True, help="Path to latte_review_results.json")
    parser.add_argument("--gold-metadata", type=Path, required=True, help="Path to title_abstracts_metadata(-annotated).jsonl")
    parser.add_argument(
        "--positive-mode",
        choices=["include_only", "include_or_maybe", "maybe_only"],
        default="include_or_maybe",
        help=(
            "How to map final_verdict to positive labels. "
            "include_or_maybe is recommended for full-recall screening."
        ),
    )
    parser.add_argument("--save-report", type=Path, default=None, help="Optional path to write JSON summary")
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="Annotate results in-place with correctness flags against gold labels.",
    )
    parser.add_argument("--strip-metadata", action="store_true", help="Drop metadata field when writing annotated output.")
    args = parser.parse_args()

    results_path = args.results.resolve()
    gold_path = args.gold_metadata.resolve()
    if not results_path.exists():
        raise SystemExit(f"Missing results file: {results_path}")
    if not gold_path.exists():
        raise SystemExit(f"Missing gold metadata file: {gold_path}")

    results = _load_records(results_path)
    if not isinstance(results, list):
        raise SystemExit(f"Expected list in {results_path}")

    gold_records = _load_records(gold_path)
    gold_map: dict[str, int] = {}
    for row in gold_records:
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        label = _parse_bool(row.get("is_evidence_base"))
        if label is None:
            continue
        gold_map[key] = 1 if label else 0

    if not gold_map:
        raise SystemExit(f"No usable is_evidence_base labels found in {gold_path}")

    pred_map: dict[str, int] = {}
    verdict_counter: dict[str, int] = {}
    dropped_no_key = 0

    for row in results:
        key = _find_key(row)
        verdict = str(row.get("final_verdict") or "")
        verdict_counter[verdict] = verdict_counter.get(verdict, 0) + 1
        pred = _predict_row(row, args.positive_mode)
        if key:
            pred_map[key] = pred
            row["key"] = key
        else:
            dropped_no_key += 1

    matched_keys = sorted(set(pred_map.keys()) & set(gold_map.keys()))

    if not matched_keys:
        print(f"[eval] paper_id={args.paper_id}")
        print(f"[eval] results_path={results_path}")
        print(f"[eval] gold_path={gold_path}")
        print("[eval] no matching keys between prediction output and gold labels.")
        report = _build_report(
            args.paper_id,
            results_path,
            gold_path,
            args.positive_mode,
            len(matched_keys),
            dropped_no_key,
            verdict_counter,
            gold_map,
            pred_map,
            None,
            len(results),
        )
        if args.save_report is not None:
            args.save_report.parent.mkdir(parents=True, exist_ok=True)
            args.save_report.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[eval] report={args.save_report}")

        if args.annotate:
            for row in results:
                if args.strip_metadata:
                    row.pop("metadata", None)
                row_key = _find_key(row)
                pred = _predict_row(row, args.positive_mode)
                row["prediction_label"] = _to_verdict_label(row.get("final_verdict"))
                row["predicted_score"] = pred
                row["is_wrong"] = None
                row["is_correct"] = None
                if row_key is not None and row_key in gold_map:
                    gt = gold_map[row_key]
                    row["ground_truth"] = bool(gt)
                    row["is_wrong"] = bool(pred != gt)
                    row["is_correct"] = bool(pred == gt)
                else:
                    row["ground_truth"] = None
                if row_key:
                    row["key"] = row_key
            results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[eval] annotated_results={results_path}")
            return 0
        raise SystemExit("No matched keys between results and gold labels.")

    tp = fp = fn = tn = 0
    for key in matched_keys:
        y_true = gold_map[key]
        y_pred = pred_map[key]
        if y_true == 1 and y_pred == 1:
            tp += 1
        elif y_true == 1 and y_pred == 0:
            fn += 1
        elif y_true == 0 and y_pred == 1:
            fp += 1
        else:
            tn += 1

    scores = _precision_recall_f1(tp, fp, fn)
    missing_from_results = sorted(set(gold_map.keys()) - set(pred_map.keys()))
    extra_in_results = sorted(set(pred_map.keys()) - set(gold_map.keys()))

    print(f"[eval] paper_id={args.paper_id}")
    print(f"[eval] results_path={results_path}")
    print(f"[eval] gold_path={gold_path}")
    print(f"[eval] rows_loaded={len(results)}")
    print(f"[eval] unique_gold={len(gold_map)}")
    print(f"[eval] matched={len(matched_keys)}")
    print(f"[eval] dropped_no_key={dropped_no_key}")
    print(f"[eval] verdict_counts={len(verdict_counter)}")
    for verdict, count in sorted(verdict_counter.items(), key=lambda item: item[1], reverse=True):
        print(f"[eval]   {verdict}: {count}")
    print(f"[eval] confusion tp={tp} fp={fp} tn={tn} fn={fn}")
    print(f"[eval] precision={scores['precision']:.4f} recall={scores['recall']:.4f} f1={scores['f1']:.4f}")
    if missing_from_results:
        print(f"[eval] gold_only_count={len(missing_from_results)}")
    if extra_in_results:
        print(f"[eval] extra_result_only_count={len(extra_in_results)}")

    report = _build_report(
        args.paper_id,
        results_path,
        gold_path,
        args.positive_mode,
        len(matched_keys),
        dropped_no_key,
        verdict_counter,
        gold_map,
        pred_map,
        scores,
        len(results),
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
    )
    if args.save_report is not None:
        args.save_report.parent.mkdir(parents=True, exist_ok=True)
        args.save_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[eval] report={args.save_report}")

    if args.annotate:
        for row in results:
            if args.strip_metadata:
                row.pop("metadata", None)
            row_key = _find_key(row)
            pred = _predict_row(row, args.positive_mode)
            row["prediction_label"] = _to_verdict_label(row.get("final_verdict"))
            row["predicted_score"] = pred
            if row_key is not None:
                row["key"] = row_key
                if row_key in gold_map:
                    gt = gold_map[row_key]
                    row["ground_truth"] = bool(gt)
                    row["is_wrong"] = bool(pred != gt)
                    row["is_correct"] = bool(pred == gt)
                else:
                    row["ground_truth"] = None
                    row["is_wrong"] = None
                    row["is_correct"] = None
            else:
                row["ground_truth"] = None
                row["is_wrong"] = None
                row["is_correct"] = None
        results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[eval] annotated_results={results_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
