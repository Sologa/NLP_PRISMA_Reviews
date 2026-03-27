#!/usr/bin/env python3
"""Backfill 2307 result artifacts with the split preprint cutoff."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screening.cutoff_time_filter import (  # noqa: E402
    apply_cutoff,
    apply_cutoff_to_results,
    cutoff_json_path,
    evaluate_record,
    load_time_policy,
)

PAPER_ID = "2307.05527"
RESULTS_DIR = REPO_ROOT / "screening" / "results" / f"{PAPER_ID}_full"
GOLD_PATH = REPO_ROOT / "refs" / PAPER_ID / "metadata" / "title_abstracts_metadata-annotated.jsonl"
METADATA_PATH = REPO_ROOT / "refs" / PAPER_ID / "metadata" / "title_abstracts_metadata.jsonl"
FULL_METADATA_PATH = REPO_ROOT / "refs" / PAPER_ID / "metadata" / "title_abstracts_full_metadata.jsonl"
CURRENT_STAGE1_REPORT = RESULTS_DIR / "review_after_stage1_senior_no_marker_report.json"
CURRENT_COMBINED_REPORT = RESULTS_DIR / "combined_after_fulltext_senior_no_marker_report.json"
RESULTS_MANIFEST_PATH = REPO_ROOT / "screening" / "results" / "results_manifest.json"
CURRENT_MD_PATH = RESULTS_DIR / "CURRENT.md"
HISTORY_HANDOFF_PATH = REPO_ROOT / "docs" / "chatgpt_current_status_handoff.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
REPO_CUTOFF_VERDICT = "exclude (cutoff_time_window)"
SKIP_REPORT_BASENAMES = {"cutoff_audit.json", "avg_review_f1_3x.json"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        item = json.loads(stripped)
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _repo_rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def _merged_metadata_rows() -> list[dict[str, Any]]:
    base_rows = _load_jsonl(METADATA_PATH)
    full_rows = {str(row.get("key") or "").strip(): row for row in _load_jsonl(FULL_METADATA_PATH)}
    merged_rows: list[dict[str, Any]] = []
    for row in base_rows:
        key = str(row.get("key") or "").strip()
        merged = dict(row)
        full_row = full_rows.get(key)
        if full_row is not None:
            for field in ("comment", "journal_ref", "doi", "source", "source_id", "source_metadata"):
                value = full_row.get(field)
                if value not in (None, ""):
                    merged[field] = value
        merged_rows.append(merged)
    return merged_rows


def _metadata_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("key") or "").strip(): row
        for row in rows
        if str(row.get("key") or "").strip()
    }


def _cutoff_bundle() -> tuple[dict[str, Any], Any, Any]:
    payload, old_policy = load_time_policy(cutoff_json_path(REPO_ROOT, PAPER_ID))
    payload = dict(payload)
    payload["_cutoff_json_path"] = _repo_rel(cutoff_json_path(REPO_ROOT, PAPER_ID))
    payload["time_policy"] = dict(payload.get("time_policy") or {})
    payload["time_policy"]["preprint_split_submitted_date"] = True
    new_policy = replace(old_policy, preprint_split_submitted_date=True)
    return payload, old_policy, new_policy


def _is_stage1_results(path: Path) -> bool:
    return path.name.startswith("latte_review_results")


def _cleanup_restored_row(row: dict[str, Any], *, decision: dict[str, Any]) -> dict[str, Any]:
    restored = dict(row)
    restored["cutoff_filter"] = decision
    if str(restored.get("discard_reason") or "").startswith("cutoff_time_window:"):
        restored.pop("discard_reason", None)
    if restored.get("review_state") == "cutoff_filtered":
        restored.pop("review_state", None)
    if restored.get("pre_cutoff_review_state") == "cutoff_filtered":
        restored.pop("pre_cutoff_review_state", None)
    if str(restored.get("pre_cutoff_final_verdict") or "").strip() == REPO_CUTOFF_VERDICT:
        restored.pop("pre_cutoff_final_verdict", None)
    if restored.get("pre_cutoff_review_skipped") is True:
        restored.pop("pre_cutoff_review_skipped", None)
    return restored


def _stage1_fallback_restore_rows(path: Path) -> dict[str, dict[str, Any]] | None:
    if path.name != "latte_review_results.ft_run1.json":
        return None
    candidate = RESULTS_DIR / "latte_review_results.json"
    if not candidate.exists():
        return None
    rows = _read_json(candidate)
    if not isinstance(rows, list):
        return None
    return {
        str(row.get("key") or "").strip(): row
        for row in rows
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    }


def _fallback_restore_rows_for_stage2(path: Path) -> dict[str, dict[str, Any]] | None:
    sibling_candidates: list[Path] = []
    renamed = path.name.replace("latte_fulltext_review_results", "latte_review_results")
    if renamed != path.name:
        sibling_candidates.append(path.parent / renamed)
    renamed = path.name.replace("latte_fulltext_review_from_run01", "latte_review_results")
    if renamed != path.name:
        sibling_candidates.append(path.parent / renamed)

    for candidate in sibling_candidates:
        if candidate.is_file():
            rows = _read_json(candidate)
            if isinstance(rows, list):
                return {
                    str(row.get("key") or "").strip(): row
                    for row in rows
                    if isinstance(row, dict) and str(row.get("key") or "").strip()
                }
    return None


def _preflight_rescue(
    *,
    path: Path,
    original_rows: list[dict[str, Any]],
    adjusted_rows: list[dict[str, Any]],
    metadata_by_key: dict[str, dict[str, Any]],
    old_policy: Any,
    new_policy: Any,
) -> dict[str, Any]:
    original_by_key = {
        str(row.get("key") or "").strip(): row
        for row in original_rows
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    }
    adjusted_by_key = {
        str(row.get("key") or "").strip(): row
        for row in adjusted_rows
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    }
    rescued_keys: list[str] = []
    failures: list[str] = []
    for key, row in original_by_key.items():
        record = metadata_by_key.get(key)
        if record is None:
            continue
        old_decision = evaluate_record(record, old_policy)
        new_decision = evaluate_record(record, new_policy)
        if old_decision["cutoff_pass"] or not new_decision["cutoff_pass"]:
            continue
        rescued_keys.append(key)
        adjusted = adjusted_by_key.get(key)
        if adjusted is None:
            failures.append(f"{key}:missing_adjusted_row")
            continue
        if str(adjusted.get("final_verdict") or "").strip() == REPO_CUTOFF_VERDICT:
            failures.append(f"{key}:still_cutoff")
        if adjusted.get("review_skipped") is True:
            failures.append(f"{key}:still_review_skipped")
        if not str(adjusted.get("final_verdict") or "").strip():
            failures.append(f"{key}:missing_final_verdict")

    if failures:
        detail = "\n".join(failures[:20])
        raise RuntimeError(f"Preflight failed for {path}:\n{detail}")

    return {"rescued_count": len(rescued_keys), "rescued_keys": rescued_keys}


def _supports_junior_maybe_restore(path: Path, original_rows: list[dict[str, Any]]) -> bool:
    if "recall_redesign" in path.name:
        return True
    return any(str(row.get("final_verdict") or "").startswith("maybe (junior:") for row in original_rows)


def _repair_stage1_junior_maybe_rows(
    *,
    path: Path,
    original_rows: list[dict[str, Any]],
    adjusted_rows: list[dict[str, Any]],
    metadata_by_key: dict[str, dict[str, Any]],
    old_policy: Any,
    new_policy: Any,
) -> list[dict[str, Any]]:
    if not _supports_junior_maybe_restore(path, original_rows):
        return adjusted_rows

    adjusted_by_key = {
        str(row.get("key") or "").strip(): dict(row)
        for row in adjusted_rows
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    }
    for original_row in original_rows:
        key = str(original_row.get("key") or "").strip()
        if not key:
            continue
        record = metadata_by_key.get(key)
        if record is None:
            continue
        old_decision = evaluate_record(record, old_policy)
        new_decision = evaluate_record(record, new_policy)
        if old_decision["cutoff_pass"] or not new_decision["cutoff_pass"]:
            continue
        adjusted = adjusted_by_key.get(key)
        if adjusted is None or str(adjusted.get("final_verdict") or "").strip() != REPO_CUTOFF_VERDICT:
            continue
        junior_nano = original_row.get("round-A_JuniorNano_evaluation")
        junior_mini = original_row.get("round-A_JuniorMini_evaluation")
        senior = original_row.get("round-B_SeniorLead_evaluation")
        if junior_nano is None or junior_mini is None or senior is not None:
            continue
        restored = dict(original_row)
        restored["final_verdict"] = f"maybe (junior:{junior_nano},{junior_mini})"
        restored["review_skipped"] = False
        adjusted_by_key[key] = _cleanup_restored_row(restored, decision=new_decision)

    return [
        adjusted_by_key.get(str(row.get("key") or "").strip(), row)
        if isinstance(row, dict)
        else row
        for row in adjusted_rows
    ]


def _patch_rows_file(
    path: Path,
    *,
    metadata_rows: list[dict[str, Any]],
    metadata_by_key: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    old_policy: Any,
    new_policy: Any,
) -> dict[str, Any]:
    rows = _read_json(path)
    if not isinstance(rows, list):
        raise ValueError(f"Expected list JSON payload: {path}")

    kwargs = {
        "metadata_rows": metadata_rows,
        "payload": payload,
        "policy": new_policy,
    }
    if _is_stage1_results(path):
        kwargs["synthesize_missing_failed_rows"] = True
        kwargs["preserve_metadata_order"] = True
        fallback_restore_rows_by_key = _stage1_fallback_restore_rows(path)
        if fallback_restore_rows_by_key is not None:
            kwargs["fallback_restore_rows_by_key"] = fallback_restore_rows_by_key
    else:
        kwargs["synthesize_missing_failed_rows"] = False
        kwargs["preserve_metadata_order"] = False
        kwargs["fallback_restore_rows_by_key"] = _fallback_restore_rows_for_stage2(path)

    rewritten = apply_cutoff_to_results([row for row in rows if isinstance(row, dict)], **kwargs)
    adjusted_rows = rewritten["rows"]
    if _is_stage1_results(path):
        adjusted_rows = _repair_stage1_junior_maybe_rows(
            path=path,
            original_rows=[row for row in rows if isinstance(row, dict)],
            adjusted_rows=adjusted_rows,
            metadata_by_key=metadata_by_key,
            old_policy=old_policy,
            new_policy=new_policy,
        )
    preflight = _preflight_rescue(
        path=path,
        original_rows=[row for row in rows if isinstance(row, dict)],
        adjusted_rows=adjusted_rows,
        metadata_by_key=metadata_by_key,
        old_policy=old_policy,
        new_policy=new_policy,
    )
    _write_json(path, adjusted_rows)

    old_cutoff = sum(1 for row in rows if isinstance(row, dict) and row.get("final_verdict") == REPO_CUTOFF_VERDICT)
    new_cutoff = sum(1 for row in adjusted_rows if row.get("final_verdict") == REPO_CUTOFF_VERDICT)
    return {
        "path": _repo_rel(path),
        "old_cutoff_count": old_cutoff,
        "new_cutoff_count": new_cutoff,
        "rescued_count": preflight["rescued_count"],
    }


def _write_cutoff_audit(path: Path, *, metadata_rows: list[dict[str, Any]], payload: dict[str, Any], policy: Any) -> dict[str, Any]:
    audit_payload = apply_cutoff(metadata_rows, payload=payload, policy=policy)["audit_payload"]
    audit_payload["paper_id"] = PAPER_ID
    audit_payload["cutoff_json_path"] = payload.get("_cutoff_json_path")
    _write_json(path, audit_payload)
    return audit_payload


def _iter_stage1_paths() -> list[Path]:
    return sorted(
        (path for path in RESULTS_DIR.rglob("latte_review_results*.json") if path.is_file()),
        key=lambda path: (
            path.name.endswith(".ft_run1.json"),
            len(path.relative_to(RESULTS_DIR).parts),
            str(path),
        ),
    )


def _iter_stage2_paths() -> list[Path]:
    paths = sorted(path for path in RESULTS_DIR.rglob("latte_fulltext_review_results*.json") if path.is_file())
    from_run01 = sorted(path for path in RESULTS_DIR.rglob("latte_fulltext_review_from_run01.json") if path.is_file())
    return paths + from_run01


def _iter_report_paths() -> list[Path]:
    report_paths: list[Path] = []
    for path in sorted(RESULTS_DIR.rglob("*.json")):
        if path.name in SKIP_REPORT_BASENAMES:
            continue
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        required = {"paper_id", "results_path", "gold_path", "metrics"}
        if required.issubset(payload.keys()) and isinstance(payload.get("metrics"), dict):
            report_paths.append(path)
    return report_paths


def _infer_base_review_results(report_path: Path, report: dict[str, Any]) -> Path | None:
    if "combined" not in report_path.name.lower():
        return None

    results_path = Path(str(report["results_path"]))
    if results_path.name == "latte_fulltext_review_from_run01.json":
        for candidate in (
            results_path.parent / "run01" / "latte_review_results.run01.json",
            results_path.parent / "run01" / "latte_review_results.json",
        ):
            if candidate.exists():
                return candidate
        return None

    if results_path.name.startswith("latte_fulltext_review_results"):
        suffix = results_path.name.removeprefix("latte_fulltext_review_results")
        candidate = results_path.parent / f"latte_review_results{suffix}"
        if candidate.exists():
            return candidate

    if results_path.name == "latte_fulltext_review_results.json":
        candidate = results_path.parent / "latte_review_results.json"
        if candidate.exists():
            return candidate
    return None


def _rerun_report(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if not isinstance(report, dict):
        raise ValueError(f"Unsupported report payload: {path}")

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        PAPER_ID,
        "--results",
        str(report["results_path"]),
        "--gold-metadata",
        str(report["gold_path"]),
        "--positive-mode",
        str(report.get("positive_mode") or "include_or_maybe"),
        "--save-report",
        str(path),
    ]
    keys_file = report.get("keys_file")
    if keys_file:
        cmd.extend(["--keys-file", str(keys_file)])
    base_review_results = _infer_base_review_results(path, report)
    if base_review_results is not None:
        cmd.append("--combine-with-base")
        cmd.extend(["--base-review-results", str(base_review_results)])

    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True, capture_output=True, text=True)
    return _read_json(path)


def _rebuild_avg_review_f1() -> dict[str, Any]:
    run_reports = [RESULTS_DIR / f"run0{idx}" / "latte_review_f1.json" for idx in (1, 2, 3)]
    payloads = [_read_json(path) for path in run_reports if path.exists()]
    macro_keys = ("precision", "recall", "f1")
    macro_average = {
        key: mean(float(payload["metrics"][key]) for payload in payloads)
        for key in macro_keys
    }
    tp = sum(int(payload["metrics"]["tp"]) for payload in payloads)
    fp = sum(int(payload["metrics"]["fp"]) for payload in payloads)
    tn = sum(int(payload["metrics"]["tn"]) for payload in payloads)
    fn = sum(int(payload["metrics"]["fn"]) for payload in payloads)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    payload = {
        "paper_id": PAPER_ID,
        "runs": str(len(payloads)),
        "run_reports": [
            {
                "run_tag": path.parent.name,
                "report_path": str(path.resolve()),
                "results_path": str(_read_json(path).get("results_path")),
                "metrics": _read_json(path).get("metrics", {}),
                "verdict_counts": _read_json(path).get("verdict_counts", {}),
                "gold_only_count": _read_json(path).get("gold_only_count"),
                "extra_result_only_count": _read_json(path).get("extra_result_only_count"),
            }
            for path in run_reports
            if path.exists()
        ],
        "macro_average": macro_average,
        "micro_average": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "accuracy": (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) else 0.0,
        },
    }
    out_path = RESULTS_DIR / "avg_review_f1_3x.json"
    _write_json(out_path, payload)
    return payload


def _render_current_md(stage1_metrics: dict[str, Any], combined_metrics: dict[str, Any], cutoff_excluded_count: int) -> str:
    return "\n".join(
        [
            f"# CURRENT: {PAPER_ID}",
            "",
            f"This file identifies the current authoritative score sources for `{PAPER_ID}`.",
            "",
            "## Current score authority",
            "",
            "Current stable reference score authority remains the latest fully benchmarked senior_no_marker metrics:",
            "",
            f"- Stage 1: `screening/results/{PAPER_ID}_full/review_after_stage1_senior_no_marker_report.json`",
            f"- Combined: `screening/results/{PAPER_ID}_full/combined_after_fulltext_senior_no_marker_report.json`",
            "",
            "Current metrics:",
            "",
            f"- Stage 1 F1: `{stage1_metrics['f1']:.4f}`",
            f"- Combined F1: `{combined_metrics['f1']:.4f}`",
            "",
            "## Cutoff-first policy",
            "",
            f"- Mandatory pre-review cutoff: `cutoff_jsons/{PAPER_ID}.json`",
            f"- Cutoff-excluded candidates: `{cutoff_excluded_count}`",
            "- Cutoff-failed rows are now forced to `exclude (cutoff_time_window)` before reviewer routing is treated as authoritative.",
            "",
            "## Provenance",
            "",
            "Current runtime uses:",
            "",
            f"- Stage 1 criteria: `criteria_stage1/{PAPER_ID}.json`",
            f"- Stage 2 criteria: `criteria_stage2/{PAPER_ID}.json`",
            "",
            "## Historical baselines in this directory",
            "",
            "These remain useful for comparison, but they are not the current score authority:",
            "- `review_after_stage1_prompt_only_v1_report.json`",
            "- `combined_after_fulltext_report.json`",
            "- `stage1_recall_redesign_report.json`",
            "- `combined_recall_redesign_report.json`",
            "- `review_after_stage1_senior_adjudication_v1_report.json`",
            "- `combined_after_fulltext_senior_adjudication_v1_report.json`",
            "- `review_after_stage1_senior_no_marker_report.json`",
            "- `combined_after_fulltext_senior_no_marker_report.json`",
            "- `review_after_stage1_senior_prompt_tuned_report.json`",
            "- `combined_after_fulltext_senior_prompt_tuned_report.json`",
            "- raw historical `latte_review_results*.json` and `latte_fulltext_review_results*.json` outputs",
            "",
            "## Do-not-confuse notes",
            "",
            "- Do not describe `criteria_jsons/*.json` as current production criteria.",
            "- Do not reuse pre-cutoff metrics as current score authority.",
            "- Read `AGENTS.md`, `docs/chatgpt_current_status_handoff.md`, and `screening/results/results_manifest.json` first.",
            "",
        ]
    )


def _update_results_manifest(stage1_report: dict[str, Any], combined_report: dict[str, Any], cutoff_excluded_count: int) -> dict[str, Any]:
    payload = _read_json(RESULTS_MANIFEST_PATH)
    entry = payload["papers"][PAPER_ID]
    stage1_metrics = stage1_report["metrics"]
    combined_metrics = combined_report["metrics"]
    entry["current_metrics"]["stage1"].update(
        {
            "precision": stage1_metrics["precision"],
            "recall": stage1_metrics["recall"],
            "f1": stage1_metrics["f1"],
            "tp": stage1_metrics["tp"],
            "fp": stage1_metrics["fp"],
            "tn": stage1_metrics["tn"],
            "fn": stage1_metrics["fn"],
        }
    )
    entry["current_metrics"]["combined"].update(
        {
            "precision": combined_metrics["precision"],
            "recall": combined_metrics["recall"],
            "f1": combined_metrics["f1"],
            "tp": combined_metrics["tp"],
            "fp": combined_metrics["fp"],
            "tn": combined_metrics["tn"],
            "fn": combined_metrics["fn"],
        }
    )
    entry["cutoff_policy"]["cutoff_excluded_count"] = cutoff_excluded_count
    _write_json(RESULTS_MANIFEST_PATH, payload)
    return payload


def _replace_table_row(text: str, *, prefix: str, replacement: str) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}.*$", re.MULTILINE)
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Failed to replace row for prefix: {prefix}")
    return updated


def _update_handoff(stage1_f1: float, combined_f1: float, cutoff_excluded_count: int) -> None:
    text = HISTORY_HANDOFF_PATH.read_text(encoding="utf-8")
    text = re.sub(r"^Date: .*$", f"Date: {date.today().isoformat()}", text, count=1, flags=re.MULTILINE)
    text = _replace_table_row(
        text,
        prefix="| `2307.05527` |",
        replacement=(
            f"| `2307.05527` | `review_after_stage1_senior_no_marker_report.json` | "
            f"`combined_after_fulltext_senior_no_marker_report.json` | "
            f"`{stage1_f1:.4f}` | `{combined_f1:.4f}` | `{cutoff_excluded_count}` |"
        ),
    )
    text = text.replace("- Cutoff-excluded candidates: `29`", f"- Cutoff-excluded candidates: `{cutoff_excluded_count}`")
    HISTORY_HANDOFF_PATH.write_text(text, encoding="utf-8")


def _update_agents(stage1_f1: float, combined_f1: float) -> None:
    text = AGENTS_PATH.read_text(encoding="utf-8")
    text = _replace_table_row(
        text,
        prefix="| `2307.05527` |",
        replacement=(
            f"| `2307.05527` | `criteria_stage1/` + `criteria_stage2/` | "
            f"latest fully benchmarked `senior_no_marker` | `{stage1_f1:.4f}` | `{combined_f1:.4f}` | stable reference |"
        ),
    )
    AGENTS_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    metadata_rows = _merged_metadata_rows()
    metadata_by_key = _metadata_by_key(metadata_rows)
    payload, old_policy, new_policy = _cutoff_bundle()

    stage1_summaries: list[dict[str, Any]] = []
    stage2_summaries: list[dict[str, Any]] = []
    audit_dirs: set[Path] = set()

    for path in _iter_stage1_paths():
        stage1_summaries.append(
            _patch_rows_file(
                path,
                metadata_rows=metadata_rows,
                metadata_by_key=metadata_by_key,
                payload=payload,
                old_policy=old_policy,
                new_policy=new_policy,
            )
        )
        audit_dirs.add(path.parent)

    for path in _iter_stage2_paths():
        stage2_summaries.append(
            _patch_rows_file(
                path,
                metadata_rows=metadata_rows,
                metadata_by_key=metadata_by_key,
                payload=payload,
                old_policy=old_policy,
                new_policy=new_policy,
            )
        )
        audit_dirs.add(path.parent)

    top_level_audit = None
    for audit_dir in sorted(audit_dirs):
        audit = _write_cutoff_audit(audit_dir / "cutoff_audit.json", metadata_rows=metadata_rows, payload=payload, policy=new_policy)
        if audit_dir == RESULTS_DIR:
            top_level_audit = audit

    report_summaries = {str(path): _rerun_report(path) for path in _iter_report_paths()}
    avg_review_f1 = _rebuild_avg_review_f1()

    stage1_report = _read_json(CURRENT_STAGE1_REPORT)
    combined_report = _read_json(CURRENT_COMBINED_REPORT)
    if top_level_audit is None:
        raise RuntimeError("Top-level cutoff audit was not written")
    cutoff_excluded_count = int(top_level_audit["cutoff_excluded_count"])

    CURRENT_MD_PATH.write_text(
        _render_current_md(stage1_report["metrics"], combined_report["metrics"], cutoff_excluded_count),
        encoding="utf-8",
    )
    _update_results_manifest(stage1_report, combined_report, cutoff_excluded_count)
    _update_handoff(stage1_report["metrics"]["f1"], combined_report["metrics"]["f1"], cutoff_excluded_count)
    _update_agents(stage1_report["metrics"]["f1"], combined_report["metrics"]["f1"])

    summary = {
        "paper_id": PAPER_ID,
        "stage1_files": stage1_summaries,
        "stage2_files": stage2_summaries,
        "reports_recomputed": len(report_summaries),
        "avg_review_f1_path": _repo_rel(RESULTS_DIR / "avg_review_f1_3x.json"),
        "current_stage1_f1": stage1_report["metrics"]["f1"],
        "current_combined_f1": combined_report["metrics"]["f1"],
        "cutoff_excluded_count": cutoff_excluded_count,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
