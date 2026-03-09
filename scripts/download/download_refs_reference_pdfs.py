#!/usr/bin/env python3
"""Download reference PDFs for arXiv-style SR folders under refs/.

The script reads ``metadata/title_abstracts_full_metadata.jsonl`` from each target
SR folder, converts rows to a CSV accepted by
``find_pdf/download_remaining_pdfs.py``, and runs repeated retry rounds until all
references succeed or ``--max-rounds`` is reached.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import signal
import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set


ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
MIN_VALID_PDF_BYTES = 8_000
DEFAULT_INCLUDE_SOURCES = "crossref,openalex,semantic_scholar,arxiv,pubmed,pmc,pubmed_central,github"
CSV_FIELDNAMES = [
    "key",
    "title_or_query",
    "source",
    "source_id",
    "doi",
    "pmid",
    "pmcid",
    "arxiv_id",
    "match_status",
    "status",
]

MANUAL_CANDIDATE_FIELDNAMES = [
    "paper_id",
    "key",
    "title_or_query",
    "source",
    "source_id",
    "doi",
    "pmid",
    "pmcid",
    "arxiv_id",
    "status_error",
    "candidate_count",
    "attempted_urls",
]


def _report_rows_by_key(path: Path) -> Dict[str, Dict[str, str]]:
    rows = {}
    for row in _safe_load_csv_rows(path):
        key = _coerce_str(row.get("key"))
        if not key:
            continue
        rows[key] = row
    return rows


def _write_manual_candidates(
    path: Path,
    paper_id: str,
    candidates: Sequence[Dict[str, str]],
    report_rows_by_key: Dict[str, Dict[str, str]],
) -> None:
    if not candidates:
        if path.exists():
            return
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANUAL_CANDIDATE_FIELDNAMES)
        writer.writeheader()
        for candidate in candidates:
            key = _coerce_str(candidate.get("key"))
            report_row = report_rows_by_key.get(key, {})
            writer.writerow(
                {
                    "paper_id": paper_id,
                    "key": key,
                    "title_or_query": _coerce_str(candidate.get("title_or_query")),
                    "source": _coerce_str(candidate.get("source")),
                    "source_id": _coerce_str(candidate.get("source_id")),
                    "doi": _coerce_str(candidate.get("doi")),
                    "pmid": _coerce_str(candidate.get("pmid")),
                    "pmcid": _coerce_str(candidate.get("pmcid")),
                    "arxiv_id": _coerce_str(candidate.get("arxiv_id")),
                    "status_error": _coerce_str(report_row.get("error")),
                    "candidate_count": _coerce_str(report_row.get("candidate_count")),
                    "attempted_urls": _coerce_str(report_row.get("attempted_urls")),
                }
            )


@dataclass
class RoundStats:
    round_no: int
    input_count: int
    downloaded: int
    existing: int
    failed: int
    pending_count: int
    report_path: Path
    failed_path: Path


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    value_lower = str(value).strip().lower()
    if value_lower in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value_lower in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value!r}")


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _sanitize_key(value: str, used: set[str], fallback: str) -> str:
    key = _coerce_str(value) or fallback
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip().strip("._")
    if not key:
        key = fallback

    if key not in used:
        return key

    i = 1
    candidate = f"{key}__{i}"
    while candidate in used:
        i += 1
        candidate = f"{key}__{i}"
    return candidate


def _extract_source_metadata_field(metadata: Any, field: str) -> str:
    if not isinstance(metadata, dict):
        return ""

    direct = _coerce_str(metadata.get(field))
    if direct:
        return direct

    ids = metadata.get("ids")
    if not isinstance(ids, dict):
        return ""

    if field == "arxiv_id":
        return _coerce_str(ids.get("arxiv"))
    return _coerce_str(ids.get(field))


def _normalize_identifier(value: str) -> str:
    value = _coerce_str(value)
    if not value:
        return ""
    low = value.lower()
    if low.startswith("https://doi.org/") or low.startswith("http://doi.org/"):
        return value.split("/", 3)[-1]
    return value


def _normalize_source_token(value: str) -> str:
    return _coerce_str(value).strip().lower().replace("-", "_")


def _parse_include_sources(value: str | None) -> set[str]:
    if value is None:
        return set()
    raw_tokens = {_normalize_source_token(item) for item in value.split(",") if item.strip()}
    # keep rows without source metadata by default unless user opts out.
    raw_tokens.add("")
    return raw_tokens


def _is_auto_source(source: str, include_sources: set[str]) -> bool:
    src = _normalize_source_token(source)
    if not include_sources:
        return True
    if src == "":
        # treat missing source as auto unless user explicitly disables by excluding it.
        return "" in include_sources or "manual" not in include_sources
    if src == "manual":
        return "manual" in include_sources
    return src in include_sources


def _pick_title(record: Dict[str, Any]) -> str:
    for field in ("title", "query_title", "query_title_original"):
        value = _coerce_str(record.get(field))
        if value:
            return value
    return ""


def _iter_full_metadata_records(path: Path):
    if not path.exists():
        return

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _build_input_rows(
    paper_id: str,
    records: Iterable[Dict[str, Any]],
    include_sources: set[str],
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    used_keys: set[str] = set()

    for idx, record in enumerate(records, start=1):
        source = _coerce_str(record.get("source"))
        if not _is_auto_source(source, include_sources):
            continue
        source_metadata = record.get("source_metadata", {})
        key = _sanitize_key(
            _coerce_str(record.get("key")),
            used=used_keys,
            fallback=f"{paper_id}_{idx:04d}",
        )
        used_keys.add(key)
        doi = _coerce_str(record.get("doi")) or _extract_source_metadata_field(source_metadata, "doi")
        pmid = _coerce_str(record.get("pmid")) or _extract_source_metadata_field(source_metadata, "pmid")
        pmcid = _coerce_str(record.get("pmcid")) or _extract_source_metadata_field(source_metadata, "pmcid")
        arxiv_id = _coerce_str(record.get("arxiv_id")) or _extract_source_metadata_field(source_metadata, "arxiv_id")
        rows.append(
            {
                "key": key,
                "title_or_query": _pick_title(record),
                "source": source,
                "source_id": _coerce_str(record.get("source_id")),
                "doi": _normalize_identifier(doi),
                "pmid": _coerce_str(pmid),
                "pmcid": _coerce_str(pmcid),
                "arxiv_id": _coerce_str(arxiv_id),
                "match_status": _coerce_str(record.get("match_status")),
                "status": _coerce_str(record.get("status")),
            }
        )
    return rows


def _load_full_metadata_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        rows: List[Dict[str, Any]] = []
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _write_csv_rows(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDNAMES})


def _safe_load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _safe_load_csv_keys(path: Path) -> list[str]:
    if not path.exists():
        return []
    keys: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        for row in reader:
            key = _coerce_str(row.get("key"))
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


def _ordered_unique_keys(rows: Sequence[Dict[str, str]]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        key = _coerce_str(row.get("key"))
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def _rows_by_keys(rows: Sequence[Dict[str, str]], keys: Iterable[str]) -> list[Dict[str, str]]:
    key_set = set(keys)
    result: list[Dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        key = _coerce_str(row.get("key"))
        if key in key_set and key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _pdf_path(output_dir: Path, key: str) -> Path:
    return output_dir / f"{key}.pdf"


def _has_valid_pdf(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size >= MIN_VALID_PDF_BYTES
    except OSError:
        return False


def _completed_keys(rows: Sequence[Dict[str, str]], output_dir: Path) -> set[str]:
    completed: set[str] = set()
    for row in rows:
        key = _coerce_str(row.get("key"))
        if not key:
            continue
        if _has_valid_pdf(_pdf_path(output_dir, key)):
            completed.add(key)
    return completed


def _run_one_round(
    script: Path,
    input_csv: Path,
    output_dir: Path,
    report_csv: Path,
    failed_csv: Path,
    force_redownload: bool,
    timeout_seconds: int,
    request_timeout: float | None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if request_timeout is not None:
        env["REQUEST_TIMEOUT_SECONDS"] = str(request_timeout)
    cmd: list[str] = [
        sys.executable,
        "-u",
        str(script),
        "--input",
        str(input_csv),
        "--output-dir",
        str(output_dir),
        "--report",
        str(report_csv),
        "--failed",
        str(failed_csv),
    ]
    if force_redownload:
        cmd.append("--force-redownload")

    try:
        if timeout_seconds > 0:
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            deadline = time.perf_counter() + timeout_seconds
            while True:
                timeout_remaining = max(0.0, deadline - time.perf_counter())
                if timeout_remaining == 0:
                    break
                try:
                    proc.wait(timeout=timeout_remaining)
                    break
                except subprocess.TimeoutExpired:
                    break_flag = time.perf_counter() >= deadline
                    if not break_flag:
                        continue
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        proc.kill()
                    break
            proc.wait()
            returncode = proc.returncode
            if returncode is None:
                returncode = 124
            elif returncode == -signal.SIGKILL:
                returncode = 124
        else:
            proc = subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            returncode = proc.returncode
        return subprocess.CompletedProcess(cmd, returncode=returncode)
    except Exception:
        return subprocess.CompletedProcess(cmd, returncode=1)


def _discover_paper_ids(refs_root: Path, paper_ids: list[str] | None) -> list[str]:
    selected = set(paper_ids or [])
    papers: list[str] = []
    for entry in sorted(refs_root.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if not ARXIV_ID_RE.match(entry.name):
            continue
        if selected and entry.name not in selected:
            continue
        papers.append(entry.name)
    return papers


def _parse_report_counts(
    report_csv: Path,
    pending_keys: Set[str],
) -> tuple[int, int, list[str]] | None:
    if not report_csv.exists():
        return None

    rows = _safe_load_csv_rows(report_csv)
    if not rows:
        return None

    downloaded = 0
    existing = 0
    failed: list[str] = []
    seen_failed: set[str] = set()

    for row in rows:
        key = _coerce_str(row.get("key"))
        if not key or key not in pending_keys:
            continue
        status = _coerce_str(row.get("status")).lower()
        if status == "downloaded":
            downloaded += 1
        elif status == "existing":
            existing += 1
        elif status == "failed":
            if key not in seen_failed:
                seen_failed.add(key)
                failed.append(key)

    if downloaded == 0 and existing == 0 and not failed:
        return None

    return downloaded, existing, failed


def _retry_failed_one_by_one(
    rows: Sequence[Dict[str, str]],
    output_dir: Path,
    report_root: Path,
    paper_id: str,
    find_pdf_script: Path,
    force_redownload: bool,
    row_timeout: int,
    round_no: int,
    run_root: Path,
    sleep_s: int,
    request_timeout: float | None,
) -> tuple[list[Dict[str, str]], list[Dict[str, str]], int]:
    if not rows:
        return [], [], 0

    resolved: list[Dict[str, str]] = []
    still_failed: list[Dict[str, str]] = []
    before_failed = _completed_keys(rows, output_dir)

    for idx, row in enumerate(rows, start=1):
        key = row["key"]
        if _has_valid_pdf(_pdf_path(output_dir, key)):
            resolved.append(row)
            continue

        single_csv = run_root / f"{paper_id}.round_{round_no:02d}.retry_{idx:03d}.{key}.csv"
        single_report = report_root / f"{paper_id}.round_{round_no:02d}.retry_{idx:03d}.{key}.report.csv"
        single_failed = report_root / f"{paper_id}.round_{round_no:02d}.retry_{idx:03d}.{key}.failed.csv"
        _write_csv_rows(single_csv, [row])

        _run_one_round(
            script=find_pdf_script,
            input_csv=single_csv,
            output_dir=output_dir,
            report_csv=single_report,
            failed_csv=single_failed,
            force_redownload=force_redownload,
            timeout_seconds=row_timeout,
            request_timeout=request_timeout,
        )

        if _has_valid_pdf(_pdf_path(output_dir, key)):
            resolved.append(row)
        else:
            still_failed.append(row)

        if sleep_s > 0:
            time.sleep(min(1, sleep_s))

    completed_after = _completed_keys(rows, output_dir)
    newly_resolved = sorted(completed_after - before_failed)
    return resolved, still_failed, len(newly_resolved)


def _write_final_summary(
    path: Path,
    paper_id: str,
    total_records: int,
    rounds: list[RoundStats],
    output_dir: Path,
    final_status: str,
) -> None:
    history_rows = [
        {
            "round": str(stat.round_no),
            "input_count": str(stat.input_count),
            "downloaded": str(stat.downloaded),
            "existing": str(stat.existing),
            "failed": str(stat.failed),
            "pending_count": str(stat.pending_count),
            "report_csv": str(stat.report_path),
            "failed_csv": str(stat.failed_path),
        }
        for stat in rounds
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    history_path = path.with_name(f"{path.stem}.rounds.csv")
    with history_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "round",
                "input_count",
                "downloaded",
                "existing",
                "failed",
                "pending_count",
                "report_csv",
                "failed_csv",
            ],
        )
        writer.writeheader()
        writer.writerows(history_rows)

    final_pending = rounds[-1].pending_count if rounds else total_records
    final_downloaded = sum(stat.downloaded + stat.existing for stat in rounds)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "total_records",
                "rounds_executed",
                "final_status",
                "final_pending_count",
                "final_downloaded_count",
                "output_dir",
                "rounds_history_csv",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "paper_id": paper_id,
                "total_records": str(total_records),
                "rounds_executed": str(len(rounds)),
                "final_status": final_status,
                "final_pending_count": str(final_pending),
                "final_downloaded_count": str(final_downloaded),
                "output_dir": str(output_dir),
                "rounds_history_csv": str(history_path),
            }
        )


def process_paper(
    paper_id: str,
    refs_root: Path,
    output_root: Path,
    metadata_filename: Path,
    include_sources: set[str],
    max_rounds: int,
    round_sleep: int,
    round_timeout: int,
    single_row_timeout: int,
    force_redownload: bool,
    find_pdf_script: Path,
    request_timeout: float | None,
    dry_run: bool,
    report_root: Path,
    stop_on_all_methods_failed: bool,
    overall_rounds: list[dict[str, str]],
) -> None:
    paper_dir = refs_root / paper_id
    metadata_path = paper_dir / metadata_filename

    # Memory-friendly metadata parsing to avoid holding both raw JSON rows and transformed rows.
    records_iter = _iter_full_metadata_records(metadata_path)
    rows = _build_input_rows(paper_id, records_iter, include_sources)
    if not rows:
        print(f"[{paper_id}] skip: no metadata rows in {metadata_path}")
        final_status = "skipped_no_records"
        summary_path = report_root / f"{paper_id}.final_summary.csv"
        _write_final_summary(
            summary_path,
            paper_id=paper_id,
            total_records=0,
            rounds=[],
            output_dir=output_root / paper_id,
            final_status=final_status,
        )
        overall_rounds.append(
            {
                "paper_id": paper_id,
                "status": final_status,
                "output_dir": str(output_root / paper_id),
                "summary_csv": str(summary_path),
                "message": f"skip: no input rows from {metadata_path}",
            }
        )
        return

    output_dir = output_root / paper_id
    run_root = output_root / ".run_tmp" / paper_id
    run_root.mkdir(parents=True, exist_ok=True)

    pending_rows: list[Dict[str, str]] = [row for row in rows if not _has_valid_pdf(_pdf_path(output_dir, row["key"]))]
    if not pending_rows:
        final_status = "success"
        rounds: list[RoundStats] = []
        summary_path = report_root / f"{paper_id}.final_summary.csv"
        _write_final_summary(
            summary_path,
            paper_id=paper_id,
            total_records=len(rows),
            rounds=rounds,
            output_dir=output_root / paper_id,
            final_status=final_status,
        )
        overall_rounds.append(
            {
                "paper_id": paper_id,
                "status": final_status,
                "total_records": str(len(rows)),
                "rounds_executed": "0",
                "final_pending": "0",
                "downloaded_or_existing": str(len(rows)),
                "output_dir": str(output_dir),
                "summary_csv": str(summary_path),
            }
        )
        return

    rounds: list[RoundStats] = []
    final_status = "max_rounds_reached"
    previous_pending_signature: tuple[str, ...] | None = None
    same_pending_streak = 0
    latest_report_rows_by_key: Dict[str, Dict[str, str]] = {}

    for round_no in range(1, max_rounds + 1):
        if not pending_rows:
            final_status = "success"
            break

        input_csv = run_root / f"{paper_id}.round_{round_no:02d}.csv"
        report_csv = report_root / f"{paper_id}.round_{round_no:02d}.report.csv"
        failed_csv = report_root / f"{paper_id}.round_{round_no:02d}.failed.csv"
        _write_csv_rows(input_csv, pending_rows)

        pending_keys = set(_ordered_unique_keys(pending_rows))
        round_input_count = len(pending_rows)
        before_done = _completed_keys(pending_rows, output_dir)

        print(f"[{paper_id}] round {round_no}/{max_rounds}: {round_input_count} candidates")

        if dry_run:
            after_done = set(before_done)
            round_existing = len(before_done & pending_keys)
            round_downloaded = 0
            failed_keys = [row["key"] for row in pending_rows]
            proc_returncode = 0
            report_rows_by_key = {}
        else:
            proc = _run_one_round(
                script=find_pdf_script,
                input_csv=input_csv,
                output_dir=output_dir,
                report_csv=report_csv,
                failed_csv=failed_csv,
                force_redownload=force_redownload,
                timeout_seconds=round_timeout,
                request_timeout=request_timeout,
            )
            proc_returncode = proc.returncode
            after_done = _completed_keys(pending_rows, output_dir)
            round_existing = len(before_done & pending_keys)
            round_downloaded = 0

            counts_from_report = _parse_report_counts(report_csv, pending_keys)
            if proc_returncode == 0 and counts_from_report is not None:
                round_downloaded, round_existing_report, failed_keys = counts_from_report
                round_existing = max(round_existing_report, round_existing)
            else:
                if proc_returncode != 0:
                    print(f"[{paper_id}] round {round_no}: find_pdf exited with {proc_returncode}")
                # fallback from existing files, including partial batches before timeout.
                if proc_returncode == 124:
                    print(
                        f"[{paper_id}] round {round_no}: timeout reached, fallback to one-by-one retry for this round"
                    )
                failed_keys = [k for k in pending_keys if k not in after_done]
                round_downloaded = len(after_done - before_done)

            # Use failed.csv as additional evidence, even when returncode!=0.
            failed_from_report = _safe_load_csv_rows(failed_csv)
            if failed_from_report:
                fallback_failed = _safe_load_csv_keys(failed_csv)
                if fallback_failed:
                    failed_keys = list(dict.fromkeys(failed_keys + fallback_failed))

            # If report parse fails to include all items, use file-status-based fallback.
            if not failed_keys and round_input_count > len(after_done):
                failed_keys = [k for k in pending_keys if k not in after_done]

            if proc_returncode == 124 and round_timeout > 0:
                unresolved_rows = _rows_by_keys(pending_rows, set(failed_keys))
                if 0 < len(unresolved_rows) <= 10:
                    _, failed_rows_after_retry, _ = _retry_failed_one_by_one(
                        rows=unresolved_rows,
                        output_dir=output_dir,
                        report_root=report_root,
                        paper_id=paper_id,
                        find_pdf_script=find_pdf_script,
                        force_redownload=force_redownload,
                        row_timeout=single_row_timeout,
                        round_no=round_no,
                        run_root=run_root,
                        sleep_s=round_sleep,
                        request_timeout=request_timeout,
                    )
                    after_done = _completed_keys(pending_rows, output_dir)
                    failed_keys = [row["key"] for row in failed_rows_after_retry]
                    round_downloaded = len(after_done - before_done)
                else:
                    failed_keys = [row["key"] for row in unresolved_rows]

            if proc_returncode == 0 and not failed_keys and len(after_done) >= len(pending_rows):
                round_downloaded = len(after_done - before_done)

            report_rows_by_key = _report_rows_by_key(report_csv)
            latest_report_rows_by_key = report_rows_by_key

        failed_rows = _rows_by_keys(pending_rows, set(failed_keys))
        halt_for_manual = False
        if stop_on_all_methods_failed and failed_rows:
            failed_all_methods = True
            for failed_row in failed_rows:
                failed_key = failed_row["key"]
                error = _coerce_str(report_rows_by_key.get(failed_key, {}).get("error"))
                if error != "all_methods_failed":
                    failed_all_methods = False
                    break

            if failed_all_methods:
                final_status = "manual_required_all_methods_failed"
                halt_for_manual = True

        pending_rows = failed_rows

        if not dry_run:
            print(
                f"[{paper_id}] round {round_no} done: downloaded={round_downloaded}, existing={round_existing}, "
                f"failed={len(failed_rows)}, pending={len(pending_rows)}"
            )
        else:
            print(
                f"[{paper_id}] round {round_no} dry-run: would process={round_input_count}, "
                f"pending={len(failed_rows)}"
            )

        rounds.append(
            RoundStats(
                round_no=round_no,
                input_count=round_input_count,
                downloaded=round_downloaded,
                existing=round_existing,
                failed=len(failed_rows),
                pending_count=len(pending_rows),
                report_path=report_csv,
                failed_path=failed_csv,
            )
        )

        pending_signature = tuple(row["key"] for row in pending_rows)
        if previous_pending_signature is not None:
            if pending_signature == previous_pending_signature:
                same_pending_streak += 1
            else:
                same_pending_streak = 0
        previous_pending_signature = pending_signature

        if same_pending_streak >= 2:
            print(
                f"[{paper_id}] round {round_no}: pending set unchanged for {same_pending_streak} consecutive rounds; "
                "stop retrying automatically"
            )
            final_status = "stalled_no_progress"
            halt_for_manual = True

        if not pending_rows:
            final_status = "success"
            break

        if halt_for_manual:
            _write_manual_candidates(
                path=report_root / f"{paper_id}.manual_candidates.csv",
                paper_id=paper_id,
                candidates=pending_rows,
                report_rows_by_key=latest_report_rows_by_key,
            )
            if final_status == "manual_required_all_methods_failed":
                print(
                    f"[{paper_id}] round {round_no}: all remaining failures are all_methods_failed; stop and mark for manual download"
                )
            else:
                print(f"[{paper_id}] round {round_no}: stalled; stop and mark for manual review")
            break

        if round_no < max_rounds:
            time.sleep(round_sleep)

        # Keep memory bounded per-round; pending_rows for next round remains by design.
        gc.collect()

    if dry_run:
        final_status = "dry_run_complete"
    elif final_status == "max_rounds_reached" and pending_rows:
        _write_manual_candidates(
            path=report_root / f"{paper_id}.manual_candidates.csv",
            paper_id=paper_id,
            candidates=pending_rows,
            report_rows_by_key=latest_report_rows_by_key,
        )

    summary_path = report_root / f"{paper_id}.final_summary.csv"
    _write_final_summary(
        summary_path,
        paper_id=paper_id,
        total_records=len(rows),
        rounds=rounds,
        output_dir=output_root / paper_id,
        final_status=final_status,
    )

    final_pending = len(pending_rows)
    downloaded_total = sum(stat.downloaded + stat.existing for stat in rounds)
    overall_rounds.append(
        {
            "paper_id": paper_id,
            "status": final_status,
            "total_records": str(len(rows)),
            "rounds_executed": str(len(rounds)),
            "final_pending": str(final_pending),
            "downloaded_or_existing": str(downloaded_total),
            "output_dir": str(output_dir),
            "summary_csv": str(summary_path),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download reference PDFs from refs/<arXiv-id>/metadata/title_abstracts_full_metadata.jsonl",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--refs-root", default="refs", help="Root folder with SR metadata")
    parser.add_argument(
        "--paper-id",
        action="append",
        default=None,
        help="Limit to one or more arXiv IDs. Repeatable.",
    )
    parser.add_argument("--output-root", default="ref_pdfs", help="Root folder for downloaded PDFs")
    parser.add_argument(
        "--metadata-filename",
        default="metadata/title_abstracts_full_metadata.jsonl",
        help="Metadata filename under each paper folder",
    )
    parser.add_argument("--max-rounds", type=int, default=10, help="Maximum download rounds")
    parser.add_argument("--round-sleep", type=int, default=8, help="Sleep seconds between rounds")
    parser.add_argument(
        "--include-sources",
        default=DEFAULT_INCLUDE_SOURCES,
        help=(
            "Comma-separated sources to include. Rows with source='manual' are skipped unless explicitly included. "
            "Default: crossref,openalex,semantic_scholar,arxiv,pubmed,pmc,pubmed_central,github"
        ),
    )
    parser.add_argument(
        "--round-timeout",
        type=int,
        default=0,
        help="Timeout (seconds) per find_pdf round (0 means no timeout)",
    )
    parser.add_argument(
        "--single-row-timeout",
        type=int,
        default=30,
        help="Timeout (seconds) for per-key retries when a batch times out",
    )
    parser.add_argument(
        "--find-pdf-request-timeout",
        type=float,
        default=None,
        help="REQUEST_TIMEOUT_SECONDS passed to download_remaining_pdfs.py (default: script default)",
    )
    parser.add_argument("--force-redownload", action="store_true", help="Force redownload PDFs")
    parser.add_argument(
        "--find-pdf-script",
        default="",
        help="Path to download_remaining_pdfs.py",
    )
    parser.add_argument("--dry-run", action="store_true", help="Prepare inputs and reports only")
    parser.add_argument(
        "--report-root",
        default="issues/ref_pdf_download",
        help="Directory for generated round/final reports",
    )
    parser.add_argument(
        "--stop-on-all-methods-failed",
        action="store_true",
        help="Stop early and output manual candidates when remaining failures are all_methods_failed",
    )
    args = parser.parse_args()

    refs_root = Path(args.refs_root)
    output_root = Path(args.output_root)
    metadata_filename = Path(args.metadata_filename)
    checked_candidates: list[Path] = []
    if args.find_pdf_script:
        find_pdf_script = Path(args.find_pdf_script)
    else:
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parents[1]
        candidates = [
            repo_root / "find_pdf" / "download_remaining_pdfs.py",
            script_dir.parent / "find_pdf" / "download_remaining_pdfs.py",
        ]
        find_pdf_script = Path("")
        for candidate in candidates:
            candidate = candidate.resolve()
            checked_candidates.append(candidate)
            if candidate.exists():
                find_pdf_script = candidate
                break

    report_root = Path(args.report_root)

    if not refs_root.exists() or not refs_root.is_dir():
        print(f"[ERROR] refs root not found: {refs_root}")
        return 1

    if not find_pdf_script.exists():
        print(f"[ERROR] download script not found; checked: {[str(c) for c in checked_candidates]}")
        return 1

    papers = _discover_paper_ids(refs_root, args.paper_id)
    if not papers:
        print("[ERROR] no matching arXiv-style paper directories found")
        return 1

    output_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str]] = []
    include_sources = _parse_include_sources(args.include_sources)
    for paper_id in papers:
        process_paper(
            paper_id=paper_id,
            refs_root=refs_root,
            output_root=output_root,
            metadata_filename=metadata_filename,
            include_sources=include_sources,
            max_rounds=args.max_rounds,
            round_sleep=args.round_sleep,
            round_timeout=args.round_timeout,
            single_row_timeout=args.single_row_timeout,
            force_redownload=args.force_redownload,
            find_pdf_script=find_pdf_script,
            request_timeout=args.find_pdf_request_timeout,
            dry_run=args.dry_run,
            report_root=report_root,
            stop_on_all_methods_failed=args.stop_on_all_methods_failed,
            overall_rounds=results,
        )

    overall_report = report_root / "overall_summary.csv"
    with overall_report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "status",
                "total_records",
                "rounds_executed",
                "final_pending",
                "downloaded_or_existing",
                "output_dir",
                "summary_csv",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"[DONE] processed {len(papers)} paper(s)")
    print(f"[DONE] summary: {overall_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
