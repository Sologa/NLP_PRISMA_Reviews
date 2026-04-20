# BCPCS Failure-Slice Execution Charter

- 實驗名稱：`bcpcs_failure_slice_gpt5nano_2stage_async`
- current run_id：`bcpcs_guarded_primary22_smoke_gpt5nano_high_allroute_evidencepacket_2026-04-20_v1`
- scope：`primary22`
- 模型：`gpt-5-nano`
- reviewer：`single_reviewer`
- workflow：`two_stage_async_batch`
- requested reasoning effort：`high`；effective：`high`；若 API 不接受，fallback 到最高可接受 effort 並記錄。
- 成本上限：提交下一批前若累計實際或保守估算會超過 `$10.00`，停止並回報。
- 性質：failure-slice diagnostic，不是 full-corpus benchmark，也不是 production workflow replacement。

## Failure Slice

- Source of truth：`docs/deep_research/llm_native_failure_modes_all4_2026-04-15/results/*.json` 的 `case_inventory`。
- Primary slice：22 個 `primary_label != criteria_or_gold_tension` 的 non-tension cases，`allowed_for_unbiased_eval=true`。
- Full inventory：127 cases，包含 primary 22 與 secondary 105。
- Secondary：105 個 criteria/gold tension cases，僅作分層診斷與 inventory reporting，不當作普通模型錯誤修正 evidence。
- `failure_slice_keys.json` 只暴露 `paper_id`、`candidate_key`、`slice_type`、`source_artifact`、`allowed_for_unbiased_eval`、`debug_exposure`、`leakage_notes`。

## Read-Only Inputs

- `criteria_stage1/<paper_id>.json` 與 `criteria_stage2/<paper_id>.json`。
- `cutoff_jsons/<paper_id>.json` cutoff-first policy。
- `refs/<paper_id>/metadata/*.jsonl` 與 `refs/<paper_id>/mds/*.md`。
- `docs/deep_research/llm_native_failure_modes_all4_2026-04-15/results/*.json` 只用於選 key 與最終 evaluation。
- Existing single-reviewer runner/helpers 僅 read-only 參考或 import；不直接呼叫會寫 `screening/results/` 的 bundle runner。

## Write Outputs

- Wrapper code：`research_bcpcs_2026-04-18/src/failure_slice_*.py`。
- Run workspace：`research_bcpcs_2026-04-18/runs/<run_id>/`。
- Reports：`research_bcpcs_2026-04-18/reports/failure_slice_execution_charter_zh.md`、`failure_slice_results_zh.md`、`failure_slice_leakage_audit_zh.md`。
- Cost ledger：`runs/<run_id>/cost/pricing_snapshot.json`、`pre_submit_estimate.*.json`、`cost_ledger.jsonl`、`cost_summary.json`。

## Prompt Boundary

- 可見：stage-specific criteria、cutoff 後的正常 metadata、Stage 1 title/abstract、Stage 2 full text、Stage 1 BCPCS handoff、ledger schema 要求。
- 不可見：gold label、previous prediction、best-run verdict、correctness flag、error_type、primary_label、secondary_labels、why_primary、why_not_other_two、appendix forensic conclusion、one-line fix direction。
- Debug/tuning 不使用真實答案；若真實 candidate 的 gold/forensic answer 被查看，該 candidate 必須 disqualify。

## Workflow

- Stage 1：cutoff-first；只看 title/abstract/metadata；`include`、`maybe`、`route_to_stage2`、`unknown` 才能進 Stage 2。
- Stage 1 unknown 不可靜默轉為 exclude。
- Stage 2：只在 full text exact/normalized resolvable 時送模；retrieval failure 不可偽裝成 semantic exclude。
- Final assembly：Stage 2 supersedes Stage 1；routed/unknown 分開計數並明確映射。

## Required Output Schema

- 每個 candidate/stage 必須輸出 final stage decision、claim-level evidence ledger、support/refute spans、missingness reason、confidence、quote、location、source_path、span_validated、route/unknown reason。
- Pydantic validation model：`research_bcpcs_2026-04-18/src/failure_slice_models.py`。

## Validation Gates

- schema validation。
- dry-run / artifact loader validation。
- forbidden prompt-field scan。
- output path audit：所有寫入必須在 `research_bcpcs_2026-04-18/`。
- source consistency：primary 22、full 127、secondary 105。
- batch terminal-state check。
- parsed output completeness check。
- cost ledger validation。
- final report generation。

## Stopping Conditions

- 累計實際或保守估算 cost 將超過 `$10.00`。
- `gpt-5-nano` 拒絕 `xhigh` 且無法自動確定可接受最高 effort。
- Batch failed/expired/cancelled after one identical retry。
- submitted prompt JSONL 出現 forbidden leakage fields。
- 需要寫到 `research_bcpcs_2026-04-18/` 以外。
- source inventory count 不是 22 / 127 / 105。
- parse/schema failures remain after one identical retry。

## Output Root

- run workspace：`research_bcpcs_2026-04-18/runs/bcpcs_guarded_primary22_smoke_gpt5nano_high_allroute_evidencepacket_2026-04-20_v1`
- 所有新 code/config/run/report 都只寫入 `research_bcpcs_2026-04-18/`。
