#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from failure_slice_common import REPORTS_ROOT, read_json, repo_rel, write_json


def _load_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        return {}
    return read_json(manifest_path)


def _metric_lines(title: str, metrics: dict[str, Any] | None, *, note: str | None = None) -> list[str]:
    lines = [f"## {title}", ""]
    if note:
        lines.extend([note, ""])
    if not metrics:
        lines.append("- not applicable for this run")
        return lines
    lines.extend(
        [
            f"- precision：{metrics.get('precision', 0):.4f}",
            f"- recall：{metrics.get('recall', 0):.4f}",
            f"- F1：{metrics.get('f1', 0):.4f}",
            f"- TP / FP / TN / FN：{metrics.get('tp', 0)} / {metrics.get('fp', 0)} / {metrics.get('tn', 0)} / {metrics.get('fn', 0)}",
            f"- routed / unknown mapped negative：{metrics.get('unknown_mapped_negative_count', 0)}",
        ]
    )
    return lines


def write_execution_charter(*, run_id: str, run_dir: Path) -> Path:
    path = REPORTS_ROOT / "failure_slice_execution_charter_zh.md"
    manifest = _load_manifest(run_dir)
    experiment_name = manifest.get("experiment_name", "bcpcs_failure_slice")
    model = manifest.get("model", "unknown")
    reviewer = manifest.get("reviewer", "single reviewer")
    workflow = manifest.get("workflow", "two-stage async / Batch")
    requested_effort = manifest.get("reasoning_effort_requested", "unspecified")
    effective_effort = manifest.get("reasoning_effort_effective", requested_effort)
    scope = manifest.get("scope", "unspecified")
    lines = [
        "# BCPCS Failure-Slice Execution Charter",
        "",
        f"- 實驗名稱：`{experiment_name}`",
        f"- current run_id：`{run_id}`",
        f"- scope：`{scope}`",
        f"- 模型：`{model}`",
        f"- reviewer：`{reviewer}`",
        f"- workflow：`{workflow}`",
        f"- requested reasoning effort：`{requested_effort}`；effective：`{effective_effort}`；若 API 不接受，fallback 到最高可接受 effort 並記錄。",
        "- 成本上限：提交下一批前若累計實際或保守估算會超過 `$10.00`，停止並回報。",
        "- 性質：failure-slice diagnostic，不是 full-corpus benchmark，也不是 production workflow replacement。",
        "",
        "## Failure Slice",
        "",
        "- Source of truth：`docs/deep_research/llm_native_failure_modes_all4_2026-04-15/results/*.json` 的 `case_inventory`。",
        "- Primary slice：22 個 `primary_label != criteria_or_gold_tension` 的 non-tension cases，`allowed_for_unbiased_eval=true`。",
        "- Full inventory：127 cases，包含 primary 22 與 secondary 105。",
        "- Secondary：105 個 criteria/gold tension cases，僅作分層診斷與 inventory reporting，不當作普通模型錯誤修正 evidence。",
        "- `failure_slice_keys.json` 只暴露 `paper_id`、`candidate_key`、`slice_type`、`source_artifact`、`allowed_for_unbiased_eval`、`debug_exposure`、`leakage_notes`。",
        "",
        "## Read-Only Inputs",
        "",
        "- `criteria_stage1/<paper_id>.json` 與 `criteria_stage2/<paper_id>.json`。",
        "- `cutoff_jsons/<paper_id>.json` cutoff-first policy。",
        "- `refs/<paper_id>/metadata/*.jsonl` 與 `refs/<paper_id>/mds/*.md`。",
        "- `docs/deep_research/llm_native_failure_modes_all4_2026-04-15/results/*.json` 只用於選 key 與最終 evaluation。",
        "- Existing single-reviewer runner/helpers 僅 read-only 參考或 import；不直接呼叫會寫 `screening/results/` 的 bundle runner。",
        "",
        "## Write Outputs",
        "",
        "- Wrapper code：`research_bcpcs_2026-04-18/src/failure_slice_*.py`。",
        "- Run workspace：`research_bcpcs_2026-04-18/runs/<run_id>/`。",
        "- Reports：`research_bcpcs_2026-04-18/reports/failure_slice_execution_charter_zh.md`、`failure_slice_results_zh.md`、`failure_slice_leakage_audit_zh.md`。",
        "- Cost ledger：`runs/<run_id>/cost/pricing_snapshot.json`、`pre_submit_estimate.*.json`、`cost_ledger.jsonl`、`cost_summary.json`。",
        "",
        "## Prompt Boundary",
        "",
        "- 可見：stage-specific criteria、cutoff 後的正常 metadata、Stage 1 title/abstract、Stage 2 full text、Stage 1 BCPCS handoff、ledger schema 要求。",
        "- 不可見：gold label、previous prediction、best-run verdict、correctness flag、error_type、primary_label、secondary_labels、why_primary、why_not_other_two、appendix forensic conclusion、one-line fix direction。",
        "- Debug/tuning 不使用真實答案；若真實 candidate 的 gold/forensic answer 被查看，該 candidate 必須 disqualify。",
        "",
        "## Workflow",
        "",
        "- Stage 1：cutoff-first；只看 title/abstract/metadata；`include`、`maybe`、`route_to_stage2`、`unknown` 才能進 Stage 2。",
        "- Stage 1 unknown 不可靜默轉為 exclude。",
        "- Stage 2：只在 full text exact/normalized resolvable 時送模；retrieval failure 不可偽裝成 semantic exclude。",
        "- Final assembly：Stage 2 supersedes Stage 1；routed/unknown 分開計數並明確映射。",
        "",
        "## Required Output Schema",
        "",
        "- 每個 candidate/stage 必須輸出 final stage decision、claim-level evidence ledger、support/refute spans、missingness reason、confidence、quote、location、source_path、span_validated、route/unknown reason。",
        "- Pydantic validation model：`research_bcpcs_2026-04-18/src/failure_slice_models.py`。",
        "",
        "## Validation Gates",
        "",
        "- schema validation。",
        "- dry-run / artifact loader validation。",
        "- forbidden prompt-field scan。",
        "- output path audit：所有寫入必須在 `research_bcpcs_2026-04-18/`。",
        "- source consistency：primary 22、full 127、secondary 105。",
        "- batch terminal-state check。",
        "- parsed output completeness check。",
        "- cost ledger validation。",
        "- final report generation。",
        "",
        "## Stopping Conditions",
        "",
        "- 累計實際或保守估算 cost 將超過 `$10.00`。",
        "- `gpt-5-nano` 拒絕 `xhigh` 且無法自動確定可接受最高 effort。",
        "- Batch failed/expired/cancelled after one identical retry。",
        "- submitted prompt JSONL 出現 forbidden leakage fields。",
        "- 需要寫到 `research_bcpcs_2026-04-18/` 以外。",
        "- source inventory count 不是 22 / 127 / 105。",
        "- parse/schema failures remain after one identical retry。",
        "",
        "## Output Root",
        "",
        f"- run workspace：`{repo_rel(run_dir)}`",
        "- 所有新 code/config/run/report 都只寫入 `research_bcpcs_2026-04-18/`。",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_results_report(*, run_id: str, run_dir: Path, evaluation: dict[str, Any], cost_summary: dict[str, Any] | None) -> Path:
    path = REPORTS_ROOT / "failure_slice_results_zh.md"
    manifest_path = run_dir / "run_manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    primary = evaluation.get("metrics_primary22") or {}
    secondary = evaluation.get("metrics_secondary")
    all_selected = evaluation.get("metrics_all_selected") or {}
    recovery = evaluation.get("recovery") or {}
    fallback = manifest.get("reasoning_effort_fallback")
    lines = [
        "# BCPCS Failure-Slice Results",
        "",
        "這是 failure-slice diagnostic，不是 full-corpus benchmark，也不是 production workflow replacement。",
        "",
        f"- run_id：`{run_id}`",
        f"- reasoning effort requested：`{manifest.get('reasoning_effort_requested')}`",
        f"- reasoning effort effective：`{manifest.get('reasoning_effort_effective')}`",
        f"- scope：`{evaluation.get('scope')}`",
        f"- rows：{evaluation.get('row_count')}，primary：{evaluation.get('primary_count')}，secondary：{evaluation.get('secondary_count')}",
        "",
    ]
    if fallback:
        lines.extend(
            [
                "## Reasoning Effort Fallback",
                "",
                f"- from：`{fallback.get('from')}`",
                f"- to：`{fallback.get('to')}`",
                f"- reason：{fallback.get('reason')}",
                "",
            ]
        )
    lines.extend(_metric_lines("Primary 22 Metrics", primary))
    lines.extend([""])
    lines.extend(
        _metric_lines(
            "Secondary Criteria/Gold-Tension Metrics",
            secondary,
            note="這組只作分層診斷；不得當作普通模型錯誤修正或 unbiased primary improvement evidence。",
        )
    )
    lines.extend([""])
    lines.extend(
        _metric_lines(
            "All Selected Inventory Metrics",
            all_selected,
            note="這是 failure-slice inventory aggregate，不是 full-corpus benchmark headline。",
        )
    )
    decision_counts = evaluation.get("decision_counts") or {}
    lines.extend(
        [
            "",
            "## Decision Counts",
            "",
        ]
    )
    if decision_counts:
        for decision, count in sorted(decision_counts.items()):
            lines.append(f"- {decision}：{count}")
    else:
        lines.append("- no decisions available")
    lines.extend(
        [
            "",
            "## Recovery",
        "",
        f"- prior FP recovered：{recovery.get('prior_fp_recovered', 0)}",
        f"- prior FN recovered：{recovery.get('prior_fn_recovered', 0)}",
        f"- still wrong：{recovery.get('still_wrong', 0)}",
        f"- newly unknown / routed：{recovery.get('newly_unknown_or_routed', 0)}",
        f"- recovery rate：{recovery.get('recovery_rate_definite_or_unknown_as_not_recovered', 0):.4f}",
        "",
        "## Evidence Ledger",
        "",
        ]
    )
    ev = evaluation.get("evidence_validity") or {}
    lines.extend(
        [
            f"- stage outputs：{ev.get('stage_outputs', 0)}",
            f"- outputs with ledger：{ev.get('stage_outputs_with_ledger', 0)}",
            f"- ledger rows：{ev.get('ledger_rows', 0)}",
            f"- span completeness：{ev.get('span_completeness_rate', 0):.4f}",
            f"- span validated rate：{ev.get('span_validated_rate', 0):.4f}",
            "",
            "## Cost",
            "",
        ]
    )
    if cost_summary:
        lines.extend(
            [
                f"- cost source：`{cost_summary.get('cost_source')}`",
                f"- total input tokens：{cost_summary.get('input_tokens', 0)}",
                f"- total output tokens：{cost_summary.get('output_tokens', 0)}",
                f"- total cost USD：{cost_summary.get('total_cost_usd', 0):.6f}",
            ]
        )
    else:
        lines.append("- no cost summary available")
    lines.extend(["", f"Machine-readable evaluation：`{repo_rel(run_dir / 'evaluation_summary.json')}`"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_leakage_audit(*, run_id: str, run_dir: Path, validation: dict[str, Any]) -> Path:
    path = REPORTS_ROOT / "failure_slice_leakage_audit_zh.md"
    lines = [
        "# BCPCS Failure-Slice Leakage Audit",
        "",
        f"- run_id：`{run_id}`",
        "- failure-slice keys 只用於選 key；gold/error taxonomy 只允許最終 evaluation/reporting 使用。",
        "- reviewer prompt 禁止包含 gold label、previous prediction、correctness、error taxonomy、forensic rationale 或 appendix fix direction。",
        "- criteria/gold tension cases 不作為 primary unbiased improvement evidence。",
        "",
        "## Validation Summary",
        "",
    ]
    for key, value in validation.items():
        lines.append(f"- {key}：`{value}`")
    lines.extend(["", f"Run workspace：`{repo_rel(run_dir)}`"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(run_dir / "leakage_audit_summary.json", validation)
    return path
