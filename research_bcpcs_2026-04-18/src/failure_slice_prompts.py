#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any


def _json_block(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


SYSTEM_BOUNDARY = """You are a single screening reviewer running a BCPCS failure-slice diagnostic.
Use only the evidence supplied in this prompt. Do not infer from prior benchmarks or external knowledge.
Return only JSON matching the response schema."""


OUTPUT_RULES = """Output requirements:
- Produce final_stage_decision as one of include, exclude, maybe, route_to_stage2, unknown.
- Fill a claim-level evidence_ledger for each decisive inclusion/exclusion criterion you used.
- Each ledger row must include support_spans, refute_spans, missingness_reason, confidence, quote, location, source_path, and span_validated.
- Use span_validated=true only when the quote is an exact substring of the supplied title, abstract, metadata, criteria, or full text.
- Do not convert missing full text, retrieval failure, or metadata ambiguity into a semantic exclusion.
- For unresolved evidence, use unknown or route_to_stage2 with a concise route_reason."""


def build_stage1_prompt(
    *,
    paper_id: str,
    candidate_key: str,
    criteria: dict[str, Any],
    metadata: dict[str, Any],
    criteria_path: str,
    metadata_path: str,
) -> str:
    visible_metadata = {
        "candidate_key": candidate_key,
        "title": metadata.get("title") or metadata.get("query_title") or "",
        "abstract": metadata.get("abstract") or "",
        "metadata": {
            "source": metadata.get("source"),
            "source_id": metadata.get("source_id"),
            "match_status": metadata.get("match_status"),
            "missing_reason": metadata.get("missing_reason"),
            "published_date": metadata.get("published_date"),
        },
        "source_paths": {
            "criteria_path": criteria_path,
            "metadata_path": metadata_path,
        },
    }
    return "\n\n".join(
        [
            SYSTEM_BOUNDARY,
            "Stage 1 task: decide from title, abstract, metadata, and stage-specific criteria only.",
            "Stage 1 unknown evidence must route forward, not silently become exclude.",
            OUTPUT_RULES,
            "Stage 1 criteria JSON:",
            _json_block(criteria),
            "Candidate visible record:",
            _json_block(visible_metadata),
        ]
    )


def build_stage2_prompt(
    *,
    paper_id: str,
    candidate_key: str,
    criteria: dict[str, Any],
    metadata: dict[str, Any],
    fulltext_text: str,
    fulltext_meta: dict[str, Any],
    stage1_handoff: dict[str, Any],
    criteria_path: str,
    metadata_path: str,
) -> str:
    visible_payload = {
        "candidate_key": candidate_key,
        "title": metadata.get("title") or metadata.get("query_title") or "",
        "abstract": metadata.get("abstract") or "",
        "metadata": {
            "source": metadata.get("source"),
            "source_id": metadata.get("source_id"),
            "match_status": metadata.get("match_status"),
            "missing_reason": metadata.get("missing_reason"),
            "published_date": metadata.get("published_date"),
        },
        "source_paths": {
            "criteria_path": criteria_path,
            "metadata_path": metadata_path,
            "fulltext_source_path": fulltext_meta.get("fulltext_source_path"),
        },
        "fulltext_meta": fulltext_meta,
        "stage1_bcpcs_handoff": stage1_handoff,
    }
    missingness_policy = {
        "allowed_stage2_missingness_reasons": [
            "none",
            "semantic_non_fit",
            "retrieval_failure",
            "metadata_ambiguity",
            "source_gold_tension",
            "evidence_incomplete",
            "not_applicable",
        ],
        "policy": "A retrieval or metadata problem must be marked as such and cannot be represented as semantic_non_fit.",
    }
    return "\n\n".join(
        [
            SYSTEM_BOUNDARY,
            "Stage 2 task: decide from full text, title, abstract, metadata, Stage 1 handoff, and stage-specific criteria.",
            "Distinguish semantic_non_fit, retrieval_failure, metadata_ambiguity, source_gold_tension, and evidence_incomplete.",
            OUTPUT_RULES,
            "Stage 2 criteria JSON:",
            _json_block(criteria),
            "Stage 2 missingness policy:",
            _json_block(missingness_policy),
            "Candidate visible record and Stage 1 handoff:",
            _json_block(visible_payload),
            "Full text:",
            fulltext_text,
        ]
    )

