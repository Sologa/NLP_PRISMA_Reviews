#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

from experiment_lib import (  # noqa: E402
    append_jsonl,
    build_openai_provider,
    load_jsonl,
    parse_json_response_text,
    read_json,
    relative_path,
    render_template,
    safe_text,
    write_json,
)
from paper_faithful_lib import (  # noqa: E402
    choose_oracle_threshold_k,
    compute_adj_judge_score,
    compute_adj_rank_score,
    compute_mad_raw_score,
    compute_ranking_metrics,
    compute_soft_vote_score,
    safe_float,
    build_threshold_results,
)
from paper_faithful_models import (  # noqa: E402
    PRIMARY_REVIEWER_ROLES,
    DebateReviewOutput,
    JudgeReviewOutput,
    PrimaryReviewOutput,
    QuestionBundle,
)
from render_summary import build_summary_payload, render_comparison_table_zh, render_summary_zh  # noqa: E402
from experiment_workflows import load_candidates, load_cutoff_result  # noqa: E402
from openai_batch_runner import build_json_schema_response_format  # noqa: E402


CONFIG_PATH = BUNDLE_DIR / "config" / "experiment.json"
STAGES_PATH = BUNDLE_DIR / "config" / "stages.json"
SMOKE_KEYS_PATH = BUNDLE_DIR / "config" / "smoke_candidates.json"
TEMPLATE_DIR = BUNDLE_DIR / "templates"


@dataclass
class PromptAssets:
    question_generation_template: str
    primary_review_template: str
    peer_review_template: str
    adjudication_template: str


@dataclass
class RequestSpec:
    request_id: str
    phase_id: str
    reviewer_role: str
    candidate_key: str
    model: str
    reasoning_effort: str | None
    prompt: str
    response_model: type[BaseModel]
    text_format: dict[str, Any]
    validator: Callable[[BaseModel], None] | None
    record_builder: Callable[[dict[str, Any]], dict[str, Any]]
    request_context: dict[str, Any]


def _load_config() -> dict[str, Any]:
    return read_json(CONFIG_PATH)


def _load_stages() -> dict[str, Any]:
    return read_json(STAGES_PATH)


def _load_prompt_assets() -> PromptAssets:
    return PromptAssets(
        question_generation_template=(TEMPLATE_DIR / "00_generate_stage_questions_TEMPLATE.md").read_text(encoding="utf-8"),
        primary_review_template=(TEMPLATE_DIR / "01_primary_qa_review_TEMPLATE.md").read_text(encoding="utf-8"),
        peer_review_template=(TEMPLATE_DIR / "02_peer_review_round_TEMPLATE.md").read_text(encoding="utf-8"),
        adjudication_template=(TEMPLATE_DIR / "03_adjudication_review_TEMPLATE.md").read_text(encoding="utf-8"),
    )


def _run_dir(run_id: str) -> Path:
    return BUNDLE_DIR / "runs" / run_id


def _run_manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / "run_manifest.json"


def _request_log_path(run_id: str) -> Path:
    return _run_dir(run_id) / "request_log.jsonl"


def _response_log_path(run_id: str) -> Path:
    return _run_dir(run_id) / "response_log.jsonl"


def _failure_log_path(run_id: str) -> Path:
    return _run_dir(run_id) / "failure_log.jsonl"


def _cutoff_audit_path(run_id: str) -> Path:
    return _run_dir(run_id) / "cutoff_audit.json"


def _candidate_set_path(run_id: str) -> Path:
    return _run_dir(run_id) / "stage1_candidate_set.json"


def _stage1_question_bundle_run_path(run_id: str) -> Path:
    return _run_dir(run_id) / "stage1_question_bundle.json"


def _primary_reviews_path(run_id: str) -> Path:
    return _run_dir(run_id) / "primary_reviews.json"


def _round1_reviews_path(run_id: str) -> Path:
    return _run_dir(run_id) / "round1_reviews.json"


def _round2_reviews_path(run_id: str) -> Path:
    return _run_dir(run_id) / "round2_reviews.json"


def _adjudication_reviews_path(run_id: str) -> Path:
    return _run_dir(run_id) / "adjudication_reviews.json"


def _comparison_table_path(run_id: str) -> Path:
    return _run_dir(run_id) / "comparison_table_zh.md"


def _summary_path(run_id: str) -> Path:
    return _run_dir(run_id) / "SUMMARY_zh.md"


def _strategy_dir(run_id: str, family_id: str) -> Path:
    return _run_dir(run_id) / "strategies" / family_id


def _family_strategy_results_path(run_id: str, family_id: str) -> Path:
    return _strategy_dir(run_id, family_id) / "strategy_results.json"


def _family_ranking_metrics_path(run_id: str, family_id: str) -> Path:
    return _strategy_dir(run_id, family_id) / "ranking_metrics.json"


def _family_threshold_metrics_path(run_id: str, family_id: str, threshold_id: str) -> Path:
    return _strategy_dir(run_id, family_id) / f"threshold_metrics.{threshold_id}.json"


def _family_threshold_results_path(run_id: str, family_id: str, threshold_id: str) -> Path:
    return _strategy_dir(run_id, family_id) / f"threshold_results.{threshold_id}.json"


def _question_asset_path() -> Path:
    stages = _load_stages()
    return REPO_ROOT / stages["stages"]["stage1_abstract"]["question_asset_path"]


def _criteria_stage1_path() -> Path:
    stages = _load_stages()
    return REPO_ROOT / stages["stages"]["stage1_abstract"]["criteria_path"]


def _criteria_stage2_path() -> Path:
    stages = _load_stages()
    return REPO_ROOT / stages["stages"]["stage2_fulltext"]["criteria_path"]


def _metadata_path() -> Path:
    return REPO_ROOT / "refs" / _load_config()["paper_id"] / "metadata" / "title_abstracts_metadata.jsonl"


def _gold_path() -> Path:
    return REPO_ROOT / "refs" / _load_config()["paper_id"] / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _cutoff_path() -> Path:
    return REPO_ROOT / "cutoff_jsons" / f"{_load_config()['paper_id']}.json"


def _load_smoke_key_map() -> dict[str, set[str]]:
    payload = read_json(SMOKE_KEYS_PATH)
    return {paper_id: {safe_text(item) for item in values if safe_text(item)} for paper_id, values in payload.items()}


def _responses_text_format(*, response_model: type[BaseModel], schema_name: str) -> dict[str, Any]:
    response_format = build_json_schema_response_format(response_model, schema_name=schema_name)
    json_schema = response_format["json_schema"]
    return {
        "type": "json_schema",
        "name": json_schema["name"],
        "strict": True,
        "schema": json_schema["schema"],
    }


def _schema_name(base: str) -> str:
    paper_id = _load_config()["paper_id"].replace(".", "_")
    return f"{base}_{paper_id}"


def _new_run_id(prefix: str) -> str:
    return datetime.now().strftime(f"%Y%m%d_%H%M%S_{prefix}")


def _load_or_init_run_manifest(
    run_id: str,
    *,
    selection_mode: str,
    key_map: dict[str, set[str]] | None,
) -> dict[str, Any]:
    path = _run_manifest_path(run_id)
    if path.exists():
        payload = read_json(path)
        changed = False
        if "selection_mode" not in payload:
            payload["selection_mode"] = selection_mode
            changed = True
        if key_map is not None and "candidate_key_map" not in payload:
            payload["candidate_key_map"] = {paper_id: sorted(keys) for paper_id, keys in key_map.items()}
            changed = True
        if changed:
            write_json(path, payload)
        return payload
    config = _load_config()
    stages = _load_stages()
    payload = {
        "run_id": run_id,
        "bundle_dir": str(BUNDLE_DIR),
        "results_root": str(_run_dir(run_id)),
        "paper_id": config["paper_id"],
        "workflow_id": config["workflow_id"],
        "workflow_version": config["workflow_version"],
        "selection_mode": selection_mode,
        "candidate_key_map": ({paper_id: sorted(keys) for paper_id, keys in key_map.items()} if key_map else None),
        "enabled_stage_ids": stages["enabled_stage_ids"],
        "models": config["models"],
        "phase_status": {},
    }
    write_json(path, payload)
    return payload


def _mark_phase_completed(run_id: str, phase_id: str) -> None:
    manifest = read_json(_run_manifest_path(run_id))
    manifest.setdefault("phase_status", {})[phase_id] = "completed"
    write_json(_run_manifest_path(run_id), manifest)


def _selection_mode_for_resume(manifest: dict[str, Any], run_id: str) -> str:
    selection_mode = safe_text(manifest.get("selection_mode")).lower()
    if selection_mode in {"smoke", "full"}:
        return selection_mode
    return "smoke" if "smoke" in run_id.lower() else "full"


def _key_map_for_resume(manifest: dict[str, Any], run_id: str) -> dict[str, set[str]] | None:
    selection_mode = _selection_mode_for_resume(manifest, run_id)
    if selection_mode != "smoke":
        return None
    candidate_key_map = manifest.get("candidate_key_map")
    if isinstance(candidate_key_map, dict):
        return {
            safe_text(paper_id): {safe_text(key) for key in keys if safe_text(key)}
            for paper_id, keys in candidate_key_map.items()
            if safe_text(paper_id)
        }
    return _load_smoke_key_map()


def _completed_request_ids(run_id: str) -> set[str]:
    return {safe_text(row.get("request_id")) for row in load_jsonl(_response_log_path(run_id))}


def _terminal_failure_ids(run_id: str) -> set[str]:
    return {safe_text(row.get("request_id")) for row in load_jsonl(_failure_log_path(run_id))}


def _gold_map() -> dict[str, int]:
    out: dict[str, int] = {}
    for row in load_jsonl(_gold_path()):
        key = safe_text(row.get("key"))
        if not key:
            continue
        out[key] = 1 if bool(row.get("is_evidence_base")) else 0
    return out


def _review_title() -> str:
    criteria = read_json(_criteria_stage1_path())
    return safe_text(criteria.get("topic")) or _load_config()["paper_id"]


def _question_bundle_context() -> dict[str, Any]:
    return {
        "REVIEW_TITLE": _review_title(),
        "PAPER_ID": _load_config()["paper_id"],
        "STAGE_ID": "stage1_abstract",
        "STAGE_CRITERIA_JSON": read_json(_criteria_stage1_path()),
    }


def _validate_primary_output(payload: BaseModel, *, candidate_key: str, reviewer_role: str) -> None:
    parsed = PrimaryReviewOutput.model_validate(payload)
    if parsed.candidate_key != candidate_key:
        raise ValueError("candidate_key mismatch")
    if parsed.reviewer_role != reviewer_role:
        raise ValueError("reviewer_role mismatch")


def _validate_debate_output(payload: BaseModel, *, candidate_key: str, reviewer_role: str) -> None:
    parsed = DebateReviewOutput.model_validate(payload)
    if parsed.candidate_key != candidate_key:
        raise ValueError("candidate_key mismatch")
    if parsed.reviewer_role != reviewer_role:
        raise ValueError("reviewer_role mismatch")


def _validate_judge_output(payload: BaseModel, *, candidate_key: str) -> None:
    parsed = JudgeReviewOutput.model_validate(payload)
    if parsed.candidate_key != candidate_key:
        raise ValueError("candidate_key mismatch")


def _request_id(phase_id: str, reviewer_role: str, candidate_key: str) -> str:
    return f"{phase_id}::{reviewer_role}::{candidate_key}"


def _question_request_id() -> str:
    return "question_generation::stage1_abstract"


def _phase_records(run_id: str, phase_id: str) -> list[dict[str, Any]]:
    rows = [
        row["record"]
        for row in load_jsonl(_response_log_path(run_id))
        if safe_text(row.get("phase_id")) == phase_id and isinstance(row.get("record"), dict)
    ]
    return sorted(
        rows,
        key=lambda row: (
            safe_text(row.get("candidate_key")),
            safe_text(row.get("reviewer_role")),
        ),
    )


def _phase_records_by_candidate(run_id: str, phase_id: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in _phase_records(run_id, phase_id):
        key = safe_text(row.get("candidate_key"))
        out.setdefault(key, []).append(row)
    return out


def _phase_records_by_candidate_and_role(run_id: str, phase_id: str) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for row in _phase_records(run_id, phase_id):
        key = safe_text(row.get("candidate_key"))
        role = safe_text(row.get("reviewer_role"))
        out.setdefault(key, {})[role] = row
    return out


def _materialize_phase_outputs(run_id: str) -> None:
    primary_rows = _phase_records(run_id, "primary_review")
    write_json(_primary_reviews_path(run_id), primary_rows)
    write_json(_round1_reviews_path(run_id), primary_rows)
    write_json(_round2_reviews_path(run_id), _phase_records(run_id, "mad_review"))
    write_json(_adjudication_reviews_path(run_id), _phase_records(run_id, "adjudication_review"))


def _runtime_inputs(run_id: str, *, key_allowlist: set[str] | None) -> dict[str, Any]:
    records = load_candidates(_metadata_path(), key_allowlist=key_allowlist)
    cutoff_result = load_cutoff_result(records=records, cutoff_path=_cutoff_path())
    gold = _gold_map()
    write_json(_cutoff_audit_path(run_id), cutoff_result["audit_payload"])

    kept_rows: list[dict[str, Any]] = []
    cutoff_excluded_rows: list[dict[str, Any]] = []
    for record in records:
        key = safe_text(record.get("key"))
        row = {
            "key": key,
            "title": safe_text(record.get("title") or record.get("query_title")),
            "abstract": safe_text(record.get("abstract")),
            "published_date": safe_text(record.get("published_date")),
            "source": safe_text(record.get("source")),
            "gold_label": gold.get(key, 0),
        }
        decision = cutoff_result["decisions_by_key"][key]
        if bool(decision.get("cutoff_pass")):
            kept_rows.append(row)
        else:
            cutoff_excluded_rows.append(row)
    write_json(
        _candidate_set_path(run_id),
        {
            "paper_id": _load_config()["paper_id"],
            "candidate_total_before_cutoff": len(records),
            "candidate_total_after_cutoff": len(kept_rows),
            "cutoff_excluded_count": len(cutoff_excluded_rows),
            "kept_candidates": kept_rows,
            "cutoff_excluded_candidates": cutoff_excluded_rows,
        },
    )
    return {
        "records": records,
        "kept_rows": kept_rows,
        "cutoff_excluded_rows": cutoff_excluded_rows,
        "cutoff_result": cutoff_result,
    }


async def _run_request(
    *,
    provider: Any,
    spec: RequestSpec,
    run_id: str,
    max_attempts: int,
) -> None:
    for attempt in range(1, max_attempts + 1):
        append_jsonl(
            _request_log_path(run_id),
            {
                "request_id": spec.request_id,
                "phase_id": spec.phase_id,
                "reviewer_role": spec.reviewer_role,
                "candidate_key": spec.candidate_key,
                "attempt": attempt,
                "model": spec.model,
                "prompt_chars": len(spec.prompt),
            },
        )
        try:
            normalized_messages = provider._normalize_messages([{"role": "user", "content": spec.prompt}])  # noqa: SLF001

            async def _call() -> Any:
                kwargs: dict[str, Any] = {
                    "model": spec.model,
                    "input": normalized_messages,
                    "text": {"format": spec.text_format},
                    "metadata": {
                        "request_id": spec.request_id,
                        "phase_id": spec.phase_id,
                        "reviewer_role": spec.reviewer_role,
                    },
                }
                if spec.reasoning_effort:
                    kwargs["reasoning"] = {"effort": spec.reasoning_effort}
                return await provider._async_client.responses.create(**kwargs)  # noqa: SLF001

            result = await provider._execute_with_retry_async(  # noqa: SLF001
                _call,
                model=spec.model,
                mode="async",
                metadata={
                    "request_id": spec.request_id,
                    "phase_id": spec.phase_id,
                    "reviewer_role": spec.reviewer_role,
                },
            )
            parsed_payload = parse_json_response_text(result.content)
            parsed_model = spec.response_model.model_validate(parsed_payload)
            if spec.validator is not None:
                spec.validator(parsed_model)
            record = spec.record_builder(parsed_model.model_dump(mode="json"))
            append_jsonl(
                _response_log_path(run_id),
                {
                    "request_id": spec.request_id,
                    "phase_id": spec.phase_id,
                    "reviewer_role": spec.reviewer_role,
                    "candidate_key": spec.candidate_key,
                    "assistant_text": result.content,
                    "parsed": parsed_model.model_dump(mode="json"),
                    "record": record,
                    "usage": {
                        "provider": result.usage.provider,
                        "model": result.usage.model,
                        "mode": result.usage.mode,
                        "input_tokens": result.usage.input_tokens,
                        "output_tokens": result.usage.output_tokens,
                        "cost": result.usage.cost,
                    },
                    "context": spec.request_context,
                },
            )
            return
        except Exception as exc:  # noqa: BLE001
            if attempt >= max_attempts:
                append_jsonl(
                    _failure_log_path(run_id),
                    {
                        "request_id": spec.request_id,
                        "phase_id": spec.phase_id,
                        "reviewer_role": spec.reviewer_role,
                        "candidate_key": spec.candidate_key,
                        "status": "terminal_failure",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "attempts": attempt,
                        "context": spec.request_context,
                    },
                )


async def _execute_specs(run_id: str, specs: list[RequestSpec]) -> None:
    if not specs:
        return
    config = _load_config()
    completed = _completed_request_ids(run_id)
    failed = _terminal_failure_ids(run_id)
    pending = [spec for spec in specs if spec.request_id not in completed and spec.request_id not in failed]
    if not pending:
        return
    provider = build_openai_provider()
    semaphore = asyncio.Semaphore(int(config["concurrency"]))

    async def worker(spec: RequestSpec) -> None:
        async with semaphore:
            await _run_request(provider=provider, spec=spec, run_id=run_id, max_attempts=int(config["max_attempts_per_request"]))

    await asyncio.gather(*(worker(spec) for spec in pending))


async def _ensure_question_bundle(run_id: str, prompt_assets: PromptAssets) -> QuestionBundle:
    asset_path = _question_asset_path()
    if asset_path.exists():
        bundle = QuestionBundle.model_validate(read_json(asset_path))
        write_json(_stage1_question_bundle_run_path(run_id), bundle.model_dump(mode="json"))
        return bundle

    response_model = QuestionBundle
    prompt = render_template(prompt_assets.question_generation_template, _question_bundle_context())
    config = _load_config()
    model_cfg = config["models"]["judge_gpt5mini"]
    spec = RequestSpec(
        request_id=_question_request_id(),
        phase_id="question_generation",
        reviewer_role="judge_gpt5mini",
        candidate_key="stage1_abstract",
        model=model_cfg["model"],
        reasoning_effort=model_cfg["reasoning_effort"],
        prompt=prompt,
        response_model=response_model,
        text_format=_responses_text_format(response_model=response_model, schema_name=_schema_name("QuestionBundle")),
        validator=lambda payload: QuestionBundle.model_validate(payload),
        record_builder=lambda parsed: parsed,
        request_context={"stage_id": "stage1_abstract"},
    )
    await _execute_specs(run_id, [spec])
    rows = _phase_records(run_id, "question_generation")
    if not rows:
        raise RuntimeError("question generation did not produce a bundle")
    bundle = QuestionBundle.model_validate(rows[0])
    write_json(asset_path, bundle.model_dump(mode="json"))
    write_json(_stage1_question_bundle_run_path(run_id), bundle.model_dump(mode="json"))
    return bundle


def _question_bundle_json(bundle: QuestionBundle) -> str:
    return json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2)


def _build_primary_specs(run_id: str, bundle: QuestionBundle, runtime: dict[str, Any], prompt_assets: PromptAssets) -> list[RequestSpec]:
    config = _load_config()
    specs: list[RequestSpec] = []
    for candidate in runtime["kept_rows"]:
        for reviewer_role in PRIMARY_REVIEWER_ROLES:
            model_cfg = config["models"][reviewer_role]
            key = candidate["key"]
            title = candidate["title"]
            prompt = render_template(
                prompt_assets.primary_review_template,
                {
                    "REVIEW_TITLE": bundle.review_title,
                    "REVIEWER_ROLE": reviewer_role,
                    "CANDIDATE_KEY": key,
                    "TITLE": title,
                    "ABSTRACT": candidate["abstract"],
                    "QUESTION_BUNDLE_JSON": _question_bundle_json(bundle),
                },
            )
            specs.append(
                RequestSpec(
                    request_id=_request_id("primary_review", reviewer_role, key),
                    phase_id="primary_review",
                    reviewer_role=reviewer_role,
                    candidate_key=key,
                    model=model_cfg["model"],
                    reasoning_effort=model_cfg["reasoning_effort"],
                    prompt=prompt,
                    response_model=PrimaryReviewOutput,
                    text_format=_responses_text_format(response_model=PrimaryReviewOutput, schema_name=_schema_name(f"Primary_{reviewer_role}")),
                    validator=lambda payload, key=key, reviewer_role=reviewer_role: _validate_primary_output(
                        payload,
                        candidate_key=key,
                        reviewer_role=reviewer_role,
                    ),
                    record_builder=lambda parsed, candidate=candidate, reviewer_role=reviewer_role: {
                        **parsed,
                        "title": candidate["title"],
                        "abstract": candidate["abstract"],
                        "gold_label": candidate["gold_label"],
                        "stage_id": "stage1_abstract",
                    },
                    request_context={"phase": "primary_review", "candidate_title": title},
                )
            )
    return specs


def _build_mad_specs(run_id: str, bundle: QuestionBundle, runtime: dict[str, Any], prompt_assets: PromptAssets) -> list[RequestSpec]:
    config = _load_config()
    primary_map = _phase_records_by_candidate_and_role(run_id, "primary_review")
    specs: list[RequestSpec] = []
    for candidate in runtime["kept_rows"]:
        key = candidate["key"]
        if key not in primary_map or any(role not in primary_map[key] for role in PRIMARY_REVIEWER_ROLES):
            continue
        for reviewer_role in PRIMARY_REVIEWER_ROLES:
            peers = [primary_map[key][role] for role in PRIMARY_REVIEWER_ROLES if role != reviewer_role]
            model_cfg = config["models"][reviewer_role]
            prompt = render_template(
                prompt_assets.peer_review_template,
                {
                    "REVIEW_TITLE": bundle.review_title,
                    "REVIEWER_ROLE": reviewer_role,
                    "CANDIDATE_KEY": key,
                    "TITLE": candidate["title"],
                    "ABSTRACT": candidate["abstract"],
                    "QUESTION_BUNDLE_JSON": _question_bundle_json(bundle),
                    "SELF_PREVIOUS_REVIEW_JSON": json.dumps(primary_map[key][reviewer_role], ensure_ascii=False, indent=2),
                    "PEER_REVIEWS_JSON": json.dumps(peers, ensure_ascii=False, indent=2),
                },
            )
            specs.append(
                RequestSpec(
                    request_id=_request_id("mad_review", reviewer_role, key),
                    phase_id="mad_review",
                    reviewer_role=reviewer_role,
                    candidate_key=key,
                    model=model_cfg["model"],
                    reasoning_effort=model_cfg["reasoning_effort"],
                    prompt=prompt,
                    response_model=DebateReviewOutput,
                    text_format=_responses_text_format(response_model=DebateReviewOutput, schema_name=_schema_name(f"Mad_{reviewer_role}")),
                    validator=lambda payload, key=key, reviewer_role=reviewer_role: _validate_debate_output(
                        payload,
                        candidate_key=key,
                        reviewer_role=reviewer_role,
                    ),
                    record_builder=lambda parsed, candidate=candidate, reviewer_role=reviewer_role: {
                        **parsed,
                        "title": candidate["title"],
                        "abstract": candidate["abstract"],
                        "gold_label": candidate["gold_label"],
                        "stage_id": "stage1_abstract",
                    },
                    request_context={"phase": "mad_review", "candidate_title": candidate["title"]},
                )
            )
    return specs


def _build_adjudication_specs(run_id: str, bundle: QuestionBundle, runtime: dict[str, Any], prompt_assets: PromptAssets) -> list[RequestSpec]:
    primary_map = _phase_records_by_candidate_and_role(run_id, "primary_review")
    config = _load_config()
    model_cfg = config["models"]["judge_gpt5mini"]
    specs: list[RequestSpec] = []
    for candidate in runtime["kept_rows"]:
        key = candidate["key"]
        if key not in primary_map or any(role not in primary_map[key] for role in PRIMARY_REVIEWER_ROLES):
            continue
        prompt = render_template(
            prompt_assets.adjudication_template,
            {
                "REVIEW_TITLE": bundle.review_title,
                "CANDIDATE_KEY": key,
                "TITLE": candidate["title"],
                "ABSTRACT": candidate["abstract"],
                "QUESTION_BUNDLE_JSON": _question_bundle_json(bundle),
                "PRIMARY_REVIEWS_JSON": json.dumps(primary_map[key], ensure_ascii=False, indent=2),
            },
        )
        specs.append(
            RequestSpec(
                request_id=_request_id("adjudication_review", "judge_gpt5mini", key),
                phase_id="adjudication_review",
                reviewer_role="judge_gpt5mini",
                candidate_key=key,
                model=model_cfg["model"],
                reasoning_effort=model_cfg["reasoning_effort"],
                prompt=prompt,
                response_model=JudgeReviewOutput,
                text_format=_responses_text_format(response_model=JudgeReviewOutput, schema_name=_schema_name("Judge")),
                validator=lambda payload, key=key: _validate_judge_output(payload, candidate_key=key),
                record_builder=lambda parsed, candidate=candidate: {
                    **parsed,
                    "title": candidate["title"],
                    "abstract": candidate["abstract"],
                    "gold_label": candidate["gold_label"],
                    "stage_id": "stage1_abstract",
                },
                request_context={"phase": "adjudication_review", "candidate_title": candidate["title"]},
            )
        )
    return specs


def _require_complete_candidate_phase_map(
    *,
    candidate_keys: list[str],
    phase_map: dict[str, dict[str, dict[str, Any]]] | dict[str, dict[str, Any]],
    phase_label: str,
) -> None:
    missing: list[str] = []
    for key in candidate_keys:
        if key not in phase_map:
            missing.append(key)
    if missing:
        raise RuntimeError(f"incomplete {phase_label}: missing candidates={missing[:10]}")


def _strategy_payloads(run_id: str, runtime: dict[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    primary_map = _phase_records_by_candidate_and_role(run_id, "primary_review")
    mad_map = _phase_records_by_candidate_and_role(run_id, "mad_review")
    judge_map = {row["candidate_key"]: row for row in _phase_records(run_id, "adjudication_review")}
    candidate_keys = [row["key"] for row in runtime["kept_rows"]]
    _require_complete_candidate_phase_map(candidate_keys=candidate_keys, phase_map=primary_map, phase_label="primary_review")
    _require_complete_candidate_phase_map(candidate_keys=candidate_keys, phase_map=mad_map, phase_label="mad_review")
    _require_complete_candidate_phase_map(candidate_keys=candidate_keys, phase_map=judge_map, phase_label="adjudication_review")

    strategies: dict[str, list[dict[str, Any]]] = {
        "soft_vote": [],
        "mad_raw": [],
        "mad_soft_vote": [],
        "adj_judge": [],
        "adj_rank": [],
    }
    for candidate in runtime["kept_rows"]:
        key = candidate["key"]
        primary_rows = [primary_map[key][role] for role in PRIMARY_REVIEWER_ROLES]
        mad_rows = [mad_map[key][role] for role in PRIMARY_REVIEWER_ROLES]
        judge_row = judge_map[key]

        strategies["soft_vote"].append(
            {
                "key": key,
                "title": candidate["title"],
                "gold_label": candidate["gold_label"],
                "score": compute_soft_vote_score(primary_rows),
                "details": {"source_phase": "primary_review"},
            }
        )
        strategies["mad_raw"].append(
            {
                "key": key,
                "title": candidate["title"],
                "gold_label": candidate["gold_label"],
                "score": compute_mad_raw_score(mad_rows),
                "details": {"source_phase": "mad_review"},
            }
        )
        strategies["mad_soft_vote"].append(
            {
                "key": key,
                "title": candidate["title"],
                "gold_label": candidate["gold_label"],
                "score": compute_soft_vote_score(mad_rows),
                "details": {"source_phase": "mad_review"},
            }
        )
        strategies["adj_judge"].append(
            {
                "key": key,
                "title": candidate["title"],
                "gold_label": candidate["gold_label"],
                "score": compute_adj_judge_score(judge_row),
                "details": {"source_phase": "adjudication_review"},
            }
        )
        strategies["adj_rank"].append(
            {
                "key": key,
                "title": candidate["title"],
                "gold_label": candidate["gold_label"],
                "score": compute_adj_rank_score(primary_rows=primary_map[key], judge_row=judge_row),
                "details": {"source_phase": "primary_review+adjudication_review"},
            }
        )
    return {
        "soft_vote": {"soft_vote": strategies["soft_vote"]},
        "mad": {"mad_raw": strategies["mad_raw"], "mad_soft_vote": strategies["mad_soft_vote"]},
        "adjudication": {"adj_judge": strategies["adj_judge"], "adj_rank": strategies["adj_rank"]},
    }


def _write_strategy_family_outputs(run_id: str, runtime: dict[str, Any]) -> None:
    current_authority = read_json(REPO_ROOT / _load_config()["current_authority_stage1_path"])["metrics"]
    single_baseline = read_json(REPO_ROOT / _load_config()["single_reviewer_stage1_baseline_path"])["metrics"]
    current_k = int(current_authority["tp"]) + int(current_authority["fp"])
    single_k = int(single_baseline["tp"]) + int(single_baseline["fp"])

    family_payloads = _strategy_payloads(run_id, runtime)
    for family_id, family_strategies in family_payloads.items():
        family_dir = _strategy_dir(run_id, family_id)
        family_dir.mkdir(parents=True, exist_ok=True)
        primary_reviews = _phase_records(run_id, "primary_review")
        write_json(family_dir / "primary_reviews.json", primary_reviews)
        if family_id == "mad":
            write_json(family_dir / "round1_reviews.json", primary_reviews)
            write_json(family_dir / "round2_reviews.json", _phase_records(run_id, "mad_review"))
        if family_id == "adjudication":
            write_json(family_dir / "adjudication_reviews.json", _phase_records(run_id, "adjudication_review"))

        ranked_strategies: dict[str, list[dict[str, Any]]] = {}
        ranking_metrics_payload: dict[str, Any] = {"family_id": family_id, "strategies": {}}
        threshold_payloads: dict[str, dict[str, Any]] = {
            "current_authority_k": {"family_id": family_id, "threshold_id": "current_authority_k", "strategies": {}},
            "single_reviewer_k": {"family_id": family_id, "threshold_id": "single_reviewer_k", "strategies": {}},
            "oracle_best_f1": {"family_id": family_id, "threshold_id": "oracle_best_f1", "strategies": {}},
        }
        threshold_results_payloads: dict[str, dict[str, Any]] = {
            "current_authority_k": {"family_id": family_id, "threshold_id": "current_authority_k", "strategies": {}},
            "single_reviewer_k": {"family_id": family_id, "threshold_id": "single_reviewer_k", "strategies": {}},
            "oracle_best_f1": {"family_id": family_id, "threshold_id": "oracle_best_f1", "strategies": {}},
        }

        for strategy_id, rows in family_strategies.items():
            ranked_rows = sorted(rows, key=lambda row: (-safe_float(row.get("score")), safe_text(row.get("key"))))
            ranked_strategies[strategy_id] = ranked_rows
            ranking_metrics_payload["strategies"][strategy_id] = compute_ranking_metrics(ranked_rows)

            current_payload = build_threshold_results(
                ranked_rows=ranked_rows,
                cutoff_excluded_rows=runtime["cutoff_excluded_rows"],
                k=min(current_k, len(ranked_rows)),
                strategy_id=strategy_id,
                threshold_id="current_authority_k",
            )
            single_payload = build_threshold_results(
                ranked_rows=ranked_rows,
                cutoff_excluded_rows=runtime["cutoff_excluded_rows"],
                k=min(single_k, len(ranked_rows)),
                strategy_id=strategy_id,
                threshold_id="single_reviewer_k",
            )
            oracle = choose_oracle_threshold_k(ranked_rows)
            oracle_payload = build_threshold_results(
                ranked_rows=ranked_rows,
                cutoff_excluded_rows=runtime["cutoff_excluded_rows"],
                k=min(int(oracle["k"]), len(ranked_rows)),
                strategy_id=strategy_id,
                threshold_id="oracle_best_f1",
            )
            threshold_payloads["current_authority_k"]["strategies"][strategy_id] = current_payload["metrics"]
            threshold_payloads["single_reviewer_k"]["strategies"][strategy_id] = single_payload["metrics"]
            threshold_payloads["oracle_best_f1"]["strategies"][strategy_id] = {
                **oracle_payload["metrics"],
                "k": oracle_payload["k"],
            }
            threshold_results_payloads["current_authority_k"]["strategies"][strategy_id] = current_payload
            threshold_results_payloads["single_reviewer_k"]["strategies"][strategy_id] = single_payload
            threshold_results_payloads["oracle_best_f1"]["strategies"][strategy_id] = oracle_payload

        write_json(_family_strategy_results_path(run_id, family_id), {"family_id": family_id, "strategies": ranked_strategies})
        write_json(_family_ranking_metrics_path(run_id, family_id), ranking_metrics_payload)
        for threshold_id, payload in threshold_payloads.items():
            write_json(_family_threshold_metrics_path(run_id, family_id, threshold_id), payload)
        for threshold_id, payload in threshold_results_payloads.items():
            write_json(_family_threshold_results_path(run_id, family_id, threshold_id), payload)


def _write_summary(run_id: str) -> None:
    summary = build_summary_payload(run_dir=_run_dir(run_id))
    write_json(_run_dir(run_id) / "summary_payload.json", summary)
    _comparison_table_path(run_id).write_text(render_comparison_table_zh(summary), encoding="utf-8")
    _summary_path(run_id).write_text(render_summary_zh(summary), encoding="utf-8")


def _assert_no_terminal_failures(run_id: str) -> None:
    failures = load_jsonl(_failure_log_path(run_id))
    if failures:
        raise RuntimeError(f"terminal failures remain: {len(failures)}")


async def _run_pipeline(run_id: str, *, selection_mode: str, key_map: dict[str, set[str]] | None) -> None:
    _load_or_init_run_manifest(run_id, selection_mode=selection_mode, key_map=key_map)
    prompt_assets = _load_prompt_assets()
    bundle = await _ensure_question_bundle(run_id, prompt_assets)
    key_allowlist = None if selection_mode == "full" else set((key_map or {}).get(_load_config()["paper_id"], set()))
    runtime = _runtime_inputs(run_id, key_allowlist=key_allowlist)

    primary_specs = _build_primary_specs(run_id, bundle, runtime, prompt_assets)
    await _execute_specs(run_id, primary_specs)
    _mark_phase_completed(run_id, "primary_review")

    mad_specs = _build_mad_specs(run_id, bundle, runtime, prompt_assets)
    await _execute_specs(run_id, mad_specs)
    _mark_phase_completed(run_id, "mad_review")

    adjudication_specs = _build_adjudication_specs(run_id, bundle, runtime, prompt_assets)
    await _execute_specs(run_id, adjudication_specs)
    _mark_phase_completed(run_id, "adjudication_review")

    _materialize_phase_outputs(run_id)
    _write_strategy_family_outputs(run_id, runtime)
    _write_summary(run_id)
    _mark_phase_completed(run_id, "summary")
    _assert_no_terminal_failures(run_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the paper-faithful A isolated async experiment for 2409.")
    parser.add_argument("--mode", required=True, choices=("validate", "smoke", "run-all", "resume"))
    parser.add_argument("--run-id")
    parser.add_argument("--check-client", action="store_true")
    args = parser.parse_args()

    if args.mode == "validate":
        from validate_bundle import main as validate_main  # noqa: WPS433,E402

        cli_args = ["validate_bundle.py"]
        if args.check_client:
            cli_args.append("--check-client")
        old_argv = sys.argv[:]
        try:
            sys.argv = cli_args
            return int(validate_main())
        finally:
            sys.argv = old_argv

    if args.mode == "smoke":
        run_id = args.run_id or _new_run_id("smoke_akinseloyin2026_paper_faithful_2409")
        key_map = _load_smoke_key_map()
        asyncio.run(_run_pipeline(run_id, selection_mode="smoke", key_map=key_map))
        print(json.dumps({"run_dir": str(_run_dir(run_id))}, ensure_ascii=False))
        return 0

    if args.mode == "run-all":
        run_id = args.run_id or _new_run_id("full_akinseloyin2026_paper_faithful_2409")
        asyncio.run(_run_pipeline(run_id, selection_mode="full", key_map=None))
        print(json.dumps({"run_dir": str(_run_dir(run_id))}, ensure_ascii=False))
        return 0

    manifest = read_json(_run_manifest_path(args.run_id))
    key_map = _key_map_for_resume(manifest, args.run_id)
    selection_mode = _selection_mode_for_resume(manifest, args.run_id)
    asyncio.run(_run_pipeline(args.run_id, selection_mode=selection_mode, key_map=key_map))
    print(json.dumps({"run_dir": str(_run_dir(args.run_id))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
