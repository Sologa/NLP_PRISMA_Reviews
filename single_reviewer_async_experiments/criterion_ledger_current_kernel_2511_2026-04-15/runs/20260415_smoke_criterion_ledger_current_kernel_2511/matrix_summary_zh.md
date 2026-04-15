# 2511.13936 Criterion Ledger Current-Kernel 摘要

- `paper_id`: `2511.13936`
- `workflow_arm`: `criterion_ledger_current_kernel`
- `total_cost`: `$0.0681`

## Metrics

| Scope | P | R | F1 | F2 | F3 | TP | FP | TN | FN | Auto coverage | Senior route rate | Senior overturn rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2 | 0 | 2 | 0 | 0.0000 | 1.0000 | 0.0000 |
| Combined | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2 | 0 | 2 | 0 | 0.0000 | 1.0000 | 0.0000 |

## Comparison

- current authority combined F1: `0.9062`
- current authority combined FN: `1`
- reference single-reviewer combined F1: `0.8824`
- delta vs current authority combined F1: `+0.0938`
- delta vs reference single-reviewer combined F1: `+0.1176`

## Cost

- `gpt-4.1-mini`: calls=6, input_tokens=38838, output_tokens=5116, cost=$0.0237
- `gpt-5-mini`: calls=4, input_tokens=23506, output_tokens=11273, cost=$0.0284
- `gpt-5-nano`: calls=6, input_tokens=38826, output_tokens=35104, cost=$0.0160

## Decision Note

可以保留這條 current-kernel 多 reviewer ledger 線作為候選，但前提是 senior route rate 和成本都還在可接受範圍。

