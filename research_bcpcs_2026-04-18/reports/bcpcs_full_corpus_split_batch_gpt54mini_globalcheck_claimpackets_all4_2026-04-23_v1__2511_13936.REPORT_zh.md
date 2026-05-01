# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `low`
- papers: `2511.13936`

## Overall

- repo-compatible F1: `0.6105` (`29/36/22/1`)
- auto-decidable F1: `0.6105` (`29/36/22/1`)
- coverage: `100.00%`
- decisions: `{"exclude": 23, "include": 11, "maybe": 54}`
- review states: `{"artifact_filtered": 2, "cutoff_filtered": 11, "reviewed": 75}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2511.13936` | 88 | 0.6105 | 0.6105 | 0.4462 | 0.9667 | 29/36/22/1 | 100.00% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$0.245502`
- input tokens: `388759`
- output tokens: `44319`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
