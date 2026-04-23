#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from failure_slice_common import (
    CostRates,
    REPO_ROOT,
    REPORTS_ROOT,
    RUNS_ROOT,
    append_jsonl,
    cost_dir,
    ensure_dir,
    estimate_batch_cost,
    estimate_text_tokens,
    load_dotenv_if_present,
    paper_dir,
    read_json,
    read_jsonl,
    repo_rel,
    request_rows_token_estimate,
    run_dir,
    safe_text,
    usage_from_batch_output_row,
    utc_now_iso,
    write_json,
    write_jsonl,
)
from failure_slice_cost_audit import audit_cost_ledger
from failure_slice_eval import decision_to_prediction, evidence_validity, load_gold_labels
from failure_slice_validate import find_forbidden_prompt_terms
import failure_slice_direct_repair_runner as direct
import failure_slice_recall_repair_runner as recall
import failure_slice_runner as base
from scripts.screening.experiment_workflows import fulltext_payload_from_resolution, metadata_payload
from scripts.screening.openai_batch_runner import (
    BatchRequestSpec,
    OpenAIBatchRunner,
    build_json_schema_response_format,
)


TODAY = time.strftime("%Y-%m-%d")
PAPER_IDS = ["2307.05527", "2409.13738", "2511.13936", "2601.19926"]
RUN_ID = f"bcpcs_full_corpus_batch_gpt54mini_recallv3_all4_{TODAY}_v1"
PHASE = "stage2_recall_repair_batch"
MAX_COMPLETION_TOKENS = 4096
DEFAULT_REASONING_EFFORT = "low"


@dataclass(frozen=True)
class BatchProfile:
    model: str
    reasoning_effort: str
    max_completion_tokens: int
    evidence_packet_chars: int
    max_quotes: int
    rates: CostRates


PROFILE = BatchProfile(
    model="gpt-5.4-mini",
    reasoning_effort=DEFAULT_REASONING_EFFORT,
    max_completion_tokens=MAX_COMPLETION_TOKENS,
    evidence_packet_chars=9000,
    max_quotes=12,
    rates=CostRates(
        input_per_million=0.75,
        cached_input_per_million=0.075,
        output_per_million=4.50,
        batch_discount=0.5,
        source="https://developers.openai.com/api/docs/models/gpt-5.4-mini/",
    ),
)


def _git_status_short() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout.splitlines()


def _status_paths(lines: list[str]) -> set[str]:
    paths: set[str] = set()
    for line in lines:
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.add(path)
    return paths


def _pricing_snapshot(profile: BatchProfile) -> dict[str, Any]:
    return {
        "captured_at": utc_now_iso(),
        "model": profile.model,
        "pricing_basis": "Batch API text tokens, per 1M tokens",
        "standard_rates_usd_per_1m": {
            "input": profile.rates.input_per_million,
            "cached_input": profile.rates.cached_input_per_million,
            "output": profile.rates.output_per_million,
        },
        "batch_discount": profile.rates.batch_discount,
        "effective_batch_rates_usd_per_1m": {
            "input": profile.rates.effective_input_per_million(),
            "output": profile.rates.effective_output_per_million(),
        },
        "sources": [
            "https://openai.com/api/pricing/",
            "https://developers.openai.com/api/docs/models/gpt-5.4-mini/",
        ],
        "notes": [
            "This run uses the current BCPCS V3 recall-repair architecture with Batch API.",
            "Prompting and local evidence packet logic are reused from failure_slice_recall_repair_runner.py.",
        ],
    }


def _gold_rows(paper_id: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
    return read_jsonl(path)


def freeze_full_corpus_inventory(*, run_id: str) -> dict[str, Any]:
    rd = ensure_dir(run_dir(run_id))
    cases: list[dict[str, Any]] = []
    per_paper_counts: dict[str, int] = {}
    per_paper_positive: dict[str, int] = {}
    per_paper_negative: dict[str, int] = {}
    for paper_id in PAPER_IDS:
        rows = _gold_rows(paper_id)
        per_paper_counts[paper_id] = len(rows)
        per_paper_positive[paper_id] = sum(1 for row in rows if row.get("is_evidence_base") is True)
        per_paper_negative[paper_id] = sum(1 for row in rows if row.get("is_evidence_base") is False)
        for row in rows:
            key = safe_text(row.get("key"))
            if not key:
                continue
            cases.append(
                {
                    "paper_id": paper_id,
                    "candidate_key": key,
                    "slice_type": "full_corpus_all",
                    "source_artifact": repo_rel(REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"),
                    "allowed_for_unbiased_eval": True,
                    "debug_exposure": False,
                    "leakage_notes": "",
                }
            )
    cases.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    summary = {
        "scope": "full_corpus_all4",
        "paper_ids": PAPER_IDS,
        "total_count": len(cases),
        "per_paper_counts": per_paper_counts,
        "per_paper_positive": per_paper_positive,
        "per_paper_negative": per_paper_negative,
        "positive_count": sum(per_paper_positive.values()),
        "negative_count": sum(per_paper_negative.values()),
    }
    public_payload = {"scope": "full_corpus_all4", "cases": cases, "summary": summary}
    private_payload = {"scope": "full_corpus_all4", "cases": cases, "summary": summary}
    write_json(rd / "failure_slice_keys.json", public_payload)
    write_json(rd / "evaluation_inventory_private.json", private_payload)
    write_json(rd / "full_corpus_inventory.json", public_payload)
    return public_payload


def init_run(*, run_id: str, profile: BatchProfile, cost_cap_usd: float) -> dict[str, Any]:
    rd = ensure_dir(run_dir(run_id))
    ensure_dir(cost_dir(run_id))
    ensure_dir(rd / "batch_jobs" / PHASE / profile.model)
    ensure_dir(rd / "papers")
    inventory = freeze_full_corpus_inventory(run_id=run_id)
    write_json(cost_dir(run_id) / "pricing_snapshot.json", _pricing_snapshot(profile))
    pre_status = _git_status_short()
    manifest = {
        "run_id": run_id,
        "experiment_name": "bcpcs_full_corpus_batch",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "scope": "full_corpus_all4",
        "paper_ids": PAPER_IDS,
        "model": profile.model,
        "reviewer": "single_reviewer",
        "workflow": "bcpcs_v3_recall_repair_batch_full_corpus",
        "reasoning_effort": profile.reasoning_effort,
        "max_completion_tokens": profile.max_completion_tokens,
        "cost_cap_usd": cost_cap_usd,
        "status": "initialized",
        "run_dir": repo_rel(rd),
        "inventory_path": repo_rel(rd / "full_corpus_inventory.json"),
        "pricing_snapshot_path": repo_rel(cost_dir(run_id) / "pricing_snapshot.json"),
        "source_counts": inventory["summary"],
        "is_bcpcs_architecture": True,
        "is_failure_slice_diagnostic": False,
        "write_scope": "research_bcpcs_2026-04-18 only",
        "pre_run_git_status_short": pre_status,
        "pre_run_outside_research_changes": sorted(path for path in _status_paths(pre_status) if not path.startswith("research_bcpcs_2026-04-18/")),
    }
    write_json(rd / "run_manifest.json", manifest)
    return manifest


def _body(prompt: str, profile: BatchProfile) -> dict[str, Any]:
    return {
        "model": profile.model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(
            recall.RecallRepairDecisionOutput,
            schema_name="BCPCSRecallRepairDecisionOutput",
        ),
        "reasoning_effort": profile.reasoning_effort,
        "max_completion_tokens": profile.max_completion_tokens,
    }


def _validate_recall_output(payload: recall.RecallRepairDecisionOutput, *, candidate_key: str) -> None:
    if payload.candidate_key != candidate_key:
        raise ValueError(f"candidate_key mismatch: {payload.candidate_key} != {candidate_key}")


def prepare_specs(*, run_id: str, profile: BatchProfile) -> tuple[list[BatchRequestSpec], dict[str, dict[str, Any]]]:
    rd = run_dir(run_id)
    paper_data = base._prepare_common(rd)
    stage1_by_key = base._load_stage_records_by_key(rd, "stage1_review")
    specs: list[BatchRequestSpec] = []
    request_by_id: dict[str, dict[str, Any]] = {}
    for paper_id, data in paper_data.items():
        criteria_path = base._criteria_path(paper_id, "stage2")
        criteria = read_json(criteria_path)
        metadata_path = base._metadata_path(paper_id)
        selected: list[str] = []
        for record in data["records"]:
            key = safe_text(record.get("key"))
            cutoff = data["cutoff_result"]["decisions_by_key"][key]
            artifact = data["artifact_result"]["decisions_by_key"][key]
            if not cutoff["cutoff_pass"] or not artifact["gate_pass"]:
                continue
            resolution = data["resolution_by_key"][key]
            if resolution["resolution_status"] not in {"exact", "normalized"} or not resolution.get("fulltext_gate_pass", True):
                continue
            selected.append(key)
            fulltext_text, fulltext_meta = fulltext_payload_from_resolution(
                resolution,
                repo_root=REPO_ROOT,
                head_chars=90_000,
                tail_chars=0,
            )
            source_path = safe_text(fulltext_meta.get("fulltext_source_path") or resolution.get("resolved_path"))
            evidence_packet = direct.build_local_evidence_packet(
                paper_id=paper_id,
                criteria=criteria,
                metadata=metadata_payload(record),
                fulltext_text=fulltext_text,
                source_path=source_path,
                metadata_path=repo_rel(metadata_path),
                max_chars=profile.evidence_packet_chars,
                max_quotes=profile.max_quotes,
            )
            stage1 = stage1_by_key.get((paper_id, key))
            prompt = recall.build_recall_prompt(
                paper_id=paper_id,
                candidate_key=key,
                criteria=criteria,
                metadata=metadata_payload(record),
                stage1_output=stage1["review_output"] if stage1 else None,
                evidence_packet=evidence_packet,
                criteria_path=repo_rel(criteria_path),
                metadata_path=repo_rel(metadata_path),
            )
            custom_id = f"{PHASE}__{paper_id}__{key}"
            request = {
                "custom_id": custom_id,
                "paper_id": paper_id,
                "candidate_key": key,
                "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                "phase": PHASE,
                "stage": "stage2",
                "criteria_path": repo_rel(criteria_path),
                "metadata_path": repo_rel(metadata_path),
                "fulltext_resolution": resolution,
                "evidence_packet": evidence_packet,
                "body": _body(prompt, profile),
            }
            request_by_id[custom_id] = request
            specs.append(
                BatchRequestSpec(
                    custom_id=custom_id,
                    model=profile.model,
                    body=request["body"],
                    response_model=recall.RecallRepairDecisionOutput,
                    validator=lambda payload, expected_key=key: _validate_recall_output(payload, candidate_key=expected_key),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": request["candidate_title"],
                        "phase": PHASE,
                        "stage": "stage2",
                        "criteria_path": request["criteria_path"],
                        "metadata_path": request["metadata_path"],
                    },
                )
            )
        write_json(paper_dir(run_id, paper_id) / "selected_for_stage2_bcpcs.keys.json", selected)
    return specs, request_by_id


def _prompt_hits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in rows:
        terms = find_forbidden_prompt_terms(json.dumps(row.get("body", {}), ensure_ascii=False))
        if terms:
            hits.append({"custom_id": row.get("custom_id"), "terms": terms})
    return hits


def _estimate_cost(rows: list[dict[str, Any]], profile: BatchProfile) -> dict[str, Any]:
    input_tokens = request_rows_token_estimate(rows)
    output_tokens = len(rows) * profile.max_completion_tokens
    return {
        "request_count": len(rows),
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": estimate_batch_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            rates=profile.rates,
        ),
    }


def _update_cost(*, run_id: str, profile: BatchProfile, output_rows: list[dict[str, Any]], parsed: dict[str, Any], request_by_id: dict[str, dict[str, Any]], batch_id: str) -> dict[str, Any]:
    output_by_id = {safe_text(row.get("custom_id")): row for row in output_rows if row.get("custom_id")}
    success_by_id = {row["custom_id"]: row for row in parsed.get("successes", [])}
    for custom_id, request in request_by_id.items():
        raw = output_by_id.get(custom_id, {})
        usage = usage_from_batch_output_row(raw)
        assistant = safe_text(success_by_id.get(custom_id, {}).get("assistant_text"))
        if usage and "input_tokens" in usage and "output_tokens" in usage:
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
            source = "batch_usage"
        else:
            input_tokens = estimate_text_tokens(json.dumps(request["body"], ensure_ascii=False))
            output_tokens = estimate_text_tokens(assistant) if assistant else profile.max_completion_tokens
            source = "estimated"
        cost = estimate_batch_cost(input_tokens=input_tokens, output_tokens=output_tokens, rates=profile.rates)
        append_jsonl(
            cost_dir(run_id) / "cost_ledger.jsonl",
            {
                "created_at": utc_now_iso(),
                "phase": PHASE,
                "custom_id": custom_id,
                "batch_id": batch_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "cost_source": source,
            },
        )
    return audit_cost_ledger(run_path=run_dir(run_id), rewrite_summary=True)["deduped_summary"]


def _write_stage2_outputs(*, run_id: str, parsed: dict[str, Any], request_by_id: dict[str, dict[str, Any]], profile: BatchProfile) -> None:
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in parsed.get("successes", []):
        request = request_by_id[item["custom_id"]]
        stage_output = recall.recall_output_to_stage_output(
            request=request,
            compact=item["parsed"],
            profile=recall.RecallProfile(
                profile_id="recall_boundary_maybe_v1",
                model=profile.model,
                reasoning_effort=profile.reasoning_effort,
                max_completion_tokens=profile.max_completion_tokens,
                evidence_packet_chars=profile.evidence_packet_chars,
                max_quotes=profile.max_quotes,
                promotable=False,
                rates=CostRates(
                    input_per_million=profile.rates.input_per_million,
                    cached_input_per_million=profile.rates.cached_input_per_million,
                    output_per_million=profile.rates.output_per_million,
                    batch_discount=0.0,
                ),
            ),
        )
        ctx = item["context"]
        rows_by_paper[ctx["paper_id"]].append(
            {
                "paper_id": ctx["paper_id"],
                "candidate_key": ctx["candidate_key"],
                "candidate_title": ctx["candidate_title"],
                "phase": PHASE,
                "stage": "stage2",
                "model": profile.model,
                "profile_id": "recall_boundary_maybe_v1",
                "criteria_path": ctx["criteria_path"],
                "metadata_path": ctx["metadata_path"],
                "review_output": stage_output,
                "recall_repair_decision": item["parsed"],
            }
        )
    for paper_id, rows in rows_by_paper.items():
        rows.sort(key=lambda row: row["candidate_key"])
        write_json(paper_dir(run_id, paper_id) / "stage2_review.json", rows)
    for paper_id in PAPER_IDS:
        path = paper_dir(run_id, paper_id) / "stage2_review.json"
        if not path.exists():
            write_json(path, [])


def _load_batch_id(*, artifact_dir: Path) -> str:
    for name in ("batch_terminal.json", "batch_latest.json", "batch_create.json"):
        path = artifact_dir / name
        if not path.exists():
            continue
        payload = read_json(path)
        batch_id = safe_text(payload.get("id"))
        if batch_id:
            return batch_id
    raise FileNotFoundError(f"No batch id found under {artifact_dir}")


def prepare_submit_payload(*, run_id: str, profile: BatchProfile, cost_cap_usd: float, dry_run: bool = False) -> dict[str, Any]:
    rd = run_dir(run_id)
    direct.write_synthetic_stage1(run_id=run_id)
    specs, request_by_id = prepare_specs(run_id=run_id, profile=profile)
    rows = [{"custom_id": spec.custom_id, "method": "POST", "url": "/v1/chat/completions", "body": spec.body} for spec in specs]
    artifact_dir = ensure_dir(rd / "batch_jobs" / PHASE / profile.model)
    write_jsonl(artifact_dir / "input.jsonl", rows)
    prompt_hits = _prompt_hits(rows)
    write_json(artifact_dir / "forbidden_prompt_scan.json", {"hit_count": len(prompt_hits), "hits": prompt_hits})
    estimate = _estimate_cost(rows, profile)
    estimate_payload = {
        "created_at": utc_now_iso(),
        "phase": PHASE,
        "request_count": estimate["request_count"],
        "estimated_input_tokens": estimate["estimated_input_tokens"],
        "estimated_output_tokens": estimate["estimated_output_tokens"],
        "estimated_cost_usd": estimate["estimated_cost_usd"],
        "cost_cap_usd": cost_cap_usd,
        "would_exceed_cost_cap": estimate["estimated_cost_usd"] > cost_cap_usd,
        "estimate_policy": "input tokenizer_or_char_overestimate; output max_completion_tokens per request with Batch discount",
    }
    write_json(cost_dir(run_id) / f"pre_submit_estimate.{PHASE}.json", estimate_payload)
    if prompt_hits:
        raise RuntimeError(f"Forbidden prompt terms detected: {prompt_hits[:3]}")
    if estimate["estimated_cost_usd"] > cost_cap_usd:
        write_json(cost_dir(run_id) / "cost_stop.json", estimate_payload)
        return {
            "status": "stopped_cost_cap_before_submit",
            "estimate": estimate_payload,
            "specs": specs,
            "request_by_id": request_by_id,
            "artifact_dir": artifact_dir,
        }
    if dry_run:
        return {
            "status": "dry_run_not_submitted",
            "estimate": estimate_payload,
            "specs": specs,
            "request_by_id": request_by_id,
            "artifact_dir": artifact_dir,
        }
    return {
        "status": "ready_to_submit",
        "estimate": estimate_payload,
        "specs": specs,
        "request_by_id": request_by_id,
        "artifact_dir": artifact_dir,
    }


def submit_only(*, run_id: str, profile: BatchProfile, cost_cap_usd: float, poll_interval_sec: float = 30.0) -> dict[str, Any]:
    rd = run_dir(run_id)
    prepared = prepare_submit_payload(run_id=run_id, profile=profile, cost_cap_usd=cost_cap_usd)
    if prepared["status"] != "ready_to_submit":
        return prepared

    load_dotenv_if_present()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; cannot submit Batch job.")
    from openai import OpenAI

    client = OpenAI()
    client.models.retrieve(profile.model)
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=poll_interval_sec)
    submit_payload = runner.submit_requests(
        specs=prepared["specs"],
        endpoint="/v1/chat/completions",
        artifact_dir=prepared["artifact_dir"],
        metadata={"experiment": "bcpcs_full_corpus_batch", "run_id": run_id, "phase": PHASE, "model": profile.model},
    )
    manifest = read_json(rd / "run_manifest.json")
    manifest["status"] = "submitted"
    manifest["batch_phase"] = {
        "phase": PHASE,
        "artifact_dir": repo_rel(prepared["artifact_dir"]),
        "batch_id": submit_payload["batch_create"]["id"],
        "batch_status": submit_payload["batch_create"]["status"],
        "request_count": len(prepared["specs"]),
        "pre_submit_estimate": prepared["estimate"],
    }
    manifest["updated_at"] = utc_now_iso()
    write_json(rd / "run_manifest.json", manifest)
    return {
        "status": "submitted",
        "estimate": prepared["estimate"],
        "batch": submit_payload["batch_create"],
    }


def collect_existing_batch(*, run_id: str, profile: BatchProfile, poll_interval_sec: float, max_wait_minutes: float, batch_id: str | None = None) -> dict[str, Any]:
    rd = run_dir(run_id)
    prepared = prepare_submit_payload(run_id=run_id, profile=profile, cost_cap_usd=float(read_json(rd / "run_manifest.json").get("cost_cap_usd") or 10.0))
    artifact_dir = prepared["artifact_dir"]
    resolved_batch_id = batch_id or _load_batch_id(artifact_dir=artifact_dir)

    load_dotenv_if_present()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; cannot collect Batch job.")
    from openai import OpenAI

    client = OpenAI()
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=poll_interval_sec)
    latest = runner.wait_until_terminal(resolved_batch_id, artifact_dir=artifact_dir, max_wait_minutes=max_wait_minutes)
    if latest.get("status") in {"failed", "expired", "cancelled"}:
        write_json(artifact_dir / "terminal_failure.json", latest)
        return {"status": "terminal_batch_failure", "batch": latest, "estimate": prepared["estimate"]}
    parsed = runner.collect_results(specs=prepared["specs"], batch_payload=latest, artifact_dir=artifact_dir)
    output_rows = read_jsonl(artifact_dir / "output.jsonl") if (artifact_dir / "output.jsonl").exists() else []
    _write_stage2_outputs(run_id=run_id, parsed=parsed, request_by_id=prepared["request_by_id"], profile=profile)
    cost_summary = _update_cost(
        run_id=run_id,
        profile=profile,
        output_rows=output_rows,
        parsed=parsed,
        request_by_id=prepared["request_by_id"],
        batch_id=safe_text(latest.get("id")),
    )
    manifest = read_json(rd / "run_manifest.json")
    manifest["status"] = "collected"
    manifest["batch_phase"] = {
        "phase": PHASE,
        "artifact_dir": repo_rel(artifact_dir),
        "batch_id": latest.get("id"),
        "batch_status": latest.get("status"),
        "request_count": len(prepared["specs"]),
        "success_count": len(parsed.get("successes", [])),
        "failure_count": len(parsed.get("failures", [])),
        "missing_count": len(parsed.get("missing", [])),
        "pre_submit_estimate": prepared["estimate"],
        "cost_summary": cost_summary.get("phases", {}).get(PHASE),
    }
    manifest["updated_at"] = utc_now_iso()
    write_json(rd / "run_manifest.json", manifest)
    return {"status": "completed", "estimate": prepared["estimate"], "batch": latest, "parsed": parsed}


def submit_collect_run(*, run_id: str, profile: BatchProfile, cost_cap_usd: float, poll_interval_sec: float, max_wait_minutes: float, dry_run: bool = False) -> dict[str, Any]:
    prepared = prepare_submit_payload(run_id=run_id, profile=profile, cost_cap_usd=cost_cap_usd, dry_run=dry_run)
    if prepared["status"] != "ready_to_submit":
        return {"status": prepared["status"], "estimate": prepared["estimate"]}

    submit_result = submit_only(run_id=run_id, profile=profile, cost_cap_usd=cost_cap_usd, poll_interval_sec=poll_interval_sec)
    if submit_result["status"] != "submitted":
        return submit_result
    return collect_existing_batch(
        run_id=run_id,
        profile=profile,
        poll_interval_sec=poll_interval_sec,
        max_wait_minutes=max_wait_minutes,
        batch_id=safe_text(submit_result["batch"].get("id")),
    )


def assemble_full_corpus(*, run_id: str) -> list[dict[str, Any]]:
    rd = run_dir(run_id)
    cases = read_json(rd / "failure_slice_keys.json")["cases"]
    paper_data = base._prepare_common(rd)
    stage1_by_key = base._load_stage_records_by_key(rd, "stage1_review")
    stage2_by_key = base._load_stage_records_by_key(rd, "stage2_review")
    rows: list[dict[str, Any]] = []
    for case in cases:
        paper_id = case["paper_id"]
        key = case["candidate_key"]
        data = paper_data[paper_id]
        record = data["record_by_key"][key]
        cutoff = data["cutoff_result"]["decisions_by_key"][key]
        artifact = data["artifact_result"]["decisions_by_key"][key]
        resolution = data["resolution_by_key"][key]
        stage1 = stage1_by_key.get((paper_id, key))
        stage2 = stage2_by_key.get((paper_id, key))
        review_state = "reviewed"
        discard_reason = None
        final_stage = "stage2"
        if not cutoff["cutoff_pass"]:
            review_state = "cutoff_filtered"
            discard_reason = "cutoff_time_window"
            final_decision = "exclude"
            final_stage = "cutoff"
        elif not artifact["gate_pass"]:
            review_state = "artifact_filtered"
            discard_reason = f"artifact_gate:{artifact.get('gate_reason')}"
            final_decision = "exclude"
            final_stage = "artifact_gate"
        elif stage2:
            final_decision = safe_text(stage2["review_output"].get("final_stage_decision")) or "unknown"
        elif resolution["resolution_status"] not in {"exact", "normalized"}:
            review_state = "fulltext_unresolved"
            discard_reason = resolution["resolution_status"]
            final_decision = "unknown"
        elif not stage1:
            review_state = "stage1_not_available"
            final_decision = "unknown"
            final_stage = "stage1"
        else:
            review_state = "stage2_not_available"
            final_decision = "unknown"
        rows.append(
            {
                "paper_id": paper_id,
                "candidate_key": key,
                "candidate_title": safe_text(record.get("title") or record.get("query_title")),
                "slice_type": case["slice_type"],
                "allowed_for_unbiased_eval": case["allowed_for_unbiased_eval"],
                "review_state": review_state,
                "discard_reason": discard_reason,
                "final_stage": final_stage,
                "final_stage_decision": final_decision,
                "final_verdict": f"{final_decision} ({final_stage})",
                "stage1_output": stage1["review_output"] if stage1 else None,
                "stage2_output": stage2["review_output"] if stage2 else None,
                "fulltext_resolution_status": resolution["resolution_status"],
                "fulltext_source_path": resolution.get("resolved_path"),
                "bcpcs_v3_recall_repair_policy": True,
            }
        )
    rows.sort(key=lambda row: (row["paper_id"], row["candidate_key"]))
    write_json(rd / "assembled_results.json", rows)
    for paper_id in PAPER_IDS:
        paper_rows = [row for row in rows if row["paper_id"] == paper_id]
        write_json(paper_dir(run_id, paper_id) / "single_reviewer_batch_results.json", paper_rows)
    return rows


def _binary_metrics(rows: list[dict[str, Any]], *, unknown_as_negative: bool) -> dict[str, Any]:
    tp = fp = tn = fn = skipped = 0
    for row in rows:
        pred = row.get("prediction")
        if pred is None:
            if not unknown_as_negative:
                skipped += 1
                continue
            pred = 0
        gold = bool(row["gold_label"])
        if pred == 1 and gold:
            tp += 1
        elif pred == 1 and not gold:
            fp += 1
        elif pred == 0 and not gold:
            tn += 1
        elif pred == 0 and gold:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall_value = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall_value / (precision + recall_value) if precision + recall_value else 0.0
    return {
        "precision": precision,
        "recall": recall_value,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "evaluated_count": tp + fp + tn + fn,
        "skipped_unknown_or_runtime_count": skipped,
    }


def _coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    definite = sum(1 for row in rows if row["prediction"] is not None)
    runtime_failures = sum(1 for row in rows if row["review_state"] == "runtime_failed")
    return {
        "row_count": total,
        "definite_decision_count": definite,
        "definite_decision_rate": definite / total if total else 0.0,
        "unknown_or_routed_count": sum(1 for row in rows if row["prediction"] is None),
        "runtime_failure_count": runtime_failures,
        "review_state_counts": dict(Counter(row["review_state"] for row in rows)),
        "decision_counts": dict(Counter(row["final_stage_decision"] for row in rows)),
    }


def evaluate_full_corpus(*, run_id: str) -> dict[str, Any]:
    rd = run_dir(run_id)
    inventory = read_json(rd / "evaluation_inventory_private.json")
    rows = read_json(rd / "assembled_results.json")
    gold = load_gold_labels(PAPER_IDS)
    eval_rows: list[dict[str, Any]] = []
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (row["paper_id"], row["candidate_key"])
        pred = decision_to_prediction(safe_text(row["final_stage_decision"]))
        eval_row = {
            "paper_id": row["paper_id"],
            "candidate_key": row["candidate_key"],
            "gold_label": bool(gold[key]),
            "final_stage_decision": safe_text(row["final_stage_decision"]),
            "prediction": pred,
            "review_state": row["review_state"],
            "stage1_output": row.get("stage1_output"),
            "stage2_output": row.get("stage2_output"),
            "final_row": row,
        }
        eval_rows.append(eval_row)
        by_paper[row["paper_id"]].append(eval_row)

    summary = {
        "scope": inventory.get("scope"),
        "paper_ids": PAPER_IDS,
        "row_count": len(eval_rows),
        "overall": {
            "repo_compatible_f1": _binary_metrics(eval_rows, unknown_as_negative=True),
            "auto_decidable_f1": _binary_metrics(eval_rows, unknown_as_negative=False),
            "coverage": _coverage(eval_rows),
            "evidence_validity": evidence_validity(eval_rows),
        },
        "per_paper": {},
        "rows": [
            {key: value for key, value in row.items() if key not in {"stage1_output", "stage2_output", "final_row"}}
            for row in eval_rows
        ],
    }
    for paper_id in PAPER_IDS:
        paper_rows = by_paper[paper_id]
        summary["per_paper"][paper_id] = {
            "row_count": len(paper_rows),
            "repo_compatible_f1": _binary_metrics(paper_rows, unknown_as_negative=True),
            "auto_decidable_f1": _binary_metrics(paper_rows, unknown_as_negative=False),
            "coverage": _coverage(paper_rows),
            "evidence_validity": evidence_validity(paper_rows),
        }
    write_json(rd / "evaluation_summary_full_corpus.json", summary)
    return summary


def validate_run(*, run_id: str) -> dict[str, Any]:
    rd = run_dir(run_id)
    input_scans = []
    for input_path in sorted((rd / "batch_jobs").glob("*/*/input.jsonl")):
        rows = read_jsonl(input_path) if input_path.exists() else []
        hits = []
        for row in rows:
            terms = find_forbidden_prompt_terms(json.dumps(row.get("body", {}), ensure_ascii=False))
            if terms:
                hits.append({"custom_id": row.get("custom_id"), "terms": terms})
        input_scans.append({"path": repo_rel(input_path), "row_count": len(rows), "hit_count": len(hits), "hits": hits})
    schema_failures = []
    checked = 0
    for path in sorted((rd / "papers").glob("*/*_review.json")):
        payload = read_json(path)
        if not isinstance(payload, list):
            schema_failures.append(f"{repo_rel(path)}: expected list")
            continue
        for row in payload:
            checked += 1
            try:
                direct.StageReviewOutput.model_validate(row.get("review_output", row))
            except Exception as exc:  # noqa: BLE001
                schema_failures.append(f"{repo_rel(path)}: {type(exc).__name__}: {exc}")
    after = _git_status_short()
    before = _status_paths(read_json(rd / "run_manifest.json").get("pre_run_git_status_short", []))
    after_paths = _status_paths(after)
    new_or_changed = sorted(after_paths - before)
    outside_new = [path for path in new_or_changed if not path.startswith("research_bcpcs_2026-04-18/")]
    cost_ledger = read_jsonl(rd / "cost" / "cost_ledger.jsonl") if (rd / "cost" / "cost_ledger.jsonl").exists() else []
    payload = {
        "created_at": utc_now_iso(),
        "forbidden_prompt_hit_count": sum(item["hit_count"] for item in input_scans),
        "schema_failure_count": len(schema_failures),
        "schema_checked_stage_outputs": checked,
        "new_or_changed_paths_since_run_start": new_or_changed,
        "outside_research_new_or_changed_since_run_start": outside_new,
        "output_path_audit_ok": not outside_new,
        "cost_ledger_ok": all("cost_usd" in row and "custom_id" in row for row in cost_ledger),
        "cost_ledger_row_count": len(cost_ledger),
        "prompt_scans": input_scans,
        "schema_failures": schema_failures[:20],
    }
    write_json(rd / "validation_summary_full_corpus.json", payload)
    return payload


def write_report(*, run_id: str, summary: dict[str, Any], validation: dict[str, Any]) -> Path:
    rd = run_dir(run_id)
    manifest = read_json(rd / "run_manifest.json")
    cost_summary = read_json(rd / "cost" / "cost_summary.json") if (rd / "cost" / "cost_summary.json").exists() else {}
    report_path = REPORTS_ROOT / f"{run_id}.REPORT_zh.md"
    lines = [
        "# BCPCS Full-Corpus Batch Report",
        "",
        "這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。",
        "它不是 current single-reviewer two-stage direct-review baseline。",
        "",
        "## Run",
        "",
        f"- run_id: `{run_id}`",
        f"- model: `{manifest['model']}`",
        f"- workflow: `{manifest['workflow']}`",
        f"- reasoning_effort: `{manifest['reasoning_effort']}`",
        f"- papers: `{', '.join(PAPER_IDS)}`",
        "",
        "## Overall",
        "",
    ]
    overall_repo = summary["overall"]["repo_compatible_f1"]
    overall_auto = summary["overall"]["auto_decidable_f1"]
    overall_cov = summary["overall"]["coverage"]
    lines.extend(
        [
            f"- repo-compatible F1: `{overall_repo['f1']:.4f}` (`{overall_repo['tp']}/{overall_repo['fp']}/{overall_repo['tn']}/{overall_repo['fn']}`)",
            f"- auto-decidable F1: `{overall_auto['f1']:.4f}` (`{overall_auto['tp']}/{overall_auto['fp']}/{overall_auto['tn']}/{overall_auto['fn']}`)",
            f"- coverage: `{overall_cov['definite_decision_rate']:.2%}`",
            f"- decisions: `{json.dumps(overall_cov['decision_counts'], ensure_ascii=False, sort_keys=True)}`",
            f"- review states: `{json.dumps(overall_cov['review_state_counts'], ensure_ascii=False, sort_keys=True)}`",
            "",
            "## Per Paper",
            "",
            "| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for paper_id in PAPER_IDS:
        paper = summary["per_paper"][paper_id]
        repo_f1 = paper["repo_compatible_f1"]
        auto_f1 = paper["auto_decidable_f1"]
        lines.append(
            f"| `{paper_id}` | {paper['row_count']} | {repo_f1['f1']:.4f} | {auto_f1['f1']:.4f} | {repo_f1['precision']:.4f} | {repo_f1['recall']:.4f} | {repo_f1['tp']}/{repo_f1['fp']}/{repo_f1['tn']}/{repo_f1['fn']} | {paper['coverage']['definite_decision_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- forbidden prompt hits: `{validation['forbidden_prompt_hit_count']}`",
            f"- schema failures: `{validation['schema_failure_count']}`",
            f"- output path audit ok: `{str(validation['output_path_audit_ok']).lower()}`",
            f"- cost ledger ok: `{str(validation['cost_ledger_ok']).lower()}`",
            "",
            "## Cost",
            "",
            f"- total cost: `${float(cost_summary.get('total_cost_usd') or 0.0):.6f}`",
            f"- input tokens: `{cost_summary.get('input_tokens')}`",
            f"- output tokens: `{cost_summary.get('output_tokens')}`",
            "",
            "## Notes",
            "",
            "- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。",
            "- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_experiment(*, run_id: str, cost_cap_usd: float, poll_interval_sec: float, max_wait_minutes: float, dry_run: bool = False) -> dict[str, Any]:
    init_run(run_id=run_id, profile=PROFILE, cost_cap_usd=cost_cap_usd)
    result = submit_collect_run(
        run_id=run_id,
        profile=PROFILE,
        cost_cap_usd=cost_cap_usd,
        poll_interval_sec=poll_interval_sec,
        max_wait_minutes=max_wait_minutes,
        dry_run=dry_run,
    )
    if dry_run or result["status"] != "completed":
        return result
    assemble_full_corpus(run_id=run_id)
    summary = evaluate_full_corpus(run_id=run_id)
    validation = validate_run(run_id=run_id)
    report_path = write_report(run_id=run_id, summary=summary, validation=validation)
    manifest = read_json(run_dir(run_id) / "run_manifest.json")
    manifest["status"] = "completed"
    manifest["evaluation_summary_full_corpus_path"] = repo_rel(run_dir(run_id) / "evaluation_summary_full_corpus.json")
    manifest["validation_summary_full_corpus_path"] = repo_rel(run_dir(run_id) / "validation_summary_full_corpus.json")
    manifest["report_path"] = repo_rel(report_path)
    manifest["updated_at"] = utc_now_iso()
    write_json(run_dir(run_id) / "run_manifest.json", manifest)
    return {
        "status": "completed",
        "run_id": run_id,
        "report_path": repo_rel(report_path),
        "summary_path": repo_rel(run_dir(run_id) / "evaluation_summary_full_corpus.json"),
        "validation_path": repo_rel(run_dir(run_id) / "validation_summary_full_corpus.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the current BCPCS V3 architecture on all four SR corpora with Batch API.")
    parser.add_argument("--mode", choices=["run", "submit", "collect"], default="run")
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--batch-id")
    parser.add_argument("--cost-cap-usd", type=float, default=10.0)
    parser.add_argument("--poll-interval-sec", type=float, default=30.0)
    parser.add_argument("--max-wait-minutes", type=float, default=240.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.mode == "submit":
        init_run(run_id=args.run_id, profile=PROFILE, cost_cap_usd=args.cost_cap_usd)
        payload = submit_only(
            run_id=args.run_id,
            profile=PROFILE,
            cost_cap_usd=args.cost_cap_usd,
            poll_interval_sec=args.poll_interval_sec,
        )
    elif args.mode == "collect":
        payload = collect_existing_batch(
            run_id=args.run_id,
            profile=PROFILE,
            poll_interval_sec=args.poll_interval_sec,
            max_wait_minutes=args.max_wait_minutes,
            batch_id=args.batch_id,
        )
        if payload["status"] == "completed":
            assemble_full_corpus(run_id=args.run_id)
            summary = evaluate_full_corpus(run_id=args.run_id)
            validation = validate_run(run_id=args.run_id)
            report_path = write_report(run_id=args.run_id, summary=summary, validation=validation)
            manifest = read_json(run_dir(args.run_id) / "run_manifest.json")
            manifest["status"] = "completed"
            manifest["evaluation_summary_full_corpus_path"] = repo_rel(run_dir(args.run_id) / "evaluation_summary_full_corpus.json")
            manifest["validation_summary_full_corpus_path"] = repo_rel(run_dir(args.run_id) / "validation_summary_full_corpus.json")
            manifest["report_path"] = repo_rel(report_path)
            manifest["updated_at"] = utc_now_iso()
            write_json(run_dir(args.run_id) / "run_manifest.json", manifest)
            payload = {
                "status": "completed",
                "run_id": args.run_id,
                "report_path": repo_rel(report_path),
                "summary_path": repo_rel(run_dir(args.run_id) / "evaluation_summary_full_corpus.json"),
                "validation_path": repo_rel(run_dir(args.run_id) / "validation_summary_full_corpus.json"),
            }
    else:
        payload = run_experiment(
            run_id=args.run_id,
            cost_cap_usd=args.cost_cap_usd,
            poll_interval_sec=args.poll_interval_sec,
            max_wait_minutes=args.max_wait_minutes,
            dry_run=args.dry_run,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
