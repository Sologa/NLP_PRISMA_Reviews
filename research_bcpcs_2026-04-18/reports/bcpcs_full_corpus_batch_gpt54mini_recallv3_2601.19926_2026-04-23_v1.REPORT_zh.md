# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_batch_gpt54mini_recallv3_2601.19926_2026-04-23_v1`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `low`
- papers: `2601.19926`

## Overall

- repo-compatible F1: `0.9669` (`336/23/1/0`)
- auto-decidable F1: `0.9669` (`336/23/1/0`)
- coverage: `100.00%`
- decisions: `{"exclude": 1, "include": 232, "maybe": 127}`
- review states: `{"artifact_filtered": 1, "reviewed": 359}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2601.19926` | 360 | 0.9669 | 0.9669 | 0.9359 | 1.0000 | 336/23/1/0 | 100.00% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `true`
- cost ledger ok: `true`

## Cost

- total cost: `$0.830864`
- input tokens: `1694039`
- output tokens: `86933`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
