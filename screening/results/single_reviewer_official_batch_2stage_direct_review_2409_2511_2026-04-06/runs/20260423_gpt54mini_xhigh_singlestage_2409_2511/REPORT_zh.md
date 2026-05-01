# 單審查者官方 Batch single-stage 直審基線

- `run_id`：`20260423_gpt54mini_xhigh_singlestage_2409_2511`
- model：`gpt-5.4-mini`
- reasoning_effort：`xhigh`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

- 此 run 為 single-stage direct-review；沒有 stage1 batch，也不計 stage1 指標。

## Final 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | 84 | 69 | 65 | 65 | 0 | 0.9130 | +0.1630 | 0.8400 | 1.0000 |
| `2511.13936` | 88 | 77 | 75 | 75 | 0 | 0.8814 | -0.0249 | 0.8966 | 0.8667 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 0 | `None` | 0 | 0 | 0 |
| `stage2_review` | 140 | `completed` | 140 | 0 | 0 |
