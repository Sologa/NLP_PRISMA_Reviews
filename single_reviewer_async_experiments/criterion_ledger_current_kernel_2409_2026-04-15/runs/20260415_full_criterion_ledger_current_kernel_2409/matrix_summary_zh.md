# 2409 Criterion Ledger Current-Kernel 摘要

- `paper_id`: `2409.13738`
- `workflow_arm`: `criterion_ledger_current_kernel`
- `total_cost`: `$1.0235`

## Metrics

| Scope | P | R | F1 | F2 | F3 | TP | FP | TN | FN | Auto coverage | Senior route rate | Senior overturn rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage1 | 0.6562 | 1.0000 | 0.7925 | 0.9052 | 0.9502 | 21 | 11 | 52 | 0 | 0.3478 | 0.6522 | 0.0444 |
| Combined | 0.8077 | 1.0000 | 0.8936 | 0.9545 | 0.9767 | 21 | 5 | 58 | 0 | 0.3333 | 0.6667 | 0.0392 |

## Comparison

- current authority combined F1: `0.7500`
- current authority combined FN: `0`
- reference single-reviewer combined F1: `0.8936`
- delta vs current authority combined F1: `+0.1436`
- delta vs reference single-reviewer combined F1: `+0.0000`

## Cost

- `gpt-4.1-mini`: calls=101, input_tokens=591881, output_tokens=86054, cost=$0.3744
- `gpt-5-mini`: calls=51, input_tokens=340976, output_tokens=133614, cost=$0.3525
- `gpt-5-nano`: calls=101, input_tokens=591679, output_tokens=667501, cost=$0.2966

## Decision Note

可以考慮擴到 2511，但前提是 senior route rate 和成本都還在可接受範圍。

