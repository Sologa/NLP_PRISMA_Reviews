#!/usr/bin/env python3
"""Convert arXiv-ID-named PDFs in `pdfs/` to markdown text files in `mds/`."""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ARXIV_ID_RE = re.compile(r"^(?P<arxiv_id>\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)$", re.IGNORECASE)


def _extract_text_pdf_with_pypdf(pdf_path: Path) -> str | None:
    try:
        from pypdf import PdfReader
    except Exception:
        return None

    try:
        reader = PdfReader(str(pdf_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        text = "\n\n".join(pages).strip()
    except Exception as exc:
        raise RuntimeError(f"pypdf failed for {pdf_path}: {exc}") from exc

    return text


def _extract_text_pdf_with_strings(pdf_path: Path) -> str | None:
    result = subprocess.run(
        ["strings", "-n", "6", str(pdf_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    text = result.stdout.strip()
    return text


def _normalize_markdown_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    normalized = []
    last_blank = False

    for line in lines:
        line = line.rstrip()
        if not line:
            if not last_blank:
                normalized.append("")
            last_blank = True
            continue
        normalized.append(line)
        last_blank = False

    return "\n".join(normalized).strip()


def _convert_one(
    pdf_path: Path,
    output_dir: Path,
    extractor: Callable[[Path], str | None],
    overwrite: bool,
) -> tuple[bool, str]:
    match = ARXIV_ID_RE.match(pdf_path.name)
    if not match:
        return False, f"skip: not arxiv-id filename ({pdf_path.name})"

    arxiv_id = match.group("arxiv_id")
    out_path = output_dir / f"{arxiv_id}.md"

    if out_path.exists() and not overwrite:
        return False, f"skip exists: {out_path.name}"

    text = extractor(pdf_path)
    if text is None:
        return False, f"failed: cannot extract text ({pdf_path.name})"

    content = _normalize_markdown_text(text)
    if not content:
        return False, f"failed: empty extracted text ({pdf_path.name})"

    header = (
        f"# {arxiv_id}\n\n"
        f"- Source: `{pdf_path.name}`\n"
        f"- Converted: `{datetime.now(timezone.utc).isoformat()}`\n\n"
    )
    out_path.write_text(header + content + "\n", encoding="utf-8")
    return True, f"wrote: {out_path.relative_to(output_dir.parent)}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert arXiv-ID-named PDFs in pdfs/ to Markdown files in mds/."
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("pdfs"),
        help="Input PDF directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("mds"),
        help="Output markdown directory",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing md output files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.pdf_dir = args.pdf_dir.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    extractor = _extract_text_pdf_with_pypdf
    candidate_pdf = sorted(args.pdf_dir.glob("*.pdf"))

    written = 0
    skipped = 0
    failed = 0

    for pdf_path in candidate_pdf:
        converted, msg = _convert_one(pdf_path, args.output_dir, extractor, args.overwrite)
        if converted:
            written += 1
        elif msg.startswith("failed"):
            # retry with fallback extractor
            fallback_text = _extract_text_pdf_with_strings(pdf_path)
            if fallback_text:
                msg2 = _convert_one(
                    pdf_path=pdf_path,
                    output_dir=args.output_dir,
                    extractor=lambda _p: fallback_text,
                    overwrite=args.overwrite,
                )
                if msg2[0]:
                    converted = True
                    written += 1
                else:
                    failed += 1
            else:
                failed += 1
        else:
            skipped += 1

    print(f"[summary] converted={written} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
