# BCPCS Full-Corpus Split-Batch Report

這是目前 BCPCS global-check / claim-packets 架構在四篇 SR 全量 corpus 上，以較小 Batch 單位完成的 all4 run。
不是 current single-reviewer two-stage direct-review baseline。

## Overall

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1`
- model: `gpt-5.4-mini`
- child runs: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527, bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2409_13738, bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936, bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926`
- repo-compatible F1: `0.8827`
- auto-decidable F1: `0.8842`
- coverage: `99.47%`
- decisions: `{"exclude": 80, "include": 292, "maybe": 378, "unknown": 4}`
- review states: `{"artifact_filtered": 11, "cutoff_filtered": 34, "reviewed": 707, "stage2_not_available": 2}`
- total estimated/actual cost: `$2.727290`

## Per Paper

| paper_id | child_run_id | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage | cost |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `2307.05527` | `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527` | 0.9072 | 0.9072 | 0.8301 | 1.0000 | 171/35/16/0 | 99.10% | $1.038670 |
| `2409.13738` | `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2409_13738` | 0.5122 | 0.5122 | 0.3443 | 1.0000 | 21/40/23/0 | 100.00% | $0.257697 |
| `2511.13936` | `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936` | 0.6105 | 0.6105 | 0.4462 | 0.9667 | 29/36/22/1 | 100.00% | $0.245502 |
| `2601.19926` | `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926` | 0.9525 | 0.9554 | 0.9497 | 0.9554 | 321/17/7/15 | 99.44% | $1.185420 |

## Notes

- 單一 707-request Batch 在服務端長時間 `in_progress` 且 `completed=0`，因此改成 split-batch 完成。
- 這仍然是 BCPCS 新架構的 full-corpus run。
