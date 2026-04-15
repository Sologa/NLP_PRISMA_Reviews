#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiment_lib import load_jsonl, read_json, write_json


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
CONFIG_PATH = BUNDLE_DIR / "config" / "experiment.json"


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _decision_note(summary: dict[str, Any]) -> str:
    combined = summary["combined_metrics"]["metrics"]
    current = summary["current_authority"]["combined"]
    baseline = summary["reference_single_reviewer"]["combined"]
    if int(combined["fn"]) > int(current["fn"]):
        return "不建議把這條 current-kernel 多 reviewer ledger 線當成下一步主線。它把 FN 拉高了，先不符合這輪 acceptance。"
    if _safe_float(combined["f1"]) < _safe_float(baseline["metrics"]["f1"]):
        return "暫時不建議把這條 current-kernel 多 reviewer ledger 線當成下一步主線。雙 junior + senior 還沒有贏過已跑完的簡化版 single-reviewer ledger baseline。"
    if _safe_float(combined["f1"]) >= _safe_float(current["f1"]):
        return "可以保留這條 current-kernel 多 reviewer ledger 線作為候選，但前提是 senior route rate 和成本都還在可接受範圍。"
    return "先不把這條線當主線。雖然沒有增加 FN，但整體沒有形成足夠清楚的收益。"


def build_run_summary_payload(run_dir: Path) -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    paper_dir = run_dir / "papers" / config["paper_id"]
    stage1_metrics = read_json(paper_dir / "stage1_metrics.json")
    combined_metrics = read_json(paper_dir / "combined_metrics.json")
    disagreement_audit = read_json(paper_dir / "disagreement_audit.json")
    current_stage1 = read_json(REPO_ROOT / config["current_authority_stage1_path"])
    current_combined = read_json(REPO_ROOT / config["current_authority_combined_path"])
    ref_stage1 = read_json(REPO_ROOT / config["reference_single_reviewer_stage1_path"])
    ref_combined = read_json(REPO_ROOT / config["reference_single_reviewer_combined_path"])

    usage_by_model: dict[str, dict[str, float]] = defaultdict(lambda: {"input_tokens": 0.0, "output_tokens": 0.0, "cost": 0.0, "calls": 0.0})
    for row in load_jsonl(run_dir / "response_log.jsonl"):
        usage = row.get("usage") or {}
        model = str(usage.get("model") or "unknown")
        usage_by_model[model]["input_tokens"] += _safe_float(usage.get("input_tokens"))
        usage_by_model[model]["output_tokens"] += _safe_float(usage.get("output_tokens"))
        usage_by_model[model]["cost"] += _safe_float(usage.get("cost"))
        usage_by_model[model]["calls"] += 1

    total_cost = sum(value["cost"] for value in usage_by_model.values())
    summary = {
        "run_dir": str(run_dir),
        "paper_id": config["paper_id"],
        "workflow_arm": config["workflow_arm"],
        "stage1_metrics": stage1_metrics,
        "combined_metrics": combined_metrics,
        "current_authority": {
            "stage1": current_stage1["metrics"],
            "combined": current_combined["metrics"],
        },
        "reference_single_reviewer": {
            "stage1": ref_stage1,
            "combined": ref_combined,
        },
        "delta_vs_current_authority": {
            "stage1_f1": _safe_float(stage1_metrics["metrics"]["f1"]) - _safe_float(current_stage1["metrics"]["f1"]),
            "combined_f1": _safe_float(combined_metrics["metrics"]["f1"]) - _safe_float(current_combined["metrics"]["f1"]),
        },
        "delta_vs_reference_single_reviewer": {
            "stage1_f1": _safe_float(stage1_metrics["metrics"]["f1"]) - _safe_float(ref_stage1["metrics"]["f1"]),
            "combined_f1": _safe_float(combined_metrics["metrics"]["f1"]) - _safe_float(ref_combined["metrics"]["f1"]),
        },
        "usage_by_model": usage_by_model,
        "total_cost": total_cost,
        "disagreement_audit": disagreement_audit,
    }
    summary["decision_note"] = _decision_note(summary)
    return summary


def render_summary_zh(summary: dict[str, Any]) -> str:
    stage1 = summary["stage1_metrics"]["metrics"]
    combined = summary["combined_metrics"]["metrics"]
    current = summary["current_authority"]["combined"]
    baseline = summary["reference_single_reviewer"]["combined"]["metrics"]
    lines = [
        f"# {summary['paper_id']} Criterion Ledger Current-Kernel 摘要",
        "",
        f"- `paper_id`: `{summary['paper_id']}`",
        f"- `workflow_arm`: `{summary['workflow_arm']}`",
        f"- `total_cost`: `${summary['total_cost']:.4f}`",
        "",
        "## Metrics",
        "",
        "| Scope | P | R | F1 | F2 | F3 | TP | FP | TN | FN | Auto coverage | Senior route rate | Senior overturn rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| Stage1 | {stage1['precision']:.4f} | {stage1['recall']:.4f} | {stage1['f1']:.4f} | {stage1['f2']:.4f} | {stage1['f3']:.4f} | {stage1['tp']} | {stage1['fp']} | {stage1['tn']} | {stage1['fn']} | {summary['stage1_metrics']['auto_resolution_coverage']:.4f} | {summary['stage1_metrics']['senior_route_rate']:.4f} | {summary['stage1_metrics']['senior_overturn_rate']:.4f} |",
        f"| Combined | {combined['precision']:.4f} | {combined['recall']:.4f} | {combined['f1']:.4f} | {combined['f2']:.4f} | {combined['f3']:.4f} | {combined['tp']} | {combined['fp']} | {combined['tn']} | {combined['fn']} | {summary['combined_metrics']['auto_resolution_coverage']:.4f} | {summary['combined_metrics']['senior_route_rate']:.4f} | {summary['combined_metrics']['senior_overturn_rate']:.4f} |",
        "",
        "## Comparison",
        "",
        f"- current authority combined F1: `{current['f1']:.4f}`",
        f"- current authority combined FN: `{current['fn']}`",
        f"- reference single-reviewer combined F1: `{baseline['f1']:.4f}`",
        f"- delta vs current authority combined F1: `{summary['delta_vs_current_authority']['combined_f1']:+.4f}`",
        f"- delta vs reference single-reviewer combined F1: `{summary['delta_vs_reference_single_reviewer']['combined_f1']:+.4f}`",
        "",
        "## Cost",
        "",
    ]
    for model, usage in sorted(summary["usage_by_model"].items()):
        lines.append(
            f"- `{model}`: calls={int(usage['calls'])}, input_tokens={int(usage['input_tokens'])}, output_tokens={int(usage['output_tokens'])}, cost=${usage['cost']:.4f}"
        )
    lines.extend(
        [
            "",
            "## Decision Note",
            "",
            summary["decision_note"],
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render summary for an isolated criterion-ledger current-kernel run.")
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()

    summary = build_run_summary_payload(args.run_dir.resolve())
    rendered = render_summary_zh(summary)
    write_json(args.run_dir / "matrix_summary.json", summary)
    (args.run_dir / "matrix_summary_zh.md").write_text(rendered, encoding="utf-8")
    (args.run_dir / "SUMMARY_zh.md").write_text(rendered, encoding="utf-8")
    (args.run_dir / "papers" / summary["paper_id"] / "SUMMARY_zh.md").write_text(rendered, encoding="utf-8")
    print(json.dumps({"matrix_summary": str(args.run_dir / "matrix_summary.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
