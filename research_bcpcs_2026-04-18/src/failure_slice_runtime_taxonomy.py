#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from failure_slice_common import read_json


RUNTIME_FAILURE_CATEGORIES = {
    "runtime_failed_json_empty",
    "runtime_failed_parse",
    "runtime_failed_schema",
    "stage2_not_available",
    "fulltext_unresolved",
    "stage1_not_available",
    "none",
}


def _assistant_text_len(raw_output: dict[str, Any]) -> int:
    response = raw_output.get("response")
    if not isinstance(response, dict):
        return 0
    body = response.get("body")
    if not isinstance(body, dict):
        return 0
    choices = body.get("choices")
    if isinstance(choices, list):
        total = 0
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str):
                total += len(content)
        return total
    output = body.get("output")
    if isinstance(output, list):
        total = 0
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for chunk in item.get("content") or []:
                if isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                    total += len(chunk["text"])
        return total
    return 0


def classify_parsed_failure(failure: dict[str, Any]) -> str:
    error_type = str(failure.get("error_type") or "")
    raw_output = failure.get("raw_output") if isinstance(failure.get("raw_output"), dict) else {}
    if error_type == "JSONDecodeError" and _assistant_text_len(raw_output) == 0:
        return "runtime_failed_json_empty"
    if error_type == "JSONDecodeError":
        return "runtime_failed_parse"
    if error_type in {"ValidationError", "ValueError"}:
        return "runtime_failed_schema"
    return "runtime_failed_parse"


def load_runtime_failures(run_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    failures: dict[tuple[str, str], dict[str, Any]] = {}
    for parsed_path in sorted((run_path / "batch_jobs").glob("stage2_review*/**/parsed_results.json")):
        parsed = read_json(parsed_path)
        for failure in parsed.get("failures") or []:
            context = failure.get("context") if isinstance(failure.get("context"), dict) else {}
            paper_id = str(context.get("paper_id") or "")
            candidate_key = str(context.get("candidate_key") or "")
            if not paper_id or not candidate_key:
                continue
            failures[(paper_id, candidate_key)] = {
                "category": classify_parsed_failure(failure),
                "source_parsed_results": str(parsed_path),
                "error_type": failure.get("error_type"),
                "error": failure.get("error"),
                "custom_id": failure.get("custom_id"),
            }
    return failures


def runtime_category_for_row(row: dict[str, Any], failures: dict[tuple[str, str], dict[str, Any]]) -> str:
    key = (str(row.get("paper_id") or ""), str(row.get("candidate_key") or ""))
    failure = failures.get(key)
    if failure:
        return str(failure.get("category") or "runtime_failed_parse")
    review_state = str(row.get("review_state") or "")
    if review_state == "stage2_not_available":
        return "stage2_not_available"
    if review_state == "fulltext_unresolved":
        return "fulltext_unresolved"
    if review_state == "stage1_not_available":
        return "stage1_not_available"
    return "none"
