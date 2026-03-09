#!/usr/bin/env python3
"""Merge repaired metadata from tmp_refs back to refs.

Workflow:
- read target keys from tmp_refs/<paper>/missing_manifest.jsonl
- check tmp metadata/sources/trace/full metadata outputs are non-missing
- write diff report for dry-run and optionally apply with backup
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    v = str(value).strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


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


def _write_jsonl_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


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


def _merge_records(
    original: OrderedDict[str, dict[str, Any]],
    tmp_records: OrderedDict[str, dict[str, Any]],
    keys_to_merge: list[str],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    ordered_keys: list[str] = list(original.keys())
    new_records: list[dict[str, Any]] = []
    replaced_keys: list[str] = []
    appended_keys: list[str] = []

    for key in ordered_keys:
        if key in tmp_records and key in keys_to_merge:
            replaced_keys.append(key)
            new_records.append(tmp_records[key])
        else:
            new_records.append(original[key])

    for key in keys_to_merge:
        if key not in original and key in tmp_records and key not in appended_keys:
            appended_keys.append(key)
            new_records.append(tmp_records[key])

    return new_records, replaced_keys, appended_keys


def _query_title(manifest_lookup: dict[str, dict[str, Any]], key: str) -> str:
    item = manifest_lookup.get(key, {})
    return str(item.get("query_title_original") or item.get("query_title") or item.get("query_title_sanitized") or "")


def _build_manifest_lookup(manifest: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in manifest:
        key = item.get("key")
        if key is None:
            continue
        out[str(key)] = item
    return out


def _collect_resolved_keys(
    manifest_keys: list[str],
    manifest_lookup: dict[str, dict[str, Any]],
    tmp_metadata: OrderedDict[str, dict[str, Any]],
    tmp_sources: OrderedDict[str, dict[str, Any]],
    tmp_traces: OrderedDict[str, dict[str, Any]],
    tmp_full: OrderedDict[str, dict[str, Any]],
    require_full: bool,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    resolved: list[str] = []
    unresolved: list[dict[str, Any]] = []
    unresolved_file_issues: list[dict[str, Any]] = []
    skipped: list[str] = []

    for key in manifest_keys:
        metadata_record = tmp_metadata.get(key)
        if _metadata_is_missing(metadata_record):
            unresolved.append(
                {
                    "key": key,
                    "reason": "tmp_metadata_missing_or_not_matched",
                    "query_title": _query_title(manifest_lookup, key),
                    "match_status": metadata_record.get("match_status") if metadata_record else None,
                    "source": metadata_record.get("source") if metadata_record else None,
                }
            )
            skipped.append(key)
            continue

        file_issues: list[str] = []
        if key not in tmp_sources:
            file_issues.append("tmp_sources_missing")
        if key not in tmp_traces:
            file_issues.append("tmp_source_trace_missing")
        if require_full and key not in tmp_full:
            file_issues.append("tmp_full_metadata_missing")

        if file_issues:
            unresolved_file_issues.append(
                {
                    "key": key,
                    "reason": ",".join(file_issues),
                    "query_title": _query_title(manifest_lookup, key),
                    "metadata": True,
                }
            )
            skipped.append(key)
            continue

        resolved.append(key)

    return resolved, unresolved, unresolved_file_issues, skipped


def _merge_one_paper(
    args: argparse.Namespace,
    refs_root: Path,
    tmp_root: Path,
    paper: str,
    timestamp: str,
) -> dict[str, Any]:
    ref_paper_root = refs_root / paper
    tmp_paper_root = tmp_root / paper
    metadata_root = tmp_paper_root / "metadata"

    manifest = _load_jsonl_list(tmp_paper_root / args.manifest_filename)
    manifest_keys: list[str] = []
    seen: set[str] = set()
    for item in manifest:
        key = item.get("key")
        if key is None:
            continue
        key = str(key)
        if key not in seen:
            seen.add(key)
            manifest_keys.append(key)

    manifest_lookup = _build_manifest_lookup(manifest)

    if not manifest:
        return {
            "paper_id": paper,
            "status": "skip_no_manifest",
            "total_target": 0,
            "resolved_count": 0,
            "still_missing_count": 0,
            "changed": False,
            "unresolved_keys": [],
            "file_diffs": {"metadata": 0, "sources": 0, "source_trace": 0, "full_metadata": 0},
        }

    if not ref_paper_root.exists():
        return {
            "paper_id": paper,
            "status": "ref_missing",
            "total_target": len(manifest_keys),
            "resolved_count": 0,
            "still_missing_count": len(manifest_keys),
            "changed": False,
            "unresolved_keys": [
                {
                    "key": key,
                    "reason": "ref_paper_missing",
                    "query_title": _query_title(manifest_lookup, key),
                }
                for key in manifest_keys
            ],
            "file_diffs": {"metadata": 0, "sources": 0, "source_trace": 0, "full_metadata": 0},
        }

    tmp_metadata = _load_jsonl_records(metadata_root / args.metadata_filename)
    tmp_sources = _load_jsonl_records(metadata_root / args.sources_filename)
    tmp_traces = _load_jsonl_records(metadata_root / args.trace_filename)
    tmp_full = _load_jsonl_records(metadata_root / args.full_metadata_filename)

    resolved_keys, unresolved, file_issue_unresolved, skipped = _collect_resolved_keys(
        manifest_keys,
        manifest_lookup,
        tmp_metadata,
        tmp_sources,
        tmp_traces,
        tmp_full,
        args.require_full_metadata,
    )

    unresolved_keys: list[dict[str, Any]] = unresolved + file_issue_unresolved

    # read original files
    orig_metadata = _load_jsonl_records(ref_paper_root / "metadata" / args.metadata_filename)
    orig_sources = _load_jsonl_records(ref_paper_root / "metadata" / args.sources_filename)
    orig_trace = _load_jsonl_records(ref_paper_root / "metadata" / args.trace_filename)
    orig_full = _load_jsonl_records(ref_paper_root / "metadata" / args.full_metadata_filename)

    # merge only resolved keys
    merged_metadata, replaced_metadata, appended_metadata = _merge_records(orig_metadata, tmp_metadata, resolved_keys)
    merged_sources, replaced_sources, appended_sources = _merge_records(orig_sources, tmp_sources, resolved_keys)
    merged_trace, replaced_trace, appended_trace = _merge_records(orig_trace, tmp_traces, resolved_keys)
    merged_full, replaced_full, appended_full = _merge_records(orig_full, tmp_full, resolved_keys)

    file_diffs = {
        "metadata": len(replaced_metadata),
        "sources": len(replaced_sources),
        "source_trace": len(replaced_trace),
        "full_metadata": len(replaced_full),
    }

    file_appended = {
        "metadata": len(appended_metadata),
        "sources": len(appended_sources),
        "source_trace": len(appended_trace),
        "full_metadata": len(appended_full),
    }

    changed = any(v > 0 or file_appended[k] > 0 for k, v in file_diffs.items())

    if args.dry_run:
        return {
            "paper_id": paper,
            "status": "ready" if changed else "no_change",
            "total_target": len(manifest_keys),
            "resolved_count": len(resolved_keys),
            "still_missing_count": len(unresolved_keys),
            "changed": changed,
            "resolved_keys": resolved_keys,
            "unresolved_keys": unresolved_keys,
            "file_diffs": file_diffs,
            "appended": file_appended,
            "skipped_keys": skipped,
        }

    # apply mode
    backup_paper_root = Path(args.backup_root) / timestamp / paper / "metadata"
    backup_paper_root.mkdir(parents=True, exist_ok=True)

    def _backup_and_write(dest: Path, records: list[dict[str, Any]], filename: str) -> None:
        if dest.exists():
            backup = backup_paper_root / filename
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, backup)
        _write_jsonl_records(dest, records)

    _backup_and_write(
        ref_paper_root / "metadata" / args.metadata_filename,
        merged_metadata,
        args.metadata_filename,
    )
    _backup_and_write(
        ref_paper_root / "metadata" / args.sources_filename,
        merged_sources,
        args.sources_filename,
    )
    _backup_and_write(
        ref_paper_root / "metadata" / args.trace_filename,
        merged_trace,
        args.trace_filename,
    )
    if args.require_full_metadata:
        _backup_and_write(
            ref_paper_root / "metadata" / args.full_metadata_filename,
            merged_full,
            args.full_metadata_filename,
        )

    return {
        "paper_id": paper,
        "status": "applied" if changed else "applied_no_change",
        "total_target": len(manifest_keys),
        "resolved_count": len(resolved_keys),
        "still_missing_count": len(unresolved_keys),
        "changed": changed,
        "resolved_keys": resolved_keys,
        "unresolved_keys": unresolved_keys,
        "file_diffs": file_diffs,
        "appended": file_appended,
        "skipped_keys": skipped,
        "backup_root": str(backup_paper_root),
    }


def _dump_markdown_report(results: list[dict[str, Any]], report_path: Path | None) -> None:
    if report_path is None:
        return

    report_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# metadata merge report\n\n")
        handle.write(f"- generated_at: {now}\n")
        handle.write(f"- total_papers: {len(results)}\n\n")

        for row in results:
            paper = row["paper_id"]
            handle.write(f"## {paper}\n")
            handle.write(f"- status: {row.get('status')}\n")
            handle.write(f"- total_target: {row.get('total_target', 0)}\n")
            handle.write(f"- resolved_count: {row.get('resolved_count', 0)}\n")
            handle.write(f"- still_missing_count: {row.get('still_missing_count', 0)}\n")
            handle.write(f"- changed: {row.get('changed', False)}\n")
            diffs = row.get("file_diffs", {})
            handle.write(
                "- file_updates: metadata={metadata}, sources={sources}, source_trace={source_trace}, full_metadata={full_metadata}\n".format(
                    metadata=diffs.get("metadata", 0),
                    sources=diffs.get("sources", 0),
                    source_trace=diffs.get("source_trace", 0),
                    full_metadata=diffs.get("full_metadata", 0),
                )
            )
            handle.write(
                f"- appendeds: metadata={row.get('appended', {}).get('metadata', 0)}, "
                f"sources={row.get('appended', {}).get('sources', 0)}, "
                f"source_trace={row.get('appended', {}).get('source_trace', 0)}, "
                f"full_metadata={row.get('appended', {}).get('full_metadata', 0)}\n"
            )
            if row.get("unresolved_keys"):
                handle.write("- unresolved keys:\n")
                for item in row["unresolved_keys"]:
                    handle.write(
                        f"  - `{item.get('key')}`: {item.get('reason')} "
                        f"{item.get('query_title', '')}\n"
                    )
            if row.get("backup_root"):
                handle.write(f"- backup: {row['backup_root']}\n")
            handle.write("\n")


def _write_json_report(results: list[dict[str, Any]], report_path: Path | None) -> None:
    if report_path is None:
        return

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge tmp_refs repair outputs back to refs.")
    parser.add_argument("--refs-root", type=Path, default=Path("refs"))
    parser.add_argument("--tmp-root", type=Path, default=Path("tmp_refs"))
    parser.add_argument("--paper-ids", nargs="*", default=None)
    parser.add_argument("--manifest-filename", default="missing_manifest.jsonl")
    parser.add_argument("--metadata-filename", default="title_abstracts_metadata.jsonl")
    parser.add_argument("--sources-filename", default="title_abstracts_sources.jsonl")
    parser.add_argument("--trace-filename", default="title_abstracts_source_trace.jsonl")
    parser.add_argument("--full-metadata-filename", default="title_abstracts_full_metadata.jsonl")
    parser.add_argument(
        "--require-full-metadata",
        type=_parse_bool,
        default=True,
        help="Require title_abstracts_full_metadata.jsonl resolved before merging.",
    )
    parser.add_argument("--backup-root", type=Path, default=Path("issues/metadata_merge_backups"))
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--report-markdown", type=Path, default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=False)
    mode.add_argument("--apply", action="store_true", default=False)

    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        args.dry_run = True

    args.refs_root = Path(args.refs_root)
    args.tmp_root = Path(args.tmp_root)

    if not args.refs_root.exists() or not args.refs_root.is_dir():
        raise SystemExit(f"refs root not found: {args.refs_root}")
    if not args.tmp_root.exists() or not args.tmp_root.is_dir():
        raise SystemExit(f"tmp root not found: {args.tmp_root}")

    papers = _iter_papers(args.tmp_root, args.paper_ids)
    if not papers:
        print("[info] no paper directories found")

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    if args.dry_run:
        if args.report_markdown is None:
            args.report_markdown = Path("issues") / f"metadata_repair_report_{timestamp}.md"
        if args.report_json is None:
            args.report_json = Path("issues") / f"metadata_repair_report_{timestamp}.json"

    results: list[dict[str, Any]] = []
    for paper in papers:
        result = _merge_one_paper(args, args.refs_root, args.tmp_root, paper, timestamp)
        results.append(result)
        print(
            f"[done] {paper}: status={result.get('status')}, total={result.get('total_target')}, "
            f"resolved={result.get('resolved_count')}, still_missing={result.get('still_missing_count')}, "
            f"changed={result.get('changed')}"
        )

    _dump_markdown_report(results, args.report_markdown)
    _write_json_report(results, args.report_json)

    unresolved_total = sum(item.get("still_missing_count", 0) for item in results)
    changed_total = sum(1 for item in results if item.get("changed"))
    print(f"[summary] papers={len(results)}, changed={changed_total}, unresolved_total={unresolved_total}")
    print(f"[summary] report_json={args.report_json}")
    print(f"[summary] report_markdown={args.report_markdown}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
