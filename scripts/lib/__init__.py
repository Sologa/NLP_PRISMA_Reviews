"""Shared helpers for PRISMA bibliography processing scripts."""

from .bib_parser import BibEntry, BibTexError, parse_bibtex  # noqa: F401
from .title_normalizer import normalize_title  # noqa: F401
from .note_parser import (
    extract_doi_from_text,
    extract_title_from_note,
    normalize_author_block,
    parse_note_to_fields,
)  # noqa: F401
from .crossref_client import CrossrefCache, fetch_crossref_metadata  # noqa: F401

__all__ = [
    "BibEntry",
    "BibTexError",
    "parse_bibtex",
    "normalize_title",
    "extract_doi_from_text",
    "extract_title_from_note",
    "normalize_author_block",
    "parse_note_to_fields",
    "CrossrefCache",
    "fetch_crossref_metadata",
]
