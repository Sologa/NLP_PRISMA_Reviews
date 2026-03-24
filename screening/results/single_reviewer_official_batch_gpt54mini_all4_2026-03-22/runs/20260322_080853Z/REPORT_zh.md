# 單審查者官方批次基線

- `run_id`：`20260322_080853Z`
- mode：`collect`
- model：`gpt-5.4-mini`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`
- batch_status：`completed`
- posthoc_cutoff_reapplied_at：`2026-03-23T07:33:40.771383+00:00`

## 指標

| Paper | Candidates | Batch requests | Cutoff filtered | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 84 | 19 | 0.8293 | +0.0450 | 0.8500 | 0.8095 |

## 工件

- batch 工件：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt54mini_all4_2026-03-22/runs/20260322_080853Z/batch_jobs/review/gpt-5.4-mini`
- run manifest：`/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/single_reviewer_official_batch_gpt54mini_all4_2026-03-22/runs/20260322_080853Z/run_manifest.json`
