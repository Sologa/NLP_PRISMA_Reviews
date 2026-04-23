# BCPCS Full-Corpus Split-Batch Report

這是目前 BCPCS V3 recall-repair 架構在四篇 SR 全量 corpus 上，以較小 Batch 單位完成的 all4 run。
不是 current single-reviewer two-stage direct-review baseline。

## Overall

- run_id: `bcpcs_full_corpus_split_batch_gpt54mini_recallv3_all4_2026-04-23_v1`
- model: `gpt-5.4-mini`
- child runs: `bcpcs_full_corpus_batch_gpt54mini_recallv3_2307.05527_2026-04-23_v1, bcpcs_full_corpus_batch_gpt54mini_recallv3_2409.13738_2026-04-23_v1, bcpcs_full_corpus_batch_gpt54mini_recallv3_2511.13936_2026-04-23_v1, bcpcs_full_corpus_batch_gpt54mini_recallv3_2601.19926_2026-04-23_v1`
- repo-compatible F1: `0.8822`
- auto-decidable F1: `0.8822`
- coverage: `99.73%`
- decisions: `{"exclude": 45, "include": 288, "maybe": 419, "unknown": 2}`
- review states: `{"artifact_filtered": 11, "cutoff_filtered": 34, "reviewed": 707, "stage2_not_available": 2}`
- total estimated/actual cost: `$1.674888`

## Per Paper

| paper_id | child_run_id | repo-compatible F1 | auto F1 | precision | recall | TP/FP/TN/FN | coverage | cost |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `2307.05527` | `bcpcs_full_corpus_batch_gpt54mini_recallv3_2307.05527_2026-04-23_v1` | 0.9024 | 0.9024 | 0.8221 | 1.0000 | 171/37/14/0 | 99.10% | $0.530726 |
| `2409.13738` | `bcpcs_full_corpus_batch_gpt54mini_recallv3_2409.13738_2026-04-23_v1` | 0.4884 | 0.4884 | 0.3231 | 1.0000 | 21/44/19/0 | 100.00% | $0.147999 |
| `2511.13936` | `bcpcs_full_corpus_batch_gpt54mini_recallv3_2511.13936_2026-04-23_v1` | 0.5714 | 0.5714 | 0.4000 | 1.0000 | 30/45/13/0 | 100.00% | $0.165299 |
| `2601.19926` | `bcpcs_full_corpus_batch_gpt54mini_recallv3_2601.19926_2026-04-23_v1` | 0.9669 | 0.9669 | 0.9359 | 1.0000 | 336/23/1/0 | 100.00% | $0.830864 |

## Notes

- 單一 707-request Batch 在服務端長時間 `in_progress` 且 `completed=0`，因此改成 split-batch 完成。
- 這仍然是 BCPCS 新架構的 full-corpus run。
