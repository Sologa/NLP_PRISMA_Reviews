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
from failure_slice_common import load_dotenv_if_present, read_json, read_jsonl, repo_rel, run_dir, utc_now_iso, write_json, write_jsonl
from scripts.screening.openai_batch_runner import OpenAIBatchRunner


def _extract_message_content(body: dict[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("missing choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("missing message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "".join(parts)
    raise ValueError("missing assistant content")


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
        "batch_id": "sync_lastmile",
        "batch_status": "completed",
        "successes": successes,
        "failures": failures,
        "missing": missing,
        "output_row_count": output_row_count,
        "error_row_count": error_row_count,
    }


def run_sync_lastmile(
    *,
    run_id: str,
    paper_id: str,
    profile: full.BatchProfile,
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
            raise RuntimeError("OPENAI_API_KEY is not set; cannot run sync lastmile.")

        rd = run_dir(run_id)
        artifact_dir = Path(prepared["artifact_dir"])
        spec_by_id = {spec.custom_id: spec for spec in prepared["specs"]}
        request_by_id = prepared["request_by_id"]
        manifest = read_json(rd / "run_manifest.json")
        client = OpenAI()
        client.models.retrieve(profile.model)
        runner = OpenAIBatchRunner(client=client, poll_interval_sec=15.0)

        parsed_parts: list[dict[str, Any]] = []
        output_rows: list[dict[str, Any]] = []
        resolved_custom_ids: set[str] = set()
        batch_ids_to_cancel: list[str] = []

        def collect_completed_batch(batch_id: str, custom_ids: list[str], artifact_dir_path: Path) -> None:
            latest = runner.retrieve_batch(batch_id, artifact_dir=artifact_dir_path)
            status = str(latest.get("status") or "")
            if status == "completed":
                parsed = runner.collect_results(
                    specs=[spec_by_id[custom_id] for custom_id in custom_ids],
                    batch_payload=latest,
                    artifact_dir=artifact_dir_path,
                )
                parsed_parts.append(parsed)
                if (artifact_dir_path / "output.jsonl").exists():
                    output_rows.extend(read_jsonl(artifact_dir_path / "output.jsonl"))
                resolved_custom_ids.update(custom_ids)
            elif status in {"validating", "in_progress", "finalizing", "cancelling"}:
                batch_ids_to_cancel.append(batch_id)
            elif status in {"failed", "expired", "cancelled"}:
                pass
            else:
                raise RuntimeError(f"unexpected status {status} for {batch_id}")

        for shard in manifest.get("batch_phase", {}).get("shard_jobs", []):
            shard_artifact_dir = rd / Path(shard["artifact_dir"]).relative_to(repo_rel(rd))
            collect_completed_batch(shard["batch_id"], shard["custom_ids"], shard_artifact_dir)

        rescue_root = artifact_dir / "rescue_reruns"
        for batch_create in sorted(rescue_root.glob("rerun_*/batch_create.json")):
            rerun_dir = batch_create.parent
            batch_payload = read_json(batch_create)
            input_rows = read_jsonl(rerun_dir / "input.jsonl")
            custom_ids = [str(row.get("custom_id")) for row in input_rows if row.get("custom_id")]
            collect_completed_batch(str(batch_payload["id"]), custom_ids, rerun_dir)

        for batch_id in batch_ids_to_cancel:
            try:
                client.batches.cancel(batch_id)
            except Exception:
                pass

        remaining_custom_ids = [custom_id for custom_id in request_by_id if custom_id not in resolved_custom_ids]
        sync_dir = artifact_dir / "sync_lastmile"
        sync_dir.mkdir(parents=True, exist_ok=True)
        sync_successes: list[dict[str, Any]] = []
        sync_failures: list[dict[str, Any]] = []
        sync_output_rows: list[dict[str, Any]] = []

        for custom_id in remaining_custom_ids:
            spec = spec_by_id[custom_id]
            try:
                response = client.chat.completions.create(**spec.body)
                body = response.model_dump(mode="json")
                assistant_text = _extract_message_content(body)
                payload = json.loads(assistant_text.strip())
                parsed = spec.response_model.model_validate(payload)
                if spec.validator is not None:
                    spec.validator(parsed)
                sync_successes.append(
                    {
                        "custom_id": custom_id,
                        "status": "ok",
                        "context": spec.context,
                        "assistant_text": assistant_text,
                        "parsed": parsed.model_dump(mode="json"),
                    }
                )
                sync_output_rows.append(
                    {
                        "custom_id": custom_id,
                        "response": {
                            "status_code": 200,
                            "body": body,
                        },
                    }
                )
            except Exception as exc:  # noqa: BLE001
                sync_failures.append(
                    {
                        "custom_id": custom_id,
                        "status": "sync_failed",
                        "context": spec.context,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )

        sync_parsed = {
            "batch_id": "sync_lastmile",
            "batch_status": "completed",
            "successes": sync_successes,
            "failures": sync_failures,
            "missing": [],
            "output_row_count": len(sync_output_rows),
            "error_row_count": 0,
        }
        write_json(sync_dir / "parsed_results.json", sync_parsed)
        write_jsonl(sync_dir / "output.jsonl", sync_output_rows)
        parsed_parts.append(sync_parsed)
        output_rows.extend(sync_output_rows)

        merged_parsed = _merge_parsed(parsed_parts)
        write_json(artifact_dir / "parsed_results.json", merged_parsed)
        write_jsonl(artifact_dir / "output.jsonl", output_rows)
        write_json(
            artifact_dir / "batch_latest.json",
            {
                "id": "sync_lastmile",
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
            batch_id="sync_lastmile",
        )
        full.assemble_full_corpus(run_id=run_id)
        summary = full.evaluate_full_corpus(run_id=run_id)
        validation = full.validate_run(run_id=run_id)
        report_path = full.write_report(run_id=run_id, summary=summary, validation=validation)

        manifest = read_json(rd / "run_manifest.json")
        manifest["status"] = "completed"
        manifest["batch_phase"]["batch_id"] = "sync_lastmile"
        manifest["batch_phase"]["batch_status"] = "completed"
        manifest["batch_phase"]["success_count"] = len(merged_parsed["successes"])
        manifest["batch_phase"]["failure_count"] = len(merged_parsed["failures"])
        manifest["batch_phase"]["missing_count"] = len(merged_parsed["missing"])
        manifest["batch_phase"]["cost_summary"] = cost_summary.get("phases", {}).get(full.PHASE)
        manifest["batch_phase"]["sync_lastmile"] = {
            "created_at": utc_now_iso(),
            "remaining_custom_ids": remaining_custom_ids,
            "sync_success_count": len(sync_successes),
            "sync_failure_count": len(sync_failures),
        }
        manifest["evaluation_summary_full_corpus_path"] = repo_rel(rd / "evaluation_summary_full_corpus.json")
        manifest["validation_summary_full_corpus_path"] = repo_rel(rd / "validation_summary_full_corpus.json")
        manifest["report_path"] = repo_rel(report_path)
        manifest["updated_at"] = utc_now_iso()
        write_json(rd / "run_manifest.json", manifest)

        return {
            "status": "completed",
            "run_id": run_id,
            "remaining_custom_ids": len(remaining_custom_ids),
            "sync_success_count": len(sync_successes),
            "sync_failure_count": len(sync_failures),
            "summary_path": repo_rel(rd / "evaluation_summary_full_corpus.json"),
            "report_path": repo_rel(report_path),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default=full.DEFAULT_REASONING_EFFORT)
    parser.add_argument("--max-completion-tokens", type=int, default=full.MAX_COMPLETION_TOKENS)
    args = parser.parse_args()
    payload = run_sync_lastmile(
        run_id=args.run_id,
        paper_id=args.paper_id,
        profile=full.make_profile(
            reasoning_effort=args.reasoning_effort,
            max_completion_tokens=args.max_completion_tokens,
        ),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
