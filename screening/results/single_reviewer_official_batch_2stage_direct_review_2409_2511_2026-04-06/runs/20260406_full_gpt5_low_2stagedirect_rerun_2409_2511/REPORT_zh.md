# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260406_full_gpt5_low_2stagedirect_rerun_2409_2511`
- model：`gpt-5`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 28 | 0.8571 | +0.1071 | 0.7500 | 1.0000 |
| `2511.13936` | 88 | 77 | 26 | 0.8929 | +0.0141 | 0.9615 | 0.8333 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 28 | 69 | 0 | 0.8889 | +0.1389 | 0.8333 | 0.9524 |
| `2511.13936` | 88 | 77 | 26 | 77 | 0 | 0.8727 | -0.0335 | 0.9600 | 0.8000 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 146 | `completed` | 146 | 0 | 0 |
| `stage2_review` | 54 | `completed` | 54 | 0 | 0 |
