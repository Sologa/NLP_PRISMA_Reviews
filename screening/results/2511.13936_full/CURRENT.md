# CURRENT: 2511.13936

This file identifies the current authoritative score sources for `2511.13936`.

## Current score authority

Current active score authority is the stage-split criteria migration metrics:

- Stage 1: `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
- Combined: `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`

Current metrics:

- Stage 1 F1: `0.8657`
- Combined F1: `0.8814`

## Provenance

Current runtime uses:

- Stage 1 criteria: `criteria_stage1/2511.13936.json`
- Stage 2 criteria: `criteria_stage2/2511.13936.json`

These stage-split criteria replaced the older single-file operational-v2 phase as the current architecture.

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
- `review_after_stage1_criteria_2511_opv2_report.json`
- `combined_after_fulltext_criteria_2511_opv2_report.json`
- all `latte_review_results.*.json` and `latte_fulltext_review_results.*.json` raw historical outputs

## Important naming caveat

The files:

- `latte_review_results.criteria_2511_opv2.json`
- `latte_fulltext_review_results.criteria_2511_opv2.json`

represent the historical operational-v2 experiment. They are not the current score authority.

Current active score authority is the migration metrics files listed at the top of this file.

## Do-not-confuse notes

- Do not describe `criteria_jsons/2511.13936.json` as the current active criteria.
- Do not use `criteria_2511_opv2` report scores as the current score.
- Performance in the old operational-v2 phase may be better, but it was methodologically rejected because of unacceptable criteria hardening.
