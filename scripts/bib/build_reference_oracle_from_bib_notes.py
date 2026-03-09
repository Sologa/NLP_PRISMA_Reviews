#!/usr/bin/env python3
"""Compatibility wrapper for the split clean/oracle pipeline.

Kept for legacy command compatibility:
- parse-bib   -> scripts/bib/build_clean_bib_from_notes.py
- parse-oracle -> scripts/bib/build_reference_oracle_from_bib.py
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bib.build_clean_bib_from_notes import build_cleaned_bib_from_paths
from scripts.bib.build_reference_oracle_from_bib import build_reference_oracle_from_paths


def _resolve_default_clean_dir(*, bib_path: Path | None, bib_dir: Path | None) -> Path:
    if bib_path:
        return bib_path.parent.parent / "per_SR_cleaned"
    if bib_dir:
        return bib_dir.parent / "per_SR_cleaned"
    return Path("bib/per_SR_cleaned")


def _disable_crossref_from_legacy(enable_crossref: bool, disable_crossref: bool) -> bool:
    if disable_crossref:
        return True
    if enable_crossref:
        return False
    return False


def _print_reference_summary(summaries: list[tuple[Path, int, int, int, int]], reasons) -> None:
    total = sum(s[1] for s in summaries)
    extracted = sum(s[2] for s in summaries)
    fallback = sum(s[3] for s in summaries)
    empty = sum(s[4] for s in summaries)

    for bib_path, total_n, extracted_n, fallback_n, empty_n in summaries:
        print(
            f"[done] {bib_path.name}: entries={total_n}, extracted={extracted_n}, "
            f"fallback={fallback_n}, empty={empty_n}"
        )
    if reasons:
        print("[reason] " + ", ".join(f"{k}:{v}" for k, v in reasons.most_common()))
    print(f"[total] entries={total}, extracted={extracted}, fallback={fallback}, empty={empty}")


def _run_oracle(args: argparse.Namespace) -> int:
    if args.bib_path:
        bib_paths = [args.bib_path]
    else:
        bib_paths = sorted(args.bib_dir.glob("*.bib"))

    if args.out_jsonl and len(bib_paths) != 1:
        raise SystemExit("--out-jsonl only supports single-file mode; remove --bib-dir when using --out-jsonl.")

    default_out_dir = _resolve_default_clean_dir(bib_path=args.bib_path, bib_dir=args.bib_dir)
    out_dir = args.out_dir or default_out_dir

    if args.emit_bib:
        warnings.warn(
            "--emit-bib is deprecated in legacy mode; use --mode parse-bib "
            "with scripts/bib/build_clean_bib_from_notes.py",
            DeprecationWarning,
        )
        build_cleaned_bib_from_paths(
            bib_paths,
            output_dir=out_dir,
            keep_empty=args.keep_empty,
            crossref_cache=args.crossref_cache,
            disable_crossref=_disable_crossref_from_legacy(args.enable_crossref, args.disable_crossref),
            confidence_report=args.confidence_report,
            include_report_all=args.confidence_report_all if args.confidence_report else False,
            review_candidates=args.review_candidates,
        )
        return 0

    template = args.name_template
    if args.out_jsonl:
        out_dir = args.out_jsonl.parent
        template = args.out_jsonl.name

    summaries, reasons = build_reference_oracle_from_paths(
        bib_paths,
        output_dir=out_dir,
        name_template=template,
        strict_title=args.strict_title,
    )
    _print_reference_summary(summaries, reasons)
    return 0


def _run_clean(args: argparse.Namespace) -> int:
    if args.bib_path:
        bib_paths = [args.bib_path]
    else:
        bib_paths = sorted(args.bib_dir.glob("*.bib"))

    out_dir = args.out_dir or _resolve_default_clean_dir(bib_path=args.bib_path, bib_dir=args.bib_dir)
    summaries, _ = build_cleaned_bib_from_paths(
        bib_paths,
        output_dir=out_dir,
        keep_empty=args.keep_empty,
        crossref_cache=args.crossref_cache,
        disable_crossref=_disable_crossref_from_legacy(args.enable_crossref, args.disable_crossref),
        confidence_report=args.confidence_report,
        include_report_all=args.confidence_report_all,
        review_candidates=args.review_candidates,
    )

    total = sum(s[1] for s in summaries)
    parsed = sum(s[2] for s in summaries)
    fallback = sum(s[3] for s in summaries)
    empty = sum(s[4] for s in summaries)

    for bib_path, n_total, n_parsed, n_fallback, n_empty in summaries:
        print(f"[done] {Path(bib_path).name}: entries={n_total}, parsed={n_parsed}, fallback={n_fallback}, empty={n_empty}")
    print(f"[total] entries={total}, parsed={parsed}, fallback={fallback}, empty={empty}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compatibility wrapper for split clean/oracle scripts")
    parser.add_argument("--bib-path", type=Path, default=None)
    parser.add_argument("--bib-dir", type=Path, default=None)
    parser.add_argument("--out-jsonl", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--mode",
        default="parse-oracle",
        choices=["parse-oracle", "parse-bib"],
        help="Operation mode",
    )
    parser.add_argument(
        "--name-template",
        type=str,
        default="{stem}/reference_oracle.jsonl",
        help="Output name template in legacy oracle directory mode",
    )
    parser.add_argument("--emit-bib", action="store_true", help="Legacy alias: parse cleaned bib")
    parser.add_argument("--keep-empty", action="store_true")
    parser.add_argument("--confidence-report", action="store_true")
    parser.add_argument("--confidence-report-all", action="store_true")
    parser.add_argument("--review-candidates", action="store_true")
    parser.add_argument("--strict-title", action="store_true")
    parser.add_argument("--crossref-cache", type=Path, default=Path(".crossref_cache.json"))
    parser.add_argument("--disable-crossref", action="store_true", help="Disable DOI -> Crossref enrich")
    parser.add_argument("--enable-crossref", action="store_true", help="Compatibility flag, default enabled")

    args = parser.parse_args()

    if args.bib_path and args.bib_dir:
        raise SystemExit("provide only one of --bib-path or --bib-dir")
    if not args.bib_path and not args.bib_dir:
        raise SystemExit("must provide either --bib-path or --bib-dir")
    if args.bib_dir:
        if not args.bib_dir.exists() or not args.bib_dir.is_dir():
            raise SystemExit(f"BibTeX directory not found: {args.bib_dir}")
        if not list(args.bib_dir.glob("*.bib")):
            raise SystemExit(f"No .bib files found in {args.bib_dir}")

    if args.enable_crossref and args.disable_crossref:
        raise SystemExit("Cannot set both --enable-crossref and --disable-crossref")

    if args.mode == "parse-oracle" and args.review_candidates:
        warnings.warn("--review-candidates is ignored in parse-oracle mode", UserWarning)
    if args.mode == "parse-oracle" and args.confidence_report_all:
        warnings.warn("--confidence-report-all is ignored in parse-oracle mode", UserWarning)

    warnings.warn(
        "build_reference_oracle_from_bib_notes.py is now a compatibility wrapper. "
        "Use scripts/bib/build_clean_bib_from_notes.py and scripts/bib/build_reference_oracle_from_bib.py directly.",
        DeprecationWarning,
    )

    if args.mode == "parse-bib":
        return _run_clean(args)
    return _run_oracle(args)


if __name__ == "__main__":
    raise SystemExit(main())
