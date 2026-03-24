# 單審查者官方批次基線

- `run_id`：`20260321_180142Z`
- mode：`collect`
- model：`gpt-5-mini`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`
- posthoc_cutoff_reapplied_at：`2026-03-23T07:33:41.174059+00:00`

## 指標

| Paper | Candidates | Batch requests | Cutoff filtered | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 222 | 30 | 0.9169 | -0.0412 | 0.9675 | 0.8713 |
| `2409.13738` | 84 | 84 | 19 | 0.8372 | +0.0529 | 0.8182 | 0.8571 |
| `2511.13936` | 88 | 88 | 37 | 0.7451 | -0.1363 | 0.9048 | 0.6333 |
| `2601.19926` | 360 | 360 | 6 | 0.9589 | -0.0144 | 0.9813 | 0.9375 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260321_180142Z/batch_jobs/review/gpt-5-mini`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260321_180142Z/run_manifest.json`
