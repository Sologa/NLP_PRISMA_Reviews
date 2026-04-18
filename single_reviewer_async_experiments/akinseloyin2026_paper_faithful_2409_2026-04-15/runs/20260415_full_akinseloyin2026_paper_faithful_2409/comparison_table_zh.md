# 2409 Paper-Faithful A 比較表

- `current authority stage1`: P=0.6000, R=1.0000, F1=0.7500, FN=0
- `single reviewer stage1 baseline`: P=0.5833, R=1.0000, F1=0.7368, FN=0

| Family | Strategy | MAP | WSS@95 | L_Rel | F1@current_k | FN@current_k | Delta vs current | F1@single_k | Delta vs single | Oracle F1 | Oracle k |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `adjudication` | `adj_judge` | 0.4191 | 0.4572 | 36 | 0.7143 | 1 | -0.0357 | 0.7368 | +0.0000 | 0.7368 | 36 |
| `adjudication` | `adj_rank` | 0.4179 | 0.4428 | 36 | 0.7143 | 1 | -0.0357 | 0.7368 | +0.0000 | 0.7368 | 36 |
| `mad` | `mad_raw` | 0.4458 | 0.4717 | 35 | 0.7500 | 0 | +0.0000 | 0.7368 | +0.0000 | 0.7500 | 35 |
| `mad` | `mad_soft_vote` | 0.4215 | 0.4572 | 35 | 0.7500 | 0 | +0.0000 | 0.7368 | +0.0000 | 0.7500 | 35 |
| `soft_vote` | `soft_vote` | 0.4344 | 0.4572 | 36 | 0.7143 | 1 | -0.0357 | 0.7368 | +0.0000 | 0.7368 | 36 |

