# 單審查者官方批次基線

- `run_id`：`20260321_173147Z`
- mode：`collect`
- model：`gpt-5-nano`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`

## 指標

| Paper | Candidates | Batch requests | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 222 | 0.6940 | -0.2641 | 0.9588 | 0.5439 |
| `2409.13738` | 84 | 84 | 0.7059 | -0.0784 | 0.6000 | 0.8571 |
| `2511.13936` | 88 | 88 | 0.9000 | +0.0186 | 0.9000 | 0.9000 |
| `2601.19926` | 360 | 360 | 0.9625 | -0.0108 | 0.9698 | 0.9554 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260321_173147Z/batch_jobs/review/gpt-5-nano`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260321_173147Z/run_manifest.json`
