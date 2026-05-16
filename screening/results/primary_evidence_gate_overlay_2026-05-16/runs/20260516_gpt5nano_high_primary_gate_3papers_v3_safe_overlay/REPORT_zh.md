# Primary Evidence Gate Overlay Report

- run_id: `20260516_gpt5nano_high_primary_gate_3papers_v3_safe_overlay`
- model: `gpt-5-nano`
- reasoning_effort: `high`
- papers: `2409.13738, 2511.13936, 2601.19926`
- excluded paper: `2307.05527`
- gate inputs: `499`
- model exclusion suggestions: `34`
- gate exclusions: `29`
- suppressed model exclusions: `5`
- introduced false negatives by gold audit: `0`

## Validation

- expected input total: `499`
- observed input total: `499`
- contains 2307: `False`

## Role-review corrected overlay

- overall before: P=0.8884, R=0.9871, F1=0.9351 (tp=382, fp=48, tn=64, fn=5)
- overall after: P=0.9205, R=0.9871, F1=0.9526 (tp=382, fp=33, tn=79, fn=5)
- overall delta F1: `0.0175`

| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |
| --- | ---: | ---: | ---: | --- |
| `2409.13738` | 0.6774 | 0.7778 | 0.1004 | 21/12/32/0 |
| `2511.13936` | 0.8571 | 0.8571 | 0.0000 | 30/10/35/0 |
| `2601.19926` | 0.9664 | 0.9764 | 0.0100 | 331/11/12/5 |

## Direct-review comparator overlay

- overall before: P=0.9307, R=0.9716, F1=0.9507 (tp=376, fp=28, tn=117, fn=11)
- overall after: P=0.9447, R=0.9716, F1=0.9580 (tp=376, fp=22, tn=123, fn=11)
- overall delta F1: `0.0073`

| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |
| --- | ---: | ---: | ---: | --- |
| `2409.13738` | 0.8077 | 0.8400 | 0.0323 | 21/8/55/0 |
| `2511.13936` | 0.8657 | 0.8657 | 0.0000 | 29/8/50/1 |
| `2601.19926` | 0.9702 | 0.9760 | 0.0058 | 326/6/18/10 |

## Artifacts

- `primary_gate_results.json`
- `primary_gate_exclusions.json`
- `primary_gate_exclusion_gold_audit.json`
- `before_after_metrics.json`
- `validation_summary.json`
- `overlays/role_review_corrected/`
- `overlays/direct_review_comparator/`
