# Screening Results

Read order for current state:

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. the relevant per-paper `CURRENT.md`

## Current authority table

| Paper | Current authority | Stage 1 path | Combined path | Stage 1 F1 | Combined F1 | Cutoff excluded |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `2307.05527` | `latest_fully_benchmarked_senior_no_marker` | `review_after_stage1_senior_no_marker_report.json` | `combined_after_fulltext_senior_no_marker_report.json` | 0.9113 | 0.9057 | 30 |
| `2409.13738` | `current_stage_split` | `stage1_f1.stage_split_criteria_migration.json` | `combined_f1.stage_split_criteria_migration.json` | 0.7500 | 0.8235 | 19 |
| `2511.13936` | `current_stage_split` | `stage1_f1.stage_split_criteria_migration.json` | `combined_f1.stage_split_criteria_migration.json` | 0.7407 | 0.7692 | 37 |
| `2601.19926` | `latest_fully_benchmarked_senior_no_marker` | `review_after_stage1_senior_no_marker_report.json` | `combined_after_fulltext_senior_no_marker_report.json` | 0.9761 | 0.9700 | 6 |

## Current runtime invariants

- Runtime prompts: `scripts/screening/runtime_prompts/runtime_prompts.json`
- Criteria authority: `criteria_stage1/<paper_id>.json` and `criteria_stage2/<paper_id>.json`
- Cutoff authority: `cutoff_jsons/<paper_id>.json` is a mandatory pre-review hard filter for repo-managed papers
