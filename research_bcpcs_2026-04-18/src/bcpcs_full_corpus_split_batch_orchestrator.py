#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import bcpcs_full_corpus_batch_runner as full
from failure_slice_common import REPORTS_ROOT, ensure_dir, read_json, repo_rel, run_dir, utc_now_iso, write_json
from failure_slice_eval import decision_to_prediction, evidence_validity, load_gold_labels


TODAY = time.strftime("%Y-%m-%d")
PAPER_IDS = ["2307.05527", "2409.13738", "2511.13936", "2601.19926"]
RUN_ID = f"bcpcs_full_corpus_split_batch_gpt54mini_recallv3_all4_{TODAY}_v1"


@contextmanager
def scoped_papers(paper_ids: list[str]):
    original = list(full.PAPER_IDS)
    full.PAPER_IDS = list(paper_ids)
    try:
        yield
    finally:
        full.PAPER_IDS = original


def _paper_run_id(paper_id: str) -> str:
    return f"bcpcs_full_corpus_batch_gpt54mini_recallv3_{paper_id}_{TODAY}_v1"


def _aggregate_binary(rows: list[dict[str, Any]], *, unknown_as_negative: bool) -> dict[str, Any]:
    return full._binary_metrics(rows, unknown_as_negative=unknown_as_negative)


def _aggregate_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return full._coverage(rows)


def _write_top_manifest(*, run_id: str, payload: dict[str, Any]) -> None:
    rd = ensure_dir(run_dir(run_id))
    write_json(rd / "run_manifest.json", payload)


def _load_eval_rows(*, child_run_ids: list[str]) -> list[dict[str, Any]]:
    gold = load_gold_labels(PAPER_IDS)
    rows: list[dict[str, Any]] = []
    for child_run_id in child_run_ids:
        assembled = read_json(run_dir(child_run_id) / "assembled_results.json")
        for row in assembled:
            rows.append(
                {
                    "paper_id": row["paper_id"],
                    "candidate_key": row["candidate_key"],
                    "gold_label": bool(gold[(row["paper_id"], row["candidate_key"])]),
                    "prediction": decision_to_prediction(str(row.get("final_stage_decision") or "")),
                    "final_stage_decision": row.get("final_stage_decision"),
                    "review_state": row.get("review_state"),
                    "stage1_output": row.get("stage1_output"),
                    "stage2_output": row.get("stage2_output"),
                }
            )
    rows.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    return rows


def _write_aggregate_report(*, run_id: str, summary: dict[str, Any]) -> Path:
    report_path = REPORTS_ROOT / f"{run_id}.REPORT_zh.md"
    lines = [
        "# BCPCS Full-Corpus Split-Batch Report",
        "",
        "這是目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上，以較小 Batch 單位完成的 all4 run。",
        "不是 current single-reviewer two-stage direct-review baseline。",
        "",
        "## Overall",
        "",
        f"- run_id: `{run_id}`",
        f"- model: `{summary['model']}`",
        f"- child runs: `{', '.join(summary['child_run_ids'])}`",
        f"- repo-compatible F1: `{summary['overall']['repo_compatible_f1']['f1']:.4f}`",
        f"- auto-decidable F1: `{summary['overall']['auto_decidable_f1']['f1']:.4f}`",
        f"- coverage: `{summary['overall']['coverage']['definite_decision_rate']:.2%}`",
        f"- decisions: `{json.dumps(summary['overall']['coverage']['decision_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- review states: `{json.dumps(summary['overall']['coverage']['review_state_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- total estimated/actual cost: `${summary['total_cost_usd']:.6f}`",
        "",
        "## Per Paper",
        "",
        "| paper_id | child_run_id | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage | cost |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for paper_id in PAPER_IDS:
        item = summary["per_paper"][paper_id]
        repo_f1 = item["repo_compatible_f1"]
        auto_f1 = item["auto_decidable_f1"]
        lines.append(
            f"| `{paper_id}` | `{item['child_run_id']}` | {repo_f1['f1']:.4f} | {auto_f1['f1']:.4f} | {repo_f1['precision']:.4f} | {repo_f1['recall']:.4f} | {repo_f1['tp']}/{repo_f1['fp']}/{repo_f1['tn']}/{repo_f1['fn']} | {item['coverage']['definite_decision_rate']:.2%} | ${item['cost_usd']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- 單一 707-request Batch 在服務端長時間 `in_progress` 且 `completed=0`，因此改成 split-batch 完成。",
            "- 這仍然是 BCPCS 新架構的 full-corpus run。",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_split_batches(*, run_id: str, cost_cap_usd: float, poll_interval_sec: float, max_wait_minutes: float) -> dict[str, Any]:
    top_manifest_path = run_dir(run_id) / "run_manifest.json"
    if top_manifest_path.exists():
        top_manifest = read_json(top_manifest_path)
    else:
        top_manifest = {
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "status": "initializing",
            "model": full.PROFILE.model,
            "workflow": "bcpcs_v3_recall_repair_split_batch_full_corpus",
            "paper_ids": PAPER_IDS,
            "notes": [
                "This top-level run uses four smaller Batch jobs after a single all4 Batch stayed in_progress with zero completed requests.",
            ],
            "child_runs": {},
        }
        _write_top_manifest(run_id=run_id, payload=top_manifest)

    cumulative_estimate = 0.0
    child_run_ids: list[str] = []
    for paper_id in PAPER_IDS:
        existing = top_manifest["child_runs"].get(paper_id)
        if existing:
            child_run_id = existing["child_run_id"]
            submit_result = existing["submit_result"]
        else:
            child_run_id = _paper_run_id(paper_id)
            with scoped_papers([paper_id]):
                full.init_run(run_id=child_run_id, profile=full.PROFILE, cost_cap_usd=cost_cap_usd)
                submit_result = full.submit_only(
                    run_id=child_run_id,
                    profile=full.PROFILE,
                    cost_cap_usd=cost_cap_usd,
                    poll_interval_sec=poll_interval_sec,
                )
            top_manifest["child_runs"][paper_id] = {
                "child_run_id": child_run_id,
                "submit_result": submit_result,
            }
            top_manifest["updated_at"] = utc_now_iso()
            top_manifest["status"] = "submitted"
            _write_top_manifest(run_id=run_id, payload=top_manifest)
        child_run_ids.append(child_run_id)
        estimate = float(submit_result["estimate"]["estimated_cost_usd"])
        cumulative_estimate += estimate
        if cumulative_estimate > cost_cap_usd:
            raise RuntimeError(f"Projected cumulative split-batch cost exceeds cap: {cumulative_estimate:.6f} > {cost_cap_usd:.2f}")

    total_cost = 0.0
    per_paper: dict[str, Any] = {}
    for paper_id in PAPER_IDS:
        child = top_manifest["child_runs"][paper_id]
        child_run_id = child["child_run_id"]
        if child.get("status") == "completed":
            child_summary = read_json(run_dir(child_run_id) / "evaluation_summary_full_corpus.json")
            child_cost = read_json(run_dir(child_run_id) / "cost" / "cost_summary.json")
            total_cost += float(child_cost.get("total_cost_usd") or 0.0)
            per_paper[paper_id] = {
                "child_run_id": child_run_id,
                "repo_compatible_f1": child_summary["overall"]["repo_compatible_f1"],
                "auto_decidable_f1": child_summary["overall"]["auto_decidable_f1"],
                "coverage": child_summary["overall"]["coverage"],
                "evidence_validity": child_summary["overall"]["evidence_validity"],
                "cost_usd": float(child_cost.get("total_cost_usd") or 0.0),
            }
            continue
        batch_id = child["submit_result"]["batch"]["id"]
        with scoped_papers([paper_id]):
            collect_result = full.collect_existing_batch(
                run_id=child_run_id,
                profile=full.PROFILE,
                poll_interval_sec=poll_interval_sec,
                max_wait_minutes=max_wait_minutes,
                batch_id=batch_id,
            )
            if collect_result["status"] != "completed":
                raise RuntimeError(f"Child batch did not complete for {paper_id}: {collect_result}")
            full.assemble_full_corpus(run_id=child_run_id)
            summary = full.evaluate_full_corpus(run_id=child_run_id)
            validation = full.validate_run(run_id=child_run_id)
            report_path = full.write_report(run_id=child_run_id, summary=summary, validation=validation)
            manifest = read_json(run_dir(child_run_id) / "run_manifest.json")
            manifest["status"] = "completed"
            manifest["evaluation_summary_full_corpus_path"] = repo_rel(run_dir(child_run_id) / "evaluation_summary_full_corpus.json")
            manifest["validation_summary_full_corpus_path"] = repo_rel(run_dir(child_run_id) / "validation_summary_full_corpus.json")
            manifest["report_path"] = repo_rel(report_path)
            manifest["updated_at"] = utc_now_iso()
            write_json(run_dir(child_run_id) / "run_manifest.json", manifest)
        child_summary = read_json(run_dir(child_run_id) / "evaluation_summary_full_corpus.json")
        child_cost = read_json(run_dir(child_run_id) / "cost" / "cost_summary.json")
        total_cost += float(child_cost.get("total_cost_usd") or 0.0)
        per_paper[paper_id] = {
            "child_run_id": child_run_id,
            "repo_compatible_f1": child_summary["overall"]["repo_compatible_f1"],
            "auto_decidable_f1": child_summary["overall"]["auto_decidable_f1"],
            "coverage": child_summary["overall"]["coverage"],
            "evidence_validity": child_summary["overall"]["evidence_validity"],
            "cost_usd": float(child_cost.get("total_cost_usd") or 0.0),
        }
        top_manifest["child_runs"][paper_id]["status"] = "completed"
        top_manifest["updated_at"] = utc_now_iso()
        _write_top_manifest(run_id=run_id, payload=top_manifest)

    eval_rows = _load_eval_rows(child_run_ids=child_run_ids)
    summary = {
        "run_id": run_id,
        "model": full.PROFILE.model,
        "workflow": "bcpcs_v3_recall_repair_split_batch_full_corpus",
        "paper_ids": PAPER_IDS,
        "child_run_ids": child_run_ids,
        "row_count": len(eval_rows),
        "overall": {
            "repo_compatible_f1": _aggregate_binary(eval_rows, unknown_as_negative=True),
            "auto_decidable_f1": _aggregate_binary(eval_rows, unknown_as_negative=False),
            "coverage": _aggregate_coverage(eval_rows),
            "evidence_validity": evidence_validity(eval_rows),
        },
        "per_paper": per_paper,
        "total_cost_usd": total_cost,
    }
    report_path = _write_aggregate_report(run_id=run_id, summary=summary)
    top_manifest["status"] = "completed"
    top_manifest["updated_at"] = utc_now_iso()
    top_manifest["summary_path"] = repo_rel(run_dir(run_id) / "evaluation_summary_full_corpus_split.json")
    top_manifest["report_path"] = repo_rel(report_path)
    write_json(run_dir(run_id) / "evaluation_summary_full_corpus_split.json", summary)
    _write_top_manifest(run_id=run_id, payload=top_manifest)
    return {
        "status": "completed",
        "run_id": run_id,
        "summary_path": repo_rel(run_dir(run_id) / "evaluation_summary_full_corpus_split.json"),
        "report_path": repo_rel(report_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BCPCS full-corpus all4 via smaller Batch jobs and aggregate the results.")
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--cost-cap-usd", type=float, default=10.0)
    parser.add_argument("--poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--max-wait-minutes", type=float, default=240.0)
    args = parser.parse_args()
    payload = run_split_batches(
        run_id=args.run_id,
        cost_cap_usd=args.cost_cap_usd,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
