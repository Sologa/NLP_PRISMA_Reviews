from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, create_model

try:
    from .. import cutoff_time_filter
except ImportError:  # pragma: no cover - script-style execution fallback
    import cutoff_time_filter  # type: ignore[no-redef]

from .common import (
    custom_id,
    decision_from_score,
    json_text,
    now_run_id,
    read_json,
    read_jsonl,
    relative_path,
    safe_text,
    stage_verdict,
    write_json,
    write_jsonl,
)
from .merged_batch_types import (
    CriterionAssessment,
    MergedCriterionAsset,
    MergedStageModelOutput,
    MergedWorkflowSpec,
    SingleReviewerMergedFinalRow,
    SourceRecordProvenance,
    StageMergedReviewRecord,
)


FULLTEXT_TRUNCATION_MARKER = "\n\n...[TRUNCATED MIDDLE]...\n\n"


def load_workflow_spec(path: Path) -> MergedWorkflowSpec:
    return MergedWorkflowSpec.model_validate(read_json(path))


def load_criterion_asset(path: Path) -> MergedCriterionAsset:
    return MergedCriterionAsset.model_validate(read_json(path))


def build_dynamic_stage_response_model(schema_name: str, *, criterion_ids: list[str]) -> type[BaseModel]:
    ordered_ids = tuple(dict.fromkeys(criterion_ids))
    if not ordered_ids:
        raise ValueError(f"{schema_name} requires at least one criterion id")
    criterion_id_literal = Literal.__getitem__(ordered_ids)
    criterion_assessment_model = create_model(
        f"{schema_name}CriterionAssessment",
        __base__=CriterionAssessment,
        criterion_id=(criterion_id_literal, ...),
    )
    constrained_assessment_list = Annotated[
        list[criterion_assessment_model],  # type: ignore[valid-type]
        Field(min_length=len(ordered_ids), max_length=len(ordered_ids)),
    ]
    return create_model(
        schema_name,
        __base__=MergedStageModelOutput,
        criterion_assessments=(constrained_assessment_list, ...),
    )


def build_stage_validator(
    *,
    paper_id: str,
    stage: str,
    candidate_key: str,
    candidate_title: str,
    expected_criterion_ids: list[str],
) -> Any:
    expected = set(expected_criterion_ids)

    def validate(payload: BaseModel) -> None:
        parsed = MergedStageModelOutput.model_validate(payload)
        observed = [item.criterion_id for item in parsed.criterion_assessments]
        if len(observed) != len(expected_criterion_ids):
            raise ValueError(
                f"criterion_assessments length mismatch for {paper_id}/{stage}/{candidate_key} ({candidate_title})"
            )
        if set(observed) != expected:
            raise ValueError(
                f"criterion_id mismatch for {paper_id}/{stage}/{candidate_key}: expected={sorted(expected)} observed={sorted(set(observed))}"
            )
        if len(observed) != len(set(observed)):
            raise ValueError("criterion_id must be unique within criterion_assessments")

    return validate


def build_stage_review_record(
    *,
    model_output: dict[str, Any],
    paper_id: str,
    candidate_key: str,
    candidate_title: str,
    stage: str,
    workflow_arm: str,
    qa_asset_path: str,
    criteria_path: str,
    provenance: SourceRecordProvenance,
) -> StageMergedReviewRecord:
    payload = dict(model_output)
    payload.update(
        {
            "paper_id": paper_id,
            "candidate_key": candidate_key,
            "candidate_title": candidate_title,
            "stage": stage,
            "workflow_arm": workflow_arm,
            "qa_asset_path": qa_asset_path,
            "criteria_path": criteria_path,
            "source_record_provenance": provenance.model_dump(mode="json"),
        }
    )
    return StageMergedReviewRecord.model_validate(payload)


def load_candidates(
    metadata_path: Path,
    *,
    max_records: int | None = None,
    key_allowlist: set[str] | None = None,
) -> list[dict[str, Any]]:
    rows = read_jsonl(metadata_path)
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in rows:
        key = safe_text(row.get("key"))
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        if key_allowlist is not None and key not in key_allowlist:
            continue
        deduped.append(row)
    if max_records is not None:
        return deduped[:max_records]
    return deduped


def apply_head_tail_limit(text: str, *, head_chars: int, tail_chars: int) -> str:
    threshold = head_chars + tail_chars
    if len(text) <= threshold:
        return text
    return text[:head_chars] + FULLTEXT_TRUNCATION_MARKER + text[-tail_chars:]


def _normalize_key(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


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
    trimmed_text = apply_head_tail_limit(text, head_chars=head_chars, tail_chars=tail_chars)
    return trimmed_text, {
        "fulltext_chars_total": total_chars,
        "fulltext_chars_used": len(trimmed_text),
        "reference_cut_applied": marker is not None,
        "reference_cut_method": "heading" if marker is not None else "none",
        "reference_cut_marker": marker,
        "reference_cut_line_no": line_no,
    }


class FulltextIndex:
    def __init__(self, fulltext_root: Path) -> None:
        self.root = fulltext_root
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

    def resolve(self, key: str, *, repo_root: Path) -> dict[str, Any]:
        exact_candidate = self.root / f"{key}.md"
        normalized_key = _normalize_key(key)
        if key in self.exact_map:
            path = self.exact_map[key]
            return {
                "resolution_status": "exact",
                "normalized_key": normalized_key,
                "exact_candidate_path": relative_path(exact_candidate, repo_root),
                "resolved_path": relative_path(path, repo_root),
                "match_candidates": [relative_path(path, repo_root)],
            }
        matches = self.normalized_map.get(normalized_key, [])
        if len(matches) == 1:
            return {
                "resolution_status": "normalized",
                "normalized_key": normalized_key,
                "exact_candidate_path": relative_path(exact_candidate, repo_root),
                "resolved_path": relative_path(matches[0], repo_root),
                "match_candidates": [relative_path(matches[0], repo_root)],
            }
        if len(matches) > 1:
            return {
                "resolution_status": "retrieval_ambiguous",
                "normalized_key": normalized_key,
                "exact_candidate_path": relative_path(exact_candidate, repo_root),
                "resolved_path": None,
                "match_candidates": [relative_path(path, repo_root) for path in matches],
            }
        return {
            "resolution_status": "retrieval_failed",
            "normalized_key": normalized_key,
            "exact_candidate_path": relative_path(exact_candidate, repo_root),
            "resolved_path": None,
            "match_candidates": [],
        }


def build_fulltext_resolution_audit(
    *,
    paper_id: str,
    records: list[dict[str, Any]],
    fulltext_root: Path,
    repo_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    index = FulltextIndex(fulltext_root)
    by_key: dict[str, dict[str, Any]] = {}
    counter: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for record in records:
        key = safe_text(record.get("key"))
        resolution = index.resolve(key, repo_root=repo_root)
        by_key[key] = resolution
        counter[resolution["resolution_status"]] += 1
        rows.append(
            {
                "key": key,
                "title": safe_text(record.get("title") or record.get("query_title")),
                **resolution,
            }
        )
    return by_key, {
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


def fulltext_payload_from_resolution(
    resolution: dict[str, Any],
    *,
    repo_root: Path,
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
    path = repo_root / str(resolution["resolved_path"])
    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    trimmed_text, meta = _cut_before_references(raw_text, head_chars=head_chars, tail_chars=tail_chars)
    meta["fulltext_source_path"] = str(path)
    return trimmed_text, meta


def build_source_record_provenance(
    *,
    record: dict[str, Any],
    paper_id: str,
    resolution: dict[str, Any],
    metadata_path: Path,
    runtime_prompts_path: Path,
    criteria_path: Path,
    repo_root: Path,
) -> SourceRecordProvenance:
    return SourceRecordProvenance(
        record_key=safe_text(record.get("key")),
        record_title=safe_text(record.get("title") or record.get("query_title")),
        source=safe_text(record.get("source")) or None,
        source_id=safe_text(record.get("source_id")) or None,
        metadata_path=str(metadata_path.relative_to(repo_root)),
        runtime_prompts_path=str(runtime_prompts_path.relative_to(repo_root)),
        criteria_path=str(criteria_path.relative_to(repo_root)),
        fulltext_candidate_path=str(resolution.get("exact_candidate_path") or ""),
        fulltext_available=resolution["resolution_status"] in {"exact", "normalized"},
    )


def metadata_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": safe_text(record.get("key")),
        "query_title": safe_text(record.get("query_title")),
        "title": safe_text(record.get("title") or record.get("query_title")),
        "abstract": safe_text(record.get("abstract")),
        "source": safe_text(record.get("source")),
        "source_id": safe_text(record.get("source_id")),
        "match_status": safe_text(record.get("match_status")),
        "missing_reason": safe_text(record.get("missing_reason")),
        "published_date": safe_text(record.get("published_date")),
    }


def load_cutoff_result(
    *,
    records: list[dict[str, Any]],
    cutoff_path: Path,
) -> dict[str, Any]:
    payload, policy = cutoff_time_filter.load_time_policy(cutoff_path)
    payload = dict(payload)
    payload["_cutoff_json_path"] = str(cutoff_path)
    return cutoff_time_filter.apply_cutoff(records, payload=payload, policy=policy)


def criteria_text_for_stage(criteria_path: Path) -> str:
    return json_text(read_json(criteria_path))


def build_stage_prompt_context(
    *,
    stage: str,
    workflow_arm: str,
    paper_id: str,
    candidate_key: str,
    candidate_title: str,
    asset: MergedCriterionAsset,
    criteria_payload: str,
    metadata: dict[str, Any],
    response_schema_hint: str,
    provenance: SourceRecordProvenance,
    prior_stage_review: dict[str, Any] | None = None,
    fulltext_resolution: dict[str, Any] | None = None,
    fulltext_text: str | None = None,
) -> dict[str, Any]:
    context = {
        "WORKFLOW_ARM": workflow_arm,
        "PAPER_ID": paper_id,
        "CANDIDATE_KEY": candidate_key,
        "CANDIDATE_TITLE": candidate_title,
        "TOPIC_DEFINITION": asset.topic_definition,
        "DECISION_POLICY": asset.decision_policy,
        "QA_ASSET_JSON": json_text(asset.model_dump(mode="json")),
        "STAGE_CRITERIA_JSON_CONTENT": criteria_payload,
        "METADATA_JSON": json_text(metadata),
        "SOURCE_RECORD_PROVENANCE_JSON": json_text(provenance.model_dump(mode="json")),
        "RESPONSE_SCHEMA_HINT_JSON": response_schema_hint,
    }
    if stage == "stage2":
        context["PRIOR_STAGE_REVIEW_JSON"] = json_text(prior_stage_review or {})
        context["FULLTEXT_RESOLUTION_JSON"] = json_text(fulltext_resolution or {})
        context["FULLTEXT_TEXT"] = fulltext_text or ""
    return context


def phase_success_rows_by_paper(
    *,
    parsed_payload: dict[str, Any],
    spec_context: dict[str, dict[str, Any]],
    stage: str,
    workflow_arm: str,
) -> dict[str, list[dict[str, Any]]]:
    rows_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    success_by_id = {item["custom_id"]: item for item in parsed_payload.get("successes", [])}
    for custom, context in spec_context.items():
        item = success_by_id.get(custom)
        if item is None:
            continue
        record = build_stage_review_record(
            model_output=item["parsed"],
            paper_id=context["paper_id"],
            candidate_key=context["candidate_key"],
            candidate_title=context["candidate_title"],
            stage=stage,
            workflow_arm=workflow_arm,
            qa_asset_path=context["qa_asset_path"],
            criteria_path=context["criteria_path"],
            provenance=SourceRecordProvenance.model_validate(context["provenance"]),
        )
        rows_by_paper[context["paper_id"]].append(record.model_dump(mode="json"))
    return rows_by_paper


def collect_phase_issues_by_key(parsed_payload_path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    if not parsed_payload_path.exists():
        return {}
    payload = read_json(parsed_payload_path)
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
                "failed_phase": context.get("phase"),
                "review_output": item,
            }
    return out


def build_cutoff_review_row(
    *,
    paper_id: str,
    workflow_arm: str,
    stage_model: str,
    record: dict[str, Any],
    decision: dict[str, Any],
) -> SingleReviewerMergedFinalRow:
    base = cutoff_time_filter.build_cutoff_excluded_row(record, decision=decision)
    return SingleReviewerMergedFinalRow(
        key=safe_text(base["key"]),
        title=safe_text(base["title"]),
        paper_id=paper_id,
        workflow_arm=workflow_arm,
        stage_model=stage_model,
        review_state=str(base["review_state"]),
        review_skipped=bool(base["review_skipped"]),
        discard_reason=str(base["discard_reason"]),
        final_verdict=str(base["final_verdict"]),
        review_output={"cutoff_filter": base["cutoff_filter"]},
    )
