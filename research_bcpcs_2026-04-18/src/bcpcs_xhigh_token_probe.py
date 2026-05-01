#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from typing import Any

import failure_slice_recall_repair_runner as recall
from bcpcs_full_corpus_batch_runner import PROFILE
from failure_slice_common import (
    REPO_ROOT,
    ensure_dir,
    estimate_batch_cost,
    load_dotenv_if_present,
    read_json,
    read_jsonl,
    utc_now_iso,
    write_json,
)
from scripts.screening.openai_batch_runner import BatchRequestSpec, OpenAIBatchRunner


DEFAULT_SOURCE_INPUT = REPO_ROOT / "research_bcpcs_2026-04-18" / "runs" / "bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926" / "batch_jobs" / "stage2_recall_repair_batch" / "gpt-5.4-mini" / "input.jsonl"
DEFAULT_SAMPLE_IDS = [
    "stage2_recall_repair_batch__2601.19926__rogers_primer_2020",
    "stage2_recall_repair_batch__2601.19926__zhou_linguistic_2025",
]
DEFAULT_BUDGETS = [4096, 12288, 25000, 32000, 50000, 65536]
DEFAULT_REASONING_EFFORT = "xhigh"


def _extract_message_content(body: dict[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                chunks.append(item["text"])
        return "".join(chunks)
    return ""


def _sample_specs(
    *,
    source_input: Path,
    sample_ids: list[str],
    budgets: list[int],
    reasoning_effort: str,
) -> tuple[list[BatchRequestSpec], dict[str, dict[str, Any]]]:
    input_rows = read_jsonl(source_input)
    by_id = {str(row.get("custom_id")): row for row in input_rows if row.get("custom_id")}
    specs: list[BatchRequestSpec] = []
    requests: dict[str, dict[str, Any]] = {}
    missing = [custom_id for custom_id in sample_ids if custom_id not in by_id]
    if missing:
        raise KeyError(f"Missing sample ids in {source_input}: {missing}")
    for original_custom_id in sample_ids:
        row = by_id[original_custom_id]
        candidate_key = original_custom_id.split("__", 2)[-1]
        original_body = row.get("body")
        if not isinstance(original_body, dict):
            raise ValueError(f"Request body missing for {original_custom_id}")
        for budget in budgets:
            custom_id = f"{original_custom_id}__mct{budget}"
            body = copy.deepcopy(original_body)
            body["max_completion_tokens"] = budget
            body["reasoning_effort"] = reasoning_effort
            requests[custom_id] = {
                "custom_id": custom_id,
                "original_custom_id": original_custom_id,
                "candidate_key": candidate_key,
                "body": body,
                "budget": budget,
                "reasoning_effort": reasoning_effort,
            }
            specs.append(
                BatchRequestSpec(
                    custom_id=custom_id,
                    model=str(body.get("model")),
                    body=body,
                    response_model=recall.RecallRepairDecisionOutput,
                    validator=lambda payload, expected_key=candidate_key: (
                        None if payload.candidate_key == expected_key else (_ for _ in ()).throw(ValueError(f"candidate_key mismatch: {payload.candidate_key} != {expected_key}"))
                    ),
                    context={
                        "original_custom_id": original_custom_id,
                        "candidate_key": candidate_key,
                        "budget": budget,
                    },
                )
            )
    return specs, requests


def _summarize(
    *,
    requests: dict[str, dict[str, Any]],
    parsed: dict[str, Any],
    output_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    output_by_id = {str(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
    success_ids = {str(row.get("custom_id")) for row in parsed.get("successes", [])}
    failure_by_id = {str(row.get("custom_id")): row for row in parsed.get("failures", [])}
    rows: list[dict[str, Any]] = []
    by_budget: dict[int, dict[str, Any]] = {}

    for custom_id, request in sorted(requests.items(), key=lambda item: (item[1]["original_custom_id"], item[1]["budget"])):
        output = output_by_id.get(custom_id, {})
        response = output.get("response", {})
        body = response.get("body", {}) if isinstance(response, dict) else {}
        choices = body.get("choices", []) if isinstance(body, dict) else []
        choice = choices[0] if isinstance(choices, list) and choices else {}
        finish_reason = choice.get("finish_reason")
        content = _extract_message_content(body) if isinstance(body, dict) else ""
        usage = body.get("usage", {}) if isinstance(body, dict) else {}
        details = usage.get("completion_tokens_details", {}) if isinstance(usage, dict) else {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        reasoning_tokens = int(details.get("reasoning_tokens") or 0)
        cost_usd = estimate_batch_cost(input_tokens=prompt_tokens, output_tokens=completion_tokens, rates=PROFILE.rates)
        parse_status = "success" if custom_id in success_ids else ("failure" if custom_id in failure_by_id else "missing")
        failure = failure_by_id.get(custom_id, {})
        row = {
            "custom_id": custom_id,
            "original_custom_id": request["original_custom_id"],
            "candidate_key": request["candidate_key"],
            "budget": request["budget"],
            "finish_reason": finish_reason,
            "content_length": len(content),
            "parse_status": parse_status,
            "error_type": failure.get("error_type"),
            "error": failure.get("error"),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "cost_usd": cost_usd,
        }
        rows.append(row)
        bucket = by_budget.setdefault(
            request["budget"],
            {
                "budget": request["budget"],
                "request_count": 0,
                "success_count": 0,
                "nonempty_content_count": 0,
                "length_finish_count": 0,
                "total_cost_usd": 0.0,
                "max_reasoning_tokens": 0,
            },
        )
        bucket["request_count"] += 1
        bucket["success_count"] += 1 if parse_status == "success" else 0
        bucket["nonempty_content_count"] += 1 if len(content) > 0 else 0
        bucket["length_finish_count"] += 1 if finish_reason == "length" else 0
        bucket["total_cost_usd"] += cost_usd
        bucket["max_reasoning_tokens"] = max(bucket["max_reasoning_tokens"], reasoning_tokens)

    thresholds = {
        "first_budget_with_any_nonempty_content": None,
        "first_budget_with_any_parse_success": None,
        "first_budget_with_all_parse_successes": None,
    }
    for budget in sorted(by_budget):
        bucket = by_budget[budget]
        if thresholds["first_budget_with_any_nonempty_content"] is None and bucket["nonempty_content_count"] > 0:
            thresholds["first_budget_with_any_nonempty_content"] = budget
        if thresholds["first_budget_with_any_parse_success"] is None and bucket["success_count"] > 0:
            thresholds["first_budget_with_any_parse_success"] = budget
        if thresholds["first_budget_with_all_parse_successes"] is None and bucket["success_count"] == bucket["request_count"]:
            thresholds["first_budget_with_all_parse_successes"] = budget

    return {
        "created_at": utc_now_iso(),
        "request_count": len(rows),
        "sample_count": len({row["original_custom_id"] for row in rows}),
        "thresholds": thresholds,
        "by_budget": [by_budget[budget] for budget in sorted(by_budget)],
        "rows": rows,
        "total_cost_usd": sum(row["cost_usd"] for row in rows),
    }


def run_probe(
    *,
    run_id: str,
    source_input: Path,
    sample_ids: list[str],
    budgets: list[int],
    reasoning_effort: str,
    poll_interval_sec: float,
    max_wait_minutes: float,
) -> dict[str, Any]:
    artifact_dir = ensure_dir(
        REPO_ROOT
        / "research_bcpcs_2026-04-18"
        / "runs"
        / run_id
        / "batch_jobs"
        / "stage2_recall_repair_batch"
        / "gpt-5.4-mini"
    )
    specs, requests = _sample_specs(
        source_input=source_input,
        sample_ids=sample_ids,
        budgets=budgets,
        reasoning_effort=reasoning_effort,
    )
    manifest = {
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "source_input": str(source_input.relative_to(REPO_ROOT)),
        "sample_ids": sample_ids,
        "budgets": budgets,
        "request_count": len(specs),
        "model": "gpt-5.4-mini",
        "reasoning_effort": reasoning_effort,
        "notes": "BCPCS micro-batch probe using exact request bodies copied from an existing failed all4 xhigh run, varying max_completion_tokens and optionally reasoning effort.",
    }
    write_json(artifact_dir.parent.parent / "probe_manifest.json", manifest)

    load_dotenv_if_present()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set after dotenv load")

    from openai import OpenAI

    client = OpenAI()
    client.models.retrieve("gpt-5.4-mini")
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=poll_interval_sec)
    submit = runner.submit_requests(
        specs=specs,
        endpoint="/v1/chat/completions",
        artifact_dir=artifact_dir,
        metadata={"experiment": "bcpcs_xhigh_token_probe", "run_id": run_id},
    )
    latest = runner.wait_until_terminal(
        submit["batch_create"]["id"],
        artifact_dir=artifact_dir,
        max_wait_minutes=max_wait_minutes,
    )
    parsed = runner.collect_results(specs=specs, batch_payload=latest, artifact_dir=artifact_dir)
    output_rows = read_jsonl(artifact_dir / "output.jsonl") if (artifact_dir / "output.jsonl").exists() else []
    summary = _summarize(requests=requests, parsed=parsed, output_rows=output_rows)
    summary["batch_id"] = latest.get("id")
    summary["batch_status"] = latest.get("status")
    summary["artifact_dir"] = str(artifact_dir.relative_to(REPO_ROOT))
    write_json(artifact_dir.parent.parent / "probe_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe BCPCS xhigh token budgets on 1-2 copied stage2 requests.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-input", type=Path, default=DEFAULT_SOURCE_INPUT)
    parser.add_argument("--sample-id", action="append", dest="sample_ids")
    parser.add_argument("--budget", action="append", dest="budgets", type=int)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT, choices=["none", "minimal", "low", "medium", "high", "xhigh"])
    parser.add_argument("--poll-interval-sec", type=float, default=10.0)
    parser.add_argument("--max-wait-minutes", type=float, default=90.0)
    args = parser.parse_args()

    summary = run_probe(
        run_id=args.run_id,
        source_input=args.source_input,
        sample_ids=args.sample_ids or DEFAULT_SAMPLE_IDS,
        budgets=args.budgets or DEFAULT_BUDGETS,
        reasoning_effort=args.reasoning_effort,
        poll_interval_sec=args.poll_interval_sec,
        max_wait_minutes=args.max_wait_minutes,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
