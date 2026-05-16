#!/usr/bin/env python3
"""Run the experiment-only primary evidence gate overlay."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = SCRIPT_DIR.parent
REPO_ROOT = BUNDLE_DIR.parents[1]
SCREENING_ROOT = REPO_ROOT / "scripts" / "screening"

if str(SCREENING_ROOT) not in sys.path:
    sys.path.insert(0, str(SCREENING_ROOT))

from openai_batch_runner import BatchRequestSpec, OpenAIBatchRunner, build_json_schema_response_format  # noqa: E402


CONFIG_PATH = BUNDLE_DIR / "config" / "experiment_config.json"
MANIFEST_PATH = BUNDLE_DIR / "manifest.json"
RESULTS_ROOT = REPO_ROOT / "screening" / "results" / "primary_evidence_gate_overlay_2026-05-16"
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
PAPER_IDS = ("2409.13738", "2511.13936", "2601.19926")
EXCLUDED_PAPER_IDS = {"2307.05527"}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PrimaryEvidenceGateOutput(_StrictModel):
    is_primary: bool
    gate_decision: Literal["pass_primary", "exclude_non_primary", "unclear_pass"]
    publication_type: Literal[
        "primary_empirical",
        "secondary_review_or_survey",
        "position_or_commentary",
        "standards_or_book_or_tool_doc",
        "non_empirical_other",
        "unknown",
    ]
    criteria_exception_applied: bool
    short_rationale: str
    evidence_fields_used: list[str] = Field(default_factory=list)
    title_abstract_quotes: list[str] = Field(default_factory=list)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL in {path}:{index}: {exc}") from exc
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _run_dir(run_id: str) -> Path:
    return RESULTS_ROOT / "runs" / run_id


def _batch_artifact_dir(run_id: str, model: str) -> Path:
    return _run_dir(run_id) / "batch_jobs" / "primary_evidence_gate" / model


def _paper_dir(run_id: str, paper_id: str) -> Path:
    return _run_dir(run_id) / "papers" / paper_id


def _load_config() -> dict[str, Any]:
    payload = _read_json(CONFIG_PATH)
    required = {
        "model",
        "reasoning_effort",
        "papers",
        "endpoint",
        "completion_window",
        "batch_poll_interval_sec",
        "batch_max_wait_minutes",
        "role_review_source_results",
        "direct_review_source_run",
        "role_positive_labels",
        "template",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise SystemExit("config missing fields: " + ", ".join(missing))
    return payload


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


def _render(template_text: str, context: dict[str, Any]) -> str:
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            missing.append(key)
            return match.group(0)
        value = context[key]
        if isinstance(value, str):
            return value
        return _json_text(value)

    rendered = PLACEHOLDER_RE.sub(replace, template_text)
    if missing:
        raise KeyError("missing placeholders: " + ", ".join(sorted(set(missing))))
    return rendered


def _metadata_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"


def _gold_path(paper_id: str) -> Path:
    return REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"


def _stage1_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage1" / f"{paper_id}.json"


def _stage2_criteria_path(paper_id: str) -> Path:
    return REPO_ROOT / "criteria_stage2" / f"{paper_id}.json"


def _source_role_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    path = REPO_ROOT / str(config["role_review_source_results"])
    rows = _read_json(path)
    if not isinstance(rows, list):
        raise SystemExit(f"Role source is not a list: {path}")
    return [row for row in rows if isinstance(row, dict)]


def _metadata_by_key(paper_id: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(_metadata_path(paper_id)):
        key = _safe_text(row.get("key"))
        if key and key not in out:
            out[key] = row
    return out


def _selected_gate_keys_by_paper(config: dict[str, Any]) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = {paper_id: [] for paper_id in PAPER_IDS}
    seen: dict[str, set[str]] = {paper_id: set() for paper_id in PAPER_IDS}
    for row in _source_role_rows(config):
        paper_id = _safe_text(row.get("paper_id"))
        if paper_id in EXCLUDED_PAPER_IDS:
            continue
        if paper_id not in selected:
            continue
        if _safe_text(row.get("review_state")) != "reviewed":
            continue
        key = _safe_text(row.get("key"))
        if not key or key in seen[paper_id]:
            continue
        seen[paper_id].add(key)
        selected[paper_id].append(key)
    return selected


def _derive_primary_policy(paper_id: str, stage1: dict[str, Any], stage2: dict[str, Any]) -> dict[str, Any]:
    criteria_text = json.dumps({"stage1": stage1, "stage2": stage2}, ensure_ascii=False).lower()
    exclusion_markers = [
        "secondary research articles are excluded",
        "survey or review articles are excluded",
        "not a survey or review article",
        "no clear empirical component",
        "position paper, survey, or review",
        "primary research article",
        "original research contribution",
    ]
    explicit_allow_markers = [
        "secondary research articles are eligible",
        "survey articles are eligible",
        "review articles are eligible",
        "surveys are included",
        "reviews are included",
    ]
    matched_exclusions = [marker for marker in exclusion_markers if marker in criteria_text]
    matched_allows = [marker for marker in explicit_allow_markers if marker in criteria_text]
    exception_allows_secondary = bool(matched_allows) and not matched_exclusions
    return {
        "paper_id": paper_id,
        "gate_default_active": not exception_allows_secondary,
        "criteria_exception_allows_secondary": exception_allows_secondary,
        "matched_exclusion_markers": matched_exclusions,
        "matched_allow_markers": matched_allows,
        "policy": (
            "Secondary/survey/review/non-primary source forms are excluded before review."
            if not exception_allows_secondary
            else "Criteria explicitly allow secondary/review source forms; do not exclude solely for publication form."
        ),
    }


def _candidate_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": _safe_text(record.get("key")),
        "query_title": _safe_text(record.get("query_title")),
        "title": _safe_text(record.get("title") or record.get("query_title")),
        "abstract": _safe_text(record.get("abstract")),
        "source": _safe_text(record.get("source")),
        "source_id": _safe_text(record.get("source_id")),
        "match_status": _safe_text(record.get("match_status")),
        "published_date": _safe_text(record.get("published_date")),
        "artifact_gate_pass": record.get("artifact_gate_pass"),
        "artifact_gate_reason": _safe_text(record.get("artifact_gate_reason")),
    }


def _build_input_manifest(config: dict[str, Any]) -> dict[str, Any]:
    selected = _selected_gate_keys_by_paper(config)
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for paper_id in PAPER_IDS:
        metadata = _metadata_by_key(paper_id)
        stage1 = _read_json(_stage1_criteria_path(paper_id))
        stage2 = _read_json(_stage2_criteria_path(paper_id))
        policy = _derive_primary_policy(paper_id, stage1, stage2)
        missing_keys: list[str] = []
        for key in selected[paper_id]:
            record = metadata.get(key)
            if record is None:
                missing_keys.append(key)
                continue
            rows.append(
                {
                    "paper_id": paper_id,
                    "key": key,
                    "title": _safe_text(record.get("title") or record.get("query_title")),
                    "metadata_path": _relative(_metadata_path(paper_id)),
                    "stage1_criteria_path": _relative(_stage1_criteria_path(paper_id)),
                    "stage2_criteria_path": _relative(_stage2_criteria_path(paper_id)),
                    "criteria_primary_gate_policy": policy,
                    "metadata": _candidate_payload(record),
                }
            )
        if missing_keys:
            raise SystemExit(f"{paper_id} selected keys missing metadata: {missing_keys[:10]}")
        counts[paper_id] = len(selected[paper_id])
    if any(row["paper_id"] in EXCLUDED_PAPER_IDS for row in rows):
        raise SystemExit("2307.05527 leaked into primary gate inputs")
    return {
        "experiment_id": config["experiment_id"],
        "model": config["model"],
        "reasoning_effort": config["reasoning_effort"],
        "papers": list(PAPER_IDS),
        "excluded_papers": sorted(EXCLUDED_PAPER_IDS),
        "gate_key_source": config["role_review_source_results"],
        "counts_by_paper": counts,
        "total": len(rows),
        "rows": rows,
    }


def _custom_id(paper_id: str, key: str) -> str:
    safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)[:120]
    return f"primary_gate:{paper_id}:{safe_key}"


def _build_body(*, model: str, prompt: str, reasoning_effort: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": build_json_schema_response_format(
            PrimaryEvidenceGateOutput,
            schema_name="primary_evidence_gate_output",
        ),
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    return body


def _build_specs(
    config: dict[str, Any],
    input_manifest: dict[str, Any],
) -> list[BatchRequestSpec]:
    template = (BUNDLE_DIR / str(config["template"])).read_text(encoding="utf-8")
    specs: list[BatchRequestSpec] = []
    for row in input_manifest["rows"]:
        paper_id = row["paper_id"]
        stage1 = _read_json(REPO_ROOT / row["stage1_criteria_path"])
        stage2 = _read_json(REPO_ROOT / row["stage2_criteria_path"])
        prompt = _render(
            template,
            {
                "PAPER_ID": paper_id,
                "METADATA_JSON": row["metadata"],
                "CRITERIA_PRIMARY_GATE_POLICY_JSON": row["criteria_primary_gate_policy"],
                "STAGE1_CRITERIA_JSON": stage1,
                "STAGE2_CRITERIA_JSON": stage2,
            },
        )
        specs.append(
            BatchRequestSpec(
                custom_id=_custom_id(paper_id, row["key"]),
                model=str(config["model"]),
                body=_build_body(
                    model=str(config["model"]),
                    prompt=prompt,
                    reasoning_effort=str(config.get("reasoning_effort") or "") or None,
                ),
                response_model=PrimaryEvidenceGateOutput,
                context={
                    "paper_id": paper_id,
                    "candidate_key": row["key"],
                    "candidate_title": row["title"],
                    "metadata_path": row["metadata_path"],
                    "stage1_criteria_path": row["stage1_criteria_path"],
                    "stage2_criteria_path": row["stage2_criteria_path"],
                    "criteria_primary_gate_policy": row["criteria_primary_gate_policy"],
                },
            )
        )
    return specs


def _run_manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / "run_manifest.json"


def _load_run_manifest(run_id: str) -> dict[str, Any]:
    path = _run_manifest_path(run_id)
    if not path.exists():
        return {}
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _save_run_manifest(run_id: str, payload: dict[str, Any]) -> None:
    payload["run_id"] = run_id
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json(_run_manifest_path(run_id), payload)


def prepare(run_id: str, config: dict[str, Any]) -> tuple[dict[str, Any], list[BatchRequestSpec]]:
    run_dir = _run_dir(run_id)
    manifest = _build_input_manifest(config)
    specs = _build_specs(config, manifest)
    artifact_dir = _batch_artifact_dir(run_id, str(config["model"]))
    runner = OpenAIBatchRunner(client=object(), poll_interval_sec=float(config["batch_poll_interval_sec"]))
    serialized = runner.serialize_requests(specs, endpoint=str(config["endpoint"]))
    _write_json(run_dir / "gate_input_manifest.json", manifest)
    _write_jsonl(artifact_dir / "input.jsonl", serialized)
    if specs:
        prompt = str(specs[0].body["messages"][0]["content"])
        (run_dir / "rendered_prompt_example.md").write_text(prompt, encoding="utf-8")
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in manifest["rows"]:
        by_paper[row["paper_id"]].append(row)
    for paper_id, rows in by_paper.items():
        _write_json(_paper_dir(run_id, paper_id) / "gate_input_manifest.json", {"paper_id": paper_id, "rows": rows})
    run_manifest = {
        **_load_run_manifest(run_id),
        "experiment_id": config["experiment_id"],
        "mode": "prepare",
        "model": config["model"],
        "reasoning_effort": config["reasoning_effort"],
        "input_counts_by_paper": manifest["counts_by_paper"],
        "input_total": manifest["total"],
        "batch_artifact_dir": _relative(artifact_dir),
        "batch_status": "not_submitted",
    }
    _save_run_manifest(run_id, run_manifest)
    return manifest, specs


def submit(run_id: str, config: dict[str, Any]) -> None:
    manifest, specs = prepare(run_id, config)
    if manifest["total"] != 499:
        raise SystemExit(f"Expected 499 gate inputs, got {manifest['total']}")
    _load_env_file()
    client = OpenAI()
    artifact_dir = _batch_artifact_dir(run_id, str(config["model"]))
    runner = OpenAIBatchRunner(client=client, poll_interval_sec=float(config["batch_poll_interval_sec"]))
    payload = runner.submit_requests(
        specs=specs,
        endpoint=str(config["endpoint"]),
        artifact_dir=artifact_dir,
        metadata={
            "experiment_id": config["experiment_id"],
            "run_id": run_id,
            "phase": "primary_evidence_gate",
        },
        completion_window=str(config["completion_window"]),
    )
    run_manifest = {
        **_load_run_manifest(run_id),
        "mode": "submit",
        "batch_id": payload["batch_create"]["id"],
        "batch_status": payload["batch_create"]["status"],
        "batch_input_file_id": payload["upload_file"]["id"],
    }
    _save_run_manifest(run_id, run_manifest)
    print(f"[submit] batch_id={payload['batch_create']['id']}", flush=True)


def _success_rows(parsed_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in parsed_payload.get("successes", []):
        context = item.get("context") or {}
        parsed = item.get("parsed") or {}
        row = {
            "paper_id": context.get("paper_id"),
            "key": context.get("candidate_key"),
            "title": context.get("candidate_title"),
            "is_primary": parsed.get("is_primary"),
            "gate_decision": parsed.get("gate_decision"),
            "publication_type": parsed.get("publication_type"),
            "criteria_exception_applied": parsed.get("criteria_exception_applied"),
            "short_rationale": parsed.get("short_rationale"),
            "evidence_fields_used": parsed.get("evidence_fields_used") or [],
            "title_abstract_quotes": parsed.get("title_abstract_quotes") or [],
            "criteria_primary_gate_policy": context.get("criteria_primary_gate_policy"),
            "custom_id": item.get("custom_id"),
        }
        rows.append(row)
    return rows


def collect(run_id: str, config: dict[str, Any], *, batch_poll_interval_sec: float | None, batch_max_wait_minutes: float | None) -> None:
    manifest, specs = prepare(run_id, config)
    run_manifest = _load_run_manifest(run_id)
    batch_id = run_manifest.get("batch_id")
    if not batch_id:
        raise SystemExit("No batch_id in run_manifest; submit first.")
    _load_env_file()
    client = OpenAI()
    artifact_dir = _batch_artifact_dir(run_id, str(config["model"]))
    runner = OpenAIBatchRunner(
        client=client,
        poll_interval_sec=float(batch_poll_interval_sec or config["batch_poll_interval_sec"]),
    )
    batch_payload = runner.wait_until_terminal(
        str(batch_id),
        artifact_dir=artifact_dir,
        max_wait_minutes=float(batch_max_wait_minutes or config["batch_max_wait_minutes"]),
    )
    parsed_payload = runner.collect_results(specs=specs, batch_payload=batch_payload, artifact_dir=artifact_dir)
    if batch_payload.get("status") != "completed":
        raise SystemExit(f"Batch did not complete: {batch_payload.get('status')}")
    if parsed_payload.get("failures") or parsed_payload.get("missing"):
        raise SystemExit(
            "Batch parse incomplete: "
            f"failures={len(parsed_payload.get('failures', []))} "
            f"missing={len(parsed_payload.get('missing', []))}"
        )
    rows = _success_rows(parsed_payload)
    if len(rows) != manifest["total"]:
        raise SystemExit(f"Expected {manifest['total']} gate rows, got {len(rows)}")
    rows.sort(key=lambda row: (str(row["paper_id"]), str(row["key"])))
    _write_json(_run_dir(run_id) / "primary_gate_results.json", rows)
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_paper[str(row["paper_id"])].append(row)
    gate_counts_by_paper: dict[str, dict[str, int]] = {}
    for paper_id in PAPER_IDS:
        paper_rows = by_paper.get(paper_id, [])
        _write_json(_paper_dir(run_id, paper_id) / "primary_gate_results.json", paper_rows)
        gate_counts_by_paper[paper_id] = dict(Counter(str(row["gate_decision"]) for row in paper_rows))
    run_manifest = {
        **run_manifest,
        "mode": "collect",
        "batch_status": batch_payload.get("status"),
        "batch_completed_at": batch_payload.get("completed_at"),
        "batch_output_file_id": batch_payload.get("output_file_id"),
        "gate_output_total": len(rows),
        "gate_counts_by_paper": gate_counts_by_paper,
    }
    _save_run_manifest(run_id, run_manifest)
    print(f"[collect] batch_status={batch_payload.get('status')} rows={len(rows)}", flush=True)


def _load_gate_by_paper(run_id: str) -> dict[str, dict[str, dict[str, Any]]]:
    path = _run_dir(run_id) / "primary_gate_results.json"
    if not path.exists():
        raise SystemExit(f"Missing gate results: {path}")
    rows = _read_json(path)
    if not isinstance(rows, list):
        raise SystemExit(f"Gate results are not a list: {path}")
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        paper_id = _safe_text(row.get("paper_id"))
        key = _safe_text(row.get("key"))
        if not paper_id or not key:
            raise SystemExit(f"Gate row missing paper/key: {row}")
        out[paper_id][key] = row
    return out


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return None


def _gold_map(paper_id: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in _read_jsonl(_gold_path(paper_id)):
        key = _safe_text(row.get("key"))
        label = _parse_bool(row.get("is_evidence_base"))
        if key and label is not None:
            out[key] = 1 if label else 0
    return out


def _verdict_positive(final_verdict: Any) -> int:
    label = str(final_verdict or "").strip().lower()
    match = re.match(r"^\s*([a-z]+)", label)
    if not match:
        return 0
    return 1 if match.group(1) in {"include", "maybe"} else 0


def _role_positive(row: dict[str, Any], positive_roles: set[str]) -> int:
    role = _safe_text(row.get("stage2_decision_recommendation") or row.get("final_role"))
    return 1 if role in positive_roles else 0


def _prf(tp: int, fp: int, tn: int, fn: int) -> dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def _binary_metrics(rows: list[dict[str, Any]], paper_id: str, pred_fn: Any) -> dict[str, Any]:
    gold = _gold_map(paper_id)
    tp = fp = tn = fn = 0
    missing: list[str] = []
    for row in rows:
        key = _safe_text(row.get("key"))
        if not key:
            continue
        if key not in gold:
            missing.append(key)
            continue
        pred = int(pred_fn(row))
        actual = gold[key]
        if actual == 1 and pred == 1:
            tp += 1
        elif actual == 1 and pred == 0:
            fn += 1
        elif actual == 0 and pred == 1:
            fp += 1
        else:
            tn += 1
    metrics = _prf(tp, fp, tn, fn)
    metrics.update({"paper_id": paper_id, "matched": tp + fp + tn + fn, "missing_gold_count": len(missing)})
    return metrics


def _aggregate_metric_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(int(report["tp"]) for report in reports)
    fp = sum(int(report["fp"]) for report in reports)
    tn = sum(int(report["tn"]) for report in reports)
    fn = sum(int(report["fn"]) for report in reports)
    metrics = _prf(tp, fp, tn, fn)
    metrics["matched"] = sum(int(report["matched"]) for report in reports)
    return metrics


def _is_cutoff_or_artifact_row(row: dict[str, Any]) -> bool:
    state = _safe_text(row.get("review_state"))
    verdict = _safe_text(row.get("final_verdict"))
    return state in {"cutoff_filtered", "artifact_filtered"} or verdict in {
        "exclude (cutoff_time_window)",
        "exclude (artifact_gate)",
    }


def _gate_excludes(gate_row: dict[str, Any] | None) -> bool:
    if not gate_row or gate_row.get("gate_decision") != "exclude_non_primary":
        return False
    publication_type = str(gate_row.get("publication_type") or "")
    if publication_type in {"secondary_review_or_survey", "position_or_commentary"}:
        return True
    if publication_type == "standards_or_book_or_tool_doc":
        return _is_guideline_or_standard_gate(gate_row)
    return False


def _is_guideline_or_standard_gate(gate_row: dict[str, Any]) -> bool:
    evidence_parts = [
        _safe_text(gate_row.get("title")),
        _safe_text(gate_row.get("short_rationale")),
        *[_safe_text(item) for item in (gate_row.get("title_abstract_quotes") or [])],
    ]
    evidence = " ".join(evidence_parts).lower()
    markers = {
        "guideline",
        "guidelines",
        "checklist",
        "reporting guidance",
        "reporting guideline",
        "updated guideline",
        "statement",
        "standard",
        "standards",
        "specification",
        "notation",
        "prisma",
        "bpmn",
        "business process model and notation",
    }
    return any(marker in evidence for marker in markers)


def _apply_direct_gate(row: dict[str, Any], gate_row: dict[str, Any] | None) -> dict[str, Any]:
    out = copy.deepcopy(row)
    if _is_cutoff_or_artifact_row(out) or not _gate_excludes(gate_row):
        return out
    out["pre_primary_gate_final_verdict"] = out.get("final_verdict")
    out["pre_primary_gate_review_state"] = out.get("review_state")
    out["review_state"] = "primary_gate_filtered"
    out["review_skipped"] = True
    out["discard_reason"] = f"primary_evidence_gate:{gate_row.get('publication_type')}"
    out["final_verdict"] = "exclude (primary_evidence_gate)"
    out["primary_evidence_gate"] = gate_row
    review_output = out.get("review_output")
    if not isinstance(review_output, dict):
        review_output = {}
    review_output["primary_evidence_gate"] = gate_row
    out["review_output"] = review_output
    return out


def _apply_role_gate(row: dict[str, Any], gate_row: dict[str, Any] | None) -> dict[str, Any]:
    out = copy.deepcopy(row)
    if not _gate_excludes(gate_row):
        return out
    out["pre_primary_gate_final_role"] = out.get("final_role")
    out["pre_primary_gate_stage2_decision_recommendation"] = out.get("stage2_decision_recommendation")
    out["review_state"] = "primary_gate_filtered"
    out["review_skipped"] = True
    out["final_role"] = "required_non_topic"
    out["stage2_decision_recommendation"] = "required_non_topic"
    out["primary_evidence_gate"] = gate_row
    review_output = out.get("review_output")
    if not isinstance(review_output, dict):
        review_output = {}
    review_output["primary_evidence_gate"] = gate_row
    out["review_output"] = review_output
    return out


def _build_exclusion_audit(
    *,
    gate_exclusion_rows: list[dict[str, Any]],
    role_before_by_paper: dict[str, list[dict[str, Any]]],
    direct_before_by_paper: dict[str, list[dict[str, Any]]],
    role_positive: set[str],
) -> list[dict[str, Any]]:
    role_by_key = {
        (paper_id, _safe_text(row.get("key"))): row
        for paper_id, rows in role_before_by_paper.items()
        for row in rows
    }
    direct_by_key = {
        (paper_id, _safe_text(row.get("key"))): row
        for paper_id, rows in direct_before_by_paper.items()
        for row in rows
    }
    gold_cache = {paper_id: _gold_map(paper_id) for paper_id in PAPER_IDS}
    out: list[dict[str, Any]] = []
    for gate_row in sorted(gate_exclusion_rows, key=lambda row: (str(row["paper_id"]), str(row["key"]))):
        paper_id = str(gate_row["paper_id"])
        key = str(gate_row["key"])
        role_row = role_by_key.get((paper_id, key), {})
        direct_row = direct_by_key.get((paper_id, key), {})
        gold_value = gold_cache.get(paper_id, {}).get(key)
        out.append(
            {
                "paper_id": paper_id,
                "key": key,
                "title": gate_row.get("title"),
                "gold_is_evidence_base": None if gold_value is None else bool(gold_value),
                "gate_decision": gate_row.get("gate_decision"),
                "publication_type": gate_row.get("publication_type"),
                "short_rationale": gate_row.get("short_rationale"),
                "title_abstract_quotes": gate_row.get("title_abstract_quotes") or [],
                "criteria_exception_applied": gate_row.get("criteria_exception_applied"),
                "role_before_label": role_row.get("stage2_decision_recommendation") or role_row.get("final_role"),
                "role_before_positive": bool(_role_positive(role_row, role_positive)) if role_row else None,
                "direct_before_final_verdict": direct_row.get("final_verdict"),
                "direct_before_positive": bool(_verdict_positive(direct_row.get("final_verdict"))) if direct_row else None,
                "introduced_false_negative": bool(gold_value == 1),
            }
        )
    return out


def _direct_source_path(config: dict[str, Any], paper_id: str) -> Path:
    return REPO_ROOT / str(config["direct_review_source_run"]) / "papers" / paper_id / "single_reviewer_batch_results.json"


def _role_source_rows_for_paper(config: dict[str, Any], paper_id: str) -> list[dict[str, Any]]:
    return [row for row in _source_role_rows(config) if _safe_text(row.get("paper_id")) == paper_id]


def _run_eval_review_f1(paper_id: str, results_path: Path, report_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        paper_id,
        "--results",
        str(results_path),
        "--gold-metadata",
        str(_gold_path(paper_id)),
        "--save-report",
        str(report_path),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(
            f"evaluate_review_f1 failed for {paper_id}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return _read_json(report_path)


def _diff_metrics(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "before": before,
        "after": after,
        "delta": {
            "precision": after["precision"] - before["precision"],
            "recall": after["recall"] - before["recall"],
            "f1": after["f1"] - before["f1"],
            "tp": after["tp"] - before["tp"],
            "fp": after["fp"] - before["fp"],
            "tn": after["tn"] - before["tn"],
            "fn": after["fn"] - before["fn"],
        },
    }


def overlay(run_id: str, config: dict[str, Any]) -> None:
    gate_by_paper = _load_gate_by_paper(run_id)
    run_dir = _run_dir(run_id)
    overlay_root = run_dir / "overlays"
    role_positive = set(str(item) for item in config["role_positive_labels"])

    role_before_reports: list[dict[str, Any]] = []
    role_after_reports: list[dict[str, Any]] = []
    direct_before_reports: list[dict[str, Any]] = []
    direct_after_reports: list[dict[str, Any]] = []
    model_exclusion_rows: list[dict[str, Any]] = []
    gate_exclusion_rows: list[dict[str, Any]] = []
    role_before_by_paper: dict[str, list[dict[str, Any]]] = {}
    direct_before_by_paper: dict[str, list[dict[str, Any]]] = {}
    row_count_checks: dict[str, Any] = {"role_review_corrected": {}, "direct_review_comparator": {}}

    role_combined_after: list[dict[str, Any]] = []
    direct_combined_after: list[dict[str, Any]] = []

    for paper_id in PAPER_IDS:
        gate_for_paper = gate_by_paper.get(paper_id, {})
        if not gate_for_paper:
            raise SystemExit(f"No gate rows for {paper_id}")

        role_source = _role_source_rows_for_paper(config, paper_id)
        role_before_by_paper[paper_id] = role_source
        role_after = [_apply_role_gate(row, gate_for_paper.get(_safe_text(row.get("key")))) for row in role_source]
        role_combined_after.extend(role_after)
        role_paper_dir = overlay_root / "role_review_corrected" / "papers" / paper_id
        _write_json(role_paper_dir / "role_review_results.primary_gate_overlay.json", role_after)
        role_before = _binary_metrics(role_source, paper_id, lambda row: _role_positive(row, role_positive))
        role_after_metrics = _binary_metrics(role_after, paper_id, lambda row: _role_positive(row, role_positive))
        role_before_reports.append(role_before)
        role_after_reports.append(role_after_metrics)
        _write_json(role_paper_dir / "role_review_metrics.primary_gate_overlay.json", _diff_metrics(role_before, role_after_metrics))
        row_count_checks["role_review_corrected"][paper_id] = {
            "before": len(role_source),
            "after": len(role_after),
            "same_keys": sorted(_safe_text(row.get("key")) for row in role_source)
            == sorted(_safe_text(row.get("key")) for row in role_after),
        }

        direct_source_path = _direct_source_path(config, paper_id)
        direct_source = _read_json(direct_source_path)
        if not isinstance(direct_source, list):
            raise SystemExit(f"Direct source is not list: {direct_source_path}")
        direct_before_by_paper[paper_id] = direct_source
        direct_after = [_apply_direct_gate(row, gate_for_paper.get(_safe_text(row.get("key")))) for row in direct_source]
        direct_combined_after.extend(direct_after)
        direct_paper_dir = overlay_root / "direct_review_comparator" / "papers" / paper_id
        direct_result_path = direct_paper_dir / "single_reviewer_batch_results.primary_gate_overlay.json"
        _write_json(direct_result_path, direct_after)
        before_report = _run_eval_review_f1(
            paper_id,
            direct_source_path,
            direct_paper_dir / "single_reviewer_batch_f1.before_recomputed.json",
        )
        after_report = _run_eval_review_f1(
            paper_id,
            direct_result_path,
            direct_paper_dir / "single_reviewer_batch_f1.primary_gate_overlay.json",
        )
        direct_before = before_report["metrics"]
        direct_after_metrics = after_report["metrics"]
        direct_before_reports.append({**direct_before, "paper_id": paper_id, "matched": after_report["matched"]})
        direct_after_reports.append({**direct_after_metrics, "paper_id": paper_id, "matched": after_report["matched"]})
        _write_json(direct_paper_dir / "single_reviewer_batch_f1.before_after_diff.json", _diff_metrics(direct_before, direct_after_metrics))
        row_count_checks["direct_review_comparator"][paper_id] = {
            "before": len(direct_source),
            "after": len(direct_after),
            "same_keys": sorted(_safe_text(row.get("key")) for row in direct_source)
            == sorted(_safe_text(row.get("key")) for row in direct_after),
            "cutoff_unchanged": all(
                before == after
                for before, after in zip(direct_source, direct_after)
                if _safe_text(before.get("final_verdict")) == "exclude (cutoff_time_window)"
            ),
        }

        for gate_row in gate_for_paper.values():
            if gate_row.get("gate_decision") == "exclude_non_primary":
                model_exclusion_rows.append(gate_row)
            if _gate_excludes(gate_row):
                gate_exclusion_rows.append(gate_row)

    _write_json(overlay_root / "role_review_corrected" / "role_review_results_3papers.primary_gate_overlay.json", role_combined_after)
    _write_json(
        overlay_root / "direct_review_comparator" / "single_reviewer_batch_results_3papers.primary_gate_overlay.json",
        direct_combined_after,
    )

    role_before_overall = _aggregate_metric_reports(role_before_reports)
    role_after_overall = _aggregate_metric_reports(role_after_reports)
    direct_before_overall = _aggregate_metric_reports(direct_before_reports)
    direct_after_overall = _aggregate_metric_reports(direct_after_reports)
    metrics = {
        "role_review_corrected": {
            "per_paper": {
                report["paper_id"]: _diff_metrics(report, after)
                for report, after in zip(role_before_reports, role_after_reports)
            },
            "overall": _diff_metrics(role_before_overall, role_after_overall),
        },
        "direct_review_comparator": {
            "per_paper": {
                report["paper_id"]: _diff_metrics(report, after)
                for report, after in zip(direct_before_reports, direct_after_reports)
            },
            "overall": _diff_metrics(direct_before_overall, direct_after_overall),
        },
    }
    exclusion_audit = _build_exclusion_audit(
        gate_exclusion_rows=gate_exclusion_rows,
        role_before_by_paper=role_before_by_paper,
        direct_before_by_paper=direct_before_by_paper,
        role_positive=role_positive,
    )
    validation = {
        "input_total_expected": 499,
        "input_total_observed": sum(len(gate_by_paper.get(paper_id, {})) for paper_id in PAPER_IDS),
        "contains_2307": "2307.05527" in gate_by_paper,
        "row_count_checks": row_count_checks,
        "safe_hard_exclude_policy": {
            "hard_exclude_publication_types": [
                "secondary_review_or_survey",
                "position_or_commentary",
                "standards_or_book_or_tool_doc only when guideline/standard markers are present",
            ],
            "manual_check_or_pass_through_publication_types": [
                "non_empirical_other",
                "standards_or_book_or_tool_doc without guideline/standard markers",
            ],
        },
        "model_exclusion_count": len(model_exclusion_rows),
        "gate_exclusion_count": len(gate_exclusion_rows),
        "suppressed_model_exclusion_count": len(model_exclusion_rows) - len(gate_exclusion_rows),
        "gate_exclusion_counts_by_paper": dict(Counter(str(row["paper_id"]) for row in gate_exclusion_rows)),
        "gate_exclusion_publication_types": dict(Counter(str(row["publication_type"]) for row in gate_exclusion_rows)),
        "gate_exclusion_gold_counts": {
            "gold_true": sum(1 for row in exclusion_audit if row["gold_is_evidence_base"] is True),
            "gold_false": sum(1 for row in exclusion_audit if row["gold_is_evidence_base"] is False),
            "gold_missing": sum(1 for row in exclusion_audit if row["gold_is_evidence_base"] is None),
        },
        "introduced_false_negative_count": sum(1 for row in exclusion_audit if row["introduced_false_negative"]),
    }
    _write_json(run_dir / "before_after_metrics.json", metrics)
    _write_json(run_dir / "validation_summary.json", validation)
    _write_json(run_dir / "primary_gate_model_exclusions.json", model_exclusion_rows)
    _write_json(run_dir / "primary_gate_exclusions.json", gate_exclusion_rows)
    _write_json(run_dir / "primary_gate_exclusion_gold_audit.json", exclusion_audit)
    _write_report(run_id, config, metrics, validation)
    run_manifest = {
        **_load_run_manifest(run_id),
        "mode": "overlay",
        "overlay_status": "completed",
        "overlay_root": _relative(overlay_root),
        "before_after_metrics": _relative(run_dir / "before_after_metrics.json"),
        "validation_summary": _relative(run_dir / "validation_summary.json"),
    }
    _save_run_manifest(run_id, run_manifest)
    print(f"[overlay] report={run_dir / 'REPORT_zh.md'}", flush=True)


def _fmt_metric(metric: dict[str, Any]) -> str:
    return (
        f"P={metric['precision']:.4f}, R={metric['recall']:.4f}, F1={metric['f1']:.4f} "
        f"(tp={metric['tp']}, fp={metric['fp']}, tn={metric['tn']}, fn={metric['fn']})"
    )


def _write_report(run_id: str, config: dict[str, Any], metrics: dict[str, Any], validation: dict[str, Any]) -> None:
    lines = [
        "# Primary Evidence Gate Overlay Report",
        "",
        f"- run_id: `{run_id}`",
        f"- model: `{config['model']}`",
        f"- reasoning_effort: `{config['reasoning_effort']}`",
        f"- papers: `{', '.join(PAPER_IDS)}`",
        f"- excluded paper: `2307.05527`",
        f"- gate inputs: `{validation['input_total_observed']}`",
        f"- model exclusion suggestions: `{validation['model_exclusion_count']}`",
        f"- gate exclusions: `{validation['gate_exclusion_count']}`",
        f"- suppressed model exclusions: `{validation['suppressed_model_exclusion_count']}`",
        f"- introduced false negatives by gold audit: `{validation['introduced_false_negative_count']}`",
        "",
        "## Validation",
        "",
        f"- expected input total: `{validation['input_total_expected']}`",
        f"- observed input total: `{validation['input_total_observed']}`",
        f"- contains 2307: `{validation['contains_2307']}`",
        "",
        "## Role-review corrected overlay",
        "",
    ]
    role = metrics["role_review_corrected"]
    lines.append(f"- overall before: {_fmt_metric(role['overall']['before'])}")
    lines.append(f"- overall after: {_fmt_metric(role['overall']['after'])}")
    lines.append(f"- overall delta F1: `{role['overall']['delta']['f1']:.4f}`")
    lines.extend(["", "| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |", "| --- | ---: | ---: | ---: | --- |"])
    for paper_id, diff in role["per_paper"].items():
        after = diff["after"]
        lines.append(
            f"| `{paper_id}` | {diff['before']['f1']:.4f} | {after['f1']:.4f} | "
            f"{diff['delta']['f1']:.4f} | {after['tp']}/{after['fp']}/{after['tn']}/{after['fn']} |"
        )
    lines.extend(["", "## Direct-review comparator overlay", ""])
    direct = metrics["direct_review_comparator"]
    lines.append(f"- overall before: {_fmt_metric(direct['overall']['before'])}")
    lines.append(f"- overall after: {_fmt_metric(direct['overall']['after'])}")
    lines.append(f"- overall delta F1: `{direct['overall']['delta']['f1']:.4f}`")
    lines.extend(["", "| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |", "| --- | ---: | ---: | ---: | --- |"])
    for paper_id, diff in direct["per_paper"].items():
        after = diff["after"]
        lines.append(
            f"| `{paper_id}` | {diff['before']['f1']:.4f} | {after['f1']:.4f} | "
            f"{diff['delta']['f1']:.4f} | {after['tp']}/{after['fp']}/{after['tn']}/{after['fn']} |"
        )
    lines.extend(["", "## Artifacts", ""])
    lines.append("- `primary_gate_results.json`")
    lines.append("- `primary_gate_exclusions.json`")
    lines.append("- `primary_gate_exclusion_gold_audit.json`")
    lines.append("- `before_after_metrics.json`")
    lines.append("- `validation_summary.json`")
    lines.append("- `overlays/role_review_corrected/`")
    lines.append("- `overlays/direct_review_comparator/`")
    (Path(_run_dir(run_id)) / "REPORT_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _now_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_primary_gate_overlay")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run primary evidence gate overlay experiment.")
    parser.add_argument("--mode", choices=["prepare", "submit", "collect", "overlay", "run"], required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default=None)
    parser.add_argument("--batch-poll-interval-sec", type=float, default=None)
    parser.add_argument("--batch-max-wait-minutes", type=float, default=None)
    args = parser.parse_args()

    config = _load_config()
    if args.model:
        config["model"] = args.model
    if args.reasoning_effort:
        config["reasoning_effort"] = "" if args.reasoning_effort == "none" else args.reasoning_effort
    run_id = args.run_id or _now_run_id()

    if args.mode == "prepare":
        manifest, _ = prepare(run_id, config)
        print(f"[prepare] inputs={manifest['total']} run_dir={_run_dir(run_id)}", flush=True)
        return 0
    if args.mode == "submit":
        submit(run_id, config)
        return 0
    if args.mode == "collect":
        collect(
            run_id,
            config,
            batch_poll_interval_sec=args.batch_poll_interval_sec,
            batch_max_wait_minutes=args.batch_max_wait_minutes,
        )
        return 0
    if args.mode == "overlay":
        overlay(run_id, config)
        return 0
    if args.mode == "run":
        submit(run_id, config)
        collect(
            run_id,
            config,
            batch_poll_interval_sec=args.batch_poll_interval_sec,
            batch_max_wait_minutes=args.batch_max_wait_minutes,
        )
        overlay(run_id, config)
        return 0
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
