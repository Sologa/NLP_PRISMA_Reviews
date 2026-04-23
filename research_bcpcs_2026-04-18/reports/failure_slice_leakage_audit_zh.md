# BCPCS Failure-Slice Leakage Audit

- run_id：`bcpcs_recall_v4g_full127_gpt54mini_globalcheck_claimpackets_compilerrelaxcov_2026-04-23_v1`
- failure-slice keys 只用於選 key；gold/error taxonomy 只允許最終 evaluation/reporting 使用。
- reviewer prompt 禁止包含 gold label、previous prediction、correctness、error taxonomy、forensic rationale 或 appendix fix direction。
- criteria/gold tension cases 不作為 primary unbiased improvement evidence。

## Validation Summary

- source_inventory_counts_ok：`True`
- source_inventory_total：`127`
- source_inventory_primary：`22`
- source_inventory_secondary：`105`
- forbidden_prompt_hit_count：`0`
- schema_failure_count：`0`
- schema_checked_stage_outputs：`254`
- output_path_audit_ok：`False`
- outside_research_change_count：`10`
- cost_ledger_ok：`True`
- direct_forbidden_prompt_hit_count：`0`

Run workspace：`research_bcpcs_2026-04-18/runs/bcpcs_recall_v4g_full127_gpt54mini_globalcheck_claimpackets_compilerrelaxcov_2026-04-23_v1`
