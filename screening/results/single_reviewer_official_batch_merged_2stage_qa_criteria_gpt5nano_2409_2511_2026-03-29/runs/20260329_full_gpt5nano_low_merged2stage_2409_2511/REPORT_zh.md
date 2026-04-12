# 單審查者官方 Batch Merged 2-Stage QA+Criteria

- `run_id`：`20260329_full_gpt5nano_low_merged2stage_2409_2511`
- model：`gpt-5-nano`
- reasoning_effort：`low`
- endpoint：`/v1/chat/completions`

## 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 47 | 69 | 0 | 0.8750 | +0.1250 | 0.7778 | 1.0000 |
| `2511.13936` | 88 | 77 | 52 | 75 | 0 | 0.7143 | -0.1920 | 0.6250 | 0.8333 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 146 | `completed` | 144 | 2 | 0 |
| `stage2_review` | 99 | `completed` | 99 | 0 | 0 |
