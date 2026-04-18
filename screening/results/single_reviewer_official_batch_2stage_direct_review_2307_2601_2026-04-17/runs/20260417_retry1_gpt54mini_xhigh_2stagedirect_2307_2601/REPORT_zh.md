# 單審查者官方 Batch 兩階段直審基線

- `run_id`：`20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601`
- model：`gpt-5.4-mini`
- reasoning_effort：`xhigh`
- endpoint：`/v1/chat/completions`

## Stage 1 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Stage1 F1 | Delta vs current stage1 | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 214 | 148 | 0.9028 | -0.0593 | 0.9730 | 0.8421 |
| `2601.19926` | 360 | 360 | 283 | 0.8918 | -0.0875 | 0.9753 | 0.8214 |

## Combined 指標

| Paper | Candidates | Cutoff pass | Stage2 selected | Reviewed | Missing | F1 | Delta vs current combined | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 214 | 148 | 210 | 0 | 0.8673 | -0.0948 | 0.9710 | 0.7836 |
| `2601.19926` | 360 | 360 | 283 | 359 | 0 | 0.8742 | -0.0990 | 0.9851 | 0.7857 |

## Phase Jobs

| Phase | Request count | Batch status | Success | Failure | Missing |
| --- | ---: | --- | ---: | ---: | ---: |
| `stage1_review` | 569 | `completed` | 569 | 0 | 0 |
| `stage2_review` | 431 | `completed` | 431 | 0 | 0 |
