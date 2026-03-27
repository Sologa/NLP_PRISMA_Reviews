# NLP PRISMA Screening: Canonical Current Status Handoff

Date: 2026-03-27
Status: authoritative current-state handoff

Use this file with:

- `AGENTS.md`
- `screening/results/results_manifest.json`

Do not infer current state from older reports before reading this file.

## Runtime authority

- Runtime prompts: `scripts/screening/runtime_prompts/runtime_prompts.json`
- Stage 1 criteria: `criteria_stage1/<paper_id>.json`
- Stage 2 criteria: `criteria_stage2/<paper_id>.json`
- Pre-review cutoff: `cutoff_jsons/<paper_id>.json`

## Current metrics table

| Paper | Stage 1 authority | Combined authority | Stage 1 F1 | Combined F1 | Cutoff excluded |
| --- | --- | --- | ---: | ---: | ---: |
| `2307.05527` | `review_after_stage1_senior_no_marker_report.json` | `combined_after_fulltext_senior_no_marker_report.json` | `0.9621` | `0.9621` | `8` |
| `2409.13738` | `stage1_f1.stage_split_criteria_migration.json` | `combined_f1.stage_split_criteria_migration.json` | `0.7500` | `0.7500` | `15` |
| `2511.13936` | `stage1_f1.stage_split_criteria_migration.json` | `combined_f1.stage_split_criteria_migration.json` | `0.8788` | `0.9062` | `11` |
| `2601.19926` | `review_after_stage1_senior_no_marker_report.json` | `combined_after_fulltext_senior_no_marker_report.json` | `0.9792` | `0.9731` | `0` |

## Workflow invariants

- Cutoff is applied before reviewer routing; cutoff-failed rows are authoritative `exclude (cutoff_time_window)` outputs.
- Stage 1 routing remains: double-high include, double-low exclude, otherwise `SeniorLead`.
- `SeniorLead` remains mandatory once invoked.

## Current score authority by paper

### `2307.05527`

- Stage 1: `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json`
- Cutoff policy: `cutoff_jsons/2307.05527.json`
- Cutoff-excluded candidates: `8`

### `2409.13738`

- Stage 1: `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
- Combined: `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
- Cutoff policy: `cutoff_jsons/2409.13738.json`
- Cutoff-excluded candidates: `15`

### `2511.13936`

- Stage 1: `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
- Combined: `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
- Cutoff policy: `cutoff_jsons/2511.13936.json`
- Cutoff-excluded candidates: `11`

### `2601.19926`

- Stage 1: `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json`
- Cutoff policy: `cutoff_jsons/2601.19926.json`
- Cutoff-excluded candidates: `0`

## Read order reminder

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. the relevant `screening/results/<paper>_full/CURRENT.md`
