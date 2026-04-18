# Baseline Recheck

This report recomputes the current score-authority metrics from `screening/results/results_manifest.json` without writing to production paths.

State-drift note: the current manifest authority for `2409.13738` combined F1 is `0.7500`; older mentions of `0.8235` are treated as stale historical context.

| Paper | Stage | Authority path | Manifest F1 | Recomputed F1 | P | R | TP | FP | TN | FN | Matched | Status |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2307.05527 | stage1 | `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json` | 0.9621 | 0.9621 | 0.9593 | 0.9649 | 165 | 7 | 40 | 6 | 218 | ok |
| 2307.05527 | combined | `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json` | 0.9621 | 0.9621 | 0.9593 | 0.9649 | 165 | 7 | 40 | 6 | 218 | ok |
| 2409.13738 | stage1 | `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json` | 0.7500 | 0.7500 | 0.6000 | 1.0000 | 21 | 14 | 45 | 0 | 80 | ok |
| 2409.13738 | combined | `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json` | 0.7500 | 0.7500 | 0.6000 | 1.0000 | 21 | 14 | 45 | 0 | 80 | ok |
| 2511.13936 | stage1 | `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json` | 0.8788 | 0.8788 | 0.8056 | 0.9667 | 29 | 7 | 50 | 1 | 87 | ok |
| 2511.13936 | combined | `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json` | 0.9062 | 0.9062 | 0.8529 | 0.9667 | 29 | 5 | 52 | 1 | 87 | ok |
| 2601.19926 | stage1 | `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json` | 0.9792 | 0.9792 | 0.9735 | 0.9851 | 330 | 9 | 14 | 5 | 358 | ok |
| 2601.19926 | combined | `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json` | 0.9731 | 0.9731 | 0.9731 | 0.9731 | 326 | 9 | 14 | 9 | 358 | ok |

Interpretation:

- This is a reproducibility check of existing authority artifacts, not a BCPCS performance result.
- Missing `gold_only` records are handled the same way as the repo evaluator: metrics are computed on matched keys.
- No production files were modified.
