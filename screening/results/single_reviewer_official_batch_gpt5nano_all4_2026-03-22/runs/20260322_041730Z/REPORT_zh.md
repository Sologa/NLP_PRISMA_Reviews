# 單審查者官方批次基線

- `run_id`：`20260322_041730Z`
- mode：`collect`
- model：`gpt-5-nano`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`
- posthoc_cutoff_reapplied_at：`2026-03-23T07:33:41.518781+00:00`

## 指標

| Paper | Candidates | Batch requests | Cutoff filtered | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 84 | 19 | 0.8085 | +0.0242 | 0.7308 | 0.9048 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260322_041730Z/batch_jobs/review/gpt-5-nano`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260322_041730Z/run_manifest.json`
