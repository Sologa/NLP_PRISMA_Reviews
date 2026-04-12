# 單審查者官方 Batch Merged 2-Stage QA+Criteria

- `run_id`：`20260329_offline_contract_probe_merged2stage_2409_2511`
- model：`gpt-5-nano`
- reasoning_effort：`offline_probe`
- endpoint：`/v1/chat/completions`

## 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 3 | 3 | 2 | 3 | 0 | 0.6667 | -0.0833 | 0.5000 | 1.0000 |
| `2511.13936` | 4 | 4 | 3 | 4 | 0 | 0.0000 | -0.9062 | 0.0000 | 0.0000 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 0 | `offline_probe` | 0 | 0 | 0 |
| `stage2_review` | 0 | `offline_probe` | 0 | 0 | 0 |
