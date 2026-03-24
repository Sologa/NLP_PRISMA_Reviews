# 單審查者官方批次基線

- `run_id`：`20260322_053646Z`
- mode：`collect`
- model：`gpt-5.4-nano`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`
- posthoc_cutoff_reapplied_at：`2026-03-23T07:33:40.896754+00:00`

## 指標

| Paper | Candidates | Batch requests | Cutoff filtered | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 84 | 19 | 0.8400 | +0.0557 | 0.7241 | 1.0000 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt54nano_all4_2026-03-21/runs/20260322_053646Z/batch_jobs/review/gpt-5.4-nano`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt54nano_all4_2026-03-21/runs/20260322_053646Z/run_manifest.json`
