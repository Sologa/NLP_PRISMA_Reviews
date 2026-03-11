#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_METADATA = REPO_ROOT / "screening" / "data" / "source" / "cads" / "arxiv_metadata.json"
DEFAULT_CRITERIA = REPO_ROOT / "screening" / "data" / "source" / "cads" / "criteria.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "screening" / "data" / "cads_smoke5"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_key_list(path: Path) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in seen:
            continue
        seen.add(stripped)
        keys.append(stripped)
    return keys


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _first_record_keys(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return []
    return sorted(records[0].keys())


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _load_metadata_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        records: list[dict[str, Any]] = []
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL at {path}:{idx}: {exc}") from exc
            if isinstance(payload, dict):
                records.append(payload)
        return records

    payload = _load_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if isinstance(payload, dict):
        for key in ("records", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]

    raise SystemExit(f"Unsupported metadata format: {path}")


def _load_criteria_payload(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        raise SystemExit(f"Expected criteria JSON in {path}, but got {path.suffix}.")

    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected criteria object JSON in {path}")

    structured = payload.get("structured_payload")
    if isinstance(structured, dict):
        return structured
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare local review inputs from metadata + criteria files. "
            "Supports metadata .json/.jsonl and criteria .json only."
        )
    )
    parser.add_argument(
        "--source-metadata",
        type=Path,
        default=DEFAULT_SOURCE_METADATA,
        help="Source metadata path (.json list or .jsonl).",
    )
    parser.add_argument(
        "--criteria",
        type=Path,
        default=DEFAULT_CRITERIA,
        help="Criteria JSON path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output folder for local smoke-test inputs.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of metadata records to keep. Set to 0 to keep all screenable records.",
    )
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=None,
        help="Optional newline-delimited keys list; when set, this overrides --top-k.",
    )
    args = parser.parse_args()

    if args.top_k < 0:
        raise SystemExit("--top-k must be >= 0")

    metadata_path = args.source_metadata.resolve()
    criteria_path = args.criteria.resolve()

    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata file: {metadata_path}")
    if not criteria_path.exists():
        raise SystemExit(f"Missing criteria file: {criteria_path}")
    keys_filter: list[str] = []
    if args.keys_file is not None:
        keys_path = args.keys_file.resolve()
        if not keys_path.exists():
            raise SystemExit(f"Missing keys file: {keys_path}")
        keys_filter = _load_key_list(keys_path)
        if not keys_filter:
            raise SystemExit(f"No usable keys in --keys-file: {keys_path}")

    raw_records = _load_metadata_records(metadata_path)

    # Keep only records that can be screened by title + abstract.
    screenable = [row for row in raw_records if str(row.get("title") or "").strip() and str(row.get("abstract") or "").strip()]
    criteria_payload = _load_criteria_payload(criteria_path)
    if keys_filter:
        by_key = {str(row.get("key") or "").strip(): row for row in screenable if str(row.get("key") or "").strip()}
        subset: list[dict[str, Any]] = []
        missing_keys: list[str] = []
        for key in keys_filter:
            row = by_key.get(key)
            if row is None:
                missing_keys.append(key)
                continue
            subset.append(row)
        if not subset:
            raise SystemExit("No matching screenable metadata rows found for --keys-file.")
        if missing_keys:
            print(f"[warn] missing keys in metadata (ignored): {len(missing_keys)}")
            for key in missing_keys:
                print(f"[warn]   {key}")
    else:
        if args.top_k > 0 and len(screenable) < args.top_k:
            raise SystemExit(
                f"Not enough screenable rows for top-k={args.top_k}; "
                f"available={len(screenable)} (raw={len(raw_records)})"
            )
        subset = screenable if args.top_k == 0 else screenable[: args.top_k]

    out_dir = args.output_dir.resolve()
    if keys_filter:
        metadata_suffix = f"keys{len(subset)}"
    else:
        metadata_suffix = "full" if args.top_k == 0 else f"top{args.top_k}"
    out_metadata = out_dir / f"arxiv_metadata.{metadata_suffix}.json"
    out_manifest = out_dir / "manifest.json"

    _write_json(out_metadata, subset)
    _write_json(
        out_manifest,
        {
            "source_metadata": _rel(metadata_path),
            "source_criteria": _rel(criteria_path),
            "source_metadata_format": metadata_path.suffix.lower(),
            "source_criteria_format": criteria_path.suffix.lower(),
            "top_k": args.top_k if args.top_k > 0 else "full",
            "keys_file": _rel(args.keys_file.resolve()) if args.keys_file is not None else None,
            "keys_count": len(keys_filter) if keys_filter else None,
            "output_metadata": _rel(out_metadata),
            "output_criteria": None,
            "metadata_total_available": len(raw_records),
            "metadata_screenable_count": len(screenable),
            "metadata_subset_count": len(subset),
            "metadata_first_record_keys": _first_record_keys(subset),
        },
    )

    print(f"[ok] wrote metadata subset: {out_metadata}")
    print(f"[ok] wrote manifest: {out_manifest}")
    print(f"[info] top_k={args.top_k}")
    if keys_filter:
        print(f"[info] keys_file={args.keys_file.resolve()}")
        print(f"[info] keys_count={len(keys_filter)}")
    print(f"[info] raw_count={len(raw_records)}")
    print(f"[info] screenable_count={len(screenable)}")
    print(f"[info] subset_count={len(subset)}")
    print(f"[info] first_record_keys={_first_record_keys(subset)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
