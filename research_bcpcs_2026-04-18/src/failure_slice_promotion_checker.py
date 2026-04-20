#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from failure_slice_common import REPORTS_ROOT, RUNS_ROOT, read_json, repo_rel, utc_now_iso, write_json


POLICY_VERSION = "pure_model_full127_gt_0p8_v2"
REQUIRED_MODELS = ("gpt-5-nano", "gpt-5.4-nano")
AUTO_F1_STRICT_THRESHOLD = 0.8
MIN_COVERAGE = 0.98
MAX_RUNTIME_FAILURES = 0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _is_hybrid_or_reused(manifest: dict[str, Any], cost_summary: dict[str, Any]) -> bool:
    model = str(manifest.get("model") or "")
    workflow = str(manifest.get("workflow") or "").lower()
    experiment_name = str(manifest.get("experiment_name") or "").lower()
    cost_source = str(cost_summary.get("cost_source") or "").lower()
    return (
        model.startswith("hybrid:")
        or "hybrid" in workflow
        or "hybrid" in experiment_name
        or bool(manifest.get("not_fully_automated_new_reviewer"))
        or cost_source.startswith("reused_")
    )


def evaluate_run(run_path: Path) -> dict[str, Any] | None:
    summary_path = run_path / "evaluation_summary_v2.json"
    if not summary_path.exists():
        return None
    summary = read_json(summary_path)
    if not isinstance(summary, dict) or "all127" not in summary:
        return None
    manifest = _load_json_if_exists(run_path / "run_manifest.json")
    cost_summary = _load_json_if_exists(run_path / "cost" / "cost_summary.json")
    bucket = summary.get("all127") or {}
    auto = bucket.get("auto_decidable_f1") or {}
    coverage = bucket.get("coverage") or {}

    run_id = run_path.name
    model = str(manifest.get("model") or summary.get("model") or "")
    manifest_scope = str(manifest.get("scope") or "")
    summary_scope = str(summary.get("scope") or "")
    f1 = _safe_float(auto.get("f1"))
    coverage_rate = _safe_float(coverage.get("definite_decision_rate"))
    runtime_failures = _safe_int(coverage.get("runtime_failure_count"))
    is_hybrid_or_reused = _is_hybrid_or_reused(manifest, cost_summary)
    is_required_pure_model = model in REQUIRED_MODELS and not is_hybrid_or_reused
    is_full127 = manifest_scope == "full127" and summary_scope == "full127"

    reject_reasons: list[str] = []
    if not is_full127:
        reject_reasons.append("not_full127_scope")
    if model not in REQUIRED_MODELS:
        reject_reasons.append("model_not_required_pure_model")
    if is_hybrid_or_reused:
        reject_reasons.append("hybrid_or_reused_baseline_not_promotable")
    if f1 <= AUTO_F1_STRICT_THRESHOLD:
        reject_reasons.append("auto_f1_not_greater_than_0.8")
    if coverage_rate < MIN_COVERAGE:
        reject_reasons.append("coverage_below_98_percent")
    if runtime_failures > MAX_RUNTIME_FAILURES:
        reject_reasons.append("runtime_failures_nonzero")

    passed = is_required_pure_model and is_full127 and not reject_reasons
    return {
        "run_id": run_id,
        "run_dir": repo_rel(run_path),
        "model": model,
        "manifest_scope": manifest_scope,
        "summary_scope": summary_scope,
        "is_full127": is_full127,
        "is_hybrid_or_reused": is_hybrid_or_reused,
        "is_required_pure_model": is_required_pure_model,
        "auto_decidable_f1": f1,
        "coverage": coverage_rate,
        "runtime_failure_count": runtime_failures,
        "passes_promotion_v2": passed,
        "reject_reasons": reject_reasons,
    }


def build_status(runs_root: Path = RUNS_ROOT) -> dict[str, Any]:
    rows = [row for path in sorted(runs_root.iterdir()) if path.is_dir() for row in [evaluate_run(path)] if row]
    pure_full127 = [
        row for row in rows if row["is_required_pure_model"] and row["is_full127"]
    ]
    best_by_model: dict[str, dict[str, Any] | None] = {}
    for model in REQUIRED_MODELS:
        candidates = [row for row in pure_full127 if row["model"] == model]
        best_by_model[model] = max(candidates, key=lambda row: row["auto_decidable_f1"], default=None)
    required_model_status = {
        model: {
            "has_passing_run": bool(best_by_model[model] and best_by_model[model]["passes_promotion_v2"]),
            "best_run": best_by_model[model],
        }
        for model in REQUIRED_MODELS
    }
    promoted = [row for row in rows if row["passes_promotion_v2"]]
    overall_passed = all(item["has_passing_run"] for item in required_model_status.values())
    return {
        "generated_at": utc_now_iso(),
        "policy_version": POLICY_VERSION,
        "requirements": {
            "required_models": list(REQUIRED_MODELS),
            "scope": "full127",
            "auto_decidable_f1_must_be_greater_than": AUTO_F1_STRICT_THRESHOLD,
            "coverage_min": MIN_COVERAGE,
            "runtime_failure_max": MAX_RUNTIME_FAILURES,
            "hybrid_or_reused_baseline_runs_promotable": False,
            "primary22_role": "smoke_only_not_final_success",
        },
        "overall_passed": overall_passed,
        "promoted_run_ids": [row["run_id"] for row in promoted],
        "required_model_status": required_model_status,
        "rejected_hybrid_or_reused_run_ids": [
            row["run_id"] for row in rows if row["is_hybrid_or_reused"]
        ],
        "all_evaluated_runs": rows,
    }


def write_markdown(status: dict[str, Any]) -> None:
    lines = [
        "# BCPCS Failure-Slice >0.8 Promotion Correction",
        "",
        "這是 corrective status report。它覆蓋先前 direct repair report 中把 hybrid row 視為 promoted 的說法。",
        "",
        "## V2 Promotion Rule",
        "",
        "- `gpt-5-nano` 和 `gpt-5.4-nano` 都必須各自以純模型 full127 run 達到 `auto_decidable_f1 > 0.8`。",
        "- primary22 只能當 smoke gate，不能替代 full127。",
        "- hybrid / reused-baseline / mixed-model result 只能是 diagnostic，不可 promotion。",
        "- coverage 必須 `>= 98%`，runtime failures 必須 `0`。",
        "",
        "## Current Status",
        "",
        f"- overall_passed：`{str(status['overall_passed']).lower()}`",
        f"- promoted_run_ids：`{status['promoted_run_ids']}`",
        "",
        "| model | best pure full127 run | auto F1 | coverage | runtime failures | passes v2 |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for model in REQUIRED_MODELS:
        best = status["required_model_status"][model]["best_run"]
        if not best:
            lines.append(f"| `{model}` | none | 0.0000 | 0.00% | 0 | no |")
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{model}`",
                    f"`{best['run_id']}`",
                    f"{best['auto_decidable_f1']:.4f}",
                    f"{best['coverage']:.2%}",
                    str(best["runtime_failure_count"]),
                    "yes" if best["passes_promotion_v2"] else "no",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Corrected Interpretation",
            "",
            "- 目前沒有任何純模型 full127 run 達到 `>0.8`。",
            "- `bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1` 是 `diagnostic_only_not_promoted`，因為它混用了 direct primary rows 與 locked-baseline secondary rows。",
            "- `gpt-5.4-nano` direct profile 的 primary22 表現可作 smoke success，但 secondary105 regression 使 full127 不達標。",
            "- 下一步應先做 FN/FP taxonomy 與 criteria/evidence-window coverage 分析，不應把目前 local-packet profile 直接擴大或宣稱成功。",
        ]
    )
    (REPORTS_ROOT / "failure_slice_requirement_correction_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_queue_status_v2(status: dict[str, Any]) -> None:
    queue_status = {
        "created_at": status["generated_at"],
        "policy_version": status["policy_version"],
        "promoted_run_id": None,
        "promoted_run_ids": [],
        "overall_passed": status["overall_passed"],
        "stop_reason": "pure_model_full127_gt_0p8_requirement_not_met",
        "diagnostic_only_not_promoted_run_ids": status["rejected_hybrid_or_reused_run_ids"],
        "note": "Previous hybrid promotion language is superseded. Hybrid/reused-baseline rows cannot satisfy the pure-model full127 >0.8 requirement.",
    }
    write_json(REPORTS_ROOT / "failure_slice_direct_repair_queue_status.json", queue_status)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check BCPCS failure-slice pure-model >0.8 promotion policy.")
    parser.add_argument("--write-reports", action="store_true", help="Write corrective JSON and Markdown reports.")
    args = parser.parse_args()

    status = build_status()
    if args.write_reports:
        write_json(REPORTS_ROOT / "failure_slice_promotion_status_v2.json", status)
        write_markdown(status)
        write_queue_status_v2(status)
    print(json.dumps({
        "policy_version": status["policy_version"],
        "overall_passed": status["overall_passed"],
        "promoted_run_ids": status["promoted_run_ids"],
        "required_model_status": {
            model: {
                "has_passing_run": payload["has_passing_run"],
                "best_run_id": payload["best_run"]["run_id"] if payload["best_run"] else None,
                "best_f1": payload["best_run"]["auto_decidable_f1"] if payload["best_run"] else None,
            }
            for model, payload in status["required_model_status"].items()
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
