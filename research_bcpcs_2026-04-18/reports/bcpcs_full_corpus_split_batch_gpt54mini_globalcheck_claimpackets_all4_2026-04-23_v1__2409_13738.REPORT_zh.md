# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2409_13738`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `low`
- papers: `2409.13738`

## Overall

- repo-compatible F1: `0.5122` (`21/40/23/0`)
- auto-decidable F1: `0.5122` (`21/40/23/0`)
- coverage: `100.00%`
- decisions: `{"exclude": 23, "include": 12, "maybe": 49}`
- review states: `{"artifact_filtered": 4, "cutoff_filtered": 15, "reviewed": 65}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2409.13738` | 84 | 0.5122 | 0.5122 | 0.3443 | 1.0000 | 21/40/23/0 | 100.00% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$0.257697`
- input tokens: `366781`
- output tokens: `53402`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
