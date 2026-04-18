#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bcpcs_utils import (
    RESEARCH_ROOT,
    compile_stub_graph,
    lexical_evidence_stub,
    load_json,
    load_jsonl,
    metadata_path,
    relative_to_repo,
    write_json,
    write_jsonl,
    write_text,
)


def _load_or_compile_graph(paper_id: str) -> dict[str, Any]:
    path = RESEARCH_ROOT / "runs/dry_run_loader/stub_graphs" / f"{paper_id}.stage1.eligibility_graph.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return compile_stub_graph(paper_id, "stage1")


def _decision_from_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    critical_inclusion = [row for row in records if row["claim_id"].endswith("IC1") or row["claim_id"].endswith("IC2")]
    supported = sum(1 for row in critical_inclusion if row["evidence_status"] == "support" and row["confidence"] >= 0.5)
    refuted = [row for row in records if row["evidence_status"] == "refute" and row["confidence"] >= 0.75]
    unknown = [row for row in critical_inclusion if row["evidence_status"] == "unknown"]
    if refuted:
        verdict = "exclude"
        route = False
        reason = "validated_refute_evidence"
    elif critical_inclusion and supported == len(critical_inclusion):
        verdict = "include"
        route = False
        reason = "all_critical_inclusion_claims_supported_by_stub"
    else:
        verdict = "route"
        route = True
        reason = "critical_claim_unknown_or_low_confidence"
    return {
        "auto_verdict": verdict,
        "route_to_senior_or_human": route,
        "decision_reason": reason,
        "critical_supported": supported,
        "critical_unknown": len(unknown),
        "critical_total": len(critical_inclusion),
    }


def main() -> int:
    subset_papers = ["2409.13738", "2511.13936"]
    ledger_rows: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for paper_id in subset_papers:
        graph = _load_or_compile_graph(paper_id)
        candidates = load_jsonl(metadata_path(paper_id))[:3]
        claims = graph["claims"][:4]
        for candidate in candidates:
            candidate_rows: list[dict[str, Any]] = []
            key = str(candidate.get("key") or "")
            for claim in claims:
                span = lexical_evidence_stub(claim["claim_text"], candidate, metadata_path(paper_id))
                status = "support" if claim["claim_type"] == "inclusion" and span is not None else "unknown"
                row = {
                    "candidate_key": key,
                    "stage": "stage1",
                    "claim_id": claim["claim_id"],
                    "evidence_status": status,
                    "support_spans": [span] if status == "support" and span is not None else [],
                    "refute_spans": [],
                    "missingness_reason": "none" if status == "support" else "not_observed_stage1",
                    "confidence": 0.55 if status == "support" else 0.0,
                    "verifier_model": "lexical-smoke-stub",
                    "quote": span["quote"] if status == "support" and span is not None else "",
                    "location": span["location"] if status == "support" and span is not None else "",
                    "source_path": relative_to_repo(metadata_path(paper_id)),
                    "span_validated": False,
                }
                ledger_rows.append(row)
                candidate_rows.append(row)
            decision = _decision_from_records(candidate_rows)
            decision.update(
                {
                    "paper_id": paper_id,
                    "candidate_key": key,
                    "stage": "stage1",
                    "mode": "smoke_structural_only",
                }
            )
            decisions.append(decision)

    write_jsonl(RESEARCH_ROOT / "runs/smoke/smoke_ledger.jsonl", ledger_rows)
    write_jsonl(RESEARCH_ROOT / "runs/smoke/smoke_decisions.jsonl", decisions)
    summary = {
        "purpose": "Structural smoke only; no performance claim.",
        "papers": subset_papers,
        "candidate_count": len(decisions),
        "ledger_row_count": len(ledger_rows),
        "routed_count": sum(1 for row in decisions if row["route_to_senior_or_human"]),
        "auto_include_count": sum(1 for row in decisions if row["auto_verdict"] == "include"),
        "auto_exclude_count": sum(1 for row in decisions if row["auto_verdict"] == "exclude"),
    }
    write_json(RESEARCH_ROOT / "runs/smoke/smoke_summary.json", summary)
    smoke_lines = [
        "# Smoke Report",
        "",
        "This smoke run checks that the BCPCS graph and ledger interfaces can be populated from current repo inputs without touching production paths.",
        "",
        "It uses a lexical stub, not an LLM retriever/verifier. The run is deliberately non-claim-bearing.",
        "",
        f"- Papers: {', '.join(subset_papers)}",
        f"- Candidates: {summary['candidate_count']}",
        f"- Ledger rows: {summary['ledger_row_count']}",
        f"- Routed cases: {summary['routed_count']}",
        f"- Auto include cases: {summary['auto_include_count']}",
        f"- Auto exclude cases: {summary['auto_exclude_count']}",
        "",
        "Artifacts:",
        "",
        "- `runs/smoke/smoke_ledger.jsonl`",
        "- `runs/smoke/smoke_decisions.jsonl`",
        "- `runs/smoke/smoke_summary.json`",
        "",
    ]
    write_text(RESEARCH_ROOT / "reports/smoke_report.md", "\n".join(smoke_lines))

    results_lines = [
        "# Results",
        "",
        "Status: scaffold validation complete; full BCPCS benchmark not yet run.",
        "",
        "Current available outputs:",
        "",
        "- Schema validation: `reports/schema_validation.md`",
        "- Baseline recheck: `reports/baseline_recheck.md`",
        "- Structural smoke run: `reports/smoke_report.md`",
        "",
        "No F1 improvement claim is made here. The next valid step is a frozen internal diagnostic with the leakage protocol already written, followed by ablations and external generalization.",
        "",
        "Conference-readiness gate:",
        "",
        "- Internal diagnostic: pending",
        "- Ablations: pending",
        "- Evidence-span validation: pending",
        "- External public benchmark: pending or blocker to be documented",
        "- Cost and repeated-run analysis: pending",
        "",
    ]
    write_text(RESEARCH_ROOT / "reports/results.md", "\n".join(results_lines))
    print(f"smoke wrote {len(ledger_rows)} ledger rows and {len(decisions)} decisions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
