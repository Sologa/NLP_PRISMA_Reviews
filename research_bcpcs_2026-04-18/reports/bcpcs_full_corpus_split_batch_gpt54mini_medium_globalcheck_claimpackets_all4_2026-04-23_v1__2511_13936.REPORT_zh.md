# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `medium`
- papers: `2511.13936`

## Overall

- repo-compatible F1: `0.5979` (`29/38/20/1`)
- auto-decidable F1: `0.5979` (`29/38/18/1`)
- coverage: `97.73%`
- decisions: `{"exclude": 19, "include": 7, "maybe": 60, "unknown": 2}`
- review states: `{"artifact_filtered": 2, "cutoff_filtered": 11, "reviewed": 75}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2511.13936` | 88 | 0.5979 | 0.5979 | 0.4328 | 0.9667 | 29/38/20/1 | 97.73% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$0.391442`
- input tokens: `388759`
- output tokens: `109181`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
