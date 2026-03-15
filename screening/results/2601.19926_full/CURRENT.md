# CURRENT: 2601.19926

This file identifies the current authoritative score sources for `2601.19926`.

## Current score authority

Current stable reference remains the latest fully benchmarked `senior_no_marker` reports:

- Stage 1: `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json`

Current metrics:

- Stage 1 F1: `0.9792`
- Combined F1: `0.9733`

## Why these files are current

`2601` has stage-split criteria files in the current repo structure, but there is not yet a same-level stage-split migration rerun that supersedes the latest fully benchmarked `senior_no_marker` reports.

Therefore, current stable reference remains the `senior_no_marker` benchmark outputs above.

## Historical baselines in this directory

These are historical comparison artifacts, not the current score authority:

- `review_after_stage1_prompt_only_v1_report.json`
- `combined_after_fulltext_report.json`
- `stage1_recall_redesign_report.json`
- `combined_recall_redesign_report.json`
- `review_after_stage1_senior_adjudication_v1_report.json`
- `combined_after_fulltext_senior_adjudication_v1_report.json`
- `review_after_stage1_senior_prompt_tuned_report.json`
- `combined_after_fulltext_senior_prompt_tuned_report.json`
- all `latte_review_results.*.json` and `latte_fulltext_review_results.*.json` historical raw files

## Do-not-confuse notes

- Do not describe `criteria_jsons/2601.19926.json` as the current active criteria.
- Do not assume `2601` should follow stricter global senior behavior learned from `2409`.
- For current answer generation, use the two authoritative report files listed at the top of this file.
