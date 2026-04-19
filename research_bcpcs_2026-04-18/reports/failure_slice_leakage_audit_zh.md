# BCPCS Failure-Slice Leakage Audit

- run_id：`bcpcs_methodfix_gpt54nano_2stage_async_2026-04-19_full127_v1`
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
- schema_checked_stage_outputs：`213`
- output_path_audit_ok：`True`
- outside_research_change_count：`0`
- cost_ledger_ok：`True`

Run workspace：`research_bcpcs_2026-04-18/runs/bcpcs_methodfix_gpt54nano_2stage_async_2026-04-19_full127_v1`
