# CURRENT: 2409.13738

This file identifies the current authoritative score sources for `2409.13738`.

## Current score authority

Current active score authority is the stage-split criteria migration metrics:

- Stage 1: `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
- Combined: `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`

Current metrics:

- Stage 1 F1: `0.7500`
- Combined F1: `0.7500`

## Cutoff-first policy

- Mandatory pre-review cutoff: `cutoff_jsons/2409.13738.json`
- Cutoff-excluded candidates: `15`
- Cutoff-failed rows are now forced to `exclude (cutoff_time_window)` before reviewer routing is treated as authoritative.

## Provenance

Current runtime uses:

- Stage 1 criteria: `criteria_stage1/2409.13738.json`
- Stage 2 criteria: `criteria_stage2/2409.13738.json`

## Historical baselines in this directory

These remain useful for comparison, but they are not the current score authority:
- `review_after_stage1_prompt_only_v1_report.json`
- `combined_after_fulltext_report.json`
- `stage1_recall_redesign_report.json`
- `combined_recall_redesign_report.json`
- `review_after_stage1_senior_adjudication_v1_report.json`
- `combined_after_fulltext_senior_adjudication_v1_report.json`
- `review_after_stage1_senior_no_marker_report.json`
- `combined_after_fulltext_senior_no_marker_report.json`
- `review_after_stage1_senior_prompt_tuned_report.json`
- `combined_after_fulltext_senior_prompt_tuned_report.json`
- `review_after_stage1_criteria_2409_stage_split_report.json`
- `combined_after_fulltext_criteria_2409_stage_split_report.json`
- raw historical `latte_review_results*.json` and `latte_fulltext_review_results*.json` outputs

## Do-not-confuse notes

- Do not describe `criteria_jsons/*.json` as current production criteria.
- Do not reuse pre-cutoff metrics as current score authority.
- Read `AGENTS.md`, `docs/chatgpt_current_status_handoff.md`, and `screening/results/results_manifest.json` first.
