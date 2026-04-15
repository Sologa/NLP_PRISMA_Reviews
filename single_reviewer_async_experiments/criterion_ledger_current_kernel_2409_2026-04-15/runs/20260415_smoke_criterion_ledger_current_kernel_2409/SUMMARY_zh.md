# 2409 Criterion Ledger Current-Kernel 摘要

- `paper_id`: `2409.13738`
- `workflow_arm`: `criterion_ledger_current_kernel`
- `total_cost`: `$0.0478`

## Metrics

| Scope | P | R | F1 | F2 | F3 | TP | FP | TN | FN | Auto coverage | Senior route rate | Senior overturn rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage1 | 0.5000 | 1.0000 | 0.6667 | 0.8333 | 0.9091 | 1 | 1 | 1 | 0 | 0.6667 | 0.3333 | 0.0000 |
| Combined | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1 | 0 | 2 | 0 | 0.3333 | 0.6667 | 0.0000 |

## Comparison

- current authority combined F1: `0.7500`
- current authority combined FN: `0`
- reference single-reviewer combined F1: `0.8936`
- delta vs current authority combined F1: `+0.2500`
- delta vs reference single-reviewer combined F1: `+0.1064`

## Cost

- `gpt-4.1-mini`: calls=5, input_tokens=27248, output_tokens=4134, cost=$0.0175
- `gpt-5-mini`: calls=2, input_tokens=17220, output_tokens=5355, cost=$0.0150
- `gpt-5-nano`: calls=5, input_tokens=27238, output_tokens=34825, cost=$0.0153

## Decision Note

可以考慮擴到 2511，但前提是 senior route rate 和成本都還在可接受範圍。

