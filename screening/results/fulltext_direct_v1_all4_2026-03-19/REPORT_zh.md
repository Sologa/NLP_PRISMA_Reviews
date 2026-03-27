# Fulltext-Direct cutoff-corrected baseline report

## Current-State Recap

- production runtime prompts：`scripts/screening/runtime_prompts/runtime_prompts.json`
- production criteria：`criteria_stage1/<paper_id>.json` / `criteria_stage2/<paper_id>.json`
- pre-review cutoff：`cutoff_jsons/<paper_id>.json`

## Metrics Summary

| Paper | Candidates | Reviewed | Direct F1 | Delta vs current combined | Cutoff excluded | Retrieval failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 192 | 0.8400 | -0.0713 | 29 | 0 |
| `2409.13738` | 84 | 65 | 0.8163 | +0.0663 | 15 | 0 |
| `2511.13936` | 89 | 52 | 0.9062 | +0.0000 | 11 | 0 |
| `2601.19926` | 360 | 354 | 0.9691 | -0.0041 | 0 | 0 |

## Baseline Authority

- `2307.05527` current authority：`latest fully benchmarked senior_no_marker`，Combined F1 = `0.9113`。
- `2409.13738` current authority：`stage_split_criteria_migration`，Combined F1 = `0.7500`。
- `2511.13936` current authority：`stage_split_criteria_migration`，Combined F1 = `0.9062`。
- `2601.19926` current authority：`latest fully benchmarked senior_no_marker`，Combined F1 = `0.9731`。

## Notes

- `cutoff_filtered` rows stay in the raw results for auditability but no longer count as reviewed.
