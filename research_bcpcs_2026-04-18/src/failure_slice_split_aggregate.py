#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from failure_slice_common import read_json, repo_rel, run_dir, write_json
from failure_slice_eval import compute_binary_metrics


def _aggregate_evidence(items: list[dict[str, Any]]) -> dict[str, Any]:
    stage_outputs = sum(int(item.get("stage_outputs", 0)) for item in items)
    outputs_with_ledger = sum(int(item.get("stage_outputs_with_ledger", 0)) for item in items)
    ledger_rows = sum(int(item.get("ledger_rows", 0)) for item in items)
    span_validated_rows = sum(int(item.get("span_validated_rows", 0)) for item in items)
    span_complete_rows = sum(int(item.get("span_complete_rows", 0)) for item in items)
    return {
        "stage_outputs": stage_outputs,
        "stage_outputs_with_ledger": outputs_with_ledger,
        "ledger_rows": ledger_rows,
        "span_validated_rows": span_validated_rows,
        "span_complete_rows": span_complete_rows,
        "stage_output_ledger_coverage": outputs_with_ledger / stage_outputs if stage_outputs else 0.0,
        "span_validated_rate": span_validated_rows / ledger_rows if ledger_rows else 0.0,
        "span_completeness_rate": span_complete_rows / ledger_rows if ledger_rows else 0.0,
    }


def _merge_cost_summaries(items: list[dict[str, Any]]) -> dict[str, Any]:
    phases: dict[str, Any] = {}
    for item in items:
        manifest = item["manifest"]
        phase_prefix = manifest.get("run_id", "run")
        for phase_name, phase_payload in (item["cost_summary"].get("phases") or {}).items():
            phases[f"{phase_prefix}:{phase_name}"] = phase_payload
    return {
        "cost_source": "batch_usage" if all(item["cost_summary"].get("cost_source") == "batch_usage" for item in items) else "mixed",
        "input_tokens": sum(int(item["cost_summary"].get("input_tokens", 0)) for item in items),
        "output_tokens": sum(int(item["cost_summary"].get("output_tokens", 0)) for item in items),
        "total_cost_usd": sum(float(item["cost_summary"].get("total_cost_usd", 0.0)) for item in items),
        "phases": phases,
    }


def aggregate_split_runs(*, run_ids: list[str], output_run_id: str) -> dict[str, Any]:
    loaded: list[dict[str, Any]] = []
    for run_id in run_ids:
        rd = run_dir(run_id)
        loaded.append(
            {
                "run_id": run_id,
                "run_dir": rd,
                "manifest": read_json(rd / "run_manifest.json"),
                "evaluation": read_json(rd / "evaluation_summary.json"),
                "cost_summary": read_json(rd / "cost" / "cost_summary.json"),
                "validation": read_json(rd / "validation_summary.json"),
            }
        )

    rows: list[dict[str, Any]] = []
    for item in loaded:
        rows.extend(item["evaluation"].get("rows") or [])
    rows.sort(key=lambda row: (str(row.get("paper_id")), str(row.get("candidate_key"))))

    primary_rows = [row for row in rows if row.get("slice_type") == "non_tension_primary"]
    secondary_rows = [row for row in rows if row.get("slice_type") != "non_tension_primary"]
    evidence = _aggregate_evidence([item["evaluation"].get("evidence_validity") or {} for item in loaded])
    decision_counts = dict(Counter(str(row.get("final_stage_decision") or "") for row in rows))
    recovery = {
        "prior_fp_recovered": sum(1 for row in rows if row.get("recovered") and row.get("prior_error_type") == "FP"),
        "prior_fn_recovered": sum(1 for row in rows if row.get("recovered") and row.get("prior_error_type") == "FN"),
        "still_wrong": sum(1 for row in rows if row.get("still_wrong")),
        "newly_unknown_or_routed": sum(1 for row in rows if row.get("outcome") == "unknown_or_routed"),
        "recovery_rate_definite_or_unknown_as_not_recovered": (sum(1 for row in rows if row.get("recovered")) / len(rows)) if rows else 0.0,
    }
    validation = {
        "source_inventory_counts_ok": all(bool(item["validation"].get("source_inventory_counts_ok")) for item in loaded),
        "source_inventory_total": 127,
        "source_inventory_primary": 22,
        "source_inventory_secondary": 105,
        "forbidden_prompt_hit_count": sum(int(item["validation"].get("forbidden_prompt_hit_count", 0)) for item in loaded),
        "schema_failure_count": sum(int(item["validation"].get("schema_failure_count", 0)) for item in loaded),
        "schema_checked_stage_outputs": sum(int(item["validation"].get("schema_checked_stage_outputs", 0)) for item in loaded),
        "output_path_audit_ok": all(bool(item["validation"].get("output_path_audit_ok")) for item in loaded),
        "outside_research_change_count": sum(int(item["validation"].get("outside_research_change_count", 0)) for item in loaded),
        "cost_ledger_ok": all(bool(item["validation"].get("cost_ledger_ok")) for item in loaded),
        "split_runs": [
            {
                "run_id": item["run_id"],
                "run_dir": repo_rel(item["run_dir"]),
                "validation_summary_path": repo_rel(item["run_dir"] / "validation_summary.json"),
            }
            for item in loaded
        ],
    }
    aggregate = {
        "aggregate_run_id": output_run_id,
        "component_run_ids": run_ids,
        "scope": "full127_split_aggregate",
        "row_count": len(rows),
        "primary_count": len(primary_rows),
        "secondary_count": len(secondary_rows),
        "metrics_primary22": compute_binary_metrics(primary_rows),
        "metrics_secondary": compute_binary_metrics(secondary_rows),
        "metrics_all_selected": compute_binary_metrics(rows),
        "recovery": recovery,
        "decision_counts": decision_counts,
        "evidence_validity": evidence,
        "cost_summary": _merge_cost_summaries(loaded),
        "validation_summary": validation,
        "rows": rows,
    }
    return aggregate


def write_aggregate_outputs(*, aggregate: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "aggregate_summary.json", aggregate)
    cost = aggregate["cost_summary"]
    primary = aggregate["metrics_primary22"]
    secondary = aggregate["metrics_secondary"]
    all_selected = aggregate["metrics_all_selected"]
    recovery = aggregate["recovery"]
    evidence = aggregate["evidence_validity"]
    lines = [
        "# GPT-5.4-mini XHigh Failure-Slice Full127 Aggregate Report",
        "",
        "這是 failure-slice diagnostic 的 full127 split aggregate，不是 full benchmark evidence。",
        "",
        f"- aggregate_run_id：`{aggregate['aggregate_run_id']}`",
        f"- component runs：{', '.join(f'`{run_id}`' for run_id in aggregate['component_run_ids'])}",
        f"- rows：{aggregate['row_count']}（primary {aggregate['primary_count']} / secondary {aggregate['secondary_count']}）",
        "",
        "## Metrics",
        "",
        f"- primary precision / recall / F1：{primary['precision']:.4f} / {primary['recall']:.4f} / {primary['f1']:.4f}",
        f"- primary TP / FP / TN / FN：{primary['tp']} / {primary['fp']} / {primary['tn']} / {primary['fn']}",
        f"- secondary precision / recall / F1：{secondary['precision']:.4f} / {secondary['recall']:.4f} / {secondary['f1']:.4f}",
        f"- all-selected precision / recall / F1：{all_selected['precision']:.4f} / {all_selected['recall']:.4f} / {all_selected['f1']:.4f}",
        "",
        "## Recovery",
        "",
        f"- prior FP recovered：{recovery['prior_fp_recovered']}",
        f"- prior FN recovered：{recovery['prior_fn_recovered']}",
        f"- still wrong：{recovery['still_wrong']}",
        f"- newly unknown / routed：{recovery['newly_unknown_or_routed']}",
        "",
        "## Evidence Ledger",
        "",
        f"- stage outputs：{evidence['stage_outputs']}",
        f"- ledger rows：{evidence['ledger_rows']}",
        f"- span completeness：{evidence['span_completeness_rate']:.4f}",
        f"- span validated rate：{evidence['span_validated_rate']:.4f}",
        "",
        "## Cost",
        "",
        f"- input tokens：{cost['input_tokens']}",
        f"- output tokens：{cost['output_tokens']}",
        f"- total cost USD：{cost['total_cost_usd']:.6f}",
        "",
        f"- aggregate_summary：`{repo_rel(output_dir / 'aggregate_summary.json')}`",
    ]
    (output_dir / "REPORT_full127_aggregate_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--run-id", action="append", dest="run_ids", required=True)
    args = parser.parse_args()
    output_dir = run_dir(args.output_run_id)
    aggregate = aggregate_split_runs(run_ids=args.run_ids, output_run_id=args.output_run_id)
    write_aggregate_outputs(aggregate=aggregate, output_dir=output_dir)
    print(repo_rel(output_dir / "aggregate_summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
