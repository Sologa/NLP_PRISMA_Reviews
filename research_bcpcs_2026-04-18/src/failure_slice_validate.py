#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from failure_slice_common import REPO_ROOT, RESEARCH_ROOT, read_json, read_jsonl, repo_rel, write_json
from failure_slice_inventory import build_failure_slice_inventory
from failure_slice_models import StageReviewOutput


FORBIDDEN_PROMPT_TERMS = [
    "gold_label",
    "screening_gold",
    "is_evidence_base",
    "previous prediction",
    "best-run verdict",
    "best run verdict",
    "correctness flag",
    "error_type",
    "primary_label",
    "secondary_labels",
    "why_primary",
    "why_not_other_two",
    "forensic conclusion",
    "one-line fix",
    "api-sim provisional",
    "selected run verdict",
    "final diagnosis",
]


def find_forbidden_prompt_terms(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in FORBIDDEN_PROMPT_TERMS if term.lower() in lowered]


def scan_input_jsonl(path: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    rows = read_jsonl(path) if path.exists() else []
    for row in rows:
        body = row.get("body", {})
        text = json.dumps(body, ensure_ascii=False)
        terms = find_forbidden_prompt_terms(text)
        if terms:
            hits.append({"custom_id": row.get("custom_id"), "terms": terms})
    return {"path": repo_rel(path), "row_count": len(rows), "hit_count": len(hits), "hits": hits}


def validate_source_inventory_counts() -> dict[str, Any]:
    inventory = build_failure_slice_inventory()
    summary = inventory["summary"]
    ok = (
        summary["total_count"] == 127
        and summary["primary_count"] == 22
        and summary["secondary_count"] == 105
    )
    return {"ok": ok, **summary}


def validate_stage_outputs(run_dir: Path) -> dict[str, Any]:
    checked = 0
    failures: list[str] = []
    for path in sorted((run_dir / "papers").glob("*/*_review.json")):
        payload = read_json(path)
        if not isinstance(payload, list):
            failures.append(f"{repo_rel(path)}: expected list")
            continue
        for row in payload:
            checked += 1
            try:
                output = row.get("review_output", row)
                StageReviewOutput.model_validate(output)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{repo_rel(path)}: {type(exc).__name__}: {exc}")
    return {"checked_stage_outputs": checked, "schema_failure_count": len(failures), "schema_failures": failures[:20]}


def validate_output_path_audit() -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    bad: list[str] = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path and not path.startswith("research_bcpcs_2026-04-18/"):
            bad.append(path)
    return {"git_status_returncode": proc.returncode, "outside_research_changes": bad, "ok": proc.returncode == 0 and not bad}


def validate_cost_ledger(run_dir: Path) -> dict[str, Any]:
    ledger_path = run_dir / "cost" / "cost_ledger.jsonl"
    if not ledger_path.exists():
        return {"ok": True, "ledger_exists": False, "row_count": 0}
    rows = read_jsonl(ledger_path)
    missing = [row for row in rows if "cost_usd" not in row or "custom_id" not in row]
    return {"ok": not missing, "ledger_exists": True, "row_count": len(rows), "missing_required_count": len(missing)}


def validate_run_artifacts(run_dir: Path) -> dict[str, Any]:
    inventory = validate_source_inventory_counts()
    prompt_scans = []
    for input_path in sorted((run_dir / "batch_jobs").glob("*/*/input.jsonl")):
        prompt_scans.append(scan_input_jsonl(input_path))
    prompt_hit_count = sum(item["hit_count"] for item in prompt_scans)
    schema = validate_stage_outputs(run_dir)
    path_audit = validate_output_path_audit()
    cost = validate_cost_ledger(run_dir)
    validation = {
        "source_inventory_counts_ok": inventory["ok"],
        "source_inventory_total": inventory["total_count"],
        "source_inventory_primary": inventory["primary_count"],
        "source_inventory_secondary": inventory["secondary_count"],
        "forbidden_prompt_hit_count": prompt_hit_count,
        "schema_failure_count": schema["schema_failure_count"],
        "schema_checked_stage_outputs": schema["checked_stage_outputs"],
        "output_path_audit_ok": path_audit["ok"],
        "outside_research_change_count": len(path_audit["outside_research_changes"]),
        "cost_ledger_ok": cost["ok"],
    }
    write_json(
        run_dir / "validation_summary.json",
        {
            **validation,
            "prompt_scans": prompt_scans,
            "schema": schema,
            "path_audit": path_audit,
            "cost": cost,
        },
    )
    return validation


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = validate_run_artifacts(args.run_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all(
        [
            payload["source_inventory_counts_ok"],
            payload["forbidden_prompt_hit_count"] == 0,
            payload["schema_failure_count"] == 0,
            payload["output_path_audit_ok"],
            payload["cost_ledger_ok"],
        ]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
