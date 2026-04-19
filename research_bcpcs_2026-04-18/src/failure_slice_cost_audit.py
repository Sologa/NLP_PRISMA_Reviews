#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from failure_slice_common import read_jsonl, run_dir, utc_now_iso, write_json


def _dedupe_key(row: dict[str, Any]) -> tuple[str, str, str]:
    phase = str(row.get("phase") or "")
    custom_id = str(row.get("custom_id") or "")
    batch_id = str(row.get("batch_id") or "")
    return (phase, custom_id, batch_id)


def audit_cost_ledger(*, run_path: Path, rewrite_summary: bool = False) -> dict[str, Any]:
    ledger_path = run_path / "cost" / "cost_ledger.jsonl"
    if not ledger_path.exists():
        payload = {
            "created_at": utc_now_iso(),
            "run_dir": str(run_path),
            "ledger_exists": False,
            "row_count": 0,
            "deduped_row_count": 0,
            "duplicate_row_count": 0,
            "duplicates": [],
            "deduped_summary": {
                "cost_source": "missing_ledger",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost_usd": 0.0,
                "phases": {},
            },
        }
        write_json(run_path / "cost" / "cost_audit.json", payload)
        return payload

    rows = read_jsonl(ledger_path)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_dedupe_key(row)].append(row)

    duplicates: list[dict[str, Any]] = []
    deduped_rows: list[dict[str, Any]] = []
    for key, group in grouped.items():
        deduped_rows.append(group[0])
        if len(group) > 1:
            duplicates.append(
                {
                    "phase": key[0],
                    "custom_id": key[1],
                    "batch_id": key[2] or None,
                    "repeat_count": len(group),
                    "costs": [row.get("cost_usd") for row in group],
                    "input_tokens": [row.get("input_tokens") for row in group],
                    "output_tokens": [row.get("output_tokens") for row in group],
                }
            )

    phases: dict[str, dict[str, Any]] = {}
    total_input = 0
    total_output = 0
    total_cost = 0.0
    cost_sources: set[str] = set()
    for row in deduped_rows:
        phase = str(row.get("phase") or "unknown")
        phase_bucket = phases.setdefault(
            phase,
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost_usd": 0.0,
                "row_count": 0,
                "cost_sources": set(),
            },
        )
        input_tokens = int(row.get("input_tokens") or 0)
        output_tokens = int(row.get("output_tokens") or 0)
        cost_usd = float(row.get("cost_usd") or 0.0)
        source = str(row.get("cost_source") or "unknown")
        phase_bucket["input_tokens"] += input_tokens
        phase_bucket["output_tokens"] += output_tokens
        phase_bucket["total_cost_usd"] += cost_usd
        phase_bucket["row_count"] += 1
        phase_bucket["cost_sources"].add(source)
        total_input += input_tokens
        total_output += output_tokens
        total_cost += cost_usd
        cost_sources.add(source)

    for payload in phases.values():
        payload["cost_sources"] = sorted(payload["cost_sources"])

    if not cost_sources:
        cost_source = "missing_ledger"
    elif len(cost_sources) == 1:
        cost_source = next(iter(cost_sources))
    else:
        cost_source = "mixed"

    summary = {
        "created_at": utc_now_iso(),
        "cost_source": cost_source,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_cost_usd": total_cost,
        "phases": phases,
    }
    payload = {
        "created_at": utc_now_iso(),
        "run_dir": str(run_path),
        "ledger_exists": True,
        "row_count": len(rows),
        "deduped_row_count": len(deduped_rows),
        "duplicate_row_count": len(rows) - len(deduped_rows),
        "duplicate_key_count": len(duplicates),
        "duplicates": duplicates,
        "deduped_summary": summary,
    }
    write_json(run_path / "cost" / "cost_audit.json", payload)
    if rewrite_summary:
        write_json(run_path / "cost" / "cost_summary.json", summary)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--rewrite-summary", action="store_true")
    args = parser.parse_args()
    payload = audit_cost_ledger(run_path=run_dir(args.run_id), rewrite_summary=args.rewrite_summary)
    print(payload["deduped_summary"]["total_cost_usd"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
