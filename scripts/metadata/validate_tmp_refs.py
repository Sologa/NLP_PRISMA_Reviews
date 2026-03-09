#!/usr/bin/env python3
"""Validate temporary metadata results generated under ``tmp_refs``.

The script compares ``missing_manifest.jsonl`` entries with collected metadata from
``metadata/title_abstracts_metadata.jsonl`` in each ``tmp_refs/<paper>`` directory.

For each paper it reports:
- ``total_target``: number of keys in manifest
- ``resolved_count``: keys still with non-missing metadata
- ``still_missing_count``: keys unresolved after temp collection
- list of unresolved keys (key + query/title/reason)
"""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")


def _metadata_is_missing(record: dict[str, Any] | None) -> bool:
    if record is None:
        return True

    source = (record.get("source") or "").strip().lower()
    match_status = (record.get("match_status") or "").strip().lower()
    return match_status == "missing" or source in {"", "missing", "none", "null"}


def _load_jsonl_records(path: Path) -> OrderedDict[str, dict[str, Any]]:
    out: OrderedDict[str, dict[str, Any]] = OrderedDict()
    if not path.exists():
        return out

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = record.get("key")
            if key is None:
                continue
            out[str(key)] = record
    return out


def _load_jsonl_list(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _iter_papers(tmp_root: Path, paper_ids: list[str] | None) -> list[str]:
    allowed = None if not paper_ids else set(paper_ids)
    papers: list[str] = []

    for child in sorted(tmp_root.iterdir()):
        if not child.is_dir():
            continue
        if not ARXIV_ID_RE.match(child.name):
            continue
        if allowed is not None and child.name not in allowed:
            continue
        papers.append(child.name)

    return papers


def _query_title_from_manifest(item: dict[str, Any]) -> str:
    return str(
        item.get("query_title_original") or item.get("query_title") or item.get("query_title_sanitized") or ""
    )


def _manifest_lookup(manifest: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in manifest:
        key = item.get("key")
        if key is None:
            continue
        out[str(key)] = item
    return out


def _dump_markdown_report(results: list[dict[str, Any]], report_path: Path | None) -> None:
    if report_path is None:
        return

    report_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# tmp_refs validation report\n\n")
        handle.write(f"- generated_at: {now}\n")
        handle.write("- total_papers: {}\n\n".format(len(results)))

        for item in results:
            paper = item["paper_id"]
            handle.write(f"## {paper}\n")
            handle.write(f"- total_target: {item['total_target']}\n")
            handle.write(f"- resolved_count: {item['resolved_count']}\n")
            handle.write(f"- still_missing_count: {item['still_missing_count']}\n")

            if item["missing_keys"]:
                handle.write("- unresolved keys:\n")
                for row in item["missing_keys"]:
                    key = row.get("key", "")
                    reason = row.get("reason") or "missing_in_tmp"
                    query_title = row.get("query_title") or ""
                    source = row.get("tmp_source")
                    if source:
                        handle.write(f"  - `{key}`: {reason}; {query_title}; source={source}\n")
                    else:
                        handle.write(f"  - `{key}`: {reason}; {query_title}\n")
            else:
                handle.write("- unresolved keys: none\n")
            handle.write("\n")


def _write_json_report(results: list[dict[str, Any]], report_path: Path | None) -> None:
    if report_path is None:
        return

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)


def _validate_paper(tmp_root: Path, paper: str, args: argparse.Namespace) -> dict[str, Any]:
    paper_dir = tmp_root / paper
    manifest_path = paper_dir / args.manifest_filename
    metadata_path = paper_dir / "metadata" / args.metadata_filename

    manifest = _load_jsonl_list(manifest_path)
    if not manifest:
        return {
            "paper_id": paper,
            "total_target": 0,
            "resolved_count": 0,
            "still_missing_count": 0,
            "resolved_keys": [],
            "missing_keys": [],
            "note": "missing_manifest_or_empty",
        }

    manifest_lookup = _manifest_lookup(manifest)
    target_keys: list[str] = []
    seen: set[str] = set()

    for item in manifest:
        key = item.get("key")
        if key is None:
            continue
        key = str(key)
        if key in seen:
            continue
        seen.add(key)
        target_keys.append(key)

    tmp_metadata = _load_jsonl_records(metadata_path)

    resolved_count = 0
    missing_keys: list[dict[str, Any]] = []
    resolved_keys: list[str] = []

    for key in target_keys:
        metadata_record = tmp_metadata.get(key)
        if _metadata_is_missing(metadata_record):
            manifest_item = manifest_lookup.get(key, {})
            missing_keys.append(
                {
                    "key": key,
                    "reason": "missing_in_tmp",
                    "query_title": _query_title_from_manifest(manifest_item),
                    "tmp_source": metadata_record.get("source") if metadata_record else None,
                    "tmp_match_status": metadata_record.get("match_status") if metadata_record else None,
                }
            )
            continue

        resolved_count += 1
        resolved_keys.append(key)

    unresolved_count = len(missing_keys)

    return {
        "paper_id": paper,
        "total_target": len(target_keys),
        "resolved_count": resolved_count,
        "still_missing_count": unresolved_count,
        "resolved_keys": resolved_keys,
        "missing_keys": missing_keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tmp_refs collection against manifest.")
    parser.add_argument("--tmp-root", type=Path, default=Path("tmp_refs"))
    parser.add_argument("--paper-ids", nargs="*", default=None)
    parser.add_argument("--manifest-filename", default="missing_manifest.jsonl")
    parser.add_argument("--metadata-filename", default="title_abstracts_metadata.jsonl")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-markdown", type=Path, default=None)

    args = parser.parse_args()
    args.tmp_root = Path(args.tmp_root)

    if not args.tmp_root.exists() or not args.tmp_root.is_dir():
        raise SystemExit(f"tmp root not found: {args.tmp_root}")

    papers = _iter_papers(args.tmp_root, args.paper_ids)
    if not papers:
        print("[info] no paper directories found")

    results: list[dict[str, Any]] = []
    total_resolved = 0
    total_unresolved = 0
    total_targets = 0

    for paper in papers:
        result = _validate_paper(args.tmp_root, paper, args)
        results.append(result)
        total_resolved += result["resolved_count"]
        total_unresolved += result["still_missing_count"]
        total_targets += result["total_target"]

        print(
            f"[done] {paper}: total={result['total_target']}, "
            f"resolved={result['resolved_count']}, still_missing={result['still_missing_count']}"
        )

    _write_json_report(results, args.output_json)
    _dump_markdown_report(results, args.output_markdown)

    print(
        f"[summary] papers={len(results)}, total_targets={total_targets}, "
        f"resolved={total_resolved}, unresolved={total_unresolved}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
