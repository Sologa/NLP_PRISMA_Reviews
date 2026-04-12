#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "screening" / "results"
RESULTS_MANIFEST_PATH = RESULTS_ROOT / "results_manifest.json"
DOCS_DIR = REPO_ROOT / "docs" / "single_reviewer_baseline"
CSV_PATH = DOCS_DIR / "single_reviewer_runs_summary.csv"
REPORT_PATH = DOCS_DIR / "REPORT_zh.md"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _format_metric(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def _delta(metric_value: Any, baseline_value: Any) -> float | None:
    metric = _safe_float(metric_value)
    baseline = _safe_float(baseline_value)
    if metric is None or baseline is None:
        return None
    return metric - baseline


def _stage_model_for_run(run_manifest: dict[str, Any]) -> str | None:
    manifest_path = Path(str(run_manifest.get("manifest_path") or ""))
    if manifest_path.exists():
        bundle_manifest = _load_json(manifest_path)
        workflow = bundle_manifest.get("workflow") or {}
        stage_model = workflow.get("stage_model")
        if stage_model:
            return str(stage_model)
    stage_model = run_manifest.get("stage_model")
    return str(stage_model) if stage_model else None


def _baseline_family(stage_model: str | None) -> str | None:
    if stage_model == "one_stage_fulltext":
        return "historical_direct_review"
    if stage_model == "two_stage_direct_review":
        return "current_two_stage_direct_review"
    return None


def _run_scope(run_manifest: dict[str, Any]) -> str:
    candidate_keys_file = run_manifest.get("candidate_keys_file")
    max_records = run_manifest.get("max_records")
    if candidate_keys_file or max_records not in (None, ""):
        return "partial"
    return "full"


def _batch_status(run_manifest: dict[str, Any]) -> str:
    phase_jobs = run_manifest.get("phase_jobs") or {}
    if "stage2_review" in phase_jobs:
        return str((phase_jobs.get("stage2_review") or {}).get("batch_status") or "")
    if "stage1_review" in phase_jobs:
        return str((phase_jobs.get("stage1_review") or {}).get("batch_status") or "")
    return str(run_manifest.get("batch_status") or "")


def _iter_relevant_run_manifests() -> list[Path]:
    paths: list[Path] = []
    for path in RESULTS_ROOT.rglob("run_manifest.json"):
        if "/runs/" not in str(path):
            continue
        if "single_reviewer_official_batch" not in str(path):
            continue
        paths.append(path)
    return sorted(paths)


def _build_rows() -> list[dict[str, Any]]:
    baseline_manifest = _load_json(RESULTS_MANIFEST_PATH)["papers"]
    rows: list[dict[str, Any]] = []
    for path in _iter_relevant_run_manifests():
        run_manifest = _load_json(path)
        stage_model = _stage_model_for_run(run_manifest)
        family = _baseline_family(stage_model)
        if family is None:
            continue
        for summary in run_manifest.get("summaries", []):
            paper_id = str(summary["paper_id"])
            current_metrics = baseline_manifest.get(paper_id, {}).get("current_metrics", {})
            current_stage1 = current_metrics.get("stage1") or {}
            current_combined = current_metrics.get("combined") or {}
            stage1_f1 = summary.get("stage1_f1")
            current_stage1_f1 = current_stage1.get("f1")
            combined_f1 = summary.get("f1")
            current_combined_f1 = current_combined.get("f1")
            rows.append(
                {
                    "baseline_family": family,
                    "run_scope": _run_scope(run_manifest),
                    "stage_model": stage_model or "",
                    "run_id": str(run_manifest.get("run_id") or ""),
                    "model": str(run_manifest.get("model") or ""),
                    "reasoning_effort": str(run_manifest.get("reasoning_effort") or "未顯式設定"),
                    "paper_id": paper_id,
                    "batch_status": _batch_status(run_manifest),
                    "candidate_total": summary.get("candidate_total"),
                    "cutoff_pass_count": summary.get("cutoff_pass_count"),
                    "cutoff_excluded_count": summary.get("cutoff_excluded_count"),
                    "stage2_selected_count": summary.get("stage2_selected_count"),
                    "reviewed_count": summary.get("reviewed_count"),
                    "missing_count": summary.get("missing_count"),
                    "stage1_precision": summary.get("stage1_precision"),
                    "stage1_recall": summary.get("stage1_recall"),
                    "stage1_f1": stage1_f1,
                    "current_stage1_baseline_f1": current_stage1_f1,
                    "delta_vs_current_stage1": summary.get("delta_vs_current_stage1")
                    if summary.get("delta_vs_current_stage1") is not None
                    else _delta(stage1_f1, current_stage1_f1),
                    "combined_precision": summary.get("precision"),
                    "combined_recall": summary.get("recall"),
                    "combined_f1": combined_f1,
                    "current_combined_baseline_f1": current_combined_f1,
                    "delta_vs_current_combined": summary.get("delta_vs_current_combined")
                    if summary.get("delta_vs_current_combined") is not None
                    else _delta(combined_f1, current_combined_f1),
                    "stage1_results_path": summary.get("stage1_results_path", ""),
                    "stage1_metrics_path": summary.get("stage1_metrics_path", ""),
                    "combined_results_path": summary.get("results_path") or summary.get("results_path", ""),
                    "combined_metrics_path": summary.get("metrics_path") or summary.get("metrics_path", ""),
                    "report_path": str((Path(run_manifest.get("run_dir") or path.parent) / "REPORT_zh.md")),
                    "run_manifest_path": str(path),
                }
            )
    return rows


def _write_csv(rows: list[dict[str, Any]]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "baseline_family",
        "run_scope",
        "stage_model",
        "run_id",
        "model",
        "reasoning_effort",
        "paper_id",
        "batch_status",
        "candidate_total",
        "cutoff_pass_count",
        "cutoff_excluded_count",
        "stage2_selected_count",
        "reviewed_count",
        "missing_count",
        "stage1_precision",
        "stage1_recall",
        "stage1_f1",
        "current_stage1_baseline_f1",
        "delta_vs_current_stage1",
        "combined_precision",
        "combined_recall",
        "combined_f1",
        "current_combined_baseline_f1",
        "delta_vs_current_combined",
        "stage1_results_path",
        "stage1_metrics_path",
        "combined_results_path",
        "combined_metrics_path",
        "report_path",
        "run_manifest_path",
    ]
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _render_table(rows: list[dict[str, Any]], *, stage: str) -> list[str]:
    lines: list[str] = []
    if stage == "stage1":
        lines.append("| Paper | 模型 | effort | Stage 1 F1 | Precision | Recall | 與 current stage1 差值 | run_id |")
        lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
        for row in rows:
            lines.append(
                f"| `{row['paper_id']}` | `{row['model']}` | `{row['reasoning_effort']}` | "
                f"`{_format_metric(_safe_float(row['stage1_f1']))}` | "
                f"`{_format_metric(_safe_float(row['stage1_precision']))}` | "
                f"`{_format_metric(_safe_float(row['stage1_recall']))}` | "
                f"`{_format_metric(_safe_float(row['delta_vs_current_stage1'])) if row['delta_vs_current_stage1'] not in ('', None) else 'N/A'}` | "
                f"`{row['run_id']}` |"
            )
        return lines

    lines.append("| Paper | 模型 | effort | Combined F1 | Precision | Recall | 與 current combined 差值 | run_id |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for row in rows:
        lines.append(
            f"| `{row['paper_id']}` | `{row['model']}` | `{row['reasoning_effort']}` | "
            f"`{_format_metric(_safe_float(row['combined_f1']))}` | "
            f"`{_format_metric(_safe_float(row['combined_precision']))}` | "
            f"`{_format_metric(_safe_float(row['combined_recall']))}` | "
            f"`{_format_metric(_safe_float(row['delta_vs_current_combined'])) if row['delta_vs_current_combined'] not in ('', None) else 'N/A'}` | "
            f"`{row['run_id']}` |"
        )
    return lines


def _sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    combined = _safe_float(row["combined_f1"])
    stage1 = _safe_float(row["stage1_f1"])
    return (
        row["paper_id"],
        0 if row["baseline_family"] == "current_two_stage_direct_review" else 1,
        -(combined or -1.0),
        -(stage1 or -1.0),
        row["model"],
        row["reasoning_effort"],
        row["run_id"],
    )


def _write_report(rows: list[dict[str, Any]]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    current_rows = sorted(
        [
            row
            for row in rows
            if row["baseline_family"] == "current_two_stage_direct_review"
            and row["run_scope"] == "full"
            and row["batch_status"] == "completed"
        ],
        key=_sort_key,
    )
    historical_rows = sorted(
        [
            row
            for row in rows
            if row["baseline_family"] == "historical_direct_review"
            and row["run_scope"] == "full"
            and row["batch_status"] == "completed"
        ],
        key=_sort_key,
    )
    partial_rows = sorted([row for row in rows if row["run_scope"] == "partial"], key=_sort_key)
    current_papers = sorted({row["paper_id"] for row in current_rows})
    pending_two_stage = [paper for paper in ("2307.05527", "2601.19926") if paper not in current_papers]

    lines: list[str] = []
    lines.append("# Single Reviewer Baseline 總報告")
    lines.append("")
    lines.append(f"- 產生時間：`{now}`")
    lines.append(f"- CSV：`docs/single_reviewer_baseline/{CSV_PATH.name}`")
    lines.append("- 說明：current single reviewer baseline 已改為 `two-stage direct-review`；舊 `one-stage fulltext direct-review` 結果保留為 historical comparison。")
    lines.append("")
    lines.append("## Current Two-Stage Direct-Review Baseline")
    lines.append("")
    lines.append(f"- 已完成 paper-level 結果列數：`{len(current_rows)}`")
    if pending_two_stage:
        lines.append(f"- 尚未補跑 two-stage baseline 的 papers：`{', '.join(pending_two_stage)}`")
    if partial_rows:
        lines.append(f"- 已忽略 partial/smoke rows：`{len(partial_rows)}`")
    lines.append("")
    lines.append("### Stage 1")
    lines.append("")
    if current_rows:
        lines.extend(_render_table(current_rows, stage="stage1"))
    else:
        lines.append("- 目前沒有已完成的 two-stage Stage 1 baseline run。")
    lines.append("")
    lines.append("### Combined")
    lines.append("")
    if current_rows:
        lines.extend(_render_table(current_rows, stage="combined"))
    else:
        lines.append("- 目前沒有已完成的 two-stage combined baseline run。")
    lines.append("")
    lines.append("## Historical One-Stage Direct-Review")
    lines.append("")
    lines.append(f"- 已完成 paper-level 結果列數：`{len(historical_rows)}`")
    lines.append("- 這些 run 沒有真實 Stage 1 artifact，因此只有 combined 指標。")
    lines.append("")
    if historical_rows:
        lines.extend(_render_table(historical_rows, stage="combined"))
    else:
        lines.append("- 目前沒有 historical one-stage rows。")
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = _build_rows()
    _write_csv(rows)
    _write_report(rows)
    print(f"wrote {CSV_PATH}")
    print(f"wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
