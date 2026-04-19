#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Literal

from failure_slice_common import REPO_ROOT, read_json, write_json


DEEP_RESEARCH_RESULTS_DIR = (
    REPO_ROOT / "docs" / "deep_research" / "llm_native_failure_modes_all4_2026-04-15" / "results"
)
APPENDIX_22_PATH = (
    REPO_ROOT
    / "docs"
    / "deep_research"
    / "llm_native_failure_modes_all4_2026-04-15"
    / "APPENDIX_22_API_SIM_CASES_zh.md"
)
NON_TENSION_LABELS = {"reviewer_semantic_gap", "paper_evidence_incomplete"}
TENSION_LABEL = "criteria_or_gold_tension"


def _source_rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def _iter_result_files(results_dir: Path = DEEP_RESEARCH_RESULTS_DIR) -> list[Path]:
    return sorted(results_dir.glob("*.json"))


def build_failure_slice_inventory(*, results_dir: Path = DEEP_RESEARCH_RESULTS_DIR) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    private_cases: list[dict[str, Any]] = []
    primary_label_counts: Counter[str] = Counter()
    per_paper_counts: Counter[str] = Counter()
    per_paper_primary_counts: Counter[str] = Counter()
    per_paper_secondary_counts: Counter[str] = Counter()

    for path in _iter_result_files(results_dir):
        payload = read_json(path)
        paper_id = str(payload.get("paper_id") or path.stem).strip()
        for item in payload.get("case_inventory", []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            primary_label = str(item.get("primary_label") or "").strip()
            if primary_label == TENSION_LABEL:
                slice_type = "criteria_gold_tension_secondary"
                allowed = False
                per_paper_secondary_counts[paper_id] += 1
            else:
                slice_type = "non_tension_primary"
                allowed = True
                per_paper_primary_counts[paper_id] += 1
            primary_label_counts[primary_label] += 1
            per_paper_counts[paper_id] += 1
            public_row = {
                "paper_id": paper_id,
                "candidate_key": key,
                "slice_type": slice_type,
                "source_artifact": _source_rel(path),
                "allowed_for_unbiased_eval": allowed,
                "debug_exposure": "none",
                "leakage_notes": (
                    "Key selected from deep_research case_inventory only; gold/error taxonomy fields withheld from prompts."
                    if allowed
                    else "Criteria/gold tension case retained for inventory/reporting only; not primary unbiased improvement evidence."
                ),
            }
            cases.append(public_row)
            private_cases.append(
                {
                    **public_row,
                    "title": item.get("title"),
                    "error_type": item.get("error_type"),
                    "primary_label": primary_label,
                    "secondary_labels": item.get("secondary_labels"),
                    "why_primary": item.get("why_primary"),
                    "why_not_other_two": item.get("why_not_other_two"),
                }
            )

    cases.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    private_cases.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    primary_count = sum(1 for row in cases if row["slice_type"] == "non_tension_primary")
    secondary_count = sum(1 for row in cases if row["slice_type"] == "criteria_gold_tension_secondary")
    return {
        "source": {
            "results_dir": _source_rel(results_dir),
            "appendix_22": _source_rel(APPENDIX_22_PATH),
            "source_of_truth": "case_inventory in per-paper JSON files",
        },
        "cases": cases,
        "private_cases": private_cases,
        "summary": {
            "total_count": len(cases),
            "primary_count": primary_count,
            "secondary_count": secondary_count,
            "primary_label_counts": dict(sorted(primary_label_counts.items())),
            "per_paper_counts": dict(sorted(per_paper_counts.items())),
            "per_paper_primary_counts": dict(sorted(per_paper_primary_counts.items())),
            "per_paper_secondary_counts": dict(sorted(per_paper_secondary_counts.items())),
        },
    }


def select_cases(inventory: dict[str, Any], *, scope: Literal["primary22", "full127"]) -> list[dict[str, Any]]:
    rows = list(inventory["cases"])
    if scope == "primary22":
        return [row for row in rows if row["slice_type"] == "non_tension_primary"]
    if scope == "full127":
        return rows
    raise ValueError(f"Unsupported scope: {scope}")


def select_private_cases(inventory: dict[str, Any], *, scope: Literal["primary22", "full127"]) -> list[dict[str, Any]]:
    rows = list(inventory["private_cases"])
    if scope == "primary22":
        return [row for row in rows if row["slice_type"] == "non_tension_primary"]
    if scope == "full127":
        return rows
    raise ValueError(f"Unsupported scope: {scope}")


def freeze_inventory_files(*, run_dir: Path, scope: Literal["primary22", "full127"]) -> dict[str, Any]:
    inventory = build_failure_slice_inventory()
    public_cases = select_cases(inventory, scope=scope)
    private_cases = select_private_cases(inventory, scope=scope)
    public_payload = {
        "scope": scope,
        "source": inventory["source"],
        "cases": public_cases,
        "summary": {
            **inventory["summary"],
            "selected_count": len(public_cases),
            "selected_primary_count": sum(1 for row in public_cases if row["slice_type"] == "non_tension_primary"),
            "selected_secondary_count": sum(
                1 for row in public_cases if row["slice_type"] == "criteria_gold_tension_secondary"
            ),
        },
    }
    private_payload = {
        "scope": scope,
        "source": inventory["source"],
        "cases": private_cases,
        "summary": public_payload["summary"],
        "allowed_use": "final evaluation and taxonomy reporting only; never reviewer prompt construction",
    }
    write_json(run_dir / "failure_slice_keys.json", public_payload)
    write_json(run_dir / "evaluation_inventory_private.json", private_payload)
    return public_payload

