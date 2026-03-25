#!/usr/bin/env python3
"""執行單審查者官方批次基線。"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

import render_prompt  # noqa: E402
import cutoff_time_filter  # noqa: E402
from openai_batch_runner import BatchRequestSpec, OpenAIBatchRunner, build_json_schema_response_format  # noqa: E402


CONFIG_PATH = BUNDLE_DIR / "config" / "experiment_config.json"
MANIFEST_PATH = BUNDLE_DIR / "manifest.json"
RESULTS_ROOT = REPO_ROOT / "screening" / "results" / "single_reviewer_official_batch_gpt5mini_all4_2026-03-22"
RESULTS_MANIFEST_PATH = REPO_ROOT / "screening" / "results" / "results_manifest.json"
WORKFLOW_ARM = "single-reviewer-official-batch"
WORKFLOW_STAGE = "stage2-single-reviewer-batch"
FULLTEXT_TRUNCATION_MARKER = "\n\n...[TRUNCATED MIDDLE]...\n\n"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRecordProvenance(_StrictModel):
    record_key: str
    record_title: str | None = None
    source: str | None = None
    source_id: str | None = None
    metadata_path: str
    criteria_stage2_path: str
    runtime_prompts_path: str
    fulltext_candidate_path: str
    fulltext_available: bool


class SingleReviewerOutput(_StrictModel):
    paper_id: str
    candidate_key: str
    candidate_title: str
    workflow_arm: Literal["single-reviewer-official-batch"]
    stage: Literal["stage2-single-reviewer-batch"]
    source_record_provenance: SourceRecordProvenance
    stage_score: int = Field(ge=1, le=5)
    decision_recommendation: Literal["include", "exclude", "maybe"]
    satisfied_inclusion_points: list[str] = Field(default_factory=list)
    triggered_exclusion_points: list[str] = Field(default_factory=list)
    uncertain_points: list[str] = Field(default_factory=list)
    evidence_highlights: list[str] = Field(default_factory=list)
    decision_rationale: str


class PromptAssets:
    def __init__(self) -> None:
        self.template = (BUNDLE_DIR / "templates" / "01_single_reviewer_TEMPLATE.md").read_text(encoding="utf-8")
        self.schema_hint = (BUNDLE_DIR / "samples" / "sample_reviewer_output.json").read_text(encoding="utf-8")
        self.retry_policy = (BUNDLE_DIR / "templates" / "validation_retry_repair_policy.md").read_text(encoding="utf-8")


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


def _load_config() -> dict[str, Any]:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    required = {
        "model",
        "papers",
        "endpoint",
        "completion_window",
        "batch_poll_interval_sec",
        "batch_max_wait_minutes",
        "fulltext_inline_head_chars",
        "fulltext_inline_tail_chars",
    }
    missing = sorted(required.difference(payload.keys()))
    if missing:
        raise SystemExit("config 缺少必要欄位: " + ", ".join(missing))
    return payload


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{index}: {exc}") from exc
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _relative(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.relative_to(REPO_ROOT))


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def _decision_from_score(score: int) -> str:
    if score >= 4:
        return "include"
    if score <= 2:
        return "exclude"
    return "maybe"


def _extract_verdict_label(verdict: str | None) -> str:
    match = re.match(r"^\s*([a-z]+)", _safe_text(verdict).lower())
    return match.group(1) if match else "unknown"


def _paper_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _paper_gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _paper_fulltext_root(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "mds"


def _paper_stage2_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage2" / f"{paper_id}.json"


def _paper_cutoff_path(paper_id: str) -> Path:
    return cutoff_time_filter.cutoff_json_path(REPO_ROOT, paper_id)


def _runtime_prompts_path() -> Path:
    return REPO_ROOT / "scripts" / "screening" / "runtime_prompts" / "runtime_prompts.json"


def _run_dir(run_id: str) -> Path:
    return RESULTS_ROOT / "runs" / run_id


def _batch_artifact_dir(run_id: str, model: str) -> Path:
    return _run_dir(run_id) / "batch_jobs" / "review" / model


def _paper_result_dir(run_id: str, paper_id: str) -> Path:
    return _run_dir(run_id) / "papers" / paper_id


def _paper_resolution_audit_path(run_id: str, paper_id: str) -> Path:
    return _paper_result_dir(run_id, paper_id) / "fulltext_resolution_audit.json"


def _paper_cutoff_audit_path(run_id: str, paper_id: str) -> Path:
    return _paper_result_dir(run_id, paper_id) / "cutoff_audit.json"


def _paper_results_path(run_id: str, paper_id: str) -> Path:
    return _paper_result_dir(run_id, paper_id) / "single_reviewer_batch_results.json"


def _paper_metrics_path(run_id: str, paper_id: str) -> Path:
    return _paper_result_dir(run_id, paper_id) / "single_reviewer_batch_f1.json"


def _run_manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / "run_manifest.json"


def _report_path(run_id: str) -> Path:
    return _run_dir(run_id) / "REPORT_zh.md"


def _normalize_key(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


def _apply_head_tail_limit(text: str, *, head_chars: int, tail_chars: int) -> str:
    threshold = head_chars + tail_chars
    if len(text) <= threshold:
        return text
    return text[:head_chars] + FULLTEXT_TRUNCATION_MARKER + text[-tail_chars:]


def _cut_before_references(text: str, *, head_chars: int, tail_chars: int) -> tuple[str, dict[str, Any]]:
    lines = text.splitlines()
    marker = None
    line_no = None
    for index, line in enumerate(lines, start=1):
        normalized = line.strip().lower().rstrip(":")
        if normalized in {"references", "bibliography"}:
            marker = line.strip()
            line_no = index
            text = "\n".join(lines[: index - 1])
            break
    total_chars = len("\n".join(lines))
    trimmed_text = _apply_head_tail_limit(text, head_chars=head_chars, tail_chars=tail_chars)
    return trimmed_text, {
        "fulltext_chars_total": total_chars,
        "fulltext_chars_used": len(trimmed_text),
        "reference_cut_applied": marker is not None,
        "reference_cut_method": "heading" if marker is not None else "none",
        "reference_cut_marker": marker,
        "reference_cut_line_no": line_no,
    }


def _load_candidates_with_cutoff(paper_id: str, *, max_records: int | None = None) -> dict[str, Any]:
    cutoff_path = _paper_cutoff_path(paper_id)
    cutoff_payload, time_policy = cutoff_time_filter.load_time_policy(cutoff_path)
    cutoff_payload = dict(cutoff_payload)
    cutoff_payload["_cutoff_json_path"] = str(cutoff_path.relative_to(REPO_ROOT))
    rows = _read_jsonl(_paper_metadata_path(paper_id))
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in rows:
        key = _safe_text(row.get("key"))
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(row)
    applied = cutoff_time_filter.apply_cutoff(deduped, payload=cutoff_payload, policy=time_policy)
    selected_records = list(applied["kept_records"])
    if max_records is not None:
        selected_records = selected_records[:max_records]
    audit_payload = dict(applied["audit_payload"])
    audit_payload["max_records_applied"] = max_records
    audit_payload["candidate_total_after_cutoff_selected_for_run"] = len(selected_records)
    return {
        "selected_records": selected_records,
        "excluded_records": list(applied["excluded_records"]),
        "decisions_by_key": dict(applied["decisions_by_key"]),
        "audit_payload": audit_payload,
    }


class FulltextIndex:
    def __init__(self, paper_id: str) -> None:
        self.paper_id = paper_id
        self.root = _paper_fulltext_root(paper_id)
        self.exact_map: dict[str, Path] = {}
        self.normalized_map: dict[str, list[Path]] = defaultdict(list)
        self.ignored_appledouble_count = 0
        for path in sorted(self.root.glob("*.md")):
            if path.name.startswith("._"):
                self.ignored_appledouble_count += 1
                continue
            self.exact_map[path.stem] = path
            self.normalized_map[_normalize_key(path.stem)].append(path)
        self.normalized_collision_count = sum(1 for value in self.normalized_map.values() if len(value) > 1)

    def resolve(self, key: str) -> dict[str, Any]:
        exact_candidate = self.root / f"{key}.md"
        normalized_key = _normalize_key(key)
        if key in self.exact_map:
            path = self.exact_map[key]
            return {
                "resolution_status": "exact",
                "normalized_key": normalized_key,
                "exact_candidate_path": _relative(exact_candidate),
                "resolved_path": _relative(path),
                "match_candidates": [_relative(path)],
            }
        matches = self.normalized_map.get(normalized_key, [])
        if len(matches) == 1:
            return {
                "resolution_status": "normalized",
                "normalized_key": normalized_key,
                "exact_candidate_path": _relative(exact_candidate),
                "resolved_path": _relative(matches[0]),
                "match_candidates": [_relative(matches[0])],
            }
        if len(matches) > 1:
            return {
                "resolution_status": "retrieval_ambiguous",
                "normalized_key": normalized_key,
                "exact_candidate_path": _relative(exact_candidate),
                "resolved_path": None,
                "match_candidates": [_relative(path) for path in matches],
            }
        return {
            "resolution_status": "retrieval_failed",
            "normalized_key": normalized_key,
            "exact_candidate_path": _relative(exact_candidate),
            "resolved_path": None,
            "match_candidates": [],
        }


def _build_resolution_audit(paper_id: str, records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    index = FulltextIndex(paper_id)
    by_key: dict[str, dict[str, Any]] = {}
    counter: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for record in records:
        key = _safe_text(record.get("key"))
        resolution = index.resolve(key)
        by_key[key] = resolution
        counter[resolution["resolution_status"]] += 1
        rows.append(
            {
                "key": key,
                "title": _safe_text(record.get("title") or record.get("query_title")),
                **resolution,
            }
        )
    return by_key, {
        "paper_id": paper_id,
        "workflow_arm": WORKFLOW_ARM,
        "candidate_total": len(records),
        "exact_match_count": counter["exact"],
        "normalized_match_count": counter["normalized"],
        "retrieval_failed_count": counter["retrieval_failed"],
        "retrieval_ambiguous_count": counter["retrieval_ambiguous"],
        "normalized_collision_count": index.normalized_collision_count,
        "appledouble_ignored_count": index.ignored_appledouble_count,
        "resolutions": rows,
    }


def _fulltext_payload_from_resolution(
    resolution: dict[str, Any],
    *,
    head_chars: int,
    tail_chars: int,
) -> tuple[str, dict[str, Any]]:
    status = resolution["resolution_status"]
    if status not in {"exact", "normalized"}:
        return "", {
            "fulltext_source_path": resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
            "fulltext_chars_total": 0,
            "fulltext_chars_used": 0,
            "reference_cut_applied": False,
            "reference_cut_method": "none",
            "reference_cut_marker": None,
            "reference_cut_line_no": None,
        }
    path = REPO_ROOT / str(resolution["resolved_path"])
    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    trimmed_text, meta = _cut_before_references(raw_text, head_chars=head_chars, tail_chars=tail_chars)
    meta["fulltext_source_path"] = str(path)
    return trimmed_text, meta


def _build_source_record_provenance(record: dict[str, Any], paper_id: str, resolution: dict[str, Any]) -> SourceRecordProvenance:
    return SourceRecordProvenance(
        record_key=_safe_text(record.get("key")),
        record_title=_safe_text(record.get("title") or record.get("query_title")),
        source=_safe_text(record.get("source")) or None,
        source_id=_safe_text(record.get("source_id")) or None,
        metadata_path=str(_paper_metadata_path(paper_id).relative_to(REPO_ROOT)),
        criteria_stage2_path=str(_paper_stage2_criteria_path(paper_id).relative_to(REPO_ROOT)),
        runtime_prompts_path=str(_runtime_prompts_path().relative_to(REPO_ROOT)),
        fulltext_candidate_path=str(resolution.get("exact_candidate_path") or ""),
        fulltext_available=resolution["resolution_status"] in {"exact", "normalized"},
    )


def _base_context(
    *,
    prompt_assets: PromptAssets,
    paper_id: str,
    record: dict[str, Any],
    resolution: dict[str, Any],
    provenance: SourceRecordProvenance,
    stage2_criteria_text: str,
    fulltext_text: str,
) -> dict[str, Any]:
    title = _safe_text(record.get("title") or record.get("query_title"))
    metadata_payload = {
        "key": _safe_text(record.get("key")),
        "query_title": _safe_text(record.get("query_title")),
        "title": title,
        "abstract": _safe_text(record.get("abstract")),
        "source": _safe_text(record.get("source")),
        "source_id": _safe_text(record.get("source_id")),
        "match_status": _safe_text(record.get("match_status")),
        "missing_reason": _safe_text(record.get("missing_reason")),
        "published_date": _safe_text(record.get("published_date")),
    }
    return {
        "PAPER_ID": paper_id,
        "CANDIDATE_KEY": _safe_text(record.get("key")),
        "CANDIDATE_TITLE": title,
        "PRODUCTION_RUNTIME_PROMPTS_PATH": str(_runtime_prompts_path().relative_to(REPO_ROOT)),
        "STAGE2_CRITERIA_JSON_PATH": str(_paper_stage2_criteria_path(paper_id).relative_to(REPO_ROOT)),
        "STAGE2_CRITERIA_JSON_CONTENT": stage2_criteria_text,
        "TITLE": title,
        "ABSTRACT": _safe_text(record.get("abstract")),
        "FULLTEXT_TEXT": fulltext_text,
        "METADATA_JSON": _json_text(metadata_payload),
        "SOURCE_RECORD_PROVENANCE_JSON": _json_text(provenance.model_dump(mode="json")),
        "FULLTEXT_RESOLUTION_JSON": _json_text(resolution),
        "REVIEW_OUTPUT_JSON_SCHEMA_HINT": prompt_assets.schema_hint,
    }


def _with_authoritative_output(
    parsed: SingleReviewerOutput,
    provenance: SourceRecordProvenance,
    *,
    paper_id: str,
    candidate_key: str,
    candidate_title: str,
) -> SingleReviewerOutput:
    return parsed.model_copy(
        update={
            "paper_id": paper_id,
            "candidate_key": candidate_key,
            "candidate_title": candidate_title,
            "workflow_arm": WORKFLOW_ARM,
            "stage": WORKFLOW_STAGE,
            "source_record_provenance": provenance,
        }
    )


def _collect_strings(payload: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(payload, str):
        strings.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            strings.extend(_collect_strings(value))
    elif isinstance(payload, list):
        for value in payload:
            strings.extend(_collect_strings(value))
    return strings


def _validate_score_alignment(score: int, recommendation: str) -> None:
    expected = _decision_from_score(score)
    if recommendation != expected:
        raise ValueError(f"decision_recommendation 必須與 stage_score 對齊 ({score} -> {expected})")


def _validate_output(parsed: SingleReviewerOutput) -> None:
    _validate_score_alignment(parsed.stage_score, parsed.decision_recommendation)
    for fragment in _collect_strings(parsed.model_dump(mode="json")):
        if "__" in fragment and "{{" in fragment:
            raise ValueError("輸出包含未替換 placeholder")


def _build_skipped_row(
    *,
    paper_id: str,
    record: dict[str, Any],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    status = resolution["resolution_status"]
    return {
        "key": _safe_text(record.get("key")),
        "title": _safe_text(record.get("title") or record.get("query_title")),
        "workflow_arm": WORKFLOW_ARM,
        "stage": WORKFLOW_STAGE,
        "fulltext_review_mode": "batch",
        "fulltext_source_path": resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
        "fulltext_chars_total": 0,
        "fulltext_chars_used": 0,
        "reference_cut_applied": False,
        "reference_cut_method": "none",
        "reference_cut_marker": None,
        "reference_cut_line_no": None,
        "review_output": None,
        "review_reasoning": None,
        "review_evaluation": None,
        "review_state": status,
        "review_skipped": True,
        "discard_reason": status,
        "final_verdict": f"maybe (review_state:{status})",
        "paper_id": paper_id,
    }


def _build_cutoff_filtered_row(
    *,
    paper_id: str,
    record: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "key": _safe_text(record.get("key")),
        "title": _safe_text(record.get("title") or record.get("query_title")),
        "workflow_arm": WORKFLOW_ARM,
        "stage": WORKFLOW_STAGE,
        "fulltext_review_mode": "batch",
        "fulltext_source_path": None,
        "fulltext_chars_total": 0,
        "fulltext_chars_used": 0,
        "reference_cut_applied": False,
        "reference_cut_method": "none",
        "reference_cut_marker": None,
        "reference_cut_line_no": None,
        "review_output": None,
        "review_reasoning": None,
        "review_evaluation": None,
        "review_state": "cutoff_filtered",
        "review_skipped": True,
        "discard_reason": f"cutoff_time_window:{decision['cutoff_status']}",
        "cutoff_filter": decision,
        "final_verdict": "exclude (cutoff_time_window)",
        "paper_id": paper_id,
    }


def _build_error_row(*, context: dict[str, Any], review_state: str, error_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = context["fulltext_meta"]
    return {
        "key": context["candidate_key"],
        "title": context["candidate_title"],
        "workflow_arm": WORKFLOW_ARM,
        "stage": WORKFLOW_STAGE,
        "fulltext_review_mode": "batch",
        "fulltext_source_path": meta.get("fulltext_source_path"),
        "fulltext_chars_total": meta.get("fulltext_chars_total"),
        "fulltext_chars_used": meta.get("fulltext_chars_used"),
        "reference_cut_applied": meta.get("reference_cut_applied"),
        "reference_cut_method": meta.get("reference_cut_method"),
        "reference_cut_marker": meta.get("reference_cut_marker"),
        "reference_cut_line_no": meta.get("reference_cut_line_no"),
        "review_output": error_payload,
        "review_reasoning": None,
        "review_evaluation": None,
        "review_state": review_state,
        "review_skipped": False,
        "discard_reason": review_state,
        "final_verdict": f"maybe (review_state:{review_state})",
        "paper_id": context["paper_id"],
    }


def _build_success_row(*, context: dict[str, Any], parsed_payload: dict[str, Any]) -> dict[str, Any]:
    parsed = _with_authoritative_output(
        SingleReviewerOutput.model_validate(parsed_payload),
        SourceRecordProvenance.model_validate(context["provenance"]),
        paper_id=context["paper_id"],
        candidate_key=context["candidate_key"],
        candidate_title=context["candidate_title"],
    )
    meta = context["fulltext_meta"]
    return {
        "key": context["candidate_key"],
        "title": context["candidate_title"],
        "workflow_arm": WORKFLOW_ARM,
        "stage": WORKFLOW_STAGE,
        "fulltext_review_mode": "batch",
        "fulltext_source_path": meta.get("fulltext_source_path"),
        "fulltext_chars_total": meta.get("fulltext_chars_total"),
        "fulltext_chars_used": meta.get("fulltext_chars_used"),
        "reference_cut_applied": meta.get("reference_cut_applied"),
        "reference_cut_method": meta.get("reference_cut_method"),
        "reference_cut_marker": meta.get("reference_cut_marker"),
        "reference_cut_line_no": meta.get("reference_cut_line_no"),
        "review_output": parsed.model_dump(mode="json"),
        "review_reasoning": parsed.decision_rationale,
        "review_evaluation": parsed.stage_score,
        "review_state": "reviewed",
        "review_skipped": False,
        "discard_reason": None,
        "final_verdict": f"{_decision_from_score(parsed.stage_score)} (single:{parsed.stage_score})",
        "paper_id": context["paper_id"],
    }


def _prepare_run_context(
    *,
    config: dict[str, Any],
    prompt_assets: PromptAssets,
    selected_papers: list[str],
    max_records: int | None,
    run_id: str,
    write_audits: bool,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    specs: list[BatchRequestSpec] = []
    skipped_rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    paper_summaries: dict[str, Any] = {}
    for paper_id in selected_papers:
        candidate_payload = _load_candidates_with_cutoff(paper_id, max_records=max_records)
        records = list(candidate_payload["selected_records"])
        excluded_records = list(candidate_payload["excluded_records"])
        decisions_by_key = dict(candidate_payload["decisions_by_key"])
        if write_audits:
            _write_json(_paper_cutoff_audit_path(run_id, paper_id), candidate_payload["audit_payload"])
        for record in excluded_records:
            key = _safe_text(record.get("key"))
            skipped_rows_by_paper[paper_id].append(
                _build_cutoff_filtered_row(
                    paper_id=paper_id,
                    record=record,
                    decision=decisions_by_key[key],
                )
            )
        resolution_by_key, audit_payload = _build_resolution_audit(paper_id, records)
        if write_audits:
            _write_json(_paper_resolution_audit_path(run_id, paper_id), audit_payload)
        stage2_criteria_text = json.dumps(_read_json(_paper_stage2_criteria_path(paper_id)), ensure_ascii=False, indent=2)
        exact_or_normalized = 0
        for record in records:
            key = _safe_text(record.get("key"))
            resolution = resolution_by_key[key]
            if resolution["resolution_status"] not in {"exact", "normalized"}:
                skipped_rows_by_paper[paper_id].append(_build_skipped_row(paper_id=paper_id, record=record, resolution=resolution))
                continue
            exact_or_normalized += 1
            provenance = _build_source_record_provenance(record, paper_id, resolution)
            fulltext_text, fulltext_meta = _fulltext_payload_from_resolution(
                resolution,
                head_chars=int(config["fulltext_inline_head_chars"]),
                tail_chars=int(config["fulltext_inline_tail_chars"]),
            )
            context = _base_context(
                prompt_assets=prompt_assets,
                paper_id=paper_id,
                record=record,
                resolution=resolution,
                provenance=provenance,
                stage2_criteria_text=stage2_criteria_text,
                fulltext_text=fulltext_text,
            )
            prompt = render_prompt._render(prompt_assets.template, context, strict=True)
            custom_id = f"{paper_id}__{key}"
            spec_context = {
                "paper_id": paper_id,
                "candidate_key": key,
                "candidate_title": _safe_text(record.get("title") or record.get("query_title")),
                "provenance": provenance.model_dump(mode="json"),
                "fulltext_meta": fulltext_meta,
            }
            body = {
                "model": str(config["model"]),
                "messages": [{"role": "user", "content": prompt}],
                "response_format": build_json_schema_response_format(
                    SingleReviewerOutput,
                    schema_name="SingleReviewerOutput",
                ),
            }
            if reasoning_effort:
                body["reasoning_effort"] = reasoning_effort
            specs.append(
                BatchRequestSpec(
                    custom_id=custom_id,
                    model=str(config["model"]),
                    body=body,
                    response_model=SingleReviewerOutput,
                    validator=lambda payload: _validate_output(payload),  # type: ignore[arg-type]
                    context=spec_context,
                )
            )
        paper_summaries[paper_id] = {
            "paper_id": paper_id,
            "candidate_total": int(candidate_payload["audit_payload"]["candidate_total_before_cutoff"]),
            "candidate_total_after_cutoff_selected_for_run": len(records),
            "cutoff_excluded_count": len(excluded_records),
            "cutoff_audit_path": _relative(_paper_cutoff_audit_path(run_id, paper_id)),
            "batch_request_count": exact_or_normalized,
            "skipped_count": len(skipped_rows_by_paper[paper_id]),
            "resolution_audit_path": _relative(_paper_resolution_audit_path(run_id, paper_id)),
        }
    return {
        "specs": specs,
        "skipped_rows_by_paper": skipped_rows_by_paper,
        "paper_summaries": paper_summaries,
    }


def _model_preflight(model: str) -> str:
    _load_env_file()
    client = OpenAI()
    model_info = client.models.retrieve(model)
    return getattr(model_info, "id", None) or model


def build_serialization_probe() -> dict[str, Any]:
    config = _load_config()
    prompt_assets = PromptAssets()
    run_id = "serialization_probe"
    context = _prepare_run_context(
        config=config,
        prompt_assets=prompt_assets,
        selected_papers=["2409.13738"],
        max_records=2,
        run_id=run_id,
        write_audits=False,
        reasoning_effort=None,
    )
    specs: list[BatchRequestSpec] = context["specs"]
    if not specs:
        raise RuntimeError("找不到可序列化的單審查者 request")
    runner = OpenAIBatchRunner(client=object(), poll_interval_sec=float(config["batch_poll_interval_sec"]))
    return runner.serialize_requests([specs[0]], endpoint=str(config["endpoint"]))[0]


def _run_f1_eval(*, paper_id: str, results_path: Path, gold_path: Path, save_report: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        paper_id,
        "--results",
        str(results_path),
        "--gold-metadata",
        str(gold_path),
        "--positive-mode",
        "include_or_maybe",
        "--save-report",
        str(save_report),
    ]
    subprocess.run(cmd, check=True, cwd=str(REPO_ROOT))
    return _read_json(save_report)


def _load_current_authority(paper_ids: list[str]) -> dict[str, Any]:
    payload = _read_json(RESULTS_MANIFEST_PATH)
    papers = payload.get("papers", {})
    out: dict[str, Any] = {}
    for paper_id in paper_ids:
        item = papers.get(paper_id, {})
        out[paper_id] = item.get("current_metrics", {})
    return out


def _build_report_zh(run_manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# 單審查者官方批次基線")
    lines.append("")
    lines.append(f"- `run_id`：`{run_manifest['run_id']}`")
    lines.append(f"- mode：`{run_manifest['mode']}`")
    lines.append(f"- model：`{run_manifest['model']}`")
    lines.append(f"- reasoning_effort：`{run_manifest.get('reasoning_effort') or '未顯式設定'}`")
    lines.append(f"- endpoint：`{run_manifest['endpoint']}`")
    lines.append(f"- batch_status：`{run_manifest.get('batch_status')}`")
    lines.append("")
    lines.append("## 指標")
    lines.append("")
    lines.append("| Paper | Candidates | Batch requests | F1 | Delta vs current combined | Precision | Recall |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for summary in run_manifest.get("summaries", []):
        paper_id = summary["paper_id"]
        current_combined = float(run_manifest["baseline"][paper_id]["combined"]["f1"])
        f1_value = float(summary["f1"])
        lines.append(
            f"| `{paper_id}` | {summary['candidate_total']} | {summary['batch_request_count']} | "
            f"{f1_value:.4f} | {f1_value - current_combined:+.4f} | "
            f"{float(summary['precision']):.4f} | {float(summary['recall']):.4f} |"
        )
    lines.append("")
    lines.append("## 工件")
    lines.append("")
    lines.append(f"- batch 工件：`{run_manifest['batch_artifact_dir']}`")
    lines.append(f"- run manifest：`{run_manifest['run_manifest_path']}`")
    return "\n".join(lines) + "\n"


def _submit_mode(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    prompt_assets: PromptAssets,
) -> int:
    _load_env_file()
    run_id = args.run_id or _now_run_id()
    run_dir = _run_dir(run_id)
    if run_dir.exists():
        raise SystemExit(f"run_id 已存在：{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)

    selected_papers = list(args.papers or config["papers"])
    reasoning_effort = args.reasoning_effort
    model_id = _model_preflight(str(config["model"]))
    context = _prepare_run_context(
        config=config,
        prompt_assets=prompt_assets,
        selected_papers=selected_papers,
        max_records=args.max_records,
        run_id=run_id,
        write_audits=True,
        reasoning_effort=reasoning_effort,
    )
    specs: list[BatchRequestSpec] = context["specs"]
    if not specs:
        run_manifest = {
            "run_id": run_id,
            "mode": args.mode,
            "bundle_dir": str(BUNDLE_DIR),
            "manifest_path": str(MANIFEST_PATH),
            "run_manifest_path": str(_run_manifest_path(run_id)),
            "results_root": str(RESULTS_ROOT),
            "run_dir": str(run_dir),
            "batch_artifact_dir": str(_batch_artifact_dir(run_id, str(config["model"]))),
            "model": str(config["model"]),
            "model_preflight_id": model_id,
            "reasoning_effort": reasoning_effort,
            "endpoint": str(config["endpoint"]),
            "papers": selected_papers,
            "max_records": args.max_records,
            "request_count": 0,
            "paper_preparation": context["paper_summaries"],
            "upload_file_id": None,
            "batch_id": None,
            "batch_status": "not_required_cutoff_only",
        }
        _write_json(_run_manifest_path(run_id), run_manifest)
        print(f"[submit] run_id={run_id}", flush=True)
        print("[submit] batch_not_required=cutoff_only", flush=True)
        return 0

    runner = OpenAIBatchRunner(
        client=OpenAI(),
        poll_interval_sec=float(args.batch_poll_interval_sec or config["batch_poll_interval_sec"]),
    )
    artifact_dir = _batch_artifact_dir(run_id, str(config["model"]))
    submit_payload = runner.submit_requests(
        specs=specs,
        endpoint=str(config["endpoint"]),
        artifact_dir=artifact_dir,
        metadata={
            "experiment": WORKFLOW_ARM,
            "run_id": run_id,
            "paper_count": len(selected_papers),
        },
        completion_window=str(config["completion_window"]),
    )

    run_manifest = {
        "run_id": run_id,
        "mode": args.mode,
        "bundle_dir": str(BUNDLE_DIR),
        "manifest_path": str(MANIFEST_PATH),
        "run_manifest_path": str(_run_manifest_path(run_id)),
        "results_root": str(RESULTS_ROOT),
        "run_dir": str(run_dir),
        "batch_artifact_dir": str(artifact_dir),
        "model": str(config["model"]),
        "model_preflight_id": model_id,
        "reasoning_effort": reasoning_effort,
        "endpoint": str(config["endpoint"]),
        "papers": selected_papers,
        "max_records": args.max_records,
        "request_count": len(specs),
        "paper_preparation": context["paper_summaries"],
        "upload_file_id": submit_payload["upload_file"]["id"],
        "batch_id": submit_payload["batch_create"]["id"],
        "batch_status": submit_payload["batch_create"]["status"],
    }
    _write_json(_run_manifest_path(run_id), run_manifest)
    print(f"[submit] run_id={run_id}", flush=True)
    print(f"[submit] batch_id={run_manifest['batch_id']}", flush=True)
    print(f"[submit] input_jsonl={artifact_dir / 'input.jsonl'}", flush=True)
    return 0


def _collect_mode(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    prompt_assets: PromptAssets,
) -> int:
    if not args.run_id:
        raise SystemExit("--mode collect 需要 --run-id")
    _load_env_file()
    manifest_path = _run_manifest_path(args.run_id)
    if not manifest_path.exists():
        raise SystemExit(f"找不到 run manifest：{manifest_path}")
    run_manifest = _read_json(manifest_path)
    selected_papers = list(run_manifest["papers"])
    max_records = run_manifest.get("max_records")
    reasoning_effort = args.reasoning_effort if args.reasoning_effort is not None else run_manifest.get("reasoning_effort")
    context = _prepare_run_context(
        config=config,
        prompt_assets=prompt_assets,
        selected_papers=selected_papers,
        max_records=max_records,
        run_id=args.run_id,
        write_audits=True,
        reasoning_effort=reasoning_effort,
    )
    specs: list[BatchRequestSpec] = context["specs"]
    artifact_dir = _batch_artifact_dir(args.run_id, str(config["model"]))
    if run_manifest.get("batch_id"):
        runner = OpenAIBatchRunner(
            client=OpenAI(),
            poll_interval_sec=float(args.batch_poll_interval_sec or config["batch_poll_interval_sec"]),
        )
        batch_payload = runner.wait_until_terminal(
            run_manifest["batch_id"],
            artifact_dir=artifact_dir,
            max_wait_minutes=float(args.batch_max_wait_minutes or config["batch_max_wait_minutes"]),
        )
        parsed_payload = runner.collect_results(specs=specs, batch_payload=batch_payload, artifact_dir=artifact_dir)
    else:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        batch_payload = {
            "status": "not_required_cutoff_only",
            "completed_at": None,
            "output_file_id": None,
            "error_file_id": None,
        }
        parsed_payload = {"successes": [], "failures": [], "missing": []}

    success_by_id = {item["custom_id"]: item for item in parsed_payload["successes"]}
    failure_by_id = {item["custom_id"]: item for item in parsed_payload["failures"]}
    missing_by_id = {item["custom_id"]: item for item in parsed_payload["missing"]}

    baseline = _load_current_authority(selected_papers)
    summaries: list[dict[str, Any]] = []
    for paper_id in selected_papers:
        paper_dir = _paper_result_dir(args.run_id, paper_id)
        paper_dir.mkdir(parents=True, exist_ok=True)
        rows = list(context["skipped_rows_by_paper"][paper_id])
        for spec in specs:
            if spec.context["paper_id"] != paper_id:
                continue
            custom_id = spec.custom_id
            if custom_id in success_by_id:
                rows.append(_build_success_row(context=spec.context, parsed_payload=success_by_id[custom_id]["parsed"]))
                continue
            if custom_id in failure_by_id:
                rows.append(
                    _build_error_row(
                        context=spec.context,
                        review_state="batch_error",
                        error_payload=failure_by_id[custom_id],
                    )
                )
                continue
            if custom_id in missing_by_id:
                rows.append(
                    _build_error_row(
                        context=spec.context,
                        review_state="batch_missing",
                        error_payload=missing_by_id[custom_id],
                    )
                )
                continue
            rows.append(_build_error_row(context=spec.context, review_state="batch_unmapped", error_payload=None))

        _write_json(_paper_results_path(args.run_id, paper_id), rows)
        metrics = _run_f1_eval(
            paper_id=paper_id,
            results_path=_paper_results_path(args.run_id, paper_id),
            gold_path=_paper_gold_path(paper_id),
            save_report=_paper_metrics_path(args.run_id, paper_id),
        )
        paper_summary = context["paper_summaries"][paper_id]
        summaries.append(
            {
                "paper_id": paper_id,
                "candidate_total": int(paper_summary["candidate_total"]),
                "batch_request_count": int(paper_summary["batch_request_count"]),
                "skipped_count": int(paper_summary["skipped_count"]),
                "results_path": _relative(_paper_results_path(args.run_id, paper_id)),
                "metrics_path": _relative(_paper_metrics_path(args.run_id, paper_id)),
                "precision": float(metrics["metrics"]["precision"]),
                "recall": float(metrics["metrics"]["recall"]),
                "f1": float(metrics["metrics"]["f1"]),
            }
        )

    run_manifest.update(
        {
            "mode": args.mode,
            "reasoning_effort": reasoning_effort,
            "batch_status": batch_payload.get("status"),
            "batch_completed_at": batch_payload.get("completed_at"),
            "batch_output_file_id": batch_payload.get("output_file_id"),
            "batch_error_file_id": batch_payload.get("error_file_id"),
            "baseline": {
                paper_id: {
                    "combined": {
                        "path": baseline[paper_id]["combined"]["path"],
                        "f1": float(baseline[paper_id]["combined"]["f1"]),
                    }
                }
                for paper_id in selected_papers
            },
            "parsed_summary": {
                "success_count": len(parsed_payload["successes"]),
                "failure_count": len(parsed_payload["failures"]),
                "missing_count": len(parsed_payload["missing"]),
            },
            "summaries": summaries,
        }
    )
    _write_json(manifest_path, run_manifest)
    _report_path(args.run_id).write_text(_build_report_zh(run_manifest), encoding="utf-8")
    print(f"[collect] run_id={args.run_id}", flush=True)
    print(f"[collect] batch_status={batch_payload.get('status')}", flush=True)
    return 0


def main() -> int:
    config = _load_config()
    parser = argparse.ArgumentParser(description="執行單審查者官方批次基線。")
    parser.add_argument("--mode", choices=["submit", "collect", "run"], required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--papers", nargs="*", choices=list(config["papers"]), default=list(config["papers"]))
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--batch-poll-interval-sec", type=float, default=None)
    parser.add_argument("--batch-max-wait-minutes", type=float, default=None)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default=None)
    args = parser.parse_args()

    prompt_assets = PromptAssets()
    if args.mode == "submit":
        return _submit_mode(args=args, config=config, prompt_assets=prompt_assets)
    if args.mode == "collect":
        return _collect_mode(args=args, config=config, prompt_assets=prompt_assets)

    run_id = args.run_id or _now_run_id()
    submit_args = argparse.Namespace(
        mode="submit",
        run_id=run_id,
        papers=args.papers,
        max_records=args.max_records,
        batch_poll_interval_sec=args.batch_poll_interval_sec,
        batch_max_wait_minutes=args.batch_max_wait_minutes,
        reasoning_effort=args.reasoning_effort,
    )
    _submit_mode(args=submit_args, config=config, prompt_assets=prompt_assets)
    collect_args = argparse.Namespace(
        mode="collect",
        run_id=run_id,
        papers=args.papers,
        max_records=args.max_records,
        batch_poll_interval_sec=args.batch_poll_interval_sec,
        batch_max_wait_minutes=args.batch_max_wait_minutes,
        reasoning_effort=args.reasoning_effort,
    )
    return _collect_mode(args=collect_args, config=config, prompt_assets=prompt_assets)


if __name__ == "__main__":
    raise SystemExit(main())
