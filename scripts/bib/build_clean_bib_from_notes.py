#!/usr/bin/env python3
"""Build cleaned BibTeX from per_SR raw note-only references."""

from __future__ import annotations

import argparse
import csv
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.bib_parser import BibEntry, parse_bibtex
from scripts.lib.crossref_client import CrossrefCache, fetch_crossref_metadata
from scripts.lib.note_parser import (
    extract_doi_from_text,
    normalize_author_block,
    parse_note_to_fields,
)


@dataclass
class ParseRecord:
    key: Optional[str]
    entry_type: str
    fields: Dict[str, str]
    source: str
    title_confidence: float
    author_confidence: float
    needs_human_review: bool
    problem_reason: str


def _format_bib_value(value: str) -> str:
    if value is None:
        return "{}"
    value = str(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return value


def _build_parsed_record(entry: BibEntry, *, crossref_cache: Optional[CrossrefCache], use_crossref: bool) -> ParseRecord:
    note = entry.fields.get("note", "")
    local_fields = parse_note_to_fields(note, prefer_fields=entry.fields)

    sr_refnum = entry.fields.get("sr_refnum", "").strip()
    sr_source = entry.fields.get("sr_source", "").strip()

    source = "local"
    title = local_fields.get("title", "")
    author = normalize_author_block(local_fields.get("author_raw", ""))

    doi_hint = extract_doi_from_text(note, entry.fields)
    doi_value = (entry.fields.get("doi", "") or "").strip().strip("{}")

    if use_crossref and doi_hint:
        cr = fetch_crossref_metadata(doi_hint, cache=crossref_cache) if crossref_cache else None
        if cr and (cr.get("title") or cr.get("author") or cr.get("journal")):
            source = "crossref"
            title = cr.get("title") or title
            if cr.get("author"):
                author = cr.get("author")
            if cr.get("journal"):
                local_fields["journal"] = cr.get("journal", local_fields.get("journal", ""))
            if cr.get("volume"):
                local_fields["volume"] = cr.get("volume")
            if cr.get("number"):
                local_fields["number"] = cr.get("number")
            if cr.get("pages"):
                local_fields["pages"] = cr.get("pages")
            if not local_fields.get("year") and cr.get("year"):
                local_fields["year"] = cr.get("year")
            if cr.get("doi"):
                doi_value = str(cr.get("doi"))
            if cr.get("url"):
                entry.fields["url"] = str(cr.get("url"))

    title_conf = 0.0
    if title:
        title_conf = 0.9 if source == "crossref" else 0.65
        if local_fields.get("_title_reason") in {"from_after_authors", "from_title_repair"}:
            title_conf = max(0.75, title_conf)
        elif local_fields.get("_title_reason", "").startswith("from_"):
            title_conf = 0.6

    author_conf = 0.2
    if author:
        author_conf = 0.85 if source == "crossref" else 0.55

    needs_review = False
    reason = local_fields.get("_title_reason", "")
    if source == "local" and (title_conf < 0.6 or author_conf < 0.5):
        needs_review = True
        reason = reason or "low_confidence"

    if not title and not author:
        source = "fallback"
        needs_review = True
        reason = reason or "missing_fields"

    return ParseRecord(
        key=entry.key,
        entry_type=entry.entry_type,
        fields={
            "title": title or "",
            "author": author or "",
            "journal": local_fields.get("journal", ""),
            "volume": local_fields.get("volume", ""),
            "number": local_fields.get("number", ""),
            "pages": local_fields.get("pages", ""),
            "year": local_fields.get("year", ""),
            "publisher": local_fields.get("publisher", ""),
            "sr_refnum": sr_refnum,
            "sr_source": sr_source,
            "note_cleaned": local_fields.get("note_cleaned", ""),
            "doi_from_text": doi_hint or "",
            "doi": doi_value,
        },
        source=source,
        title_confidence=title_conf,
        author_confidence=author_conf,
        needs_human_review=needs_review,
        problem_reason=reason or "",
    )


def _emit_bib_entry(key: str, entry_type: str, original_fields: Dict[str, str], parsed: ParseRecord) -> str:
    fields = dict(original_fields)
    if parsed.fields.get("title"):
        fields["title"] = parsed.fields.get("title", "")
    if parsed.fields.get("author"):
        fields["author"] = parsed.fields.get("author", "")
    if parsed.fields.get("journal"):
        fields["journal"] = parsed.fields.get("journal", "")
    if parsed.fields.get("volume"):
        fields["volume"] = parsed.fields["volume"]
    if parsed.fields.get("number"):
        fields["number"] = parsed.fields["number"]
    if parsed.fields.get("pages"):
        fields["pages"] = parsed.fields["pages"]
    if parsed.fields.get("publisher"):
        fields["organization"] = parsed.fields.get("publisher", "")

    year_hint = fields.get("year", "") or parsed.fields.get("year", "")
    if year_hint:
        fields["year"] = str(year_hint)

    if parsed.fields.get("doi"):
        fields["doi"] = parsed.fields.get("doi")
    elif parsed.fields.get("doi_from_text"):
        fields.setdefault("doi", parsed.fields.get("doi_from_text", ""))

    fields["note"] = parsed.fields.get("note_cleaned") or fields.get("note", "")

    rendered_fields = []
    for k in sorted(fields.keys()):
        v = fields.get(k)
        if v is None or v == "":
            continue
        if k == "publisher":
            continue
        rendered_fields.append(f"  {k} = {{{_format_bib_value(v)}}},")

    return "\n".join([f"@{entry_type}{{{key},"] + rendered_fields + ["}"])


def _write_parse_bib(entries: Iterable[BibEntry], output_path: Path, *, crossref_cache: Optional[CrossrefCache], use_crossref: bool, keep_empty: bool) -> list[ParseRecord]:
    records: list[ParseRecord] = []
    bib_chunks: list[str] = []

    output_path.parent.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        record = _build_parsed_record(
            entry,
            crossref_cache=crossref_cache,
            use_crossref=use_crossref,
        )
        records.append(record)

        if not keep_empty and not record.fields.get("title") and not record.fields.get("author"):
            continue

        bib_chunks.append(
            _emit_bib_entry(
                entry.key or "",
                entry.entry_type or "misc",
                entry.fields,
                record,
            )
        )

    with output_path.open("w", encoding="utf-8") as handle:
        if output_path.suffix != ".bib":
            handle.write("% ============================================\n")
            handle.write(f"% File: {output_path}\n")
            handle.write("% ============================================\n")
        else:
            header = [
                "% ================================================",
                f"% File: {output_path}",
                "% ================================================",
                "% Purpose",
                "%   Cleaned BibTeX output from note-only BibTeX references.",
                "% ================================================",
                "",
            ]
            if bib_chunks:
                handle.write("\n".join(header))
        handle.write("\n\n".join(bib_chunks) + ("\n" if bib_chunks else ""))

    return records


def _write_report(report_path: Path, records: list[ParseRecord]) -> None:
    header = [
        "key",
        "sr_refnum",
        "has_title",
        "has_author",
        "source",
        "title_confidence",
        "author_confidence",
        "needs_human_review",
        "problem_reason",
    ]
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for rec in records:
            sr_refnum = rec.fields.get("sr_refnum", "")
            writer.writerow(
                [
                    rec.key or "",
                    sr_refnum,
                    "true" if rec.fields.get("title") else "false",
                    "true" if rec.fields.get("author") else "false",
                    rec.source,
                    f"{rec.title_confidence:.2f}",
                    f"{rec.author_confidence:.2f}",
                    "true" if rec.needs_human_review else "false",
                    rec.problem_reason.replace(",", ";"),
                ]
            )


def build_cleaned_bib_from_paths(
    bib_paths: list[Path],
    output_dir: Path,
    *,
    keep_empty: bool,
    crossref_cache: Path,
    disable_crossref: bool,
    confidence_report: bool,
    include_report_all: bool = False,
    review_candidates: bool = False,
) -> tuple[list[tuple[Path, int, int, int, int]], list[ParseRecord]]:
    crossref_client: Optional[CrossrefCache] = None
    if not disable_crossref:
        crossref_client = CrossrefCache(crossref_cache)

    summaries: list[tuple[Path, int, int, int, int]] = []
    all_records: list[ParseRecord] = []

    for bib_path in bib_paths:
        text = bib_path.read_text(encoding="utf-8", errors="ignore")
        entries = parse_bibtex(text)

        out_path = output_dir / f"{bib_path.stem}.bib"
        records = _write_parse_bib(
            entries,
            out_path,
            crossref_cache=crossref_client,
            use_crossref=(not disable_crossref),
            keep_empty=keep_empty,
        )

        total = len(entries)
        parsed = sum(1 for r in records if r.source in {"crossref", "local"})
        fallback = sum(1 for r in records if r.source == "fallback")
        empty = sum(1 for r in records if not r.fields.get("title"))
        summaries.append((bib_path, total, parsed, fallback, empty))
        all_records.extend(records)

        if confidence_report:
            report_path = output_dir / f"{bib_path.stem}_parse_report.csv"
            _write_report(report_path, records)

    if confidence_report and include_report_all:
        report_all_path = output_dir / "per_SR_parse_report_all.csv"
        _write_report(report_all_path, all_records)

    if review_candidates:
        candidate_path = output_dir / "review_candidates_all.csv"
        with candidate_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["key", "sr_refnum", "query_title", "query_author", "source", "problem_reason", "title_confidence", "author_confidence"])
            for rec in all_records:
                if rec.needs_human_review:
                    writer.writerow(
                        [
                            rec.key or "",
                            rec.fields.get("sr_refnum", ""),
                            rec.fields.get("title", ""),
                            rec.fields.get("author", ""),
                            rec.source,
                            rec.problem_reason,
                            f"{rec.title_confidence:.2f}",
                            f"{rec.author_confidence:.2f}",
                        ]
                    )

    if crossref_client is not None:
        crossref_client.save()

    return summaries, all_records


def _print_summary(summaries: list[tuple[Path, int, int, int, int]], all_records: list[ParseRecord]) -> None:
    total = sum(s[1] for s in summaries)
    parsed = sum(s[2] for s in summaries)
    fallback = sum(s[3] for s in summaries)
    empty = sum(s[4] for s in summaries)
    review = sum(1 for rec in all_records if rec.needs_human_review)

    for bib_path, n_total, n_parsed, n_fallback, n_empty in summaries:
        print(
            f"[done] {Path(bib_path).name}: entries={n_total}, parsed={n_parsed}, fallback={n_fallback}, empty={n_empty}"
        )

    print(f"[total] entries={total}, parsed={parsed}, fallback={fallback}, empty={empty}, review={review}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build cleaned per_SR BibTeX from note-heavy BibTeX.")
    parser.add_argument("--bib-path", type=Path, default=None, help="Single BibTeX input")
    parser.add_argument("--bib-dir", type=Path, default=None, help="Directory with BibTeX files")
    parser.add_argument("--out-dir", type=Path, default=Path("bib/per_SR_cleaned"), help="Output directory")
    parser.add_argument("--keep-empty", action="store_true", help="Keep entries with both title and author missing")
    parser.add_argument("--confidence-report", action="store_true", help="Write per-file parse CSV")
    parser.add_argument("--confidence-report-all", action="store_true", help="Write global parse report")
    parser.add_argument("--review-candidates", action="store_true", help="Write review_candidates_all.csv")
    parser.add_argument("--disable-crossref", action="store_true", help="Disable DOI -> Crossref enrich")
    parser.add_argument(
        "--enable-crossref",
        action="store_true",
        help="Compatibility flag (default behavior is Crossref enabled)",
    )
    parser.add_argument("--crossref-cache", type=Path, default=Path(".crossref_cache.json"), help="Crossref cache path")

    args = parser.parse_args()

    if not args.bib_path and not args.bib_dir:
        raise SystemExit("must provide either --bib-path or --bib-dir")
    if args.bib_path and args.bib_dir:
        raise SystemExit("provide only one of --bib-path or --bib-dir")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.bib_path:
        bib_paths = [args.bib_path]
    else:
        if not args.bib_dir.exists() or not args.bib_dir.is_dir():
            raise SystemExit(f"BibTeX directory not found: {args.bib_dir}")
        bib_paths = sorted(args.bib_dir.glob("*.bib"))
        if not bib_paths:
            raise SystemExit(f"No .bib files found in {args.bib_dir}")

    if args.enable_crossref and args.disable_crossref:
        raise SystemExit("Cannot set both --enable-crossref and --disable-crossref")

    disable_crossref = args.disable_crossref
    if args.enable_crossref:
        disable_crossref = False

    summaries, all_records = build_cleaned_bib_from_paths(
        bib_paths,
        output_dir=args.out_dir,
        keep_empty=args.keep_empty,
        crossref_cache=args.crossref_cache,
        disable_crossref=disable_crossref,
        confidence_report=args.confidence_report,
        include_report_all=args.confidence_report_all,
        review_candidates=args.review_candidates,
    )

    _print_summary(summaries, all_records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
