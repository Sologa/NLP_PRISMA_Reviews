# 單審查者官方批次基線

- `run_id`：`20260321_173147Z`
- mode：`collect`
- model：`gpt-5-nano`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`
- posthoc_cutoff_reapplied_at：`2026-03-23T07:33:41.433368+00:00`

## 指標

| Paper | Candidates | Batch requests | Cutoff filtered | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 222 | 30 | 0.6299 | -0.3282 | 0.9639 | 0.4678 |
| `2409.13738` | 84 | 84 | 19 | 0.7660 | -0.0183 | 0.6923 | 0.8571 |
| `2511.13936` | 88 | 88 | 37 | 0.7347 | -0.1467 | 0.9474 | 0.6000 |
| `2601.19926` | 360 | 360 | 6 | 0.9594 | -0.0139 | 0.9696 | 0.9494 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260321_173147Z/batch_jobs/review/gpt-5-nano`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260321_173147Z/run_manifest.json`
