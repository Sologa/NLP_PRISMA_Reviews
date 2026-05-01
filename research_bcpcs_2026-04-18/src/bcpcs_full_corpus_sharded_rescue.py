#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

import bcpcs_full_corpus_batch_runner as full
import bcpcs_full_corpus_sharded_fallback as fallback
from failure_slice_common import ensure_dir, load_dotenv_if_present, read_json, read_jsonl, repo_rel, run_dir, utc_now_iso, write_json, write_jsonl
from scripts.screening.openai_batch_runner import OpenAIBatchRunner


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
        "batch_id": "rescue_sharded",
        "batch_status": "completed",
        "successes": successes,
        "failures": failures,
        "missing": missing,
        "output_row_count": output_row_count,
        "error_row_count": error_row_count,
    }


def rescue_run(
    *,
    run_id: str,
    paper_id: str,
    profile: full.BatchProfile,
    rerun_shard_size: int,
    poll_interval_sec: float,
    max_wait_minutes: float,
) -> dict[str, Any]:
    with fallback.scoped_papers([paper_id]):
        prepared = full.prepare_submit_payload(
            run_id=run_id,
            profile=profile,
            cost_cap_usd=float(read_json(run_dir(run_id) / "run_manifest.json").get("cost_cap_usd") or 10.0),
        )
        if prepared["status"] != "ready_to_submit":
            raise RuntimeError(f"prepare_submit_payload failed: {prepared}")

        load_dotenv_if_present()
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set; cannot run rescue.")

        rd = run_dir(run_id)
        artifact_dir = Path(prepared["artifact_dir"])
        spec_by_id = {spec.custom_id: spec for spec in prepared["specs"]}
        request_by_id = prepared["request_by_id"]
        manifest = read_json(rd / "run_manifest.json")
        shard_jobs = manifest.get("batch_phase", {}).get("shard_jobs", [])
        if not shard_jobs:
            raise RuntimeError(f"No shard jobs found in {run_id}")

        client = OpenAI()
        client.models.retrieve(profile.model)
        runner = OpenAIBatchRunner(client=client, poll_interval_sec=poll_interval_sec)

        parsed_parts: list[dict[str, Any]] = []
        output_rows: list[dict[str, Any]] = []
        rerun_custom_ids: list[str] = []
        collected_shards: list[int] = []
        cancelled_shards: list[int] = []

        for shard in shard_jobs:
            shard_artifact_dir = rd / Path(shard["artifact_dir"]).relative_to(repo_rel(rd))
            latest = runner.retrieve_batch(shard["batch_id"], artifact_dir=shard_artifact_dir)
            status = str(latest.get("status") or "")
            shard["rescue_observed_status"] = status
            if status == "completed":
                if (shard_artifact_dir / "parsed_results.json").exists():
                    parsed = read_json(shard_artifact_dir / "parsed_results.json")
                else:
                    parsed = runner.collect_results(
                        specs=[spec_by_id[custom_id] for custom_id in shard["custom_ids"]],
                        batch_payload=latest,
                        artifact_dir=shard_artifact_dir,
                    )
                parsed_parts.append(parsed)
                if (shard_artifact_dir / "output.jsonl").exists():
                    output_rows.extend(read_jsonl(shard_artifact_dir / "output.jsonl"))
                collected_shards.append(int(shard["shard_index"]))
                continue

            if status in {"validating", "in_progress", "finalizing"}:
                client.batches.cancel(shard["batch_id"])
                cancelled_shards.append(int(shard["shard_index"]))
                rerun_custom_ids.extend(shard["custom_ids"])
                continue

            if status in {"failed", "expired", "cancelled"}:
                rerun_custom_ids.extend(shard["custom_ids"])
                continue

            raise RuntimeError(f"Unexpected shard status for {run_id} shard {shard['shard_index']}: {status}")

        rescue_dir = ensure_dir(artifact_dir / "rescue_reruns")
        rerun_jobs: list[dict[str, Any]] = []
        for index, custom_ids in enumerate(fallback._chunk(rerun_custom_ids, rerun_shard_size), start=1):
            shard_artifact_dir = ensure_dir(rescue_dir / f"rerun_{index:02d}")
            submit_payload = runner.submit_requests(
                specs=[spec_by_id[custom_id] for custom_id in custom_ids],
                endpoint="/v1/chat/completions",
                artifact_dir=shard_artifact_dir,
                metadata={
                    "experiment": "bcpcs_full_corpus_batch_sharded_rescue",
                    "run_id": run_id,
                    "paper_id": paper_id,
                    "phase": full.PHASE,
                    "model": profile.model,
                    "rerun_index": str(index),
                },
            )
            rerun_jobs.append(
                {
                    "rerun_index": index,
                    "request_count": len(custom_ids),
                    "batch_id": submit_payload["batch_create"]["id"],
                    "artifact_dir": repo_rel(shard_artifact_dir),
                    "custom_ids": custom_ids,
                }
            )

        for rerun in rerun_jobs:
            shard_artifact_dir = rd / Path(rerun["artifact_dir"]).relative_to(repo_rel(rd))
            latest = runner.wait_until_terminal(
                rerun["batch_id"],
                artifact_dir=shard_artifact_dir,
                max_wait_minutes=max_wait_minutes,
            )
            if latest.get("status") in {"failed", "expired", "cancelled"}:
                write_json(shard_artifact_dir / "terminal_failure.json", latest)
                raise RuntimeError(f"Rescue rerun failed for {run_id} rerun {rerun['rerun_index']}: {latest.get('status')}")
            parsed = runner.collect_results(
                specs=[spec_by_id[custom_id] for custom_id in rerun["custom_ids"]],
                batch_payload=latest,
                artifact_dir=shard_artifact_dir,
            )
            parsed_parts.append(parsed)
            output_rows.extend(read_jsonl(shard_artifact_dir / "output.jsonl"))

        merged_parsed = _merge_parsed(parsed_parts)
        write_json(artifact_dir / "parsed_results.json", merged_parsed)
        write_jsonl(artifact_dir / "output.jsonl", output_rows)
        write_json(
            artifact_dir / "batch_latest.json",
            {
                "id": "rescue_sharded",
                "status": "completed",
                "request_counts": {
                    "total": len(prepared["specs"]),
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
            output_rows=output_rows,
            parsed=merged_parsed,
            request_by_id=request_by_id,
            batch_id="rescue_sharded",
        )
        full.assemble_full_corpus(run_id=run_id)
        summary = full.evaluate_full_corpus(run_id=run_id)
        validation = full.validate_run(run_id=run_id)
        report_path = full.write_report(run_id=run_id, summary=summary, validation=validation)

        manifest = read_json(rd / "run_manifest.json")
        manifest["status"] = "completed"
        manifest["batch_phase"]["batch_id"] = "rescue_sharded"
        manifest["batch_phase"]["batch_status"] = "completed"
        manifest["batch_phase"]["success_count"] = len(merged_parsed["successes"])
        manifest["batch_phase"]["failure_count"] = len(merged_parsed["failures"])
        manifest["batch_phase"]["missing_count"] = len(merged_parsed["missing"])
        manifest["batch_phase"]["cost_summary"] = cost_summary.get("phases", {}).get(full.PHASE)
        manifest["batch_phase"]["rescue"] = {
            "created_at": utc_now_iso(),
            "collected_completed_shards": collected_shards,
            "cancelled_incomplete_shards": cancelled_shards,
            "rerun_shard_size": rerun_shard_size,
            "rerun_request_count": len(rerun_custom_ids),
            "rerun_jobs": rerun_jobs,
        }
        manifest["evaluation_summary_full_corpus_path"] = repo_rel(rd / "evaluation_summary_full_corpus.json")
        manifest["validation_summary_full_corpus_path"] = repo_rel(rd / "validation_summary_full_corpus.json")
        manifest["report_path"] = repo_rel(report_path)
        manifest["updated_at"] = utc_now_iso()
        write_json(rd / "run_manifest.json", manifest)

        return {
            "status": "completed",
            "run_id": run_id,
            "collected_completed_shards": collected_shards,
            "cancelled_incomplete_shards": cancelled_shards,
            "rerun_request_count": len(rerun_custom_ids),
            "summary_path": repo_rel(rd / "evaluation_summary_full_corpus.json"),
            "report_path": repo_rel(report_path),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default=full.DEFAULT_REASONING_EFFORT)
    parser.add_argument("--max-completion-tokens", type=int, default=full.MAX_COMPLETION_TOKENS)
    parser.add_argument("--rerun-shard-size", type=int, default=2)
    parser.add_argument("--poll-interval-sec", type=float, default=15.0)
    parser.add_argument("--max-wait-minutes", type=float, default=240.0)
    args = parser.parse_args()
    payload = rescue_run(
        run_id=args.run_id,
        paper_id=args.paper_id,
        profile=full.make_profile(
            reasoning_effort=args.reasoning_effort,
            max_completion_tokens=args.max_completion_tokens,
        ),
        rerun_shard_size=args.rerun_shard_size,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
