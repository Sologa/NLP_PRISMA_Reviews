# 2511.13936 Criterion Ledger Current-Kernel 摘要

- `paper_id`: `2511.13936`
- `workflow_arm`: `criterion_ledger_current_kernel`
- `total_cost`: `$1.2886`

## Metrics

| Scope | P | R | F1 | F2 | F3 | TP | FP | TN | FN | Auto coverage | Senior route rate | Senior overturn rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage1 | 0.8485 | 0.9333 | 0.8889 | 0.9150 | 0.9241 | 28 | 5 | 53 | 2 | 0.0260 | 0.9740 | 0.0133 |
| Combined | 0.9310 | 0.9000 | 0.9153 | 0.9060 | 0.9030 | 27 | 2 | 56 | 3 | 0.0260 | 0.9740 | 0.0125 |

## Comparison

- current authority combined F1: `0.9062`
- current authority combined FN: `1`
- reference single-reviewer combined F1: `0.8824`
- delta vs current authority combined F1: `+0.0090`
- delta vs reference single-reviewer combined F1: `+0.0329`

## Cost

- `gpt-4.1-mini`: calls=110, input_tokens=663701, output_tokens=96884, cost=$0.4205
- `gpt-5-mini`: calls=80, input_tokens=524356, output_tokens=206522, cost=$0.5441
- `gpt-5-nano`: calls=110, input_tokens=663481, output_tokens=726878, cost=$0.3239

## Decision Note

不建議把這條 current-kernel 多 reviewer ledger 線當成下一步主線。它把 FN 拉高了，先不符合這輪 acceptance。

