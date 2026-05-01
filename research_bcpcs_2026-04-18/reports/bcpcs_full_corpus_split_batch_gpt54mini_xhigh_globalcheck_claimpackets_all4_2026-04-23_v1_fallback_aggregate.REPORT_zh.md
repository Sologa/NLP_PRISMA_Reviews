# BCPCS Full-Corpus Split-Batch Report

這是目前 BCPCS global-check / claim-packets 架構在四篇 SR 全量 corpus 上，以較小 Batch 單位完成的 all4 run。
不是 current single-reviewer two-stage direct-review baseline。

## Overall

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate`
- model: `gpt-5.4-mini`
- reasoning_effort: `xhigh`
- child runs: `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527, bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2409_13738_fallback_shard30, bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936_fallback_shard30, bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926`
- repo-compatible F1: `0.2355`
- auto-decidable F1: `0.9740`
- coverage: `16.45%`
- decisions: `{"exclude": 45, "include": 74, "maybe": 5, "unknown": 630}`
- review states: `{"artifact_filtered": 11, "cutoff_filtered": 34, "reviewed": 79, "stage2_not_available": 630}`
- total estimated/actual cost: `$7.808285`

## Per Paper

| paper_id | child_run_id | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage | cost |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `2307.05527` | `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2307_05527` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/0/51/171 | 5.41% | $2.415868 |
| `2409.13738` | `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2409_13738_fallback_shard30` | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/0/63/21 | 22.62% | $0.736583 |
| `2511.13936` | `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2511_13936_fallback_shard30` | 0.1176 | 0.6667 | 0.5000 | 0.0667 | 2/2/56/28 | 19.32% | $0.831776 |
| `2601.19926` | `bcpcs_full_corpus_split_batch_gpt54mini_xhigh_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926` | 0.3552 | 0.9865 | 0.9733 | 0.2173 | 73/2/22/263 | 21.11% | $3.824058 |

## Notes

- 單一 707-request Batch 在服務端長時間 `in_progress` 且 `completed=0`，因此改成 split-batch 完成。
- 這仍然是 BCPCS 新架構的 full-corpus run。
