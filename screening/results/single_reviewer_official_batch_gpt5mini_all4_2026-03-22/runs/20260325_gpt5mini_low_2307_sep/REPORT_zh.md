# 單審查者官方批次基線

- `run_id`：`20260325_gpt5mini_low_2307_sep`
- mode：`collect`
- model：`gpt-5-mini`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`

## 指標

| Paper | Candidates | Batch requests | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 192 | 0.9130 | -0.0451 | 0.9761 | 0.8596 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260325_gpt5mini_low_2307_sep/batch_jobs/review/gpt-5-mini`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt5mini_all4_2026-03-22/runs/20260325_gpt5mini_low_2307_sep/run_manifest.json`
