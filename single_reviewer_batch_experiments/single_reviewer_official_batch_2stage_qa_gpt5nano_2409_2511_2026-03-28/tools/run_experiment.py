#!/usr/bin/env python3
"""執行 single reviewer official-batch 2-stage QA 實驗線。"""

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
RESULTS_ROOT = REPO_ROOT / "screening" / "results" / "single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28"
RESULTS_MANIFEST_PATH = REPO_ROOT / "screening" / "results" / "results_manifest.json"
WORKFLOW_ARM = "single-reviewer-official-batch-2stage-qa"
WORKFLOW_STAGE_MODEL = "two_stage_qa"
PHASES = ("stage1_qa", "stage1_eval", "stage2_qa", "stage2_eval")
FULLTEXT_TRUNCATION_MARKER = "\n\n...[TRUNCATED MIDDLE]...\n\n"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRecordProvenance(_StrictModel):
    record_key: str
    record_title: str | None = None
    source: str | None = None
    source_id: str | None = None
    metadata_path: str
    runtime_prompts_path: str
    criteria_stage1_path: str
    criteria_stage2_path: str
    fulltext_candidate_path: str
    fulltext_available: bool


class PriorStageReference(_StrictModel):
    stage: str
    available: bool
    candidate_key: str | None = None
    candidate_title: str | None = None


class QAAnswer(_StrictModel):
    qid: str
    criterion_family: str
    answer_state: Literal["present", "absent", "unclear"]
    state_basis: Literal["direct_support", "direct_counterevidence", "insufficient_signal", "mixed_signal"]
    answer_rationale: str
    supporting_quotes: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    missingness_reason: str | None = None
    stage2_handoff_note: str | None = None
    conflict_note: str | None = None
    candidate_synthesis_fields: list[str] | None = None


class StageQAOutput(_StrictModel):
    paper_id: str
    candidate_key: str
    candidate_title: str
    stage: Literal["stage1", "stage2"]
    workflow_arm: Literal["single-reviewer-official-batch-2stage-qa"]
    qa_source_path: str
    source_record_provenance: SourceRecordProvenance
    reviewer_guardrails_applied: list[str] = Field(default_factory=list)
    answers: list[QAAnswer]


class FieldRecord(_StrictModel):
    field_name: str
    state: Literal["present", "absent", "unclear"]
    state_basis: Literal["direct_support", "direct_counterevidence", "insufficient_signal", "mixed_signal"]
    normalized_value: str | list[str] | None = None
    supporting_quotes: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    missingness_reason: str | None = None
    conflict_note: str | None = None
    derived_from_qids: list[str] = Field(default_factory=list)
    stage_handoff_status: str
    support_source_kind: Literal["current_stage_qa", "prior_stage_output", "current_stage_qa_and_prior_stage_output"]


class StageSynthesisOutput(_StrictModel):
    paper_id: str
    candidate_key: str
    candidate_title: str
    stage: Literal["stage1", "stage2"]
    workflow_arm: Literal["single-reviewer-official-batch-2stage-qa"]
    source_record_provenance: SourceRecordProvenance
    prior_stage_reference: PriorStageReference
    field_records: list[FieldRecord]


class CriterionMappingItem(_StrictModel):
    criterion_text: str
    status: str
    support_ids: list[str] = Field(default_factory=list)


class StageCriteriaEvaluationOutput(_StrictModel):
    paper_id: str
    candidate_key: str
    candidate_title: str
    stage: Literal["stage1", "stage2"]
    workflow_arm: Literal["single-reviewer-official-batch-2stage-qa"]
    source_record_provenance: SourceRecordProvenance
    stage_score: int = Field(ge=1, le=5)
    scoring_basis: Literal[
        "clear_include",
        "clear_exclude_with_direct_negative",
        "unresolved_without_direct_negative",
        "mixed_conflict",
    ]
    decision_recommendation: Literal["include", "exclude", "maybe"]
    positive_fit_evidence_ids: list[str] = Field(default_factory=list)
    direct_negative_evidence_ids: list[str] = Field(default_factory=list)
    unresolved_core_evidence_ids: list[str] = Field(default_factory=list)
    deferred_core_evidence_ids: list[str] = Field(default_factory=list)
    criterion_mapping: list[CriterionMappingItem] = Field(default_factory=list)
    criterion_conflicts: list[str] = Field(default_factory=list)
    decision_rationale: str
    manual_review_needed: bool
    routing_note: str


class SingleReviewerFinalRow(_StrictModel):
    key: str
    title: str
    paper_id: str
    workflow_arm: Literal["single-reviewer-official-batch-2stage-qa"]
    stage_model: Literal["two_stage_qa"]
    review_state: str
    review_skipped: bool
    failed_phase: str | None = None
    discard_reason: str | None = None
    final_verdict: str
    stage1_stage_score: int | None = None
    stage1_decision_recommendation: Literal["include", "exclude", "maybe"] | None = None
    stage2_stage_score: int | None = None
    stage2_decision_recommendation: Literal["include", "exclude", "maybe"] | None = None
    stage1_eval_path: str | None = None
    stage2_eval_path: str | None = None
    stage1_synthesis_path: str | None = None
    stage2_synthesis_path: str | None = None
    source_record_provenance: SourceRecordProvenance | None = None
    review_output: dict[str, Any] | None = None
    fulltext_source_path: str | None = None
    fulltext_resolution_status: str | None = None


class PromptAssets:
    def __init__(self) -> None:
        self.templates = {
            "stage1_qa": (BUNDLE_DIR / "templates" / "01_stage1_qa_TEMPLATE.md").read_text(encoding="utf-8"),
            "stage1_eval": (BUNDLE_DIR / "templates" / "02_stage1_eval_TEMPLATE.md").read_text(encoding="utf-8"),
            "stage2_qa": (BUNDLE_DIR / "templates" / "03_stage2_qa_TEMPLATE.md").read_text(encoding="utf-8"),
            "stage2_eval": (BUNDLE_DIR / "templates" / "04_stage2_eval_TEMPLATE.md").read_text(encoding="utf-8"),
        }
        self.schema_hints = {
            "stage1_qa": (BUNDLE_DIR / "samples" / "stage1_qa_output.sample.json").read_text(encoding="utf-8"),
            "stage1_eval": (BUNDLE_DIR / "samples" / "stage1_eval_output.sample.json").read_text(encoding="utf-8"),
            "stage2_qa": (BUNDLE_DIR / "samples" / "stage2_qa_output.sample.json").read_text(encoding="utf-8"),
            "stage2_eval": (BUNDLE_DIR / "samples" / "stage2_eval_output.sample.json").read_text(encoding="utf-8"),
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


def _load_config() -> dict[str, Any]:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    required = {
        "model",
        "papers",
        "supported_phases",
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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _relative(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def _decision_from_score(score: int) -> Literal["include", "exclude", "maybe"]:
    if score >= 4:
        return "include"
    if score <= 2:
        return "exclude"
    return "maybe"


def _stage_verdict(stage: str, score: int) -> str:
    return f"{_decision_from_score(score)} ({stage}:{score})"


def _normalize_key(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


def _paper_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _paper_gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _paper_fulltext_root(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "mds"


def _paper_stage1_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage1" / f"{paper_id}.json"


def _paper_stage2_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage2" / f"{paper_id}.json"


def _paper_cutoff_path(paper_id: str) -> Path:
    return cutoff_time_filter.cutoff_json_path(REPO_ROOT, paper_id)


def _runtime_prompts_path() -> Path:
    return REPO_ROOT / "scripts" / "screening" / "runtime_prompts" / "runtime_prompts.json"


def _qa_asset_path(paper_id: str, stage: str) -> Path:
    return BUNDLE_DIR / "qa_assets" / f"{paper_id}.{stage}.json"


def _run_dir(run_id: str) -> Path:
    return RESULTS_ROOT / "runs" / run_id


def _batch_artifact_dir(run_id: str, phase: str, model: str) -> Path:
    return _run_dir(run_id) / "batch_jobs" / phase / model


def _paper_dir(run_id: str, paper_id: str) -> Path:
    return _run_dir(run_id) / "papers" / paper_id


def _paper_cutoff_audit_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "cutoff_audit.json"


def _paper_fulltext_resolution_audit_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "fulltext_resolution_audit.json"


def _paper_stage1_qa_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage1_qa.jsonl"


def _paper_stage1_synthesis_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage1_synthesis.json"


def _paper_stage1_eval_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage1_eval.json"


def _paper_stage2_selection_keys_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "selected_for_stage2.keys.txt"


def _paper_stage2_qa_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage2_qa.jsonl"


def _paper_stage2_synthesis_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage2_synthesis.json"


def _paper_stage2_eval_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "stage2_eval.json"


def _paper_results_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "single_reviewer_batch_results.json"


def _paper_metrics_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "single_reviewer_batch_f1.json"


def _paper_eval_keys_path(run_id: str, paper_id: str) -> Path:
    return _paper_dir(run_id, paper_id) / "eval_keys.txt"


def _run_manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / "run_manifest.json"


def _report_path(run_id: str) -> Path:
    return _run_dir(run_id) / "REPORT_zh.md"


def _custom_id(phase: str, paper_id: str, key: str) -> str:
    return f"{phase}__{paper_id}__{key}"


def _load_candidate_key_map(path: Path | None, *, selected_papers: list[str]) -> dict[str, set[str]] | None:
    if path is None:
        return None
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise SystemExit("--candidate-keys-file 必須是 paper_id -> key list 的 JSON object")
    out: dict[str, set[str]] = {}
    for paper_id in selected_papers:
        values = payload.get(paper_id, [])
        if not isinstance(values, list):
            raise SystemExit(f"candidate keys for {paper_id} 必須是 list")
        out[paper_id] = {str(item).strip() for item in values if str(item).strip()}
    return out


def _load_candidates(
    paper_id: str,
    *,
    max_records: int | None = None,
    key_allowlist: set[str] | None = None,
) -> list[dict[str, Any]]:
    rows = _read_jsonl(_paper_metadata_path(paper_id))
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in rows:
        key = _safe_text(row.get("key"))
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        if key_allowlist is not None and key not in key_allowlist:
            continue
        deduped.append(row)
    if max_records is not None:
        return deduped[:max_records]
    return deduped


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


class FulltextIndex:
    def __init__(self, paper_id: str) -> None:
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
        "workflow_arm": WORKFLOW_ARM,
        "paper_id": paper_id,
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
        runtime_prompts_path=str(_runtime_prompts_path().relative_to(REPO_ROOT)),
        criteria_stage1_path=str(_paper_stage1_criteria_path(paper_id).relative_to(REPO_ROOT)),
        criteria_stage2_path=str(_paper_stage2_criteria_path(paper_id).relative_to(REPO_ROOT)),
        fulltext_candidate_path=str(resolution.get("exact_candidate_path") or ""),
        fulltext_available=resolution["resolution_status"] in {"exact", "normalized"},
    )


def _metadata_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": _safe_text(record.get("key")),
        "query_title": _safe_text(record.get("query_title")),
        "title": _safe_text(record.get("title") or record.get("query_title")),
        "abstract": _safe_text(record.get("abstract")),
        "source": _safe_text(record.get("source")),
        "source_id": _safe_text(record.get("source_id")),
        "match_status": _safe_text(record.get("match_status")),
        "missing_reason": _safe_text(record.get("missing_reason")),
        "published_date": _safe_text(record.get("published_date")),
    }


def _load_cutoff_result(
    *,
    paper_id: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    cutoff_path = _paper_cutoff_path(paper_id)
    payload, policy = cutoff_time_filter.load_time_policy(cutoff_path)
    payload = dict(payload)
    payload["_cutoff_json_path"] = str(cutoff_path.relative_to(REPO_ROOT))
    return cutoff_time_filter.apply_cutoff(records, payload=payload, policy=policy)


def _load_phase_json_outputs(path: Path, model: type[_StrictModel]) -> list[_StrictModel]:
    if not path.exists():
        return []
    if path.suffix == ".jsonl":
        rows = _read_jsonl(path)
    else:
        payload = _read_json(path)
        rows = payload if isinstance(payload, list) else []
    return [model.model_validate(row) for row in rows]


def _outputs_by_key(outputs: list[_StrictModel]) -> dict[str, _StrictModel]:
    keyed: dict[str, _StrictModel] = {}
    for output in outputs:
        keyed[str(getattr(output, "candidate_key"))] = output
    return keyed


def _dedupe_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _synthesis_state_from_bases(bases: list[str]) -> tuple[str, str]:
    has_support = any(base == "direct_support" for base in bases)
    has_counter = any(base == "direct_counterevidence" for base in bases)
    if has_support and not has_counter:
        return "present", "direct_support"
    if has_counter and not has_support:
        return "absent", "direct_counterevidence"
    if has_support or has_counter:
        return "unclear", "mixed_signal"
    if any(base == "mixed_signal" for base in bases):
        return "unclear", "mixed_signal"
    return "unclear", "insufficient_signal"


def _synthesize_from_qa(
    qa_output: StageQAOutput,
    *,
    prior_stage_synthesis: StageSynthesisOutput | None = None,
) -> StageSynthesisOutput:
    bucket: dict[str, dict[str, Any]] = {}

    if prior_stage_synthesis is not None:
        for field in prior_stage_synthesis.field_records:
            bucket[field.field_name] = {
                "prior": [field],
                "current": [],
            }

    for answer in qa_output.answers:
        field_names = answer.candidate_synthesis_fields or [answer.qid]
        for field_name in field_names:
            bucket.setdefault(field_name, {"prior": [], "current": []})
            bucket[field_name]["current"].append(answer)

    field_records: list[FieldRecord] = []
    for field_name in sorted(bucket):
        prior_items = bucket[field_name]["prior"]
        current_items = bucket[field_name]["current"]
        bases: list[str] = []
        supporting_quotes: list[str] = []
        locations: list[str] = []
        missingness_reason: str | None = None
        conflict_bits: list[str] = []
        derived_from_qids: list[str] = []

        for field in prior_items:
            bases.append(field.state_basis)
            supporting_quotes.extend(field.supporting_quotes)
            locations.extend(field.locations)
            if missingness_reason is None and field.missingness_reason:
                missingness_reason = field.missingness_reason
            if field.conflict_note:
                conflict_bits.append(field.conflict_note)
            derived_from_qids.extend(field.derived_from_qids)

        for answer in current_items:
            bases.append(answer.state_basis)
            supporting_quotes.extend(answer.supporting_quotes)
            locations.extend(answer.locations)
            if missingness_reason is None and answer.missingness_reason:
                missingness_reason = answer.missingness_reason
            if answer.conflict_note:
                conflict_bits.append(answer.conflict_note)
            derived_from_qids.append(answer.qid)

        state, state_basis = _synthesis_state_from_bases(bases)
        current_exists = bool(current_items)
        prior_exists = bool(prior_items)
        if qa_output.stage == "stage2":
            if current_exists and prior_exists:
                stage_handoff_status = "resolved_in_stage2"
                support_source_kind = "current_stage_qa_and_prior_stage_output"
            elif prior_exists:
                stage_handoff_status = "carried_from_stage1"
                support_source_kind = "prior_stage_output"
            else:
                stage_handoff_status = "current_stage_only"
                support_source_kind = "current_stage_qa"
        else:
            stage_handoff_status = "current_stage_only"
            support_source_kind = "current_stage_qa"

        conflict_note = None
        if any(base == "direct_support" for base in bases) and any(base == "direct_counterevidence" for base in bases):
            conflict_bits.append("support and counterevidence coexist in the aggregated evidence.")
        if conflict_bits:
            conflict_note = " ".join(_dedupe_list(conflict_bits))

        field_records.append(
            FieldRecord(
                field_name=field_name,
                state=state,
                state_basis=state_basis,
                normalized_value=None,
                supporting_quotes=_dedupe_list(supporting_quotes),
                locations=_dedupe_list(locations),
                missingness_reason=missingness_reason,
                conflict_note=conflict_note,
                derived_from_qids=_dedupe_list(derived_from_qids),
                stage_handoff_status=stage_handoff_status,
                support_source_kind=support_source_kind,
            )
        )

    prior_reference = PriorStageReference(
        stage="stage1",
        available=prior_stage_synthesis is not None,
        candidate_key=qa_output.candidate_key if prior_stage_synthesis is not None else None,
        candidate_title=qa_output.candidate_title if prior_stage_synthesis is not None else None,
    )
    return StageSynthesisOutput(
        paper_id=qa_output.paper_id,
        candidate_key=qa_output.candidate_key,
        candidate_title=qa_output.candidate_title,
        stage=qa_output.stage,
        workflow_arm=WORKFLOW_ARM,
        source_record_provenance=qa_output.source_record_provenance,
        prior_stage_reference=prior_reference,
        field_records=field_records,
    )


def _load_criteria_entries(paper_id: str, stage: str) -> list[str]:
    criteria_path = _paper_stage1_criteria_path(paper_id) if stage == "stage1" else _paper_stage2_criteria_path(paper_id)
    payload = _read_json(criteria_path)
    out: list[str] = []
    inclusion = payload.get("inclusion_criteria", {})
    required = inclusion.get("required", []) if isinstance(inclusion, dict) else []
    for item in required:
        if isinstance(item, dict):
            out.append(str(item.get("criterion") or "").strip())
    for item in payload.get("exclusion_criteria", []):
        if isinstance(item, dict):
            out.append(str(item.get("criterion") or "").strip())
    return [item for item in out if item]


def _make_stage_qa_validator(
    *,
    paper_id: str,
    stage: str,
    candidate_key: str,
    candidate_title: str,
    qa_source_path: str,
    expected_qids: list[str],
) -> Any:
    expected = set(expected_qids)

    def validate(payload: BaseModel) -> None:
        parsed = StageQAOutput.model_validate(payload)
        if parsed.paper_id != paper_id:
            raise ValueError("paper_id mismatch")
        if parsed.stage != stage:
            raise ValueError("stage mismatch")
        if parsed.candidate_key != candidate_key:
            raise ValueError("candidate_key mismatch")
        if parsed.candidate_title != candidate_title:
            raise ValueError("candidate_title mismatch")
        if parsed.workflow_arm != WORKFLOW_ARM:
            raise ValueError("workflow_arm mismatch")
        if parsed.qa_source_path != qa_source_path:
            raise ValueError("qa_source_path mismatch")
        if len(parsed.answers) != len(expected):
            raise ValueError(f"answers length mismatch: expected={len(expected)} observed={len(parsed.answers)}")
        observed = {answer.qid for answer in parsed.answers}
        if observed != expected:
            raise ValueError(f"qid mismatch: expected={sorted(expected)} observed={sorted(observed)}")

    return validate


def _make_eval_validator(
    *,
    paper_id: str,
    stage: str,
    candidate_key: str,
    candidate_title: str,
    expected_field_names: set[str],
) -> Any:
    def validate(payload: BaseModel) -> None:
        parsed = StageCriteriaEvaluationOutput.model_validate(payload)
        if parsed.paper_id != paper_id:
            raise ValueError("paper_id mismatch")
        if parsed.stage != stage:
            raise ValueError("stage mismatch")
        if parsed.candidate_key != candidate_key:
            raise ValueError("candidate_key mismatch")
        if parsed.candidate_title != candidate_title:
            raise ValueError("candidate_title mismatch")
        if parsed.workflow_arm != WORKFLOW_ARM:
            raise ValueError("workflow_arm mismatch")
        expected_decision = _decision_from_score(parsed.stage_score)
        if parsed.decision_recommendation != expected_decision:
            raise ValueError(
                f"decision_recommendation 必須與 stage_score 對齊 ({parsed.stage_score} -> {expected_decision})"
            )
        referenced = set(
            parsed.positive_fit_evidence_ids
            + parsed.direct_negative_evidence_ids
            + parsed.unresolved_core_evidence_ids
            + parsed.deferred_core_evidence_ids
        )
        for mapping in parsed.criterion_mapping:
            referenced.update(mapping.support_ids)
        unknown = sorted(referenced.difference(expected_field_names))
        if unknown:
            raise ValueError("未知 evidence ids: " + ", ".join(unknown))

    return validate


def _criteria_text_for_stage(paper_id: str, stage: str) -> str:
    path = _paper_stage1_criteria_path(paper_id) if stage == "stage1" else _paper_stage2_criteria_path(paper_id)
    return _json_text(_read_json(path))


def _load_qa_asset(paper_id: str, stage: str) -> dict[str, Any]:
    payload = _read_json(_qa_asset_path(paper_id, stage))
    if not isinstance(payload, dict):
        raise SystemExit(f"QA asset 不是 JSON object: {paper_id}.{stage}")
    return payload


def _build_body(
    *,
    model: str,
    prompt: str,
    response_model: type[BaseModel],
    schema_name: str,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(response_model, schema_name=schema_name),
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    return body


def _prepare_stage1_qa_specs(
    *,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    write_audits: bool,
) -> dict[str, Any]:
    specs: list[BatchRequestSpec] = []
    paper_summaries: dict[str, Any] = {}
    for paper_id in selected_papers:
        key_allowlist = key_map.get(paper_id) if key_map is not None else None
        records = _load_candidates(paper_id, max_records=max_records, key_allowlist=key_allowlist)
        if key_allowlist is not None:
            keys_path = _paper_eval_keys_path(run_id, paper_id)
            keys_path.parent.mkdir(parents=True, exist_ok=True)
            keys_path.write_text("\n".join([_safe_text(row.get("key")) for row in records]) + ("\n" if records else ""), encoding="utf-8")
        resolution_by_key, resolution_audit = _build_resolution_audit(paper_id, records)
        if write_audits:
            _write_json(_paper_fulltext_resolution_audit_path(run_id, paper_id), resolution_audit)
        cutoff_result = _load_cutoff_result(paper_id=paper_id, records=records)
        if write_audits:
            _write_json(_paper_cutoff_audit_path(run_id, paper_id), cutoff_result["audit_payload"])
        qa_asset = _load_qa_asset(paper_id, "stage1")
        expected_qids = [str(item["qid"]) for item in qa_asset.get("questions", []) if isinstance(item, dict) and item.get("qid")]
        criteria_text = _criteria_text_for_stage(paper_id, "stage1")
        for record in cutoff_result["kept_records"]:
            key = _safe_text(record.get("key"))
            title = _safe_text(record.get("title") or record.get("query_title"))
            resolution = resolution_by_key[key]
            provenance = _build_source_record_provenance(record, paper_id, resolution)
            context = {
                "WORKFLOW_ARM": WORKFLOW_ARM,
                "PAPER_ID": paper_id,
                "CANDIDATE_KEY": key,
                "CANDIDATE_TITLE": title,
                "QA_ASSET_JSON": _json_text(qa_asset),
                "STAGE_CRITERIA_JSON_CONTENT": criteria_text,
                "METADATA_JSON": _json_text(_metadata_payload(record)),
                "SOURCE_RECORD_PROVENANCE_JSON": _json_text(provenance.model_dump(mode="json")),
                "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.schema_hints["stage1_qa"],
            }
            prompt = render_prompt._render(prompt_assets.templates["stage1_qa"], context, strict=True)
            specs.append(
                BatchRequestSpec(
                    custom_id=_custom_id("stage1_qa", paper_id, key),
                    model=str(config["model"]),
                    body=_build_body(
                        model=str(config["model"]),
                        prompt=prompt,
                        response_model=StageQAOutput,
                        schema_name="StageQAOutput",
                        reasoning_effort=reasoning_effort,
                    ),
                    response_model=StageQAOutput,
                    validator=_make_stage_qa_validator(
                        paper_id=paper_id,
                        stage="stage1",
                        candidate_key=key,
                        candidate_title=title,
                        qa_source_path=f"qa_assets/{paper_id}.stage1.json",
                        expected_qids=expected_qids,
                    ),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": title,
                        "phase": "stage1_qa",
                        "provenance": provenance.model_dump(mode="json"),
                    },
                )
            )
        paper_summaries[paper_id] = {
            "candidate_total": len(records),
            "cutoff_pass_count": len(cutoff_result["kept_records"]),
            "cutoff_excluded_count": len(cutoff_result["excluded_records"]),
            "request_count": len(cutoff_result["kept_records"]),
        }
    return {"specs": specs, "paper_summaries": paper_summaries}


def _prepare_stage1_eval_specs(
    *,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    reasoning_effort: str | None,
) -> dict[str, Any]:
    specs: list[BatchRequestSpec] = []
    paper_summaries: dict[str, Any] = {}
    for paper_id in selected_papers:
        qa_outputs = [StageQAOutput.model_validate(row) for row in _read_jsonl(_paper_stage1_qa_path(run_id, paper_id))] if _paper_stage1_qa_path(run_id, paper_id).exists() else []
        synth_outputs = [_synthesize_from_qa(output) for output in qa_outputs]
        _write_json(_paper_stage1_synthesis_path(run_id, paper_id), [output.model_dump(mode="json") for output in synth_outputs])
        criteria_text = _criteria_text_for_stage(paper_id, "stage1")
        for synth in synth_outputs:
            field_names = {field.field_name for field in synth.field_records}
            context = {
                "WORKFLOW_ARM": WORKFLOW_ARM,
                "PAPER_ID": paper_id,
                "CANDIDATE_KEY": synth.candidate_key,
                "SYNTHESIS_JSON": _json_text(synth.model_dump(mode="json")),
                "ALLOWED_EVIDENCE_IDS_JSON": _json_text(sorted(field_names)),
                "STAGE_CRITERIA_JSON_CONTENT": criteria_text,
                "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.schema_hints["stage1_eval"],
            }
            prompt = render_prompt._render(prompt_assets.templates["stage1_eval"], context, strict=True)
            specs.append(
                BatchRequestSpec(
                    custom_id=_custom_id("stage1_eval", paper_id, synth.candidate_key),
                    model=str(config["model"]),
                    body=_build_body(
                        model=str(config["model"]),
                        prompt=prompt,
                        response_model=StageCriteriaEvaluationOutput,
                        schema_name="StageCriteriaEvaluationOutput",
                        reasoning_effort=reasoning_effort,
                    ),
                    response_model=StageCriteriaEvaluationOutput,
                    validator=_make_eval_validator(
                        paper_id=paper_id,
                        stage="stage1",
                        candidate_key=synth.candidate_key,
                        candidate_title=synth.candidate_title,
                        expected_field_names=field_names,
                    ),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": synth.candidate_key,
                        "candidate_title": synth.candidate_title,
                        "phase": "stage1_eval",
                        "provenance": synth.source_record_provenance.model_dump(mode="json"),
                    },
                )
            )
        paper_summaries[paper_id] = {"request_count": len(synth_outputs), "synthesis_count": len(synth_outputs)}
    return {"specs": specs, "paper_summaries": paper_summaries}


def _prepare_stage2_qa_specs(
    *,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    write_audits: bool,
) -> dict[str, Any]:
    specs: list[BatchRequestSpec] = []
    paper_summaries: dict[str, Any] = {}
    for paper_id in selected_papers:
        key_allowlist = key_map.get(paper_id) if key_map is not None else None
        records = _load_candidates(paper_id, max_records=max_records, key_allowlist=key_allowlist)
        resolution_by_key, resolution_audit = _build_resolution_audit(paper_id, records)
        if write_audits:
            _write_json(_paper_fulltext_resolution_audit_path(run_id, paper_id), resolution_audit)
        eval_outputs = [StageCriteriaEvaluationOutput.model_validate(row) for row in _read_json(_paper_stage1_eval_path(run_id, paper_id))] if _paper_stage1_eval_path(run_id, paper_id).exists() else []
        synth_outputs = [StageSynthesisOutput.model_validate(row) for row in _read_json(_paper_stage1_synthesis_path(run_id, paper_id))] if _paper_stage1_synthesis_path(run_id, paper_id).exists() else []
        eval_by_key = _outputs_by_key(eval_outputs)
        synth_by_key = _outputs_by_key(synth_outputs)
        qa_asset = _load_qa_asset(paper_id, "stage2")
        expected_qids = [str(item["qid"]) for item in qa_asset.get("questions", []) if isinstance(item, dict) and item.get("qid")]
        criteria_text = _criteria_text_for_stage(paper_id, "stage2")
        selected_keys: list[str] = []
        for record in records:
            key = _safe_text(record.get("key"))
            stage1_eval = eval_by_key.get(key)
            if stage1_eval is None:
                continue
            if stage1_eval.decision_recommendation == "exclude":
                continue
            selected_keys.append(key)
            resolution = resolution_by_key[key]
            if resolution["resolution_status"] not in {"exact", "normalized"}:
                continue
            stage1_synth = synth_by_key.get(key)
            if stage1_synth is None:
                continue
            fulltext_text, fulltext_meta = _fulltext_payload_from_resolution(
                resolution,
                head_chars=int(config["fulltext_inline_head_chars"]),
                tail_chars=int(config["fulltext_inline_tail_chars"]),
            )
            title = _safe_text(record.get("title") or record.get("query_title"))
            provenance = _build_source_record_provenance(record, paper_id, resolution)
            context = {
                "WORKFLOW_ARM": WORKFLOW_ARM,
                "PAPER_ID": paper_id,
                "CANDIDATE_KEY": key,
                "CANDIDATE_TITLE": title,
                "QA_ASSET_JSON": _json_text(qa_asset),
                "STAGE_CRITERIA_JSON_CONTENT": criteria_text,
                "METADATA_JSON": _json_text(_metadata_payload(record)),
                "PRIOR_STAGE_EVAL_JSON": _json_text(stage1_eval.model_dump(mode="json")),
                "PRIOR_STAGE_SYNTHESIS_JSON": _json_text(stage1_synth.model_dump(mode="json")),
                "FULLTEXT_RESOLUTION_JSON": _json_text(resolution),
                "FULLTEXT_TEXT": fulltext_text,
                "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.schema_hints["stage2_qa"],
            }
            prompt = render_prompt._render(prompt_assets.templates["stage2_qa"], context, strict=True)
            specs.append(
                BatchRequestSpec(
                    custom_id=_custom_id("stage2_qa", paper_id, key),
                    model=str(config["model"]),
                    body=_build_body(
                        model=str(config["model"]),
                        prompt=prompt,
                        response_model=StageQAOutput,
                        schema_name="StageQAOutput",
                        reasoning_effort=reasoning_effort,
                    ),
                    response_model=StageQAOutput,
                    validator=_make_stage_qa_validator(
                        paper_id=paper_id,
                        stage="stage2",
                        candidate_key=key,
                        candidate_title=title,
                        qa_source_path=f"qa_assets/{paper_id}.stage2.json",
                        expected_qids=expected_qids,
                    ),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": key,
                        "candidate_title": title,
                        "phase": "stage2_qa",
                        "provenance": provenance.model_dump(mode="json"),
                        "fulltext_meta": fulltext_meta,
                        "resolution_status": resolution["resolution_status"],
                    },
                )
            )
        selected_path = _paper_stage2_selection_keys_path(run_id, paper_id)
        selected_path.parent.mkdir(parents=True, exist_ok=True)
        selected_path.write_text("\n".join(selected_keys) + ("\n" if selected_keys else ""), encoding="utf-8")
        paper_summaries[paper_id] = {
            "selected_for_stage2_count": len(selected_keys),
            "request_count": sum(1 for spec in specs if spec.context["paper_id"] == paper_id),
        }
    return {"specs": specs, "paper_summaries": paper_summaries}


def _prepare_stage2_eval_specs(
    *,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    reasoning_effort: str | None,
) -> dict[str, Any]:
    specs: list[BatchRequestSpec] = []
    paper_summaries: dict[str, Any] = {}
    for paper_id in selected_papers:
        stage2_qa_outputs = [StageQAOutput.model_validate(row) for row in _read_jsonl(_paper_stage2_qa_path(run_id, paper_id))] if _paper_stage2_qa_path(run_id, paper_id).exists() else []
        stage1_synth_outputs = [StageSynthesisOutput.model_validate(row) for row in _read_json(_paper_stage1_synthesis_path(run_id, paper_id))] if _paper_stage1_synthesis_path(run_id, paper_id).exists() else []
        stage1_synth_by_key = _outputs_by_key(stage1_synth_outputs)
        synth_outputs: list[StageSynthesisOutput] = []
        for qa_output in stage2_qa_outputs:
            prior = stage1_synth_by_key.get(qa_output.candidate_key)
            synth_outputs.append(_synthesize_from_qa(qa_output, prior_stage_synthesis=prior))
        _write_json(_paper_stage2_synthesis_path(run_id, paper_id), [output.model_dump(mode="json") for output in synth_outputs])
        stage1_eval_outputs = [StageCriteriaEvaluationOutput.model_validate(row) for row in _read_json(_paper_stage1_eval_path(run_id, paper_id))] if _paper_stage1_eval_path(run_id, paper_id).exists() else []
        stage1_eval_by_key = _outputs_by_key(stage1_eval_outputs)
        criteria_text = _criteria_text_for_stage(paper_id, "stage2")
        for synth in synth_outputs:
            field_names = {field.field_name for field in synth.field_records}
            prior_eval = stage1_eval_by_key.get(synth.candidate_key)
            context = {
                "WORKFLOW_ARM": WORKFLOW_ARM,
                "PAPER_ID": paper_id,
                "CANDIDATE_KEY": synth.candidate_key,
                "PRIOR_STAGE_EVAL_JSON": _json_text(prior_eval.model_dump(mode="json")) if prior_eval is not None else "null",
                "SYNTHESIS_JSON": _json_text(synth.model_dump(mode="json")),
                "ALLOWED_EVIDENCE_IDS_JSON": _json_text(sorted(field_names)),
                "STAGE_CRITERIA_JSON_CONTENT": criteria_text,
                "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.schema_hints["stage2_eval"],
            }
            prompt = render_prompt._render(prompt_assets.templates["stage2_eval"], context, strict=True)
            specs.append(
                BatchRequestSpec(
                    custom_id=_custom_id("stage2_eval", paper_id, synth.candidate_key),
                    model=str(config["model"]),
                    body=_build_body(
                        model=str(config["model"]),
                        prompt=prompt,
                        response_model=StageCriteriaEvaluationOutput,
                        schema_name="StageCriteriaEvaluationOutput",
                        reasoning_effort=reasoning_effort,
                    ),
                    response_model=StageCriteriaEvaluationOutput,
                    validator=_make_eval_validator(
                        paper_id=paper_id,
                        stage="stage2",
                        candidate_key=synth.candidate_key,
                        candidate_title=synth.candidate_title,
                        expected_field_names=field_names,
                    ),
                    context={
                        "paper_id": paper_id,
                        "candidate_key": synth.candidate_key,
                        "candidate_title": synth.candidate_title,
                        "phase": "stage2_eval",
                        "provenance": synth.source_record_provenance.model_dump(mode="json"),
                    },
                )
            )
        paper_summaries[paper_id] = {
            "synthesis_count": len(synth_outputs),
            "request_count": sum(1 for spec in specs if spec.context["paper_id"] == paper_id),
        }
    return {"specs": specs, "paper_summaries": paper_summaries}


def _phase_preparation(
    *,
    phase: str,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    write_audits: bool,
) -> dict[str, Any]:
    if phase == "stage1_qa":
        return _prepare_stage1_qa_specs(
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            max_records=max_records,
            reasoning_effort=reasoning_effort,
            write_audits=write_audits,
        )
    if phase == "stage1_eval":
        return _prepare_stage1_eval_specs(
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            reasoning_effort=reasoning_effort,
        )
    if phase == "stage2_qa":
        return _prepare_stage2_qa_specs(
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            max_records=max_records,
            reasoning_effort=reasoning_effort,
            write_audits=write_audits,
        )
    if phase == "stage2_eval":
        return _prepare_stage2_eval_specs(
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            reasoning_effort=reasoning_effort,
        )
    raise ValueError(f"unsupported phase: {phase}")


def _init_run_manifest(
    *,
    run_id: str,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map_path: Path | None,
    max_records: int | None,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "bundle_dir": str(BUNDLE_DIR),
        "manifest_path": str(MANIFEST_PATH),
        "run_manifest_path": str(_run_manifest_path(run_id)),
        "results_root": str(RESULTS_ROOT),
        "run_dir": str(_run_dir(run_id)),
        "model": str(config["model"]),
        "endpoint": str(config["endpoint"]),
        "papers": selected_papers,
        "max_records": max_records,
        "candidate_keys_file": _relative(key_map_path),
        "reasoning_effort": reasoning_effort,
        "phase_jobs": {},
    }


def _load_or_init_run_manifest(
    *,
    run_id: str,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map_path: Path | None,
    max_records: int | None,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    manifest_path = _run_manifest_path(run_id)
    if manifest_path.exists():
        return _read_json(manifest_path)
    manifest = _init_run_manifest(
        run_id=run_id,
        config=config,
        selected_papers=selected_papers,
        key_map_path=key_map_path,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
    )
    _write_json(manifest_path, manifest)
    return manifest


def _load_batch_payload_for_phase(run_id: str, phase: str, model: str) -> dict[str, Any] | None:
    artifact_dir = _batch_artifact_dir(run_id, phase, model)
    for filename in ("batch_latest.json", "batch_create.json"):
        path = artifact_dir / filename
        if path.exists():
            return _read_json(path)
    return None


def _write_phase_outputs(run_id: str, phase: str, paper_id: str, rows: list[dict[str, Any]]) -> None:
    if phase == "stage1_qa":
        _write_jsonl(_paper_stage1_qa_path(run_id, paper_id), rows)
    elif phase == "stage1_eval":
        _write_json(_paper_stage1_eval_path(run_id, paper_id), rows)
    elif phase == "stage2_qa":
        _write_jsonl(_paper_stage2_qa_path(run_id, paper_id), rows)
    elif phase == "stage2_eval":
        _write_json(_paper_stage2_eval_path(run_id, paper_id), rows)
    else:
        raise ValueError(f"unsupported phase: {phase}")


def _submit_phase(
    *,
    phase: str,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    key_map_path: Path | None,
    max_records: int | None,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    _load_env_file()
    _run_dir(run_id).mkdir(parents=True, exist_ok=True)
    run_manifest = _load_or_init_run_manifest(
        run_id=run_id,
        config=config,
        selected_papers=selected_papers,
        key_map_path=key_map_path,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
    )
    prep = _phase_preparation(
        phase=phase,
        run_id=run_id,
        prompt_assets=prompt_assets,
        config=config,
        selected_papers=selected_papers,
        key_map=key_map,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
        write_audits=True,
    )
    specs: list[BatchRequestSpec] = prep["specs"]
    artifact_dir = _batch_artifact_dir(run_id, phase, str(config["model"]))
    if not specs:
        parsed_payload = {
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
        _write_json(artifact_dir / "parsed_results.json", parsed_payload)
        run_manifest["phase_jobs"][phase] = {
            "phase": phase,
            "batch_artifact_dir": str(artifact_dir),
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "request_count": 0,
            "paper_preparation": prep["paper_summaries"],
        }
        _write_json(_run_manifest_path(run_id), run_manifest)
        print(f"[submit:{phase}] no requests", flush=True)
        return run_manifest["phase_jobs"][phase]

    model_id = OpenAI().models.retrieve(str(config["model"])).id
    runner = OpenAIBatchRunner(
        client=OpenAI(),
        poll_interval_sec=float(config["batch_poll_interval_sec"]),
    )
    submit_payload = runner.submit_requests(
        specs=specs,
        endpoint=str(config["endpoint"]),
        artifact_dir=artifact_dir,
        metadata={
            "experiment": WORKFLOW_ARM,
            "phase": phase,
            "run_id": run_id,
            "paper_count": len(selected_papers),
        },
        completion_window=str(config["completion_window"]),
    )
    run_manifest["model_preflight_id"] = model_id
    run_manifest["phase_jobs"][phase] = {
        "phase": phase,
        "batch_artifact_dir": str(artifact_dir),
        "batch_id": submit_payload["batch_create"]["id"],
        "batch_status": submit_payload["batch_create"]["status"],
        "request_count": len(specs),
        "paper_preparation": prep["paper_summaries"],
        "upload_file_id": submit_payload["upload_file"]["id"],
    }
    _write_json(_run_manifest_path(run_id), run_manifest)
    print(f"[submit:{phase}] run_id={run_id}", flush=True)
    print(f"[submit:{phase}] batch_id={submit_payload['batch_create']['id']}", flush=True)
    return run_manifest["phase_jobs"][phase]


def _collect_phase(
    *,
    phase: str,
    run_id: str,
    prompt_assets: PromptAssets,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    reasoning_effort: str | None,
    batch_poll_interval_sec: float | None,
    batch_max_wait_minutes: float | None,
) -> dict[str, Any]:
    _load_env_file()
    run_manifest = _read_json(_run_manifest_path(run_id))
    prep = _phase_preparation(
        phase=phase,
        run_id=run_id,
        prompt_assets=prompt_assets,
        config=config,
        selected_papers=selected_papers,
        key_map=key_map,
        max_records=max_records,
        reasoning_effort=reasoning_effort,
        write_audits=True,
    )
    specs: list[BatchRequestSpec] = prep["specs"]
    artifact_dir = _batch_artifact_dir(run_id, phase, str(config["model"]))
    batch_payload = _load_batch_payload_for_phase(run_id, phase, str(config["model"]))
    if batch_payload is None or batch_payload.get("id") is None:
        parsed_payload = _read_json(artifact_dir / "parsed_results.json") if (artifact_dir / "parsed_results.json").exists() else {
            "batch_id": None,
            "batch_status": "skipped_no_requests",
            "successes": [],
            "failures": [],
            "missing": [],
            "output_row_count": 0,
            "error_row_count": 0,
        }
    else:
        runner = OpenAIBatchRunner(
            client=OpenAI(),
            poll_interval_sec=float(batch_poll_interval_sec or config["batch_poll_interval_sec"]),
        )
        batch_payload = runner.wait_until_terminal(
            str(batch_payload["id"]),
            artifact_dir=artifact_dir,
            max_wait_minutes=float(batch_max_wait_minutes or config["batch_max_wait_minutes"]),
        )
        parsed_payload = runner.collect_results(specs=specs, batch_payload=batch_payload, artifact_dir=artifact_dir)
        run_manifest["phase_jobs"].setdefault(phase, {})
        run_manifest["phase_jobs"][phase].update(
            {
                "batch_status": batch_payload.get("status"),
                "batch_completed_at": batch_payload.get("completed_at"),
                "batch_output_file_id": batch_payload.get("output_file_id"),
                "batch_error_file_id": batch_payload.get("error_file_id"),
            }
        )

    success_by_id = {item["custom_id"]: item for item in parsed_payload["successes"]}
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for spec in specs:
        item = success_by_id.get(spec.custom_id)
        if item is None:
            continue
        rows_by_paper[spec.context["paper_id"]].append(item["parsed"])

    for paper_id in selected_papers:
        _write_phase_outputs(run_id, phase, paper_id, rows_by_paper.get(paper_id, []))

    run_manifest["phase_jobs"].setdefault(phase, {})
    run_manifest["phase_jobs"][phase]["parsed_summary"] = {
        "success_count": len(parsed_payload["successes"]),
        "failure_count": len(parsed_payload["failures"]),
        "missing_count": len(parsed_payload["missing"]),
    }
    _write_json(_run_manifest_path(run_id), run_manifest)
    print(f"[collect:{phase}] run_id={run_id}", flush=True)
    print(f"[collect:{phase}] batch_status={parsed_payload.get('batch_status')}", flush=True)
    return parsed_payload


def _phase_issue_by_key(run_id: str, phase: str) -> dict[str, dict[str, dict[str, Any]]]:
    artifact_dir = _batch_artifact_dir(run_id, phase, str(_load_config()["model"]))
    path = artifact_dir / "parsed_results.json"
    if not path.exists():
        return {}
    payload = _read_json(path)
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for status_name, review_state in (("failures", "batch_error"), ("missing", "batch_missing")):
        for item in payload.get(status_name, []):
            context = item.get("context") or {}
            paper_id = str(context.get("paper_id") or "")
            candidate_key = str(context.get("candidate_key") or "")
            if not paper_id or not candidate_key:
                continue
            out[paper_id][candidate_key] = {
                "review_state": review_state,
                "failed_phase": phase,
                "review_output": item,
            }
    success_ids = {str(item.get("custom_id") or "") for item in payload.get("successes", [])}
    for item in payload.get("missing", []):
        custom_id = str(item.get("custom_id") or "")
        if custom_id in success_ids:
            continue
    return out


def _build_error_final_row(
    *,
    paper_id: str,
    record: dict[str, Any],
    provenance: SourceRecordProvenance,
    review_state: str,
    failed_phase: str,
    review_output: dict[str, Any] | None,
    discard_reason: str | None = None,
) -> SingleReviewerFinalRow:
    return SingleReviewerFinalRow(
        key=_safe_text(record.get("key")),
        title=_safe_text(record.get("title") or record.get("query_title")),
        paper_id=paper_id,
        workflow_arm=WORKFLOW_ARM,
        stage_model=WORKFLOW_STAGE_MODEL,
        review_state=review_state,
        review_skipped=False,
        failed_phase=failed_phase,
        discard_reason=discard_reason or review_state,
        final_verdict=f"maybe (review_state:{review_state})",
        source_record_provenance=provenance,
        review_output=review_output,
        fulltext_source_path=provenance.fulltext_candidate_path,
        fulltext_resolution_status=None,
    )


def _build_cutoff_row(
    *,
    paper_id: str,
    record: dict[str, Any],
    decision: dict[str, Any],
) -> SingleReviewerFinalRow:
    base = cutoff_time_filter.build_cutoff_excluded_row(record, decision=decision)
    return SingleReviewerFinalRow(
        key=_safe_text(base["key"]),
        title=_safe_text(base["title"]),
        paper_id=paper_id,
        workflow_arm=WORKFLOW_ARM,
        stage_model=WORKFLOW_STAGE_MODEL,
        review_state=str(base["review_state"]),
        review_skipped=bool(base["review_skipped"]),
        discard_reason=str(base["discard_reason"]),
        final_verdict=str(base["final_verdict"]),
        review_output={"cutoff_filter": base["cutoff_filter"]},
    )


def _assemble_results_and_metrics(
    *,
    run_id: str,
    config: dict[str, Any],
    selected_papers: list[str],
    key_map: dict[str, set[str]] | None,
    max_records: int | None,
    report_reasoning_effort: str | None,
) -> dict[str, Any]:
    baseline = _read_json(RESULTS_MANIFEST_PATH)["papers"]
    stage1_issue_by_paper = _phase_issue_by_key(run_id, "stage1_qa")
    stage1_eval_issue_by_paper = _phase_issue_by_key(run_id, "stage1_eval")
    stage2_qa_issue_by_paper = _phase_issue_by_key(run_id, "stage2_qa")
    stage2_eval_issue_by_paper = _phase_issue_by_key(run_id, "stage2_eval")
    summaries: list[dict[str, Any]] = []

    for paper_id in selected_papers:
        key_allowlist = key_map.get(paper_id) if key_map is not None else None
        records = _load_candidates(paper_id, max_records=max_records, key_allowlist=key_allowlist)
        cutoff_result = _load_cutoff_result(paper_id=paper_id, records=records)
        _write_json(_paper_cutoff_audit_path(run_id, paper_id), cutoff_result["audit_payload"])
        resolution_by_key, resolution_audit = _build_resolution_audit(paper_id, records)
        _write_json(_paper_fulltext_resolution_audit_path(run_id, paper_id), resolution_audit)

        stage1_eval_outputs = [StageCriteriaEvaluationOutput.model_validate(row) for row in (_read_json(_paper_stage1_eval_path(run_id, paper_id)) if _paper_stage1_eval_path(run_id, paper_id).exists() else [])]
        stage1_synth_outputs = [StageSynthesisOutput.model_validate(row) for row in (_read_json(_paper_stage1_synthesis_path(run_id, paper_id)) if _paper_stage1_synthesis_path(run_id, paper_id).exists() else [])]
        stage2_eval_outputs = [StageCriteriaEvaluationOutput.model_validate(row) for row in (_read_json(_paper_stage2_eval_path(run_id, paper_id)) if _paper_stage2_eval_path(run_id, paper_id).exists() else [])]
        stage2_synth_outputs = [StageSynthesisOutput.model_validate(row) for row in (_read_json(_paper_stage2_synthesis_path(run_id, paper_id)) if _paper_stage2_synthesis_path(run_id, paper_id).exists() else [])]
        stage1_eval_by_key = _outputs_by_key(stage1_eval_outputs)
        stage1_synth_by_key = _outputs_by_key(stage1_synth_outputs)
        stage2_eval_by_key = _outputs_by_key(stage2_eval_outputs)
        stage2_synth_by_key = _outputs_by_key(stage2_synth_outputs)

        rows: list[dict[str, Any]] = []
        reviewed_count = 0
        missing_count = 0
        for record in records:
            key = _safe_text(record.get("key"))
            decision = cutoff_result["decisions_by_key"][key]
            resolution = resolution_by_key[key]
            provenance = _build_source_record_provenance(record, paper_id, resolution)
            if not decision["cutoff_pass"]:
                rows.append(_build_cutoff_row(paper_id=paper_id, record=record, decision=decision).model_dump(mode="json"))
                continue
            stage1_issue = stage1_issue_by_paper.get(paper_id, {}).get(key)
            if stage1_issue is not None:
                rows.append(
                    _build_error_final_row(
                        paper_id=paper_id,
                        record=record,
                        provenance=provenance,
                        review_state=stage1_issue["review_state"],
                        failed_phase="stage1_qa",
                        review_output=stage1_issue["review_output"],
                    ).model_dump(mode="json")
                )
                continue
            stage1_eval_issue = stage1_eval_issue_by_paper.get(paper_id, {}).get(key)
            if stage1_eval_issue is not None or key not in stage1_eval_by_key:
                rows.append(
                    _build_error_final_row(
                        paper_id=paper_id,
                        record=record,
                        provenance=provenance,
                        review_state=(stage1_eval_issue or {}).get("review_state", "batch_unmapped"),
                        failed_phase="stage1_eval",
                        review_output=(stage1_eval_issue or {}).get("review_output"),
                    ).model_dump(mode="json")
                )
                continue

            stage1_eval = stage1_eval_by_key[key]
            stage1_synth = stage1_synth_by_key.get(key)
            stage1_verdict = _stage_verdict("stage1", stage1_eval.stage_score)
            if stage1_eval.decision_recommendation == "exclude":
                reviewed_count += 1
                rows.append(
                    SingleReviewerFinalRow(
                        key=key,
                        title=_safe_text(record.get("title") or record.get("query_title")),
                        paper_id=paper_id,
                        workflow_arm=WORKFLOW_ARM,
                        stage_model=WORKFLOW_STAGE_MODEL,
                        review_state="reviewed",
                        review_skipped=False,
                        final_verdict=stage1_verdict,
                        stage1_stage_score=stage1_eval.stage_score,
                        stage1_decision_recommendation=stage1_eval.decision_recommendation,
                        stage1_eval_path=_relative(_paper_stage1_eval_path(run_id, paper_id)),
                        stage1_synthesis_path=_relative(_paper_stage1_synthesis_path(run_id, paper_id)),
                        source_record_provenance=provenance,
                        review_output=stage1_eval.model_dump(mode="json"),
                        fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                        fulltext_resolution_status=resolution["resolution_status"],
                    ).model_dump(mode="json")
                )
                continue

            if resolution["resolution_status"] not in {"exact", "normalized"}:
                missing_count += 1
                rows.append(
                    SingleReviewerFinalRow(
                        key=key,
                        title=_safe_text(record.get("title") or record.get("query_title")),
                        paper_id=paper_id,
                        workflow_arm=WORKFLOW_ARM,
                        stage_model=WORKFLOW_STAGE_MODEL,
                        review_state="missing",
                        review_skipped=True,
                        discard_reason="fulltext_missing",
                        final_verdict=stage1_verdict,
                        stage1_stage_score=stage1_eval.stage_score,
                        stage1_decision_recommendation=stage1_eval.decision_recommendation,
                        stage1_eval_path=_relative(_paper_stage1_eval_path(run_id, paper_id)),
                        stage1_synthesis_path=_relative(_paper_stage1_synthesis_path(run_id, paper_id)),
                        source_record_provenance=provenance,
                        review_output={
                            "fulltext_missing_or_unmatched": True,
                            "resolution": resolution,
                            "stage1_eval": stage1_eval.model_dump(mode="json"),
                        },
                        fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                        fulltext_resolution_status=resolution["resolution_status"],
                    ).model_dump(mode="json")
                )
                continue

            stage2_issue = stage2_qa_issue_by_paper.get(paper_id, {}).get(key)
            if stage2_issue is not None:
                rows.append(
                    _build_error_final_row(
                        paper_id=paper_id,
                        record=record,
                        provenance=provenance,
                        review_state=stage2_issue["review_state"],
                        failed_phase="stage2_qa",
                        review_output=stage2_issue["review_output"],
                    ).model_dump(mode="json")
                )
                continue
            stage2_eval_issue = stage2_eval_issue_by_paper.get(paper_id, {}).get(key)
            if stage2_eval_issue is not None or key not in stage2_eval_by_key:
                rows.append(
                    _build_error_final_row(
                        paper_id=paper_id,
                        record=record,
                        provenance=provenance,
                        review_state=(stage2_eval_issue or {}).get("review_state", "batch_unmapped"),
                        failed_phase="stage2_eval",
                        review_output=(stage2_eval_issue or {}).get("review_output"),
                    ).model_dump(mode="json")
                )
                continue

            stage2_eval = stage2_eval_by_key[key]
            stage2_synth = stage2_synth_by_key.get(key)
            reviewed_count += 1
            rows.append(
                SingleReviewerFinalRow(
                    key=key,
                    title=_safe_text(record.get("title") or record.get("query_title")),
                    paper_id=paper_id,
                    workflow_arm=WORKFLOW_ARM,
                    stage_model=WORKFLOW_STAGE_MODEL,
                    review_state="reviewed",
                    review_skipped=False,
                    final_verdict=_stage_verdict("stage2", stage2_eval.stage_score),
                    stage1_stage_score=stage1_eval.stage_score,
                    stage1_decision_recommendation=stage1_eval.decision_recommendation,
                    stage2_stage_score=stage2_eval.stage_score,
                    stage2_decision_recommendation=stage2_eval.decision_recommendation,
                    stage1_eval_path=_relative(_paper_stage1_eval_path(run_id, paper_id)),
                    stage2_eval_path=_relative(_paper_stage2_eval_path(run_id, paper_id)),
                    stage1_synthesis_path=_relative(_paper_stage1_synthesis_path(run_id, paper_id)),
                    stage2_synthesis_path=_relative(_paper_stage2_synthesis_path(run_id, paper_id)),
                    source_record_provenance=provenance,
                    review_output={
                        "stage1_eval": stage1_eval.model_dump(mode="json"),
                        "stage1_synthesis": stage1_synth.model_dump(mode="json") if stage1_synth is not None else None,
                        "stage2_eval": stage2_eval.model_dump(mode="json"),
                        "stage2_synthesis": stage2_synth.model_dump(mode="json") if stage2_synth is not None else None,
                    },
                    fulltext_source_path=resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
                    fulltext_resolution_status=resolution["resolution_status"],
                ).model_dump(mode="json")
            )

        _write_json(_paper_results_path(run_id, paper_id), rows)
        eval_cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
            paper_id,
            "--results",
            str(_paper_results_path(run_id, paper_id)),
            "--gold-metadata",
            str(_paper_gold_path(paper_id)),
            "--positive-mode",
            "include_or_maybe",
            "--save-report",
            str(_paper_metrics_path(run_id, paper_id)),
        ]
        keys_path = _paper_eval_keys_path(run_id, paper_id)
        if keys_path.exists():
            eval_cmd.extend(["--keys-file", str(keys_path)])
        subprocess.run(eval_cmd, check=True, cwd=str(REPO_ROOT))
        metrics = _read_json(_paper_metrics_path(run_id, paper_id))
        baseline_combined = float(baseline[paper_id]["current_metrics"]["combined"]["f1"])
        selected_keys = _paper_stage2_selection_keys_path(run_id, paper_id)
        selected_count = 0
        if selected_keys.exists():
            selected_count = len([line for line in selected_keys.read_text(encoding="utf-8").splitlines() if line.strip()])
        summaries.append(
            {
                "paper_id": paper_id,
                "candidate_total": len(records),
                "cutoff_pass_count": cutoff_result["audit_payload"]["candidate_total_after_cutoff"],
                "cutoff_excluded_count": cutoff_result["audit_payload"]["cutoff_excluded_count"],
                "stage2_selected_count": selected_count,
                "reviewed_count": reviewed_count,
                "missing_count": missing_count,
                "results_path": _relative(_paper_results_path(run_id, paper_id)),
                "metrics_path": _relative(_paper_metrics_path(run_id, paper_id)),
                "precision": float(metrics["metrics"]["precision"]),
                "recall": float(metrics["metrics"]["recall"]),
                "f1": float(metrics["metrics"]["f1"]),
                "delta_vs_current_combined": float(metrics["metrics"]["f1"]) - baseline_combined,
            }
        )

    run_manifest = _read_json(_run_manifest_path(run_id))
    run_manifest["mode"] = "collect"
    run_manifest["reasoning_effort"] = report_reasoning_effort
    run_manifest["baseline"] = {
        paper_id: {
            "combined": {
                "path": baseline[paper_id]["current_metrics"]["combined"]["path"],
                "f1": float(baseline[paper_id]["current_metrics"]["combined"]["f1"]),
            }
        }
        for paper_id in selected_papers
    }
    run_manifest["summaries"] = summaries
    _write_json(_run_manifest_path(run_id), run_manifest)
    _report_path(run_id).write_text(_build_report_zh(run_manifest), encoding="utf-8")
    return run_manifest


def _build_report_zh(run_manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# 單審查者官方 Batch 2-Stage QA")
    lines.append("")
    lines.append(f"- `run_id`：`{run_manifest['run_id']}`")
    lines.append(f"- model：`{run_manifest['model']}`")
    lines.append(f"- reasoning_effort：`{run_manifest.get('reasoning_effort') or '未顯式設定'}`")
    lines.append(f"- endpoint：`{run_manifest['endpoint']}`")
    lines.append("")
    lines.append("## 指標")
    lines.append("")
    lines.append("| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for summary in run_manifest.get("summaries", []):
        lines.append(
            f"| `{summary['paper_id']}` | {summary['candidate_total']} | {summary['cutoff_pass_count']} | "
            f"{summary['stage2_selected_count']} | {summary['reviewed_count']} | {summary['missing_count']} | "
            f"{summary['f1']:.4f} | {summary['delta_vs_current_combined']:+.4f} | "
            f"{summary['precision']:.4f} | {summary['recall']:.4f} |"
        )
    lines.append("")
    lines.append("## Phase Jobs")
    lines.append("")
    lines.append("| Phase | Request count | Batch status | Success | Failure | Missing |")
    lines.append("| --- | ---: | --- | ---: | ---: | ---: |")
    for phase in PHASES:
        job = run_manifest.get("phase_jobs", {}).get(phase, {})
        parsed = job.get("parsed_summary", {})
        lines.append(
            f"| `{phase}` | {int(job.get('request_count') or 0)} | `{job.get('batch_status')}` | "
            f"{int(parsed.get('success_count') or 0)} | {int(parsed.get('failure_count') or 0)} | {int(parsed.get('missing_count') or 0)} |"
        )
    return "\n".join(lines) + "\n"


def _model_preflight(model: str) -> str:
    _load_env_file()
    client = OpenAI()
    model_info = client.models.retrieve(model)
    return getattr(model_info, "id", None) or model


def _sample_provenance(paper_id: str, candidate_key: str, candidate_title: str) -> SourceRecordProvenance:
    resolution = {
        "resolution_status": "exact",
        "exact_candidate_path": f"refs/{paper_id}/mds/{candidate_key}.md",
    }
    return SourceRecordProvenance(
        record_key=candidate_key,
        record_title=candidate_title,
        source="sample",
        source_id="sample",
        metadata_path=str(_paper_metadata_path(paper_id).relative_to(REPO_ROOT)),
        runtime_prompts_path=str(_runtime_prompts_path().relative_to(REPO_ROOT)),
        criteria_stage1_path=str(_paper_stage1_criteria_path(paper_id).relative_to(REPO_ROOT)),
        criteria_stage2_path=str(_paper_stage2_criteria_path(paper_id).relative_to(REPO_ROOT)),
        fulltext_candidate_path=str(resolution["exact_candidate_path"]),
        fulltext_available=True,
    )


def build_serialization_probe(phase: str) -> dict[str, Any]:
    config = _load_config()
    prompt_assets = PromptAssets()
    if phase == "stage1_qa":
        key_map = _load_candidate_key_map(BUNDLE_DIR / "smoke" / "smoke_candidates.json", selected_papers=["2409.13738"])
        prep = _prepare_stage1_qa_specs(
            run_id="serialization_probe",
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=["2409.13738"],
            key_map=key_map,
            max_records=None,
            reasoning_effort="low",
            write_audits=False,
        )
        spec = prep["specs"][0]
    elif phase == "stage1_eval":
        sample_qa = StageQAOutput.model_validate(_read_json(BUNDLE_DIR / "samples" / "stage1_qa_output.sample.json"))
        synth = _synthesize_from_qa(sample_qa)
        paper_id = synth.paper_id
        field_names = {field.field_name for field in synth.field_records}
        context = {
            "WORKFLOW_ARM": WORKFLOW_ARM,
            "PAPER_ID": paper_id,
            "CANDIDATE_KEY": synth.candidate_key,
            "SYNTHESIS_JSON": _json_text(synth.model_dump(mode="json")),
            "ALLOWED_EVIDENCE_IDS_JSON": _json_text(sorted(field_names)),
            "STAGE_CRITERIA_JSON_CONTENT": _criteria_text_for_stage(paper_id, "stage1"),
            "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.schema_hints["stage1_eval"],
        }
        prompt = render_prompt._render(prompt_assets.templates["stage1_eval"], context, strict=True)
        spec = BatchRequestSpec(
            custom_id="probe_stage1_eval",
            model=str(config["model"]),
            body=_build_body(
                model=str(config["model"]),
                prompt=prompt,
                response_model=StageCriteriaEvaluationOutput,
                schema_name="StageCriteriaEvaluationOutput",
                reasoning_effort="low",
            ),
            response_model=StageCriteriaEvaluationOutput,
            context={"phase": "stage1_eval"},
        )
    elif phase == "stage2_qa":
        paper_id = "2511.13936"
        candidate_key = "han2020ordinal"
        record = next(row for row in _load_candidates(paper_id, key_allowlist={candidate_key}) if _safe_text(row.get("key")) == candidate_key)
        resolution_by_key, _ = _build_resolution_audit(paper_id, [record])
        resolution = resolution_by_key[candidate_key]
        provenance = _build_source_record_provenance(record, paper_id, resolution)
        fulltext_text, _ = _fulltext_payload_from_resolution(
            resolution,
            head_chars=int(config["fulltext_inline_head_chars"]),
            tail_chars=int(config["fulltext_inline_tail_chars"]),
        )
        prior_synth = StageSynthesisOutput(
            paper_id=paper_id,
            candidate_key=candidate_key,
            candidate_title=_safe_text(record.get("title") or record.get("query_title")),
            stage="stage1",
            workflow_arm=WORKFLOW_ARM,
            source_record_provenance=provenance,
            prior_stage_reference=PriorStageReference(stage="stage1", available=False),
            field_records=[
                FieldRecord(
                    field_name="preference_learning_signal",
                    state="present",
                    state_basis="direct_support",
                    normalized_value=None,
                    supporting_quotes=[],
                    locations=[],
                    missingness_reason=None,
                    conflict_note=None,
                    derived_from_qids=["S1_PREF_SIGNAL"],
                    stage_handoff_status="current_stage_only",
                    support_source_kind="current_stage_qa",
                )
            ],
        )
        prior_eval = StageCriteriaEvaluationOutput(
            paper_id=paper_id,
            candidate_key=candidate_key,
            candidate_title=_safe_text(record.get("title") or record.get("query_title")),
            stage="stage1",
            workflow_arm=WORKFLOW_ARM,
            source_record_provenance=provenance,
            stage_score=4,
            scoring_basis="clear_include",
            decision_recommendation="include",
            positive_fit_evidence_ids=["preference_learning_signal"],
            direct_negative_evidence_ids=[],
            unresolved_core_evidence_ids=[],
            deferred_core_evidence_ids=[],
            criterion_mapping=[],
            criterion_conflicts=[],
            decision_rationale="probe",
            manual_review_needed=False,
            routing_note="probe",
        )
        qa_asset = _load_qa_asset(paper_id, "stage2")
        context = {
            "WORKFLOW_ARM": WORKFLOW_ARM,
            "PAPER_ID": paper_id,
            "CANDIDATE_KEY": candidate_key,
            "CANDIDATE_TITLE": _safe_text(record.get("title") or record.get("query_title")),
            "QA_ASSET_JSON": _json_text(qa_asset),
            "STAGE_CRITERIA_JSON_CONTENT": _criteria_text_for_stage(paper_id, "stage2"),
            "METADATA_JSON": _json_text(_metadata_payload(record)),
            "PRIOR_STAGE_EVAL_JSON": _json_text(prior_eval.model_dump(mode="json")),
            "PRIOR_STAGE_SYNTHESIS_JSON": _json_text(prior_synth.model_dump(mode="json")),
            "FULLTEXT_RESOLUTION_JSON": _json_text(resolution),
            "FULLTEXT_TEXT": fulltext_text,
            "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.schema_hints["stage2_qa"],
        }
        prompt = render_prompt._render(prompt_assets.templates["stage2_qa"], context, strict=True)
        spec = BatchRequestSpec(
            custom_id="probe_stage2_qa",
            model=str(config["model"]),
            body=_build_body(
                model=str(config["model"]),
                prompt=prompt,
                response_model=StageQAOutput,
                schema_name="StageQAOutput",
                reasoning_effort="low",
            ),
            response_model=StageQAOutput,
            context={"phase": "stage2_qa"},
        )
    elif phase == "stage2_eval":
        sample_qa = StageQAOutput.model_validate(_read_json(BUNDLE_DIR / "samples" / "stage2_qa_output.sample.json"))
        prior_synth = StageSynthesisOutput(
            paper_id=sample_qa.paper_id,
            candidate_key=sample_qa.candidate_key,
            candidate_title=sample_qa.candidate_title,
            stage="stage1",
            workflow_arm=WORKFLOW_ARM,
            source_record_provenance=sample_qa.source_record_provenance,
            prior_stage_reference=PriorStageReference(stage="stage1", available=False),
            field_records=[],
        )
        synth = _synthesize_from_qa(sample_qa, prior_stage_synthesis=prior_synth)
        prior_eval = StageCriteriaEvaluationOutput(
            paper_id=sample_qa.paper_id,
            candidate_key=sample_qa.candidate_key,
            candidate_title=sample_qa.candidate_title,
            stage="stage1",
            workflow_arm=WORKFLOW_ARM,
            source_record_provenance=sample_qa.source_record_provenance,
            stage_score=4,
            scoring_basis="clear_include",
            decision_recommendation="include",
            positive_fit_evidence_ids=[],
            direct_negative_evidence_ids=[],
            unresolved_core_evidence_ids=[],
            deferred_core_evidence_ids=[],
            criterion_mapping=[],
            criterion_conflicts=[],
            decision_rationale="probe",
            manual_review_needed=False,
            routing_note="probe",
        )
        context = {
            "WORKFLOW_ARM": WORKFLOW_ARM,
            "PAPER_ID": sample_qa.paper_id,
            "CANDIDATE_KEY": sample_qa.candidate_key,
            "PRIOR_STAGE_EVAL_JSON": _json_text(prior_eval.model_dump(mode="json")),
            "SYNTHESIS_JSON": _json_text(synth.model_dump(mode="json")),
            "ALLOWED_EVIDENCE_IDS_JSON": _json_text(sorted(field.field_name for field in synth.field_records)),
            "STAGE_CRITERIA_JSON_CONTENT": _criteria_text_for_stage(sample_qa.paper_id, "stage2"),
            "RESPONSE_SCHEMA_HINT_JSON": prompt_assets.schema_hints["stage2_eval"],
        }
        prompt = render_prompt._render(prompt_assets.templates["stage2_eval"], context, strict=True)
        spec = BatchRequestSpec(
            custom_id="probe_stage2_eval",
            model=str(config["model"]),
            body=_build_body(
                model=str(config["model"]),
                prompt=prompt,
                response_model=StageCriteriaEvaluationOutput,
                schema_name="StageCriteriaEvaluationOutput",
                reasoning_effort="low",
            ),
            response_model=StageCriteriaEvaluationOutput,
            context={"phase": "stage2_eval"},
        )
    else:
        raise ValueError(f"unsupported phase: {phase}")

    runner = OpenAIBatchRunner(client=object(), poll_interval_sec=float(config["batch_poll_interval_sec"]))
    return runner.serialize_requests([spec], endpoint=str(config["endpoint"]))[0]


def main() -> int:
    config = _load_config()
    parser = argparse.ArgumentParser(description="執行 single reviewer official-batch 2-stage QA。")
    parser.add_argument("--mode", choices=["submit", "collect", "run"], required=True)
    parser.add_argument("--phase", choices=[*PHASES, "all"], required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--papers", nargs="*", choices=list(config["papers"]), default=list(config["papers"]))
    parser.add_argument("--candidate-keys-file", type=Path, default=None)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--batch-poll-interval-sec", type=float, default=None)
    parser.add_argument("--batch-max-wait-minutes", type=float, default=None)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default=None)
    args = parser.parse_args()

    if args.mode in {"submit", "collect"} and args.phase == "all":
        raise SystemExit("--mode submit/collect 不支援 --phase all")
    prompt_assets = PromptAssets()

    selected_papers = list(args.papers or config["papers"])
    key_map = _load_candidate_key_map(args.candidate_keys_file, selected_papers=selected_papers)
    reasoning_effort = args.reasoning_effort
    run_id = args.run_id or _now_run_id()

    if args.mode == "submit":
        _submit_phase(
            phase=args.phase,
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            key_map_path=args.candidate_keys_file,
            max_records=args.max_records,
            reasoning_effort=reasoning_effort,
        )
        return 0

    if args.mode == "collect":
        _collect_phase(
            phase=args.phase,
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            max_records=args.max_records,
            reasoning_effort=reasoning_effort,
            batch_poll_interval_sec=args.batch_poll_interval_sec,
            batch_max_wait_minutes=args.batch_max_wait_minutes,
        )
        if args.phase == "stage2_eval":
            _assemble_results_and_metrics(
                run_id=run_id,
                config=config,
                selected_papers=selected_papers,
                key_map=key_map,
                max_records=args.max_records,
                report_reasoning_effort=reasoning_effort,
            )
        return 0

    if args.phase != "all":
        _submit_phase(
            phase=args.phase,
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            key_map_path=args.candidate_keys_file,
            max_records=args.max_records,
            reasoning_effort=reasoning_effort,
        )
        _collect_phase(
            phase=args.phase,
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            max_records=args.max_records,
            reasoning_effort=reasoning_effort,
            batch_poll_interval_sec=args.batch_poll_interval_sec,
            batch_max_wait_minutes=args.batch_max_wait_minutes,
        )
        if args.phase == "stage2_eval":
            _assemble_results_and_metrics(
                run_id=run_id,
                config=config,
                selected_papers=selected_papers,
                key_map=key_map,
                max_records=args.max_records,
                report_reasoning_effort=reasoning_effort,
            )
        return 0

    for phase in PHASES:
        _submit_phase(
            phase=phase,
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            key_map_path=args.candidate_keys_file,
            max_records=args.max_records,
            reasoning_effort=reasoning_effort,
        )
        _collect_phase(
            phase=phase,
            run_id=run_id,
            prompt_assets=prompt_assets,
            config=config,
            selected_papers=selected_papers,
            key_map=key_map,
            max_records=args.max_records,
            reasoning_effort=reasoning_effort,
            batch_poll_interval_sec=args.batch_poll_interval_sec,
            batch_max_wait_minutes=args.batch_max_wait_minutes,
        )

    _assemble_results_and_metrics(
        run_id=run_id,
        config=config,
        selected_papers=selected_papers,
        key_map=key_map,
        max_records=args.max_records,
        report_reasoning_effort=reasoning_effort,
    )
    print(f"[run] run_id={run_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
