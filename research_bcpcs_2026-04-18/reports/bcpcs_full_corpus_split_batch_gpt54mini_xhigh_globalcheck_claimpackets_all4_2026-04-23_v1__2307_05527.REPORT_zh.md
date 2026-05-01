# BCPCS Full-Corpus Batch Report

這是使用目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上的 Batch run。
它不是 current single-reviewer two-stage direct-review baseline。

## Run

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527`
- model: `gpt-5.4-mini`
- workflow: `bcpcs_v3_recall_repair_batch_full_corpus`
- reasoning_effort: `xhigh`
- papers: `2307.05527`

## Overall

- repo-compatible F1: `0.0000` (`0/0/51/171`)
- auto-decidable F1: `0.0000` (`0/0/12/0`)
- coverage: `5.41%`
- decisions: `{"exclude": 12, "unknown": 210}`
- review states: `{"artifact_filtered": 4, "cutoff_filtered": 8, "stage2_not_available": 210}`

## Per Paper

| paper_id | rows | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `2307.05527` | 222 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/0/51/171 | 5.41% |

## Validation

- forbidden prompt hits: `0`
- schema failures: `0`
- output path audit ok: `false`
- cost ledger ok: `true`

## Cost

- total cost: `$2.415868`
- input tokens: `1330507`
- output tokens: `851968`

## Notes

- 這是 full-corpus run，所以 headline 應看 repo-compatible F1，而不是 failure-slice >0.8 gate。
- 目前架構仍是 recall-biased maybe policy；因此需要同時看 F1、coverage 和 decision mix。
