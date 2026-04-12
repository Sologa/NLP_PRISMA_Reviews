# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260408_full_gpt54_low_2stagedirect_2409_2511`
- model：`gpt-5.4`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 22 | 0.7727 | +0.0227 | 0.7391 | 0.8095 |
| `2511.13936` | 88 | 77 | 28 | 0.8438 | -0.0350 | 0.7941 | 0.9000 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 22 | 68 | 0 | 0.7692 | +0.0192 | 0.8333 | 0.7143 |
| `2511.13936` | 88 | 77 | 28 | 71 | 0 | 0.8333 | -0.0729 | 0.8333 | 0.8333 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 146 | `completed` | 139 | 7 | 0 |
| `stage2_review` | 50 | `completed` | 50 | 0 | 0 |
