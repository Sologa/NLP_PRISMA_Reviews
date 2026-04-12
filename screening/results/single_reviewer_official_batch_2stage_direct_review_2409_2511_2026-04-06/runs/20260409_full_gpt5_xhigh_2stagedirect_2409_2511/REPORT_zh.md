# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260409_full_gpt5_xhigh_2stagedirect_2409_2511`
- model：`gpt-5`
- reasoning_effort：`xhigh`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 0 | 0.4667 | -0.2833 | 0.3043 | 1.0000 |
| `2511.13936` | 88 | 77 | 0 | 0.5607 | -0.3180 | 0.3896 | 1.0000 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 0 | 0 | 0 | 0.4667 | -0.2833 | 0.3043 | 1.0000 |
| `2511.13936` | 88 | 77 | 0 | 0 | 0 | 0.5607 | -0.3455 | 0.3896 | 1.0000 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 146 | `completed` | 0 | 146 | 0 |
| `stage2_review` | 0 | `skipped_no_requests` | 0 | 0 | 0 |
