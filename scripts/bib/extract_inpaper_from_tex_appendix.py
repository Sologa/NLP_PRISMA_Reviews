#!/usr/bin/env python3
"""Extract included-study rows from a TeX appendix enumerate list.

This script targets SR papers that enumerate included works inside ``main.tex``
appendix sections (for example, ``2307.05527``). It matches each appendix item
to a BibTeX key by title, handling:

- quoted titles (``“...”`` / ``"..."``)
- unquoted title items (``Author. Title. Month Year.``)
- dehyphen artifacts from line breaks (``text-to- speech``)
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.bib_parser import parse_bibtex


def _normalize_title(text: str) -> str:
    s = text or ""
    s = s.replace("“", '"').replace("”", '"').replace("’", "'")
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("\\&", "&")
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"([A-Za-z])-\s+([A-Za-z])", r"\1-\2", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _extract_items(tex_text: str, section_title: str) -> List[str]:
    lines = tex_text.splitlines()
    section_pat = re.compile(rf"\\section\{{\s*{re.escape(section_title)}\s*\}}")
    section_idx = next((i for i, line in enumerate(lines) if section_pat.search(line)), None)
    if section_idx is None:
        raise ValueError(f"section not found: {section_title}")

    begin_idx = None
    for i in range(section_idx + 1, len(lines)):
        if lines[i].strip().startswith("\\begin{enumerate}"):
            begin_idx = i
            break
    if begin_idx is None:
        raise ValueError("enumerate block not found after section")

    items: List[str] = []
    current: List[str] = []
    in_enum = True
    for i in range(begin_idx + 1, len(lines)):
        raw = lines[i].strip()
        if raw == "\\end{enumerate}":
            if current:
                items.append(" ".join(" ".join(current).split()))
            in_enum = False
            break
        if raw.startswith("\\item"):
            if current:
                items.append(" ".join(" ".join(current).split()))
            current = [raw[len("\\item") :].strip()]
        elif current:
            current.append(raw)

    if in_enum:
        raise ValueError("enumerate block not closed")
    return items


def _extract_item_title(item: str) -> tuple[Optional[str], str]:
    quoted = re.search(r'[“"]([^”"]+)[”"]', item)
    if quoted:
        return quoted.group(1).strip(), "quoted"

    # Typical unquoted style: "Author list. Title. Month Year."
    parts = [p.strip() for p in re.split(r"\.\s+", item) if p.strip()]
    if len(parts) >= 2:
        return parts[1].strip(" ."), "unquoted"
    return None, "none"


def _load_bib_title_map(bib_path: Path) -> tuple[dict[str, str], dict[str, List[str]]]:
    entries = parse_bibtex(bib_path.read_text(encoding="utf-8", errors="ignore"))
    key_to_title: dict[str, str] = {}
    norm_to_keys: dict[str, List[str]] = {}
    for entry in entries:
        key = (entry.key or "").strip()
        if not key:
            continue
        title = (entry.fields.get("title") or "").strip()
        if not title:
            continue
        title = " ".join(title.split()).replace("{", "").replace("}", "")
        key_to_title[key] = title
        norm = _normalize_title(title)
        norm_to_keys.setdefault(norm, []).append(key)
    return key_to_title, norm_to_keys


def _fuzzy_match_key(
    title: str,
    key_to_title: dict[str, str],
    min_similarity: float,
) -> tuple[Optional[str], float]:
    norm_title = _normalize_title(title)
    best_key = None
    best_score = 0.0
    for key, bib_title in key_to_title.items():
        score = difflib.SequenceMatcher(None, norm_title, _normalize_title(bib_title)).ratio()
        if score > best_score:
            best_score = score
            best_key = key
    if best_key and best_score >= min_similarity:
        return best_key, best_score
    return None, best_score


def _build_rows(
    items: Iterable[str],
    key_to_title: dict[str, str],
    norm_to_keys: dict[str, List[str]],
    min_similarity: float,
    sr_arxiv: str,
) -> List[dict]:
    rows: List[dict] = []
    for item in items:
        title, parse_mode = _extract_item_title(item)
        if not title:
            rows.append(
                {
                    "bibkey": None,
                    "title": None,
                    "match_confidence": "none",
                    "score": 0.0,
                    "method": "appendix item parse failed: no title",
                    "sr_arxiv": sr_arxiv,
                }
            )
            continue

        norm_title = _normalize_title(title)
        keys = norm_to_keys.get(norm_title, [])
        if len(keys) == 1:
            key = keys[0]
            rows.append(
                {
                    "bibkey": key,
                    "title": key_to_title[key],
                    "match_confidence": "high",
                    "score": 1.0,
                    "method": f"appendix item title->bibkey exact match ({parse_mode})",
                    "sr_arxiv": sr_arxiv,
                }
            )
            continue

        match_key, score = _fuzzy_match_key(title, key_to_title, min_similarity=min_similarity)
        if match_key:
            conf = "high" if score >= 0.95 else "low"
            rows.append(
                {
                    "bibkey": match_key,
                    "title": key_to_title[match_key],
                    "match_confidence": conf,
                    "score": round(score, 3),
                    "method": f"appendix item title->bibkey fuzzy match ({parse_mode})",
                    "sr_arxiv": sr_arxiv,
                }
            )
        else:
            rows.append(
                {
                    "bibkey": None,
                    "title": title,
                    "match_confidence": "none",
                    "score": round(score, 3),
                    "method": f"appendix item title->bibkey no match ({parse_mode})",
                    "sr_arxiv": sr_arxiv,
                }
            )
    return rows


def _write_outputs(rows: List[dict], jsonl_path: Path, csv_path: Path) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    jsonl_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )

    cols = ["bibkey", "title", "match_confidence", "score", "method", "sr_arxiv"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col) for col in cols})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tex-path", type=Path, required=True)
    parser.add_argument("--bib-path", type=Path, required=True)
    parser.add_argument("--section-title", type=str, default="References for Works Included in Systematic Literature Review")
    parser.add_argument("--sr-arxiv", type=str, required=True)
    parser.add_argument("--out-jsonl", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--min-similarity", type=float, default=0.9)
    args = parser.parse_args()

    items = _extract_items(args.tex_path.read_text(encoding="utf-8", errors="ignore"), args.section_title)
    key_to_title, norm_to_keys = _load_bib_title_map(args.bib_path)
    rows = _build_rows(
        items,
        key_to_title,
        norm_to_keys,
        min_similarity=args.min_similarity,
        sr_arxiv=args.sr_arxiv,
    )
    _write_outputs(rows, args.out_jsonl, args.out_csv)

    total = len(rows)
    with_key = sum(1 for row in rows if row.get("bibkey"))
    print(f"[done] rows={total}, with_bibkey={with_key}, null_bibkey={total - with_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
