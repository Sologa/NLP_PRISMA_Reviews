# BCPCS Full-Corpus Split-Batch Report

這是目前 BCPCS global-check / claim-packets 架構在四篇 SR 全量 corpus 上，以較小 Batch 單位完成的 all4 run。
不是 current single-reviewer two-stage direct-review baseline。

## Overall

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate`
- model: `gpt-5.4-mini`
- reasoning_effort: `medium`
- child runs: `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527_fallback_shard15b, bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2409_13738_fallback_shard10b, bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936, bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926`
- repo-compatible F1: `0.8654`
- auto-decidable F1: `0.8838`
- coverage: `95.49%`
- decisions: `{"exclude": 74, "include": 273, "maybe": 373, "unknown": 34}`
- review states: `{"artifact_filtered": 11, "cutoff_filtered": 34, "reviewed": 690, "stage2_not_available": 19}`
- total estimated/actual cost: `$4.808946`

## Per Paper

| paper_id | child_run_id | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage | cost |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `2307.05527` | `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527_fallback_shard15b` | 0.8760 | 0.9060 | 0.8281 | 0.9298 | 159/33/18/12 | 92.79% | $2.036397 |
| `2409.13738` | `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2409_13738_fallback_shard10b` | 0.5250 | 0.5250 | 0.3559 | 1.0000 | 21/38/25/0 | 97.62% | $0.496102 |
| `2511.13936` | `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936` | 0.5979 | 0.5979 | 0.4328 | 0.9667 | 29/38/20/1 | 97.73% | $0.391442 |
| `2601.19926` | `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926` | 0.9398 | 0.9585 | 0.9512 | 0.9286 | 312/16/8/24 | 96.11% | $1.885005 |

## Notes

- 單一 707-request Batch 在服務端長時間 `in_progress` 且 `completed=0`，因此改成 split-batch 完成。
- 這仍然是 BCPCS 新架構的 full-corpus run。
