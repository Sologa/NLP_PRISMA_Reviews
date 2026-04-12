# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260406_full_gpt5mini_low_2stagedirect_2409_2511`
- model：`gpt-5-mini`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 32 | 0.7925 | +0.0425 | 0.6562 | 1.0000 |
| `2511.13936` | 88 | 77 | 29 | 0.8475 | -0.0313 | 0.8621 | 0.8333 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 32 | 69 | 0 | 0.8750 | +0.1250 | 0.7778 | 1.0000 |
| `2511.13936` | 88 | 77 | 29 | 77 | 0 | 0.8621 | -0.0442 | 0.8929 | 0.8333 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 146 | `completed` | 146 | 0 | 0 |
| `stage2_review` | 61 | `completed` | 61 | 0 | 0 |
