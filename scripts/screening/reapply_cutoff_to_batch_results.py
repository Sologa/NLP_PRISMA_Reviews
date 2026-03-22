#!/usr/bin/env python3
"""對既有單審查者 batch 結果重新套用 cutoff_jsons。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import cutoff_time_filter

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _paper_results_path(run_dir: Path, paper_id: str) -> Path:
    return run_dir / "papers" / paper_id / "single_reviewer_batch_results.json"


def _paper_gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _paper_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _results_after_cutoff_path(run_dir: Path, paper_id: str, suffix: str) -> Path:
    return run_dir / "papers" / paper_id / f"single_reviewer_batch_results.{suffix}.json"


def _metrics_after_cutoff_path(run_dir: Path, paper_id: str, suffix: str) -> Path:
    return run_dir / "papers" / paper_id / f"single_reviewer_batch_f1.{suffix}.json"


def _audit_after_cutoff_path(run_dir: Path, paper_id: str, suffix: str) -> Path:
    return run_dir / "papers" / paper_id / f"cutoff_reapply_audit.{suffix}.json"


def _run_manifest_after_cutoff_path(run_dir: Path, suffix: str) -> Path:
    return run_dir / f"run_manifest.{suffix}.json"


def _report_after_cutoff_path(run_dir: Path, suffix: str) -> Path:
    return run_dir / f"REPORT_{suffix}_zh.md"


def _run_f1_eval(*, paper_id: str, results_path: Path, gold_path: Path, save_report: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        paper_id,
        "--results",
        str(results_path),
        "--gold-metadata",
        str(gold_path),
        "--positive-mode",
        "include_or_maybe",
        "--save-report",
        str(save_report),
    ]
    subprocess.run(cmd, check=True, cwd=str(REPO_ROOT))
    return _read_json(save_report)


def _build_report_zh(run_manifest: dict[str, Any], suffix: str) -> str:
    lines: list[str] = []
    lines.append("# 既有 Batch 結果重新套用 cutoff")
    lines.append("")
    lines.append(f"- 原始 run_id：`{run_manifest.get('run_id')}`")
    lines.append(f"- 輸出 suffix：`{suffix}`")
    lines.append("")
    lines.append("| Paper | F1 | Precision | Recall | Results | Metrics |")
    lines.append("| --- | ---: | ---: | ---: | --- | --- |")
    for summary in run_manifest.get("cutoff_reapply_summaries", []):
        lines.append(
            f"| `{summary['paper_id']}` | {float(summary['f1']):.4f} | {float(summary['precision']):.4f} | "
            f"{float(summary['recall']):.4f} | `{summary['results_path']}` | `{summary['metrics_path']}` |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="對既有單審查者 batch 結果重新套用 cutoff_jsons。")
    parser.add_argument("--run-manifest", required=True)
    parser.add_argument("--suffix", default="after_cutoff")
    args = parser.parse_args()

    manifest_path = Path(args.run_manifest).resolve()
    run_manifest = _read_json(manifest_path)
    run_dir = Path(run_manifest["run_dir"]).resolve()
    summaries: list[dict[str, Any]] = []

    for paper_id in run_manifest["papers"]:
        results_path = _paper_results_path(run_dir, paper_id)
        rows = _read_json(results_path)
        metadata_rows = _read_jsonl(_paper_metadata_path(paper_id))
        cutoff_path = cutoff_time_filter.cutoff_json_path(REPO_ROOT, paper_id)
        payload, policy = cutoff_time_filter.load_time_policy(cutoff_path)
        payload = dict(payload)
        payload["_cutoff_json_path"] = str(cutoff_path.relative_to(REPO_ROOT))
        adjusted = cutoff_time_filter.apply_cutoff_to_results(
            rows,
            metadata_rows=metadata_rows,
            payload=payload,
            policy=policy,
        )
        adjusted_results_path = _results_after_cutoff_path(run_dir, paper_id, args.suffix)
        adjusted_metrics_path = _metrics_after_cutoff_path(run_dir, paper_id, args.suffix)
        adjusted_audit_path = _audit_after_cutoff_path(run_dir, paper_id, args.suffix)
        _write_json(adjusted_results_path, adjusted["rows"])
        _write_json(adjusted_audit_path, adjusted["audit_payload"])
        metrics = _run_f1_eval(
            paper_id=paper_id,
            results_path=adjusted_results_path,
            gold_path=_paper_gold_path(paper_id),
            save_report=adjusted_metrics_path,
        )
        summaries.append(
            {
                "paper_id": paper_id,
                "results_path": str(adjusted_results_path),
                "metrics_path": str(adjusted_metrics_path),
                "audit_path": str(adjusted_audit_path),
                "precision": float(metrics["metrics"]["precision"]),
                "recall": float(metrics["metrics"]["recall"]),
                "f1": float(metrics["metrics"]["f1"]),
            }
        )

    updated_manifest = dict(run_manifest)
    updated_manifest["cutoff_reapply_suffix"] = args.suffix
    updated_manifest["cutoff_reapply_summaries"] = summaries
    manifest_out = _run_manifest_after_cutoff_path(run_dir, args.suffix)
    report_out = _report_after_cutoff_path(run_dir, args.suffix)
    _write_json(manifest_out, updated_manifest)
    report_out.write_text(_build_report_zh(updated_manifest, args.suffix), encoding="utf-8")
    print(f"cutoff_reapply_manifest={manifest_out}", flush=True)
    print(f"cutoff_reapply_report={report_out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
