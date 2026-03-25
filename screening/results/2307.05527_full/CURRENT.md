# CURRENT: 2307.05527

This file identifies the current authoritative score sources for `2307.05527`.

## Current score authority

Current stable reference score authority remains the latest fully benchmarked senior_no_marker metrics:

- Stage 1: `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json`

Current metrics:

- Stage 1 F1: `0.9113`
- Combined F1: `0.9057`

## Cutoff-first policy

- Mandatory pre-review cutoff: `cutoff_jsons/2307.05527.json`
- Cutoff-excluded candidates: `30`
- Cutoff-failed rows are now forced to `exclude (cutoff_time_window)` before reviewer routing is treated as authoritative.

## Provenance

Current runtime uses:

- Stage 1 criteria: `criteria_stage1/2307.05527.json`
- Stage 2 criteria: `criteria_stage2/2307.05527.json`

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
- raw historical `latte_review_results*.json` and `latte_fulltext_review_results*.json` outputs

## Do-not-confuse notes

- Do not describe `criteria_jsons/*.json` as current production criteria.
- Do not reuse pre-cutoff metrics as current score authority.
- Read `AGENTS.md`, `docs/chatgpt_current_status_handoff.md`, and `screening/results/results_manifest.json` first.
