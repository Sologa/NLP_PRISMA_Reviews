#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_METADATA = REPO_ROOT / "screening" / "data" / "source" / "cads" / "arxiv_metadata.json"
DEFAULT_SOURCE_CRITERIA = REPO_ROOT / "screening" / "data" / "source" / "cads" / "criteria.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "screening" / "data" / "cads_smoke5"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _first_record_keys(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    return sorted(records[0].keys())


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _parse_date_bound(raw: Any) -> date | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if value.isdigit() and len(value) == 4:
        return date(int(value), 1, 1)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return None


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_metadata_record(row: dict[str, Any]) -> dict[str, Any]:
    title = str(
        _first_non_empty(
            row.get("title"),
            row.get("query_title"),
            row.get("normalized_title"),
        )
        or ""
    ).strip()
    abstract = str(_first_non_empty(row.get("abstract"), row.get("summary")) or "").strip()

    published_raw = _first_non_empty(
        row.get("published"),
        row.get("published_date"),
        row.get("publication_date"),
        row.get("date"),
        row.get("year"),
    )
    published_dt = _parse_date_bound(published_raw)
    published_iso = published_dt.isoformat() if published_dt else None
    year = _first_non_empty(row.get("year"), str(published_dt.year) if published_dt else None)

    source_id = _first_non_empty(row.get("source_id"), row.get("doi"), row.get("arxiv_id"))
    arxiv_id = _first_non_empty(row.get("arxiv_id"), source_id)

    normalized: dict[str, Any] = {
        "key": row.get("key"),
        "title": title,
        "abstract": abstract,
        "summary": abstract,
        "source": row.get("source"),
        "source_id": source_id,
        "arxiv_id": arxiv_id,
        "published": published_iso or row.get("published"),
        "published_date": published_iso or row.get("published_date"),
        "publication_date": published_iso or row.get("publication_date"),
        "year": str(year).strip() if year is not None else None,
        "match_status": row.get("match_status"),
        "match_score": row.get("match_score"),
        "metadata": dict(row),
    }
    return normalized


def _load_metadata_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        records: list[dict[str, Any]] = []
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL at {path}:{idx}: {exc}") from exc
            if isinstance(payload, dict):
                records.append(payload)
        return records

    payload = _load_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if isinstance(payload, dict):
        for key in ("records", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]

    raise SystemExit(f"Unsupported metadata format: {path}")


def _clean_criterion_line(text: str) -> str:
    line = text.strip()
    line = re.sub(r"^[-*]\s+", "", line)
    line = re.sub(r"^[IE]\d+[\.:]\s*", "", line)
    line = re.sub(r"^\d+[\.)]\s*", "", line)
    return line.strip()


def _parse_criteria_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    topic = path.stem
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            topic = stripped[2:].strip()
            break

    inclusion: list[str] = []
    exclusion: list[str] = []
    mode: str | None = None
    inclusion_header_re = re.compile(r"^(?:#{1,6}\s*)?inclusion criteria\b", re.IGNORECASE)
    exclusion_header_re = re.compile(r"^(?:#{1,6}\s*)?exclusion criteria\b", re.IGNORECASE)
    inclusion_item_re = re.compile(r"^(?:I\d+[\.:]|\d+[\.)]|[-*])\s*")
    exclusion_item_re = re.compile(r"^(?:E\d+[\.:]|\d+[\.)]|[-*])\s*")

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue

        if inclusion_header_re.match(stripped):
            mode = "inclusion"
            continue
        if exclusion_header_re.match(stripped):
            mode = "exclusion"
            continue

        lower = stripped.lower()
        if mode and stripped.startswith("##") and "criteria" not in lower:
            mode = None
            continue
        if mode and stripped.startswith("---"):
            mode = None
            continue

        if mode is None:
            continue
        if mode == "inclusion" and not inclusion_item_re.match(stripped):
            continue
        if mode == "exclusion" and not exclusion_item_re.match(stripped):
            continue

        line = _clean_criterion_line(stripped)
        if not line:
            continue
        if line.endswith(":") or line.endswith("："):
            continue

        if mode == "inclusion":
            inclusion.append(line)
        elif mode == "exclusion":
            exclusion.append(line)

    if not inclusion and not exclusion:
        raise SystemExit(f"Cannot parse Inclusion/Exclusion criteria from markdown: {path}")

    source = _rel(path)
    topic_id = "S1"
    return {
        "topic": topic,
        "topic_definition": topic,
        "summary": f"Parsed screening criteria from {source}",
        "summary_topics": [{"id": topic_id, "description": topic}],
        "inclusion_criteria": {
            "required": [
                {"criterion": item, "source": source, "topic_ids": [topic_id]} for item in inclusion
            ]
        },
        "exclusion_criteria": [
            {"criterion": item, "source": source, "topic_ids": [topic_id]} for item in exclusion
        ],
        "sources": [source],
    }


def _load_criteria_payload(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".md":
        return _parse_criteria_markdown(path)

    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected criteria object JSON in {path}")

    structured = payload.get("structured_payload")
    if isinstance(structured, dict):
        return structured
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare local smoke-test inputs (top-k metadata + criteria). "
            "Supports metadata .json/.jsonl and criteria .json/.md."
        )
    )
    parser.add_argument(
        "--source-metadata",
        type=Path,
        default=DEFAULT_SOURCE_METADATA,
        help="Source metadata path (.json list or .jsonl).",
    )
    parser.add_argument(
        "--source-criteria",
        type=Path,
        default=DEFAULT_SOURCE_CRITERIA,
        help="Source criteria path (.json or .md).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output folder for local smoke-test inputs.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of metadata records to keep.")
    args = parser.parse_args()

    if args.top_k <= 0:
        raise SystemExit("--top-k must be > 0")

    metadata_path = args.source_metadata.resolve()
    criteria_path = args.source_criteria.resolve()

    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata file: {metadata_path}")
    if not criteria_path.exists():
        raise SystemExit(f"Missing criteria file: {criteria_path}")

    raw_records = _load_metadata_records(metadata_path)
    normalized_records = [_normalize_metadata_record(row) for row in raw_records if isinstance(row, dict)]

    # Keep only records that can be screened by title + abstract.
    screenable = [
        row for row in normalized_records if str(row.get("title") or "").strip() and str(row.get("abstract") or "").strip()
    ]
    if len(screenable) < args.top_k:
        raise SystemExit(
            f"Not enough screenable rows for top-k={args.top_k}; "
            f"available={len(screenable)} (raw={len(raw_records)})"
        )

    criteria_payload = _load_criteria_payload(criteria_path)

    subset = screenable[: args.top_k]

    out_dir = args.output_dir.resolve()
    out_metadata = out_dir / f"arxiv_metadata.top{args.top_k}.json"
    out_criteria = out_dir / "criteria.json"
    out_manifest = out_dir / "manifest.json"

    _write_json(out_metadata, subset)
    _write_json(out_criteria, criteria_payload)
    _write_json(
        out_manifest,
        {
            "source_metadata": _rel(metadata_path),
            "source_criteria": _rel(criteria_path),
            "source_metadata_format": metadata_path.suffix.lower(),
            "source_criteria_format": criteria_path.suffix.lower(),
            "top_k": args.top_k,
            "output_metadata": _rel(out_metadata),
            "output_criteria": _rel(out_criteria),
            "metadata_total_available": len(raw_records),
            "metadata_screenable_count": len(screenable),
            "metadata_subset_count": len(subset),
            "metadata_first_record_keys": _first_record_keys(subset),
        },
    )

    print(f"[ok] wrote metadata subset: {out_metadata}")
    print(f"[ok] wrote criteria copy: {out_criteria}")
    print(f"[ok] wrote manifest: {out_manifest}")
    print(f"[info] raw_count={len(raw_records)}")
    print(f"[info] screenable_count={len(screenable)}")
    print(f"[info] subset_count={len(subset)}")
    print(f"[info] first_record_keys={_first_record_keys(subset)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
