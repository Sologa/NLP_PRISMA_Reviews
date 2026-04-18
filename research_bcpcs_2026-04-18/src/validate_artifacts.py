#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from bcpcs_utils import RESEARCH_ROOT, load_jsonl, write_json, write_text


class ValidationError(Exception):
    pass


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def validate(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _type_matches(value, expected_type):
        raise ValidationError(f"{path}: expected {expected_type}, got {type(value).__name__}")

    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(f"{path}: {value!r} is not one of {schema['enum']!r}")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < int(min_length):
            raise ValidationError(f"{path}: string shorter than minLength={min_length}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValidationError(f"{path}: {value!r} below minimum {schema['minimum']!r}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValidationError(f"{path}: {value!r} above maximum {schema['maximum']!r}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            raise ValidationError(f"{path}: array shorter than minItems={schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate(item, item_schema, f"{path}[{index}]")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ValidationError(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ValidationError(f"{path}: unexpected properties {extra!r}")
        for key, child_schema in properties.items():
            if key in value:
                validate(value[key], child_schema, f"{path}.{key}")


def _sample_graph() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "review_id": "sample-review",
        "stage": "stage1",
        "criterion_source_path": "criteria_stage1/sample-review.json",
        "topic": "Sample review",
        "topic_definition": "Sample source-faithful definition.",
        "claims": [
            {
                "claim_id": "S1-IC1",
                "claim_text": "Title and abstract indicate target-domain NLP screening relevance.",
                "claim_type": "inclusion",
                "required_status": "support",
                "decision_operator": "all",
                "source_criterion_ids": ["IC1"],
                "stage_observability": "observable_stage1",
                "source": "source-review",
                "topic_ids": ["S1"],
            }
        ],
        "decision_graph": {
            "include_rule": "All required inclusion claims are supported.",
            "exclude_rule": "Any exclusion claim with validated refute evidence excludes.",
            "route_rule": "Unknown critical claims route.",
        },
    }


def _sample_ledger() -> dict[str, Any]:
    return {
        "candidate_key": "sample2026paper",
        "stage": "stage1",
        "claim_id": "S1-IC1",
        "evidence_status": "support",
        "support_spans": [
            {
                "quote": "This paper studies target-domain NLP screening.",
                "location": "abstract:sentence:1",
                "source_path": "refs/sample/metadata/title_abstracts_metadata.jsonl",
                "source_field": "abstract",
            }
        ],
        "refute_spans": [],
        "missingness_reason": "none",
        "confidence": 0.82,
        "verifier_model": "schema-test",
        "quote": "This paper studies target-domain NLP screening.",
        "location": "abstract:sentence:1",
        "source_path": "refs/sample/metadata/title_abstracts_metadata.jsonl",
        "span_validated": True,
    }


def _sample_atlas() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "review_id": "sample-review",
        "split_scope": "train_only",
        "archetypes": [
            {
                "archetype_id": "A1",
                "archetype_type": "contrast_pair",
                "allowed_use": "calibration_only",
                "source_provenance": {
                    "source_type": "expert_authored",
                    "source_path_or_url": "protocol/annotation_guidelines.md",
                    "built_before_eval": True,
                },
                "contrast_claim_ids": ["S1-IC1", "S1-EC1"],
                "forbidden_eval_keys": ["heldout_key_1"],
            }
        ],
    }


def main() -> int:
    schema_dir = RESEARCH_ROOT / "schemas"
    schemas = {
        "eligibility_graph": json.loads((schema_dir / "eligibility_graph.schema.json").read_text(encoding="utf-8")),
        "evidence_ledger": json.loads((schema_dir / "evidence_ledger.schema.json").read_text(encoding="utf-8")),
        "boundary_atlas": json.loads((schema_dir / "boundary_atlas.schema.json").read_text(encoding="utf-8")),
    }
    samples = {
        "eligibility_graph": _sample_graph(),
        "evidence_ledger": _sample_ledger(),
        "boundary_atlas": _sample_atlas(),
    }

    results: list[dict[str, Any]] = []
    for name, schema in schemas.items():
        validate(samples[name], schema)
        results.append({"artifact": name, "case": "valid_sample", "status": "passed"})

    invalid_graph = copy.deepcopy(samples["eligibility_graph"])
    del invalid_graph["claims"][0]["claim_text"]
    invalid_ledger = copy.deepcopy(samples["evidence_ledger"])
    invalid_ledger["confidence"] = 1.5
    invalid_atlas = copy.deepcopy(samples["boundary_atlas"])
    invalid_atlas["archetypes"][0]["source_provenance"]["built_before_eval"] = "yes"
    invalid_samples = {
        "eligibility_graph": invalid_graph,
        "evidence_ledger": invalid_ledger,
        "boundary_atlas": invalid_atlas,
    }

    for name, invalid in invalid_samples.items():
        try:
            validate(invalid, schemas[name])
        except ValidationError as exc:
            results.append({"artifact": name, "case": "invalid_sample", "status": "rejected", "reason": str(exc)})
        else:
            raise SystemExit(f"Invalid sample unexpectedly passed: {name}")

    for graph_path in sorted((RESEARCH_ROOT / "runs/dry_run_loader/stub_graphs").glob("*.eligibility_graph.json")):
        validate(json.loads(graph_path.read_text(encoding="utf-8")), schemas["eligibility_graph"])
        results.append(
            {
                "artifact": "eligibility_graph",
                "case": str(graph_path.relative_to(RESEARCH_ROOT)),
                "status": "passed",
            }
        )

    for ledger_path in [
        RESEARCH_ROOT / "runs/dry_run_loader/sample_stage1_ledger.jsonl",
        RESEARCH_ROOT / "runs/smoke/smoke_ledger.jsonl",
    ]:
        if not ledger_path.exists():
            continue
        count = 0
        for row in load_jsonl(ledger_path):
            validate(row, schemas["evidence_ledger"])
            count += 1
        results.append(
            {
                "artifact": "evidence_ledger",
                "case": str(ledger_path.relative_to(RESEARCH_ROOT)),
                "status": "passed",
                "reason": f"{count} records",
            }
        )

    write_json(RESEARCH_ROOT / "runs/schema_validation/schema_validation.json", {"results": results})
    lines = [
        "# Schema Validation",
        "",
        "Validation used local Draft-2020-12-style schemas plus a minimal in-repo validator for the schema features used here.",
        "",
        "| Artifact | Case | Status | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for row in results:
        lines.append(
            f"| {row['artifact']} | {row['case']} | {row['status']} | {row.get('reason', '')} |"
        )
    lines.append("")
    write_text(RESEARCH_ROOT / "reports/schema_validation.md", "\n".join(lines))
    print("validated schemas and sample artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
