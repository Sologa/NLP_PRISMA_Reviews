# Primary Evidence Gate Overlay Report

- run_id: `20260516_gpt5nano_high_primary_gate_3papers_v2`
- model: `gpt-5-nano`
- reasoning_effort: `high`
- papers: `2409.13738, 2511.13936, 2601.19926`
- excluded paper: `2307.05527`
- gate inputs: `499`
- gate exclusions: `34`
- introduced false negatives by gold audit: `1`

## Validation

- expected input total: `499`
- observed input total: `499`
- contains 2307: `False`

## Role-review corrected overlay

- overall before: P=0.8884, R=0.9871, F1=0.9351 (tp=382, fp=48, tn=64, fn=5)
- overall after: P=0.9248, R=0.9845, F1=0.9537 (tp=381, fp=31, tn=81, fn=6)
- overall delta F1: `0.0186`

| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |
| --- | ---: | ---: | ---: | --- |
| `2409.13738` | 0.6774 | 0.7692 | 0.0918 | 20/11/33/1 |
| `2511.13936` | 0.8571 | 0.8571 | 0.0000 | 30/10/35/0 |
| `2601.19926` | 0.9664 | 0.9778 | 0.0114 | 331/10/13/5 |

## Direct-review comparator overlay

- overall before: P=0.9307, R=0.9716, F1=0.9507 (tp=376, fp=28, tn=117, fn=11)
- overall after: P=0.9470, R=0.9690, F1=0.9579 (tp=375, fp=21, tn=124, fn=12)
- overall delta F1: `0.0072`

| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |
| --- | ---: | ---: | ---: | --- |
| `2409.13738` | 0.8077 | 0.8333 | 0.0256 | 20/7/56/1 |
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
