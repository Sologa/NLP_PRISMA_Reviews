# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926_fallback_shard90b`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `low`
- papers: `2601.19926`

## Overall

- repo-compatible F1: `0.9587` (`325/17/7/11`)
- auto-decidable F1: `0.9601` (`325/17/6/10`)
- coverage: `99.44%`
- decisions: `{"exclude": 16, "include": 246, "maybe": 96, "unknown": 2}`
- review states: `{"artifact_filtered": 1, "reviewed": 359}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2601.19926` | 360 | 0.9587 | 0.9601 | 0.9503 | 0.9673 | 325/17/7/11 | 99.44% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$1.184794`
- input tokens: `1915999`
- output tokens: `207242`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
