# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260417_full_gpt54mini_xhigh_2stagedirect_2307_2601`
- model：`gpt-5.4-mini`
- reasoning_effort：`xhigh`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 193 | 135 | 0.8627 | -0.0994 | 0.9778 | 0.7719 |
| `2601.19926` | 360 | 360 | 276 | 0.8856 | -0.0936 | 0.9819 | 0.8065 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 193 | 135 | 189 | 0 | 0.8283 | -0.1338 | 0.9762 | 0.7193 |
| `2601.19926` | 360 | 360 | 276 | 359 | 0 | 0.8610 | -0.1122 | 0.9847 | 0.7649 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 548 | `completed` | 548 | 0 | 0 |
| `stage2_review` | 411 | `completed` | 411 | 0 | 0 |
