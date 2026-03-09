#!/usr/bin/env python3
"""Build temporary reference_oracle inputs for missing metadata keys.

This script scans `refs/<paper>/metadata/title_abstracts_metadata.jsonl` and
compares against `bib/per_SR_cleaned/<paper>/reference_oracle.jsonl` to extract
"missing" and "absent" keys, then writes only those keys into
`tmp_refs/<paper>/reference_oracle.jsonl`.

Output convention:
- The generated oracle keeps all original fields.
- Original query title is preserved in `query_title_original`.
- If cleanup is enabled, `query_title` is replaced by a normalized title and
  `query_title_sanitized` is added.
- `missing_manifest.jsonl` contains per-key reasons and traceability fields.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import OrderedDict
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
LATEX_COMMAND_WITH_ARG_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]+)\}")
LATEX_COMMAND_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?")
LATEX_ACCENT_IN_BRACES_RE = re.compile(r"\{\\[`'^\"~=.](.)\}")
LATEX_ACCENT_RE = re.compile(r"\{\\([a-zA-Z]{1,4})\{(.)\}\}")
LATEX_ESCAPED_CHAR_RE = re.compile(r"\\[`'^\"~=.]" )


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    v = str(value).strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def _strip_ws(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _load_jsonl_records(path: Path) -> OrderedDict[str, dict[str, Any]]:
    records: OrderedDict[str, dict[str, Any]] = OrderedDict()
    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = record.get("key")
            if key is None:
                continue
            records[str(key)] = record

    return records


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


def _write_jsonl_records(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _metadata_record_is_missing(record: dict[str, Any] | None) -> bool:
    if record is None:
        return True
    source = (record.get("source") or "").strip().lower()
    match_status = (record.get("match_status") or "").strip().lower()
    return match_status == "missing" or source in {"", "missing", "none", "null"}


def _sanitize_query_title(value: Any) -> str:
    if value is None:
        return ""
    cleaned = html.unescape(str(value))
    cleaned = cleaned.replace('\\"', '"')
    cleaned = re.sub(r"\\showarticletitle\{([^{}]+)\}", r"\1", cleaned)
    cleaned = LATEX_COMMAND_WITH_ARG_RE.sub(r"\1", cleaned)
    cleaned = LATEX_COMMAND_RE.sub("", cleaned)
    cleaned = LATEX_ACCENT_IN_BRACES_RE.sub(r"\1", cleaned)
    cleaned = LATEX_ACCENT_RE.sub(r"\2", cleaned)
    cleaned = LATEX_ESCAPED_CHAR_RE.sub("", cleaned)
    cleaned = cleaned.replace("\\\\_", "_")
    cleaned = cleaned.replace("\\_", " ")
    cleaned = cleaned.replace("\\n", " ")
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = cleaned.replace("\\", "")
    cleaned = cleaned.replace('"', " ")
    cleaned = re.sub(r"[\s,]*(19|20)\d{2}\s*$", "", cleaned)
    return _strip_ws(cleaned)


def _extract_title_from_raw_local(raw: Any) -> str:
    if not isinstance(raw, dict):
        return ""

    local = raw.get("local")
    if not local:
        return ""

    candidate_blobs: list[str] = []
    if isinstance(local, str):
        candidate_blobs.append(local)
    elif isinstance(local, dict):
        direct_title = local.get("title")
        if isinstance(direct_title, str):
            candidate_blobs.append(direct_title)
        for value in local.values():
            if isinstance(value, str) and ("title" in value.lower() or "\\showarticletitle" in value):
                candidate_blobs.append(value)

    if not candidate_blobs:
        return ""

    title_kv_re = re.compile(r"(?is)\btitle\s*=\s*(?:\{(?P<braced>.*?)\}|\"(?P<quoted>.*?)\")\s*,?")
    title_line_re = re.compile(r"(?i)^\s*title\s*=\s*(.+?)\s*(,|$)")
    for blob in candidate_blobs:
        normalized_blob = blob.replace("\\{", "{").replace("\\}", "}")
        if "showarticletitle" in normalized_blob.lower():
            marker = "showarticletitle"
            marker_idx = normalized_blob.lower().find(marker)
            if marker_idx != -1:
                brace_start = normalized_blob.find("{", marker_idx)
                brace_end = normalized_blob.find("}", brace_start + 1)
                if brace_start != -1 and brace_end != -1:
                    show_title = normalized_blob[brace_start + 1 : brace_end]
                    if show_title.strip():
                        return _strip_ws(show_title)

        for line in normalized_blob.splitlines():
            m = title_line_re.search(line)
            if not m:
                continue
            title_expr = m.group(1).strip()
            if not title_expr:
                continue
            if title_expr.startswith('"') and title_expr.endswith('"'):
                title_expr = title_expr[1:-1]
            title_expr = title_expr.replace("{", "").replace("}", "")
            title_expr = LATEX_COMMAND_WITH_ARG_RE.sub(r"\1", title_expr)
            title_expr = LATEX_COMMAND_RE.sub("", title_expr)
            if title_expr:
                return _strip_ws(title_expr)

        for match in title_kv_re.finditer(blob):
            title = (match.group("braced") or "").strip()
            if title and title.startswith('"') and title.endswith('"'):
                title = title[1:-1]
            if not title and match.group("quoted"):
                title = match.group("quoted").strip().strip('"')
            if title:
                return _strip_ws(title)

    return ""


def _get_preferred_query_title(entry: dict[str, Any]) -> str:
    original_query_title = entry.get("query_title")
    raw_title = _extract_title_from_raw_local(entry.get("raw"))
    if raw_title:
        return raw_title
    if original_query_title:
        return original_query_title
    return ""


def _iter_arxiv_papers(refs_root: Path, paper_ids: list[str] | None) -> list[str]:
    papers: list[str] = []
    allowed = None if not paper_ids else set(paper_ids)

    for child in sorted(refs_root.iterdir()):
        if not child.is_dir():
            continue
        if not ARXIV_ID_RE.match(child.name):
            continue
        if allowed is not None and child.name not in allowed:
            continue
        papers.append(child.name)

    return papers


def _build_targets_for_paper(
    paper_id: str,
    oracle_records: OrderedDict[str, dict[str, Any]],
    metadata_records: OrderedDict[str, dict[str, Any]],
    include_absent: bool,
    cleanup_query_title: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest: list[dict[str, Any]] = []
    tmp_records: list[dict[str, Any]] = []

    now = datetime.now(timezone.utc).isoformat()

    for key, entry in oracle_records.items():
        metadata_record = metadata_records.get(key)
        has_metadata = metadata_record is not None

        if has_metadata:
            if not _metadata_record_is_missing(metadata_record):
                continue
            reason = "metadata_missing_status"
        else:
            if not include_absent:
                continue
            reason = "metadata_key_absent"

        source = metadata_record.get("source") if metadata_record else None
        match_status = metadata_record.get("match_status") if metadata_record else None

        original_query_title = entry.get("query_title")
        prepared_query_title = _get_preferred_query_title(entry)
        prepared_source = "raw_local" if _extract_title_from_raw_local(entry.get("raw")) else "original"
        sanitized_query_title = ""

        if cleanup_query_title:
            sanitized_query_title = _sanitize_query_title(prepared_query_title)
            if sanitized_query_title:
                prepared_query_title = sanitized_query_title

        tmp_entry = dict(entry)
        tmp_entry["query_title_original"] = original_query_title
        tmp_entry["query_title_sanitized"] = sanitized_query_title or _strip_ws(prepared_query_title)
        tmp_entry["query_title"] = prepared_query_title
        tmp_entry["tmp_query_title_source"] = prepared_source
        tmp_entry["tmp_repair_reason"] = reason
        tmp_entry["tmp_generated_at"] = now

        manifest_entry: dict[str, Any] = {
            "paper_id": paper_id,
            "key": key,
            "reason": reason,
            "has_metadata_entry": has_metadata,
            "metadata_source": source,
            "metadata_match_status": match_status,
            "query_title_original": original_query_title,
            "query_title_sanitized": tmp_entry["query_title_sanitized"],
            "query_title_source": prepared_source,
        }

        tmp_records.append(tmp_entry)
        manifest.append(manifest_entry)

    return tmp_records, manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build tmp_refs containing only missing/absent SR reference entries."
    )
    parser.add_argument("--refs-root", type=Path, default=Path("refs"))
    parser.add_argument("--oracle-root", type=Path, default=Path("bib/per_SR_cleaned"))
    parser.add_argument("--tmp-root", type=Path, default=Path("tmp_refs"))
    parser.add_argument("--paper-ids", nargs="*", default=None)
    parser.add_argument("--include-absent-keys", type=_parse_bool, default=True)
    parser.add_argument("--cleanup-query-title", type=_parse_bool, default=True)
    parser.add_argument("--write-manifest", type=_parse_bool, default=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    args.refs_root = Path(args.refs_root)
    args.oracle_root = Path(args.oracle_root)
    args.tmp_root = Path(args.tmp_root)

    if not args.refs_root.exists() or not args.refs_root.is_dir():
        raise SystemExit(f"refs root not found or not a directory: {args.refs_root}")
    if not args.oracle_root.exists() or not args.oracle_root.is_dir():
        raise SystemExit(f"oracle root not found or not a directory: {args.oracle_root}")

    total_papers = 0
    total_missing = 0
    total_absent = 0
    total_written = 0

    paper_ids = _iter_arxiv_papers(args.refs_root, args.paper_ids)
    if not paper_ids:
        print("[info] no matching paper ids")
        return 0

    for paper in paper_ids:
        refs_meta_path = args.refs_root / paper / "metadata" / "title_abstracts_metadata.jsonl"
        oracle_path = args.oracle_root / paper / "reference_oracle.jsonl"

        if not oracle_path.exists():
            print(f"[skip] {paper}: missing oracle -> {oracle_path}")
            continue

        oracle_records = _load_jsonl_records(oracle_path)
        metadata_records = _load_jsonl_records(refs_meta_path)

        tmp_records, manifest = _build_targets_for_paper(
            paper,
            oracle_records,
            metadata_records,
            include_absent=args.include_absent_keys,
            cleanup_query_title=args.cleanup_query_title,
        )

        missing_count = sum(1 for item in manifest if item["has_metadata_entry"])
        absent_count = sum(1 for item in manifest if not item["has_metadata_entry"])
        total_papers += 1
        total_missing += missing_count
        total_absent += absent_count

        if args.dry_run:
            raw = sum(1 for item in manifest if item.get("query_title_source") == "raw_local")
            print(
                f"[dry-run] {paper}: total={len(oracle_records)} "
                f"targets={len(tmp_records)} (missing={missing_count}, absent={absent_count}, raw_title={raw})"
            )
            for item in manifest[:5]:
                print(
                    f"         - {item['key']}: reason={item['reason']} "
                    f"metadata={item['metadata_match_status']} source={item['metadata_source']} "
                    f"qt_source={item.get('query_title_source')}"
                )
            if len(manifest) > 5:
                print(f"         ... and {len(manifest)-5} more")
            continue

        tmp_paper_root = args.tmp_root / paper
        tmp_oracle_path = tmp_paper_root / "reference_oracle.jsonl"
        tmp_manifest_path = tmp_paper_root / "missing_manifest.jsonl"

        _write_jsonl_records(tmp_oracle_path, tmp_records)
        if args.write_manifest:
            _write_jsonl_records(tmp_manifest_path, manifest)

        total_written += len(tmp_records)
        print(
            f"[write] {paper}: targets={len(tmp_records)} "
            f"(missing={missing_count}, absent={absent_count}) -> {tmp_oracle_path}"
        )

    print(
        f"[summary] papers={total_papers}, missing={total_missing}, "
        f"absent={total_absent}, total_targets={total_missing + total_absent}, written={total_written}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
