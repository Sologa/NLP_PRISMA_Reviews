#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiment_lib import load_best_observed_single_reviewer, read_json, write_json


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
CONFIG_PATH = BUNDLE_DIR / "config" / "experiment_matrix.json"


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_matrix_summary(run_dir: Path) -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    results_manifest = read_json(REPO_ROOT / config["current_results_manifest"])
    best_by_paper = load_best_observed_single_reviewer(REPO_ROOT / config["single_reviewer_summary_csv"])
    papers = config["papers"]
    arm_ids = [arm["id"] for arm in config["arms"]]

    summary: dict[str, Any] = {
        "run_dir": str(run_dir),
        "arms": {},
    }
    for arm_id in arm_ids:
        arm_payload: dict[str, Any] = {"papers": {}}
        for paper_id in papers:
            paper_dir = run_dir / "arms" / arm_id / "papers" / paper_id
            stage1_metrics = read_json(paper_dir / "stage1_metrics.json")
            combined_metrics = read_json(paper_dir / "combined_metrics.json")
            current = results_manifest["papers"][paper_id]["current_metrics"]["combined"]
            best = best_by_paper.get(paper_id, {})
            arm_payload["papers"][paper_id] = {
                "stage1_metrics_path": str((paper_dir / "stage1_metrics.json").relative_to(REPO_ROOT)),
                "combined_metrics_path": str((paper_dir / "combined_metrics.json").relative_to(REPO_ROOT)),
                "stage1_metrics": stage1_metrics,
                "combined_metrics": combined_metrics,
                "delta_vs_current_combined_f1": _safe_float(combined_metrics["metrics"]["f1"]) - _safe_float(current["f1"]),
                "delta_vs_best_observed_single_reviewer_f1": _safe_float(combined_metrics["metrics"]["f1"]) - _safe_float(best.get("combined_f1")),
                "current_authority_combined_f1": _safe_float(current["f1"]),
                "best_observed_single_reviewer_combined_f1": _safe_float(best.get("combined_f1")),
                "best_observed_single_reviewer_run_id": best.get("run_id"),
                "best_observed_single_reviewer_model": best.get("model"),
            }
        summary["arms"][arm_id] = arm_payload
    return summary


def render_matrix_summary_zh(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# gpt-5-nano Async 四篇全矩陣摘要")
    lines.append("")
    for arm_id, arm_payload in summary.get("arms", {}).items():
        lines.append(f"## `{arm_id}`")
        lines.append("")
        lines.append("| Paper | Stage1 F1 | Combined F1 | F2 | F3 | Delta vs current | Delta vs best single | Route rate | Overturn rate |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for paper_id, payload in arm_payload.get("papers", {}).items():
            stage1_metrics = payload["stage1_metrics"]["metrics"]
            combined_metrics = payload["combined_metrics"]["metrics"]
            lines.append(
                f"| `{paper_id}` | {stage1_metrics['f1']:.4f} | {combined_metrics['f1']:.4f} | "
                f"{combined_metrics['f2']:.4f} | {combined_metrics['f3']:.4f} | "
                f"{payload['delta_vs_current_combined_f1']:+.4f} | "
                f"{payload['delta_vs_best_observed_single_reviewer_f1']:+.4f} | "
                f"{payload['combined_metrics']['verification_route_rate']:.4f} | "
                f"{payload['combined_metrics']['verification_overturn_rate']:.4f} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render matrix summary for the isolated async experiment tree.")
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    summary = build_matrix_summary(run_dir)
    write_json(run_dir / "matrix_summary.json", summary)
    (run_dir / "matrix_summary_zh.md").write_text(render_matrix_summary_zh(summary), encoding="utf-8")
    print(json.dumps({"matrix_summary": str(run_dir / "matrix_summary.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
