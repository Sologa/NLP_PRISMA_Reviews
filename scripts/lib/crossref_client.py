#!/usr/bin/env python3
"""Crossref helper used by per-SR cleaned BibTeX reconstruction."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional


class CrossrefCache:
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.payload: Dict[str, Dict[str, object]] = {}
        self._load()

    def _load(self) -> None:
        if not self.cache_path.exists():
            self.payload = {}
            return
        try:
            with self.cache_path.open("r", encoding="utf-8") as handle:
                self.payload = json.load(handle)
        except Exception:
            self.payload = {}

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("w", encoding="utf-8") as handle:
            json.dump(self.payload, handle, ensure_ascii=True, indent=2)

    def get(self, doi: str) -> Optional[Dict[str, object]]:
        return self.payload.get(self._normalize_key(doi))

    def set(self, doi: str, record: Dict[str, object]) -> None:
        self.payload[self._normalize_key(doi)] = {
            **record,
            "_cached_at": int(time.time()),
        }

    @staticmethod
    def _normalize_key(doi: str) -> str:
        return doi.lower().strip()


def _coerce_str_list(value) -> str:
    if isinstance(value, list):
        return value[0] if value else ""
    return str(value) if value else ""


def fetch_crossref_metadata(doi: str, *, cache: CrossrefCache) -> Optional[Dict[str, object]]:
    if not doi:
        return None

    norm_doi = cache._normalize_key(doi)
    cached = cache.get(norm_doi)
    if cached:
        return cached

    quoted = urllib.parse.quote(norm_doi, safe="")
    url = f"https://api.crossref.org/works/{quoted}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "bib-note-parser/1.0 (mailto:example@example.com)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="ignore")
            data = json.loads(raw)
            msg = data.get("message", {}) if isinstance(data, dict) else {}

            record: Dict[str, object] = {
                "title": _coerce_str_list(msg.get("title")) if isinstance(msg, dict) else "",
                "journal": _coerce_str_list(msg.get("container-title")) if isinstance(msg, dict) else "",
                "volume": msg.get("volume", "") or "",
                "number": msg.get("issue", "") or "",
                "pages": msg.get("page", "") or msg.get("article-number", "") or "",
                "year": "",
                "doi": msg.get("DOI", "") or norm_doi,
                "url": msg.get("URL", "") or "",
                "author": "",
            }

            if isinstance(msg, dict):
                issued = msg.get("issued", {}) or msg.get("published-print", {}) or msg.get("published-online", {})
                if isinstance(issued, dict):
                    date_parts = issued.get("date-parts", [])
                    if date_parts:
                        try:
                            record["year"] = str(date_parts[0][0])
                        except Exception:
                            pass

                authors: List[str] = []
                for a in msg.get("author", []) if isinstance(msg.get("author"), list) else []:
                    family = a.get("family", "").strip()
                    given = a.get("given", "").strip()
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                if authors:
                    record["author"] = " and ".join(authors)

            cache.set(norm_doi, record)
            cache.save()
            return record
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    except Exception:
        return None
