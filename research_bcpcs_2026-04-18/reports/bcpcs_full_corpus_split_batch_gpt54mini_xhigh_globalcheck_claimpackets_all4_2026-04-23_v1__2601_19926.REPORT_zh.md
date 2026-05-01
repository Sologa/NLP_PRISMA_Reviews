# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `xhigh`
- papers: `2307.05527, 2409.13738, 2511.13936, 2601.19926`

## Overall

- repo-compatible F1: `0.3552` (`73/2/22/263`)
- auto-decidable F1: `0.9865` (`73/2/1/0`)
- coverage: `21.11%`
- decisions: `{"exclude": 1, "include": 73, "maybe": 2, "unknown": 284}`
- review states: `{"artifact_filtered": 1, "reviewed": 75, "stage2_not_available": 284}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2307.05527` | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/0/0/0 | 0.00% |
| `2409.13738` | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/0/0/0 | 0.00% |
| `2511.13936` | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/0/0/0 | 0.00% |
| `2601.19926` | 360 | 0.3552 | 0.9865 | 0.9733 | 0.2173 | 73/2/22/263 | 21.11% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$3.824058`
- input tokens: `1915999`
- output tokens: `1380248`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
