#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from openai import OpenAI

import bcpcs_full_corpus_batch_runner as full
from failure_slice_common import ensure_dir, load_dotenv_if_present, read_json, read_jsonl, repo_rel, run_dir, utc_now_iso, write_json, write_jsonl
from scripts.screening.openai_batch_runner import OpenAIBatchRunner


@contextmanager
def scoped_papers(paper_ids: list[str]):
    original = list(full.PAPER_IDS)
    full.PAPER_IDS = list(paper_ids)
    try:
        yield
    finally:
        full.PAPER_IDS = original


def _chunk(items: list[Any], shard_size: int) -> list[list[Any]]:
    return [items[i : i + shard_size] for i in range(0, len(items), shard_size)]


def _merge_parsed(parts: list[dict[str, Any]]) -> dict[str, Any]:
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    output_row_count = 0
    error_row_count = 0
    for payload in parts:
        successes.extend(payload.get("successes", []))
        failures.extend(payload.get("failures", []))
        missing.extend(payload.get("missing", []))
        output_row_count += int(payload.get("output_row_count") or 0)
        error_row_count += int(payload.get("error_row_count") or 0)
    successes.sort(key=lambda row: str(row.get("custom_id") or ""))
    failures.sort(key=lambda row: str(row.get("custom_id") or ""))
    missing.sort(key=lambda row: str(row.get("custom_id") or ""))
    return {
        "batch_id": "fallback_sharded",
        "batch_status": "completed",
        "successes": successes,
        "failures": failures,
        "missing": missing,
        "output_row_count": output_row_count,
        "error_row_count": error_row_count,
    }


def run_fallback(
    *,
    run_id: str,
    paper_id: str,
    profile: full.BatchProfile,
    shard_size: int,
    cost_cap_usd: float,
    poll_interval_sec: float,
    max_wait_minutes: float,
) -> dict[str, Any]:
    with scoped_papers([paper_id]):
        full.init_run(run_id=run_id, profile=profile, cost_cap_usd=cost_cap_usd)
        prepared = full.prepare_submit_payload(run_id=run_id, profile=profile, cost_cap_usd=cost_cap_usd)
        if prepared["status"] != "ready_to_submit":
            return prepared

        load_dotenv_if_present()
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set; cannot submit sharded Batch job.")

        rd = run_dir(run_id)
        artifact_dir = Path(prepared["artifact_dir"])
        shards_dir = ensure_dir(artifact_dir / "shards")
        specs = prepared["specs"]
        request_by_id = prepared["request_by_id"]
        spec_by_id = {spec.custom_id: spec for spec in specs}
        shards = _chunk(specs, shard_size)

        client = OpenAI()
        client.models.retrieve(profile.model)
        runner = OpenAIBatchRunner(client=client, poll_interval_sec=poll_interval_sec)

        manifest = read_json(rd / "run_manifest.json")
        manifest["status"] = "submitted"
        manifest["batch_phase"] = {
            "phase": full.PHASE,
            "artifact_dir": repo_rel(artifact_dir),
            "batch_id": "fallback_sharded",
            "batch_status": "submitted",
            "request_count": len(specs),
            "pre_submit_estimate": prepared["estimate"],
            "shard_jobs": [],
        }
        manifest["updated_at"] = utc_now_iso()
        write_json(rd / "run_manifest.json", manifest)

        shard_meta: list[dict[str, Any]] = []
        for index, shard_specs in enumerate(shards, start=1):
            shard_artifact_dir = ensure_dir(shards_dir / f"shard_{index:02d}")
            submit_payload = runner.submit_requests(
                specs=shard_specs,
                endpoint="/v1/chat/completions",
                artifact_dir=shard_artifact_dir,
                metadata={
                    "experiment": "bcpcs_full_corpus_batch_sharded_fallback",
                    "run_id": run_id,
                    "paper_id": paper_id,
                    "phase": full.PHASE,
                    "model": profile.model,
                    "shard_index": str(index),
                },
            )
            shard_meta.append(
                {
                    "shard_index": index,
                    "request_count": len(shard_specs),
                    "batch_id": submit_payload["batch_create"]["id"],
                    "artifact_dir": repo_rel(shard_artifact_dir),
                    "custom_ids": [spec.custom_id for spec in shard_specs],
                }
            )
        manifest = read_json(rd / "run_manifest.json")
        manifest["batch_phase"]["shard_jobs"] = shard_meta
        manifest["updated_at"] = utc_now_iso()
        write_json(rd / "run_manifest.json", manifest)

        shard_outputs: list[dict[str, Any]] = []
        shard_parsed: list[dict[str, Any]] = []
        for shard in shard_meta:
            shard_artifact_dir = Path(rd / Path(shard["artifact_dir"]).relative_to(repo_rel(rd)))
            latest = runner.wait_until_terminal(
                shard["batch_id"],
                artifact_dir=shard_artifact_dir,
                max_wait_minutes=max_wait_minutes,
            )
            shard["batch_status"] = latest.get("status")
            if latest.get("status") in {"failed", "expired", "cancelled"}:
                write_json(shard_artifact_dir / "terminal_failure.json", latest)
                raise RuntimeError(f"Sharded fallback batch failed for {run_id} shard {shard['shard_index']}: {latest.get('status')}")
            parsed = runner.collect_results(
                specs=[spec_by_id[custom_id] for custom_id in shard["custom_ids"]],
                batch_payload=latest,
                artifact_dir=shard_artifact_dir,
            )
            shard_parsed.append(parsed)
            shard_outputs.extend(read_jsonl(shard_artifact_dir / "output.jsonl"))

        merged_parsed = _merge_parsed(shard_parsed)
        write_json(artifact_dir / "parsed_results.json", merged_parsed)
        write_jsonl(artifact_dir / "output.jsonl", shard_outputs)
        write_json(
            artifact_dir / "batch_latest.json",
            {
                "id": "fallback_sharded",
                "status": "completed",
                "request_counts": {
                    "total": len(specs),
                    "completed": len(merged_parsed["successes"]),
                    "failed": len(merged_parsed["failures"]),
                },
                "completed_at": utc_now_iso(),
            },
        )

        full._write_stage2_outputs(run_id=run_id, parsed=merged_parsed, request_by_id=request_by_id, profile=profile)
        cost_summary = full._update_cost(
            run_id=run_id,
            profile=profile,
            output_rows=shard_outputs,
            parsed=merged_parsed,
            request_by_id=request_by_id,
            batch_id="fallback_sharded",
        )

        manifest = read_json(rd / "run_manifest.json")
        manifest["status"] = "collected"
        manifest["batch_phase"]["batch_status"] = "completed"
        manifest["batch_phase"]["success_count"] = len(merged_parsed["successes"])
        manifest["batch_phase"]["failure_count"] = len(merged_parsed["failures"])
        manifest["batch_phase"]["missing_count"] = len(merged_parsed["missing"])
        manifest["batch_phase"]["cost_summary"] = cost_summary.get("phases", {}).get(full.PHASE)
        manifest["updated_at"] = utc_now_iso()
        write_json(rd / "run_manifest.json", manifest)

        full.assemble_full_corpus(run_id=run_id)
        summary = full.evaluate_full_corpus(run_id=run_id)
        validation = full.validate_run(run_id=run_id)
        report_path = full.write_report(run_id=run_id, summary=summary, validation=validation)
        manifest = read_json(rd / "run_manifest.json")
        manifest["status"] = "completed"
        manifest["evaluation_summary_full_corpus_path"] = repo_rel(rd / "evaluation_summary_full_corpus.json")
        manifest["validation_summary_full_corpus_path"] = repo_rel(rd / "validation_summary_full_corpus.json")
        manifest["report_path"] = repo_rel(report_path)
        manifest["updated_at"] = utc_now_iso()
        write_json(rd / "run_manifest.json", manifest)
        return {
            "status": "completed",
            "run_id": run_id,
            "report_path": repo_rel(report_path),
            "summary_path": repo_rel(rd / "evaluation_summary_full_corpus.json"),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default=full.DEFAULT_REASONING_EFFORT)
    parser.add_argument("--max-completion-tokens", type=int, default=full.MAX_COMPLETION_TOKENS)
    parser.add_argument("--shard-size", type=int, default=90)
    parser.add_argument("--cost-cap-usd", type=float, default=12.0)
    parser.add_argument("--poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--max-wait-minutes", type=float, default=360.0)
    args = parser.parse_args()
    payload = run_fallback(
        run_id=args.run_id,
        paper_id=args.paper_id,
        profile=full.make_profile(
            reasoning_effort=args.reasoning_effort,
            max_completion_tokens=args.max_completion_tokens,
        ),
        shard_size=args.shard_size,
        cost_cap_usd=args.cost_cap_usd,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
