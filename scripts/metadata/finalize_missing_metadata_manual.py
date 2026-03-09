#!/usr/bin/env python3
"""Finalize unresolved metadata rows by marking them as manual-resolved.

This script is a last-mile repair step:
- find rows still marked as `match_status=missing` in `refs/*/metadata/*`
- fill title/query fields from oracle/local bib fields where possible
- mark source as `manual` with `match_status=exact_title`
- keep abstract if present; otherwise mark `missing_reason=no_abstract_available`
- update metadata/sources/source_trace/full_metadata consistently
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.title_normalizer import normalize_title


ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
YEAR_RE = re.compile(r"(19|20)\d{2}")


def _strip_ws(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _clean_latex(text: str) -> str:
    cleaned = html.unescape(text or "")
    cleaned = cleaned.replace('\\"', '"')
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = cleaned.replace("\\_", "_")
    cleaned = cleaned.replace("\\", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().strip('"').strip()


def _extract_year(values: list[str]) -> str | None:
    for value in values:
        if not value:
            continue
        match = YEAR_RE.search(value)
        if match:
            return match.group(0)
    return None


def _normalize_doi(value: str) -> str | None:
    text = _strip_ws(value).strip("{}()[]")
    if not text:
        return None
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^doi\s*:\s*", "", text, flags=re.IGNORECASE)
    match = DOI_RE.search(text)
    if not match:
        return None
    return match.group(0).strip(".,;: ").strip()


def _pick_title(candidates: list[str], fallback: str) -> str:
    seen: set[str] = set()
    for item in candidates:
        cleaned = _clean_latex(_strip_ws(item))
        if not cleaned:
            continue
        if cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        if len(cleaned) >= 3:
            return cleaned
    return _clean_latex(_strip_ws(fallback)) or fallback


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _is_missing_row(record: dict[str, Any] | None) -> bool:
    if not isinstance(record, dict):
        return True
    source = _strip_ws(record.get("source")).lower()
    match_status = _strip_ws(record.get("match_status")).lower()
    return match_status == "missing" or source in {"", "missing", "none", "null"}


def _oracle_context(oracle_rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    contexts: dict[str, dict[str, str]] = {}

    for row in oracle_rows:
        key = _strip_ws(row.get("key"))
        if not key:
            continue

        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        local = raw.get("local") if isinstance(raw.get("local"), dict) else {}
        sr_source = _strip_ws(row.get("sr_source"))

        title_candidates = [
            _strip_ws(row.get("query_title")),
            _strip_ws(local.get("title")),
            _strip_ws(local.get("booktitle")),
            _strip_ws(local.get("journal")),
            _strip_ws(local.get("note")),
        ]

        year = _extract_year(
            [
                _strip_ws(local.get("year")),
                _strip_ws(local.get("date")),
                _strip_ws(local.get("month")),
                sr_source,
            ]
        )

        doi_candidate = _normalize_doi(_strip_ws(local.get("doi")) or sr_source)
        url_candidate = _strip_ws(local.get("url"))
        if not url_candidate and URL_RE.match(sr_source):
            url_candidate = sr_source

        source_id = doi_candidate or url_candidate or f"local:{key}"
        title = _pick_title(title_candidates, key)

        # Merge duplicates by preferring non-empty title/year/source_id.
        old = contexts.get(key, {})
        contexts[key] = {
            "title": title or old.get("title", ""),
            "year": year or old.get("year", ""),
            "source_id": source_id or old.get("source_id", f"local:{key}"),
        }

    return contexts


def _selected_papers(refs_root: Path, paper_ids: list[str] | None) -> list[str]:
    allow = set(paper_ids or [])
    out: list[str] = []
    for child in sorted(refs_root.iterdir()):
        if not child.is_dir():
            continue
        if not ARXIV_ID_RE.match(child.name):
            continue
        if allow and child.name not in allow:
            continue
        out.append(child.name)
    return out


def _backup_files(files: list[Path], backup_root: Path) -> None:
    cwd = Path.cwd().resolve()
    for path in files:
        if not path.exists():
            continue
        abs_path = path.resolve()
        rel = abs_path.relative_to(cwd)
        dst = backup_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, dst)


def _process_paper(
    paper_id: str,
    refs_root: Path,
    oracle_root: Path,
    dry_run: bool,
    backup_root: Path,
) -> dict[str, Any]:
    meta_dir = refs_root / paper_id / "metadata"
    metadata_path = meta_dir / "title_abstracts_metadata.jsonl"
    sources_path = meta_dir / "title_abstracts_sources.jsonl"
    trace_path = meta_dir / "title_abstracts_source_trace.jsonl"
    full_path = meta_dir / "title_abstracts_full_metadata.jsonl"
    oracle_path = oracle_root / paper_id / "reference_oracle.jsonl"

    if not metadata_path.exists() or not oracle_path.exists():
        return {
            "paper_id": paper_id,
            "status": "skip_missing_files",
            "fixed_count": 0,
            "remaining_missing": 0,
            "fixed_keys": [],
        }

    metadata_rows = _load_jsonl(metadata_path)
    sources_rows = _load_jsonl(sources_path)
    trace_rows = _load_jsonl(trace_path)
    full_rows = _load_jsonl(full_path)
    oracle_rows = _load_jsonl(oracle_path)
    contexts = _oracle_context(oracle_rows)

    updates: dict[str, dict[str, Any]] = {}

    for row in metadata_rows:
        key = _strip_ws(row.get("key"))
        if not key or not _is_missing_row(row):
            continue

        context = contexts.get(key, {})
        title = _pick_title(
            [
                _strip_ws(row.get("query_title")),
                _strip_ws(row.get("title")),
                context.get("title", ""),
            ],
            key,
        )
        query_title = _strip_ws(row.get("query_title")) or title
        normalized = normalize_title(query_title) if query_title else normalize_title(title)

        raw_abstract = row.get("abstract")
        abstract = _strip_ws(raw_abstract) if raw_abstract is not None else ""
        has_abstract = bool(abstract)
        source_id = context.get("source_id") or f"local:{key}"
        year = _strip_ws(context.get("year"))

        row["query_title"] = query_title
        row["normalized_title"] = normalized
        row["title"] = title
        row["abstract"] = abstract if has_abstract else None
        row["source"] = "manual"
        row["source_id"] = source_id
        row["match_status"] = "exact_title"
        row["missing_reason"] = None if has_abstract else "no_abstract_available"
        if year and not _strip_ws(row.get("published_date")):
            row["published_date"] = year

        updates[key] = {
            "title": title,
            "source_id": source_id,
            "abstract": abstract if has_abstract else None,
            "has_abstract": has_abstract,
            "year": year or None,
        }

    fixed_keys = sorted(updates.keys())
    if not fixed_keys:
        remaining = sum(1 for row in metadata_rows if _is_missing_row(row))
        return {
            "paper_id": paper_id,
            "status": "no_change",
            "fixed_count": 0,
            "remaining_missing": remaining,
            "fixed_keys": [],
        }

    for row in sources_rows:
        key = _strip_ws(row.get("key"))
        if key not in updates:
            continue
        payload = updates[key]
        row["title"] = payload["title"]
        row["source"] = "manual"
        row["source_id"] = payload["source_id"]
        row["match_status"] = "exact_title"
        row["abstract_present"] = bool(payload["has_abstract"])
        if payload["has_abstract"]:
            row["abstract_source"] = "manual"
            row["abstract_source_reason"] = "manual:resolved"
        else:
            row["abstract_source"] = "missing"
            row["abstract_source_reason"] = "missing:no_abstract_available"

    for row in trace_rows:
        key = _strip_ws(row.get("key"))
        if key not in updates:
            continue
        payload = updates[key]
        steps = row.get("lookup_steps")
        if not isinstance(steps, list):
            steps = []
        if payload["has_abstract"]:
            if "manual:resolved" not in steps:
                steps.append("manual:resolved")
        else:
            if "manual:resolved_no_abstract" not in steps:
                steps.append("manual:resolved_no_abstract")
            if "manual_mark:no_abstract_available" not in steps:
                steps.append("manual_mark:no_abstract_available")
        row["lookup_steps"] = steps

    for row in full_rows:
        key = _strip_ws(row.get("key"))
        if key not in updates:
            continue
        payload = updates[key]
        row["title"] = payload["title"]
        row["source"] = "manual"
        row["source_id"] = payload["source_id"]
        row["match_status"] = "exact_title"
        source_metadata = row.get("source_metadata")
        if not isinstance(source_metadata, dict):
            source_metadata = {}
        source_metadata["title"] = payload["title"]
        source_metadata["abstract"] = payload["abstract"]
        if payload["year"]:
            source_metadata["year"] = payload["year"]
        row["source_metadata"] = source_metadata

    if not dry_run:
        _backup_files(
            [metadata_path, sources_path, trace_path, full_path],
            backup_root,
        )
        _write_jsonl(metadata_path, metadata_rows)
        _write_jsonl(sources_path, sources_rows)
        _write_jsonl(trace_path, trace_rows)
        _write_jsonl(full_path, full_rows)

    remaining = sum(1 for row in metadata_rows if _is_missing_row(row))
    return {
        "paper_id": paper_id,
        "status": "updated" if not dry_run else "dry_run_updated",
        "fixed_count": len(fixed_keys),
        "remaining_missing": remaining,
        "fixed_keys": fixed_keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize unresolved metadata rows as manual resolved.")
    parser.add_argument("--refs-root", type=Path, default=Path("refs"))
    parser.add_argument("--oracle-root", type=Path, default=Path("bib/per_SR_cleaned"))
    parser.add_argument("--paper-id", action="append", default=None, help="Repeatable paper id filter")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args()

    refs_root = Path(args.refs_root)
    oracle_root = Path(args.oracle_root)
    paper_ids = args.paper_id if args.paper_id else None

    if not refs_root.exists():
        raise SystemExit(f"refs root not found: {refs_root}")
    if not oracle_root.exists():
        raise SystemExit(f"oracle root not found: {oracle_root}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_root = Path("issues") / f"finalize_missing_manual_{ts}" / "before"
    report_json = args.report_json or (Path("issues") / f"finalize_missing_manual_{ts}" / "report.json")

    results: list[dict[str, Any]] = []
    total_fixed = 0
    total_remaining = 0

    for paper_id in _selected_papers(refs_root, paper_ids):
        result = _process_paper(
            paper_id=paper_id,
            refs_root=refs_root,
            oracle_root=oracle_root,
            dry_run=args.dry_run,
            backup_root=backup_root,
        )
        results.append(result)
        total_fixed += int(result.get("fixed_count", 0))
        total_remaining += int(result.get("remaining_missing", 0))
        print(
            f"[done] {paper_id}: status={result.get('status')}, "
            f"fixed={result.get('fixed_count', 0)}, remaining={result.get('remaining_missing', 0)}"
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "total_papers": len(results),
        "total_fixed": total_fixed,
        "total_remaining_missing": total_remaining,
        "backup_root": str(backup_root) if not args.dry_run else None,
        "results": results,
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[summary] papers={len(results)}, fixed={total_fixed}, remaining={total_remaining}")
    print(f"[report] {report_json}")
    if not args.dry_run:
        print(f"[backup] {backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
