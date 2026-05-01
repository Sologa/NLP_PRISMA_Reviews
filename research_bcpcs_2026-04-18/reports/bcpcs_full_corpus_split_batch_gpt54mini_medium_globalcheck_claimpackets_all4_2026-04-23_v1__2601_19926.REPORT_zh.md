# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `medium`
- papers: `2601.19926`

## Overall

- repo-compatible F1: `0.9398` (`312/16/8/24`)
- auto-decidable F1: `0.9585` (`312/16/7/11`)
- coverage: `96.11%`
- decisions: `{"exclude": 18, "include": 235, "maybe": 93, "unknown": 14}`
- review states: `{"artifact_filtered": 1, "reviewed": 358, "stage2_not_available": 1}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2601.19926` | 360 | 0.9398 | 0.9585 | 0.9512 | 0.9286 | 312/16/8/24 | 96.11% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$1.885005`
- input tokens: `1915999`
- output tokens: `518447`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
