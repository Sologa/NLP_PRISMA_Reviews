# CURRENT: 2409.13738

This file identifies the current authoritative score sources for `2409.13738`.

## Current score authority

Current active score authority is the stage-split criteria migration metrics:

- Stage 1: `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
- Combined: `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`

Current metrics:

- Stage 1 F1: `0.7500`
- Combined F1: `0.7843`

## Provenance

Current runtime uses:

- Stage 1 criteria: `criteria_stage1/2409.13738.json`
- Stage 2 criteria: `criteria_stage2/2409.13738.json`

This means the old single-file criteria history and older reports are no longer the current score basis.

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
- all `latte_review_results.*.json` and `latte_fulltext_review_results.*.json` raw historical outputs

## Important naming caveat

The files:

- `latte_review_results.criteria_2409_stage_split.json`
- `latte_fulltext_review_results.criteria_2409_stage_split.json`

look close to the current story, but they are still historical experiment artifacts from the older `criteria_2409_stage_split` phase.

Current active score authority is not those files. It is the migration metrics files listed at the top of this file.

## Do-not-confuse notes

- Do not describe `criteria_jsons/2409.13738.json` as the current active criteria.
- Do not use `criteria_2409_stage_split` report scores as the current score.
- Do not describe `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md` as adopted current architecture.
