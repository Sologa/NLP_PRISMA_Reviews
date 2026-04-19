# GPT-5.4-mini XHigh Failure-Slice Remaining67 Report

這是 failure-slice diagnostic 的 remaining67 staged run，不是 full benchmark evidence。

- run_id：`bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_remaining67_full127_v1`
- model：`gpt-5.4-mini`
- reasoning effort：`xhigh`
- scope：`remaining67_full127`
- selected rows：67（primary 12 / secondary 55）

## Metrics

- primary precision / recall / F1：1.0000 / 0.5000 / 0.6667
- primary TP / FP / TN / FN：6 / 0 / 0 / 6
- secondary precision / recall / F1：0.5882 / 0.2083 / 0.3077
- all-selected precision / recall / F1：0.6957 / 0.2667 / 0.3855

## Recovery

- prior FP recovered：0
- prior FN recovered：16
- still wrong：50
- newly unknown / routed：1

## Evidence Ledger

- stage outputs：104
- ledger rows：230
- span completeness：1.0000
- span validated rate：0.9913

## Cost

- input tokens：580764
- output tokens：1571363
- total cost USD：3.753353

## Validation

- forbidden_prompt_hit_count：`0`
- schema_failure_count：`0`
- output_path_audit_ok：`True`
- cost_ledger_ok：`True`

- evaluation_summary：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_remaining67_full127_v1/evaluation_summary.json`
- validation_summary：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_remaining67_full127_v1/validation_summary.json`
