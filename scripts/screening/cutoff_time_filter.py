#!/usr/bin/env python3
"""時間窗 cutoff 的 deterministic helper。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TimePolicy:
    enabled: bool
    date_field: str
    start_date: date | None
    start_inclusive: bool
    end_date: date | None
    end_inclusive: bool
    timezone: str


def cutoff_json_path(repo_root: Path, paper_id: str) -> Path:
    return repo_root / "cutoff_jsons" / f"{paper_id}.json"


def load_cutoff_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"cutoff json 不是 object: {path}")
    return payload


def load_time_policy(path: Path) -> tuple[dict[str, Any], TimePolicy]:
    payload = load_cutoff_payload(path)
    raw_policy = payload.get("time_policy")
    if not isinstance(raw_policy, dict):
        raise ValueError(f"cutoff json 缺少 time_policy: {path}")
    policy = TimePolicy(
        enabled=bool(raw_policy.get("enabled", False)),
        date_field=str(raw_policy.get("date_field") or "published"),
        start_date=_parse_bound_date(raw_policy.get("start_date")),
        start_inclusive=bool(raw_policy.get("start_inclusive", True)),
        end_date=_parse_bound_date(raw_policy.get("end_date")),
        end_inclusive=bool(raw_policy.get("end_inclusive", False)),
        timezone=str(raw_policy.get("timezone") or "UTC"),
    )
    return payload, policy


def _parse_bound_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or text.lower() == "null":
        return None
    parsed = _parse_candidate_date(text)
    if parsed is None:
        raise ValueError(f"無法解析 cutoff bound 日期: {text}")
    return parsed


def _parse_candidate_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    if text.endswith("Z"):
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            pass

    for parser in (
        _try_datetime_fromisoformat,
        _try_date_patterns,
    ):
        parsed = parser(text)
        if parsed is not None:
            return parsed
    return None


def _try_datetime_fromisoformat(text: str) -> date | None:
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _try_date_patterns(text: str) -> date | None:
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def evaluate_record(record: dict[str, Any], policy: TimePolicy) -> dict[str, Any]:
    raw_published_date = str(record.get("published_date") or "").strip()
    normalized = _parse_candidate_date(raw_published_date)
    normalized_iso = normalized.isoformat() if normalized is not None else None

    if not policy.enabled:
        return {
            "cutoff_policy_enabled": False,
            "cutoff_status": "disabled",
            "cutoff_pass": True,
            "published_date_raw": raw_published_date or None,
            "published_date_iso": normalized_iso,
        }

    if not raw_published_date:
        return {
            "cutoff_policy_enabled": True,
            "cutoff_status": "missing_published_date",
            "cutoff_pass": False,
            "published_date_raw": None,
            "published_date_iso": None,
        }

    if normalized is None:
        return {
            "cutoff_policy_enabled": True,
            "cutoff_status": "unparseable_published_date",
            "cutoff_pass": False,
            "published_date_raw": raw_published_date,
            "published_date_iso": None,
        }

    if policy.start_date is not None:
        if policy.start_inclusive:
            if normalized < policy.start_date:
                return {
                    "cutoff_policy_enabled": True,
                    "cutoff_status": "before_start",
                    "cutoff_pass": False,
                    "published_date_raw": raw_published_date,
                    "published_date_iso": normalized_iso,
                }
        elif normalized <= policy.start_date:
            return {
                "cutoff_policy_enabled": True,
                "cutoff_status": "before_or_equal_start",
                "cutoff_pass": False,
                "published_date_raw": raw_published_date,
                "published_date_iso": normalized_iso,
            }

    if policy.end_date is not None:
        if policy.end_inclusive:
            if normalized > policy.end_date:
                return {
                    "cutoff_policy_enabled": True,
                    "cutoff_status": "after_end",
                    "cutoff_pass": False,
                    "published_date_raw": raw_published_date,
                    "published_date_iso": normalized_iso,
                }
        elif normalized >= policy.end_date:
            return {
                "cutoff_policy_enabled": True,
                "cutoff_status": "after_or_equal_end",
                "cutoff_pass": False,
                "published_date_raw": raw_published_date,
                "published_date_iso": normalized_iso,
            }

    return {
        "cutoff_policy_enabled": True,
        "cutoff_status": "passed",
        "cutoff_pass": True,
        "published_date_raw": raw_published_date,
        "published_date_iso": normalized_iso,
    }


def apply_cutoff(records: list[dict[str, Any]], *, payload: dict[str, Any], policy: TimePolicy) -> dict[str, Any]:
    kept_records: list[dict[str, Any]] = []
    excluded_records: list[dict[str, Any]] = []
    decisions_by_key: dict[str, dict[str, Any]] = {}
    audit_rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for record in records:
        key = str(record.get("key") or "").strip()
        decision = evaluate_record(record, policy)
        decisions_by_key[key] = decision
        status = str(decision["cutoff_status"])
        counts[status] = counts.get(status, 0) + 1
        row = {
            "key": key,
            "title": str(record.get("title") or record.get("query_title") or "").strip(),
            **decision,
        }
        audit_rows.append(row)
        if decision["cutoff_pass"]:
            kept_records.append(record)
        else:
            excluded_records.append(record)

    audit_payload = {
        "paper_id": payload.get("paper_id"),
        "cutoff_json_path": str(payload.get("_cutoff_json_path") or ""),
        "time_policy": payload.get("time_policy"),
        "evidence": payload.get("evidence"),
        "normalization_notes": payload.get("normalization_notes"),
        "candidate_total_before_cutoff": len(records),
        "candidate_total_after_cutoff": len(kept_records),
        "cutoff_excluded_count": len(excluded_records),
        "status_counts": counts,
        "rows": audit_rows,
    }
    return {
        "kept_records": kept_records,
        "excluded_records": excluded_records,
        "decisions_by_key": decisions_by_key,
        "audit_payload": audit_payload,
    }


def build_cutoff_excluded_row(
    record: dict[str, Any],
    *,
    decision: dict[str, Any],
    existing_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = str(decision["cutoff_status"])
    if existing_row is not None:
        updated = dict(existing_row)
        updated["pre_cutoff_final_verdict"] = updated.get("final_verdict")
        updated["pre_cutoff_review_state"] = updated.get("review_state")
        updated["pre_cutoff_review_skipped"] = updated.get("review_skipped")
    else:
        updated = {
            "title": str(record.get("title") or record.get("query_title") or "").strip(),
            "abstract": str(record.get("abstract") or record.get("summary") or "").strip(),
            "key": str(record.get("key") or "").strip(),
            "review_skipped": True,
        }

    updated["cutoff_filter"] = decision
    updated["final_verdict"] = "exclude (cutoff_time_window)"
    updated["discard_reason"] = f"cutoff_time_window:{status}"
    updated["review_state"] = "cutoff_filtered"
    updated["review_skipped"] = True
    return updated


def apply_cutoff_to_results(
    rows: list[dict[str, Any]],
    *,
    metadata_rows: list[dict[str, Any]],
    payload: dict[str, Any],
    policy: TimePolicy,
    synthesize_missing_failed_rows: bool = False,
    preserve_metadata_order: bool = False,
) -> dict[str, Any]:
    metadata_by_key = {
        str(row.get("key") or "").strip(): row
        for row in metadata_rows
        if str(row.get("key") or "").strip()
    }
    adjusted_by_key: dict[str, dict[str, Any]] = {}
    untouched_extra_rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    filtered_count = 0
    synthesized_count = 0
    seen_keys: set[str] = set()

    for row in rows:
        updated = dict(row)
        key = str(updated.get("key") or "").strip()
        if not key:
            untouched_extra_rows.append(updated)
            continue
        seen_keys.add(key)
        record = metadata_by_key.get(key, {"key": key, "published_date": None})
        decision = evaluate_record(record, policy)
        status = str(decision["cutoff_status"])
        counts[status] = counts.get(status, 0) + 1
        if decision["cutoff_pass"]:
            updated["cutoff_filter"] = decision
            adjusted_by_key[key] = updated
            continue
        filtered_count += 1
        adjusted_by_key[key] = build_cutoff_excluded_row(
            record,
            decision=decision,
            existing_row=updated,
        )

    if synthesize_missing_failed_rows:
        for key, record in metadata_by_key.items():
            if key in seen_keys:
                continue
            decision = evaluate_record(record, policy)
            status = str(decision["cutoff_status"])
            counts[status] = counts.get(status, 0) + 1
            if decision["cutoff_pass"]:
                continue
            filtered_count += 1
            synthesized_count += 1
            adjusted_by_key[key] = build_cutoff_excluded_row(record, decision=decision)

    if preserve_metadata_order:
        adjusted_rows = []
        appended_keys: set[str] = set()
        for record in metadata_rows:
            key = str(record.get("key") or "").strip()
            if not key:
                continue
            row = adjusted_by_key.get(key)
            if row is None:
                continue
            adjusted_rows.append(row)
            appended_keys.add(key)
        for row in rows:
            key = str(row.get("key") or "").strip()
            if not key or key in appended_keys:
                continue
            adjusted = adjusted_by_key.get(key)
            adjusted_rows.append(adjusted if adjusted is not None else dict(row))
        adjusted_rows.extend(untouched_extra_rows)
    else:
        adjusted_rows = list(adjusted_by_key.values()) + untouched_extra_rows

    audit_payload = {
        "paper_id": payload.get("paper_id"),
        "cutoff_json_path": str(payload.get("_cutoff_json_path") or ""),
        "time_policy": payload.get("time_policy"),
        "evidence": payload.get("evidence"),
        "normalization_notes": payload.get("normalization_notes"),
        "rows_total": len(rows),
        "filtered_count": filtered_count,
        "synthesized_count": synthesized_count,
        "status_counts": counts,
    }
    return {
        "rows": adjusted_rows,
        "audit_payload": audit_payload,
    }
