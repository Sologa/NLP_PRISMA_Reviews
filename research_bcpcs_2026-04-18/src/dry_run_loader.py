#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from bcpcs_utils import (
    REPO_ROOT,
    RESEARCH_ROOT,
    annotated_metadata_path,
    compile_stub_graph,
    cutoff_path,
    criteria_path,
    file_sha256,
    lexical_evidence_stub,
    load_json,
    load_jsonl,
    load_manifest,
    metadata_path,
    relative_to_repo,
    write_json,
    write_jsonl,
)


def _criterion_count(criteria: dict[str, Any]) -> tuple[int, int]:
    inclusion = criteria.get("inclusion_criteria", {}).get("required", [])
    exclusion = criteria.get("exclusion_criteria", [])
    return len(inclusion), len(exclusion)


def main() -> int:
    manifest = load_manifest()
    papers = sorted(manifest.get("papers", {}))
    runtime_prompt_path = REPO_ROOT / "scripts/screening/runtime_prompts/runtime_prompts.json"
    summaries: list[dict[str, Any]] = []
    dry_ledger_rows: list[dict[str, Any]] = []

    for paper_id in papers:
        metadata = load_jsonl(metadata_path(paper_id))
        annotated = load_jsonl(annotated_metadata_path(paper_id))
        paper_summary: dict[str, Any] = {
            "paper_id": paper_id,
            "metadata_path": relative_to_repo(metadata_path(paper_id)),
            "metadata_count": len(metadata),
            "annotated_metadata_path": relative_to_repo(annotated_metadata_path(paper_id)),
            "annotated_count": len(annotated),
            "cutoff_path": relative_to_repo(cutoff_path(paper_id)),
            "cutoff_exists": cutoff_path(paper_id).exists(),
            "stages": {},
        }
        for stage in ("stage1", "stage2"):
            path = criteria_path(paper_id, stage)
            criteria = load_json(path)
            inclusion_count, exclusion_count = _criterion_count(criteria)
            graph = compile_stub_graph(paper_id, stage)
            graph_path = RESEARCH_ROOT / "runs/dry_run_loader/stub_graphs" / f"{paper_id}.{stage}.eligibility_graph.json"
            write_json(graph_path, graph)
            paper_summary["stages"][stage] = {
                "criteria_path": relative_to_repo(path),
                "criteria_sha256": file_sha256(path),
                "inclusion_count": inclusion_count,
                "exclusion_count": exclusion_count,
                "compiled_claim_count": len(graph["claims"]),
                "graph_output_path": str(graph_path.relative_to(RESEARCH_ROOT)),
            }

            if stage == "stage1":
                for candidate in metadata[:2]:
                    key = str(candidate.get("key") or "")
                    for claim in graph["claims"][:3]:
                        span = lexical_evidence_stub(claim["claim_text"], candidate, metadata_path(paper_id))
                        status = "support" if claim["claim_type"] == "inclusion" and span is not None else "unknown"
                        dry_ledger_rows.append(
                            {
                                "candidate_key": key,
                                "stage": "stage1",
                                "claim_id": claim["claim_id"],
                                "evidence_status": status,
                                "support_spans": [span] if status == "support" and span is not None else [],
                                "refute_spans": [],
                                "missingness_reason": "none" if status == "support" else "not_observed_stage1",
                                "confidence": 0.55 if status == "support" else 0.0,
                                "verifier_model": "lexical-dry-run-stub",
                                "quote": span["quote"] if status == "support" and span is not None else "",
                                "location": span["location"] if status == "support" and span is not None else "",
                                "source_path": relative_to_repo(metadata_path(paper_id)),
                                "span_validated": False,
                            }
                        )
        summaries.append(paper_summary)

    output = {
        "purpose": "Dry run only: read current criteria/metadata and compile structural BCPCS graph artifacts.",
        "runtime_prompt_path": relative_to_repo(runtime_prompt_path),
        "runtime_prompt_sha256": file_sha256(runtime_prompt_path),
        "manifest_path": "screening/results/results_manifest.json",
        "manifest_sha256": file_sha256(REPO_ROOT / "screening/results/results_manifest.json"),
        "papers": summaries,
    }
    write_json(RESEARCH_ROOT / "runs/dry_run_loader/criteria_summary.json", output)
    write_jsonl(RESEARCH_ROOT / "runs/dry_run_loader/sample_stage1_ledger.jsonl", dry_ledger_rows)
    print(f"dry-run loaded {len(papers)} papers and wrote {len(dry_ledger_rows)} ledger rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
