# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527_fallback_shard15b`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `medium`
- papers: `2307.05527`

## Overall

- repo-compatible F1: `0.8760` (`159/33/18/12`)
- auto-decidable F1: `0.9060` (`159/33/14/0`)
- coverage: `92.79%`
- decisions: `{"exclude": 14, "include": 13, "maybe": 179, "unknown": 16}`
- review states: `{"artifact_filtered": 4, "cutoff_filtered": 8, "reviewed": 194, "stage2_not_available": 16}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2307.05527` | 222 | 0.8760 | 0.9060 | 0.8281 | 0.9298 | 159/33/18/12 | 92.79% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$1.794242`
- input tokens: `1336877`
- output tokens: `574628`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
