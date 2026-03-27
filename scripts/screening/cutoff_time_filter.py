#!/usr/bin/env python3
"""時間窗 cutoff 的 deterministic helper。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
    preprint_split_submitted_date: bool = False


_YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
_ARXIV_MONTH_ID_RE = re.compile(r"^(?P<yy>\d{2})(?P<mm>\d{2})\.\d+(?:v\d+)?$")
_PEER_REVIEW_SIGNAL_PATTERNS = (
    re.compile(r"\baccepted\b", re.IGNORECASE),
    re.compile(r"\bpublished\b", re.IGNORECASE),
    re.compile(r"\bappears in\b", re.IGNORECASE),
    re.compile(r"\bjournal\b", re.IGNORECASE),
    re.compile(r"\bconference\b", re.IGNORECASE),
    re.compile(r"\bproceedings?\b", re.IGNORECASE),
    re.compile(r"\bproc(?:eedings?)?\.?\b", re.IGNORECASE),
    re.compile(r"\btransactions?\b", re.IGNORECASE),
    re.compile(r"\btrans(?:actions?)?\.?\b", re.IGNORECASE),
)


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
    interval = _parse_candidate_date_interval(value)
    if interval is None:
        return None
    return interval[0]


def _parse_candidate_date_interval(value: Any) -> tuple[date, date] | None:
    text = str(value or "").strip()
    if not text:
        return None

    if text.endswith("Z"):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            return parsed, parsed
        except ValueError:
            pass

    exact = _try_datetime_fromisoformat(text)
    if exact is not None:
        return exact, exact

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            parsed = datetime.strptime(text, fmt).date()
            return parsed, parsed
        except ValueError:
            continue

    if re.fullmatch(r"\d{4}-\d{2}", text):
        year_text, month_text = text.split("-")
        year = int(year_text)
        month = int(month_text)
        try:
            start = date(year, month, 1)
        except ValueError:
            return None
        return start, _month_end(start)

    if re.fullmatch(r"\d{4}", text):
        year = int(text)
        return date(year, 1, 1), date(year, 12, 31)

    return None


def _try_datetime_fromisoformat(text: str) -> date | None:
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _month_end(value: date) -> date:
    next_month = value.replace(day=28) + timedelta(days=4)
    return next_month.replace(day=1) - timedelta(days=1)


def _record_source_metadata(record: dict[str, Any]) -> dict[str, Any]:
    source_metadata = record.get("source_metadata")
    if isinstance(source_metadata, dict):
        return source_metadata
    return {}


def _year_values(*values: Any) -> list[int]:
    years: list[int] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        years.extend(int(match) for match in _YEAR_RE.findall(text))
    return years


def _has_peer_review_signal(text: Any) -> bool:
    comment = str(text or "").strip()
    if not comment:
        return False
    return any(pattern.search(comment) for pattern in _PEER_REVIEW_SIGNAL_PATTERNS)


def _arxiv_submitted_interval_from_source_id(source_id: Any) -> tuple[date, date] | None:
    match = _ARXIV_MONTH_ID_RE.match(str(source_id or "").strip())
    if match is None:
        return None
    year = 2000 + int(match.group("yy"))
    month = int(match.group("mm"))
    start = date(year, month, 1)
    return start, _month_end(start)


def _submitted_interval_for_record(record: dict[str, Any]) -> tuple[tuple[date, date] | None, str | None]:
    source_metadata = _record_source_metadata(record)
    submitted_raw = str(source_metadata.get("published") or record.get("published") or "").strip()
    interval = _parse_candidate_date_interval(submitted_raw)
    if interval is not None:
        return interval, submitted_raw or None
    interval = _arxiv_submitted_interval_from_source_id(record.get("source_id"))
    if interval is not None:
        return interval, str(record.get("source_id") or "").strip() or None
    return None, None


def _infer_arxiv_peer_review_status(record: dict[str, Any]) -> tuple[str, str]:
    source_metadata = _record_source_metadata(record)
    journal_ref = str(source_metadata.get("journal_ref") or record.get("journal_ref") or "").strip()
    doi = str(source_metadata.get("doi") or record.get("doi") or "").strip()
    comment = str(source_metadata.get("comment") or record.get("comment") or "").strip()
    if journal_ref:
        return "peer_reviewed", "journal_ref"
    if doi:
        return "peer_reviewed", "doi"
    if _has_peer_review_signal(comment):
        return "peer_reviewed", "comment_signal"
    return "preprint", "default_preprint"


def _build_interval_decision(
    *,
    policy: TimePolicy,
    interval_start: date | None,
    interval_end: date | None,
    missing_status: str,
    extra: dict[str, Any],
) -> dict[str, Any]:
    if interval_start is None or interval_end is None:
        return {
            "cutoff_policy_enabled": True,
            "cutoff_status": missing_status,
            "cutoff_pass": False,
            **extra,
        }

    if policy.start_date is not None:
        if policy.start_inclusive:
            if interval_end < policy.start_date:
                return {
                    "cutoff_policy_enabled": True,
                    "cutoff_status": "before_start",
                    "cutoff_pass": False,
                    **extra,
                }
        elif interval_end <= policy.start_date:
            return {
                "cutoff_policy_enabled": True,
                "cutoff_status": "before_or_equal_start",
                "cutoff_pass": False,
                **extra,
            }

    if policy.end_date is not None:
        if policy.end_inclusive:
            if interval_start > policy.end_date:
                return {
                    "cutoff_policy_enabled": True,
                    "cutoff_status": "after_end",
                    "cutoff_pass": False,
                    **extra,
                }
        elif interval_start >= policy.end_date:
            return {
                "cutoff_policy_enabled": True,
                "cutoff_status": "after_or_equal_end",
                "cutoff_pass": False,
                **extra,
            }

    return {
        "cutoff_policy_enabled": True,
        "cutoff_status": "passed",
        "cutoff_pass": True,
        **extra,
    }


def _evaluate_record_with_preprint_split(record: dict[str, Any], policy: TimePolicy) -> dict[str, Any]:
    raw_published_date = str(record.get("published_date") or "").strip()
    normalized_published = _parse_candidate_date(raw_published_date)
    source = str(record.get("source") or "").strip().lower()
    source_metadata = _record_source_metadata(record)
    extra = {
        "published_date_raw": raw_published_date or None,
        "published_date_iso": normalized_published.isoformat() if normalized_published is not None else None,
        "cutoff_split_mode": True,
        "cutoff_record_source": source or None,
        "cutoff_interval_start_iso": None,
        "cutoff_interval_end_iso": None,
    }

    if source == "arxiv":
        peer_status, peer_status_basis = _infer_arxiv_peer_review_status(record)
        extra["cutoff_peer_review_status"] = peer_status
        extra["cutoff_peer_review_status_basis"] = peer_status_basis
        if peer_status == "preprint":
            interval, submitted_raw = _submitted_interval_for_record(record)
            interval_start = interval[0] if interval is not None else None
            interval_end = interval[1] if interval is not None else None
            extra.update(
                {
                    "cutoff_date_basis": "submitted_date",
                    "cutoff_date_role": "preprint",
                    "cutoff_raw_value": submitted_raw or None,
                    "cutoff_interval_start_iso": interval_start.isoformat() if interval_start is not None else None,
                    "cutoff_interval_end_iso": interval_end.isoformat() if interval_end is not None else None,
                }
            )
            return _build_interval_decision(
                policy=policy,
                interval_start=interval_start,
                interval_end=interval_end,
                missing_status="missing_submitted_date",
                extra=extra,
            )

        publish_raw = raw_published_date or None
        publish_interval = _parse_candidate_date_interval(raw_published_date)
        publish_years = _year_values(
            source_metadata.get("journal_ref"),
            source_metadata.get("comment"),
            record.get("key"),
        )
        if publish_years:
            publish_year = max(publish_years)
            publish_interval = (date(publish_year, 1, 1), date(publish_year, 12, 31))
            publish_raw = str(publish_year)
        interval_start = publish_interval[0] if publish_interval is not None else None
        interval_end = publish_interval[1] if publish_interval is not None else None
        extra.update(
            {
                "cutoff_date_basis": "published_date",
                "cutoff_date_role": "peer_reviewed",
                "cutoff_raw_value": publish_raw,
                "cutoff_interval_start_iso": interval_start.isoformat() if interval_start is not None else None,
                "cutoff_interval_end_iso": interval_end.isoformat() if interval_end is not None else None,
            }
        )
        publish_decision = _build_interval_decision(
            policy=policy,
            interval_start=interval_start,
            interval_end=interval_end,
            missing_status="missing_published_date",
            extra=extra,
        )
        if publish_decision["cutoff_pass"]:
            return publish_decision

        submitted_interval, submitted_raw = _submitted_interval_for_record(record)
        submitted_start = submitted_interval[0] if submitted_interval is not None else None
        submitted_end = submitted_interval[1] if submitted_interval is not None else None
        submitted_extra = dict(extra)
        submitted_extra.update(
            {
                "cutoff_date_basis": "submitted_date_fallback",
                "cutoff_raw_value": submitted_raw,
                "cutoff_interval_start_iso": submitted_start.isoformat() if submitted_start is not None else None,
                "cutoff_interval_end_iso": submitted_end.isoformat() if submitted_end is not None else None,
            }
        )
        submitted_decision = _build_interval_decision(
            policy=policy,
            interval_start=submitted_start,
            interval_end=submitted_end,
            missing_status="missing_submitted_date",
            extra=submitted_extra,
        )
        if submitted_decision["cutoff_pass"]:
            return submitted_decision
        return publish_decision

    interval = _parse_candidate_date_interval(raw_published_date)
    interval_start = interval[0] if interval is not None else None
    interval_end = interval[1] if interval is not None else None
    extra.update(
        {
            "cutoff_date_basis": "published_date",
            "cutoff_date_role": "published_default",
            "cutoff_raw_value": raw_published_date or None,
            "cutoff_interval_start_iso": interval_start.isoformat() if interval_start is not None else None,
            "cutoff_interval_end_iso": interval_end.isoformat() if interval_end is not None else None,
        }
    )
    return _build_interval_decision(
        policy=policy,
        interval_start=interval_start,
        interval_end=interval_end,
        missing_status="missing_published_date",
        extra=extra,
    )


def evaluate_record(record: dict[str, Any], policy: TimePolicy) -> dict[str, Any]:
    if policy.preprint_split_submitted_date:
        if not policy.enabled:
            return {
                "cutoff_policy_enabled": False,
                "cutoff_status": "disabled",
                "cutoff_pass": True,
                "published_date_raw": str(record.get("published_date") or "").strip() or None,
                "published_date_iso": _parse_candidate_date(record.get("published_date")).isoformat()
                if _parse_candidate_date(record.get("published_date")) is not None
                else None,
                "cutoff_split_mode": True,
            }
        return _evaluate_record_with_preprint_split(record, policy)

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


def _is_cutoff_excluded_verdict(value: Any) -> bool:
    return str(value or "").strip() == "exclude (cutoff_time_window)"


def _coerce_score(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        return None
    if numeric.is_integer():
        return int(numeric)
    return None


def _infer_stage1_verdict_from_row(row: dict[str, Any]) -> str | None:
    junior_nano = _coerce_score(row.get("round-A_JuniorNano_evaluation"))
    junior_mini = _coerce_score(row.get("round-A_JuniorMini_evaluation"))
    senior = _coerce_score(row.get("round-B_SeniorLead_evaluation"))

    if junior_nano is not None and junior_mini is not None:
        if junior_nano >= 4 and junior_mini >= 4:
            return f"include (junior:{junior_nano},{junior_mini})"
        if junior_nano <= 2 and junior_mini <= 2:
            return f"exclude (junior:{junior_nano},{junior_mini})"

    if senior is not None:
        if senior >= 4:
            return f"include (senior:{senior})"
        if senior == 3:
            return "maybe (senior:3)"
        if senior <= 2:
            return f"exclude (senior:{senior})"
    return None


def _cleanup_restored_row(row: dict[str, Any], *, decision: dict[str, Any]) -> dict[str, Any]:
    restored = dict(row)
    restored["cutoff_filter"] = decision
    if str(restored.get("discard_reason") or "").startswith("cutoff_time_window:"):
        restored.pop("discard_reason", None)
    if restored.get("review_state") == "cutoff_filtered":
        restored.pop("review_state", None)
    if restored.get("pre_cutoff_review_state") == "cutoff_filtered":
        restored.pop("pre_cutoff_review_state", None)
    if _is_cutoff_excluded_verdict(restored.get("pre_cutoff_final_verdict")):
        restored.pop("pre_cutoff_final_verdict", None)
    if restored.get("pre_cutoff_review_skipped") is True and not _is_cutoff_excluded_verdict(restored.get("final_verdict")):
        restored.pop("pre_cutoff_review_skipped", None)
    return restored


def restore_cutoff_passed_row(
    row: dict[str, Any],
    *,
    decision: dict[str, Any],
    fallback_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requires_restore = (
        _is_cutoff_excluded_verdict(row.get("final_verdict"))
        or row.get("review_state") == "cutoff_filtered"
        or str(row.get("discard_reason") or "").startswith("cutoff_time_window:")
    )
    if not requires_restore:
        restored = dict(row)
        restored["cutoff_filter"] = decision
        return restored

    if fallback_row is not None:
        restored = dict(fallback_row)
        return _cleanup_restored_row(restored, decision=decision)

    restored = dict(row)
    pre_cutoff_verdict = restored.get("pre_cutoff_final_verdict")
    if isinstance(pre_cutoff_verdict, str) and pre_cutoff_verdict and not _is_cutoff_excluded_verdict(pre_cutoff_verdict):
        restored["final_verdict"] = pre_cutoff_verdict
        pre_cutoff_state = restored.get("pre_cutoff_review_state")
        if pre_cutoff_state not in (None, "", "cutoff_filtered"):
            restored["review_state"] = pre_cutoff_state
        pre_cutoff_skipped = restored.get("pre_cutoff_review_skipped")
        if isinstance(pre_cutoff_skipped, bool):
            restored["review_skipped"] = pre_cutoff_skipped
        elif restored.get("review_skipped") is True:
            restored["review_skipped"] = False
        return _cleanup_restored_row(restored, decision=decision)

    inferred_verdict = _infer_stage1_verdict_from_row(restored)
    if inferred_verdict is not None:
        restored["final_verdict"] = inferred_verdict
        restored["review_skipped"] = False
        return _cleanup_restored_row(restored, decision=decision)

    restored["cutoff_filter"] = decision
    return restored


def apply_cutoff_to_results(
    rows: list[dict[str, Any]],
    *,
    metadata_rows: list[dict[str, Any]],
    payload: dict[str, Any],
    policy: TimePolicy,
    synthesize_missing_failed_rows: bool = False,
    preserve_metadata_order: bool = False,
    fallback_restore_rows_by_key: dict[str, dict[str, Any]] | None = None,
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
            adjusted_by_key[key] = restore_cutoff_passed_row(
                updated,
                decision=decision,
                fallback_row=(fallback_restore_rows_by_key or {}).get(key),
            )
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
