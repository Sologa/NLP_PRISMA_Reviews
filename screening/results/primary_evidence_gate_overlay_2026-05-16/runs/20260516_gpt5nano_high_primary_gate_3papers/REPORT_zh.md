# Primary Evidence Gate Overlay Report

- run_id: `20260516_gpt5nano_high_primary_gate_3papers`
- model: `gpt-5-nano`
- reasoning_effort: `high`
- papers: `2409.13738, 2511.13936, 2601.19926`
- excluded paper: `2307.05527`
- gate inputs: `499`
- gate exclusions: `41`

## Validation

- expected input total: `499`
- observed input total: `499`
- contains 2307: `False`

## Role-review corrected overlay

- overall before: P=0.8884, R=0.9871, F1=0.9351 (tp=382, fp=48, tn=64, fn=5)
- overall after: P=0.9261, R=0.9716, F1=0.9483 (tp=376, fp=30, tn=82, fn=11)
- overall delta F1: `0.0132`

| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |
| --- | ---: | ---: | ---: | --- |
| `2409.13738` | 0.6774 | 0.7925 | 0.1150 | 21/11/33/0 |
| `2511.13936` | 0.8571 | 0.8571 | 0.0000 | 30/10/35/0 |
| `2601.19926` | 0.9664 | 0.9701 | 0.0037 | 325/9/14/11 |

## Direct-review comparator overlay

- overall before: P=0.9307, R=0.9716, F1=0.9507 (tp=376, fp=28, tn=117, fn=11)
- overall after: P=0.9487, R=0.9561, F1=0.9524 (tp=370, fp=20, tn=125, fn=17)
- overall delta F1: `0.0017`

| Paper | Before F1 | After F1 | Delta F1 | TP/FP/TN/FN after |
| --- | ---: | ---: | ---: | --- |
| `2409.13738` | 0.8077 | 0.8571 | 0.0495 | 21/7/56/0 |
| `2511.13936` | 0.8657 | 0.8657 | 0.0000 | 29/8/50/1 |
| `2601.19926` | 0.9702 | 0.9682 | -0.0020 | 320/5/19/16 |

## Artifacts

- `primary_gate_results.json`
- `primary_gate_exclusions.json`
- `before_after_metrics.json`
- `validation_summary.json`
- `overlays/role_review_corrected/`
- `overlays/direct_review_comparator/`
