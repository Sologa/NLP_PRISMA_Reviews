# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260409_probe_2409_gpt54_xhigh_stage1`
- model：`gpt-5.4`
- reasoning_effort：`xhigh`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 0 | 0.7451 | -0.0049 | 0.6333 | 0.9048 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 0 | 39 | 0 | 0.7451 | -0.0049 | 0.6333 | 0.9048 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 69 | `completed` | 60 | 9 | 0 |
| `stage2_review` | 0 | `None` | 0 | 0 | 0 |
