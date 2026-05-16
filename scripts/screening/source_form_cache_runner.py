#!/usr/bin/env python3
"""Generate and collect source-form classification cache rows."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from experiment_workflows import (  # noqa: E402
    DEFAULT_CACHE_DIR_RELATIVE,
    DEFAULT_SOURCE_FORM_MODEL,
    DEFAULT_SOURCE_FORM_REASONING_EFFORT,
    SOURCE_FORM_PHASE_ID,
    build_source_form_specs_for_records,
    cache_records_from_parsed_successes,
    load_source_form_cache,
    load_source_form_policy,
    policy_for_paper,
    read_json,
    read_jsonl,
    relative_path,
    write_json,
    write_source_form_cache_artifacts,
)
from openai_batch_runner import OpenAIBatchRunner  # noqa: E402


DEFAULT_CACHE_SCOPE = [
    "2306.12834",
    "2310.07264",
    "2312.05172",
    "2401.09244",
    "2405.15604",
    "2507.07741",
    "2509.11446",
    "2510.01145",
]

EXPECTED_COUNTS = {
    "2306.12834": 263,
    "2310.07264": 108,
    "2312.05172": 150,
    "2401.09244": 207,
    "2405.15604": 244,
    "2507.07741": 193,
    "2509.11446": 164,
    "2510.01145": 123,
}


def _load_env_file() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def _metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage1" / f"{paper_id}.json"


def _load_stage1_criteria_or_stub(paper_id: str) -> dict[str, Any]:
    path = _criteria_path(paper_id)
    if path.exists():
        return read_json(path)
    return {
        "paper_id": paper_id,
        "stage": "stage1",
        "criteria_missing": True,
        "criteria_path": str(path),
        "note": "No current criteria_stage1 file exists for this SR; source-form classification uses title, abstract, and metadata only.",
    }


def _policy_path() -> Path:
    return REPO_ROOT / "screening" / "gates" / "source_form_policy.json"


def _artifact_dir(cache_dir: Path, model: str) -> Path:
    return cache_dir / "batch_jobs" / SOURCE_FORM_PHASE_ID / model


def _load_records(papers: list[str]) -> dict[str, list[dict[str, Any]]]:
    records_by_paper: dict[str, list[dict[str, Any]]] = {}
    for paper_id in papers:
        metadata_path = _metadata_path(paper_id)
        if not metadata_path.exists():
            continue
        raw_rows = read_jsonl(metadata_path)
        key_counts: Counter[str] = Counter()
        rows: list[dict[str, Any]] = []
        for index, row in enumerate(raw_rows, start=1):
            key = str(row.get("key") or "").strip()
            key_counts[key] += 1
            disambiguated = dict(row)
            if key_counts[key] > 1:
                disambiguated["source_form_row_key"] = f"{key}__row{index}"
                disambiguated["source_form_original_key"] = key
            rows.append(disambiguated)
        records_by_paper[paper_id] = rows
    return records_by_paper


def _load_inputs(
    *,
    papers: list[str],
    cache_dir: Path,
    model: str,
    reasoning_effort: str,
    ignore_cache: bool = False,
) -> dict[str, Any]:
    records_by_paper = _load_records(papers)
    ledger = load_source_form_policy(_policy_path())
    policies_by_paper = {paper_id: policy_for_paper(ledger, paper_id) for paper_id in records_by_paper}
    criteria_by_paper = {paper_id: _load_stage1_criteria_or_stub(paper_id) for paper_id in records_by_paper}
    cache_rows = {} if ignore_cache else load_source_form_cache(cache_dir)
    specs = []
    paper_summaries: dict[str, Any] = {}
    for paper_id, records in records_by_paper.items():
        paper_specs, hits_by_key = build_source_form_specs_for_records(
            paper_id=paper_id,
            records=records,
            policy=policies_by_paper[paper_id],
            stage1_criteria=criteria_by_paper[paper_id],
            cache_rows=cache_rows,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        specs.extend(paper_specs)
        paper_summaries[paper_id] = {
            "candidate_total": len(records),
            "cache_hit_count": len(hits_by_key),
            "request_count": len(paper_specs),
            "allow_secondary_source_forms": policies_by_paper[paper_id].allow_secondary_source_forms,
        }
    return {
        "records_by_paper": records_by_paper,
        "policies_by_paper": policies_by_paper,
        "criteria_by_paper": criteria_by_paper,
        "specs": specs,
        "paper_summaries": paper_summaries,
    }


def _validate_scope_counts(records_by_paper: dict[str, list[dict[str, Any]]], *, expected_total: int | None) -> None:
    for paper_id, expected in EXPECTED_COUNTS.items():
        if paper_id in records_by_paper and len(records_by_paper[paper_id]) != expected:
            raise SystemExit(f"{paper_id} row count mismatch: expected={expected} observed={len(records_by_paper[paper_id])}")
    observed_total = sum(len(rows) for rows in records_by_paper.values())
    if expected_total is not None and observed_total != expected_total:
        raise SystemExit(f"scope row count mismatch: expected={expected_total} observed={observed_total}")
    forbidden = {"2303.13365", "2407.17844"}.intersection(records_by_paper)
    if forbidden:
        raise SystemExit("cache scope unexpectedly includes skipped papers: " + ", ".join(sorted(forbidden)))


def _load_batch_payload(artifact_dir: Path) -> dict[str, Any] | None:
    for name in ("batch_latest.json", "batch_create.json"):
        path = artifact_dir / name
        if path.exists():
            return read_json(path)
    return None


def _prepare(
    *,
    cache_dir: Path,
    papers: list[str],
    model: str,
    reasoning_effort: str,
    expected_total: int | None,
    ignore_cache: bool,
) -> dict[str, Any]:
    state = _load_inputs(
        papers=papers,
        cache_dir=cache_dir,
        model=model,
        reasoning_effort=reasoning_effort,
        ignore_cache=ignore_cache,
    )
    _validate_scope_counts(state["records_by_paper"], expected_total=expected_total)
    artifact_dir = _artifact_dir(cache_dir, model)
    runner = OpenAIBatchRunner(client=object(), poll_interval_sec=30.0)
    input_rows = runner.serialize_requests(state["specs"], endpoint="/v1/chat/completions")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    from experiment_workflows import write_jsonl  # local import keeps package export check focused

    write_jsonl(artifact_dir / "input.jsonl", input_rows)
    payload = {
        "mode": "prepare",
        "cache_dir": str(cache_dir),
        "artifact_dir": str(artifact_dir),
        "model": model,
        "reasoning_effort": reasoning_effort,
        "request_count": len(state["specs"]),
        "paper_preparation": state["paper_summaries"],
    }
    write_json(artifact_dir / "prepare_summary.json", payload)
    return payload


def _submit(
    *,
    cache_dir: Path,
    papers: list[str],
    model: str,
    reasoning_effort: str,
    poll_interval_sec: float,
    completion_window: str,
    expected_total: int | None,
) -> dict[str, Any]:
    _load_env_file()
    state = _load_inputs(papers=papers, cache_dir=cache_dir, model=model, reasoning_effort=reasoning_effort)
    _validate_scope_counts(state["records_by_paper"], expected_total=expected_total)
    artifact_dir = _artifact_dir(cache_dir, model)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if not state["specs"]:
        parsed_payload = {
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
        write_json(artifact_dir / "parsed_results.json", parsed_payload)
        job = {
            "phase": SOURCE_FORM_PHASE_ID,
            "batch_artifact_dir": str(artifact_dir),
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "request_count": 0,
            "paper_preparation": state["paper_summaries"],
        }
        write_json(artifact_dir / "batch_job.json", job)
        return job

    client = OpenAI()
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=poll_interval_sec)
    submit_payload = runner.submit_requests(
        specs=state["specs"],
        endpoint="/v1/chat/completions",
        artifact_dir=artifact_dir,
        metadata={
            "phase": SOURCE_FORM_PHASE_ID,
            "paper_count": len(state["records_by_paper"]),
            "cache_dir": relative_path(cache_dir, REPO_ROOT),
        },
        completion_window=completion_window,
    )
    job = {
        "phase": SOURCE_FORM_PHASE_ID,
        "batch_artifact_dir": str(artifact_dir),
        "batch_id": submit_payload["batch_create"]["id"],
        "batch_status": submit_payload["batch_create"]["status"],
        "request_count": len(state["specs"]),
        "upload_file_id": submit_payload["upload_file"]["id"],
        "paper_preparation": state["paper_summaries"],
    }
    write_json(artifact_dir / "batch_job.json", job)
    return job


def _collect(
    *,
    cache_dir: Path,
    papers: list[str],
    model: str,
    reasoning_effort: str,
    poll_interval_sec: float,
    max_wait_minutes: float,
    expected_total: int | None,
) -> dict[str, Any]:
    _load_env_file()
    state = _load_inputs(papers=papers, cache_dir=cache_dir, model=model, reasoning_effort=reasoning_effort)
    _validate_scope_counts(state["records_by_paper"], expected_total=expected_total)
    artifact_dir = _artifact_dir(cache_dir, model)
    batch_payload = _load_batch_payload(artifact_dir)
    if batch_payload is None or batch_payload.get("id") is None:
        parsed_payload = read_json(artifact_dir / "parsed_results.json")
    else:
        runner = OpenAIBatchRunner(client=OpenAI(), poll_interval_sec=poll_interval_sec)
        batch_payload = runner.wait_until_terminal(
            str(batch_payload["id"]),
            artifact_dir=artifact_dir,
            max_wait_minutes=max_wait_minutes,
        )
        parsed_payload = runner.collect_results(
            specs=state["specs"],
            batch_payload=batch_payload,
            artifact_dir=artifact_dir,
        )
        if parsed_payload.get("batch_status") != "completed":
            raise SystemExit(f"source-form batch ended with status={parsed_payload.get('batch_status')}")

    if parsed_payload.get("failures") or parsed_payload.get("missing"):
        raise SystemExit(
            "source-form parse validation failed: "
            f"failures={len(parsed_payload.get('failures') or [])} "
            f"missing={len(parsed_payload.get('missing') or [])}"
        )

    new_records = cache_records_from_parsed_successes(
        parsed_payload=parsed_payload,
        records_by_paper=state["records_by_paper"],
        policies_by_paper=state["policies_by_paper"],
        criteria_by_paper=state["criteria_by_paper"],
        model=model,
        reasoning_effort=reasoning_effort,
    )
    cache_manifest = write_source_form_cache_artifacts(
        cache_dir=cache_dir,
        records=new_records,
        manifest_extra={
            "model": model,
            "reasoning_effort": reasoning_effort,
            "latest_batch_artifact_dir": str(artifact_dir),
            "latest_success_count": len(parsed_payload.get("successes") or []),
            "latest_failure_count": len(parsed_payload.get("failures") or []),
            "latest_missing_count": len(parsed_payload.get("missing") or []),
        },
    )
    scoped_count = sum(cache_manifest["papers"].get(paper_id, {}).get("row_count", 0) for paper_id in papers)
    if expected_total is not None and scoped_count != expected_total:
        raise SystemExit(f"cache scoped row count mismatch after collect: expected={expected_total} observed={scoped_count}")
    forbidden = {"2303.13365", "2407.17844"}.intersection(cache_manifest.get("papers", {}))
    if forbidden:
        raise SystemExit("cache manifest unexpectedly includes skipped papers: " + ", ".join(sorted(forbidden)))
    return {
        "parsed_summary": {
            "success_count": len(parsed_payload.get("successes") or []),
            "failure_count": len(parsed_payload.get("failures") or []),
            "missing_count": len(parsed_payload.get("missing") or []),
        },
        "cache_manifest": cache_manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate source-form classifier cache for screening candidate metadata.")
    parser.add_argument("--mode", choices=["prepare", "submit", "collect", "run"], required=True)
    parser.add_argument("--papers", nargs="*", default=DEFAULT_CACHE_SCOPE)
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / DEFAULT_CACHE_DIR_RELATIVE)
    parser.add_argument("--model", default=DEFAULT_SOURCE_FORM_MODEL)
    parser.add_argument("--reasoning-effort", default=DEFAULT_SOURCE_FORM_REASONING_EFFORT)
    parser.add_argument("--completion-window", default="24h")
    parser.add_argument("--batch-poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--batch-max-wait-minutes", type=float, default=1440.0)
    parser.add_argument("--expected-total", type=int, default=1452)
    parser.add_argument("--ignore-cache", action="store_true")
    args = parser.parse_args()

    papers = list(args.papers)
    expected_total = args.expected_total if set(papers) == set(DEFAULT_CACHE_SCOPE) else None
    if args.mode == "prepare":
        payload = _prepare(
            cache_dir=args.cache_dir,
            papers=papers,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            expected_total=expected_total,
            ignore_cache=args.ignore_cache,
        )
        print(f"[prepare] request_count={payload['request_count']} artifact_dir={payload['artifact_dir']}", flush=True)
        return 0

    if args.mode in {"submit", "run"}:
        job = _submit(
            cache_dir=args.cache_dir,
            papers=papers,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            poll_interval_sec=args.batch_poll_interval_sec,
            completion_window=args.completion_window,
            expected_total=expected_total,
        )
        print(f"[submit] status={job['batch_status']} request_count={job['request_count']}", flush=True)

    if args.mode in {"collect", "run"}:
        payload = _collect(
            cache_dir=args.cache_dir,
            papers=papers,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            poll_interval_sec=args.batch_poll_interval_sec,
            max_wait_minutes=args.batch_max_wait_minutes,
            expected_total=expected_total,
        )
        print(
            "[collect] "
            f"success={payload['parsed_summary']['success_count']} "
            f"cache_rows={payload['cache_manifest']['row_count']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
