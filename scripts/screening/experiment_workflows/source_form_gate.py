from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

try:
    from ..openai_batch_runner import BatchRequestSpec
    from ..openai_batch_runner import build_json_schema_response_format
except ImportError:  # pragma: no cover - script-style execution fallback
    from openai_batch_runner import BatchRequestSpec  # type: ignore[no-redef]
    from openai_batch_runner import build_json_schema_response_format  # type: ignore[no-redef]

from .common import json_text, read_json, read_jsonl, safe_text, write_json, write_jsonl


SOURCE_FORM_PHASE_ID = "source_form_classification"
SOURCE_FORM_SCHEMA_VERSION = "source_form_gate_v1"
SOURCE_FORM_PROMPT_VERSION = "source_form_classifier_v1"
DEFAULT_SOURCE_FORM_MODEL = "gpt-5-nano"
DEFAULT_SOURCE_FORM_REASONING_EFFORT = "high"
DEFAULT_CACHE_DIR_RELATIVE = "screening/gates/source_form_cache/gpt-5-nano_high_v1"

PublicationType = Literal[
    "primary_empirical_or_original",
    "secondary_review_or_survey",
    "tertiary_review_of_reviews",
    "guideline_or_standard",
    "position_or_commentary",
    "book_or_chapter",
    "tool_dataset_software_doc",
    "non_empirical_other",
    "unknown",
]

GateDecision = Literal["pass", "exclude_source_form", "manual_or_unclear_pass"]

HARD_EXCLUDED_WHEN_SECONDARY_DISALLOWED: tuple[PublicationType, ...] = (
    "secondary_review_or_survey",
    "tertiary_review_of_reviews",
    "guideline_or_standard",
    "position_or_commentary",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceFormClassificationOutput(_StrictModel):
    publication_type: PublicationType
    is_primary_empirical_or_original: bool
    confidence: Literal["high", "medium", "low"]
    short_rationale: str = Field(min_length=1, max_length=600)
    evidence_fields_used: list[str] = Field(default_factory=list)
    title_abstract_quotes: list[str] = Field(default_factory=list, max_length=3)


class SourceFormPolicy(_StrictModel):
    paper_id: str
    allow_secondary_source_forms: bool = False
    notes: str = ""


class SourceFormPolicyLedger(_StrictModel):
    schema_version: str
    default: SourceFormPolicy
    papers: dict[str, SourceFormPolicy]


class SourceFormGateRecord(_StrictModel):
    schema_version: str
    prompt_version: str
    model: str
    reasoning_effort: str
    paper_id: str
    candidate_key: str
    title: str
    metadata_hash: str
    criteria_hash: str
    policy_hash: str
    prompt_hash: str
    cache_key: str
    custom_id: str
    classification: SourceFormClassificationOutput
    gate_decision: GateDecision
    gate_pass: bool
    exclusion_reason: str | None = None
    policy: SourceFormPolicy


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def source_form_custom_id(paper_id: str, candidate_key: str) -> str:
    return f"{SOURCE_FORM_PHASE_ID}__{paper_id}__{candidate_key}"


def source_form_metadata_payload(record: dict[str, Any]) -> dict[str, Any]:
    row_key = safe_text(record.get("source_form_row_key") or record.get("key"))
    return {
        "key": row_key,
        "original_key": safe_text(record.get("key")),
        "query_title": safe_text(record.get("query_title")),
        "title": safe_text(record.get("title") or record.get("query_title")),
        "abstract": safe_text(record.get("abstract")),
        "source": safe_text(record.get("source")),
        "source_id": safe_text(record.get("source_id")),
        "doi": safe_text(record.get("doi")),
        "journal_ref": safe_text(record.get("journal_ref")),
        "comment": safe_text(record.get("comment")),
        "published_date": safe_text(record.get("published_date")),
        "match_status": safe_text(record.get("match_status")),
        "missing_reason": safe_text(record.get("missing_reason")),
    }


def load_source_form_policy(path: Path) -> SourceFormPolicyLedger:
    payload = read_json(path)
    default_payload = dict(payload.get("default") or {})
    default_payload.setdefault("paper_id", "*")
    papers = {}
    for paper_id, item in dict(payload.get("papers") or {}).items():
        paper_payload = dict(item or {})
        paper_payload.setdefault("paper_id", paper_id)
        papers[paper_id] = SourceFormPolicy.model_validate(paper_payload)
    return SourceFormPolicyLedger.model_validate(
        {
            "schema_version": payload.get("schema_version"),
            "default": default_payload,
            "papers": papers,
        }
    )


def policy_for_paper(ledger: SourceFormPolicyLedger, paper_id: str) -> SourceFormPolicy:
    if paper_id in ledger.papers:
        return ledger.papers[paper_id]
    default = ledger.default.model_dump(mode="json")
    default["paper_id"] = paper_id
    return SourceFormPolicy.model_validate(default)


def source_form_policy_hash(policy: SourceFormPolicy) -> str:
    return stable_hash(policy.model_dump(mode="json"))


def classify_prompt(
    *,
    paper_id: str,
    candidate_key: str,
    metadata: dict[str, Any],
    stage1_criteria: dict[str, Any],
) -> str:
    return (
        "You are classifying the source form / publication type of one candidate record.\n"
        "Do not decide whether the record should be included or excluded. Return only the source-form classification.\n\n"
        "Use only title, abstract, and metadata. Stage 1 criteria are included for context, but you must not apply eligibility.\n\n"
        "Publication type definitions:\n"
        "- primary_empirical_or_original: original empirical study, original experiment, original observational study, original method evaluation, dataset study, benchmark study, or original research contribution.\n"
        "- secondary_review_or_survey: narrative review, systematic review, scoping review, literature survey, mapping review, meta-analysis, or review article synthesizing prior studies.\n"
        "- tertiary_review_of_reviews: umbrella review, overview of reviews, review of systematic reviews, or tertiary synthesis.\n"
        "- guideline_or_standard: guideline, consensus statement, reporting standard, protocol standard, recommendation, or best-practice standard.\n"
        "- position_or_commentary: editorial, viewpoint, commentary, perspective, opinion, letter, correspondence, position paper, or debate piece.\n"
        "- book_or_chapter: book, textbook, monograph, or book chapter.\n"
        "- tool_dataset_software_doc: documentation or description of software, tool, package, dataset, benchmark resource, registry, or database where the record is not clearly an empirical study.\n"
        "- non_empirical_other: other non-empirical publication forms not covered above.\n"
        "- unknown: insufficient title/abstract/metadata evidence to classify reliably.\n\n"
        "Tie-breaking rules:\n"
        "- If the title or abstract explicitly says review, survey, scoping review, systematic review, mapping review, meta-analysis, or literature review, choose secondary_review_or_survey unless it is clearly a tertiary review.\n"
        "- If the record includes original evaluation plus a review background, choose primary_empirical_or_original.\n"
        "- If evidence is ambiguous, choose unknown and confidence low.\n"
        "- Keep quotes short and only from title/abstract/metadata.\n\n"
        f"PAPER_ID: {paper_id}\n"
        f"CANDIDATE_KEY: {candidate_key}\n\n"
        "METADATA_JSON:\n"
        f"{json_text(metadata)}\n\n"
        "STAGE1_CRITERIA_JSON:\n"
        f"{json_text(stage1_criteria)}\n"
    )


def source_form_prompt_hash() -> str:
    return stable_hash(
        {
            "prompt_version": SOURCE_FORM_PROMPT_VERSION,
            "schema_version": SOURCE_FORM_SCHEMA_VERSION,
            "definitions": list(HARD_EXCLUDED_WHEN_SECONDARY_DISALLOWED),
        }
    )


def source_form_cache_key(
    *,
    paper_id: str,
    candidate_key: str,
    metadata_hash: str,
    criteria_hash: str,
    policy_hash: str,
    model: str,
    reasoning_effort: str,
) -> str:
    return stable_hash(
        {
            "paper_id": paper_id,
            "candidate_key": candidate_key,
            "metadata_hash": metadata_hash,
            "criteria_hash": criteria_hash,
            "policy_hash": policy_hash,
            "prompt_hash": source_form_prompt_hash(),
            "prompt_version": SOURCE_FORM_PROMPT_VERSION,
            "schema_version": SOURCE_FORM_SCHEMA_VERSION,
            "model": model,
            "reasoning_effort": reasoning_effort,
        }
    )


def determine_source_form_gate(policy: SourceFormPolicy, classification: SourceFormClassificationOutput) -> dict[str, Any]:
    publication_type = classification.publication_type
    if publication_type == "unknown" or classification.confidence == "low":
        gate_decision: GateDecision = "manual_or_unclear_pass"
        return {
            "gate_decision": gate_decision,
            "gate_pass": True,
            "exclusion_reason": None,
        }
    if policy.allow_secondary_source_forms and publication_type in {
        "secondary_review_or_survey",
        "tertiary_review_of_reviews",
    }:
        return {
            "gate_decision": "pass",
            "gate_pass": True,
            "exclusion_reason": None,
        }
    if (not policy.allow_secondary_source_forms) and publication_type in HARD_EXCLUDED_WHEN_SECONDARY_DISALLOWED:
        return {
            "gate_decision": "exclude_source_form",
            "gate_pass": False,
            "exclusion_reason": f"policy_disallows_{publication_type}",
        }
    return {
        "gate_decision": "pass",
        "gate_pass": True,
        "exclusion_reason": None,
    }


def build_source_form_record(
    *,
    paper_id: str,
    record: dict[str, Any],
    classification: SourceFormClassificationOutput,
    policy: SourceFormPolicy,
    stage1_criteria: dict[str, Any],
    model: str,
    reasoning_effort: str,
) -> SourceFormGateRecord:
    metadata = source_form_metadata_payload(record)
    candidate_key = metadata["key"]
    metadata_hash = stable_hash(metadata)
    criteria_hash = stable_hash(stage1_criteria)
    policy_hash = source_form_policy_hash(policy)
    gate = determine_source_form_gate(policy, classification)
    return SourceFormGateRecord.model_validate(
        {
            "schema_version": SOURCE_FORM_SCHEMA_VERSION,
            "prompt_version": SOURCE_FORM_PROMPT_VERSION,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "paper_id": paper_id,
            "candidate_key": candidate_key,
            "title": metadata["title"],
            "metadata_hash": metadata_hash,
            "criteria_hash": criteria_hash,
            "policy_hash": policy_hash,
            "prompt_hash": source_form_prompt_hash(),
            "cache_key": source_form_cache_key(
                paper_id=paper_id,
                candidate_key=candidate_key,
                metadata_hash=metadata_hash,
                criteria_hash=criteria_hash,
                policy_hash=policy_hash,
                model=model,
                reasoning_effort=reasoning_effort,
            ),
            "custom_id": source_form_custom_id(paper_id, candidate_key),
            "classification": classification.model_dump(mode="json"),
            "gate_decision": gate["gate_decision"],
            "gate_pass": gate["gate_pass"],
            "exclusion_reason": gate["exclusion_reason"],
            "policy": policy.model_dump(mode="json"),
        }
    )


def build_source_form_request_spec(
    *,
    paper_id: str,
    record: dict[str, Any],
    policy: SourceFormPolicy,
    stage1_criteria: dict[str, Any],
    model: str,
    reasoning_effort: str,
) -> BatchRequestSpec:
    metadata = source_form_metadata_payload(record)
    candidate_key = metadata["key"]
    metadata_hash = stable_hash(metadata)
    criteria_hash = stable_hash(stage1_criteria)
    policy_hash = source_form_policy_hash(policy)
    cache_key = source_form_cache_key(
        paper_id=paper_id,
        candidate_key=candidate_key,
        metadata_hash=metadata_hash,
        criteria_hash=criteria_hash,
        policy_hash=policy_hash,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    prompt = classify_prompt(
        paper_id=paper_id,
        candidate_key=candidate_key,
        metadata=metadata,
        stage1_criteria=stage1_criteria,
    )
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(
            SourceFormClassificationOutput,
            schema_name=f"SourceFormClassification_{paper_id.replace('.', '_')}",
        ),
        "reasoning_effort": reasoning_effort,
    }
    return BatchRequestSpec(
        custom_id=source_form_custom_id(paper_id, candidate_key),
        model=model,
        body=body,
        response_model=SourceFormClassificationOutput,
        context={
            "phase": SOURCE_FORM_PHASE_ID,
            "paper_id": paper_id,
            "candidate_key": candidate_key,
            "candidate_title": metadata["title"],
            "metadata_hash": metadata_hash,
            "criteria_hash": criteria_hash,
            "policy_hash": policy_hash,
            "prompt_hash": source_form_prompt_hash(),
            "cache_key": cache_key,
            "schema_version": SOURCE_FORM_SCHEMA_VERSION,
            "prompt_version": SOURCE_FORM_PROMPT_VERSION,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "policy": policy.model_dump(mode="json"),
        },
    )


def load_source_form_cache(cache_dir: Path) -> dict[str, SourceFormGateRecord]:
    rows: dict[str, SourceFormGateRecord] = {}
    paths = [cache_dir / "source_form_classifications.jsonl"]
    for path in paths:
        if not path.exists():
            continue
        for payload in read_jsonl(path):
            record = SourceFormGateRecord.model_validate(payload)
            rows[record.cache_key] = record
    return rows


def source_form_cache_record_for(
    *,
    cache_rows: dict[str, SourceFormGateRecord],
    paper_id: str,
    record: dict[str, Any],
    policy: SourceFormPolicy,
    stage1_criteria: dict[str, Any],
    model: str,
    reasoning_effort: str,
) -> SourceFormGateRecord | None:
    metadata = source_form_metadata_payload(record)
    key = source_form_cache_key(
        paper_id=paper_id,
        candidate_key=metadata["key"],
        metadata_hash=stable_hash(metadata),
        criteria_hash=stable_hash(stage1_criteria),
        policy_hash=source_form_policy_hash(policy),
        model=model,
        reasoning_effort=reasoning_effort,
    )
    return cache_rows.get(key)


def build_source_form_specs_for_records(
    *,
    paper_id: str,
    records: list[dict[str, Any]],
    policy: SourceFormPolicy,
    stage1_criteria: dict[str, Any],
    cache_rows: dict[str, SourceFormGateRecord],
    model: str,
    reasoning_effort: str,
) -> tuple[list[BatchRequestSpec], dict[str, SourceFormGateRecord]]:
    specs: list[BatchRequestSpec] = []
    hits_by_key: dict[str, SourceFormGateRecord] = {}
    for record in records:
        cached = source_form_cache_record_for(
            cache_rows=cache_rows,
            paper_id=paper_id,
            record=record,
            policy=policy,
            stage1_criteria=stage1_criteria,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        if cached is not None:
            hits_by_key[cached.candidate_key] = cached
            continue
        specs.append(
            build_source_form_request_spec(
                paper_id=paper_id,
                record=record,
                policy=policy,
                stage1_criteria=stage1_criteria,
                model=model,
                reasoning_effort=reasoning_effort,
            )
        )
    return specs, hits_by_key


def cache_records_from_parsed_successes(
    *,
    parsed_payload: dict[str, Any],
    records_by_paper: dict[str, list[dict[str, Any]]],
    policies_by_paper: dict[str, SourceFormPolicy],
    criteria_by_paper: dict[str, dict[str, Any]],
    model: str,
    reasoning_effort: str,
) -> list[SourceFormGateRecord]:
    records_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for paper_id, records in records_by_paper.items():
        for record in records:
            records_lookup[(paper_id, source_form_metadata_payload(record)["key"])] = record

    out: list[SourceFormGateRecord] = []
    for item in parsed_payload.get("successes", []):
        context = item.get("context") or {}
        paper_id = safe_text(context.get("paper_id"))
        candidate_key = safe_text(context.get("candidate_key"))
        source_record = records_lookup.get((paper_id, candidate_key))
        if source_record is None:
            continue
        classification = SourceFormClassificationOutput.model_validate(item.get("parsed") or {})
        out.append(
            build_source_form_record(
                paper_id=paper_id,
                record=source_record,
                classification=classification,
                policy=policies_by_paper[paper_id],
                stage1_criteria=criteria_by_paper[paper_id],
                model=model,
                reasoning_effort=reasoning_effort,
            )
        )
    return out


def write_source_form_cache_artifacts(
    *,
    cache_dir: Path,
    records: list[SourceFormGateRecord],
    manifest_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = load_source_form_cache(cache_dir)
    merged: dict[str, SourceFormGateRecord] = dict(existing)
    for record in records:
        merged[record.cache_key] = record
    all_rows = sorted(merged.values(), key=lambda item: (item.paper_id, item.candidate_key, item.cache_key))
    write_jsonl(cache_dir / "source_form_classifications.jsonl", [row.model_dump(mode="json") for row in all_rows])

    by_paper: dict[str, list[SourceFormGateRecord]] = defaultdict(list)
    counter: Counter[str] = Counter()
    for row in all_rows:
        by_paper[row.paper_id].append(row)
        counter[row.classification.publication_type] += 1
    papers_manifest: dict[str, Any] = {}
    for paper_id, rows in sorted(by_paper.items()):
        write_jsonl(cache_dir / "papers" / f"{paper_id}.jsonl", [row.model_dump(mode="json") for row in rows])
        papers_manifest[paper_id] = {
            "row_count": len(rows),
            "excluded_count": sum(1 for row in rows if row.gate_decision == "exclude_source_form"),
            "manual_or_unclear_pass_count": sum(1 for row in rows if row.gate_decision == "manual_or_unclear_pass"),
        }

    manifest = {
        "schema_version": SOURCE_FORM_SCHEMA_VERSION,
        "prompt_version": SOURCE_FORM_PROMPT_VERSION,
        "row_count": len(all_rows),
        "source_form_classifications_path": str(cache_dir / "source_form_classifications.jsonl"),
        "papers": papers_manifest,
        "publication_type_counts": dict(counter),
    }
    if manifest_extra:
        manifest.update(manifest_extra)
    write_json(cache_dir / "manifest.json", manifest)
    return manifest


def build_source_form_gate_result(
    *,
    paper_id: str,
    records: list[dict[str, Any]],
    policy: SourceFormPolicy,
    stage1_criteria: dict[str, Any],
    cache_dir: Path,
    model: str,
    reasoning_effort: str,
    require_cache: bool = True,
) -> dict[str, Any]:
    cache_rows = load_source_form_cache(cache_dir)
    decisions_by_key: dict[str, dict[str, Any]] = {}
    missing_keys: list[str] = []
    for record in records:
        key = source_form_metadata_payload(record)["key"]
        cached = source_form_cache_record_for(
            cache_rows=cache_rows,
            paper_id=paper_id,
            record=record,
            policy=policy,
            stage1_criteria=stage1_criteria,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        if cached is None:
            if require_cache:
                missing_keys.append(key)
                continue
            classification = SourceFormClassificationOutput(
                publication_type="unknown",
                is_primary_empirical_or_original=False,
                confidence="low",
                short_rationale="Serialization-only uncached pass-through.",
                evidence_fields_used=[],
                title_abstract_quotes=[],
            )
            cached = build_source_form_record(
                paper_id=paper_id,
                record=record,
                classification=classification,
                policy=policy,
                stage1_criteria=stage1_criteria,
                model=model,
                reasoning_effort=reasoning_effort,
            )
        decisions_by_key[key] = cached.model_dump(mode="json")
    if missing_keys:
        sample = ", ".join(missing_keys[:5])
        raise FileNotFoundError(
            f"missing source-form cache for {paper_id}: {len(missing_keys)} rows; run {SOURCE_FORM_PHASE_ID} first. sample={sample}"
        )
    excluded = [row for row in decisions_by_key.values() if row["gate_decision"] == "exclude_source_form"]
    audit_payload = {
        "paper_id": paper_id,
        "candidate_total": len(records),
        "cache_dir": str(cache_dir),
        "model": model,
        "reasoning_effort": reasoning_effort,
        "source_form_excluded_count": len(excluded),
        "manual_or_unclear_pass_count": sum(
            1 for row in decisions_by_key.values() if row["gate_decision"] == "manual_or_unclear_pass"
        ),
        "publication_type_counts": dict(Counter(row["classification"]["publication_type"] for row in decisions_by_key.values())),
        "decisions": list(decisions_by_key.values()),
    }
    return {"decisions_by_key": decisions_by_key, "audit_payload": audit_payload}


def attach_source_form_gate(row: dict[str, Any], source_form_gate: dict[str, Any]) -> dict[str, Any]:
    updated = dict(row)
    review_output = dict(updated.get("review_output") or {})
    review_output["source_form_gate"] = source_form_gate
    updated["review_output"] = review_output
    return updated


def build_source_form_filtered_row(
    *,
    paper_id: str,
    workflow_arm: str,
    stage_model: str,
    record: dict[str, Any],
    source_form_gate: dict[str, Any],
) -> dict[str, Any]:
    publication_type = source_form_gate["classification"]["publication_type"]
    return {
        "key": safe_text(record.get("key")),
        "title": safe_text(record.get("title") or record.get("query_title")),
        "paper_id": paper_id,
        "workflow_arm": workflow_arm,
        "stage_model": stage_model,
        "review_state": "source_form_filtered",
        "review_skipped": True,
        "discard_reason": f"source_form_gate:{publication_type}",
        "final_verdict": "exclude (source_form_gate)",
        "review_output": {"source_form_gate": source_form_gate},
    }
