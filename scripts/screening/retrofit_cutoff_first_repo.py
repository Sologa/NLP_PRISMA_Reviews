#!/usr/bin/env python3
"""Retrofit cutoff-first semantics across historical 3-reviewer result families."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import types
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screening.cutoff_time_filter import (
    apply_cutoff,
    apply_cutoff_to_results,
    cutoff_json_path,
    load_time_policy,
)

RESULTS_ROOT = REPO_ROOT / "screening" / "results"
DOCS_ROOT = REPO_ROOT / "docs"
ARXIV_ID_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)")

CANONICAL_PAPERS = ("2307.05527", "2409.13738", "2511.13936", "2601.19926")
TARGET_ROOTS = (
    RESULTS_ROOT / "2307.05527_full",
    RESULTS_ROOT / "2409.13738_full",
    RESULTS_ROOT / "2511.13936_full",
    RESULTS_ROOT / "2601.19926_full",
    RESULTS_ROOT / "source_faithful_vs_operational_2409_2511_runA",
    RESULTS_ROOT / "qa_first_v0_2409_2511_2026-03-18",
    RESULTS_ROOT / "qa_first_v1_global_repair_2409_2511_2026-03-18",
    RESULTS_ROOT / "qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19",
    RESULTS_ROOT / "qa_first_v1_2409_stage2_followup_2026-03-19",
    RESULTS_ROOT / "qa_first_v1_2409_stage2_final_ablation_2026-03-19",
    RESULTS_ROOT / "fulltext_direct_v1_all4_2026-03-19",
)
QA_REPORT_BUNDLES = {
    "qa_first_v0_2409_2511_2026-03-18": REPO_ROOT
    / "qa_first_experiments"
    / "qa_first_experiment_v0_2409_2511_2026-03-18"
    / "tools"
    / "run_experiment.py",
    "qa_first_v1_global_repair_2409_2511_2026-03-18": REPO_ROOT
    / "qa_first_experiments"
    / "qa_first_experiment_v1_global_repair_2409_2511_2026-03-18"
    / "tools"
    / "run_experiment.py",
    "qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19": REPO_ROOT
    / "qa_first_experiments"
    / "qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19"
    / "tools"
    / "run_experiment.py",
    "qa_first_v1_2409_stage2_followup_2026-03-19": REPO_ROOT
    / "qa_first_experiments"
    / "qa_first_experiment_v1_2409_stage2_followup_2026-03-19"
    / "tools"
    / "run_experiment.py",
    "qa_first_v1_2409_stage2_final_ablation_2026-03-19": REPO_ROOT
    / "qa_first_experiments"
    / "qa_first_experiment_v1_2409_stage2_final_ablation_2026-03-19"
    / "tools"
    / "run_experiment.py",
}
FULLTEXT_DIRECT_BUNDLE = (
    REPO_ROOT
    / "fulltext_direct_experiments"
    / "fulltext_direct_experiment_v1_all4_2026-03-19"
    / "tools"
    / "run_experiment.py"
)
CURRENT_AUTHORITY = {
    "2307.05527": {
        "status": "latest_fully_benchmarked_senior_no_marker",
        "label": "latest fully benchmarked senior_no_marker",
        "stage1": RESULTS_ROOT / "2307.05527_full" / "review_after_stage1_senior_no_marker_report.json",
        "combined": RESULTS_ROOT / "2307.05527_full" / "combined_after_fulltext_senior_no_marker_report.json",
    },
    "2409.13738": {
        "status": "current_stage_split",
        "label": "stage_split_criteria_migration",
        "stage1": RESULTS_ROOT / "2409.13738_full" / "stage1_f1.stage_split_criteria_migration.json",
        "combined": RESULTS_ROOT / "2409.13738_full" / "combined_f1.stage_split_criteria_migration.json",
    },
    "2511.13936": {
        "status": "current_stage_split",
        "label": "stage_split_criteria_migration",
        "stage1": RESULTS_ROOT / "2511.13936_full" / "stage1_f1.stage_split_criteria_migration.json",
        "combined": RESULTS_ROOT / "2511.13936_full" / "combined_f1.stage_split_criteria_migration.json",
    },
    "2601.19926": {
        "status": "latest_fully_benchmarked_senior_no_marker",
        "label": "latest fully benchmarked senior_no_marker",
        "stage1": RESULTS_ROOT / "2601.19926_full" / "review_after_stage1_senior_no_marker_report.json",
        "combined": RESULTS_ROOT / "2601.19926_full" / "combined_after_fulltext_senior_no_marker_report.json",
    },
}
PRE_CUTOFF_CURRENT_SNAPSHOT = {
    "2307.05527": {
        "stage1": {
            "precision": 0.9593023255813954,
            "recall": 0.9649122807017544,
            "f1": 0.9620991253644314,
            "tp": 165,
            "fp": 7,
            "tn": 40,
            "fn": 6,
        },
        "combined": {
            "precision": 0.9815950920245399,
            "recall": 0.935672514619883,
            "f1": 0.9580838323353292,
            "tp": 160,
            "fp": 3,
            "tn": 44,
            "fn": 11,
        },
    },
    "2409.13738": {
        "stage1": {
            "precision": 0.6,
            "recall": 1.0,
            "f1": 0.75,
            "tp": 21,
            "fp": 14,
            "tn": 43,
            "fn": 0,
        },
        "combined": {
            "precision": 0.6666666666666666,
            "recall": 0.9523809523809523,
            "f1": 0.7843137254901961,
            "tp": 20,
            "fp": 10,
            "tn": 47,
            "fn": 1,
        },
    },
    "2511.13936": {
        "stage1": {
            "precision": 0.7837837837837838,
            "recall": 0.9666666666666667,
            "f1": 0.8656716417910447,
            "tp": 29,
            "fp": 8,
            "tn": 46,
            "fn": 1,
        },
        "combined": {
            "precision": 0.896551724137931,
            "recall": 0.8666666666666667,
            "f1": 0.8813559322033899,
            "tp": 26,
            "fp": 3,
            "tn": 51,
            "fn": 4,
        },
    },
    "2601.19926": {
        "stage1": {
            "precision": 0.9734513274336283,
            "recall": 0.9850746268656716,
            "f1": 0.9792284866468842,
            "tp": 330,
            "fp": 9,
            "tn": 14,
            "fn": 5,
        },
        "combined": {
            "precision": 0.967551622418879,
            "recall": 0.9791044776119403,
            "f1": 0.973293768545994,
            "tp": 328,
            "fp": 11,
            "tn": 12,
            "fn": 7,
        },
    },
}
SKIP_REPORT_BASENAMES = {
    "run_manifest.json",
    "summary.json",
    "results_manifest.json",
    "cutoff_corrected_metrics_manifest.json",
    "cutoff_audit.json",
    "fulltext_resolution_audit.json",
    "hygiene_summary.json",
}

_metadata_cache: dict[str, list[dict[str, Any]]] = {}
_gold_cache: dict[str, list[dict[str, Any]]] = {}
_cutoff_cache: dict[str, tuple[dict[str, Any], Any, dict[str, Any]]] = {}
_module_cache: dict[Path, Any] = {}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def _infer_paper_id(path: Path) -> str:
    matches = ARXIV_ID_RE.findall(str(path))
    if not matches:
        raise ValueError(f"Unable to infer paper_id from path: {path}")
    return matches[0]


def _metadata_rows(paper_id: str) -> list[dict[str, Any]]:
    if paper_id not in _metadata_cache:
        path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata.jsonl"
        _metadata_cache[paper_id] = _load_jsonl(path)
    return _metadata_cache[paper_id]


def _gold_rows(paper_id: str) -> list[dict[str, Any]]:
    if paper_id not in _gold_cache:
        path = REPO_ROOT / "refs" / paper_id / "metadata" / "title_abstracts_metadata-annotated.jsonl"
        _gold_cache[paper_id] = _load_jsonl(path)
    return _gold_cache[paper_id]


def _cutoff_bundle(paper_id: str) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    if paper_id not in _cutoff_cache:
        path = cutoff_json_path(REPO_ROOT, paper_id)
        payload, policy = load_time_policy(path)
        payload = dict(payload)
        payload["_cutoff_json_path"] = _rel(path)
        decision_bundle = apply_cutoff(_metadata_rows(paper_id), payload=payload, policy=policy)
        _cutoff_cache[paper_id] = (payload, policy, decision_bundle["audit_payload"])
    return _cutoff_cache[paper_id]


def _label_from_verdict(value: Any) -> str:
    verdict = str(value or "").strip().lower()
    match = re.match(r"^\s*([a-z]+)", verdict)
    return match.group(1) if match else ""


def _stage1_positive_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    for row in rows:
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        if _label_from_verdict(row.get("final_verdict")) in {"include", "maybe"}:
            keys.append(key)
    return keys


def _write_cutoff_audit(path: Path, paper_id: str) -> dict[str, Any]:
    payload, _, audit = _cutoff_bundle(paper_id)
    enriched = dict(audit)
    enriched["paper_id"] = paper_id
    enriched["cutoff_json_path"] = payload.get("_cutoff_json_path")
    _write_json(path, enriched)
    return enriched


def _patch_rows_file(
    path: Path,
    *,
    synthesize_missing_failed_rows: bool,
    preserve_metadata_order: bool,
) -> dict[str, Any]:
    paper_id = _infer_paper_id(path)
    payload, policy, audit = _cutoff_bundle(paper_id)
    rows = _read_json(path)
    if not isinstance(rows, list):
        raise ValueError(f"Expected list JSON payload: {path}")
    rewritten = apply_cutoff_to_results(
        [row for row in rows if isinstance(row, dict)],
        metadata_rows=_metadata_rows(paper_id),
        payload=payload,
        policy=policy,
        synthesize_missing_failed_rows=synthesize_missing_failed_rows,
        preserve_metadata_order=preserve_metadata_order,
    )
    _write_json(path, rewritten["rows"])
    return {
        "paper_id": paper_id,
        "path": _rel(path),
        "filtered_count": rewritten["audit_payload"].get("filtered_count", 0),
        "synthesized_count": rewritten["audit_payload"].get("synthesized_count", 0),
        "cutoff_excluded_count": audit.get("cutoff_excluded_count", 0),
    }


def _patch_raw_results() -> dict[str, Any]:
    summary: dict[str, Any] = {"stage1": [], "stage2": [], "direct": [], "cutoff_audits": []}
    audited_dirs: set[Path] = set()

    for root in TARGET_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("latte_review_results*.json")):
            if not path.is_file():
                continue
            summary["stage1"].append(
                _patch_rows_file(
                    path,
                    synthesize_missing_failed_rows=True,
                    preserve_metadata_order=True,
                )
            )
            audit_dir = path.parent
            if audit_dir not in audited_dirs:
                summary["cutoff_audits"].append(
                    {
                        "dir": _rel(audit_dir),
                        "audit_path": _rel(audit_dir / "cutoff_audit.json"),
                        **_write_cutoff_audit(audit_dir / "cutoff_audit.json", _infer_paper_id(path)),
                    }
                )
                audited_dirs.add(audit_dir)

        for path in sorted(root.rglob("latte_fulltext_review_results*.json")):
            if not path.is_file():
                continue
            summary["stage2"].append(
                _patch_rows_file(
                    path,
                    synthesize_missing_failed_rows=False,
                    preserve_metadata_order=False,
                )
            )

        for path in sorted(root.rglob("latte_fulltext_review_from_run01.json")):
            summary["stage2"].append(
                _patch_rows_file(
                    path,
                    synthesize_missing_failed_rows=False,
                    preserve_metadata_order=False,
                )
            )

        for path in sorted(root.rglob("fulltext_direct_review_results.json")):
            if not path.is_file():
                continue
            summary["direct"].append(
                _patch_rows_file(
                    path,
                    synthesize_missing_failed_rows=True,
                    preserve_metadata_order=True,
                )
            )
            audit_dir = path.parent
            if audit_dir not in audited_dirs:
                summary["cutoff_audits"].append(
                    {
                        "dir": _rel(audit_dir),
                        "audit_path": _rel(audit_dir / "cutoff_audit.json"),
                        **_write_cutoff_audit(audit_dir / "cutoff_audit.json", _infer_paper_id(path)),
                    }
                )
                audited_dirs.add(audit_dir)
    return summary


def _load_module(path: Path) -> Any:
    resolved = path.resolve()
    cached = _module_cache.get(resolved)
    if cached is not None:
        return cached
    if "openai" not in sys.modules:
        stub = types.ModuleType("openai")
        stub.AsyncOpenAI = object
        sys.modules["openai"] = stub
    spec = importlib.util.spec_from_file_location(f"_cutoff_retrofit_{resolved.stem}_{len(_module_cache)}", resolved)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {resolved}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _module_cache[resolved] = module
    return module


def _report_paths_under_targets() -> list[Path]:
    report_paths: list[Path] = []
    for root in TARGET_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            if path.name in SKIP_REPORT_BASENAMES:
                continue
            if path.suffix.lower() != ".json":
                continue
            try:
                payload = _read_json(path)
            except Exception:
                continue
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


def _rerun_report(report_path: Path) -> dict[str, Any]:
    report = _read_json(report_path)
    if not isinstance(report, dict):
        raise ValueError(f"Unsupported report payload: {report_path}")
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "evaluate_review_f1.py"),
        str(report["paper_id"]),
        "--results",
        str(report["results_path"]),
        "--gold-metadata",
        str(report["gold_path"]),
        "--positive-mode",
        str(report.get("positive_mode") or "include_or_maybe"),
        "--save-report",
        str(report_path),
    ]
    keys_file = report.get("keys_file")
    if keys_file:
        cmd.extend(["--keys-file", str(keys_file)])
    base_path = _infer_base_review_results(report_path, report)
    if base_path is not None:
        cmd.append("--combine-with-base")
        cmd.extend(["--base-review-results", str(base_path)])
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    return _read_json(report_path)


def _recompute_all_reports() -> dict[str, Any]:
    report_summaries: dict[str, Any] = {}
    for report_path in _report_paths_under_targets():
        updated = _rerun_report(report_path)
        report_summaries[_rel(report_path)] = {
            "paper_id": updated.get("paper_id"),
            "results_path": updated.get("results_path"),
            "metrics": updated.get("metrics", {}),
            "verdict_counts": updated.get("verdict_counts", {}),
        }
    return report_summaries


def _rebuild_avg_review_f1() -> dict[str, Any]:
    rebuilt: dict[str, Any] = {}
    for paper_id in CANONICAL_PAPERS:
        root = RESULTS_ROOT / f"{paper_id}_full"
        run_paths = [root / "run01" / "latte_review_f1.json", root / "run02" / "latte_review_f1.json", root / "run03" / "latte_review_f1.json"]
        reports = [path for path in run_paths if path.exists()]
        if not reports:
            continue
        payloads = [_read_json(path) for path in reports]
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
        micro_average = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "accuracy": (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) else 0.0,
        }
        payload = {
            "paper_id": paper_id,
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
                for path in reports
            ],
            "macro_average": macro_average,
            "micro_average": micro_average,
        }
        out_path = root / "avg_review_f1_3x.json"
        _write_json(out_path, payload)
        rebuilt[_rel(out_path)] = payload
    return rebuilt


def _rebuild_selected_stage2_keys() -> dict[str, Any]:
    rebuilt: dict[str, Any] = {}
    for path in sorted(RESULTS_ROOT.rglob("selected_for_stage2.keys.txt")):
        stage1_path = path.parent / "latte_review_results.json"
        if not stage1_path.exists():
            continue
        rows = _read_json(stage1_path)
        if not isinstance(rows, list):
            continue
        keys = _stage1_positive_keys([row for row in rows if isinstance(row, dict)])
        path.write_text("\n".join(keys) + ("\n" if keys else ""), encoding="utf-8")
        rebuilt[_rel(path)] = {
            "paper_id": _infer_paper_id(path),
            "selected_count": len(keys),
        }
    return rebuilt


def _current_report(paper_id: str, kind: str) -> dict[str, Any]:
    return _read_json(CURRENT_AUTHORITY[paper_id][kind])


def _qa_summary(paper_id: str, arm: str, arm_dir: Path) -> dict[str, Any]:
    stage1_report = _read_json(arm_dir / "stage1_f1.json")
    combined_report = _read_json(arm_dir / "combined_f1.json")
    stage2_rows = _read_json(arm_dir / "latte_fulltext_review_results.json")
    selected_keys = (arm_dir / "selected_for_stage2.keys.txt").read_text(encoding="utf-8").splitlines()
    cutoff_path = arm_dir / "cutoff_audit.json"
    cutoff_payload = _read_json(cutoff_path) if cutoff_path.exists() else {}
    return {
        "paper_id": paper_id,
        "arm": arm,
        "stage1_f1": stage1_report["metrics"]["f1"],
        "combined_f1": combined_report["metrics"]["f1"],
        "stage1_precision": stage1_report["metrics"]["precision"],
        "stage1_recall": stage1_report["metrics"]["recall"],
        "combined_precision": combined_report["metrics"]["precision"],
        "combined_recall": combined_report["metrics"]["recall"],
        "stage2_selected": len([key for key in selected_keys if key.strip()]),
        "stage2_reviewed": sum(1 for row in stage2_rows if row.get("review_state") == "reviewed"),
        "stage2_missing": sum(1 for row in stage2_rows if row.get("review_state") == "missing"),
        "stage1_verdict_counts": stage1_report.get("verdict_counts", {}),
        "combined_verdict_counts": combined_report.get("verdict_counts", {}),
        "cutoff_audit_path": _rel(cutoff_path) if cutoff_path.exists() else None,
        "candidate_total_before_cutoff": cutoff_payload.get("candidate_total_before_cutoff"),
        "candidate_total_after_cutoff": cutoff_payload.get("candidate_total_after_cutoff"),
        "cutoff_excluded_count": cutoff_payload.get("cutoff_excluded_count"),
    }


def _render_qa_report_zh(run_manifest: dict[str, Any]) -> str:
    lines = [
        "# QA-first cutoff-corrected 實驗結果報告",
        "",
        "## Current-State Recap",
        "",
        "- runtime prompts：`scripts/screening/runtime_prompts/runtime_prompts.json`",
        "- production criteria：`criteria_stage1/<paper_id>.json` 與 `criteria_stage2/<paper_id>.json`",
        "- repo-managed 3-reviewer path 現在一律先套 `cutoff_jsons/<paper_id>.json`",
        "",
        "## Metrics Summary",
        "",
        "| Paper | Arm | Stage 1 F1 | Combined F1 | Stage 2 selected | Stage 2 reviewed | Cutoff excluded |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in run_manifest.get("summaries", []):
        lines.append(
            f"| `{summary['paper_id']}` | `{summary['arm']}` | {summary['stage1_f1']:.4f} | "
            f"{summary['combined_f1']:.4f} | {summary['stage2_selected']} | "
            f"{summary['stage2_reviewed']} | {summary.get('cutoff_excluded_count') or 0} |"
        )
    lines.extend(["", "## Baseline Authority", ""])
    for paper_id, baseline in run_manifest.get("baseline", {}).items():
        lines.append(
            f"- `{paper_id}` current Stage 1 F1 = `{baseline['stage1']['metrics']['f1']:.4f}`; "
            f"Combined F1 = `{baseline['combined']['metrics']['f1']:.4f}`."
        )
    lines.extend(["", "## Notes", "", "- `cutoff_filtered` rows are now authoritative excludes.", ""])
    return "\n".join(lines)


def _rebuild_qa_manifests() -> dict[str, Any]:
    rebuilt: dict[str, Any] = {}
    for result_root_name, bundle_path in QA_REPORT_BUNDLES.items():
        result_root = RESULTS_ROOT / result_root_name
        manifest_path = result_root / "run_manifest.json"
        existing = _read_json(manifest_path)
        papers = list(existing.get("papers") or [])
        arms = list(existing.get("arms") or [])
        baseline = {
            paper_id: {
                "stage1": _current_report(paper_id, "stage1"),
                "combined": _current_report(paper_id, "combined"),
            }
            for paper_id in papers
        }
        summaries = []
        for paper_id in papers:
            for arm in arms:
                arm_dir = result_root / f"{paper_id}__{arm}"
                if not arm_dir.exists():
                    continue
                summaries.append(_qa_summary(paper_id, arm, arm_dir))
        hygiene = []
        for paper_id in papers:
            for arm in arms:
                summary_path = result_root / f"{paper_id}__{arm}" / "hygiene_summary.json"
                if summary_path.exists():
                    hygiene.append(_read_json(summary_path))
        run_manifest = dict(existing)
        run_manifest.update(
            {
                "baseline": baseline,
                "summaries": summaries,
                "hygiene": hygiene,
                "cutoff_policy": "pre_review_hard_filter",
            }
        )
        _write_json(manifest_path, run_manifest)
        (result_root / "REPORT_zh.md").write_text(_render_qa_report_zh(run_manifest), encoding="utf-8")
        rebuilt[_rel(manifest_path)] = {
            "summaries": summaries,
            "papers": papers,
            "arms": arms,
        }
    return rebuilt


def _fulltext_direct_summary(paper_id: str, result_root: Path) -> dict[str, Any]:
    paper_dir = result_root / f"{paper_id}__fulltext-direct"
    rows = _read_json(paper_dir / "fulltext_direct_review_results.json")
    metrics = _read_json(paper_dir / "fulltext_direct_f1.json")
    audit = _read_json(paper_dir / "fulltext_resolution_audit.json")
    cutoff_path = paper_dir / "cutoff_audit.json"
    cutoff_payload = _read_json(cutoff_path) if cutoff_path.exists() else {}
    baseline_report = _current_report(paper_id, "combined")
    reviewed_rows = [row for row in rows if row.get("review_state") == "reviewed"]
    senior_invocations = sum(1 for row in reviewed_rows if row.get("round-B_SeniorLead_evaluation") is not None)
    junior_double_high = sum(
        1
        for row in reviewed_rows
        if (row.get("round-A_JuniorNano_evaluation") or 0) >= 4
        and (row.get("round-A_JuniorMini_evaluation") or 0) >= 4
    )
    junior_double_low = sum(
        1
        for row in reviewed_rows
        if (row.get("round-A_JuniorNano_evaluation") or 9) <= 2
        and (row.get("round-A_JuniorMini_evaluation") or 9) <= 2
    )
    return {
        "paper_id": paper_id,
        "workflow_arm": "fulltext-direct",
        "candidate_total": len(rows),
        "reviewed_count": len(reviewed_rows),
        "retrieval_failed_count": sum(1 for row in rows if row.get("review_state") == "retrieval_failed"),
        "retrieval_ambiguous_count": sum(1 for row in rows if row.get("review_state") == "retrieval_ambiguous"),
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
        "current_authority_label": CURRENT_AUTHORITY[paper_id]["label"],
        "current_authority_combined_path": _rel(CURRENT_AUTHORITY[paper_id]["combined"]),
        "cutoff_audit_path": _rel(cutoff_path) if cutoff_path.exists() else None,
        "candidate_total_before_cutoff": cutoff_payload.get("candidate_total_before_cutoff"),
        "candidate_total_after_cutoff": cutoff_payload.get("candidate_total_after_cutoff"),
        "cutoff_excluded_count": cutoff_payload.get("cutoff_excluded_count"),
    }


def _render_fulltext_direct_report_zh(run_manifest: dict[str, Any]) -> str:
    lines = [
        "# Fulltext-Direct cutoff-corrected baseline report",
        "",
        "## Current-State Recap",
        "",
        "- production runtime prompts：`scripts/screening/runtime_prompts/runtime_prompts.json`",
        "- production criteria：`criteria_stage1/<paper_id>.json` / `criteria_stage2/<paper_id>.json`",
        "- pre-review cutoff：`cutoff_jsons/<paper_id>.json`",
        "",
        "## Metrics Summary",
        "",
        "| Paper | Candidates | Reviewed | Direct F1 | Delta vs current combined | Cutoff excluded | Retrieval failed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in run_manifest.get("summaries", []):
        lines.append(
            f"| `{summary['paper_id']}` | {summary['candidate_total']} | {summary['reviewed_count']} | "
            f"{summary['fulltext_direct_f1']:.4f} | {summary['delta_vs_current_combined']:+.4f} | "
            f"{summary.get('cutoff_excluded_count') or 0} | "
            f"{summary['retrieval_failed_count'] + summary['retrieval_ambiguous_count']} |"
        )
    lines.extend(["", "## Baseline Authority", ""])
    for paper_id, baseline in run_manifest.get("baseline", {}).items():
        lines.append(
            f"- `{paper_id}` current authority：`{baseline['authority_label']}`，Combined F1 = `{baseline['combined_metrics']['f1']:.4f}`。"
        )
    lines.extend(["", "## Notes", "", "- `cutoff_filtered` rows stay in the raw results for auditability but no longer count as reviewed.", ""])
    return "\n".join(lines)


def _rebuild_fulltext_direct_manifest() -> dict[str, Any]:
    result_root = RESULTS_ROOT / "fulltext_direct_v1_all4_2026-03-19"
    manifest_path = result_root / "run_manifest.json"
    existing = _read_json(manifest_path)
    papers = list(existing.get("papers") or [])
    baseline = {
        paper_id: {
            "authority_label": CURRENT_AUTHORITY[paper_id]["label"],
            "stage1_path": _rel(CURRENT_AUTHORITY[paper_id]["stage1"]),
            "combined_path": _rel(CURRENT_AUTHORITY[paper_id]["combined"]),
            "combined_metrics": _current_report(paper_id, "combined")["metrics"],
        }
        for paper_id in papers
    }
    summaries = [_fulltext_direct_summary(paper_id, result_root) for paper_id in papers]
    hygiene = []
    for paper_id in papers:
        hygiene_path = result_root / f"{paper_id}__fulltext-direct" / "hygiene_summary.json"
        if hygiene_path.exists():
            hygiene.append(_read_json(hygiene_path))
    for paper_id in papers:
        audit_path = result_root / f"{paper_id}__fulltext-direct" / "fulltext_resolution_audit.json"
        if audit_path.exists():
            audit_payload = _read_json(audit_path)
            cutoff_path = result_root / f"{paper_id}__fulltext-direct" / "cutoff_audit.json"
            cutoff_payload = _read_json(cutoff_path) if cutoff_path.exists() else {}
            audit_payload["candidate_total_before_cutoff"] = cutoff_payload.get("candidate_total_before_cutoff")
            audit_payload["candidate_total_after_cutoff"] = cutoff_payload.get("candidate_total_after_cutoff")
            audit_payload["cutoff_excluded_count"] = cutoff_payload.get("cutoff_excluded_count")
            audit_payload["cutoff_audit_path"] = _rel(cutoff_path) if cutoff_path.exists() else None
            _write_json(audit_path, audit_payload)

    run_manifest = dict(existing)
    run_manifest.update(
        {
            "baseline": baseline,
            "summaries": summaries,
            "hygiene": hygiene,
            "cutoff_policy": "pre_review_hard_filter",
        }
    )
    _write_json(manifest_path, run_manifest)
    (result_root / "REPORT_zh.md").write_text(_render_fulltext_direct_report_zh(run_manifest), encoding="utf-8")
    return {_rel(manifest_path): {"summaries": summaries, "papers": papers}}


def _rebuild_source_summary() -> dict[str, Any]:
    root = RESULTS_ROOT / "source_faithful_vs_operational_2409_2511_runA"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "screening" / "summarize_source_faithful_vs_operational.py"),
        "--results-root",
        str(root),
        "--output-json",
        str(root / "summary.json"),
    ]
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True, capture_output=True, text=True)
    payload = _read_json(root / "summary.json")
    for paper_id, variants in payload.get("papers", {}).items():
        for variant, variant_payload in variants.items():
            for run in variant_payload.get("runs", []):
                run_dir = Path(run["run_dir"])
                cutoff_path = run_dir / "cutoff_audit.json"
                if cutoff_path.exists():
                    cutoff_payload = _read_json(cutoff_path)
                    run["cutoff_audit_path"] = _rel(cutoff_path)
                    run["candidate_total_before_cutoff"] = cutoff_payload.get("candidate_total_before_cutoff")
                    run["candidate_total_after_cutoff"] = cutoff_payload.get("candidate_total_after_cutoff")
                    run["cutoff_excluded_count"] = cutoff_payload.get("cutoff_excluded_count")
    _write_json(root / "summary.json", payload)
    return {_rel(root / "summary.json"): payload}


def _render_current_md(paper_id: str, manifest_entry: dict[str, Any], cutoff_excluded_count: int) -> str:
    historical = manifest_entry.get("historical_baselines", {})
    status = manifest_entry["current_metrics"]["status"]
    status_line = (
        "Current active score authority is the stage-split criteria migration metrics:"
        if status == "current_stage_split"
        else "Current stable reference score authority remains the latest fully benchmarked senior_no_marker metrics:"
    )
    stage1_path = manifest_entry["current_metrics"]["stage1"]["path"]
    combined_path = manifest_entry["current_metrics"]["combined"]["path"]
    stage1_f1 = manifest_entry["current_metrics"]["stage1"]["f1"]
    combined_f1 = manifest_entry["current_metrics"]["combined"]["f1"]
    lines = [
        f"# CURRENT: {paper_id}",
        "",
        f"This file identifies the current authoritative score sources for `{paper_id}`.",
        "",
        "## Current score authority",
        "",
        status_line,
        "",
        f"- Stage 1: `{stage1_path}`",
        f"- Combined: `{combined_path}`",
        "",
        "Current metrics:",
        "",
        f"- Stage 1 F1: `{stage1_f1:.4f}`",
        f"- Combined F1: `{combined_f1:.4f}`",
        "",
        "## Cutoff-first policy",
        "",
        f"- Mandatory pre-review cutoff: `cutoff_jsons/{paper_id}.json`",
        f"- Cutoff-excluded candidates: `{cutoff_excluded_count}`",
        "- Cutoff-failed rows are now forced to `exclude (cutoff_time_window)` before reviewer routing is treated as authoritative.",
        "",
        "## Provenance",
        "",
        "Current runtime uses:",
        "",
        f"- Stage 1 criteria: `criteria_stage1/{paper_id}.json`",
        f"- Stage 2 criteria: `criteria_stage2/{paper_id}.json`",
        "",
        "## Historical baselines in this directory",
        "",
        "These remain useful for comparison, but they are not the current score authority:",
    ]
    for _, paths in historical.items():
        for path in paths:
            lines.append(f"- `{Path(path).name}`")
    lines.extend(
        [
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
    return "\n".join(lines)


def _render_results_readme(results_manifest: dict[str, Any], cutoff_counts: dict[str, int]) -> str:
    lines = [
        "# Screening Results",
        "",
        "Read order for current state:",
        "",
        "1. `AGENTS.md`",
        "2. `docs/chatgpt_current_status_handoff.md`",
        "3. `screening/results/results_manifest.json`",
        "4. the relevant per-paper `CURRENT.md`",
        "",
        "## Current authority table",
        "",
        "| Paper | Current authority | Stage 1 path | Combined path | Stage 1 F1 | Combined F1 | Cutoff excluded |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for paper_id in CANONICAL_PAPERS:
        entry = results_manifest["papers"][paper_id]
        lines.append(
            f"| `{paper_id}` | `{entry['current_metrics']['status']}` | "
            f"`{Path(entry['current_metrics']['stage1']['path']).name}` | "
            f"`{Path(entry['current_metrics']['combined']['path']).name}` | "
            f"{entry['current_metrics']['stage1']['f1']:.4f} | "
            f"{entry['current_metrics']['combined']['f1']:.4f} | "
            f"{cutoff_counts[paper_id]} |"
        )
    lines.extend(
        [
            "",
            "## Current runtime invariants",
            "",
            "- Runtime prompts: `scripts/screening/runtime_prompts/runtime_prompts.json`",
            "- Criteria authority: `criteria_stage1/<paper_id>.json` and `criteria_stage2/<paper_id>.json`",
            "- Cutoff authority: `cutoff_jsons/<paper_id>.json` is a mandatory pre-review hard filter for repo-managed papers",
            "",
        ]
    )
    return "\n".join(lines)


def _render_handoff(results_manifest: dict[str, Any], cutoff_counts: dict[str, int]) -> str:
    lines = [
        "# NLP PRISMA Screening: Canonical Current Status Handoff",
        "",
        "Date: 2026-03-25",
        "Status: authoritative current-state handoff",
        "",
        "Use this file with:",
        "",
        "- `AGENTS.md`",
        "- `screening/results/results_manifest.json`",
        "",
        "Do not infer current state from older reports before reading this file.",
        "",
        "## Runtime authority",
        "",
        "- Runtime prompts: `scripts/screening/runtime_prompts/runtime_prompts.json`",
        "- Stage 1 criteria: `criteria_stage1/<paper_id>.json`",
        "- Stage 2 criteria: `criteria_stage2/<paper_id>.json`",
        "- Pre-review cutoff: `cutoff_jsons/<paper_id>.json`",
        "",
        "## Current metrics table",
        "",
        "| Paper | Stage 1 authority | Combined authority | Stage 1 F1 | Combined F1 | Cutoff excluded |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for paper_id in CANONICAL_PAPERS:
        entry = results_manifest["papers"][paper_id]
        lines.append(
            f"| `{paper_id}` | `{Path(entry['current_metrics']['stage1']['path']).name}` | "
            f"`{Path(entry['current_metrics']['combined']['path']).name}` | "
            f"`{entry['current_metrics']['stage1']['f1']:.4f}` | "
            f"`{entry['current_metrics']['combined']['f1']:.4f}` | "
            f"`{cutoff_counts[paper_id]}` |"
        )
    lines.extend(
        [
            "",
            "## Workflow invariants",
            "",
            "- Cutoff is applied before reviewer routing; cutoff-failed rows are authoritative `exclude (cutoff_time_window)` outputs.",
            "- Stage 1 routing remains: double-high include, double-low exclude, otherwise `SeniorLead`.",
            "- `SeniorLead` remains mandatory once invoked.",
            "",
            "## Current score authority by paper",
            "",
        ]
    )
    for paper_id in CANONICAL_PAPERS:
        entry = results_manifest["papers"][paper_id]
        lines.extend(
            [
                f"### `{paper_id}`",
                "",
                f"- Stage 1: `{entry['current_metrics']['stage1']['path']}`",
                f"- Combined: `{entry['current_metrics']['combined']['path']}`",
                f"- Cutoff policy: `cutoff_jsons/{paper_id}.json`",
                f"- Cutoff-excluded candidates: `{cutoff_counts[paper_id]}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Read order reminder",
            "",
            "1. `AGENTS.md`",
            "2. `docs/chatgpt_current_status_handoff.md`",
            "3. `screening/results/results_manifest.json`",
            "4. the relevant `screening/results/<paper>_full/CURRENT.md`",
            "",
        ]
    )
    return "\n".join(lines)


def _render_stage_split_report(results_manifest: dict[str, Any], cutoff_counts: dict[str, int]) -> str:
    lines = [
        "# Stage-Split Criteria Migration Report",
        "",
        "This report reflects the cutoff-corrected repository state after enforcing pre-review cutoff-first semantics.",
        "",
        "## Adopted production rules",
        "",
        "- Runtime prompts: `scripts/screening/runtime_prompts/runtime_prompts.json`",
        "- Criteria authority: `criteria_stage1/<paper_id>.json` and `criteria_stage2/<paper_id>.json`",
        "- Cutoff authority: `cutoff_jsons/<paper_id>.json` is applied before reviewer routing",
        "",
        "## Current authority metrics",
        "",
        "| Paper | Stage 1 F1 | Combined F1 | Cutoff excluded |",
        "| --- | ---: | ---: | ---: |",
    ]
    for paper_id in ("2409.13738", "2511.13936"):
        entry = results_manifest["papers"][paper_id]
        lines.append(
            f"| `{paper_id}` | {entry['current_metrics']['stage1']['f1']:.4f} | "
            f"{entry['current_metrics']['combined']['f1']:.4f} | {cutoff_counts[paper_id]} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The adopted authority files remain the stage-split migration metrics for `2409` and `2511`.",
            "- The numbers above supersede all pre-cutoff stage-split references elsewhere in the repository.",
            "- Historical comparisons remain useful, but they must now be interpreted through cutoff-first semantics.",
            "",
        ]
    )
    return "\n".join(lines)


def _snapshot_current_metrics() -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for paper_id, config in CURRENT_AUTHORITY.items():
        snapshot[paper_id] = {
            "stage1": _read_json(config["stage1"])["metrics"],
            "combined": _read_json(config["combined"])["metrics"],
        }
    return snapshot


def _replacement_pairs(old_current: dict[str, dict[str, Any]], new_current: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    replacements: list[tuple[str, str]] = []
    for paper_id in CANONICAL_PAPERS:
        for kind in ("stage1", "combined"):
            old_metrics = old_current[paper_id][kind]
            new_metrics = new_current[paper_id][kind]
            replacements.append((f"{old_metrics['f1']:.4f}", f"{new_metrics['f1']:.4f}"))
            replacements.append((f"{old_metrics['precision']:.4f}", f"{new_metrics['precision']:.4f}"))
            replacements.append((f"{old_metrics['recall']:.4f}", f"{new_metrics['recall']:.4f}"))
            old_tuple = f"TP {old_metrics['tp']} / FP {old_metrics['fp']} / TN {old_metrics['tn']} / FN {old_metrics['fn']}"
            new_tuple = f"TP {new_metrics['tp']} / FP {new_metrics['fp']} / TN {new_metrics['tn']} / FN {new_metrics['fn']}"
            replacements.append((old_tuple, new_tuple))
    return replacements


def _rewrite_narrative_docs(old_current: dict[str, dict[str, Any]], new_current: dict[str, dict[str, Any]]) -> list[str]:
    touched: list[str] = []
    replacements = _replacement_pairs(old_current, new_current)
    for path in sorted(DOCS_ROOT.rglob("*")):
        if path.suffix.lower() not in {".md", ".csv", ".json"}:
            continue
        if path.name == "chatgpt_current_status_handoff.md":
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            touched.append(_rel(path))

    for path in sorted(RESULTS_ROOT.rglob("REPORT_zh.md")):
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            touched.append(_rel(path))
    return touched


def _rebuild_current_state_docs() -> dict[str, Any]:
    results_manifest = _read_json(RESULTS_ROOT / "results_manifest.json")
    cutoff_counts = {paper_id: _cutoff_bundle(paper_id)[2]["cutoff_excluded_count"] for paper_id in CANONICAL_PAPERS}
    for paper_id in CANONICAL_PAPERS:
        entry = results_manifest["papers"][paper_id]
        stage1_metrics = _current_report(paper_id, "stage1")["metrics"]
        combined_metrics = _current_report(paper_id, "combined")["metrics"]
        entry["current_metrics"]["stage1"].update(stage1_metrics)
        entry["current_metrics"]["combined"].update(combined_metrics)
        entry["cutoff_policy"] = {
            "path": f"cutoff_jsons/{paper_id}.json",
            "cutoff_excluded_count": cutoff_counts[paper_id],
        }
    results_manifest["current_architecture"]["notes"] = [
        "criteria_jsons/*.json are historical/reference only",
        "repo-managed 3-reviewer workflows now enforce cutoff_jsons/<paper_id>.json before reviewer routing",
        "2409 and 2511 current score authority is stage_split_criteria_migration (cutoff-corrected)",
        "2307 and 2601 current stable reference remains latest fully benchmarked senior_no_marker (cutoff-corrected)",
    ]
    _write_json(RESULTS_ROOT / "results_manifest.json", results_manifest)

    for paper_id in CANONICAL_PAPERS:
        current_path = RESULTS_ROOT / f"{paper_id}_full" / "CURRENT.md"
        current_text = _render_current_md(paper_id, results_manifest["papers"][paper_id], cutoff_counts[paper_id])
        current_path.write_text(current_text, encoding="utf-8")

    (RESULTS_ROOT / "README.md").write_text(_render_results_readme(results_manifest, cutoff_counts), encoding="utf-8")
    (DOCS_ROOT / "chatgpt_current_status_handoff.md").write_text(
        _render_handoff(results_manifest, cutoff_counts),
        encoding="utf-8",
    )
    (DOCS_ROOT / "stage_split_criteria_migration_report.md").write_text(
        _render_stage_split_report(results_manifest, cutoff_counts),
        encoding="utf-8",
    )
    return {
        "results_manifest": _rel(RESULTS_ROOT / "results_manifest.json"),
        "current_md": [_rel(RESULTS_ROOT / f"{paper}_full" / "CURRENT.md") for paper in CANONICAL_PAPERS],
        "handoff": _rel(DOCS_ROOT / "chatgpt_current_status_handoff.md"),
        "stage_split_report": _rel(DOCS_ROOT / "stage_split_criteria_migration_report.md"),
        "results_readme": _rel(RESULTS_ROOT / "README.md"),
    }


def _write_ledger(
    old_current: dict[str, dict[str, Any]],
    report_metrics: dict[str, Any],
    avg_metrics: dict[str, Any],
    selected_keys: dict[str, Any],
    qa_manifests: dict[str, Any],
    fulltext_direct_manifest: dict[str, Any],
    source_summary: dict[str, Any],
    raw_patch_summary: dict[str, Any],
) -> dict[str, Any]:
    current_after = {
        paper_id: {
            "status": CURRENT_AUTHORITY[paper_id]["status"],
            "label": CURRENT_AUTHORITY[paper_id]["label"],
            "stage1_path": _rel(CURRENT_AUTHORITY[paper_id]["stage1"]),
            "combined_path": _rel(CURRENT_AUTHORITY[paper_id]["combined"]),
            "stage1_metrics": _read_json(CURRENT_AUTHORITY[paper_id]["stage1"])["metrics"],
            "combined_metrics": _read_json(CURRENT_AUTHORITY[paper_id]["combined"])["metrics"],
            "cutoff_json_path": f"cutoff_jsons/{paper_id}.json",
            "cutoff_excluded_count": _cutoff_bundle(paper_id)[2]["cutoff_excluded_count"],
        }
        for paper_id in CANONICAL_PAPERS
    }
    ledger = {
        "generated_at": "2026-03-25",
        "old_current_authority_metrics": old_current,
        "current_authority": current_after,
        "raw_patch_summary": raw_patch_summary,
        "report_metrics": report_metrics,
        "avg_review_f1_3x": avg_metrics,
        "selected_for_stage2": selected_keys,
        "qa_manifests": qa_manifests,
        "fulltext_direct_manifest": fulltext_direct_manifest,
        "source_summary": source_summary,
        "stale_binary_docs": [],
    }
    out_path = RESULTS_ROOT / "cutoff_corrected_metrics_manifest.json"
    _write_json(out_path, ledger)
    return ledger


def main() -> int:
    old_current = PRE_CUTOFF_CURRENT_SNAPSHOT
    raw_patch_summary = _patch_raw_results()
    report_metrics = _recompute_all_reports()
    avg_metrics = _rebuild_avg_review_f1()
    selected_keys = _rebuild_selected_stage2_keys()
    qa_manifests = _rebuild_qa_manifests()
    fulltext_direct_manifest = _rebuild_fulltext_direct_manifest()
    source_summary = _rebuild_source_summary()
    current_doc_summary = _rebuild_current_state_docs()
    new_current = {
        paper_id: {
            "stage1": _read_json(CURRENT_AUTHORITY[paper_id]["stage1"])["metrics"],
            "combined": _read_json(CURRENT_AUTHORITY[paper_id]["combined"])["metrics"],
        }
        for paper_id in CANONICAL_PAPERS
    }
    touched_docs = _rewrite_narrative_docs(old_current, new_current)
    ledger = _write_ledger(
        old_current,
        report_metrics,
        avg_metrics,
        selected_keys,
        qa_manifests,
        fulltext_direct_manifest,
        source_summary,
        raw_patch_summary,
    )
    print(
        json.dumps(
            {
                "ledger_path": _rel(RESULTS_ROOT / "cutoff_corrected_metrics_manifest.json"),
                "raw_stage1_patched": len(raw_patch_summary["stage1"]),
                "raw_stage2_patched": len(raw_patch_summary["stage2"]),
                "direct_patched": len(raw_patch_summary["direct"]),
                "reports_recomputed": len(report_metrics),
                "avg_review_f1_rebuilt": len(avg_metrics),
                "selected_keys_rebuilt": len(selected_keys),
                "qa_manifests_rebuilt": len(qa_manifests),
                "fulltext_direct_rebuilt": len(fulltext_direct_manifest),
                "source_summary_rebuilt": len(source_summary),
                "current_docs_rebuilt": current_doc_summary,
                "narrative_docs_touched": len(touched_docs),
                "current_authority": ledger["current_authority"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
