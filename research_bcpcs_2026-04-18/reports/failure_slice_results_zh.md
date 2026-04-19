# BCPCS Failure-Slice Results

這是 failure-slice diagnostic，不是 full-corpus benchmark，也不是 production workflow replacement。

- run_id：`bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1`
- reasoning effort requested：`xhigh`
- reasoning effort effective：`xhigh`
- scope：`full127`
- rows：127，primary：22，secondary：105

## Primary 22 Metrics

- precision：0.9333
- recall：0.6667
- F1：0.7778
- TP / FP / TN / FN：14 / 1 / 0 / 7
- routed / unknown mapped negative：1

## Secondary Criteria/Gold-Tension Metrics

這組只作分層診斷；不得當作普通模型錯誤修正或 unbiased primary improvement evidence。

- precision：0.8000
- recall：0.3871
- F1：0.5217
- TP / FP / TN / FN：36 / 9 / 3 / 57
- routed / unknown mapped negative：7

## All Selected Inventory Metrics

這是 failure-slice inventory aggregate，不是 full-corpus benchmark headline。

- precision：0.8333
- recall：0.4386
- F1：0.5747
- TP / FP / TN / FN：50 / 10 / 3 / 64
- routed / unknown mapped negative：8

## Decision Counts

- exclude：59
- include：59
- maybe：1
- route_to_stage2：2
- unknown：6

## Recovery

- prior FP recovered：0
- prior FN recovered：50
- still wrong：69
- newly unknown / routed：8
- recovery rate：0.3937

## Evidence Ledger

- stage outputs：208
- outputs with ledger：208
- ledger rows：629
- span completeness：1.0000
- span validated rate：0.9650

## Cost

- cost source：`batch_usage`
- total input tokens：1482405
- total output tokens：4008416
- total cost USD：2.653501

Machine-readable evaluation：`research_bcpcs_2026-04-18/runs/bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1/evaluation_summary.json`
