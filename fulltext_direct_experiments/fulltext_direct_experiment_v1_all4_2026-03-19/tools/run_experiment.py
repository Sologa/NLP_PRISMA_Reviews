#!/usr/bin/env python3
"""Run the four-paper fulltext-direct / stage2-direct non-QA baseline."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
try:
    from tqdm.auto import tqdm
except ModuleNotFoundError:  # pragma: no cover
    tqdm = None

if TYPE_CHECKING:
    from openai import AsyncOpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]

sys.path.insert(0, str(SCRIPT_DIR))
import render_prompt  # noqa: E402


RESULTS_ROOT = REPO_ROOT / "screening" / "results" / "fulltext_direct_v1_all4_2026-03-19"
PAPERS = ("2307.05527", "2409.13738", "2511.13936", "2601.19926")
WORKFLOW_ARM = "fulltext-direct"
WORKFLOW_STAGE = "stage2-direct"
JUNIOR_MODELS = (
    ("JuniorNano", "gpt-5-nano"),
    ("JuniorMini", "gpt-4.1-mini"),
)
SENIOR_MODEL = "gpt-5-mini"
FULLTEXT_INLINE_HEAD_CHARS = 24000
FULLTEXT_INLINE_TAIL_CHARS = 12000
FULLTEXT_TRUNCATION_MARKER = "\n\n...[TRUNCATED MIDDLE]...\n\n"
RETRY_ATTEMPTS = 5
SENTINEL_PATTERN = re.compile(r"__[A-Z0-9_]+__")

CURRENT_AUTHORITY = {
    "2307.05527": {
        "authority_label": "latest fully benchmarked senior_no_marker",
        "stage1_path": REPO_ROOT / "screening" / "results" / "2307.05527_full" / "review_after_stage1_senior_no_marker_report.json",
        "combined_path": REPO_ROOT / "screening" / "results" / "2307.05527_full" / "combined_after_fulltext_senior_no_marker_report.json",
    },
    "2409.13738": {
        "authority_label": "stage_split_criteria_migration",
        "stage1_path": REPO_ROOT / "screening" / "results" / "2409.13738_full" / "stage1_f1.stage_split_criteria_migration.json",
        "combined_path": REPO_ROOT / "screening" / "results" / "2409.13738_full" / "combined_f1.stage_split_criteria_migration.json",
    },
    "2511.13936": {
        "authority_label": "stage_split_criteria_migration",
        "stage1_path": REPO_ROOT / "screening" / "results" / "2511.13936_full" / "stage1_f1.stage_split_criteria_migration.json",
        "combined_path": REPO_ROOT / "screening" / "results" / "2511.13936_full" / "combined_f1.stage_split_criteria_migration.json",
    },
    "2601.19926": {
        "authority_label": "latest fully benchmarked senior_no_marker",
        "stage1_path": REPO_ROOT / "screening" / "results" / "2601.19926_full" / "review_after_stage1_senior_no_marker_report.json",
        "combined_path": REPO_ROOT / "screening" / "results" / "2601.19926_full" / "combined_after_fulltext_senior_no_marker_report.json",
    },
}

QA_FIRST_COMPARISON_SOURCES = (
    {
        "paper_id": "2409.13738",
        "label": "v0 qa-only",
        "manifest_path": REPO_ROOT / "screening" / "results" / "qa_first_v0_2409_2511_2026-03-18" / "run_manifest.json",
        "arm": "qa-only",
    },
    {
        "paper_id": "2409.13738",
        "label": "v0 qa+synthesis",
        "manifest_path": REPO_ROOT / "screening" / "results" / "qa_first_v0_2409_2511_2026-03-18" / "run_manifest.json",
        "arm": "qa+synthesis",
    },
    {
        "paper_id": "2409.13738",
        "label": "v1 second-pass qa+synthesis",
        "manifest_path": REPO_ROOT / "screening" / "results" / "qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19" / "run_manifest.json",
        "arm": "qa+synthesis",
    },
    {
        "paper_id": "2409.13738",
        "label": "v1 final ablation qa+synthesis",
        "manifest_path": REPO_ROOT / "screening" / "results" / "qa_first_v1_2409_stage2_final_ablation_2026-03-19" / "run_manifest.json",
        "arm": "qa+synthesis",
    },
    {
        "paper_id": "2511.13936",
        "label": "v0 qa-only",
        "manifest_path": REPO_ROOT / "screening" / "results" / "qa_first_v0_2409_2511_2026-03-18" / "run_manifest.json",
        "arm": "qa-only",
    },
    {
        "paper_id": "2511.13936",
        "label": "v0 qa+synthesis",
        "manifest_path": REPO_ROOT / "screening" / "results" / "qa_first_v0_2409_2511_2026-03-18" / "run_manifest.json",
        "arm": "qa+synthesis",
    },
    {
        "paper_id": "2511.13936",
        "label": "v1 second-pass qa+synthesis",
        "manifest_path": REPO_ROOT / "screening" / "results" / "qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19" / "run_manifest.json",
        "arm": "qa+synthesis",
    },
)


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


class JuniorReviewOutput(_StrictModel):
    paper_id: str
    candidate_key: str
    candidate_title: str
    workflow_arm: Literal["fulltext-direct"]
    stage: Literal["stage2-direct"]
    source_record_provenance: SourceRecordProvenance
    stage_score: int = Field(ge=1, le=5)
    decision_recommendation: Literal["include", "exclude", "maybe"]
    satisfied_inclusion_points: list[str] = Field(default_factory=list)
    triggered_exclusion_points: list[str] = Field(default_factory=list)
    uncertain_points: list[str] = Field(default_factory=list)
    evidence_highlights: list[str] = Field(default_factory=list)
    decision_rationale: str


class SeniorReviewOutput(_StrictModel):
    paper_id: str
    candidate_key: str
    candidate_title: str
    workflow_arm: Literal["fulltext-direct"]
    stage: Literal["stage2-direct"]
    source_record_provenance: SourceRecordProvenance
    senior_stage_score: int = Field(ge=1, le=5)
    decision_recommendation: Literal["include", "exclude", "maybe"]
    agreement_summary: str
    disagreement_summary: str
    satisfied_inclusion_points: list[str] = Field(default_factory=list)
    triggered_exclusion_points: list[str] = Field(default_factory=list)
    uncertain_points: list[str] = Field(default_factory=list)
    evidence_highlights: list[str] = Field(default_factory=list)
    decision_rationale: str


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


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _build_openai_client() -> Any:
    try:
        from openai import AsyncOpenAI
    except ModuleNotFoundError as exc:
        raise SystemExit("Missing dependency: install the `openai` package before running run_experiment.py.") from exc
    return AsyncOpenAI()


def _paper_metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _paper_gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _paper_fulltext_root(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "mds"


def _paper_stage2_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage2" / f"{paper_id}.json"


def _paper_result_dir(paper_id: str) -> Path:
    return RESULTS_ROOT / f"{paper_id}__{WORKFLOW_ARM}"


def _resolution_audit_path(paper_id: str) -> Path:
    return _paper_result_dir(paper_id) / "fulltext_resolution_audit.json"


def _result_rows_path(paper_id: str) -> Path:
    return _paper_result_dir(paper_id) / "fulltext_direct_review_results.json"


def _metrics_path(paper_id: str) -> Path:
    return _paper_result_dir(paper_id) / "fulltext_direct_f1.json"


def _validation_failures_path(paper_id: str) -> Path:
    return _paper_result_dir(paper_id) / "validation_failures.jsonl"


def _hygiene_summary_path(paper_id: str) -> Path:
    return _paper_result_dir(paper_id) / "hygiene_summary.json"


def _runtime_prompts_path() -> Path:
    return REPO_ROOT / "scripts" / "screening" / "runtime_prompts" / "runtime_prompts.json"


def _normalize_key(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


def _relative(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.relative_to(REPO_ROOT))


def _decision_from_score(score: int) -> str:
    if score >= 4:
        return "include"
    if score <= 2:
        return "exclude"
    return "maybe"


def _extract_verdict_label(verdict: str | None) -> str:
    match = re.match(r"^\s*([a-z]+)", _safe_text(verdict).lower())
    return match.group(1) if match else "unknown"


def _derive_final_verdict(*, junior_scores: tuple[int, int], senior_score: int | None) -> str:
    if senior_score is not None:
        if senior_score >= 4:
            return f"include (senior:{senior_score})"
        if senior_score <= 2:
            return f"exclude (senior:{senior_score})"
        return f"maybe (senior:{senior_score})"

    score_1, score_2 = junior_scores
    if score_1 >= 4 and score_2 >= 4:
        return f"include (junior:{score_1},{score_2})"
    if score_1 <= 2 and score_2 <= 2:
        return f"exclude (junior:{score_1},{score_2})"
    return f"maybe (junior:{score_1},{score_2})"


def _apply_head_tail_limit(text: str) -> str:
    threshold = FULLTEXT_INLINE_HEAD_CHARS + FULLTEXT_INLINE_TAIL_CHARS
    if len(text) <= threshold:
        return text
    return (
        text[:FULLTEXT_INLINE_HEAD_CHARS]
        + FULLTEXT_TRUNCATION_MARKER
        + text[-FULLTEXT_INLINE_TAIL_CHARS :]
    )


def _cut_before_references(text: str) -> tuple[str, dict[str, Any]]:
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
    trimmed_text = _apply_head_tail_limit(text)
    return trimmed_text, {
        "fulltext_chars_total": total_chars,
        "fulltext_chars_used": len(trimmed_text),
        "reference_cut_applied": marker is not None,
        "reference_cut_method": "heading" if marker is not None else "none",
        "reference_cut_marker": marker,
        "reference_cut_line_no": line_no,
    }


def _load_candidates(paper_id: str, *, keys: set[str] | None = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(_paper_metadata_path(paper_id))
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in rows:
        key = _safe_text(row.get("key"))
        if not key or key in seen_keys:
            continue
        if keys is not None and key not in keys:
            continue
        seen_keys.add(key)
        deduped.append(row)
    return deduped


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

        self.normalized_collision_count = sum(1 for paths in self.normalized_map.values() if len(paths) > 1)

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
    audit_rows: list[dict[str, Any]] = []

    for record in records:
        key = _safe_text(record.get("key"))
        resolution = index.resolve(key)
        by_key[key] = resolution
        counter[resolution["resolution_status"]] += 1
        audit_rows.append(
            {
                "key": key,
                "title": _safe_text(record.get("title") or record.get("query_title")),
                **resolution,
            }
        )

    audit_payload = {
        "paper_id": paper_id,
        "workflow_arm": WORKFLOW_ARM,
        "candidate_total": len(records),
        "exact_match_count": counter["exact"],
        "normalized_match_count": counter["normalized"],
        "retrieval_failed_count": counter["retrieval_failed"],
        "retrieval_ambiguous_count": counter["retrieval_ambiguous"],
        "normalized_collision_count": index.normalized_collision_count,
        "appledouble_ignored_count": index.ignored_appledouble_count,
        "resolutions": audit_rows,
    }
    return by_key, audit_payload


def _fulltext_payload_from_resolution(resolution: dict[str, Any]) -> tuple[str, dict[str, Any]]:
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
    trimmed_text, meta = _cut_before_references(raw_text)
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


class PromptAssets:
    def __init__(self) -> None:
        self.templates = {
            "junior": (BUNDLE_DIR / "templates" / "01_fulltext_direct_junior_reviewer_TEMPLATE.md").read_text(encoding="utf-8"),
            "senior": (BUNDLE_DIR / "templates" / "02_fulltext_direct_senior_reviewer_TEMPLATE.md").read_text(encoding="utf-8"),
        }
        self.schema_hints = {
            "junior": (BUNDLE_DIR / "samples" / "sample_junior_output.json").read_text(encoding="utf-8"),
            "senior": (BUNDLE_DIR / "samples" / "sample_senior_output.json").read_text(encoding="utf-8"),
        }
        self.retry_policy = (BUNDLE_DIR / "templates" / "validation_retry_repair_policy.md").read_text(encoding="utf-8")


def _base_context(
    *,
    prompt_assets: PromptAssets,
    paper_id: str,
    record: dict[str, Any],
    resolution: dict[str, Any],
    provenance: SourceRecordProvenance,
    stage2_criteria_text: str,
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
        "FULLTEXT_TEXT": "",
        "METADATA_JSON": _json_text(metadata_payload),
        "SOURCE_RECORD_PROVENANCE_JSON": _json_text(provenance.model_dump()),
        "FULLTEXT_RESOLUTION_JSON": _json_text(resolution),
        "JUNIOR_REVIEW_OUTPUTS_JSON": "[]",
        "JUNIOR_OUTPUT_JSON_SCHEMA_HINT": prompt_assets.schema_hints["junior"],
        "SENIOR_OUTPUT_JSON_SCHEMA_HINT": prompt_assets.schema_hints["senior"],
    }


def _render_prompt(template_text: str, context: dict[str, Any]) -> str:
    return render_prompt._render(template_text, context, strict=True)


def _with_authoritative_junior_output(parsed: JuniorReviewOutput, provenance: SourceRecordProvenance, *, paper_id: str, candidate_key: str, candidate_title: str) -> JuniorReviewOutput:
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


def _with_authoritative_senior_output(parsed: SeniorReviewOutput, provenance: SourceRecordProvenance, *, paper_id: str, candidate_key: str, candidate_title: str) -> SeniorReviewOutput:
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


def _validate_score_alignment(score: int, recommendation: str, *, label: str) -> None:
    expected = _decision_from_score(score)
    if recommendation != expected:
        raise ValueError(f"{label} decision_recommendation must align with score ({score} -> {expected})")


def _validate_text_payload(payload: dict[str, Any]) -> None:
    for fragment in _collect_strings(payload):
        match = SENTINEL_PATTERN.search(fragment)
        if match:
            raise ValueError(f"sentinel placeholder leaked into output: {match.group(0)}")


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


def _validate_junior_output(parsed: JuniorReviewOutput) -> None:
    payload = parsed.model_dump()
    _validate_score_alignment(parsed.stage_score, parsed.decision_recommendation, label="junior")
    _validate_text_payload(payload)


def _validate_senior_output(parsed: SeniorReviewOutput) -> None:
    payload = parsed.model_dump()
    _validate_score_alignment(parsed.senior_stage_score, parsed.decision_recommendation, label="senior")
    _validate_text_payload(payload)


class ValidationTracker:
    def record_failure(self, *, paper_id: str, payload: dict[str, Any]) -> None:
        _append_jsonl(_validation_failures_path(paper_id), payload)

    def write_summary(self, *, paper_id: str) -> dict[str, Any]:
        path = _validation_failures_path(paper_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        failure_count = 0
        if path.exists():
            failure_count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        payload = {
            "paper_id": paper_id,
            "workflow_arm": WORKFLOW_ARM,
            "validation_failure_count": failure_count,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        _write_json(_hygiene_summary_path(paper_id), payload)
        return payload


class LLMRunner:
    def __init__(self, client: "AsyncOpenAI", concurrency: int, tracker: ValidationTracker, retry_policy_text: str) -> None:
        self.client = client
        self.semaphore = asyncio.Semaphore(concurrency)
        self.tracker = tracker
        self.retry_policy_text = retry_policy_text

    async def call(
        self,
        *,
        model: str,
        prompt: str,
        response_model: type[BaseModel],
        validator: Any,
        failure_context: dict[str, Any],
    ) -> BaseModel:
        delay = 2.0
        last_error: Exception | None = None
        active_prompt = prompt
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                async with self.semaphore:
                    response = await self.client.beta.chat.completions.parse(
                        model=model,
                        messages=[{"role": "user", "content": active_prompt}],
                        response_format=response_model,
                        timeout=180,
                    )
                parsed = response.choices[0].message.parsed
                if parsed is None:
                    raise RuntimeError("Structured response was empty.")
                validator(parsed)
                return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                print(f"[retry] model={model} attempt={attempt} error={type(exc).__name__}: {exc}", flush=True)
                self.tracker.record_failure(
                    paper_id=failure_context["paper_id"],
                    payload={
                        **failure_context,
                        "attempt": attempt,
                        "model": model,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                if attempt == RETRY_ATTEMPTS:
                    break
                if isinstance(exc, ValueError):
                    active_prompt = (
                        f"{prompt}\n\n## Validation Retry Repair\n{self.retry_policy_text}\n\n"
                        f"Previous attempt failed with validator error: {exc}\n"
                        "Return a corrected JSON object that fixes this exact issue."
                    )
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError(f"Model call failed after retries: {last_error}") from last_error


def _load_existing_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    keyed: dict[str, dict[str, Any]] = {}
    for row in _read_json(path):
        if not isinstance(row, dict):
            continue
        key = _safe_text(row.get("key"))
        if key:
            keyed[key] = row
    return keyed


def _ordered_rows(records: list[dict[str, Any]], keyed_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for record in records:
        key = _safe_text(record.get("key"))
        if key in keyed_rows:
            ordered.append(keyed_rows[key])
    return ordered


async def _review_record(
    *,
    llm: LLMRunner,
    prompt_assets: PromptAssets,
    paper_id: str,
    record: dict[str, Any],
    resolution: dict[str, Any],
    stage2_criteria_text: str,
) -> dict[str, Any]:
    key = _safe_text(record.get("key"))
    title = _safe_text(record.get("title") or record.get("query_title"))
    provenance = _build_source_record_provenance(record, paper_id, resolution)

    if resolution["resolution_status"] not in {"exact", "normalized"}:
        review_state = resolution["resolution_status"]
        final_verdict = f"maybe (review_state:{review_state})"
        return {
            "key": key,
            "title": title,
            "workflow_arm": WORKFLOW_ARM,
            "fulltext_review_mode": "inline",
            "fulltext_source_path": resolution.get("resolved_path") or resolution.get("exact_candidate_path"),
            "fulltext_chars_total": 0,
            "fulltext_chars_used": 0,
            "reference_cut_applied": False,
            "reference_cut_method": "none",
            "reference_cut_marker": None,
            "reference_cut_line_no": None,
            "review_state": review_state,
            "fulltext_missing_or_unmatched": True,
            "round-A_JuniorNano_output": None,
            "round-A_JuniorNano_reasoning": None,
            "round-A_JuniorNano_evaluation": None,
            "round-A_JuniorMini_output": None,
            "round-A_JuniorMini_reasoning": None,
            "round-A_JuniorMini_evaluation": None,
            "round-B_SeniorLead_output": None,
            "round-B_SeniorLead_reasoning": None,
            "round-B_SeniorLead_evaluation": None,
            "final_verdict": final_verdict,
            "review_skipped": True,
            "discard_reason": review_state,
        }

    fulltext_text, fulltext_meta = _fulltext_payload_from_resolution(resolution)
    context = _base_context(
        prompt_assets=prompt_assets,
        paper_id=paper_id,
        record=record,
        resolution=resolution,
        provenance=provenance,
        stage2_criteria_text=stage2_criteria_text,
    )
    context["FULLTEXT_TEXT"] = fulltext_text

    junior_prompts = {
        reviewer_name: _render_prompt(prompt_assets.templates["junior"], context)
        for reviewer_name, _ in JUNIOR_MODELS
    }

    async def _run_junior(reviewer_name: str, model: str) -> JuniorReviewOutput:
        parsed = await llm.call(
            model=model,
            prompt=junior_prompts[reviewer_name],
            response_model=JuniorReviewOutput,
            validator=_validate_junior_output,
            failure_context={
                "paper_id": paper_id,
                "workflow_arm": WORKFLOW_ARM,
                "candidate_key": key,
                "stage": WORKFLOW_STAGE,
                "step": reviewer_name,
            },
        )
        assert isinstance(parsed, JuniorReviewOutput)
        return _with_authoritative_junior_output(parsed, provenance, paper_id=paper_id, candidate_key=key, candidate_title=title)

    junior_outputs = await asyncio.gather(*[_run_junior(name, model) for name, model in JUNIOR_MODELS])
    junior_by_name = {name: output for (name, _), output in zip(JUNIOR_MODELS, junior_outputs, strict=True)}

    junior_scores = (
        junior_by_name["JuniorNano"].stage_score,
        junior_by_name["JuniorMini"].stage_score,
    )

    senior_output: SeniorReviewOutput | None = None
    if not ((junior_scores[0] >= 4 and junior_scores[1] >= 4) or (junior_scores[0] <= 2 and junior_scores[1] <= 2)):
        senior_context = dict(context)
        senior_context["JUNIOR_REVIEW_OUTPUTS_JSON"] = _json_text([output.model_dump() for output in junior_outputs])
        senior_prompt = _render_prompt(prompt_assets.templates["senior"], senior_context)
        parsed = await llm.call(
            model=SENIOR_MODEL,
            prompt=senior_prompt,
            response_model=SeniorReviewOutput,
            validator=_validate_senior_output,
            failure_context={
                "paper_id": paper_id,
                "workflow_arm": WORKFLOW_ARM,
                "candidate_key": key,
                "stage": WORKFLOW_STAGE,
                "step": "SeniorLead",
            },
        )
        assert isinstance(parsed, SeniorReviewOutput)
        senior_output = _with_authoritative_senior_output(parsed, provenance, paper_id=paper_id, candidate_key=key, candidate_title=title)

    final_verdict = _derive_final_verdict(
        junior_scores=junior_scores,
        senior_score=senior_output.senior_stage_score if senior_output else None,
    )

    discard_reason = None
    verdict_label = _extract_verdict_label(final_verdict)
    if verdict_label == "exclude":
        discard_reason = final_verdict
    elif verdict_label == "maybe":
        discard_reason = "review_needs_followup"

    return {
        "key": key,
        "title": title,
        "workflow_arm": WORKFLOW_ARM,
        "fulltext_review_mode": "inline",
        **fulltext_meta,
        "review_state": "reviewed",
        "fulltext_missing_or_unmatched": False,
        "round-A_JuniorNano_output": junior_by_name["JuniorNano"].model_dump(),
        "round-A_JuniorNano_reasoning": junior_by_name["JuniorNano"].decision_rationale,
        "round-A_JuniorNano_evaluation": junior_by_name["JuniorNano"].stage_score,
        "round-A_JuniorMini_output": junior_by_name["JuniorMini"].model_dump(),
        "round-A_JuniorMini_reasoning": junior_by_name["JuniorMini"].decision_rationale,
        "round-A_JuniorMini_evaluation": junior_by_name["JuniorMini"].stage_score,
        "round-B_SeniorLead_output": senior_output.model_dump() if senior_output else None,
        "round-B_SeniorLead_reasoning": senior_output.decision_rationale if senior_output else None,
        "round-B_SeniorLead_evaluation": senior_output.senior_stage_score if senior_output else None,
        "final_verdict": final_verdict,
        "review_skipped": False,
        "discard_reason": discard_reason,
    }


def _run_eval(*, paper_id: str, results_path: Path, save_report: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        paper_id,
        "--results",
        str(results_path),
        "--gold-metadata",
        str(_paper_gold_path(paper_id)),
        "--positive-mode",
        "include_or_maybe",
        "--save-report",
        str(save_report),
    ]
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip())
    return _read_json(save_report)


def _current_baseline_report(paper_id: str) -> dict[str, Any]:
    return _read_json(CURRENT_AUTHORITY[paper_id]["combined_path"])


def _qa_first_history() -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cache: dict[Path, dict[str, Any]] = {}
    for source in QA_FIRST_COMPARISON_SOURCES:
        manifest_path = source["manifest_path"]
        if manifest_path not in cache:
            cache[manifest_path] = _read_json(manifest_path)
        manifest = cache[manifest_path]
        for summary in manifest.get("summaries", []):
            if summary.get("paper_id") == source["paper_id"] and summary.get("arm") == source["arm"]:
                history[source["paper_id"]].append(
                    {
                        "label": source["label"],
                        "combined_f1": summary["combined_f1"],
                        "manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
                    }
                )
                break
    return history


def _summarize_paper(
    *,
    paper_id: str,
    records: list[dict[str, Any]],
    audit: dict[str, Any],
    metrics: dict[str, Any],
    baseline_report: dict[str, Any],
) -> dict[str, Any]:
    reviewed_rows = [row for row in records if row.get("review_state") == "reviewed"]
    senior_invocations = sum(1 for row in reviewed_rows if row.get("round-B_SeniorLead_evaluation") is not None)
    junior_double_high = sum(
        1
        for row in reviewed_rows
        if (row.get("round-A_JuniorNano_evaluation") or 0) >= 4 and (row.get("round-A_JuniorMini_evaluation") or 0) >= 4
    )
    junior_double_low = sum(
        1
        for row in reviewed_rows
        if (row.get("round-A_JuniorNano_evaluation") or 9) <= 2 and (row.get("round-A_JuniorMini_evaluation") or 9) <= 2
    )
    return {
        "paper_id": paper_id,
        "workflow_arm": WORKFLOW_ARM,
        "candidate_total": len(records),
        "reviewed_count": len(reviewed_rows),
        "retrieval_failed_count": sum(1 for row in records if row.get("review_state") == "retrieval_failed"),
        "retrieval_ambiguous_count": sum(1 for row in records if row.get("review_state") == "retrieval_ambiguous"),
        "exact_match_count": audit["exact_match_count"],
        "normalized_match_count": audit["normalized_match_count"],
        "appledouble_ignored_count": audit["appledouble_ignored_count"],
        "normalized_collision_count": audit["normalized_collision_count"],
        "senior_invocation_count": senior_invocations,
        "junior_double_high_count": junior_double_high,
        "junior_double_low_count": junior_double_low,
        "fulltext_direct_precision": metrics["metrics"]["precision"],
        "fulltext_direct_recall": metrics["metrics"]["recall"],
        "fulltext_direct_f1": metrics["metrics"]["f1"],
        "tp": metrics["metrics"]["tp"],
        "fp": metrics["metrics"]["fp"],
        "tn": metrics["metrics"]["tn"],
        "fn": metrics["metrics"]["fn"],
        "current_combined_f1": baseline_report["metrics"]["f1"],
        "delta_vs_current_combined": metrics["metrics"]["f1"] - baseline_report["metrics"]["f1"],
        "current_authority_label": CURRENT_AUTHORITY[paper_id]["authority_label"],
        "current_authority_combined_path": str(CURRENT_AUTHORITY[paper_id]["combined_path"].relative_to(REPO_ROOT)),
    }


def _comparison_text(delta: float) -> str:
    if delta > 0.01:
        return "better"
    if delta < -0.01:
        return "worse"
    return "roughly similar"


def _build_report_zh(run_manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Fulltext-Direct / Stage2-Direct Non-QA Baseline Report")
    lines.append("")
    if run_manifest.get("max_records") is not None:
        lines.append("> 這是一個 smoke / partial run，不是四篇 paper 的完整 benchmark。")
        lines.append("")
    lines.append("## Current-State Recap")
    lines.append("")
    lines.append("- production runtime prompt authority：`scripts/screening/runtime_prompts/runtime_prompts.json`。")
    lines.append("- production criteria authority：`criteria_stage1/<paper_id>.json`、`criteria_stage2/<paper_id>.json`。")
    lines.append("- 本次 `fulltext-direct` 是 experiment-only baseline，不覆寫 production。")
    for paper_id in run_manifest["papers"]:
        baseline = run_manifest["baseline"][paper_id]
        lines.append(
            f"- `{paper_id}` current authority：`{baseline['authority_label']}`，Combined F1 = `{baseline['combined_metrics']['f1']:.4f}`。"
        )
    lines.append("")
    lines.append("## Metrics Summary")
    lines.append("")
    lines.append("| Paper | Candidates | Direct F1 | Delta vs current combined | Precision | Recall | Senior invoked | Retrieval failed | Resolution exact/normalized |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for summary in run_manifest["summaries"]:
        lines.append(
            f"| `{summary['paper_id']}` | {summary['candidate_total']} | {summary['fulltext_direct_f1']:.4f} | "
            f"{summary['delta_vs_current_combined']:+.4f} | {summary['fulltext_direct_precision']:.4f} | "
            f"{summary['fulltext_direct_recall']:.4f} | {summary['senior_invocation_count']} | "
            f"{summary['retrieval_failed_count'] + summary['retrieval_ambiguous_count']} | "
            f"{summary['exact_match_count']}/{summary['normalized_match_count']} |"
        )
    lines.append("")
    lines.append("## Direct Vs Current")
    lines.append("")
    for summary in run_manifest["summaries"]:
        comparison = _comparison_text(summary["delta_vs_current_combined"])
        lines.append(
            f"- `{summary['paper_id']}`：direct baseline is `{comparison}` than current production combined "
            f"(`{summary['fulltext_direct_f1']:.4f}` vs `{summary['current_combined_f1']:.4f}`)."
        )
    lines.append("")
    lines.append("## QA-First Comparison")
    lines.append("")
    qa_history = run_manifest.get("qa_first_history", {})
    for paper_id in ("2409.13738", "2511.13936"):
        if paper_id not in qa_history:
            continue
        lines.append(f"### `{paper_id}`")
        lines.append("")
        direct_f1 = next(summary["fulltext_direct_f1"] for summary in run_manifest["summaries"] if summary["paper_id"] == paper_id)
        lines.append(f"- current direct baseline combined F1：`{direct_f1:.4f}`")
        for entry in qa_history[paper_id]:
            lines.append(f"- {entry['label']}：`{entry['combined_f1']:.4f}`")
        lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append("- `2601.19926` requires normalized filename resolution for 29 keys; this is retrieval hygiene, not methodological improvement.")
    lines.append("- Missing or ambiguous fulltext is scored as `maybe`, so retrieval artifacts can depress precision under `include_or_maybe` evaluation.")
    lines.append("- This baseline is not production-ready because it removes Stage 1 cost control and forces full-text review on every candidate.")
    lines.append("- If many experiment tracks are opened in parallel, use `www.k-dense.ai` to manage the workflow.")
    lines.append("")
    return "\n".join(lines)


async def _run_paper(
    *,
    llm: LLMRunner,
    prompt_assets: PromptAssets,
    tracker: ValidationTracker,
    paper_id: str,
    max_records: int | None,
    key_filter: set[str] | None,
    record_batch_size: int,
) -> dict[str, Any]:
    stage2_criteria_text = _paper_stage2_criteria_path(paper_id).read_text(encoding="utf-8")
    candidates = _load_candidates(paper_id, keys=key_filter)
    if max_records is not None:
        candidates = candidates[:max_records]

    resolutions_by_key, audit_payload = _build_resolution_audit(paper_id, candidates)
    _write_json(_resolution_audit_path(paper_id), audit_payload)

    results_path = _result_rows_path(paper_id)
    keyed_rows = _load_existing_rows(results_path)
    pending = [record for record in candidates if _safe_text(record.get("key")) not in keyed_rows]

    print(
        f"[run] paper={paper_id} total={len(candidates)} pending={len(pending)} exact={audit_payload['exact_match_count']} "
        f"normalized={audit_payload['normalized_match_count']} failed={audit_payload['retrieval_failed_count']} "
        f"ambiguous={audit_payload['retrieval_ambiguous_count']}",
        flush=True,
    )

    tasks = [
        asyncio.create_task(
            _review_record(
                llm=llm,
                prompt_assets=prompt_assets,
                paper_id=paper_id,
                record=record,
                resolution=resolutions_by_key[_safe_text(record.get("key"))],
                stage2_criteria_text=stage2_criteria_text,
            )
        )
        for record in pending
    ]
    progress = tqdm(total=len(tasks), desc=paper_id, unit="rec", dynamic_ncols=True) if tqdm and tasks else None
    completed_count = 0
    try:
        for task in asyncio.as_completed(tasks):
            row = await task
            keyed_rows[_safe_text(row.get("key"))] = row
            _write_json(results_path, _ordered_rows(candidates, keyed_rows))
            completed_count += 1
            if progress is not None:
                progress.update(1)
            elif completed_count == 1 or completed_count % 10 == 0 or completed_count == len(tasks):
                print(f"[run] paper={paper_id} progress={completed_count}/{len(tasks)} last_key={row['key']}", flush=True)
    finally:
        if progress is not None:
            progress.close()

    rows = _ordered_rows(candidates, keyed_rows)
    _write_json(results_path, rows)
    metrics = _run_eval(paper_id=paper_id, results_path=results_path, save_report=_metrics_path(paper_id))
    hygiene = tracker.write_summary(paper_id=paper_id)
    baseline_report = _current_baseline_report(paper_id)

    return {
        "audit": audit_payload,
        "rows": rows,
        "metrics": metrics,
        "baseline_report": baseline_report,
        "hygiene": hygiene,
    }


async def run_all(args: argparse.Namespace, prompt_assets: PromptAssets) -> None:
    _load_env_file()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    selected_papers = tuple(args.papers or PAPERS)
    key_filter = set(args.keys) if args.keys else None
    tracker = ValidationTracker()
    client = _build_openai_client()
    llm = LLMRunner(
        client=client,
        concurrency=args.concurrency,
        tracker=tracker,
        retry_policy_text=prompt_assets.retry_policy,
    )

    baseline = {
        paper_id: {
            "authority_label": CURRENT_AUTHORITY[paper_id]["authority_label"],
            "stage1_path": str(CURRENT_AUTHORITY[paper_id]["stage1_path"].relative_to(REPO_ROOT)),
            "combined_path": str(CURRENT_AUTHORITY[paper_id]["combined_path"].relative_to(REPO_ROOT)),
            "combined_metrics": _current_baseline_report(paper_id)["metrics"],
        }
        for paper_id in selected_papers
    }

    summaries: list[dict[str, Any]] = []
    hygiene: list[dict[str, Any]] = []

    for paper_id in selected_papers:
        result = await _run_paper(
            llm=llm,
            prompt_assets=prompt_assets,
            tracker=tracker,
            paper_id=paper_id,
            max_records=args.max_records,
            key_filter=key_filter,
            record_batch_size=args.record_batch_size,
        )
        summaries.append(
            _summarize_paper(
                paper_id=paper_id,
                records=result["rows"],
                audit=result["audit"],
                metrics=result["metrics"],
                baseline_report=result["baseline_report"],
            )
        )
        hygiene.append(result["hygiene"])

    run_manifest = {
        "bundle_dir": str(BUNDLE_DIR),
        "results_root": str(RESULTS_ROOT),
        "run_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "papers": list(selected_papers),
        "workflow_arm": WORKFLOW_ARM,
        "models": {
            "JuniorNano": JUNIOR_MODELS[0][1],
            "JuniorMini": JUNIOR_MODELS[1][1],
            "SeniorLead": SENIOR_MODEL,
        },
        "fulltext_truncation": {
            "head_chars": FULLTEXT_INLINE_HEAD_CHARS,
            "tail_chars": FULLTEXT_INLINE_TAIL_CHARS,
        },
        "max_records": args.max_records,
        "key_filter": sorted(key_filter) if key_filter else None,
        "baseline": baseline,
        "summaries": summaries,
        "hygiene": hygiene,
        "qa_first_history": _qa_first_history(),
    }
    _write_json(RESULTS_ROOT / "run_manifest.json", run_manifest)
    (RESULTS_ROOT / "REPORT_zh.md").write_text(_build_report_zh(run_manifest), encoding="utf-8")
    print(f"[done] results_root={RESULTS_ROOT}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fulltext-direct / stage2-direct non-QA baseline.")
    parser.add_argument("--papers", nargs="*", choices=PAPERS, default=list(PAPERS))
    parser.add_argument("--keys", nargs="*", default=None, help="Optional candidate keys to keep across selected papers.")
    parser.add_argument("--max-records", type=int, default=None, help="Optional max records per paper after filtering.")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--record-batch-size", type=int, default=6)
    args = parser.parse_args()
    if args.record_batch_size <= 0:
        raise SystemExit("--record-batch-size must be > 0")
    prompt_assets = PromptAssets()
    asyncio.run(run_all(args, prompt_assets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
