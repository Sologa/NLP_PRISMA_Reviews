#!/usr/bin/env python3
"""Build reference_oracle.jsonl from cleaned BibTeX entries."""

from __future__ import annotations

import argparse
import json
from collections import Counter
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.bib_parser import parse_bibtex
from scripts.lib.oracle_writer import build_reference_oracle_records


def _render_output_path(out_base: Path, bib_path: Path, name_template: str) -> Path:
    rel = name_template.format(stem=bib_path.stem)
    return out_base / rel


def build_reference_oracle_from_paths(
    bib_paths: list[Path],
    output_dir: Path,
    *,
    name_template: str = "{stem}/reference_oracle.jsonl",
    strict_title: bool = False,
) -> tuple[list[tuple[Path, int, int, int, int]], Counter]:
    summaries: list[tuple[Path, int, int, int, int]] = []
    reasons: Counter = Counter()

    for bib_path in bib_paths:
        text = bib_path.read_text(encoding="utf-8", errors="ignore")
        entries = parse_bibtex(text)

        records, local_reasons = build_reference_oracle_records(entries, use_title_first=True, strict_title=strict_title)
        reasons.update(local_reasons)

        out_path = _render_output_path(output_dir, bib_path, name_template)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            for rec in records:
                handle.write(json.dumps(rec, ensure_ascii=True) + "\n")

        total = len(records)
        extracted = sum(1 for r in records if r.get("query_title"))
        fallback = total - extracted
        empty = sum(1 for r in records if not r.get("query_title"))
        summaries.append((bib_path, total, extracted, fallback, empty))

    return summaries, reasons


def _print_summary(summaries: list[tuple[Path, int, int, int, int]], reasons: Counter) -> None:
    total = sum(s[1] for s in summaries)
    extracted = sum(s[2] for s in summaries)
    fallback = sum(s[3] for s in summaries)
    empty = sum(s[4] for s in summaries)

    for bib_path, total_n, extracted_n, fallback_n, empty_n in summaries:
        print(
            f"[done] {bib_path.name}: entries={total_n}, extracted={extracted_n}, fallback={fallback_n}, empty={empty_n}"
        )

    if reasons:
        print("[reason] " + ", ".join(f"{k}:{v}" for k, v in reasons.most_common()))

    print(f"[total] entries={total}, extracted={extracted}, fallback={fallback}, empty={empty}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reference_oracle.jsonl from cleaned per_SR BibTeX.")
    parser.add_argument("--bib-path", type=Path, default=None)
    parser.add_argument("--bib-dir", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("bib/per_SR_cleaned"), help="Base output directory")
    parser.add_argument(
        "--name-template",
        type=str,
        default="{stem}/reference_oracle.jsonl",
        help="Output path template, use {stem}",
    )
    parser.add_argument("--strict-title", action="store_true")

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

    summaries, reasons = build_reference_oracle_from_paths(
        bib_paths,
        output_dir=args.out_dir,
        name_template=args.name_template,
        strict_title=args.strict_title,
    )

    _print_summary(summaries, reasons)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
