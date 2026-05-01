#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BCPCS_ROOT = REPO_ROOT / "research_bcpcs_2026-04-18"
REPORTS_ROOT = BCPCS_ROOT / "reports"
BCPCS_RUNS_ROOT = BCPCS_ROOT / "runs"
BASELINE_ROOT_2409_2511 = REPO_ROOT / "screening" / "results" / "single_reviewer_official_batch_2stage_direct_review_2409_2511_2026-04-06" / "runs"
BASELINE_ROOT_2307_2601 = REPO_ROOT / "screening" / "results" / "single_reviewer_official_batch_2stage_direct_review_2307_2601_2026-04-17" / "runs"
PAPER_IDS = ["2307.05527", "2409.13738", "2511.13936", "2601.19926"]
INPUT_RATE = 0.75 * 0.5 / 1_000_000
OUTPUT_RATE = 4.50 * 0.5 / 1_000_000


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def usage_tokens(usage: dict[str, Any]) -> tuple[int, int]:
    input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    return input_tokens, output_tokens


def verdict_to_prediction(value: Any) -> int | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    label = text.split(" ", 1)[0].split("(", 1)[0]
    if label == "include":
        return 1
    if label == "maybe":
        return 1
    if label == "exclude":
        return 0
    return None


def metrics(rows: list[dict[str, Any]], *, prediction_key: str) -> dict[str, Any]:
    tp = fp = tn = fn = skipped = 0
    for row in rows:
        pred = verdict_to_prediction(row.get(prediction_key))
        if pred is None:
            skipped += 1
            pred = 0
        gold = bool(row["gold_label"])
        if pred == 1 and gold:
            tp += 1
        elif pred == 1 and not gold:
            fp += 1
        elif pred == 0 and gold:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "evaluated_count": tp + fp + tn + fn,
        "skipped_unknown_or_runtime_count": skipped,
    }


def load_gold() -> dict[tuple[str, str], bool]:
    gold: dict[tuple[str, str], bool] = {}
    for paper_id in PAPER_IDS:
        path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
        for row in read_jsonl(path):
            key = str(row.get("key") or "").strip()
            if key:
                gold[(paper_id, key)] = bool(row.get("is_evidence_base"))
    return gold


def baseline_run_root(run_id: str, *, paper_id: str) -> Path:
    root = BASELINE_ROOT_2409_2511 if paper_id in {"2409.13738", "2511.13936"} else BASELINE_ROOT_2307_2601
    return root / run_id


def baseline_rows(run_ids: dict[str, str], gold: dict[tuple[str, str], bool]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, float]]:
    rows_by_paper: dict[str, list[dict[str, Any]]] = {}
    costs_by_paper: dict[str, float] = defaultdict(float)
    for paper_id in PAPER_IDS:
        run_root = baseline_run_root(run_ids[paper_id], paper_id=paper_id)
        results = read_json(run_root / "papers" / paper_id / "single_reviewer_batch_results.json")
        rows: list[dict[str, Any]] = []
        for row in results:
            key = str(row.get("key") or "").strip()
            rows.append(
                {
                    "paper_id": paper_id,
                    "candidate_key": key,
                    "gold_label": bool(gold[(paper_id, key)]),
                    "final_verdict": row.get("final_verdict"),
                }
            )
        rows_by_paper[paper_id] = rows

    bundle_run_ids = sorted(set(run_ids.values()))
    for run_id in bundle_run_ids:
        sample_paper = next(paper for paper, value in run_ids.items() if value == run_id)
        run_root = baseline_run_root(run_id, paper_id=sample_paper)
        output_path = run_root / "batch_jobs" / "stage2_review" / "gpt-5.4-mini" / "output.jsonl"
        for row in read_jsonl(output_path):
            custom_id = str(row.get("custom_id") or "")
            parts = custom_id.split("__", 2)
            if len(parts) != 3:
                continue
            paper_id = parts[1]
            usage = (((row.get("response") or {}).get("body") or {}).get("usage") or {})
            input_tokens, output_tokens = usage_tokens(usage)
            costs_by_paper[paper_id] += input_tokens * INPUT_RATE + output_tokens * OUTPUT_RATE
    return rows_by_paper, costs_by_paper


def bcpcs_rows(run_id: str, gold: dict[tuple[str, str], bool]) -> dict[str, list[dict[str, Any]]]:
    summary = read_json(BCPCS_RUNS_ROOT / run_id / "evaluation_summary_full_corpus_split.json")
    child_run_ids = summary["child_run_ids"]
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for child_run_id in child_run_ids:
        assembled = read_json(BCPCS_RUNS_ROOT / child_run_id / "assembled_results.json")
        for row in assembled:
            paper_id = row["paper_id"]
            key = row["candidate_key"]
            rows_by_paper[paper_id].append(
                {
                    "paper_id": paper_id,
                    "candidate_key": key,
                    "gold_label": bool(gold[(paper_id, key)]),
                    "final_stage_decision": row.get("final_stage_decision"),
                }
            )
    for paper_id in PAPER_IDS:
        rows_by_paper[paper_id].sort(key=lambda row: row["candidate_key"])
    return rows_by_paper


def load_bcpcs_costs(run_id: str) -> tuple[dict[str, float], float]:
    summary = read_json(BCPCS_RUNS_ROOT / run_id / "evaluation_summary_full_corpus_split.json")
    costs: dict[str, float] = {}
    for paper_id, payload in summary["per_paper"].items():
        costs[paper_id] = float(payload["cost_usd"])
    return costs, float(summary["total_cost_usd"])


def load_bcpcs_validity(run_id: str) -> dict[str, Any]:
    summary = read_json(BCPCS_RUNS_ROOT / run_id / "evaluation_summary_full_corpus_split.json")
    overall = {
        "reviewed_rows": 0,
        "parsed_successes": 0,
        "parsed_failures": 0,
        "missing_rows": 0,
        "length_empty_rows": 0,
    }
    per_paper: dict[str, dict[str, int]] = {}
    for child_run_id in summary["child_run_ids"]:
        child_manifest = read_json(BCPCS_RUNS_ROOT / child_run_id / "run_manifest.json")
        paper_id = next(iter(child_manifest["paper_ids"]))
        parsed_path = BCPCS_RUNS_ROOT / child_run_id / "batch_jobs" / "stage2_recall_repair_batch" / "gpt-5.4-mini" / "parsed_results.json"
        output_path = BCPCS_RUNS_ROOT / child_run_id / "batch_jobs" / "stage2_recall_repair_batch" / "gpt-5.4-mini" / "output.jsonl"
        parsed = read_json(parsed_path)
        output_rows = read_jsonl(output_path)
        counts = {
            "reviewed_rows": len(output_rows),
            "parsed_successes": len(parsed.get("successes", [])),
            "parsed_failures": len(parsed.get("failures", [])),
            "missing_rows": len(parsed.get("missing", [])),
            "length_empty_rows": 0,
        }
        for row in output_rows:
            body = ((row.get("response") or {}).get("body") or {})
            choice = ((body.get("choices") or [{}])[0])
            message = choice.get("message") or {}
            if choice.get("finish_reason") == "length" and not str(message.get("content") or "").strip():
                counts["length_empty_rows"] += 1
        per_paper[paper_id] = counts
        for key, value in counts.items():
            overall[key] += value
    overall["quality_comparison_valid"] = not (
        overall["length_empty_rows"] > 0 or overall["parsed_failures"] > overall["parsed_successes"]
    )
    return {"overall": overall, "per_paper": per_paper}


def slice_rows(rows_by_paper: dict[str, list[dict[str, Any]]], keys: set[tuple[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for paper_id in PAPER_IDS:
        for row in rows_by_paper.get(paper_id, []):
            pair = (paper_id, row["candidate_key"])
            if pair in keys:
                out.append(row)
    return out


def overall_rows(rows_by_paper: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for paper_id in PAPER_IDS:
        out.extend(rows_by_paper.get(paper_id, []))
    return out


def dedicated_127_rows(summary_path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = read_json(summary_path)
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload["rows"]:
        paper_id = row["paper_id"]
        rows_by_paper[paper_id].append(
            {
                "paper_id": paper_id,
                "candidate_key": row["candidate_key"],
                "gold_label": bool(row["gold_label"]),
                "final_stage_decision": row.get("final_stage_decision"),
            }
        )
    for paper_id in PAPER_IDS:
        rows_by_paper[paper_id].sort(key=lambda row: row["candidate_key"])
    return rows_by_paper


def load_127_keys(path: Path) -> tuple[set[tuple[str, str]], dict[str, Any]]:
    payload = read_json(path)
    keys = {(row["paper_id"], row["candidate_key"]) for row in payload["cases"]}
    return keys, payload["summary"]


def format_float(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def write_report(
    *,
    output_path: Path,
    summary_path: Path,
    baseline_rows_by_paper: dict[str, list[dict[str, Any]]],
    baseline_costs: dict[str, float],
    bcpcs_rows_by_paper: dict[str, list[dict[str, Any]]],
    bcpcs_costs: dict[str, float],
    bcpcs_total_cost: float,
    bcpcs_validity: dict[str, Any],
    baseline_total_cost: float,
    baseline_run_ids: dict[str, str],
    subset_127_keys: set[tuple[str, str]],
    subset_127_summary: dict[str, Any],
    dedicated_full127_path: Path,
) -> None:
    baseline_overall = metrics(overall_rows(baseline_rows_by_paper), prediction_key="final_verdict")
    bcpcs_overall = metrics(overall_rows(bcpcs_rows_by_paper), prediction_key="final_stage_decision")
    per_paper_rows = []
    for paper_id in PAPER_IDS:
        baseline_paper = metrics(baseline_rows_by_paper[paper_id], prediction_key="final_verdict")
        bcpcs_paper = metrics(bcpcs_rows_by_paper[paper_id], prediction_key="final_stage_decision")
        per_paper_rows.append(
            {
                "paper_id": paper_id,
                "baseline": baseline_paper,
                "bcpcs": bcpcs_paper,
                "baseline_cost_usd": baseline_costs.get(paper_id, 0.0),
                "bcpcs_cost_usd": bcpcs_costs.get(paper_id, 0.0),
                "baseline_run_id": baseline_run_ids[paper_id],
            }
        )

    baseline_127 = metrics(slice_rows(baseline_rows_by_paper, subset_127_keys), prediction_key="final_verdict")
    bcpcs_127 = metrics(slice_rows(bcpcs_rows_by_paper, subset_127_keys), prediction_key="final_stage_decision")
    dedicated_payload = read_json(dedicated_full127_path)
    dedicated_127 = dedicated_payload["all127"]["auto_decidable_f1"]
    dedicated_127_rows_by_paper = dedicated_127_rows(dedicated_full127_path)
    per_paper_127_rows = []
    for paper_id in PAPER_IDS:
        baseline_paper_127 = metrics(slice_rows({paper_id: baseline_rows_by_paper[paper_id]}, subset_127_keys), prediction_key="final_verdict")
        bcpcs_paper_127 = metrics(slice_rows({paper_id: bcpcs_rows_by_paper[paper_id]}, subset_127_keys), prediction_key="final_stage_decision")
        dedicated_paper_127 = metrics(dedicated_127_rows_by_paper[paper_id], prediction_key="final_stage_decision")
        per_paper_127_rows.append(
            {
                "paper_id": paper_id,
                "baseline": baseline_paper_127,
                "bcpcs_full_corpus_slice": bcpcs_paper_127,
                "bcpcs_dedicated_full127": dedicated_paper_127,
            }
        )
    summary_payload = {
        "baseline_overall": baseline_overall,
        "bcpcs_overall": bcpcs_overall,
        "per_paper": per_paper_rows,
        "baseline_total_cost_usd": baseline_total_cost,
        "bcpcs_total_cost_usd": bcpcs_total_cost,
        "bcpcs_validity": bcpcs_validity,
        "baseline_127": baseline_127,
        "bcpcs_127": bcpcs_127,
        "dedicated_bcpcs_full127_reference": dedicated_127,
        "per_paper_127": per_paper_127_rows,
        "subset_127_summary": subset_127_summary,
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# BCPCS XHigh vs `gpt-5.4-mini` XHigh Single-Stage Baseline",
        "",
        "## Scope",
        "",
        "- baseline: cutoff-pass rows direct to current Stage 2 prompt, `gpt-5.4-mini`, `xhigh`, Batch API",
        "- BCPCS: global-check / claim-packets full-corpus split-batch rerun, `gpt-5.4-mini`, `xhigh`, Batch API",
        f"- original 127 slice source: `{subset_127_summary.get('total_count')}` rows from current full127 inventory",
        "",
        "## Validity",
        "",
        f"- BCPCS quality-comparison valid: `{bcpcs_validity['overall']['quality_comparison_valid']}`",
        f"- BCPCS reviewed rows: `{bcpcs_validity['overall']['reviewed_rows']}`",
        f"- BCPCS parsed successes / failures / missing: `{bcpcs_validity['overall']['parsed_successes']}` / `{bcpcs_validity['overall']['parsed_failures']}` / `{bcpcs_validity['overall']['missing_rows']}`",
        f"- BCPCS `finish_reason=length` + empty content rows: `{bcpcs_validity['overall']['length_empty_rows']}`",
        "- Interpretation: if most BCPCS rows exhausted completion budget on reasoning and returned empty content, the reported F1 is an execution-failure artifact, not a clean model-quality comparison.",
        "",
        "## Overall Full Corpus",
        "",
        "| system | F1 | precision | recall | TP/FP/TN/FN | total cost |",
        "| --- | ---: | ---: | ---: | --- | ---: |",
        f"| baseline single-stage xhigh | {baseline_overall['f1']:.4f} | {baseline_overall['precision']:.4f} | {baseline_overall['recall']:.4f} | {baseline_overall['tp']}/{baseline_overall['fp']}/{baseline_overall['tn']}/{baseline_overall['fn']} | ${baseline_total_cost:.6f} |",
        f"| BCPCS xhigh | {bcpcs_overall['f1']:.4f} | {bcpcs_overall['precision']:.4f} | {bcpcs_overall['recall']:.4f} | {bcpcs_overall['tp']}/{bcpcs_overall['fp']}/{bcpcs_overall['tn']}/{bcpcs_overall['fn']} | ${bcpcs_total_cost:.6f} |",
        "",
        "## Per Paper",
        "",
        "| paper | baseline F1 | BCPCS F1 | delta | baseline P/R | BCPCS P/R | baseline TP/FP/TN/FN | BCPCS TP/FP/TN/FN | baseline cost | BCPCS cost | baseline run |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in per_paper_rows:
        baseline = row["baseline"]
        bcpcs = row["bcpcs"]
        lines.append(
            f"| `{row['paper_id']}` | {baseline['f1']:.4f} | {bcpcs['f1']:.4f} | {bcpcs['f1'] - baseline['f1']:+.4f} | "
            f"{baseline['precision']:.4f} / {baseline['recall']:.4f} | {bcpcs['precision']:.4f} / {bcpcs['recall']:.4f} | "
            f"{baseline['tp']}/{baseline['fp']}/{baseline['tn']}/{baseline['fn']} | {bcpcs['tp']}/{bcpcs['fp']}/{bcpcs['tn']}/{bcpcs['fn']} | "
            f"${row['baseline_cost_usd']:.6f} | ${row['bcpcs_cost_usd']:.6f} | `{row['baseline_run_id']}` |"
        )

    lines.extend(
        [
            "",
            "## Original 127 Slice",
            "",
            f"- total: `{subset_127_summary['total_count']}`",
            f"- primary / secondary: `{subset_127_summary['primary_count']}` / `{subset_127_summary['secondary_count']}`",
            f"- per paper: `{json.dumps(subset_127_summary['per_paper_counts'], ensure_ascii=False, sort_keys=True)}`",
            "",
            "| system | F1 | precision | recall | TP/FP/TN/FN |",
            "| --- | ---: | ---: | ---: | --- |",
            f"| baseline single-stage xhigh on original 127 | {baseline_127['f1']:.4f} | {baseline_127['precision']:.4f} | {baseline_127['recall']:.4f} | {baseline_127['tp']}/{baseline_127['fp']}/{baseline_127['tn']}/{baseline_127['fn']} |",
            f"| BCPCS xhigh full-corpus slice on original 127 | {bcpcs_127['f1']:.4f} | {bcpcs_127['precision']:.4f} | {bcpcs_127['recall']:.4f} | {bcpcs_127['tp']}/{bcpcs_127['fp']}/{bcpcs_127['tn']}/{bcpcs_127['fn']} |",
            f"| BCPCS dedicated full127 reference run | {dedicated_127['f1']:.4f} | {dedicated_127['precision']:.4f} | {dedicated_127['recall']:.4f} | {dedicated_127['tp']}/{dedicated_127['fp']}/{dedicated_127['tn']}/{dedicated_127['fn']} |",
            "",
            "### Original 127 Per Paper",
            "",
            "| paper | baseline single-stage xhigh F1 | BCPCS xhigh all4-slice F1 | BCPCS dedicated full127 F1 | baseline TP/FP/TN/FN | BCPCS all4-slice TP/FP/TN/FN | BCPCS full127 TP/FP/TN/FN |",
            "| --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in per_paper_127_rows:
        baseline = row["baseline"]
        bcpcs_slice = row["bcpcs_full_corpus_slice"]
        dedicated = row["bcpcs_dedicated_full127"]
        lines.append(
            f"| `{row['paper_id']}` | {baseline['f1']:.4f} | {bcpcs_slice['f1']:.4f} | {dedicated['f1']:.4f} | "
            f"{baseline['tp']}/{baseline['fp']}/{baseline['tn']}/{baseline['fn']} | "
            f"{bcpcs_slice['tp']}/{bcpcs_slice['fp']}/{bcpcs_slice['tn']}/{bcpcs_slice['fn']} | "
            f"{dedicated['tp']}/{dedicated['fp']}/{dedicated['tn']}/{dedicated['fn']} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `BCPCS xhigh full-corpus slice on original 127` is the original 127 inventory intersected with the new all4 full-corpus BCPCS xhigh outputs.",
            "- `BCPCS dedicated full127 reference run` stays as the direct guardrail reference for the current full127 architecture line, so the two BCPCS rows answer different questions.",
            "- The baseline row on the original 127 answers how many of those historical error cases are still missed by the new single-stage xhigh baseline.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bcpcs-run-id", required=True)
    parser.add_argument("--baseline-run-2409-2511", required=True)
    parser.add_argument("--baseline-run-2307-2601", required=True)
    parser.add_argument(
        "--inventory-127-path",
        type=Path,
        default=BCPCS_RUNS_ROOT / "bcpcs_recall_v4g_full127_gpt54mini_globalcheck_claimpackets_compilerrelaxcov_2026-04-23_v1" / "failure_slice_keys.json",
    )
    parser.add_argument(
        "--dedicated-full127-summary",
        type=Path,
        default=BCPCS_RUNS_ROOT / "bcpcs_recall_v4g_full127_gpt54mini_globalcheck_claimpackets_compilerrelaxcov_2026-04-23_v1" / "evaluation_summary_v2.json",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=REPORTS_ROOT / "bcpcs_xhigh_vs_gpt54mini_xhigh_single_stage_2026-04-23.md",
    )
    parser.add_argument(
        "--output-summary",
        type=Path,
        default=BCPCS_RUNS_ROOT / "bcpcs_xhigh_vs_gpt54mini_xhigh_single_stage_2026-04-23.summary.json",
    )
    args = parser.parse_args()

    gold = load_gold()
    baseline_run_ids = {
        "2307.05527": args.baseline_run_2307_2601,
        "2409.13738": args.baseline_run_2409_2511,
        "2511.13936": args.baseline_run_2409_2511,
        "2601.19926": args.baseline_run_2307_2601,
    }
    baseline_rows_by_paper, baseline_costs = baseline_rows(baseline_run_ids, gold)
    bcpcs_rows_by_paper = bcpcs_rows(args.bcpcs_run_id, gold)
    bcpcs_costs, bcpcs_total_cost = load_bcpcs_costs(args.bcpcs_run_id)
    bcpcs_validity = load_bcpcs_validity(args.bcpcs_run_id)
    baseline_total_cost = sum(baseline_costs.values())
    subset_127_keys, subset_127_summary = load_127_keys(args.inventory_127_path)
    write_report(
        output_path=args.output_report,
        summary_path=args.output_summary,
        baseline_rows_by_paper=baseline_rows_by_paper,
        baseline_costs=baseline_costs,
        bcpcs_rows_by_paper=bcpcs_rows_by_paper,
        bcpcs_costs=bcpcs_costs,
        bcpcs_total_cost=bcpcs_total_cost,
        bcpcs_validity=bcpcs_validity,
        baseline_total_cost=baseline_total_cost,
        baseline_run_ids=baseline_run_ids,
        subset_127_keys=subset_127_keys,
        subset_127_summary=subset_127_summary,
        dedicated_full127_path=args.dedicated_full127_summary,
    )


if __name__ == "__main__":
    main()
