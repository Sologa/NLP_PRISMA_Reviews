# 單審查者官方批次基線

- `run_id`：`20260321_180142Z`
- mode：`collect`
- model：`gpt-5-mini`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`

## 指標

| Paper | Candidates | Batch requests | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 222 | 0.9649 | +0.0068 | 0.9649 | 0.9649 |
| `2409.13738` | 84 | 84 | 0.8182 | +0.0339 | 0.7826 | 0.8571 |
| `2511.13936` | 88 | 88 | 0.9032 | +0.0218 | 0.8750 | 0.9333 |
| `2601.19926` | 360 | 360 | 0.9636 | -0.0097 | 0.9815 | 0.9464 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260321_180142Z/batch_jobs/review/gpt-5-mini`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260321_180142Z/run_manifest.json`
