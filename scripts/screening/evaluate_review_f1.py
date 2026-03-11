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


def _load_key_filter(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keys.add(stripped)
    if not keys:
        raise SystemExit(f"No usable keys found in {path}")
    return keys


def _predict_row(row: dict[str, Any], positive_mode: str) -> int:
    pred = _to_verdict_bool(row.get("final_verdict"), positive_mode)
    if pred is not None:
        return pred
    if row.get("round-B_SeniorLead_evaluation") is not None:
        pred = _int_to_bool(row.get("round-B_SeniorLead_evaluation"))
    elif row.get("round-A_JuniorNano_evaluation") is not None:
        pred = _int_to_bool(row.get("round-A_JuniorNano_evaluation"))
    return 0 if pred is None else pred


def _index_records_by_key(
    records: list[dict[str, Any]],
    *,
    key_filter: set[str] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str], int, list[dict[str, Any]]]:
    keyed: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    dropped_no_key = 0
    skipped: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        key = _find_key(row)
        if key_filter is not None and key is not None and key not in key_filter:
            continue
        if not key:
            dropped_no_key += 1
            skipped.append(row)
            continue
        if key not in keyed:
            keyed[key] = row
            order.append(key)
    return keyed, order, dropped_no_key, skipped


def _collect_verdict_and_predictions(
    records: list[dict[str, Any]],
    *,
    positive_mode: str,
    key_filter: set[str] | None = None,
) -> tuple[dict[str, int], dict[str, int], int]:
    pred_map: dict[str, int] = {}
    verdict_counter: dict[str, int] = {}
    dropped_no_key = 0
    for row in records:
        if not isinstance(row, dict):
            continue
        key = _find_key(row)
        if key_filter is not None and key is not None and key not in key_filter:
            continue
        verdict = str(row.get("final_verdict") or "")
        verdict_counter[verdict] = verdict_counter.get(verdict, 0) + 1
        pred = _predict_row(row, positive_mode)
        if key:
            pred_map[key] = pred
            row["key"] = key
        else:
            dropped_no_key += 1
    return pred_map, verdict_counter, dropped_no_key


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
    keys_file: Path | None = None,
    keys_count: int | None = None,
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
    if keys_file is not None:
        report["keys_file"] = str(keys_file)
    if keys_count is not None:
        report["keys_count"] = int(keys_count)
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
        "--keys-file",
        type=Path,
        default=None,
        help="Optional newline-delimited key list; evaluate only these keys.",
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="Annotate results in-place with correctness flags against gold labels.",
    )
    parser.add_argument("--strip-metadata", action="store_true", help="Drop metadata field when writing annotated output.")
    parser.add_argument(
        "--combine-with-base",
        action="store_true",
        help="Combine fulltext output with base-review outputs before computing metrics.",
    )
    parser.add_argument(
        "--base-review-results",
        type=Path,
        default=None,
        help="When --combine-with-base is set, provide the base review results JSON.",
    )
    args = parser.parse_args()

    results_path = args.results.resolve()
    gold_path = args.gold_metadata.resolve()
    if not results_path.exists():
        raise SystemExit(f"Missing results file: {results_path}")
    if not gold_path.exists():
        raise SystemExit(f"Missing gold metadata file: {gold_path}")
    if args.combine_with_base and args.base_review_results is None:
        raise SystemExit("--combine-with-base requires --base-review-results")
    key_filter: set[str] | None = None
    if args.keys_file is not None:
        keys_path = args.keys_file.resolve()
        if not keys_path.exists():
            raise SystemExit(f"Missing keys file: {keys_path}")
        key_filter = _load_key_filter(keys_path)

    results = _load_records(results_path)
    if not isinstance(results, list):
        raise SystemExit(f"Expected list in {results_path}")

    base_results = None
    if args.base_review_results is not None:
        base_path = args.base_review_results.resolve()
        if not base_path.exists():
            raise SystemExit(f"Missing base review results file: {base_path}")
        base_results = _load_records(base_path)
        if not isinstance(base_results, list):
            raise SystemExit(f"Expected list in {base_path}")

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
    if key_filter is not None:
        gold_map = {key: value for key, value in gold_map.items() if key in key_filter}

    if not gold_map:
        raise SystemExit(f"No usable is_evidence_base labels found in {gold_path}")

    combined_rows: list[dict[str, Any]]
    pred_map: dict[str, int] = {}
    verdict_counter: dict[str, int] = {}
    dropped_no_key = 0

    if args.combine_with_base:
        if base_results is None:
            raise SystemExit("--combine-with-base requires --base-review-results")
        base_records, base_order, base_dropped_no_key, _ = _index_records_by_key(
            base_results,
            key_filter=key_filter,
        )
        fulltext_records, _, fulltext_dropped_no_key, _ = _index_records_by_key(
            results,
            key_filter=key_filter,
        )
        dropped_no_key = base_dropped_no_key + fulltext_dropped_no_key
        combined_rows = []
        for key in base_order:
            base_row = base_records[key]
            merged = dict(base_row)
            source_row = base_row
            if key in fulltext_records:
                fulltext_row = fulltext_records[key]
                merged.update(fulltext_row)
                merged["base_final_verdict"] = str(base_row.get("final_verdict") or "")
                source_row = fulltext_row

            source_verdict = str(source_row.get("final_verdict") or "")
            verdict_counter[source_verdict] = verdict_counter.get(source_verdict, 0) + 1
            pred = _predict_row(source_row, args.positive_mode)
            pred_map[key] = pred
            merged["key"] = key
            combined_rows.append(merged)
        for key, fulltext_row in fulltext_records.items():
            if key in base_records:
                continue
            pred = _predict_row(fulltext_row, args.positive_mode)
            pred_map[key] = pred
            verdict = str(fulltext_row.get("final_verdict") or "")
            verdict_counter[verdict] = verdict_counter.get(verdict, 0) + 1
            row_with_key = dict(fulltext_row)
            row_with_key["key"] = key
            combined_rows.append(row_with_key)
    else:
        pred_map, verdict_counter, dropped_no_key = _collect_verdict_and_predictions(
            results,
            positive_mode=args.positive_mode,
            key_filter=key_filter,
        )
        combined_rows = [row for row in results if isinstance(row, dict)]

    matched_keys = sorted(set(pred_map.keys()) & set(gold_map.keys()))

    if not matched_keys:
        print(f"[eval] paper_id={args.paper_id}")
        print(f"[eval] results_path={results_path}")
        print(f"[eval] gold_path={gold_path}")
        if args.combine_with_base:
            print("[eval] combine_with_base=True")
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
            len(combined_rows),
            keys_file=args.keys_file.resolve() if args.keys_file is not None else None,
            keys_count=len(key_filter) if key_filter is not None else None,
        )
        if args.save_report is not None:
            args.save_report.parent.mkdir(parents=True, exist_ok=True)
            args.save_report.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[eval] report={args.save_report}")

        if args.annotate:
            rows_to_annotate = combined_rows if args.combine_with_base else [row for row in results if isinstance(row, dict)]
            for row in rows_to_annotate:
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
            results_path.write_text(json.dumps(rows_to_annotate, ensure_ascii=False, indent=2), encoding="utf-8")
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
    if args.combine_with_base:
        print("[eval] combine_with_base=True")
    if key_filter is not None:
        print(f"[eval] keys_filter={len(key_filter)} from {args.keys_file.resolve()}")
    print(f"[eval] rows_loaded={len(combined_rows)}")
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
        len(combined_rows),
        keys_file=args.keys_file.resolve() if args.keys_file is not None else None,
        keys_count=len(key_filter) if key_filter is not None else None,
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
        rows_to_annotate = combined_rows if args.combine_with_base else [row for row in results if isinstance(row, dict)]
        for row in rows_to_annotate:
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
        results_path.write_text(json.dumps(rows_to_annotate, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[eval] annotated_results={results_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
