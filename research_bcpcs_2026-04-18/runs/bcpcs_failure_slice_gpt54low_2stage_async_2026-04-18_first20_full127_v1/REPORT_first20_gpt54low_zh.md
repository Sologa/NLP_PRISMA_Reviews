# GPT-5.4 Low Failure-Slice First20 Report

這是 failure-slice diagnostic 的 first20 staged run，不是 full benchmark evidence。

- run_id：`bcpcs_failure_slice_gpt54low_2stage_async_2026-04-18_first20_full127_v1`
- model：`gpt-5.4`
- reasoning effort：`low`
- scope：`first20_full127`
- selected rows：20（primary 4 / secondary 16）

## Metrics

- primary precision / recall / F1：1.0000 / 0.5000 / 0.6667
- primary TP / FP / TN / FN：2 / 0 / 0 / 2
- secondary precision / recall / F1：0.7500 / 0.2143 / 0.3333
- all-selected precision / recall / F1：0.8333 / 0.2778 / 0.4167

## Recovery

- prior FP recovered：1
- prior FN recovered：5
- still wrong：14
- newly unknown / routed：0

## Evidence Ledger

- stage outputs：32
- ledger rows：80
- span completeness：1.0000
- span validated rate：0.9625

## Cost

- input tokens：159257
- output tokens：35363
- total cost USD：0.464294

## Validation


- evaluation_summary：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54low_2stage_async_2026-04-18_first20_full127_v1/evaluation_summary.json`
- validation_summary：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54low_2stage_async_2026-04-18_first20_full127_v1/validation_summary.json`
