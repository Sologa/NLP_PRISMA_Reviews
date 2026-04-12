# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260408_full_gpt54mini_low_2stagedirect_2409_2511`
- model：`gpt-5.4-mini`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 23 | 0.7727 | +0.0227 | 0.7391 | 0.8095 |
| `2511.13936` | 88 | 77 | 22 | 0.8077 | -0.0711 | 0.9545 | 0.7000 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 23 | 69 | 0 | 0.8095 | +0.0595 | 0.8095 | 0.8095 |
| `2511.13936` | 88 | 77 | 22 | 77 | 0 | 0.8077 | -0.0986 | 0.9545 | 0.7000 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 146 | `completed` | 146 | 0 | 0 |
| `stage2_review` | 45 | `completed` | 45 | 0 | 0 |
