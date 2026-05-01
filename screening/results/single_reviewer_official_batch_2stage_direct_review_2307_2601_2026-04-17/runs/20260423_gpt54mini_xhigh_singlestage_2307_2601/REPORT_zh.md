# 單審查者官方 Batch single-stage 直審基線

- `run_id`：`20260423_gpt54mini_xhigh_singlestage_2307_2601`
- model：`gpt-5.4-mini`
- reasoning_effort：`xhigh`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

- 此 run 為 single-stage direct-review；沒有 stage1 batch，也不計 stage1 指標。

## Final 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 214 | 208 | 208 | 0 | 0.8959 | -0.0662 | 0.9726 | 0.8304 |
| `2601.19926` | 360 | 360 | 359 | 359 | 0 | 0.9308 | -0.0423 | 0.9867 | 0.8810 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 0 | `None` | 0 | 0 | 0 |
| `stage2_review` | 567 | `completed` | 567 | 0 | 0 |
