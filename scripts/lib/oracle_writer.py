#!/usr/bin/env python3
"""Build reference_oracle payloads from parsed BibTeX entries."""

from __future__ import annotations

import json
from collections import Counter
from typing import Dict, Iterable, List, Tuple

from .bib_parser import BibEntry
from .note_parser import extract_doi_from_text, extract_title_from_note
from .title_normalizer import normalize_title


def build_reference_oracle_records(
    entries: Iterable[BibEntry],
    *,
    use_title_first: bool = True,
    strict_title: bool = False,
) -> Tuple[List[dict], Counter]:
    """Build JSONL records for one or more BibTeX entries.

    - `use_title_first`: prefer `entry.fields["title"]` when available.
    - if no title found, fallback to `extract_title_from_note`.
    Returns:
        records list and reason counter for summary diagnostics.
    """
    records: List[dict] = []
    reasons: Counter = Counter()

    for entry in entries:
        note = entry.fields.get("note", "")
        title_reason = ""

        query_title = ""
        if use_title_first:
            query_title = (entry.fields.get("title") or "").strip()
        if not query_title:
            query_title, title_reason = extract_title_from_note(note, strict_title=strict_title)
            if not title_reason:
                title_reason = "from_note"
        else:
            title_reason = "from_title"

        if not query_title and strict_title:
            reasons["strict_missing_title"] += 1
        elif not query_title:
            reasons["empty_title"] += 1
        else:
            reasons[f"ok:{title_reason}"] += 1

        record = {
            "key": entry.key,
            "entry_type": entry.entry_type,
            "query_title": query_title,
            "normalized_title": normalize_title(query_title),
            "matched": False,
            "match_score": 0.0,
            "arxiv": None,
            "sources": {"query_title": "local"},
            "raw": {
                "local": entry.raw_fields,
            },
        }
        records.append(record)

    return records, reasons


def oracle_records_to_jsonl_lines(records: Iterable[dict]) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=True) for r in records) + ("\n" if records else "")
