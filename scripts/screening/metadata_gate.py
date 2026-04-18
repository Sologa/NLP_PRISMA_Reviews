from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


ARTIFACT_GATE_PASS_FIELD = "artifact_gate_pass"
ARTIFACT_GATE_REASON_FIELD = "artifact_gate_reason"
FULLTEXT_GATE_PASS_FIELD = "fulltext_gate_pass"
FULLTEXT_GATE_REASON_FIELD = "fulltext_gate_reason"


def _parse_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "t", "yes", "y", "1"}:
            return True
        if normalized in {"false", "f", "no", "n", "0"}:
            return False
    return None


def _reason_text(record: dict[str, Any], field: str, *, fallback: str) -> str:
    value = record.get(field)
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def evaluate_artifact_gate(record: dict[str, Any]) -> dict[str, Any]:
    gate_flag = _parse_optional_bool(record.get(ARTIFACT_GATE_PASS_FIELD))
    if gate_flag is False:
        return {
            "gate_name": "artifact_gate",
            "gate_pass": False,
            "gate_status": "failed",
            "gate_reason": _reason_text(record, ARTIFACT_GATE_REASON_FIELD, fallback="metadata_flag_false"),
        }
    return {
        "gate_name": "artifact_gate",
        "gate_pass": True,
        "gate_status": "passed",
        "gate_reason": None,
    }


def apply_artifact_gate(records: list[dict[str, Any]]) -> dict[str, Any]:
    kept_records: list[dict[str, Any]] = []
    excluded_records: list[dict[str, Any]] = []
    decisions_by_key: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    counter: Counter[str] = Counter()

    for record in records:
        key = str(record.get("key") or "").strip()
        title = str(record.get("title") or record.get("query_title") or "").strip()
        decision = evaluate_artifact_gate(record)
        decisions_by_key[key] = decision
        if decision["gate_pass"]:
            kept_records.append(record)
            counter["passed"] += 1
        else:
            excluded_records.append(record)
            counter["failed"] += 1
        rows.append(
            {
                "key": key,
                "title": title,
                **decision,
            }
        )

    return {
        "kept_records": kept_records,
        "excluded_records": excluded_records,
        "decisions_by_key": decisions_by_key,
        "audit_payload": {
            "candidate_total": len(records),
            "artifact_pass_count": counter["passed"],
            "artifact_excluded_count": counter["failed"],
            "artifact_gate": rows,
        },
    }


def evaluate_fulltext_gate(
    record: dict[str, Any],
    resolution: dict[str, Any] | None,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    gate_flag = _parse_optional_bool(record.get(FULLTEXT_GATE_PASS_FIELD))
    if gate_flag is False:
        return {
            "gate_name": "fulltext_gate",
            "gate_pass": False,
            "gate_status": "failed",
            "gate_reason": _reason_text(record, FULLTEXT_GATE_REASON_FIELD, fallback="metadata_flag_false"),
            "resolved_file_size_bytes": None,
        }

    resolution_status = str((resolution or {}).get("resolution_status") or "")
    if resolution_status not in {"exact", "normalized"}:
        return {
            "gate_name": "fulltext_gate",
            "gate_pass": True,
            "gate_status": "passed",
            "gate_reason": None,
            "resolved_file_size_bytes": None,
        }

    candidate = (resolution or {}).get("resolved_path") or (resolution or {}).get("exact_candidate_path")
    if not candidate:
        return {
            "gate_name": "fulltext_gate",
            "gate_pass": False,
            "gate_status": "failed",
            "gate_reason": "missing_resolved_fulltext",
            "resolved_file_size_bytes": None,
        }

    path = repo_root / str(candidate)
    if not path.exists() or not path.is_file():
        return {
            "gate_name": "fulltext_gate",
            "gate_pass": False,
            "gate_status": "failed",
            "gate_reason": "missing_resolved_fulltext",
            "resolved_file_size_bytes": None,
        }

    size = path.stat().st_size
    if size == 0:
        return {
            "gate_name": "fulltext_gate",
            "gate_pass": False,
            "gate_status": "failed",
            "gate_reason": "zero_byte_md",
            "resolved_file_size_bytes": size,
        }

    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return {
            "gate_name": "fulltext_gate",
            "gate_pass": False,
            "gate_status": "failed",
            "gate_reason": "empty_text",
            "resolved_file_size_bytes": size,
        }

    return {
        "gate_name": "fulltext_gate",
        "gate_pass": True,
        "gate_status": "passed",
        "gate_reason": None,
        "resolved_file_size_bytes": size,
    }
