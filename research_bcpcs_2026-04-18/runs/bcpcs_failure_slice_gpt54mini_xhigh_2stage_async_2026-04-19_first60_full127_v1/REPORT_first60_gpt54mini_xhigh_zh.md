# GPT-5.4-mini XHigh Failure-Slice First60 Report

這是 failure-slice diagnostic 的 first60 staged run，不是 full benchmark evidence。

- run_id：`bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_first60_full127_v1`
- model：`gpt-5.4-mini`
- reasoning effort：`xhigh`
- scope：`first60_full127`
- selected rows：60（primary 10 / secondary 50）

## Metrics

- primary precision / recall / F1：0.8571 / 0.6667 / 0.7500
- primary TP / FP / TN / FN：6 / 1 / 0 / 3
- secondary precision / recall / F1：0.7727 / 0.3778 / 0.5075
- all-selected precision / recall / F1：0.7931 / 0.4259 / 0.5542

## Recovery

- prior FP recovered：0
- prior FN recovered：23
- still wrong：37
- newly unknown / routed：0

## Evidence Ledger

- stage outputs：100
- ledger rows：238
- span completeness：1.0000
- span validated rate：0.9958

## Cost

- input tokens：584964
- output tokens：1580165
- total cost USD：3.774733

## Retry Note

- stage2 main batch 有 1 個 candidate 因 `finish_reason=length` 導致空輸出；已做 1 次 identical single-item Batch retry 並成功整合。
- retry custom_id：`stage2_review__2409.13738__bellan_gpt3_2022`
- retry cost USD：0.052257

## Validation

- forbidden_prompt_hit_count：`0`
- schema_failure_count：`0`
- output_path_audit_ok：`True`
- cost_ledger_ok：`True`

- evaluation_summary：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_first60_full127_v1/evaluation_summary.json`
- validation_summary：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_first60_full127_v1/validation_summary.json`
