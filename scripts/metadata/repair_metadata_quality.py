#!/usr/bin/env python3
"""Repair metadata quality issues: published_date backfill + obvious bad matches.

Scope:
- Backfill `published_date` from oracle/local year and source metadata year.
- Fix obvious source mismatch rows (wrong title/abstract from noisy matches).
"""

from __future__ import annotations

import argparse
import csv
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


YEAR_RE = re.compile(r"(19|20)\d{2}")
ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)
PUBLISHED_DATE_RE = re.compile(r"^\d{4}(?:-\d{2})?(?:-\d{2})?$")
ARXIV_SOURCE_ID_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/)?(?P<id>\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?",
    re.IGNORECASE,
)


# Known-bad keys discovered by audit where fetched title/abstract is clearly wrong.
KNOWN_BAD_KEYS: set[tuple[str, str]] = {
    ("2306.12834", "weiner2018semi"),
    ("2306.12834", "portet2009automatic"),
    ("2307.05527", "kersta1962voiceprint"),
    ("2312.05172", "Knight2002"),
    ("2401.09244", "kumar2022multi"),
    ("2409.13738", "weske2007business"),
    ("2409.13738", "goncalves2011let"),
    ("2509.11446", "chen2025nlp4reindustry"),
    ("2509.11446", "Binder2024-gr"),
    ("2509.11446", "wang2023automating"),
    ("2509.11446", "zhang2023llm"),
    ("2509.11446", "Kitchenham2011"),
    ("2510.01145", "alhumud2024improving"),
    ("2510.01145", "masekwameng2020effects"),
    ("2510.01145", "Held2023"),
    ("2510.01145", "emiru2021amharic"),
    ("2601.19926", "chatgpt5:2025"),
    ("2601.19926", "zhang_dependency-based_2021"),
}


def _strip_ws(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _clean_latex(text: str) -> str:
    cleaned = html.unescape(text or "")
    cleaned = cleaned.replace('\\"', '"')
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", cleaned)
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    cleaned = cleaned.replace("\\_", "_").replace("\\", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().strip('"').strip()


def _norm_ascii_tokens(text: str) -> list[str]:
    norm = _clean_latex(text).lower()
    norm = re.sub(r"[^a-z0-9]+", " ", norm)
    return [token for token in norm.split() if token]


def _jaccard_title(left: str, right: str) -> float:
    lset = set(_norm_ascii_tokens(left))
    rset = set(_norm_ascii_tokens(right))
    if not lset or not rset:
        return 0.0
    return len(lset & rset) / len(lset | rset)


def _good_query_title(text: str) -> bool:
    cleaned = _clean_latex(text)
    if not cleaned or len(cleaned) < 15:
        return False
    tokens = [t for t in re.findall(r"[A-Za-z0-9]+", cleaned) if len(t) >= 3]
    return len(tokens) >= 3


def _extract_year_candidates(values: list[str]) -> str | None:
    for value in values:
        if not value:
            continue
        match = YEAR_RE.search(value)
        if match:
            return match.group(0)
    return None


def _extract_year_from_source_metadata(source_metadata: dict[str, Any]) -> str | None:
    if not isinstance(source_metadata, dict):
        return None

    for field in ("year", "publicationYear", "published", "publicationDate", "date", "updated"):
        value = source_metadata.get(field)
        if value is None:
            continue

        if isinstance(value, dict):
            date_parts = value.get("date-parts")
            if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                year = str(date_parts[0][0])
                if re.fullmatch(r"(19|20)\d{2}", year):
                    return year
            continue

        year_match = YEAR_RE.search(str(value))
        if year_match:
            return year_match.group(0)

    return None


def _is_reasonable_year(year_text: str) -> bool:
    year_text = _strip_ws(year_text)
    if not re.fullmatch(r"\d{4}", year_text):
        return False
    year = int(year_text)
    max_year = datetime.now(timezone.utc).year + 2
    return 1800 <= year <= max_year


def _published_date_year(value: str) -> str | None:
    text = _strip_ws(value)
    if not PUBLISHED_DATE_RE.fullmatch(text):
        return None
    year_part = text.split("-", 1)[0]
    return year_part if _is_reasonable_year(year_part) else None


def _is_valid_published_date(value: str) -> bool:
    text = _strip_ws(value)
    if not text:
        return False
    if not PUBLISHED_DATE_RE.fullmatch(text):
        return False
    parts = text.split("-")
    year = int(parts[0])
    if not _is_reasonable_year(str(year)):
        return False
    if len(parts) >= 2:
        month = int(parts[1])
        if month < 1 or month > 12:
            return False
    if len(parts) == 3:
        day = int(parts[2])
        if day < 1 or day > 31:
            return False
    return True


def _arxiv_year_month_from_source_id(source_id: str) -> tuple[str | None, str | None]:
    text = _strip_ws(source_id)
    if not text:
        return None, None
    match = ARXIV_SOURCE_ID_RE.search(text)
    if not match:
        return None, None
    arxiv_id = match.group("id")
    if not arxiv_id:
        return None, None
    yymm = arxiv_id.split(".", 1)[0]
    if len(yymm) != 4 or not yymm.isdigit():
        return None, None
    yy = int(yymm[:2])
    mm = int(yymm[2:])
    if mm < 1 or mm > 12:
        return None, None
    year = 2000 + yy
    if not _is_reasonable_year(str(year)):
        return None, None
    return str(year), f"{year:04d}-{mm:02d}"


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


def _backup_files(paths: list[Path], backup_root: Path) -> None:
    cwd = Path.cwd().resolve()
    for path in paths:
        if not path.exists():
            continue
        abs_path = path.resolve()
        rel = abs_path.relative_to(cwd)
        dst = backup_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, dst)


def _oracle_context(oracles_root: Path, paper_id: str) -> dict[str, dict[str, str]]:
    oracle_path = oracles_root / paper_id / "reference_oracle.jsonl"
    rows = _load_jsonl(oracle_path)

    context: dict[str, dict[str, str]] = {}
    for row in rows:
        key = _strip_ws(row.get("key"))
        if not key:
            continue

        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        local = raw.get("local") if isinstance(raw.get("local"), dict) else {}

        title_candidates = [
            _strip_ws(row.get("query_title")),
            _strip_ws(local.get("title")),
            _strip_ws(local.get("booktitle")),
            _strip_ws(local.get("journal")),
            _strip_ws(local.get("note")),
        ]

        title = ""
        for candidate in title_candidates:
            cleaned = _clean_latex(candidate)
            if cleaned:
                title = cleaned
                break

        year = _extract_year_candidates(
            [
                _strip_ws(local.get("year")),
                _strip_ws(local.get("date")),
                _strip_ws(local.get("month")),
                _strip_ws(row.get("sr_source")),
                _strip_ws(local.get("note")),
            ]
        )

        source_id = f"local:{key}"
        doi_text = _strip_ws(local.get("doi")) or _strip_ws(row.get("sr_source"))
        doi_match = DOI_RE.search(doi_text)
        if doi_match:
            source_id = doi_match.group(0)
        else:
            url_text = _strip_ws(local.get("url")) or _strip_ws(row.get("sr_source"))
            if re.match(r"^https?://", url_text, re.IGNORECASE):
                source_id = url_text

        prev = context.get(key, {})
        context[key] = {
            "title": title or prev.get("title", ""),
            "year": year or prev.get("year", ""),
            "source_id": source_id or prev.get("source_id", f"local:{key}"),
        }

    return context


def _should_force_manual_fix(paper_id: str, row: dict[str, Any]) -> bool:
    key = _strip_ws(row.get("key"))
    if not key:
        return False
    return (paper_id, key) in KNOWN_BAD_KEYS


def _apply_manual_fix(
    paper_id: str,
    key: str,
    metadata_rows: list[dict[str, Any]],
    sources_rows: list[dict[str, Any]],
    trace_rows: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
    context: dict[str, dict[str, str]],
) -> None:
    meta_title = context.get(key, {}).get("title") or key
    meta_year = context.get(key, {}).get("year") or ""
    source_id = context.get(key, {}).get("source_id") or f"local:{key}"

    for row in metadata_rows:
        if _strip_ws(row.get("key")) != key:
            continue
        query_title = _clean_latex(_strip_ws(row.get("query_title")) or meta_title)
        title = _clean_latex(meta_title or query_title or key)
        row["query_title"] = query_title
        row["normalized_title"] = normalize_title(title or query_title)
        row["title"] = title
        row["abstract"] = None
        row["source"] = "manual"
        row["source_id"] = source_id
        row["match_status"] = "exact_title"
        row["missing_reason"] = "no_abstract_available"
        if meta_year:
            row["published_date"] = meta_year

    for row in sources_rows:
        if _strip_ws(row.get("key")) != key:
            continue
        row["title"] = _clean_latex(meta_title or key)
        row["source"] = "manual"
        row["source_id"] = source_id
        row["match_status"] = "exact_title"
        row["abstract_present"] = False
        row["abstract_source"] = "missing"
        row["abstract_source_reason"] = "missing:no_abstract_available"

    for row in trace_rows:
        if _strip_ws(row.get("key")) != key:
            continue
        steps = row.get("lookup_steps")
        if not isinstance(steps, list):
            steps = []
        if "manual_fix:suspicious_source_mismatch" not in steps:
            steps.append("manual_fix:suspicious_source_mismatch")
        if "manual:resolved_no_abstract" not in steps:
            steps.append("manual:resolved_no_abstract")
        if "manual_mark:no_abstract_available" not in steps:
            steps.append("manual_mark:no_abstract_available")
        row["lookup_steps"] = steps

    for row in full_rows:
        if _strip_ws(row.get("key")) != key:
            continue
        row["title"] = _clean_latex(meta_title or key)
        row["source"] = "manual"
        row["source_id"] = source_id
        row["match_status"] = "exact_title"
        source_metadata = row.get("source_metadata")
        if not isinstance(source_metadata, dict):
            source_metadata = {}
        source_metadata["title"] = _clean_latex(meta_title or key)
        source_metadata["abstract"] = None
        if meta_year:
            source_metadata["year"] = meta_year
        row["source_metadata"] = source_metadata


def _iter_papers(refs_root: Path, paper_ids: list[str] | None) -> list[str]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair metadata quality issues.")
    parser.add_argument("--refs-root", type=Path, default=Path("refs"))
    parser.add_argument("--oracle-root", type=Path, default=Path("bib/per_SR_cleaned"))
    parser.add_argument("--paper-id", action="append", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    refs_root = args.refs_root
    oracle_root = args.oracle_root
    paper_ids = args.paper_id if args.paper_id else None

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    issue_root = Path("issues") / f"metadata_quality_fix_{ts}"
    backup_root = issue_root / "before"
    issue_root.mkdir(parents=True, exist_ok=True)

    report_rows: list[dict[str, Any]] = []
    fixed_total = 0
    backfill_total = 0
    full_year_fix_total = 0

    for paper_id in _iter_papers(refs_root, paper_ids):
        meta_path = refs_root / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
        src_path = refs_root / paper_id / "metadata" / "title_abstracts_sources.jsonl"
        trace_path = refs_root / paper_id / "metadata" / "title_abstracts_source_trace.jsonl"
        full_path = refs_root / paper_id / "metadata" / "title_abstracts_full_metadata.jsonl"
        if not all(path.exists() for path in (meta_path, src_path, trace_path, full_path)):
            continue

        metadata_rows = _load_jsonl(meta_path)
        sources_rows = _load_jsonl(src_path)
        trace_rows = _load_jsonl(trace_path)
        full_rows = _load_jsonl(full_path)
        oracle_ctx = _oracle_context(oracle_root, paper_id)
        full_by_key: dict[str, dict[str, Any]] = {}
        for row in full_rows:
            key = _strip_ws(row.get("key"))
            if key and key not in full_by_key:
                full_by_key[key] = row

        forced_keys: set[str] = set()
        pd_backfill = 0
        pd_overwrite = 0
        full_year_fix = 0

        # Phase 1: published_date fix/backfill
        for row in metadata_rows:
            key = _strip_ws(row.get("key"))
            if not key:
                continue

            source = _strip_ws(row.get("source")).lower()
            source_id = _strip_ws(row.get("source_id"))
            full_row = full_by_key.get(key) or {}
            source_metadata = (
                full_row.get("source_metadata")
                if isinstance(full_row.get("source_metadata"), dict)
                else {}
            )
            current_pd = _strip_ws(row.get("published_date"))
            oracle_year = _strip_ws(oracle_ctx.get(key, {}).get("year"))
            source_meta_year = _extract_year_from_source_metadata(
                source_metadata if isinstance(source_metadata, dict) else {}
            )
            arxiv_year, arxiv_year_month = (
                _arxiv_year_month_from_source_id(source_id)
                if source == "arxiv"
                else (None, None)
            )

            # Normalize malformed arXiv year values stored in full metadata (`2307` -> `2023`).
            if source == "arxiv" and isinstance(source_metadata, dict) and arxiv_year:
                raw_year = _strip_ws(source_metadata.get("year"))
                if raw_year != arxiv_year:
                    source_metadata["year"] = arxiv_year
                    full_row["source_metadata"] = source_metadata
                    full_year_fix += 1
                if not source_meta_year:
                    source_meta_year = arxiv_year

            if not current_pd:
                # Prefer source metadata year (publication-oriented) for most sources.
                # Zenodo commonly reflects deposit/update year; prefer oracle bibliographic year there.
                if source == "arxiv":
                    candidate = arxiv_year_month or source_meta_year or oracle_year
                elif source == "zenodo":
                    candidate = oracle_year or source_meta_year
                else:
                    candidate = source_meta_year or oracle_year
                if candidate:
                    row["published_date"] = candidate
                    pd_backfill += 1
                continue

            current_year = _published_date_year(current_pd)
            if source == "arxiv":
                candidate = arxiv_year_month or source_meta_year or oracle_year
                candidate_year = arxiv_year or source_meta_year or oracle_year
                if not _is_valid_published_date(current_pd):
                    if candidate and current_pd != candidate:
                        row["published_date"] = candidate
                        pd_overwrite += 1
                    continue
                if candidate_year and current_year and current_year != candidate_year:
                    if candidate and current_pd != candidate:
                        row["published_date"] = candidate
                        pd_overwrite += 1
                continue

            if not _is_valid_published_date(current_pd):
                if source == "zenodo":
                    candidate = oracle_year or source_meta_year
                else:
                    candidate = source_meta_year or oracle_year
                if candidate and current_pd != candidate:
                    row["published_date"] = candidate
                    pd_overwrite += 1
                continue

            if not current_year:
                continue

            if source == "zenodo":
                if oracle_year and current_year != oracle_year:
                    row["published_date"] = oracle_year
                    pd_overwrite += 1
            else:
                if source_meta_year and current_year != source_meta_year:
                    row["published_date"] = source_meta_year
                    pd_overwrite += 1

        # Phase 2: obvious bad source match -> manual no_abstract
        for row in metadata_rows:
            key = _strip_ws(row.get("key"))
            if not key:
                continue
            if _should_force_manual_fix(paper_id, row):
                forced_keys.add(key)

        for key in sorted(forced_keys):
            _apply_manual_fix(
                paper_id=paper_id,
                key=key,
                metadata_rows=metadata_rows,
                sources_rows=sources_rows,
                trace_rows=trace_rows,
                full_rows=full_rows,
                context=oracle_ctx,
            )

        if not args.dry_run and (pd_backfill or pd_overwrite or full_year_fix or forced_keys):
            _backup_files([meta_path, src_path, trace_path, full_path], backup_root)
            _write_jsonl(meta_path, metadata_rows)
            _write_jsonl(src_path, sources_rows)
            _write_jsonl(trace_path, trace_rows)
            _write_jsonl(full_path, full_rows)

        fixed_total += len(forced_keys)
        backfill_total += pd_backfill + pd_overwrite
        full_year_fix_total += full_year_fix
        report_rows.append(
            {
                "paper_id": paper_id,
                "forced_manual_fix_count": len(forced_keys),
                "forced_manual_keys": "|".join(sorted(forced_keys)),
                "published_date_backfill_count": pd_backfill,
                "published_date_overwrite_count": pd_overwrite,
                "full_metadata_year_fix_count": full_year_fix,
            }
        )
        print(
            f"[done] {paper_id}: forced_fix={len(forced_keys)}, "
            f"pd_backfill={pd_backfill}, pd_overwrite={pd_overwrite}, "
            f"full_year_fix={full_year_fix}"
        )

    report_csv = issue_root / "quality_fix_report.csv"
    with report_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "forced_manual_fix_count",
                "forced_manual_keys",
                "published_date_backfill_count",
                "published_date_overwrite_count",
                "full_metadata_year_fix_count",
            ],
        )
        writer.writeheader()
        writer.writerows(report_rows)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "forced_fix_total": fixed_total,
        "published_date_updates_total": backfill_total,
        "full_metadata_year_fixes_total": full_year_fix_total,
        "report_csv": str(report_csv),
        "backup_root": str(backup_root) if not args.dry_run else None,
    }
    (issue_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "[summary] forced_fix_total="
        f"{fixed_total}, published_date_updates_total={backfill_total}, "
        f"full_metadata_year_fixes_total={full_year_fix_total}"
    )
    print(f"[report] {report_csv}")
    if not args.dry_run:
        print(f"[backup] {backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
