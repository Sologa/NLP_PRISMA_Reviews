#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screening.cutoff_time_filter import cutoff_json_path, evaluate_record, load_time_policy

DEFAULT_PAPERS = [
    "2307.05527",
    "2409.13738",
    "2511.13936",
    "2601.19926",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL in {path}:{line_no}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _bool_label(value: Any) -> bool:
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
    raise SystemExit(f"Unsupported is_evidence_base label: {value!r}")


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _dedupe_records(
    rows: list[dict[str, Any]],
    *,
    label: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    keyed: dict[str, dict[str, Any]] = {}
    counts: Counter[str] = Counter()
    for row in rows:
        key = str(row.get("key") or "").strip()
        if not key:
            raise SystemExit(f"{label} contains a row without a usable key")
        counts[key] += 1
        if key not in keyed:
            keyed[key] = row
    duplicates = {key: count for key, count in sorted(counts.items()) if count > 1}
    return keyed, duplicates


def _load_gold_map(path: Path) -> tuple[dict[str, bool], dict[str, int]]:
    rows = _load_jsonl(path)
    keyed: dict[str, bool] = {}
    counts: Counter[str] = Counter()
    for row in rows:
        key = str(row.get("key") or "").strip()
        if not key:
            raise SystemExit(f"{path} contains a row without a usable key")
        label = _bool_label(row.get("is_evidence_base"))
        counts[key] += 1
        if key in keyed and keyed[key] != label:
            raise SystemExit(f"Conflicting gold labels for key {key} in {path}")
        keyed[key] = label
    duplicates = {key: count for key, count in sorted(counts.items()) if count > 1}
    return keyed, duplicates


def _round4(value: float) -> float:
    return round(value, 4)


def _build_paper_report(paper_id: str) -> dict[str, Any]:
    metadata_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
    gold_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
    cutoff_path = cutoff_json_path(REPO_ROOT, paper_id)

    metadata_rows = _load_jsonl(metadata_path)
    metadata_by_key, metadata_duplicates = _dedupe_records(metadata_rows, label=str(metadata_path))
    gold_by_key, gold_duplicates = _load_gold_map(gold_path)
    _, policy = load_time_policy(cutoff_path)

    metadata_keys = set(metadata_by_key)
    gold_keys = set(gold_by_key)
    missing_in_gold = sorted(metadata_keys - gold_keys)
    missing_in_metadata = sorted(gold_keys - metadata_keys)
    if missing_in_gold or missing_in_metadata:
        raise SystemExit(
            f"Key mismatch for {paper_id}: "
            f"missing_in_gold={len(missing_in_gold)} missing_in_metadata={len(missing_in_metadata)}"
        )

    status_counts: Counter[str] = Counter()
    tp = fp = tn = fn = 0
    gold_true_cutoffed_keys: list[str] = []

    for key in sorted(metadata_by_key):
        decision = evaluate_record(metadata_by_key[key], policy)
        gold_positive = gold_by_key[key]
        cutoff_pass = bool(decision["cutoff_pass"])
        status_counts[str(decision["cutoff_status"])] += 1

        if cutoff_pass and gold_positive:
            tp += 1
        elif cutoff_pass and not gold_positive:
            fp += 1
        elif (not cutoff_pass) and gold_positive:
            fn += 1
            gold_true_cutoffed_keys.append(key)
        else:
            tn += 1

    total = len(metadata_by_key)
    gold_positive_count = sum(1 for value in gold_by_key.values() if value)
    gold_negative_count = total - gold_positive_count
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0
    correct_predictions_via_cutoff_exclude = tn
    correct_predictions_via_cutoff_pass = tp
    all_correct_predictions_are_cutoffed = correct_predictions_via_cutoff_pass == 0
    all_gold_true_are_cutoffed = tp == 0

    if all_correct_predictions_are_cutoffed:
        core_question_answer = "Yes. All correct predictions come from cutoff excludes."
    else:
        core_question_answer = (
            "No. Some correct predictions remain after cutoff "
            f"({correct_predictions_via_cutoff_pass} pass-and-correct, "
            f"{len(gold_true_cutoffed_keys)} gold-positive cutoffed)."
        )

    return {
        "paper_id": paper_id,
        "metadata_path": _relative(metadata_path),
        "gold_path": _relative(gold_path),
        "cutoff_json_path": _relative(cutoff_path),
        "time_policy": {
            "enabled": policy.enabled,
            "date_field": policy.date_field,
            "start_date": policy.start_date.isoformat() if policy.start_date is not None else None,
            "start_inclusive": policy.start_inclusive,
            "end_date": policy.end_date.isoformat() if policy.end_date is not None else None,
            "end_inclusive": policy.end_inclusive,
            "timezone": policy.timezone,
        },
        "dedup": {
            "metadata_input_rows": len(metadata_rows),
            "metadata_unique_keys": total,
            "metadata_duplicate_keys": metadata_duplicates,
            "gold_duplicate_keys": gold_duplicates,
        },
        "key_consistency": {
            "missing_in_gold_count": len(missing_in_gold),
            "missing_in_gold_keys": missing_in_gold,
            "missing_in_metadata_count": len(missing_in_metadata),
            "missing_in_metadata_keys": missing_in_metadata,
            "verified_no_missing_keys_after_dedup": not missing_in_gold and not missing_in_metadata,
            "verified_2511_dedup_total_is_88": paper_id != "2511.13936" or total == 88,
        },
        "total_candidates": total,
        "gold_positive_count": gold_positive_count,
        "gold_negative_count": gold_negative_count,
        "cutoff_status_counts": dict(sorted(status_counts.items())),
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        },
        "metrics_if_cutoff_pass_means_include": {
            "accuracy": _round4(accuracy),
            "precision": _round4(precision),
            "recall": _round4(recall),
            "f1": _round4(f1),
        },
        "correct_predictions_via_cutoff_exclude": correct_predictions_via_cutoff_exclude,
        "correct_predictions_via_cutoff_pass": correct_predictions_via_cutoff_pass,
        "all_correct_predictions_are_cutoffed": all_correct_predictions_are_cutoffed,
        "all_gold_true_are_cutoffed": all_gold_true_are_cutoffed,
        "gold_true_cutoffed_count": len(gold_true_cutoffed_keys),
        "gold_true_cutoffed_keys": gold_true_cutoffed_keys,
        "core_question_answer": core_question_answer,
    }


def _render_report(summary: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Cutoff-Only Audit Against Gold",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "- Decision rule: `cutoff_pass=true => include/keep`, `cutoff_pass=false => exclude`",
        "- Gold label: `is_evidence_base=true`",
        "- Candidate universe: unique `key` values from `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`",
        "",
        "## Summary",
        "",
        "| Paper | Total | Gold+ | Gold+ cutoffed | Correct via cutoff exclude | Correct via cutoff pass | All correct cutoffed? |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for paper_id in summary["paper_order"]:
        report = summary["papers"][paper_id]
        lines.append(
            f"| `{paper_id}` | {report['total_candidates']} | {report['gold_positive_count']} | "
            f"{report['gold_true_cutoffed_count']} | {report['correct_predictions_via_cutoff_exclude']} | "
            f"{report['correct_predictions_via_cutoff_pass']} | "
            f"{'yes' if report['all_correct_predictions_are_cutoffed'] else 'no'} |"
        )

    for paper_id in summary["paper_order"]:
        report = summary["papers"][paper_id]
        lines.extend(
            [
                "",
                f"## {paper_id}",
                "",
                f"- Core question answer: {report['core_question_answer']}",
                f"- Key consistency verified: `{report['key_consistency']['verified_no_missing_keys_after_dedup']}`",
                f"- Cutoff status counts: `{json.dumps(report['cutoff_status_counts'], ensure_ascii=True)}`",
                f"- Confusion matrix: `{json.dumps(report['confusion_matrix'], ensure_ascii=True)}`",
                f"- Gold-positive papers removed by cutoff: `{report['gold_true_cutoffed_count']}`",
                "",
            ]
        )
        if report["gold_true_cutoffed_keys"]:
            for key in report["gold_true_cutoffed_keys"]:
                lines.append(f"- `{key}`")
        else:
            lines.append("- `(none)`")

    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit cutoff-only decisions against gold labels.")
    parser.add_argument(
        "--papers",
        nargs="*",
        default=DEFAULT_PAPERS,
        help="Paper IDs to audit. Defaults to the four canonical SR papers.",
    )
    parser.add_argument(
        "--output-dir",
        default=f"screening/results/cutoff_only_audit_{datetime.now().date().isoformat()}",
        help="Directory to write audit artifacts into.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    papers = list(dict.fromkeys(args.papers))

    output_dir.mkdir(parents=True, exist_ok=True)
    papers_dir = output_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "analysis_name": "cutoff_only_audit_vs_gold",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "output_dir": _relative(output_dir),
        "paper_order": papers,
        "assumptions": {
            "gold_positive_label": "is_evidence_base=true",
            "cutoff_pass_interpretation": "include_or_keep",
            "cutoff_fail_interpretation": "exclude",
            "candidate_universe": "unique metadata keys",
            "missing_or_unparseable_published_date_fails_cutoff": True,
        },
        "papers": {},
    }

    papers_with_all_correct_cutoffed: list[str] = []
    papers_with_gold_true_cutoffed: list[str] = []

    for paper_id in papers:
        report = _build_paper_report(paper_id)
        summary["papers"][paper_id] = report
        if report["all_correct_predictions_are_cutoffed"]:
            papers_with_all_correct_cutoffed.append(paper_id)
        if report["gold_true_cutoffed_count"] > 0:
            papers_with_gold_true_cutoffed.append(paper_id)
        paper_dir = papers_dir / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)
        _write_json(paper_dir / "cutoff_vs_gold.json", report)

    summary["global_summary"] = {
        "all_papers_have_all_correct_answers_cutoffed": len(papers_with_all_correct_cutoffed) == len(papers),
        "papers_with_all_correct_answers_cutoffed": papers_with_all_correct_cutoffed,
        "papers_with_any_gold_true_cutoffed": papers_with_gold_true_cutoffed,
        "papers_with_zero_gold_true_cutoffed": [
            paper_id for paper_id in papers if paper_id not in papers_with_gold_true_cutoffed
        ],
    }

    report_text = _render_report(summary)
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "report.md").write_text(report_text, encoding="utf-8")
    _write_json(
        output_dir / "run_manifest.json",
        {
            "analysis_name": summary["analysis_name"],
            "generated_at": summary["generated_at"],
            "papers": papers,
            "summary_path": _relative(output_dir / "summary.json"),
            "report_path": _relative(output_dir / "report.md"),
        },
    )

    print(f"[cutoff-audit] wrote {output_dir / 'summary.json'}")
    print(f"[cutoff-audit] wrote {output_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
