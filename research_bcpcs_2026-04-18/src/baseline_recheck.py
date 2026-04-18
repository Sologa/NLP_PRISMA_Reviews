#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from bcpcs_utils import RESEARCH_ROOT, load_manifest, recompute_f1_from_report, repo_path, write_json, write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> int:
    manifest = load_manifest()
    rows: list[dict[str, Any]] = []
    for paper_id, paper in sorted(manifest.get("papers", {}).items()):
        current_metrics = paper.get("current_metrics", {})
        for stage in ("stage1", "combined"):
            authority = current_metrics.get(stage, {})
            authority_path = repo_path(authority["path"])
            recomputed = recompute_f1_from_report(authority_path)
            stored = recomputed["stored_metrics"]
            recomputed_metrics = recomputed["metrics"]
            row = {
                "paper_id": paper_id,
                "stage": stage,
                "authority_path": authority["path"],
                "manifest_f1": authority.get("f1"),
                "stored_report_f1": stored.get("f1"),
                "recomputed_f1": recomputed_metrics.get("f1"),
                "manifest_precision": authority.get("precision"),
                "recomputed_precision": recomputed_metrics.get("precision"),
                "manifest_recall": authority.get("recall"),
                "recomputed_recall": recomputed_metrics.get("recall"),
                "tp": recomputed_metrics.get("tp"),
                "fp": recomputed_metrics.get("fp"),
                "tn": recomputed_metrics.get("tn"),
                "fn": recomputed_metrics.get("fn"),
                "matched": recomputed.get("matched"),
                "gold_size": recomputed.get("gold_size"),
                "results_size": recomputed.get("results_size"),
            }
            row["f1_matches_manifest"] = abs(float(row["manifest_f1"]) - float(row["recomputed_f1"])) < 1e-12
            rows.append(row)

    write_json(RESEARCH_ROOT / "runs/baseline_recheck/baseline_recheck.json", {"rows": rows})
    lines = [
        "# Baseline Recheck",
        "",
        "This report recomputes the current score-authority metrics from `screening/results/results_manifest.json` without writing to production paths.",
        "",
        "State-drift note: the current manifest authority for `2409.13738` combined F1 is `0.7500`; older mentions of `0.8235` are treated as stale historical context.",
        "",
        "| Paper | Stage | Authority path | Manifest F1 | Recomputed F1 | P | R | TP | FP | TN | FN | Matched | Status |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        status = "ok" if row["f1_matches_manifest"] else "drift"
        lines.append(
            "| {paper_id} | {stage} | `{authority_path}` | {manifest_f1} | {recomputed_f1} | {p} | {r} | {tp} | {fp} | {tn} | {fn} | {matched} | {status} |".format(
                paper_id=row["paper_id"],
                stage=row["stage"],
                authority_path=row["authority_path"],
                manifest_f1=_fmt(row["manifest_f1"]),
                recomputed_f1=_fmt(row["recomputed_f1"]),
                p=_fmt(row["recomputed_precision"]),
                r=_fmt(row["recomputed_recall"]),
                tp=row["tp"],
                fp=row["fp"],
                tn=row["tn"],
                fn=row["fn"],
                matched=row["matched"],
                status=status,
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- This is a reproducibility check of existing authority artifacts, not a BCPCS performance result.",
            "- Missing `gold_only` records are handled the same way as the repo evaluator: metrics are computed on matched keys.",
            "- No production files were modified.",
            "",
        ]
    )
    write_text(RESEARCH_ROOT / "reports/baseline_recheck.md", "\n".join(lines))
    print(f"rechecked {len(rows)} authority metric artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
