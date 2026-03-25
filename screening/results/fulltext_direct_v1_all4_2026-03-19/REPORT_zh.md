# Fulltext-Direct cutoff-corrected baseline report

## Current-State Recap

- production runtime prompts：`scripts/screening/runtime_prompts/runtime_prompts.json`
- production criteria：`criteria_stage1/<paper_id>.json` / `criteria_stage2/<paper_id>.json`
- pre-review cutoff：`cutoff_jsons/<paper_id>.json`

## Metrics Summary

| Paper | Candidates | Reviewed | Direct F1 | Delta vs current combined | Cutoff excluded | Retrieval failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 222 | 192 | 0.8400 | -0.0657 | 30 | 0 |
| `2409.13738` | 84 | 65 | 0.8163 | -0.0072 | 19 | 0 |
| `2511.13936` | 89 | 52 | 0.7547 | -0.0145 | 37 | 0 |
| `2601.19926` | 360 | 354 | 0.9674 | -0.0026 | 6 | 0 |

## Baseline Authority

- `2307.05527` current authority：`latest fully benchmarked senior_no_marker`，Combined F1 = `0.9057`。
- `2409.13738` current authority：`stage_split_criteria_migration`，Combined F1 = `0.8235`。
- `2511.13936` current authority：`stage_split_criteria_migration`，Combined F1 = `0.7692`。
- `2601.19926` current authority：`latest fully benchmarked senior_no_marker`，Combined F1 = `0.9700`。

## Notes

- `cutoff_filtered` rows stay in the raw results for auditability but no longer count as reviewed.
