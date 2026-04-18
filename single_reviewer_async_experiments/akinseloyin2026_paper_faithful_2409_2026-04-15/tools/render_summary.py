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


def _strategy_rows(run_dir: Path) -> list[dict[str, Any]]:
    config = read_json(CONFIG_PATH)
    current = read_json(REPO_ROOT / config["current_authority_stage1_path"])["metrics"]
    baseline = read_json(REPO_ROOT / config["single_reviewer_stage1_baseline_path"])["metrics"]
    rows: list[dict[str, Any]] = []
    for family_dir in sorted((run_dir / "strategies").glob("*")):
        if not family_dir.is_dir():
            continue
        family_id = family_dir.name
        ranking = read_json(family_dir / "ranking_metrics.json")
        current_threshold = read_json(family_dir / "threshold_metrics.current_authority_k.json")
        single_threshold = read_json(family_dir / "threshold_metrics.single_reviewer_k.json")
        oracle_threshold = read_json(family_dir / "threshold_metrics.oracle_best_f1.json")
        for strategy_id, metrics in ranking["strategies"].items():
            current_metrics = current_threshold["strategies"][strategy_id]
            single_metrics = single_threshold["strategies"][strategy_id]
            oracle_metrics = oracle_threshold["strategies"][strategy_id]
            rows.append(
                {
                    "family_id": family_id,
                    "strategy_id": strategy_id,
                    "ranking_metrics": metrics,
                    "threshold_metrics": {
                        "current_authority_k": current_metrics,
                        "single_reviewer_k": single_metrics,
                        "oracle_best_f1": oracle_metrics,
                    },
                    "delta_vs_current_authority_f1": _safe_float(current_metrics["f1"]) - _safe_float(current["f1"]),
                    "delta_vs_single_reviewer_f1": _safe_float(single_metrics["f1"]) - _safe_float(baseline["f1"]),
                }
            )
    return sorted(rows, key=lambda row: (row["family_id"], row["strategy_id"]))


def _decision_note(summary: dict[str, Any]) -> str:
    strategies = summary["strategies"]
    if not strategies:
        return "沒有 strategy 結果，不能判斷。"
    current_fn = int(summary["current_authority_stage1"]["fn"])
    safe_rows = [row for row in strategies if int(row["threshold_metrics"]["current_authority_k"]["fn"]) <= current_fn]
    if not safe_rows:
        return "沒有任何 strategy 在 current-authority threshold 下守住 FN，暫時不值得擴到 stage2。"
    best_safe = max(safe_rows, key=lambda row: _safe_float(row["threshold_metrics"]["current_authority_k"]["f1"]))
    if _safe_float(best_safe["delta_vs_single_reviewer_f1"]) > 0:
        return (
            f"目前最值得往後推的是 `{best_safe['strategy_id']}`。"
            "它在守住 current-authority FN 的前提下，也比 single-reviewer stage1 baseline 更好。"
        )
    return (
        f"目前最穩的是 `{best_safe['strategy_id']}`，但它還沒有明確贏過 single-reviewer stage1 baseline。"
        " 先不要擴到 stage2，除非你要追的是排序品質而不是 stage1 F1。"
    )


def build_summary_payload(*, run_dir: Path) -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    current = read_json(REPO_ROOT / config["current_authority_stage1_path"])["metrics"]
    baseline = read_json(REPO_ROOT / config["single_reviewer_stage1_baseline_path"])["metrics"]

    usage_by_model: dict[str, dict[str, float]] = defaultdict(
        lambda: {"input_tokens": 0.0, "output_tokens": 0.0, "cost": 0.0, "calls": 0.0}
    )
    for row in load_jsonl(run_dir / "response_log.jsonl"):
        usage = row.get("usage") or {}
        model = str(usage.get("model") or "unknown")
        usage_by_model[model]["input_tokens"] += _safe_float(usage.get("input_tokens"))
        usage_by_model[model]["output_tokens"] += _safe_float(usage.get("output_tokens"))
        usage_by_model[model]["cost"] += _safe_float(usage.get("cost"))
        usage_by_model[model]["calls"] += 1

    summary = {
        "run_dir": str(run_dir),
        "paper_id": config["paper_id"],
        "current_authority_stage1": current,
        "single_reviewer_stage1_baseline": baseline,
        "current_authority_k": int(current["tp"]) + int(current["fp"]),
        "single_reviewer_k": int(baseline["tp"]) + int(baseline["fp"]),
        "strategies": _strategy_rows(run_dir),
        "usage_by_model": usage_by_model,
        "total_cost": sum(item["cost"] for item in usage_by_model.values()),
    }
    summary["decision_note"] = _decision_note(summary)
    return summary


def render_comparison_table_zh(summary: dict[str, Any]) -> str:
    lines = [
        "# 2409 Paper-Faithful A 比較表",
        "",
        f"- `current authority stage1`: P={summary['current_authority_stage1']['precision']:.4f}, R={summary['current_authority_stage1']['recall']:.4f}, F1={summary['current_authority_stage1']['f1']:.4f}, FN={summary['current_authority_stage1']['fn']}",
        f"- `single reviewer stage1 baseline`: P={summary['single_reviewer_stage1_baseline']['precision']:.4f}, R={summary['single_reviewer_stage1_baseline']['recall']:.4f}, F1={summary['single_reviewer_stage1_baseline']['f1']:.4f}, FN={summary['single_reviewer_stage1_baseline']['fn']}",
        "",
        "| Family | Strategy | MAP | WSS@95 | L_Rel | F1@current_k | FN@current_k | Delta vs current | F1@single_k | Delta vs single | Oracle F1 | Oracle k |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["strategies"]:
        ranking = row["ranking_metrics"]
        current = row["threshold_metrics"]["current_authority_k"]
        single = row["threshold_metrics"]["single_reviewer_k"]
        oracle = row["threshold_metrics"]["oracle_best_f1"]
        lines.append(
            f"| `{row['family_id']}` | `{row['strategy_id']}` | {ranking['map']:.4f} | {ranking['wss95']:.4f} | "
            f"{ranking['last_relevant_rank']} | {current['f1']:.4f} | {current['fn']} | {row['delta_vs_current_authority_f1']:+.4f} | "
            f"{single['f1']:.4f} | {row['delta_vs_single_reviewer_f1']:+.4f} | {oracle['f1']:.4f} | {oracle['k']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def render_summary_zh(summary: dict[str, Any]) -> str:
    lines = [
        "# 2409 Paper-Faithful A 摘要",
        "",
        f"- `paper_id`: `{summary['paper_id']}`",
        f"- `current_authority_k`: `{summary['current_authority_k']}`",
        f"- `single_reviewer_k`: `{summary['single_reviewer_k']}`",
        f"- `total_cost`: `${summary['total_cost']:.4f}`",
        "",
        "## Key Findings",
        "",
    ]
    if summary["strategies"]:
        best_current = max(summary["strategies"], key=lambda row: _safe_float(row["threshold_metrics"]["current_authority_k"]["f1"]))
        best_single = max(summary["strategies"], key=lambda row: _safe_float(row["threshold_metrics"]["single_reviewer_k"]["f1"]))
        best_map = max(summary["strategies"], key=lambda row: _safe_float(row["ranking_metrics"]["map"]))
        lines.extend(
            [
                f"- current-authority threshold 下 F1 最高的是 `{best_current['strategy_id']}`，F1=`{best_current['threshold_metrics']['current_authority_k']['f1']:.4f}`，FN=`{best_current['threshold_metrics']['current_authority_k']['fn']}`。",
                f"- single-reviewer threshold 下 F1 最高的是 `{best_single['strategy_id']}`，F1=`{best_single['threshold_metrics']['single_reviewer_k']['f1']:.4f}`。",
                f"- ranking MAP 最高的是 `{best_map['strategy_id']}`，MAP=`{best_map['ranking_metrics']['map']:.4f}`，WSS@95=`{best_map['ranking_metrics']['wss95']:.4f}`。",
                "",
            ]
        )
    lines.extend(["## Decision Note", "", summary["decision_note"], "", "## Cost", ""])
    for model, usage in sorted(summary["usage_by_model"].items()):
        lines.append(
            f"- `{model}`: calls={int(usage['calls'])}, input_tokens={int(usage['input_tokens'])}, output_tokens={int(usage['output_tokens'])}, cost=${usage['cost']:.4f}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render summary for the isolated paper-faithful 2409 run.")
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    summary = build_summary_payload(run_dir=run_dir)
    write_json(run_dir / "summary_payload.json", summary)
    (run_dir / "comparison_table_zh.md").write_text(render_comparison_table_zh(summary), encoding="utf-8")
    (run_dir / "SUMMARY_zh.md").write_text(render_summary_zh(summary), encoding="utf-8")
    print(json.dumps({"summary_payload": str(run_dir / "summary_payload.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
