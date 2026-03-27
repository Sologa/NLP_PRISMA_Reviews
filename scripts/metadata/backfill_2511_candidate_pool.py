#!/usr/bin/env python3
"""Backfill candidate-pool metadata/PDFs for refs/2511.13936.

This script creates a self-contained candidate-pool dataset under:

- refs/2511.13936/candidate_pool/metadata/
- refs/2511.13936/candidate_pool/pdfs/

It is resumable and record-based. Main refs/2511.13936 metadata/PDFs are treated
as read-only source material.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.bib_parser import parse_bibtex
from scripts.lib.title_normalizer import normalize_title


PAPER_ID = "2511.13936"
MIN_VALID_PDF_BYTES = 8_000
USER_AGENT = "Codex-Candidate-Pool-Backfill/1.0"

MANUAL_MAIN_ALIASES = {
    "Cited_by_published.bib::liao_baton_2024": "liao2024baton",
}

EVIDENCE_BASE_EXPECTED_TRUE = {
    "anastassiou2024seed",
    "cao2012combining",
    "cao2015speaker",
    "chu2024qwen2",
    "chumbalov2020scalable",
    "cideron2024musicrl",
    "dong2020pyramid",
    "gao2025emo",
    "han2020ordinal",
    "huang2025step",
    "jayawardena2020ordinal",
    "kumar2025using",
    "lei2023audio",
    "liao2024baton",
    "liu2021reinforcement",
    "lopes2017modelling",
    "lotfian2016practical",
    "lotfian2016retrieving",
    "luo2025openomni",
    "nagpal2025speech",
    "naini2023preference",
    "naini2023unsupervised",
    "parthasarathy2016using",
    "parthasarathy2017ranking",
    "parthasarathy2018preference",
    "wu2023interval",
    "wu2025adaptive",
    "yang2010ranking",
    "zhang2024speechalign",
    "zhou2021interactive",
}

ARXIV_ID_RE = re.compile(r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)", re.IGNORECASE)
ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)(?:\.pdf)?", re.IGNORECASE)
ARXIV_TEXT_RE = re.compile(r"arxiv\s*:?\s*(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)", re.IGNORECASE)
ARXIV_BARE_RE = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?$", re.IGNORECASE)
ARXIV_META_RE = re.compile(r'<meta\s+name="(?P<name>[^"]+)"\s+content="(?P<content>[^"]*)"', re.IGNORECASE)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
NON_ASCII_SPACE_RE = re.compile(r"\s+")

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass(frozen=True)
class WorkItem:
    record_index: int
    record_id: str
    emitted_key: str
    pool_key: str
    source_family: str
    source_segment: str
    source_file: str
    entry_type: str
    title_from_pool: str
    normalized_pool_title: str
    year_from_pool: str
    authors_from_pool: str
    doi_from_pool: str
    url_from_pool: str
    eprint_from_pool: str
    archiveprefix_from_pool: str
    abstract_from_pool: str


@dataclass
class MainRecord:
    key: str
    metadata: dict[str, Any]
    sources: dict[str, Any] | None
    trace: dict[str, Any] | None
    full_metadata: dict[str, Any] | None
    bib_fields: dict[str, str]
    pdf_path: Path | None
    is_evidence_base: bool


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
    cleaned = NON_ASCII_SPACE_RE.sub(" ", cleaned)
    return cleaned.strip().strip('"').strip()


def _sanitize_component(value: str) -> str:
    text = _clean_latex(_strip_ws(value))
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("._") or "unknown"


def _emitted_key(source_file: str, pool_key: str) -> str:
    stem = Path(source_file).stem
    return f"{_sanitize_component(stem)}__{_sanitize_component(pool_key)}"


def _normalize_doi(value: str) -> str:
    text = _strip_ws(value).strip("{}()[]")
    if not text:
        return ""
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^doi\s*:\s*", "", text, flags=re.IGNORECASE)
    match = DOI_RE.search(text)
    return match.group(0).rstrip(".,;: ").lower() if match else ""


def _extract_arxiv_id(*values: str) -> str:
    for value in values:
        text = _strip_ws(value)
        if not text:
            continue
        match = ARXIV_URL_RE.search(text)
        if match:
            return match.group("id")
        match = ARXIV_TEXT_RE.search(text)
        if match:
            return match.group("id")
        if ARXIV_BARE_RE.fullmatch(text):
            return text
        if "arxiv" not in text.lower():
            continue
        match = ARXIV_ID_RE.search(text)
        if match:
            return match.group("id")
    return ""


def _strip_arxiv_version(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", _strip_ws(arxiv_id), flags=re.IGNORECASE)


def _first_author_surname_from_pool(authors_text: str) -> str:
    text = _clean_latex(authors_text)
    if not text:
        return ""
    first = re.split(r";|\band\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    if "," in first:
        return first.split(",", 1)[0].strip().lower()
    parts = first.split()
    return parts[-1].strip().lower() if parts else ""


def _first_author_surname_from_bib(authors_text: str) -> str:
    text = _clean_latex(authors_text)
    if not text:
        return ""
    first = text.split(" and ", 1)[0].strip()
    if "," in first:
        return first.split(",", 1)[0].strip().lower()
    parts = first.split()
    return parts[-1].strip().lower() if parts else ""


def _first_author_surname_from_crossref(message: dict[str, Any]) -> str:
    authors = message.get("author")
    if isinstance(authors, list) and authors:
        first = authors[0]
        family = _strip_ws(first.get("family"))
        if family:
            return family.lower()
        name = " ".join(part for part in [_strip_ws(first.get("given")), _strip_ws(first.get("family"))] if part)
        return name.split()[-1].lower() if name else ""
    return ""


def _first_author_surname_from_arxiv(entry: dict[str, Any]) -> str:
    authors = entry.get("authors")
    if isinstance(authors, list) and authors:
        name = _strip_ws(authors[0].get("name"))
        if "," in name:
            return name.split(",", 1)[0].strip().lower()
        parts = name.split()
        return parts[-1].lower() if parts else ""
    return ""


def _year_from_string(value: str) -> str:
    match = re.search(r"(19|20)\d{2}", _strip_ws(value))
    return match.group(0) if match else ""


def _year_from_crossref(message: dict[str, Any]) -> str:
    for field in ("issued", "published-print", "published-online", "created"):
        part = message.get(field)
        if not isinstance(part, dict):
            continue
        date_parts = part.get("date-parts")
        if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
            return str(date_parts[0][0])
    return ""


def _published_date_from_crossref(message: dict[str, Any]) -> str:
    for field in ("published-online", "published-print", "issued", "created"):
        part = message.get(field)
        if not isinstance(part, dict):
            continue
        date_parts = part.get("date-parts")
        if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
            return "-".join(str(x) for x in date_parts[0])
    return ""


def _strip_html(text: str) -> str:
    if not text:
        return ""
    cleaned = HTML_TAG_RE.sub(" ", html.unescape(text))
    return NON_ASCII_SPACE_RE.sub(" ", cleaned).strip()


def _request(url: str, *, accept_json: bool = False, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if accept_json:
        request.add_header("Accept", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp_path.replace(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    tmp_path.replace(path)


def _is_valid_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < MIN_VALID_PDF_BYTES:
        return False
    with path.open("rb") as handle:
        header = handle.read(5)
    return header == b"%PDF-"


def _copy_pdf(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return _is_valid_pdf(dst)


def _symlink_pdf(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    rel_target = os.path.relpath(src, start=dst.parent)
    dst.symlink_to(rel_target)
    return dst.is_symlink() and _is_valid_pdf(dst)


def _download_pdf(url: str, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dst.with_suffix(dst.suffix + ".tmp")
    data = _request(url, timeout=60)
    with tmp_path.open("wb") as handle:
        handle.write(data)
    tmp_path.replace(dst)
    return _is_valid_pdf(dst)


def _load_worklist(pool_json_path: Path) -> list[WorkItem]:
    data = json.loads(pool_json_path.read_text(encoding="utf-8"))
    worklist: list[WorkItem] = []
    for row in data:
        worklist.append(
            WorkItem(
                record_index=int(row["record_index"]),
                record_id=_strip_ws(row["record_id"]),
                emitted_key=_emitted_key(_strip_ws(row["source_file"]), _strip_ws(row["key"])),
                pool_key=_strip_ws(row["key"]),
                source_family=_strip_ws(row["source_family"]),
                source_segment=_strip_ws(row["source_segment"]),
                source_file=_strip_ws(row["source_file"]),
                entry_type=_strip_ws(row["entry_type"]),
                title_from_pool=_clean_latex(_strip_ws(row["title"])),
                normalized_pool_title=normalize_title(_clean_latex(_strip_ws(row["title"]))),
                year_from_pool=_year_from_string(_strip_ws(row["year"])),
                authors_from_pool=_clean_latex(_strip_ws(row["authors"])),
                doi_from_pool=_normalize_doi(_strip_ws(row["doi"])),
                url_from_pool=_strip_ws(row["url"]),
                eprint_from_pool=_strip_arxiv_version(_extract_arxiv_id(_strip_ws(row["eprint"]))),
                archiveprefix_from_pool=_strip_ws(row["archiveprefix"]),
                abstract_from_pool=_clean_latex(_strip_ws(row["abstract"])),
            )
        )
    return sorted(worklist, key=lambda item: item.record_index)


def _main_pdf_map(main_pdf_dir: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in sorted(main_pdf_dir.glob("*.pdf")):
        if path.name.startswith("._"):
            continue
        mapping[path.stem] = path
    return mapping


def _extract_source_metadata_identifiers(full_metadata_row: dict[str, Any] | None) -> tuple[set[str], set[str]]:
    doi_values: set[str] = set()
    arxiv_values: set[str] = set()
    if not isinstance(full_metadata_row, dict):
        return doi_values, arxiv_values
    source_id = _strip_ws(full_metadata_row.get("source_id"))
    if source_id:
        doi = _normalize_doi(source_id)
        if doi:
            doi_values.add(doi)
        arxiv_id = _strip_arxiv_version(_extract_arxiv_id(source_id))
        if arxiv_id:
            arxiv_values.add(arxiv_id)
    source_metadata = full_metadata_row.get("source_metadata")
    if isinstance(source_metadata, dict):
        doi_candidates = [
            _strip_ws(source_metadata.get("doi")),
            _strip_ws(source_metadata.get("DOI")),
        ]
        for candidate in doi_candidates:
            normalized = _normalize_doi(candidate)
            if normalized:
                doi_values.add(normalized)
        authors = source_metadata.get("externalIds")
        if isinstance(authors, dict):
            normalized = _normalize_doi(_strip_ws(authors.get("DOI")))
            if normalized:
                doi_values.add(normalized)
            arxiv_id = _strip_arxiv_version(_extract_arxiv_id(_strip_ws(authors.get("ArXiv"))))
            if arxiv_id:
                arxiv_values.add(arxiv_id)
        for key in ("id", "url", "pdf_url"):
            arxiv_id = _strip_arxiv_version(_extract_arxiv_id(_strip_ws(source_metadata.get(key))))
            if arxiv_id:
                arxiv_values.add(arxiv_id)
    return doi_values, arxiv_values


def _load_main_context() -> tuple[dict[str, MainRecord], dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    refs_dir = REPO_ROOT / "refs" / PAPER_ID
    metadata_rows = {row["key"]: row for row in _load_jsonl(refs_dir / "metadata" / "title_abstracts_metadata.jsonl")}
    sources_rows = {row["key"]: row for row in _load_jsonl(refs_dir / "metadata" / "title_abstracts_sources.jsonl")}
    trace_rows = {row["key"]: row for row in _load_jsonl(refs_dir / "metadata" / "title_abstracts_source_trace.jsonl")}
    full_rows = {row["key"]: row for row in _load_jsonl(refs_dir / "metadata" / "title_abstracts_full_metadata.jsonl")}
    annotated_rows = {row["key"]: bool(row["is_evidence_base"]) for row in _load_jsonl(refs_dir / "metadata" / "title_abstracts_metadata-annotated.jsonl")}

    bib_entries = {
        entry.key: entry.fields
        for entry in parse_bibtex((REPO_ROOT / "bib" / "per_SR" / f"{PAPER_ID}.bib").read_text(encoding="utf-8"))
        if entry.key
    }
    pdf_map = _main_pdf_map(refs_dir / "pdfs")

    records: dict[str, MainRecord] = {}
    title_index: dict[str, list[str]] = defaultdict(list)
    doi_index: dict[str, list[str]] = defaultdict(list)
    arxiv_index: dict[str, list[str]] = defaultdict(list)

    for key, metadata in metadata_rows.items():
        main_record = MainRecord(
            key=key,
            metadata=metadata,
            sources=sources_rows.get(key),
            trace=trace_rows.get(key),
            full_metadata=full_rows.get(key),
            bib_fields=copy.deepcopy(bib_entries.get(key, {})),
            pdf_path=pdf_map.get(key),
            is_evidence_base=annotated_rows.get(key, False),
        )
        records[key] = main_record
        normalized = normalize_title(_strip_ws(metadata.get("query_title") or metadata.get("title")))
        if normalized:
            title_index[normalized].append(key)

        bib_doi = _normalize_doi(main_record.bib_fields.get("doi", ""))
        if bib_doi:
            doi_index[bib_doi].append(key)

        source_dois, source_arxiv = _extract_source_metadata_identifiers(main_record.full_metadata)
        for doi in source_dois:
            doi_index[doi].append(key)
        bib_arxiv = _strip_arxiv_version(_extract_arxiv_id(main_record.bib_fields.get("url", ""), main_record.bib_fields.get("note", "")))
        if bib_arxiv:
            arxiv_index[bib_arxiv].append(key)
        for arxiv_id in source_arxiv:
            arxiv_index[arxiv_id].append(key)

    return records, title_index, doi_index, arxiv_index


def _match_main_record(
    item: WorkItem,
    main_records: dict[str, MainRecord],
    title_index: dict[str, list[str]],
    doi_index: dict[str, list[str]],
    arxiv_index: dict[str, list[str]],
) -> tuple[MainRecord | None, str]:
    manual_alias = MANUAL_MAIN_ALIASES.get(item.record_id)
    if manual_alias and manual_alias in main_records:
        return main_records[manual_alias], "manual_alias"

    if item.doi_from_pool and item.doi_from_pool in doi_index:
        candidates = doi_index[item.doi_from_pool]
        if len(candidates) == 1:
            return main_records[candidates[0]], "doi"

    pool_arxiv = _strip_arxiv_version(_extract_arxiv_id(item.eprint_from_pool, item.url_from_pool))
    if pool_arxiv and pool_arxiv in arxiv_index:
        candidates = arxiv_index[pool_arxiv]
        if len(candidates) == 1:
            return main_records[candidates[0]], "arxiv_id"

    title_candidates = title_index.get(item.normalized_pool_title, [])
    if len(title_candidates) == 1:
        return main_records[title_candidates[0]], "normalized_title"

    return None, ""


def _build_identifier_notes(item: WorkItem, main_record: MainRecord) -> tuple[bool, bool, str]:
    pool_identifiers = []
    if item.doi_from_pool:
        pool_identifiers.append(f"doi={item.doi_from_pool}")
    pool_arxiv = _strip_arxiv_version(_extract_arxiv_id(item.eprint_from_pool, item.url_from_pool))
    if pool_arxiv:
        pool_identifiers.append(f"arxiv={pool_arxiv}")
    if item.url_from_pool:
        pool_identifiers.append(f"url={item.url_from_pool}")

    bib_fields = main_record.bib_fields
    source_dois, source_arxiv = _extract_source_metadata_identifiers(main_record.full_metadata)
    main_identifiers = sorted(
        {
            value
            for value in [_normalize_doi(bib_fields.get("doi", "")), *list(source_dois)]
            if value
        }
    )
    main_arxiv_values = sorted(set(filter(None, [
        _strip_arxiv_version(_extract_arxiv_id(bib_fields.get("url", ""), bib_fields.get("note", ""))),
        *(_strip_arxiv_version(x) for x in source_arxiv),
    ])))
    has_pool_identifiers = bool(item.doi_from_pool or pool_arxiv)
    matched = False
    if item.doi_from_pool and item.doi_from_pool in source_dois:
        matched = True
    if item.doi_from_pool and _normalize_doi(bib_fields.get("doi", "")) == item.doi_from_pool:
        matched = True
    if pool_arxiv and pool_arxiv in main_arxiv_values:
        matched = True
    if not pool_identifiers:
        matched = True

    note = "pool_identifiers={pool}; main_identifiers={main_doi}; main_arxiv={main_arxiv}".format(
        pool=", ".join(pool_identifiers) or "none",
        main_doi=", ".join(main_identifiers) or "none",
        main_arxiv=", ".join(main_arxiv_values) or "none",
    )
    return matched, has_pool_identifiers, note


def _verify_main_record(item: WorkItem, main_record: MainRecord) -> tuple[bool, str]:
    final_title = _strip_ws(main_record.metadata.get("title") or main_record.metadata.get("query_title"))
    final_normalized_title = normalize_title(final_title)
    title_ok = item.normalized_pool_title == final_normalized_title
    title_overlap = 0.0
    if not title_ok and item.normalized_pool_title and final_normalized_title:
        pool_tokens = set(item.normalized_pool_title.split())
        final_tokens = set(final_normalized_title.split())
        title_overlap = len(pool_tokens & final_tokens) / max(len(pool_tokens | final_tokens), 1)
        title_ok = title_overlap >= 0.88

    pool_year = item.year_from_pool
    main_year = _year_from_string(_strip_ws(main_record.bib_fields.get("year") or main_record.metadata.get("published_date")))
    year_ok = (not pool_year) or (not main_year) or (pool_year == main_year)

    pool_author = _first_author_surname_from_pool(item.authors_from_pool)
    main_author = _first_author_surname_from_bib(main_record.bib_fields.get("author", ""))
    author_ok = (not pool_author) or (not main_author) or (pool_author == main_author)

    identifier_ok, has_pool_identifiers, identifier_note = _build_identifier_notes(item, main_record)

    ok = title_ok and author_ok and (year_ok or identifier_ok or not has_pool_identifiers)
    manual_alias_override = False
    if (
        not ok
        and item.record_id in MANUAL_MAIN_ALIASES
        and author_ok
        and year_ok
        and (title_ok or title_overlap >= 0.80)
    ):
        ok = True
        manual_alias_override = True
    note = (
        f"title_ok={title_ok}; title_overlap={title_overlap:.3f}; pool_year={pool_year or 'n/a'}; main_year={main_year or 'n/a'}; "
        f"year_exact={year_ok}; pool_first_author={pool_author or 'n/a'}; "
        f"main_first_author={main_author or 'n/a'}; author_ok={author_ok}; "
        f"identifier_ok={identifier_ok}; manual_alias_override={manual_alias_override}; {identifier_note}"
    )
    return ok, note


def _arxiv_api_query(*, arxiv_id: str | None = None, title: str | None = None) -> tuple[dict[str, Any] | None, list[str]]:
    steps: list[str] = []
    if arxiv_id:
        query_url = "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(arxiv_id)
        steps.append(f"arxiv_api:id:{arxiv_id}")
    elif title:
        search = f'ti:"{title}"'
        query_url = "https://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(search) + "&max_results=5"
        steps.append(f"arxiv_api:title_search:{title}")
    else:
        return None, steps

    try:
        raw = _request(query_url, timeout=30)
    except (urllib.error.URLError, TimeoutError) as exc:
        steps.append(f"arxiv_api:error:{type(exc).__name__}")
        if arxiv_id:
            fallback_row, fallback_steps = _arxiv_abs_page_query(arxiv_id)
            steps.extend(fallback_steps)
            return fallback_row, steps
        return None, steps

    root = ET.fromstring(raw)
    entries = root.findall("atom:entry", ATOM_NS)
    if not entries:
        steps.append("arxiv_api:no_entry")
        if arxiv_id:
            fallback_row, fallback_steps = _arxiv_abs_page_query(arxiv_id)
            steps.extend(fallback_steps)
            return fallback_row, steps
        return None, steps

    best: dict[str, Any] | None = None
    best_score = -1.0
    for entry in entries:
        title_text = _strip_ws(entry.findtext("atom:title", default="", namespaces=ATOM_NS))
        summary_text = _strip_ws(entry.findtext("atom:summary", default="", namespaces=ATOM_NS))
        published_text = _strip_ws(entry.findtext("atom:published", default="", namespaces=ATOM_NS))
        updated_text = _strip_ws(entry.findtext("atom:updated", default="", namespaces=ATOM_NS))
        entry_id = _strip_ws(entry.findtext("atom:id", default="", namespaces=ATOM_NS))
        authors = [{"name": _strip_ws(author.findtext("atom:name", default="", namespaces=ATOM_NS))} for author in entry.findall("atom:author", ATOM_NS)]
        links: list[dict[str, str]] = []
        pdf_url = ""
        for link in entry.findall("atom:link", ATOM_NS):
            href = _strip_ws(link.attrib.get("href"))
            rel = _strip_ws(link.attrib.get("rel"))
            type_value = _strip_ws(link.attrib.get("type"))
            title_attr = _strip_ws(link.attrib.get("title"))
            links.append({"href": href, "rel": rel, "type": type_value, "title": title_attr})
            if type_value == "application/pdf" or title_attr.lower() == "pdf":
                pdf_url = href
        parsed = {
            "id": entry_id,
            "title": title_text,
            "abstract": summary_text,
            "published": published_text,
            "updated": updated_text,
            "authors": authors,
            "links": links,
            "pdf_url": pdf_url or ("https://arxiv.org/pdf/" + _strip_arxiv_version(_extract_arxiv_id(entry_id)) + ".pdf" if entry_id else ""),
            "arxiv_id": _strip_arxiv_version(_extract_arxiv_id(entry_id)),
        }
        score = 1.0 if arxiv_id and parsed["arxiv_id"] == _strip_arxiv_version(arxiv_id) else 0.0
        if title and normalize_title(title_text) == normalize_title(title):
            score = max(score, 0.95)
        if title and not score:
            pool_title_norm = normalize_title(title)
            candidate_norm = normalize_title(title_text)
            if pool_title_norm and candidate_norm:
                overlap = len(set(pool_title_norm.split()) & set(candidate_norm.split())) / max(len(set(pool_title_norm.split()) | set(candidate_norm.split())), 1)
                score = overlap
        if score > best_score:
            best = parsed
            best_score = score

    if best is None:
        steps.append("arxiv_api:no_best_match")
        return None, steps

    steps.append(f"arxiv_api:best_score:{best_score:.3f}")
    return best, steps


def _meta_content_map(html_text: str) -> dict[str, list[str]]:
    meta_map: dict[str, list[str]] = defaultdict(list)
    for match in ARXIV_META_RE.finditer(html_text):
        meta_map[match.group("name").lower()].append(_strip_ws(html.unescape(match.group("content"))))
    return meta_map


def _normalize_meta_date(value: str) -> str:
    text = _strip_ws(value).replace("/", "-")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text + "-01"
    if re.fullmatch(r"\d{4}", text):
        return text + "-01-01"
    return text


def _arxiv_abs_page_query(arxiv_id: str) -> tuple[dict[str, Any] | None, list[str]]:
    steps = [f"arxiv_abs_html:id:{arxiv_id}"]
    url = f"https://arxiv.org/abs/{urllib.parse.quote(_strip_arxiv_version(arxiv_id))}"
    try:
        raw = _request(url, timeout=30)
    except (urllib.error.URLError, TimeoutError) as exc:
        steps.append(f"arxiv_abs_html:error:{type(exc).__name__}")
        return None, steps

    html_text = raw.decode("utf-8", errors="replace")
    meta_map = _meta_content_map(html_text)
    title = _strip_ws((meta_map.get("citation_title") or [""])[0])
    abstract = _strip_ws((meta_map.get("citation_abstract") or [""])[0])
    pdf_url = _strip_ws((meta_map.get("citation_pdf_url") or [""])[0]) or f"https://arxiv.org/pdf/{_strip_arxiv_version(arxiv_id)}.pdf"
    parsed_id = _strip_ws((meta_map.get("citation_arxiv_id") or [""])[0]) or _strip_arxiv_version(arxiv_id)
    published = _normalize_meta_date(_strip_ws((meta_map.get("citation_date") or [""])[0]))
    updated = _normalize_meta_date(_strip_ws((meta_map.get("citation_online_date") or [""])[0]))
    authors = [{"name": name} for name in meta_map.get("citation_author", []) if _strip_ws(name)]
    if not title:
        steps.append("arxiv_abs_html:missing_title")
        return None, steps
    steps.append("arxiv_abs_html:parsed")
    return {
        "id": url,
        "title": title,
        "abstract": abstract,
        "published": published,
        "updated": updated or published,
        "authors": authors,
        "links": [{"href": pdf_url, "rel": "related", "type": "application/pdf", "title": "pdf"}] if pdf_url else [],
        "pdf_url": pdf_url,
        "arxiv_id": _strip_arxiv_version(parsed_id),
    }, steps


def _verify_arxiv(item: WorkItem, arxiv_row: dict[str, Any]) -> tuple[bool, str]:
    final_title = _strip_ws(arxiv_row.get("title"))
    title_ok = item.normalized_pool_title == normalize_title(final_title)
    if not title_ok and item.normalized_pool_title and normalize_title(final_title):
        pool_tokens = set(item.normalized_pool_title.split())
        final_tokens = set(normalize_title(final_title).split())
        overlap = len(pool_tokens & final_tokens) / max(len(pool_tokens | final_tokens), 1)
        title_ok = overlap >= 0.92
    pool_year = item.year_from_pool
    arxiv_year = _year_from_string(_strip_ws(arxiv_row.get("published")))
    year_ok = (not pool_year) or (pool_year == arxiv_year)
    pool_author = _first_author_surname_from_pool(item.authors_from_pool)
    arxiv_author = _first_author_surname_from_arxiv(arxiv_row)
    author_ok = (not pool_author) or (pool_author == arxiv_author)
    pool_arxiv = _strip_arxiv_version(_extract_arxiv_id(item.eprint_from_pool, item.url_from_pool))
    arxiv_id = _strip_arxiv_version(_strip_ws(arxiv_row.get("arxiv_id")))
    identifier_ok = (not pool_arxiv) or (pool_arxiv == arxiv_id)

    ok = title_ok and year_ok and author_ok and identifier_ok
    note = (
        f"title_ok={title_ok}; pool_year={pool_year or 'n/a'}; arxiv_year={arxiv_year or 'n/a'}; "
        f"year_ok={year_ok}; pool_first_author={pool_author or 'n/a'}; "
        f"arxiv_first_author={arxiv_author or 'n/a'}; author_ok={author_ok}; "
        f"pool_arxiv={pool_arxiv or 'n/a'}; arxiv_id={arxiv_id or 'n/a'}; identifier_ok={identifier_ok}"
    )
    return ok, note


def _crossref_query(doi: str) -> tuple[dict[str, Any] | None, list[str]]:
    steps = [f"crossref:doi:{doi}"]
    if not doi:
        steps.append("crossref:no_doi")
        return None, steps
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        raw = _request(url, accept_json=True, timeout=30)
    except (urllib.error.URLError, TimeoutError) as exc:
        steps.append(f"crossref:error:{type(exc).__name__}")
        return None, steps
    payload = json.loads(raw)
    message = payload.get("message")
    if not isinstance(message, dict):
        steps.append("crossref:missing_message")
        return None, steps
    steps.append("crossref:ok")
    return message, steps


def _verify_crossref(item: WorkItem, message: dict[str, Any]) -> tuple[bool, str]:
    titles = message.get("title")
    final_title = _strip_ws(titles[0] if isinstance(titles, list) and titles else "")
    title_ok = normalize_title(final_title) == item.normalized_pool_title
    pool_year = item.year_from_pool
    crossref_year = _year_from_crossref(message)
    year_ok = (not pool_year) or (not crossref_year) or (pool_year == crossref_year)
    pool_author = _first_author_surname_from_pool(item.authors_from_pool)
    crossref_author = _first_author_surname_from_crossref(message)
    author_ok = (not pool_author) or (not crossref_author) or (pool_author == crossref_author)
    doi_ok = (not item.doi_from_pool) or (_normalize_doi(_strip_ws(message.get("DOI"))) == item.doi_from_pool)

    ok = title_ok and year_ok and author_ok and doi_ok
    note = (
        f"title_ok={title_ok}; pool_year={pool_year or 'n/a'}; crossref_year={crossref_year or 'n/a'}; "
        f"year_ok={year_ok}; pool_first_author={pool_author or 'n/a'}; "
        f"crossref_first_author={crossref_author or 'n/a'}; author_ok={author_ok}; doi_ok={doi_ok}"
    )
    return ok, note


def _metadata_row_from_main(item: WorkItem, main_record: MainRecord) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    metadata_row = copy.deepcopy(main_record.metadata)
    metadata_row["key"] = item.emitted_key
    metadata_row["query_title"] = item.title_from_pool
    metadata_row["normalized_title"] = item.normalized_pool_title

    sources_row = copy.deepcopy(main_record.sources or {})
    sources_row["key"] = item.emitted_key
    sources_row["title"] = metadata_row.get("title") or metadata_row.get("query_title")
    sources_row["source"] = metadata_row.get("source")
    sources_row["source_id"] = metadata_row.get("source_id")
    sources_row["match_status"] = metadata_row.get("match_status")
    sources_row["abstract_present"] = bool(_strip_ws(metadata_row.get("abstract")))

    trace_row = copy.deepcopy(main_record.trace or {})
    trace_steps = list(trace_row.get("lookup_steps", [])) if isinstance(trace_row.get("lookup_steps"), list) else []
    trace_steps.append(f"candidate_pool:copied_from_main:{main_record.key}")
    trace_row = {"key": item.emitted_key, "lookup_steps": trace_steps}

    full_row = copy.deepcopy(main_record.full_metadata or {})
    full_row["key"] = item.emitted_key
    full_row["title"] = metadata_row.get("title") or metadata_row.get("query_title")
    full_row["source"] = metadata_row.get("source")
    full_row["source_id"] = metadata_row.get("source_id")
    full_row["match_status"] = metadata_row.get("match_status")
    full_row["source_metadata"] = copy.deepcopy((main_record.full_metadata or {}).get("source_metadata", {}))
    return metadata_row, sources_row, trace_row, full_row


def _metadata_row_from_arxiv(item: WorkItem, arxiv_row: dict[str, Any], trace_steps: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    title = _strip_ws(arxiv_row.get("title")) or item.title_from_pool
    abstract = _strip_ws(arxiv_row.get("abstract"))
    source_id = f"https://arxiv.org/abs/{_strip_arxiv_version(_strip_ws(arxiv_row.get('arxiv_id')))}" if _strip_ws(arxiv_row.get("arxiv_id")) else _strip_ws(arxiv_row.get("id"))
    published = _strip_ws(arxiv_row.get("published"))
    published_date = "-".join(published.split("T", 1)[0].split("-")[:2]) if published else (item.year_from_pool or None)

    metadata_row = {
        "key": item.emitted_key,
        "query_title": item.title_from_pool,
        "normalized_title": item.normalized_pool_title,
        "title": title,
        "abstract": abstract or None,
        "source": "arxiv",
        "source_id": source_id,
        "match_status": "exact_id" if item.eprint_from_pool else "exact_title",
        "missing_reason": None if abstract else "no_abstract_available",
        "published_date": published_date,
    }
    sources_row = {
        "key": item.emitted_key,
        "title": title,
        "source": "arxiv",
        "source_id": source_id,
        "match_status": metadata_row["match_status"],
        "abstract_present": bool(abstract),
        "abstract_source": "arxiv" if abstract else "missing",
        "abstract_source_reason": "arxiv:exact_id" if item.eprint_from_pool else ("arxiv:exact_title" if abstract else "missing:no_abstract_available"),
    }
    trace_row = {"key": item.emitted_key, "lookup_steps": trace_steps}
    full_row = {
        "key": item.emitted_key,
        "title": title,
        "source": "arxiv",
        "source_id": source_id,
        "match_status": metadata_row["match_status"],
        "source_metadata": {
            "id": _strip_ws(arxiv_row.get("id")),
            "title": title,
            "abstract": abstract or None,
            "published": published or None,
            "updated": _strip_ws(arxiv_row.get("updated")) or None,
            "authors": copy.deepcopy(arxiv_row.get("authors", [])),
            "links": copy.deepcopy(arxiv_row.get("links", [])),
            "pdf_url": _strip_ws(arxiv_row.get("pdf_url")),
            "arxiv_id": _strip_ws(arxiv_row.get("arxiv_id")),
        },
    }
    return metadata_row, sources_row, trace_row, full_row


def _metadata_row_from_crossref(item: WorkItem, message: dict[str, Any], trace_steps: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    titles = message.get("title")
    title = _strip_ws(titles[0] if isinstance(titles, list) and titles else "") or item.title_from_pool
    abstract = _strip_html(_strip_ws(message.get("abstract")))
    doi = _normalize_doi(_strip_ws(message.get("DOI"))) or item.doi_from_pool
    source_id = doi
    published_date = _published_date_from_crossref(message) or item.year_from_pool or None

    metadata_row = {
        "key": item.emitted_key,
        "query_title": item.title_from_pool,
        "normalized_title": item.normalized_pool_title,
        "title": title,
        "abstract": abstract or None,
        "source": "crossref",
        "source_id": source_id,
        "match_status": "exact_title",
        "missing_reason": None if abstract else "no_abstract_available",
        "published_date": published_date,
    }
    sources_row = {
        "key": item.emitted_key,
        "title": title,
        "source": "crossref",
        "source_id": source_id,
        "match_status": "exact_title",
        "abstract_present": bool(abstract),
        "abstract_source": "crossref" if abstract else "missing",
        "abstract_source_reason": "crossref:doi" if abstract else "missing:no_abstract_available",
    }
    trace_row = {"key": item.emitted_key, "lookup_steps": trace_steps}
    full_row = {
        "key": item.emitted_key,
        "title": title,
        "source": "crossref",
        "source_id": source_id,
        "match_status": "exact_title",
        "source_metadata": copy.deepcopy(message),
    }
    return metadata_row, sources_row, trace_row, full_row


def _verify_manual_source(item: WorkItem, manual_source: dict[str, Any]) -> tuple[bool, str]:
    final_title = _strip_ws(manual_source.get("verified_title"))
    title_ok = normalize_title(final_title) == item.normalized_pool_title
    title_overlap = 0.0
    if not title_ok and final_title and item.normalized_pool_title:
        pool_tokens = set(item.normalized_pool_title.split())
        final_tokens = set(normalize_title(final_title).split())
        title_overlap = len(pool_tokens & final_tokens) / max(len(pool_tokens | final_tokens), 1)
        title_ok = title_overlap >= 0.88

    pool_year = item.year_from_pool
    verified_year = _year_from_string(_strip_ws(str(manual_source.get("verified_year", ""))))
    year_ok = (not pool_year) or (not verified_year) or (pool_year == verified_year)

    pool_author = _first_author_surname_from_pool(item.authors_from_pool)
    verified_authors = manual_source.get("verified_authors")
    if isinstance(verified_authors, list):
        verified_author_text = "; ".join(_strip_ws(str(x)) for x in verified_authors if _strip_ws(str(x)))
    else:
        verified_author_text = _strip_ws(str(verified_authors or ""))
    verified_author = _first_author_surname_from_pool(verified_author_text)
    author_ok = (not pool_author) or (not verified_author) or (pool_author == verified_author)

    verified_doi = _normalize_doi(_strip_ws(str(manual_source.get("verified_doi", ""))))
    landing_url = _strip_ws(str(manual_source.get("landing_url", "")))
    pdf_url = _strip_ws(str(manual_source.get("pdf_url", "")))
    if item.doi_from_pool:
        identifier_ok = verified_doi == item.doi_from_pool
    elif item.url_from_pool:
        identifier_ok = item.url_from_pool in {landing_url, pdf_url}
    else:
        identifier_ok = True

    ok = title_ok and year_ok and author_ok and identifier_ok
    note = (
        f"title_ok={title_ok}; title_overlap={title_overlap:.3f}; pool_year={pool_year or 'n/a'}; "
        f"verified_year={verified_year or 'n/a'}; year_ok={year_ok}; pool_first_author={pool_author or 'n/a'}; "
        f"verified_first_author={verified_author or 'n/a'}; author_ok={author_ok}; identifier_ok={identifier_ok}; "
        f"verified_doi={verified_doi or 'n/a'}; landing_url={landing_url or 'n/a'}; pdf_url={pdf_url or 'n/a'}"
    )
    return ok, note


def _metadata_row_from_manual_source(item: WorkItem, manual_source: dict[str, Any], trace_steps: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    title = _strip_ws(str(manual_source.get("verified_title") or item.title_from_pool))
    abstract = _strip_ws(str(manual_source.get("abstract") or ""))
    source = _strip_ws(str(manual_source.get("source") or "manual_verified"))
    source_id = _strip_ws(
        str(
            manual_source.get("source_id")
            or manual_source.get("verified_doi")
            or manual_source.get("landing_url")
            or manual_source.get("pdf_url")
            or ""
        )
    )
    published_date = _strip_ws(str(manual_source.get("published_date") or manual_source.get("verified_year") or item.year_from_pool or ""))

    metadata_row = {
        "key": item.emitted_key,
        "query_title": item.title_from_pool,
        "normalized_title": item.normalized_pool_title,
        "title": title,
        "abstract": abstract or None,
        "source": source,
        "source_id": source_id,
        "match_status": "exact_title",
        "missing_reason": None if abstract else "no_abstract_available",
        "published_date": published_date or None,
    }
    sources_row = {
        "key": item.emitted_key,
        "title": title,
        "source": source,
        "source_id": source_id,
        "match_status": "exact_title",
        "abstract_present": bool(abstract),
        "abstract_source": source if abstract else "missing",
        "abstract_source_reason": f"{source}:manual_verified" if abstract else "missing:no_abstract_available",
    }
    trace_row = {"key": item.emitted_key, "lookup_steps": trace_steps}
    full_row = {
        "key": item.emitted_key,
        "title": title,
        "source": source,
        "source_id": source_id,
        "match_status": "exact_title",
        "source_metadata": copy.deepcopy(manual_source),
    }
    return metadata_row, sources_row, trace_row, full_row


def _missing_rows(item: WorkItem, *, missing_reason: str, trace_steps: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    metadata_row = {
        "key": item.emitted_key,
        "query_title": item.title_from_pool,
        "normalized_title": item.normalized_pool_title,
        "title": item.title_from_pool,
        "abstract": None,
        "source": "missing",
        "source_id": "",
        "match_status": "missing",
        "missing_reason": missing_reason,
        "published_date": item.year_from_pool or None,
    }
    sources_row = {
        "key": item.emitted_key,
        "title": item.title_from_pool,
        "source": "missing",
        "source_id": "",
        "match_status": "missing",
        "abstract_present": False,
        "abstract_source": "missing",
        "abstract_source_reason": f"missing:{missing_reason}",
    }
    trace_row = {"key": item.emitted_key, "lookup_steps": trace_steps + [f"missing:{missing_reason}"]}
    full_row = {
        "key": item.emitted_key,
        "title": item.title_from_pool,
        "source": "missing",
        "source_id": "",
        "match_status": "missing",
        "source_metadata": {},
    }
    return metadata_row, sources_row, trace_row, full_row


def _processing_log_row(
    item: WorkItem,
    *,
    final_matched_title: str | None,
    source_type: str,
    metadata_action: str,
    pdf_action: str,
    source_url_or_copy_from: str,
    manual_verification_note: str,
    matched_main_key: str | None = None,
    status_reason: str | None = None,
    evidence_base_source_key: str | None = None,
) -> dict[str, Any]:
    return {
        "record_index": item.record_index,
        "record_id": item.record_id,
        "emitted_key": item.emitted_key,
        "pool_entry_key": item.pool_key,
        "title_from_pool": item.title_from_pool,
        "final_matched_title": final_matched_title,
        "source_family": item.source_family,
        "source_segment": item.source_segment,
        "source_file": item.source_file,
        "source_type": source_type,
        "metadata_action": metadata_action,
        "pdf_action": pdf_action,
        "source_url_or_copy_from": source_url_or_copy_from,
        "manual_verification_note": manual_verification_note,
        "status_reason": status_reason,
        "matched_main_key": matched_main_key,
        "evidence_base_source_key": evidence_base_source_key,
        "pool_year": item.year_from_pool,
        "pool_authors": item.authors_from_pool,
        "pool_identifier": {
            "doi": item.doi_from_pool or None,
            "url": item.url_from_pool or None,
            "eprint": item.eprint_from_pool or None,
        },
    }


def _is_arxiv_item(item: WorkItem) -> bool:
    return item.source_family == "arxiv" or item.source_segment == "arxiv_clip"


def _has_direct_pdf_url(item: WorkItem) -> bool:
    url = item.url_from_pool.lower()
    return url.endswith(".pdf") or "/pdf" in url


def _reuse_main_record(
    item: WorkItem,
    matched: MainRecord,
    candidate_pdf_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    metadata_row, sources_row, trace_row, full_row = _metadata_row_from_main(item, matched)
    pdf_action = "missing"
    copy_from = ""
    verification_ok, verification_note = _verify_main_record(item, matched)
    if not verification_ok:
        metadata_row, sources_row, trace_row, full_row = _missing_rows(
            item,
            missing_reason="existing_main_verification_failed",
            trace_steps=list(trace_row.get("lookup_steps", [])),
        )
        log_row = _processing_log_row(
            item,
            final_matched_title=None,
            source_type="copied_existing",
            metadata_action="failed",
            pdf_action="failed",
            source_url_or_copy_from="",
            manual_verification_note=verification_note,
            matched_main_key=matched.key,
            status_reason="existing_main_verification_failed",
            evidence_base_source_key=matched.key if matched.is_evidence_base else None,
        )
        return metadata_row, sources_row, trace_row, full_row, log_row

    if matched.pdf_path and matched.pdf_path.exists():
        dst_pdf = candidate_pdf_dir / f"{item.emitted_key}.pdf"
        if _symlink_pdf(matched.pdf_path, dst_pdf):
            pdf_action = "copied"
            copy_from = str(matched.pdf_path)
            verification_note = f"{verification_note}; candidate_pdf_mode=symlink"
        else:
            pdf_action = "failed"
            copy_from = str(matched.pdf_path)
    final_title = _strip_ws(metadata_row.get("title"))
    log_row = _processing_log_row(
        item,
        final_matched_title=final_title,
        source_type="copied_existing",
        metadata_action="copied",
        pdf_action=pdf_action,
        source_url_or_copy_from=copy_from,
        manual_verification_note=verification_note,
        matched_main_key=matched.key,
        status_reason=None if pdf_action != "failed" else "copy_existing_pdf_invalid",
        evidence_base_source_key=matched.key if matched.is_evidence_base else None,
    )
    return metadata_row, sources_row, trace_row, full_row, log_row


def _process_arxiv_item(
    item: WorkItem,
    candidate_pdf_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    trace_steps: list[str] = []
    arxiv_id = _strip_arxiv_version(_extract_arxiv_id(item.eprint_from_pool, item.url_from_pool))
    arxiv_row, lookup_steps = _arxiv_api_query(arxiv_id=arxiv_id or None, title=item.title_from_pool if not arxiv_id else None)
    trace_steps.extend(lookup_steps)
    if arxiv_row is None and arxiv_id:
        arxiv_row, title_steps = _arxiv_api_query(title=item.title_from_pool)
        trace_steps.extend(title_steps)
    if arxiv_row is None:
        metadata_row, sources_row, trace_row, full_row = _missing_rows(
            item,
            missing_reason="arxiv_lookup_failed",
            trace_steps=trace_steps,
        )
        log_row = _processing_log_row(
            item,
            final_matched_title=None,
            source_type="arxiv",
            metadata_action="failed",
            pdf_action="failed",
            source_url_or_copy_from=item.url_from_pool,
            manual_verification_note="arXiv metadata lookup failed",
            status_reason="arxiv_lookup_failed",
        )
        return metadata_row, sources_row, trace_row, full_row, log_row

    verified, verification_note = _verify_arxiv(item, arxiv_row)
    if not verified:
        metadata_row, sources_row, trace_row, full_row = _missing_rows(
            item,
            missing_reason="arxiv_manual_verification_failed",
            trace_steps=trace_steps,
        )
        log_row = _processing_log_row(
            item,
            final_matched_title=None,
            source_type="arxiv",
            metadata_action="failed",
            pdf_action="failed",
            source_url_or_copy_from=_strip_ws(arxiv_row.get("id")),
            manual_verification_note=verification_note,
            status_reason="arxiv_manual_verification_failed",
        )
        return metadata_row, sources_row, trace_row, full_row, log_row

    trace_steps.append("arxiv:verified")
    metadata_row, sources_row, trace_row, full_row = _metadata_row_from_arxiv(item, arxiv_row, trace_steps)
    pdf_url = _strip_ws(arxiv_row.get("pdf_url"))
    pdf_action = "failed"
    dst_pdf = candidate_pdf_dir / f"{item.emitted_key}.pdf"
    if _is_valid_pdf(dst_pdf):
        pdf_action = "downloaded"
        verification_note = f"{verification_note}; candidate_pdf_reused=true"
    elif pdf_url:
        try:
            if _download_pdf(pdf_url, dst_pdf):
                pdf_action = "downloaded"
            else:
                pdf_action = "failed"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            pdf_action = "failed"
            verification_note = f"{verification_note}; pdf_download_error={type(exc).__name__}"

    log_row = _processing_log_row(
        item,
        final_matched_title=_strip_ws(metadata_row.get("title")),
        source_type="arxiv",
        metadata_action="downloaded",
        pdf_action=pdf_action,
        source_url_or_copy_from=pdf_url or _strip_ws(arxiv_row.get("id")),
        manual_verification_note=verification_note,
        status_reason=None if pdf_action == "downloaded" else "arxiv_pdf_download_failed",
    )
    return metadata_row, sources_row, trace_row, full_row, log_row


def _process_non_arxiv_manual(
    item: WorkItem,
    candidate_pdf_dir: Path,
    manual_sources: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    trace_steps: list[str] = []
    manual_source = manual_sources.get(item.record_id) if isinstance(manual_sources, dict) else None
    if isinstance(manual_source, dict):
        trace_steps.append("manual_source_map:hit")
        verified, verification_note = _verify_manual_source(item, manual_source)
        if verified:
            metadata_row, sources_row, trace_row, full_row = _metadata_row_from_manual_source(item, manual_source, trace_steps + ["manual_source_map:verified"])
            pdf_action = "missing"
            pdf_url = _strip_ws(str(manual_source.get("pdf_url", "")))
            landing_url = _strip_ws(str(manual_source.get("landing_url", "")))
            dst_pdf = candidate_pdf_dir / f"{item.emitted_key}.pdf"
            if _is_valid_pdf(dst_pdf):
                pdf_action = "downloaded"
                verification_note = f"{verification_note}; candidate_pdf_reused=true"
            elif pdf_url:
                try:
                    if _download_pdf(pdf_url, dst_pdf):
                        pdf_action = "downloaded"
                    else:
                        pdf_action = "failed"
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    pdf_action = "failed"
                    verification_note = f"{verification_note}; pdf_download_error={type(exc).__name__}"
            log_row = _processing_log_row(
                item,
                final_matched_title=_strip_ws(metadata_row.get("title")),
                source_type="non_arxiv_manual",
                metadata_action="downloaded",
                pdf_action=pdf_action,
                source_url_or_copy_from=pdf_url or landing_url,
                manual_verification_note=verification_note,
                status_reason=None if pdf_action in {"downloaded", "missing"} else "non_arxiv_pdf_download_failed",
            )
            return metadata_row, sources_row, trace_row, full_row, log_row

        metadata_row, sources_row, trace_row, full_row = _missing_rows(
            item,
            missing_reason="non_arxiv_manual_verification_failed",
            trace_steps=trace_steps,
        )
        log_row = _processing_log_row(
            item,
            final_matched_title=None,
            source_type="non_arxiv_manual",
            metadata_action="failed",
            pdf_action="failed",
            source_url_or_copy_from=_strip_ws(str(manual_source.get("landing_url") or manual_source.get("pdf_url") or "")),
            manual_verification_note=verification_note,
            status_reason="non_arxiv_manual_verification_failed",
        )
        return metadata_row, sources_row, trace_row, full_row, log_row

    if item.doi_from_pool:
        message, lookup_steps = _crossref_query(item.doi_from_pool)
        trace_steps.extend(lookup_steps)
        if message is not None:
            verified, verification_note = _verify_crossref(item, message)
            if verified:
                metadata_row, sources_row, trace_row, full_row = _metadata_row_from_crossref(item, message, trace_steps + ["crossref:verified"])
                pdf_action = "missing"
                download_source = item.url_from_pool or f"https://doi.org/{item.doi_from_pool}"
                dst_pdf = candidate_pdf_dir / f"{item.emitted_key}.pdf"
                if _is_valid_pdf(dst_pdf):
                    pdf_action = "downloaded"
                    verification_note = f"{verification_note}; candidate_pdf_reused=true"
                elif item.url_from_pool and _has_direct_pdf_url(item):
                    try:
                        if _download_pdf(item.url_from_pool, dst_pdf):
                            pdf_action = "downloaded"
                        else:
                            pdf_action = "failed"
                    except (urllib.error.URLError, TimeoutError, OSError) as exc:
                        pdf_action = "failed"
                        verification_note = f"{verification_note}; pdf_download_error={type(exc).__name__}"
                log_row = _processing_log_row(
                    item,
                    final_matched_title=_strip_ws(metadata_row.get("title")),
                    source_type="non_arxiv_manual",
                    metadata_action="downloaded",
                    pdf_action=pdf_action,
                    source_url_or_copy_from=download_source,
                    manual_verification_note=verification_note,
                    status_reason=None if pdf_action in {"downloaded", "missing"} else "non_arxiv_pdf_download_failed",
                )
                return metadata_row, sources_row, trace_row, full_row, log_row

            metadata_row, sources_row, trace_row, full_row = _missing_rows(
                item,
                missing_reason="non_arxiv_manual_verification_failed",
                trace_steps=trace_steps,
            )
            log_row = _processing_log_row(
                item,
                final_matched_title=None,
                source_type="non_arxiv_manual",
                metadata_action="failed",
                pdf_action="failed",
                source_url_or_copy_from=item.url_from_pool or f"https://doi.org/{item.doi_from_pool}",
                manual_verification_note=verification_note,
                status_reason="non_arxiv_manual_verification_failed",
            )
            return metadata_row, sources_row, trace_row, full_row, log_row

    metadata_row, sources_row, trace_row, full_row = _missing_rows(
        item,
        missing_reason="non_arxiv_manual_pending",
        trace_steps=trace_steps,
    )
    log_row = _processing_log_row(
        item,
        final_matched_title=None,
        source_type="non_arxiv_manual",
        metadata_action="skipped",
        pdf_action="missing",
        source_url_or_copy_from=item.url_from_pool or (f"https://doi.org/{item.doi_from_pool}" if item.doi_from_pool else ""),
        manual_verification_note="Manual non-arXiv verification/download pending; no safe direct source was auto-confirmed in this batch.",
        status_reason="non_arxiv_manual_pending",
    )
    return metadata_row, sources_row, trace_row, full_row, log_row


def _annotated_row(item: WorkItem, log_row: dict[str, Any], true_keys: set[str]) -> dict[str, Any]:
    evidence_source_key = _strip_ws(log_row.get("evidence_base_source_key"))
    return {
        "key": item.emitted_key,
        "is_evidence_base": evidence_source_key in true_keys,
    }


def _validate_outputs(metadata_rows: list[dict[str, Any]], sources_rows: list[dict[str, Any]], trace_rows: list[dict[str, Any]], full_rows: list[dict[str, Any]], annotated_rows: list[dict[str, Any]], candidate_pdf_dir: Path, log_rows: list[dict[str, Any]]) -> dict[str, Any]:
    key_order = [row["key"] for row in metadata_rows]
    validation = {
        "row_counts": {
            "metadata": len(metadata_rows),
            "sources": len(sources_rows),
            "trace": len(trace_rows),
            "full_metadata": len(full_rows),
            "annotated": len(annotated_rows),
            "processing_log": len(log_rows),
        },
        "unique_emitted_keys": len(set(key_order)),
        "all_row_orders_match": (
            key_order == [row["key"] for row in sources_rows]
            == [row["key"] for row in trace_rows]
            == [row["key"] for row in full_rows]
            == [row["key"] for row in annotated_rows]
        ),
        "valid_pdf_count": 0,
        "invalid_pdf_files": [],
    }
    for path in sorted(candidate_pdf_dir.glob("*.pdf")):
        if path.name.startswith("._"):
            continue
        if _is_valid_pdf(path):
            validation["valid_pdf_count"] += 1
        else:
            validation["invalid_pdf_files"].append(str(path))
    return validation


def _build_summary(
    worklist: list[WorkItem],
    log_rows: list[dict[str, Any]],
    annotated_rows: list[dict[str, Any]],
    validation: dict[str, Any],
) -> dict[str, Any]:
    by_source = Counter()
    copied_meta = 0
    copied_pdf = 0
    failures = Counter()
    arxiv_success = 0
    non_arxiv_success = 0

    for row in log_rows:
        source_type = row["source_type"]
        metadata_action = row["metadata_action"]
        pdf_action = row["pdf_action"]
        reason = _strip_ws(row.get("status_reason"))
        if metadata_action == "copied":
            copied_meta += 1
        if pdf_action == "copied":
            copied_pdf += 1
        if metadata_action == "failed" or pdf_action == "failed":
            failures[reason or "unspecified_failure"] += 1
        if source_type == "arxiv" and metadata_action in {"copied", "downloaded"} and pdf_action in {"copied", "downloaded"}:
            arxiv_success += 1
        if source_type == "non_arxiv_manual" and metadata_action in {"copied", "downloaded"} and pdf_action in {"copied", "downloaded"}:
            non_arxiv_success += 1
        by_source[source_type] += 1

    evidence_true_count = sum(1 for row in annotated_rows if row["is_evidence_base"])
    evidence_missing_from_pool = []
    if "zhou2021interactive" in EVIDENCE_BASE_EXPECTED_TRUE:
        mapped_source_keys = {row.get("evidence_base_source_key") for row in log_rows if row.get("evidence_base_source_key")}
        if "zhou2021interactive" not in mapped_source_keys:
            evidence_missing_from_pool.append(
                {
                    "main_key": "zhou2021interactive",
                    "title": "Interactive Exploration-Exploitation Balancing for Generative Melody Composition",
                    "reason": "Present in main review bibliography and arXiv_included.bib, but absent from the 521-pool source chain; pool only contains the 2020 precursor 'Generative melody composition with human-in-the-loop Bayesian optimization'.",
                }
            )

    return {
        "paper_id": PAPER_ID,
        "generated_at_epoch": int(time.time()),
        "worklist_size": len(worklist),
        "counts": {
            "arxiv_success": arxiv_success,
            "non_arxiv_success": non_arxiv_success,
            "copied_existing_metadata": copied_meta,
            "copied_existing_pdf": copied_pdf,
            "failed_rows": sum(failures.values()),
            "source_type_rows": dict(by_source),
        },
        "failure_reasons": dict(sorted(failures.items())),
        "evidence_base_audit": {
            "expected_true_count_main": len(EVIDENCE_BASE_EXPECTED_TRUE),
            "annotated_true_count_candidate_pool": evidence_true_count,
            "missing_from_pool": evidence_missing_from_pool,
            "manual_alias_notes": [
                "liao2024baton is represented in the pool as cited version liao_baton_2024 and is mapped to evidence_base=true.",
            ],
        },
        "validation": validation,
        "unresolved_items": [
            row for row in log_rows if row["metadata_action"] in {"failed", "skipped"} or row["pdf_action"] in {"failed", "missing"}
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-id", default=PAPER_ID)
    parser.add_argument("--resume", action="store_true", help="Reuse existing candidate-pool outputs/logs.")
    parser.add_argument(
        "--redo-actions",
        default="",
        help="Comma-separated processing actions to revisit from existing log (e.g. skipped,failed).",
    )
    parser.add_argument(
        "--arxiv-download-limit",
        type=int,
        default=None,
        help="Optional limit for new arXiv downloads in this run. Existing-copy matches are not counted.",
    )
    parser.add_argument(
        "--non-arxiv-download-limit",
        type=int,
        default=0,
        help="Optional limit for non-arXiv manual-download attempts in this run.",
    )
    args = parser.parse_args()

    if args.paper_id != PAPER_ID:
        raise SystemExit(f"This script is currently scoped to {PAPER_ID}.")

    candidate_root = REPO_ROOT / "refs" / PAPER_ID / "candidate_pool"
    metadata_dir = candidate_root / "metadata"
    pdf_dir = candidate_root / "pdfs"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    pool_json_path = candidate_root / "list" / "pool_521.json"
    worklist = _load_worklist(pool_json_path)

    main_records, title_index, doi_index, arxiv_index = _load_main_context()
    evidence_true_keys = {key for key, record in main_records.items() if record.is_evidence_base}
    manual_non_arxiv_sources = _load_json(candidate_root / "manual_non_arxiv_sources.json")

    existing_metadata = {row["key"]: row for row in _load_jsonl(metadata_dir / "title_abstracts_metadata.jsonl")} if args.resume else {}
    existing_sources = {row["key"]: row for row in _load_jsonl(metadata_dir / "title_abstracts_sources.jsonl")} if args.resume else {}
    existing_trace = {row["key"]: row for row in _load_jsonl(metadata_dir / "title_abstracts_source_trace.jsonl")} if args.resume else {}
    existing_full = {row["key"]: row for row in _load_jsonl(metadata_dir / "title_abstracts_full_metadata.jsonl")} if args.resume else {}
    existing_annotated = {row["key"]: row for row in _load_jsonl(metadata_dir / "title_abstracts_metadata-annotated.jsonl")} if args.resume else {}
    existing_log = {row["emitted_key"]: row for row in _load_jsonl(candidate_root / "processing_log.jsonl")} if args.resume else {}

    redo_actions = {part.strip() for part in args.redo_actions.split(",") if part.strip()}
    arxiv_downloads_used = 0
    non_arxiv_downloads_used = 0

    metadata_rows_out: list[dict[str, Any]] = []
    sources_rows_out: list[dict[str, Any]] = []
    trace_rows_out: list[dict[str, Any]] = []
    full_rows_out: list[dict[str, Any]] = []
    annotated_rows_out: list[dict[str, Any]] = []
    log_rows_out: list[dict[str, Any]] = []

    for item in worklist:
        existing_log_row = existing_log.get(item.emitted_key)
        if existing_log_row and existing_log_row.get("metadata_action") not in redo_actions and existing_log_row.get("pdf_action") not in redo_actions:
            metadata_rows_out.append(copy.deepcopy(existing_metadata[item.emitted_key]))
            sources_rows_out.append(copy.deepcopy(existing_sources[item.emitted_key]))
            trace_rows_out.append(copy.deepcopy(existing_trace[item.emitted_key]))
            full_rows_out.append(copy.deepcopy(existing_full[item.emitted_key]))
            annotated_rows_out.append(copy.deepcopy(existing_annotated[item.emitted_key]))
            log_rows_out.append(copy.deepcopy(existing_log_row))
            continue

        matched_main, match_reason = _match_main_record(item, main_records, title_index, doi_index, arxiv_index)
        if matched_main is not None and matched_main.pdf_path and matched_main.pdf_path.exists():
            metadata_row, sources_row, trace_row, full_row, log_row = _reuse_main_record(item, matched_main, pdf_dir)
            if match_reason:
                trace_row["lookup_steps"].append(f"main_match:{match_reason}")
        elif _is_arxiv_item(item):
            if args.arxiv_download_limit is not None and arxiv_downloads_used >= args.arxiv_download_limit:
                metadata_row, sources_row, trace_row, full_row = _missing_rows(
                    item,
                    missing_reason="arxiv_batch_pending",
                    trace_steps=["arxiv:batch_pending"],
                )
                log_row = _processing_log_row(
                    item,
                    final_matched_title=None,
                    source_type="arxiv",
                    metadata_action="skipped",
                    pdf_action="missing",
                    source_url_or_copy_from=item.url_from_pool,
                    manual_verification_note="ArXiv batch limit reached; deferred to next resumable run.",
                    status_reason="arxiv_batch_pending",
                )
            else:
                metadata_row, sources_row, trace_row, full_row, log_row = _process_arxiv_item(item, pdf_dir)
                if log_row["metadata_action"] == "downloaded":
                    arxiv_downloads_used += 1
        else:
            if args.non_arxiv_download_limit is not None and non_arxiv_downloads_used >= args.non_arxiv_download_limit:
                metadata_row, sources_row, trace_row, full_row = _missing_rows(
                    item,
                    missing_reason="non_arxiv_manual_pending",
                    trace_steps=["non_arxiv:batch_pending"],
                )
                log_row = _processing_log_row(
                    item,
                    final_matched_title=None,
                    source_type="non_arxiv_manual",
                    metadata_action="skipped",
                    pdf_action="missing",
                    source_url_or_copy_from=item.url_from_pool or (f"https://doi.org/{item.doi_from_pool}" if item.doi_from_pool else ""),
                    manual_verification_note="Non-arXiv manual batch not started in this run.",
                    status_reason="non_arxiv_manual_pending",
                )
            else:
                metadata_row, sources_row, trace_row, full_row, log_row = _process_non_arxiv_manual(item, pdf_dir, manual_non_arxiv_sources)
                if log_row["metadata_action"] == "downloaded":
                    non_arxiv_downloads_used += 1

        annotated_row = _annotated_row(item, log_row, evidence_true_keys)

        metadata_rows_out.append(metadata_row)
        sources_rows_out.append(sources_row)
        trace_rows_out.append(trace_row)
        full_rows_out.append(full_row)
        annotated_rows_out.append(annotated_row)
        log_rows_out.append(log_row)

    _write_jsonl(metadata_dir / "title_abstracts_metadata.jsonl", metadata_rows_out)
    _write_jsonl(metadata_dir / "title_abstracts_sources.jsonl", sources_rows_out)
    _write_jsonl(metadata_dir / "title_abstracts_source_trace.jsonl", trace_rows_out)
    _write_jsonl(metadata_dir / "title_abstracts_full_metadata.jsonl", full_rows_out)
    _write_jsonl(metadata_dir / "title_abstracts_metadata-annotated.jsonl", annotated_rows_out)
    _write_jsonl(candidate_root / "processing_log.jsonl", log_rows_out)

    validation = _validate_outputs(
        metadata_rows_out,
        sources_rows_out,
        trace_rows_out,
        full_rows_out,
        annotated_rows_out,
        pdf_dir,
        log_rows_out,
    )
    summary = _build_summary(worklist, log_rows_out, annotated_rows_out, validation)
    _write_json(candidate_root / "processing_summary.json", summary)

    print(
        "candidate-pool backfill complete: rows={rows}, arxiv_downloads={arxiv}, non_arxiv_downloads={non_arxiv}, valid_pdfs={pdfs}".format(
            rows=len(worklist),
            arxiv=arxiv_downloads_used,
            non_arxiv=non_arxiv_downloads_used,
            pdfs=validation["valid_pdf_count"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
