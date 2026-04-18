# 2409 Paper-Faithful A 比較表

- `current authority stage1`: P=0.6000, R=1.0000, F1=0.7500, FN=0
- `single reviewer stage1 baseline`: P=0.5833, R=1.0000, F1=0.7368, FN=0

| Family | Strategy | MAP | WSS@95 | L_Rel | F1@current_k | FN@current_k | Delta vs current | F1@single_k | Delta vs single | Oracle F1 | Oracle k |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `adjudication` | `adj_judge` | 1.0000 | 0.7000 | 1 | 0.4000 | 0 | -0.3500 | 0.4000 | -0.3368 | 1.0000 | 1 |
| `adjudication` | `adj_rank` | 0.3333 | 0.2000 | 3 | 0.4000 | 0 | -0.3500 | 0.4000 | -0.3368 | 0.5000 | 3 |
| `mad` | `mad_raw` | 1.0000 | 0.7000 | 1 | 0.4000 | 0 | -0.3500 | 0.4000 | -0.3368 | 1.0000 | 1 |
| `mad` | `mad_soft_vote` | 1.0000 | 0.7000 | 1 | 0.4000 | 0 | -0.3500 | 0.4000 | -0.3368 | 1.0000 | 1 |
| `soft_vote` | `soft_vote` | 1.0000 | 0.7000 | 1 | 0.4000 | 0 | -0.3500 | 0.4000 | -0.3368 | 1.0000 | 1 |

