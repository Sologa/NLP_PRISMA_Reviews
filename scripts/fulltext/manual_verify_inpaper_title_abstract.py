#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import unicodedata
from collections import Counter, defaultdict
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


ABSTRACT_PREFIX_LEN = 220
MAX_PAGES_FOR_ABSTRACT = 20
PAGES_FOR_TITLE = 3


def normalize_text(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def list_inpaper_ids(inpaper_dir: Path) -> List[str]:
    out: List[str] = []
    for p in sorted(glob.glob(str(inpaper_dir / "*_included.jsonl"))):
        m = re.search(r"/([0-9]{4}\.[0-9]{5})_included\.jsonl$", p)
        if m:
            out.append(m.group(1))
    return out


def read_metadata_for_papers(refs_root: Path, paper_ids: Iterable[str]) -> Dict[Tuple[str, str], Dict[str, str]]:
    wanted = set(paper_ids)
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    for pid in sorted(wanted):
        meta_path = refs_root / pid / "metadata" / "title_abstracts_metadata.jsonl"
        if not meta_path.exists():
            continue
        with meta_path.open("r", encoding="utf-8") as fh:
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
                rows[(pid, key)] = {
                    "title": str(obj.get("title") or "").strip(),
                    "abstract": str(obj.get("abstract") or "").strip(),
                }
    return rows


def list_pdf_keys(pdf_root: Path, paper_id: str) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    pdir = pdf_root / paper_id
    if not pdir.exists():
        return out
    for p in sorted(pdir.rglob("*.pdf")):
        key = p.relative_to(pdir).with_suffix("").as_posix()
        out[key] = p
    return out


def extract_pdf_texts(pdf_path: Path) -> Tuple[str, str]:
    doc = fitz.open(pdf_path)
    try:
        n = len(doc)
        title_pages = min(PAGES_FOR_TITLE, n)
        title_text = "\n".join(doc[i].get_text("text") for i in range(title_pages))
        abs_pages = min(MAX_PAGES_FOR_ABSTRACT, n)
        abs_text = "\n".join(doc[i].get_text("text") for i in range(abs_pages))
    finally:
        doc.close()
    return title_text, abs_text


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inpaper-dir", type=Path, default=Path("evidence_base_list/inpaper"))
    ap.add_argument("--refs-root", type=Path, default=Path("refs"))
    ap.add_argument("--pdf-root", type=Path, default=Path("ref_pdfs"))
    ap.add_argument("--out-dir", type=Path, default=Path("issues/pdf_metadata_verify_inpaper_manual"))
    args = ap.parse_args()

    paper_ids = list_inpaper_ids(args.inpaper_dir)
    metadata = read_metadata_for_papers(args.refs_root, paper_ids)

    rows: List[Dict[str, object]] = []
    for pid in paper_ids:
        pdf_map = list_pdf_keys(args.pdf_root, pid)
        keys_for_pid = sorted(k for (p, k) in metadata.keys() if p == pid)
        for key in keys_for_pid:
            m = metadata.get((pid, key), {})
            title = m.get("title", "")
            abstract = m.get("abstract", "")

            base = {
                "paper_id": pid,
                "key": key,
                "pdf_path": "",
                "metadata_title": title,
                "metadata_abstract": abstract,
                "title_in_pdf": False,
                "abstract_prefix_in_pdf": False,
                "status": "",
                "reason": "",
            }

            pdf_path = pdf_map.get(key)
            if pdf_path is None:
                base["status"] = "missing_pdf"
                base["reason"] = "no_pdf_for_metadata_key"
                rows.append(base)
                continue

            base["pdf_path"] = pdf_path.as_posix()
            if not title:
                base["status"] = "missing_metadata_title"
                base["reason"] = "metadata_title_empty"
                rows.append(base)
                continue
            if not abstract:
                base["status"] = "missing_metadata_abstract"
                base["reason"] = "metadata_abstract_empty"
                rows.append(base)
                continue

            try:
                title_text, abs_text = extract_pdf_texts(pdf_path)
            except Exception as exc:
                base["status"] = "pdf_unreadable"
                base["reason"] = f"pdf_open_error:{exc.__class__.__name__}"
                rows.append(base)
                continue

            title_hit = normalize_text(title) in normalize_text(title_text)
            abs_prefix = normalize_text(abstract)[:ABSTRACT_PREFIX_LEN]
            abs_hit = bool(abs_prefix) and (abs_prefix in normalize_text(abs_text))

            base["title_in_pdf"] = title_hit
            base["abstract_prefix_in_pdf"] = abs_hit

            if title_hit and abs_hit:
                base["status"] = "pass_manual_title_abstract"
                base["reason"] = "title_and_abstract_prefix_found"
            elif (not title_hit) and (not abs_hit):
                base["status"] = "fail_manual_both_mismatch"
                base["reason"] = "title_not_found_and_abstract_prefix_not_found"
            elif not title_hit:
                base["status"] = "fail_manual_title_mismatch"
                base["reason"] = "title_not_found_in_pdf_front_pages"
            else:
                base["status"] = "fail_manual_abstract_mismatch"
                base["reason"] = "abstract_prefix_not_found_in_pdf_text"

            rows.append(base)

    rows.sort(key=lambda r: (str(r["paper_id"]), str(r["key"])))
    fields = [
        "paper_id",
        "key",
        "pdf_path",
        "metadata_title",
        "metadata_abstract",
        "title_in_pdf",
        "abstract_prefix_in_pdf",
        "status",
        "reason",
    ]
    write_csv(args.out_dir / "manual_title_abstract_alignment.csv", rows, fields)

    by_paper: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for r in rows:
        by_paper[str(r["paper_id"])].append(r)

    summary_rows: List[Dict[str, object]] = []
    for pid in paper_ids:
        grp = by_paper.get(pid, [])
        c = Counter(str(r["status"]) for r in grp)
        total = len(grp)
        p = c["pass_manual_title_abstract"]
        summary_rows.append(
            {
                "paper_id": pid,
                "total": total,
                "pass_manual_title_abstract": p,
                "non_pass": total - p,
                "missing_pdf": c["missing_pdf"],
                "fail_manual_title_mismatch": c["fail_manual_title_mismatch"],
                "fail_manual_abstract_mismatch": c["fail_manual_abstract_mismatch"],
                "fail_manual_both_mismatch": c["fail_manual_both_mismatch"],
                "other": total
                - p
                - c["missing_pdf"]
                - c["fail_manual_title_mismatch"]
                - c["fail_manual_abstract_mismatch"]
                - c["fail_manual_both_mismatch"],
            }
        )

    write_csv(
        args.out_dir / "summary_manual_title_abstract.csv",
        summary_rows,
        [
            "paper_id",
            "total",
            "pass_manual_title_abstract",
            "non_pass",
            "missing_pdf",
            "fail_manual_title_mismatch",
            "fail_manual_abstract_mismatch",
            "fail_manual_both_mismatch",
            "other",
        ],
    )

    print("paper_ids", ",".join(paper_ids))
    print("rows_total", len(rows))
    print("pass_manual_title_abstract", sum(1 for r in rows if r["status"] == "pass_manual_title_abstract"))
    print("non_pass", sum(1 for r in rows if r["status"] != "pass_manual_title_abstract"))
    print("out_dir", args.out_dir.as_posix())


if __name__ == "__main__":
    main()
