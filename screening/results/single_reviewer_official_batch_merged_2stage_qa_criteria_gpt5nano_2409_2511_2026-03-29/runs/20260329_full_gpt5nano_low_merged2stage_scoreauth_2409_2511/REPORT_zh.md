# 單審查者官方 Batch Merged 2-Stage QA+Criteria

- `run_id`：`20260329_full_gpt5nano_low_merged2stage_scoreauth_2409_2511`
- model：`gpt-5-nano`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 48 | 69 | 0 | 0.8571 | +0.1071 | 0.7500 | 1.0000 |
| `2511.13936` | 88 | 77 | 53 | 77 | 0 | 0.8116 | -0.0947 | 0.7179 | 0.9333 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 146 | `completed` | 146 | 0 | 0 |
| `stage2_review` | 101 | `completed` | 101 | 0 | 0 |
