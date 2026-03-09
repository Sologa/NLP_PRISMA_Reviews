#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF


def read_metadata_keys(meta_path: Path) -> List[str]:
    keys: List[str] = []
    with meta_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = str(row.get("key") or "").strip()
            if key:
                keys.append(key)
    return keys


def safe_stem(key: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip("._")
    if not stem:
        stem = "key"
    return stem


def assign_unique_md_names(keys: List[str]) -> List[str]:
    """Assign one dedup-safe md filename per metadata row (not per unique key)."""
    used: Dict[str, int] = {}
    out: List[str] = []
    for key in keys:
        base = safe_stem(key)
        count = used.get(base, 0) + 1
        used[base] = count
        if count == 1:
            name = f"{base}.md"
        else:
            name = f"{base}__dup{count}.md"
        out.append(name)
    return out


def extract_texts_from_pdf(pdf_path: Path) -> Tuple[str, str, str]:
    """Return (full_text, page1_text, note)."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        return "", "", f"pdf_open_error:{exc.__class__.__name__}"

    try:
        pages = []
        for p in doc:
            pages.append((p.get_text("text") or "").replace("\x00", ""))
        full = "\n".join(pages).strip()
        page1 = (pages[0] if pages else "").strip()
    except Exception as exc:
        doc.close()
        return "", "", f"pdf_extract_error:{exc.__class__.__name__}"

    doc.close()
    return full, page1, "ok"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def count_zip_entries(zip_path: Path) -> int:
    with zipfile.ZipFile(zip_path, "r") as zf:
        return len(zf.infolist())


def main() -> int:
    ap = argparse.ArgumentParser(description="Post-process md + zips aligned to metadata keys")
    ap.add_argument("--paper-id", required=True)
    ap.add_argument("--refs-root", default="refs", type=Path)
    ap.add_argument("--pdf-root", default="ref_pdfs", type=Path)
    ap.add_argument("--issues-root", default="issues/manual_pdf_match", type=Path)
    args = ap.parse_args()

    paper_id = args.paper_id
    ref_dir = args.refs_root / paper_id
    meta_path = ref_dir / "metadata" / "title_abstracts_metadata.jsonl"
    mds_dir = ref_dir / "mds"
    zip_full = ref_dir / "fulltexts_text_only.zip"
    zip_page1 = ref_dir / "fulltexts_text_only-page1.zip"

    manifest_path = args.issues_root / f"{paper_id}_md_zip_manifest.csv"
    summary_path = args.issues_root / f"{paper_id}_md_zip_summary.md"

    keys = read_metadata_keys(meta_path)
    key_count = len(keys)
    if key_count == 0:
        raise SystemExit(f"No metadata keys found: {meta_path}")

    # Rebuild mds directory to make file count strictly aligned to metadata keys.
    if mds_dir.exists():
        shutil.rmtree(mds_dir)
    mds_dir.mkdir(parents=True, exist_ok=True)

    md_names = assign_unique_md_names(keys)

    rows: List[dict] = []
    missing_pdf_keys: List[str] = []
    unreadable_pdf_keys: List[str] = []

    with zipfile.ZipFile(zip_full, "w", compression=zipfile.ZIP_DEFLATED) as zf_full, zipfile.ZipFile(
        zip_page1, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf_p1:
        for key, md_name in zip(keys, md_names):
            md_path = mds_dir / md_name
            pdf_path = args.pdf_root / paper_id / f"{key}.pdf"

            pdf_exists = pdf_path.exists() and pdf_path.is_file()
            status = "ok"
            note = ""
            full_text = ""
            p1_text = ""

            if pdf_exists:
                full_text, p1_text, extract_note = extract_texts_from_pdf(pdf_path)
                if extract_note != "ok":
                    status = "pdf_unreadable"
                    note = extract_note
                    unreadable_pdf_keys.append(key)
            else:
                status = "missing_pdf"
                note = "pdf_not_found_at_ref_pdfs_key_path"
                missing_pdf_keys.append(key)

            # text-only output: write plain extracted body text (no extra headers)
            write_text(md_path, full_text)

            # Zip entry names are kept unique with dedup-safe md filenames.
            zf_full.writestr(md_name, full_text)
            zf_p1.writestr(md_name, p1_text)

            rows.append(
                {
                    "paper_id": paper_id,
                    "key": key,
                    "pdf_exists": "1" if pdf_exists else "0",
                    "md_path": md_path.as_posix(),
                    "zip_entry_full": md_name,
                    "zip_entry_page1": md_name,
                    "status": status,
                    "note": note,
                }
            )

    fields = [
        "paper_id",
        "key",
        "pdf_exists",
        "md_path",
        "zip_entry_full",
        "zip_entry_page1",
        "status",
        "note",
    ]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    mds_count = len(list(mds_dir.glob("*.md")))
    zip_full_count = count_zip_entries(zip_full)
    zip_p1_count = count_zip_entries(zip_page1)

    aligned = mds_count == key_count and zip_full_count == key_count and zip_p1_count == key_count

    with summary_path.open("w", encoding="utf-8") as f:
        f.write(f"# MD+ZIP Postprocess Summary: {paper_id}\n\n")
        f.write(f"- metadata key total: {key_count}\n")
        f.write(f"- mds file total: {mds_count}\n")
        f.write(f"- zip entry total (full): {zip_full_count}\n")
        f.write(f"- zip entry total (page1): {zip_p1_count}\n")
        f.write(f"- missing pdf count: {len(missing_pdf_keys)}\n")
        f.write(f"- unreadable pdf count: {len(unreadable_pdf_keys)}\n")
        f.write(f"- 100% aligned to metadata key count: {'YES' if aligned else 'NO'}\n\n")

        f.write("## Missing PDF Keys\n")
        if missing_pdf_keys:
            for k in missing_pdf_keys:
                f.write(f"- {k}\n")
        else:
            f.write("- none\n")

        f.write("\n## Unreadable PDF Keys\n")
        if unreadable_pdf_keys:
            for k in unreadable_pdf_keys:
                f.write(f"- {k}\n")
        else:
            f.write("- none\n")

    print(f"paper_id={paper_id}")
    print(f"metadata_keys={key_count}")
    print(f"mds_count={mds_count}")
    print(f"zip_full_entries={zip_full_count}")
    print(f"zip_page1_entries={zip_p1_count}")
    print(f"missing_pdf_count={len(missing_pdf_keys)}")
    print(f"unreadable_pdf_count={len(unreadable_pdf_keys)}")
    print(f"aligned={'yes' if aligned else 'no'}")
    print(f"manifest={manifest_path.as_posix()}")
    print(f"summary={summary_path.as_posix()}")
    print(f"zip_full={zip_full.as_posix()}")
    print(f"zip_page1={zip_page1.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
