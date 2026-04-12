# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260406_smoke_gpt5mini_low_2stagedirect_2409_2511`
- model：`gpt-5-mini`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 3 | 3 | 1 | 1.0000 | +0.2500 | 1.0000 | 1.0000 |
| `2511.13936` | 4 | 4 | 2 | 0.6667 | -0.2121 | 0.5000 | 1.0000 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 3 | 3 | 1 | 3 | 0 | 1.0000 | +0.2500 | 1.0000 | 1.0000 |
| `2511.13936` | 4 | 4 | 2 | 4 | 0 | 0.6667 | -0.2396 | 0.5000 | 1.0000 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 7 | `completed` | 7 | 0 | 0 |
| `stage2_review` | 3 | `completed` | 3 | 0 | 0 |
