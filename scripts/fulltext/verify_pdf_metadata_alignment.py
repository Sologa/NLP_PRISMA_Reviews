#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    import fitz  # PyMuPDF
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "PyMuPDF (fitz) is required. Install with: pip install pymupdf\n"
        f"Import error: {exc}"
    )

try:
    fitz.TOOLS.mupdf_display_errors(False)
except Exception:
    pass


SIMILARITY_THRESHOLD = 0.90
ABSTRACT_PREFIX_LEN = 220
MIN_READABLE_TEXT_LEN = 120
MIN_READABLE_RATIO = 0.75


@dataclass
class MetadataRow:
    paper_id: str
    key: str
    title: str
    abstract: str


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sanitize_field(text: str, max_chars: int = 20000) -> str:
    text = text or ""
    text = text.replace("\x00", " ").strip()
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def is_text_quality_low(text: str) -> bool:
    if not text or len(text.strip()) < MIN_READABLE_TEXT_LEN:
        return True
    printable = sum(1 for ch in text if ch.isprintable() and ch not in "\x0b\x0c")
    ratio = printable / max(len(text), 1)
    return ratio < MIN_READABLE_RATIO


def list_metadata_files(refs_root: Path) -> List[Path]:
    files = sorted(refs_root.glob("*/metadata/title_abstracts_metadata.jsonl"))
    return [p for p in files if p.is_file()]


def read_metadata(refs_root: Path) -> Dict[Tuple[str, str], MetadataRow]:
    by_key: Dict[Tuple[str, str], MetadataRow] = {}
    for mfile in list_metadata_files(refs_root):
        paper_id = mfile.parents[1].name
        with mfile.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = str(obj.get("key", "")).strip()
                if not key:
                    continue
                title = str(obj.get("title") or "").strip()
                abstract = str(obj.get("abstract") or "").strip()
                by_key[(paper_id, key)] = MetadataRow(
                    paper_id=paper_id, key=key, title=title, abstract=abstract
                )
    return by_key


def list_pdf_entries(pdf_root: Path) -> List[Tuple[str, str, Path]]:
    entries: List[Tuple[str, str, Path]] = []
    for paper_dir in sorted(pdf_root.iterdir()):
        if not paper_dir.is_dir():
            continue
        paper_id = paper_dir.name
        for pdf_path in sorted(paper_dir.rglob("*.pdf")):
            if not pdf_path.is_file():
                continue
            rel = pdf_path.relative_to(paper_dir)
            key = rel.with_suffix("").as_posix()
            entries.append((paper_id, key, pdf_path))
    return entries


def extract_title_from_first_page(doc: fitz.Document) -> str:
    if len(doc) == 0:
        return ""
    page = doc[0]
    text_dict = page.get_text("dict")
    candidates: List[Tuple[float, float, str]] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_text = "".join(span.get("text", "") for span in spans).strip()
            if not line_text:
                continue
            if len(line_text) < 8:
                continue
            norm = normalize_text(line_text)
            if norm in {"abstract", "keywords", "index terms"}:
                continue
            max_size = max((float(span.get("size", 0)) for span in spans), default=0.0)
            y0 = float(line.get("bbox", [0, 0, 0, 0])[1])
            candidates.append((max_size, -y0, line_text))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][2].strip()

    fallback_lines = [ln.strip() for ln in page.get_text("text").splitlines() if ln.strip()]
    for ln in fallback_lines:
        if len(ln) >= 8:
            return ln
    return ""


ABSTRACT_START_RE = re.compile(r"(?is)\babstract\b[\s:.\-]*")
ABSTRACT_END_RE = re.compile(
    r"(?im)^\s*(?:keywords?|index terms?|1\.?\s+introduction|i\.?\s+introduction|"
    r"introduction|background|materials?\s+and\s+methods?|methods)\b"
)


def extract_abstract_from_front_pages(doc: fitz.Document, max_pages: int = 3) -> Tuple[str, str]:
    page_count = min(len(doc), max_pages)
    front_pages = []
    for i in range(page_count):
        front_pages.append(doc[i].get_text("text"))
    front_text = "\n".join(front_pages).strip()
    if not front_text:
        return "", ""

    m = ABSTRACT_START_RE.search(front_text)
    if m:
        after = front_text[m.end() :].strip()
        endm = ABSTRACT_END_RE.search(after)
        if endm:
            abstract = after[: endm.start()].strip()
        else:
            abstract = after[:3000].strip()
        return abstract, front_text

    first_chunk = front_text[:2200].strip()
    return first_chunk, front_text


def compute_abstract_similarity(meta_abs: str, pdf_abs: str) -> float:
    meta_n = normalize_text(meta_abs)
    pdf_n = normalize_text(pdf_abs)
    if not meta_n or not pdf_n:
        return 0.0
    seq_ratio = SequenceMatcher(None, meta_n, pdf_n).ratio()
    meta_tokens = set(meta_n.split())
    pdf_tokens = set(pdf_n.split())
    if not meta_tokens:
        token_recall = 0.0
    else:
        token_recall = len(meta_tokens & pdf_tokens) / len(meta_tokens)
    return 0.5 * seq_ratio + 0.5 * token_recall


def abstract_prefix_exact(meta_abs: str, pdf_abs: str) -> bool:
    meta_n = normalize_text(meta_abs)
    pdf_n = normalize_text(pdf_abs)
    if not meta_n or not pdf_n:
        return False
    prefix_len = min(ABSTRACT_PREFIX_LEN, len(meta_n))
    prefix = meta_n[:prefix_len]
    return prefix in pdf_n


def compare_one_pdf(
    paper_id: str,
    key: str,
    pdf_path: Path,
    mrow: MetadataRow | None,
) -> Dict[str, object]:
    base = {
        "paper_id": paper_id,
        "key": key,
        "pdf_path": str(pdf_path),
        "metadata_title": "",
        "metadata_abstract": "",
        "pdf_title": "",
        "pdf_abstract": "",
        "title_norm_exact": False,
        "abstract_prefix_exact": False,
        "abstract_similarity": 0.0,
        "status": "",
        "reason": "",
    }

    if mrow is None:
        base["status"] = "orphan_pdf"
        base["reason"] = "no_metadata_key_match"
        return base

    base["metadata_title"] = sanitize_field(mrow.title)
    base["metadata_abstract"] = sanitize_field(mrow.abstract)

    if not mrow.title:
        base["status"] = "fail_missing_metadata_title"
        base["reason"] = "missing_metadata_title"
        return base
    if not mrow.abstract:
        base["status"] = "fail_missing_metadata_abstract"
        base["reason"] = "missing_metadata_abstract"
        return base

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        base["status"] = "fail_pdf_unreadable"
        base["reason"] = f"pdf_open_error:{exc.__class__.__name__}"
        return base

    try:
        pdf_title = extract_title_from_first_page(doc)
        pdf_abstract, front_text = extract_abstract_from_front_pages(doc)
    finally:
        doc.close()

    base["pdf_title"] = sanitize_field(pdf_title, max_chars=4000)
    base["pdf_abstract"] = sanitize_field(pdf_abstract)

    quality_probe = pdf_abstract if pdf_abstract else front_text
    if is_text_quality_low(quality_probe):
        base["status"] = "uncertain_text_extraction"
        base["reason"] = "low_text_quality_or_short_extraction"
        return base

    title_exact = normalize_text(mrow.title) == normalize_text(pdf_title)
    prefix_exact = abstract_prefix_exact(mrow.abstract, pdf_abstract)
    abs_sim = compute_abstract_similarity(mrow.abstract, pdf_abstract)

    base["title_norm_exact"] = title_exact
    base["abstract_prefix_exact"] = prefix_exact
    base["abstract_similarity"] = round(abs_sim, 6)

    if not title_exact:
        base["status"] = "fail_title_mismatch"
        base["reason"] = "title_norm_not_exact"
        return base
    if (not prefix_exact) or (abs_sim < SIMILARITY_THRESHOLD):
        base["status"] = "fail_abstract_mismatch"
        base["reason"] = (
            f"abstract_prefix_exact={prefix_exact};"
            f"abstract_similarity={abs_sim:.4f}<threshold={SIMILARITY_THRESHOLD:.2f}"
            if abs_sim < SIMILARITY_THRESHOLD
            else "abstract_prefix_not_found"
        )
        return base

    base["status"] = "pass_strict"
    base["reason"] = "strict_three_layer_pass"
    return base


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_summary(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    by_paper: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_paper[str(row["paper_id"])].append(row)

    out: List[Dict[str, object]] = []
    for paper_id in sorted(by_paper):
        grp = by_paper[paper_id]
        total = len(grp)
        pass_count = sum(1 for r in grp if r["status"] == "pass_strict")
        fail_count = sum(
            1
            for r in grp
            if str(r["status"]).startswith("fail_") or r["status"] in {"orphan_pdf", "orphan_metadata"}
        )
        uncertain_count = sum(1 for r in grp if r["status"] == "uncertain_text_extraction")
        reason_counts = Counter(str(r["reason"]) for r in grp)
        top3 = [f"{k}:{v}" for k, v in reason_counts.most_common(3)]
        out.append(
            {
                "paper_id": paper_id,
                "total_rows": total,
                "pass_strict_count": pass_count,
                "non_pass_count": total - pass_count,
                "fail_count": fail_count,
                "uncertain_count": uncertain_count,
                "pass_rate": round(pass_count / total, 6) if total else 0.0,
                "reason_top3": " | ".join(top3),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify all downloaded PDFs against metadata title/abstract with strict 3-layer matching."
    )
    parser.add_argument("--refs-root", required=True, type=Path)
    parser.add_argument("--pdf-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--mode", default="strict_three_layer", choices=["strict_three_layer"])
    args = parser.parse_args()

    refs_root = args.refs_root
    pdf_root = args.pdf_root
    out_dir = args.out_dir

    metadata = read_metadata(refs_root)
    pdf_entries = list_pdf_entries(pdf_root)

    all_rows: List[Dict[str, object]] = []
    matched_meta_keys: set[Tuple[str, str]] = set()

    for paper_id, key, pdf_path in pdf_entries:
        mrow = metadata.get((paper_id, key))
        if mrow is not None:
            matched_meta_keys.add((paper_id, key))
        row = compare_one_pdf(paper_id, key, pdf_path, mrow)
        all_rows.append(row)

    orphan_metadata_rows: List[Dict[str, object]] = []
    for (paper_id, key), mrow in sorted(metadata.items(), key=lambda x: (x[0][0], x[0][1])):
        if (paper_id, key) in matched_meta_keys:
            continue
        row = {
            "paper_id": paper_id,
            "key": key,
            "pdf_path": "",
            "metadata_title": sanitize_field(mrow.title),
            "metadata_abstract": sanitize_field(mrow.abstract),
            "pdf_title": "",
            "pdf_abstract": "",
            "title_norm_exact": False,
            "abstract_prefix_exact": False,
            "abstract_similarity": 0.0,
            "status": "orphan_metadata",
            "reason": "no_pdf_for_metadata_key",
        }
        all_rows.append(row)
        orphan_metadata_rows.append(row)

    all_rows.sort(key=lambda r: (str(r["paper_id"]), str(r["key"]), str(r["status"]), str(r["pdf_path"])))

    verification_fields = [
        "paper_id",
        "key",
        "pdf_path",
        "metadata_title",
        "metadata_abstract",
        "pdf_title",
        "pdf_abstract",
        "title_norm_exact",
        "abstract_prefix_exact",
        "abstract_similarity",
        "status",
        "reason",
    ]
    write_csv(out_dir / "verification_rows.csv", all_rows, verification_fields)

    summary_rows = build_summary(all_rows)
    write_csv(
        out_dir / "verification_summary_by_paper.csv",
        summary_rows,
        [
            "paper_id",
            "total_rows",
            "pass_strict_count",
            "non_pass_count",
            "fail_count",
            "uncertain_count",
            "pass_rate",
            "reason_top3",
        ],
    )

    manual_review_rows = [r for r in all_rows if r["status"] != "pass_strict"]
    write_csv(out_dir / "manual_review_queue.csv", manual_review_rows, verification_fields)

    orphan_pdf_rows = [r for r in all_rows if r["status"] == "orphan_pdf"]
    write_csv(out_dir / "orphan_pdf.csv", orphan_pdf_rows, verification_fields)

    write_csv(out_dir / "orphan_metadata.csv", orphan_metadata_rows, verification_fields)

    total = len(all_rows)
    pass_count = sum(1 for r in all_rows if r["status"] == "pass_strict")
    print(f"mode={args.mode}")
    print(f"rows_total={total}")
    print(f"pass_strict={pass_count}")
    print(f"non_pass={total - pass_count}")
    print(f"out_dir={out_dir}")


if __name__ == "__main__":
    main()
