#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screening.cutoff_time_filter import _parse_candidate_date

DEFAULT_PAPERS = [
    "2303.13365",
    "2306.12834",
    "2307.05527",
    "2310.07264",
    "2312.05172",
    "2401.09244",
    "2405.15604",
    "2407.17844",
    "2409.13738",
    "2503.04799",
    "2507.07741",
    "2507.18910",
    "2509.11446",
    "2510.01145",
    "2511.13936",
    "2601.19926",
]
SUMMARY_FILENAME = "summary.json"
REPORT_FILENAME = "report.md"
YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parser_provenance() -> dict[str, Any]:
    parser_path = REPO_ROOT / "scripts" / "screening" / "cutoff_time_filter.py"
    return {
        "import_target": "scripts.screening.cutoff_time_filter._parse_candidate_date",
        "parser_file": _relative(parser_path),
        "parser_sha256": hashlib.sha256(parser_path.read_bytes()).hexdigest(),
    }


def _read_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL in {path}:{line_no}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SystemExit(f"Expected object JSONL row in {path}:{line_no}")
        rows.append((line_no, payload))
    return rows


def _parse_success_rate(parsed_count: int, total_unique_keys: int) -> float | None:
    if total_unique_keys <= 0:
        return None
    return round(parsed_count / total_unique_keys, 4)


def _classify_published_date(raw_value: Any) -> dict[str, Any]:
    raw = str(raw_value or "").strip()
    if not raw:
        return {
            "parse_status": "missing_empty",
            "published_date_raw": None,
            "published_date_iso": None,
        }

    parsed = _parse_candidate_date(raw)
    if parsed is None:
        return {
            "parse_status": "unparseable",
            "published_date_raw": raw,
            "published_date_iso": None,
        }

    return {
        "parse_status": "parsed",
        "published_date_raw": raw,
        "published_date_iso": parsed.isoformat(),
    }


def _make_missing_file_summary(paper_id: str, metadata_path: Path, detail_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = {
        "paper_id": paper_id,
        "detail_json_path": _relative(detail_path),
        "metadata_path": _relative(metadata_path),
        "input_file_status": "input_file_missing",
        "total_input_rows": 0,
        "total_unique_keys": 0,
        "duplicate_keys_count": 0,
        "duplicate_rows_skipped": 0,
        "duplicate_keys_with_published_date_disagreement_count": 0,
        "duplicate_keys_with_published_date_disagreement": [],
        "parsed_count": 0,
        "unparseable_count": 0,
        "missing_empty_count": 0,
        "parse_success_rate": None,
        "unparseable_raw_strings": {},
    }
    detail = {
        **summary,
        "duplicate_details": [],
        "rows": [],
    }
    return summary, detail


def _audit_paper(paper_id: str, output_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata_path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
    detail_path = output_dir / "papers" / f"{paper_id}.json"
    if not metadata_path.exists():
        return _make_missing_file_summary(paper_id, metadata_path, detail_path)

    input_rows = _read_jsonl(metadata_path)
    first_by_key: dict[str, tuple[int, dict[str, Any]]] = {}
    duplicate_details: dict[str, dict[str, Any]] = {}

    for line_no, row in input_rows:
        key = str(row.get("key") or "").strip()
        if not key:
            raise SystemExit(f"{metadata_path}:{line_no} is missing a usable key")
        if key not in first_by_key:
            first_by_key[key] = (line_no, row)
            continue

        first_line_no, first_row = first_by_key[key]
        detail = duplicate_details.setdefault(
            key,
            {
                "key": key,
                "first_occurrence_line": first_line_no,
                "first_occurrence_published_date_raw": str(first_row.get("published_date") or "").strip() or None,
                "duplicate_occurrences": [],
            },
        )
        detail["duplicate_occurrences"].append(
            {
                "line": line_no,
                "published_date_raw": str(row.get("published_date") or "").strip() or None,
            }
        )

    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    unparseable_raw_strings: dict[str, dict[str, Any]] = {}

    for key, (line_no, row) in first_by_key.items():
        classified = _classify_published_date(row.get("published_date"))
        status = str(classified["parse_status"])
        status_counts[status] += 1
        row_payload = {
            "key": key,
            "source_line": line_no,
            "published_date_raw": classified["published_date_raw"],
            "published_date_iso": classified["published_date_iso"],
            "parse_status": status,
        }
        rows.append(row_payload)

        if status != "unparseable":
            continue
        raw = str(classified["published_date_raw"])
        bucket = unparseable_raw_strings.setdefault(raw, {"count": 0, "example_keys": []})
        bucket["count"] += 1
        if len(bucket["example_keys"]) < 5:
            bucket["example_keys"].append(key)

    duplicate_detail_rows: list[dict[str, Any]] = []
    disagreement_keys: list[str] = []
    for key in sorted(duplicate_details):
        detail = duplicate_details[key]
        published_date_values = []
        first_value = detail["first_occurrence_published_date_raw"]
        published_date_values.append(first_value)
        published_date_values.extend(item["published_date_raw"] for item in detail["duplicate_occurrences"])
        normalized_values = [value for value in published_date_values]
        disagree = len(set(normalized_values)) > 1
        if disagree:
            disagreement_keys.append(key)
        duplicate_detail_rows.append(
            {
                **detail,
                "duplicate_line_numbers": [item["line"] for item in detail["duplicate_occurrences"]],
                "published_date_values": sorted({value for value in normalized_values}, key=lambda value: "" if value is None else value),
                "published_date_disagree": disagree,
            }
        )

    sorted_unparseable = dict(
        sorted(
            unparseable_raw_strings.items(),
            key=lambda item: (-int(item[1]["count"]), item[0]),
        )
    )
    duplicate_rows_skipped = sum(len(item["duplicate_occurrences"]) for item in duplicate_detail_rows)
    summary = {
        "paper_id": paper_id,
        "detail_json_path": _relative(detail_path),
        "metadata_path": _relative(metadata_path),
        "input_file_status": "ok",
        "total_input_rows": len(input_rows),
        "total_unique_keys": len(first_by_key),
        "duplicate_keys_count": len(duplicate_detail_rows),
        "duplicate_rows_skipped": duplicate_rows_skipped,
        "duplicate_keys_with_published_date_disagreement_count": len(disagreement_keys),
        "duplicate_keys_with_published_date_disagreement": disagreement_keys,
        "parsed_count": status_counts.get("parsed", 0),
        "unparseable_count": status_counts.get("unparseable", 0),
        "missing_empty_count": status_counts.get("missing_empty", 0),
        "parse_success_rate": _parse_success_rate(status_counts.get("parsed", 0), len(first_by_key)),
        "unparseable_raw_strings": sorted_unparseable,
    }
    detail = {
        **summary,
        "duplicate_details": duplicate_detail_rows,
        "rows": rows,
    }
    return summary, detail


def _aggregate_global_summary(paper_order: list[str], paper_summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    total_input_rows = 0
    total_unique_keys = 0
    total_duplicate_keys = 0
    total_duplicate_rows_skipped = 0
    total_parsed = 0
    total_unparseable = 0
    total_missing_empty = 0
    papers_with_missing_input_files: list[str] = []
    all_unparseable_raw_strings: dict[str, dict[str, Any]] = {}

    for paper_id in paper_order:
        paper = paper_summaries[paper_id]
        if paper["input_file_status"] != "ok":
            papers_with_missing_input_files.append(paper_id)
            continue
        total_input_rows += int(paper["total_input_rows"])
        total_unique_keys += int(paper["total_unique_keys"])
        total_duplicate_keys += int(paper["duplicate_keys_count"])
        total_duplicate_rows_skipped += int(paper["duplicate_rows_skipped"])
        total_parsed += int(paper["parsed_count"])
        total_unparseable += int(paper["unparseable_count"])
        total_missing_empty += int(paper["missing_empty_count"])

        for raw, item in paper["unparseable_raw_strings"].items():
            bucket = all_unparseable_raw_strings.setdefault(raw, {"count": 0, "papers": [], "example_keys": []})
            bucket["count"] += int(item["count"])
            if paper_id not in bucket["papers"]:
                bucket["papers"].append(paper_id)
            for key in item["example_keys"]:
                if key not in bucket["example_keys"] and len(bucket["example_keys"]) < 8:
                    bucket["example_keys"].append(key)

    sorted_all_unparseable = dict(
        sorted(
            all_unparseable_raw_strings.items(),
            key=lambda item: (-int(item[1]["count"]), item[0]),
        )
    )
    most_affected_papers = [
        {
            "paper_id": paper_id,
            "unparseable_count": int(paper_summaries[paper_id]["unparseable_count"]),
            "parse_success_rate": paper_summaries[paper_id]["parse_success_rate"],
        }
        for paper_id in paper_order
        if paper_summaries[paper_id]["input_file_status"] == "ok" and int(paper_summaries[paper_id]["unparseable_count"]) > 0
    ]
    most_affected_papers.sort(
        key=lambda item: (-int(item["unparseable_count"]), item["parse_success_rate"], item["paper_id"])
    )
    papers_with_year_month_unparseable = [
        {
            "paper_id": paper_id,
            "year_month_unparseable_count": sum(
                int(item["count"])
                for raw, item in paper_summaries[paper_id]["unparseable_raw_strings"].items()
                if YEAR_MONTH_RE.match(raw)
            ),
        }
        for paper_id in paper_order
        if paper_summaries[paper_id]["input_file_status"] == "ok"
    ]
    papers_with_year_month_unparseable = [
        item for item in papers_with_year_month_unparseable if item["year_month_unparseable_count"] > 0
    ]
    papers_with_year_month_unparseable.sort(
        key=lambda item: (-int(item["year_month_unparseable_count"]), item["paper_id"])
    )

    return {
        "papers_requested": len(paper_order),
        "papers_with_input": len(paper_order) - len(papers_with_missing_input_files),
        "papers_with_missing_input_files": papers_with_missing_input_files,
        "total_input_rows": total_input_rows,
        "total_unique_keys": total_unique_keys,
        "total_duplicate_keys": total_duplicate_keys,
        "total_duplicate_rows_skipped": total_duplicate_rows_skipped,
        "total_parsed": total_parsed,
        "total_unparseable": total_unparseable,
        "total_missing_empty": total_missing_empty,
        "overall_parse_success_rate": _parse_success_rate(total_parsed, total_unique_keys),
        "all_unparseable_raw_strings": sorted_all_unparseable,
        "top_unparseable_raw_strings": [
            {"raw": raw, **payload}
            for raw, payload in list(sorted_all_unparseable.items())[:20]
        ],
        "most_affected_papers": most_affected_papers,
        "papers_with_year_month_unparseable": papers_with_year_month_unparseable,
    }


def _render_run_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Publication Date Parse Audit",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Output dir: `{summary['output_dir']}`",
        f"- Parser target: `{summary['parser_provenance']['import_target']}`",
        f"- Parser file: `{summary['parser_provenance']['parser_file']}`",
        f"- Parser sha256: `{summary['parser_provenance']['parser_sha256']}`",
        "",
        "## Global Summary",
        "",
        f"- Papers requested: `{summary['global_summary']['papers_requested']}`",
        f"- Papers with input files: `{summary['global_summary']['papers_with_input']}`",
        f"- Papers missing input files: `{len(summary['global_summary']['papers_with_missing_input_files'])}`",
        f"- Total input rows: `{summary['global_summary']['total_input_rows']}`",
        f"- Total unique keys: `{summary['global_summary']['total_unique_keys']}`",
        f"- Total duplicate keys: `{summary['global_summary']['total_duplicate_keys']}`",
        f"- Total duplicate rows skipped: `{summary['global_summary']['total_duplicate_rows_skipped']}`",
        f"- Parsed count: `{summary['global_summary']['total_parsed']}`",
        f"- Unparseable count: `{summary['global_summary']['total_unparseable']}`",
        f"- Missing/empty count: `{summary['global_summary']['total_missing_empty']}`",
        f"- Parse success rate: `{summary['global_summary']['overall_parse_success_rate']}`",
        "",
        "## Per-Paper Table",
        "",
        "| Paper | Input | Rows | Unique | Dup keys | Dup rows | Parsed | Unparseable | Missing | Success rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for paper_id in summary["paper_order"]:
        paper = summary["papers"][paper_id]
        lines.append(
            f"| `{paper_id}` | {paper['input_file_status']} | {paper['total_input_rows']} | "
            f"{paper['total_unique_keys']} | {paper['duplicate_keys_count']} | {paper['duplicate_rows_skipped']} | "
            f"{paper['parsed_count']} | {paper['unparseable_count']} | {paper['missing_empty_count']} | "
            f"{paper['parse_success_rate']} |"
        )

    lines.extend(["", "## Missing Input Files", ""])
    if summary["global_summary"]["papers_with_missing_input_files"]:
        for paper_id in summary["global_summary"]["papers_with_missing_input_files"]:
            lines.append(f"- `{paper_id}`")
    else:
        lines.append("- `(none)`")

    lines.extend(["", "## Top Unparseable Raw Strings", ""])
    if summary["global_summary"]["top_unparseable_raw_strings"]:
        for item in summary["global_summary"]["top_unparseable_raw_strings"]:
            lines.append(
                f"- `{item['raw']}`: count `{item['count']}`, papers `{', '.join(item['papers'])}`, "
                f"example keys `{', '.join(item['example_keys'])}`"
            )
    else:
        lines.append("- `(none)`")

    lines.extend(["", "## Most Affected Papers", ""])
    if summary["global_summary"]["most_affected_papers"]:
        for item in summary["global_summary"]["most_affected_papers"]:
            lines.append(
                f"- `{item['paper_id']}`: unparseable `{item['unparseable_count']}`, "
                f"success rate `{item['parse_success_rate']}`"
            )
    else:
        lines.append("- `(none)`")

    for paper_id in summary["paper_order"]:
        paper = summary["papers"][paper_id]
        lines.extend(["", f"## {paper_id}", ""])
        lines.append(f"- Input status: `{paper['input_file_status']}`")
        lines.append(f"- Metadata path: `{paper['metadata_path']}`")
        lines.append(f"- Detail JSON: `{paper['detail_json_path']}`")
        if paper["input_file_status"] != "ok":
            continue
        lines.append(f"- Duplicate keys: `{paper['duplicate_keys_count']}`")
        lines.append(f"- Duplicate rows skipped: `{paper['duplicate_rows_skipped']}`")
        if paper["duplicate_keys_with_published_date_disagreement"]:
            lines.append(
                "- Duplicate keys with conflicting `published_date`: "
                f"`{', '.join(paper['duplicate_keys_with_published_date_disagreement'])}`"
            )
        else:
            lines.append("- Duplicate keys with conflicting `published_date`: `(none)`")
        if paper["unparseable_raw_strings"]:
            lines.append("- Unparseable raw strings:")
            for raw, item in paper["unparseable_raw_strings"].items():
                lines.append(
                    f"  - `{raw}`: count `{item['count']}`, example keys `{', '.join(item['example_keys'])}`"
                )
        else:
            lines.append("- Unparseable raw strings: `(none)`")

    return "\n".join(lines) + "\n"


def _summary_path(path_or_dir: str) -> Path:
    path = Path(path_or_dir)
    if path.is_dir():
        return path / SUMMARY_FILENAME
    return path


def _year_month_count(unparseable_raw_strings: dict[str, dict[str, Any]]) -> int:
    return sum(int(item["count"]) for raw, item in unparseable_raw_strings.items() if YEAR_MONTH_RE.match(raw))


def _build_compare_summary(before: dict[str, Any], after: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    paper_order = list(before["paper_order"])
    per_paper_changes: dict[str, dict[str, Any]] = {}
    papers_improved: list[str] = []
    papers_unchanged: list[str] = []
    papers_with_remaining_unparseable: list[str] = []
    papers_with_missing_input: list[str] = []

    for paper_id in paper_order:
        before_paper = before["papers"][paper_id]
        after_paper = after["papers"][paper_id]
        change = {
            "paper_id": paper_id,
            "input_file_status_before": before_paper["input_file_status"],
            "input_file_status_after": after_paper["input_file_status"],
            "parsed_before": before_paper["parsed_count"],
            "parsed_after": after_paper["parsed_count"],
            "parsed_delta": after_paper["parsed_count"] - before_paper["parsed_count"],
            "unparseable_before": before_paper["unparseable_count"],
            "unparseable_after": after_paper["unparseable_count"],
            "unparseable_delta": after_paper["unparseable_count"] - before_paper["unparseable_count"],
            "missing_empty_before": before_paper["missing_empty_count"],
            "missing_empty_after": after_paper["missing_empty_count"],
            "parse_success_rate_before": before_paper["parse_success_rate"],
            "parse_success_rate_after": after_paper["parse_success_rate"],
            "year_month_unparseable_before": _year_month_count(before_paper["unparseable_raw_strings"]),
            "year_month_unparseable_after": _year_month_count(after_paper["unparseable_raw_strings"]),
        }
        per_paper_changes[paper_id] = change

        if after_paper["input_file_status"] != "ok":
            papers_with_missing_input.append(paper_id)
            continue
        if change["unparseable_delta"] < 0 or change["parsed_delta"] > 0:
            papers_improved.append(paper_id)
        elif change["unparseable_delta"] == 0 and change["parsed_delta"] == 0:
            papers_unchanged.append(paper_id)
        if after_paper["unparseable_count"] > 0:
            papers_with_remaining_unparseable.append(paper_id)

    before_unparseable = before["global_summary"]["all_unparseable_raw_strings"]
    after_unparseable = after["global_summary"]["all_unparseable_raw_strings"]
    raw_keys = sorted(set(before_unparseable) | set(after_unparseable))
    resolved_unparseable_raw_strings = []
    partially_resolved_unparseable_raw_strings = []
    remaining_unparseable_raw_strings = []

    for raw in raw_keys:
        before_item = before_unparseable.get(raw)
        after_item = after_unparseable.get(raw)
        before_count = 0 if before_item is None else int(before_item["count"])
        after_count = 0 if after_item is None else int(after_item["count"])
        payload = {
            "raw": raw,
            "before_count": before_count,
            "after_count": after_count,
            "before_papers": [] if before_item is None else before_item["papers"],
            "after_papers": [] if after_item is None else after_item["papers"],
        }
        if before_count > 0 and after_count == 0:
            resolved_unparseable_raw_strings.append(payload)
        elif before_count > after_count > 0:
            partially_resolved_unparseable_raw_strings.append(payload)
        if after_count > 0:
            remaining_unparseable_raw_strings.append(payload)

    compare_summary = {
        "generated_at": _utc_now(),
        "output_dir": _relative(output_dir),
        "before_summary_path": before["summary_path"],
        "after_summary_path": after["summary_path"],
        "before_parser_provenance": before["parser_provenance"],
        "after_parser_provenance": after["parser_provenance"],
        "paper_order": paper_order,
        "per_paper_changes": per_paper_changes,
        "global_changes": {
            "total_parsed_before": before["global_summary"]["total_parsed"],
            "total_parsed_after": after["global_summary"]["total_parsed"],
            "total_parsed_delta": after["global_summary"]["total_parsed"] - before["global_summary"]["total_parsed"],
            "total_unparseable_before": before["global_summary"]["total_unparseable"],
            "total_unparseable_after": after["global_summary"]["total_unparseable"],
            "total_unparseable_delta": after["global_summary"]["total_unparseable"] - before["global_summary"]["total_unparseable"],
            "resolved_unparseable_raw_strings": resolved_unparseable_raw_strings,
            "partially_resolved_unparseable_raw_strings": partially_resolved_unparseable_raw_strings,
            "remaining_unparseable_raw_strings": remaining_unparseable_raw_strings,
            "papers_improved": papers_improved,
            "papers_unchanged": papers_unchanged,
            "papers_with_remaining_unparseable": papers_with_remaining_unparseable,
            "papers_with_missing_input": papers_with_missing_input,
            "year_month_unparseable_before": sum(
                int(item["count"])
                for raw, item in before_unparseable.items()
                if YEAR_MONTH_RE.match(raw)
            ),
            "year_month_unparseable_after": sum(
                int(item["count"])
                for raw, item in after_unparseable.items()
                if YEAR_MONTH_RE.match(raw)
            ),
            "papers_with_year_month_issues_before": [
                item["paper_id"] for item in before["global_summary"]["papers_with_year_month_unparseable"]
            ],
            "papers_with_year_month_issues_after": [
                item["paper_id"] for item in after["global_summary"]["papers_with_year_month_unparseable"]
            ],
            "paper_2601_19926_2020_12_before": before["papers"]["2601.19926"]["unparseable_raw_strings"].get("2020-12", {}).get("count", 0),
            "paper_2601_19926_2020_12_after": after["papers"]["2601.19926"]["unparseable_raw_strings"].get("2020-12", {}).get("count", 0),
            "paper_2601_19926_2020_12_resolved": (
                before["papers"]["2601.19926"]["unparseable_raw_strings"].get("2020-12", {}).get("count", 0) > 0
                and after["papers"]["2601.19926"]["unparseable_raw_strings"].get("2020-12", {}).get("count", 0) == 0
            ),
        },
    }
    return compare_summary


def _render_compare_report(summary: dict[str, Any]) -> str:
    global_changes = summary["global_changes"]
    lines = [
        "# Publication Date Parse Audit Comparison",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Output dir: `{summary['output_dir']}`",
        f"- Before summary: `{summary['before_summary_path']}`",
        f"- After summary: `{summary['after_summary_path']}`",
        f"- Before parser sha256: `{summary['before_parser_provenance']['parser_sha256']}`",
        f"- After parser sha256: `{summary['after_parser_provenance']['parser_sha256']}`",
        "",
        "## Global Delta",
        "",
        f"- Total parsed: `{global_changes['total_parsed_before']}` -> `{global_changes['total_parsed_after']}`",
        f"- Total unparseable: `{global_changes['total_unparseable_before']}` -> `{global_changes['total_unparseable_after']}`",
        f"- `%Y-%m`-shaped unparseable count: `{global_changes['year_month_unparseable_before']}` -> `{global_changes['year_month_unparseable_after']}`",
        f"- `2601.19926` raw `2020-12`: `{global_changes['paper_2601_19926_2020_12_before']}` -> "
        f"`{global_changes['paper_2601_19926_2020_12_after']}`",
        f"- `2601.19926` `2020-12` resolved: `{global_changes['paper_2601_19926_2020_12_resolved']}`",
        "",
        "## Per-Paper Changes",
        "",
        "| Paper | Input | Parsed before | Parsed after | Delta | Unparseable before | Unparseable after | Delta |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for paper_id in summary["paper_order"]:
        item = summary["per_paper_changes"][paper_id]
        lines.append(
            f"| `{paper_id}` | {item['input_file_status_after']} | {item['parsed_before']} | {item['parsed_after']} | "
            f"{item['parsed_delta']} | {item['unparseable_before']} | {item['unparseable_after']} | "
            f"{item['unparseable_delta']} |"
        )

    lines.extend(["", "## Resolved Raw Strings", ""])
    if global_changes["resolved_unparseable_raw_strings"]:
        for item in global_changes["resolved_unparseable_raw_strings"]:
            lines.append(
                f"- `{item['raw']}`: before `{item['before_count']}`, after `{item['after_count']}`, "
                f"affected papers before `{', '.join(item['before_papers'])}`"
            )
    else:
        lines.append("- `(none)`")

    lines.extend(["", "## Remaining Unparseable Raw Strings", ""])
    if global_changes["remaining_unparseable_raw_strings"]:
        for item in global_changes["remaining_unparseable_raw_strings"]:
            lines.append(
                f"- `{item['raw']}`: before `{item['before_count']}`, after `{item['after_count']}`, "
                f"affected papers after `{', '.join(item['after_papers'])}`"
            )
    else:
        lines.append("- `(none)`")

    lines.extend(["", "## `%Y-%m` Findings", ""])
    lines.append(
        "- Papers with `%Y-%m`-shaped failures before: "
        f"`{', '.join(global_changes['papers_with_year_month_issues_before']) or '(none)'}`"
    )
    lines.append(
        "- Papers with `%Y-%m`-shaped failures after: "
        f"`{', '.join(global_changes['papers_with_year_month_issues_after']) or '(none)'}`"
    )
    lines.append(
        "- Papers improved: "
        f"`{', '.join(global_changes['papers_improved']) or '(none)'}`"
    )
    lines.append(
        "- Papers unchanged: "
        f"`{', '.join(global_changes['papers_unchanged']) or '(none)'}`"
    )
    lines.append(
        "- Papers still unparseable after fix: "
        f"`{', '.join(global_changes['papers_with_remaining_unparseable']) or '(none)'}`"
    )
    lines.append(
        "- Papers missing input files: "
        f"`{', '.join(global_changes['papers_with_missing_input']) or '(none)'}`"
    )
    return "\n".join(lines) + "\n"


def _run_audit(args: argparse.Namespace) -> int:
    output_dir = REPO_ROOT / args.output_dir
    papers_dir = output_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    paper_order = list(args.papers)
    paper_summaries: dict[str, dict[str, Any]] = {}

    for paper_id in paper_order:
        summary, detail = _audit_paper(paper_id, output_dir)
        paper_summaries[paper_id] = summary
        detail_path = output_dir / "papers" / f"{paper_id}.json"
        _write_json(detail_path, detail)

    run_summary = {
        "generated_at": _utc_now(),
        "output_dir": _relative(output_dir),
        "parser_provenance": _parser_provenance(),
        "paper_order": paper_order,
        "papers": paper_summaries,
        "global_summary": _aggregate_global_summary(paper_order, paper_summaries),
    }
    _write_json(output_dir / SUMMARY_FILENAME, run_summary)
    (output_dir / REPORT_FILENAME).write_text(_render_run_report(run_summary), encoding="utf-8")
    return 0


def _load_summary_for_compare(path_or_dir: str) -> dict[str, Any]:
    summary_path = _summary_path(path_or_dir)
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["summary_path"] = _relative(summary_path)
    return payload


def _run_compare(args: argparse.Namespace) -> int:
    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    before_summary = _load_summary_for_compare(args.before)
    after_summary = _load_summary_for_compare(args.after)
    compare_summary = _build_compare_summary(before_summary, after_summary, output_dir)
    _write_json(output_dir / SUMMARY_FILENAME, compare_summary)
    (output_dir / REPORT_FILENAME).write_text(_render_compare_report(compare_summary), encoding="utf-8")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit publication date parser coverage and compare before/after runs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an audit with the live parser.")
    run_parser.add_argument(
        "--papers",
        nargs="*",
        default=DEFAULT_PAPERS,
        help="Paper IDs to audit.",
    )
    run_parser.add_argument(
        "--output-dir",
        default=f"screening/results/publication_date_parse_audit_{datetime.now().date().isoformat()}",
        help="Directory to write run artifacts into.",
    )
    run_parser.set_defaults(func=_run_audit)

    compare_parser = subparsers.add_parser("compare", help="Compare two saved audit summaries.")
    compare_parser.add_argument("--before", required=True, help="Baseline summary path or directory.")
    compare_parser.add_argument("--after", required=True, help="After-fix summary path or directory.")
    compare_parser.add_argument(
        "--output-dir",
        default=f"screening/results/publication_date_parse_audit_{datetime.now().date().isoformat()}",
        help="Directory to write comparison artifacts into.",
    )
    compare_parser.set_defaults(func=_run_compare)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
