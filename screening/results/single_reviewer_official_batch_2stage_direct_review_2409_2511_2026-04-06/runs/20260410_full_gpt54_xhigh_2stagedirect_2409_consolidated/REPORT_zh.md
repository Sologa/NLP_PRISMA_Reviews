# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260410_full_gpt54_xhigh_2stagedirect_2409_consolidated`
- model：`gpt-5.4`
- reasoning_effort：`xhigh`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 26 | 0.8085 | +0.0585 | 0.7308 | 0.9048 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 26 | 69 | 0 | 0.8095 | +0.0595 | 0.8095 | 0.8095 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 69 | `consolidated_success` | 69 | 0 | 0 |
| `stage2_review` | 26 | `consolidated_success` | 26 | 0 | 0 |
