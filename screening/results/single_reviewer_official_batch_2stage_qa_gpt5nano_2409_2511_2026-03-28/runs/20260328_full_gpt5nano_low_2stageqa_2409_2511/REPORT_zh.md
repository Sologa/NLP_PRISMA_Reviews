# 單審查者官方 Batch 2-Stage QA

- `run_id`：`20260328_full_gpt5nano_low_2stageqa_2409_2511`
- model：`gpt-5-nano`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 35 | 60 | 0 | 0.7037 | -0.0463 | 0.5758 | 0.9048 |
| `2511.13936` | 88 | 77 | 50 | 73 | 0 | 0.6970 | -0.2093 | 0.6389 | 0.7667 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_qa` | 146 | `completed` | 142 | 4 | 0 |
| `stage1_eval` | 142 | `completed` | 142 | 0 | 0 |
| `stage2_qa` | 85 | `completed` | 76 | 9 | 0 |
| `stage2_eval` | 76 | `completed` | 76 | 0 | 0 |
