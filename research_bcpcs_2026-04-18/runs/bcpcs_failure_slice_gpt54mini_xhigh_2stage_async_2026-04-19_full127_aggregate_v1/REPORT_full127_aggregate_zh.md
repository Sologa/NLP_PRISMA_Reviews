# GPT-5.4-mini XHigh Failure-Slice Full127 Aggregate Report

這是 failure-slice diagnostic 的 full127 split aggregate，不是 full benchmark evidence。

- aggregate_run_id：`bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_full127_aggregate_v1`
- component runs：`bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_first60_full127_v1`, `bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_remaining67_full127_v1`
- rows：127（primary 22 / secondary 105）

## Metrics

- primary precision / recall / F1：0.9231 / 0.5714 / 0.7059
- primary TP / FP / TN / FN：12 / 1 / 0 / 9
- secondary precision / recall / F1：0.6923 / 0.2903 / 0.4091
- all-selected precision / recall / F1：0.7500 / 0.3421 / 0.4699

## Recovery

- prior FP recovered：0
- prior FN recovered：39
- still wrong：87
- newly unknown / routed：1

## Evidence Ledger

- stage outputs：204
- ledger rows：468
- span completeness：1.0000
- span validated rate：0.9936

## Cost

- input tokens：1165728
- output tokens：3151528
- total cost USD：7.528086

- aggregate_summary：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54mini_xhigh_2stage_async_2026-04-19_full127_aggregate_v1/aggregate_summary.json`
