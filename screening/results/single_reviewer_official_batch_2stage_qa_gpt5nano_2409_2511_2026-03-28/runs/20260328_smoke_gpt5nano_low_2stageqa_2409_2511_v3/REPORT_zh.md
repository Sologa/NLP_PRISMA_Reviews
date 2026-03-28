# 單審查者官方 Batch 2-Stage QA

- `run_id`：`20260328_smoke_gpt5nano_low_2stageqa_2409_2511_v3`
- model：`gpt-5-nano`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 3 | 2 | 0 | 2 | 0 | 0.0000 | -0.7500 | 0.0000 | 0.0000 |
| `2511.13936` | 4 | 3 | 2 | 3 | 0 | 0.6667 | -0.2396 | 0.5000 | 1.0000 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_qa` | 5 | `completed` | 5 | 0 | 0 |
| `stage1_eval` | 5 | `completed` | 5 | 0 | 0 |
| `stage2_qa` | 2 | `completed` | 2 | 0 | 0 |
| `stage2_eval` | 2 | `completed` | 2 | 0 | 0 |
