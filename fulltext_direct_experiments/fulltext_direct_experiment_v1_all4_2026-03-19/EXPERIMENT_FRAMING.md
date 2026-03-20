# Fulltext-Direct / Stage2-Direct Non-QA Baseline

This bundle defines an experiment-only baseline for four papers:

- `2307.05527`
- `2409.13738`
- `2511.13936`
- `2601.19926`

## What This Is

- one-stage full-text review
- direct use of `criteria_stage2/<paper_id>.json`
- two junior reviewers plus `SeniorLead` adjudication on mixed cases
- no Stage 1 routing
- no QA
- no synthesis
- no seed-QA patching

## What This Is Not

- not a production replacement
- not a criteria rewrite
- not a runtime prompt rewrite
- not a QA-first variant

## Current-State Constraints

- Production runtime prompt authority stays:
  - `scripts/screening/runtime_prompts/runtime_prompts.json`
- Production criteria authority stays:
  - `criteria_stage1/<paper_id>.json`
  - `criteria_stage2/<paper_id>.json`
- Current score authority stays:
  - `2307.05527`: latest fully benchmarked `senior_no_marker`
  - `2409.13738`: `stage_split_criteria_migration`
  - `2511.13936`: `stage_split_criteria_migration`
  - `2601.19926`: latest fully benchmarked `senior_no_marker`

## Implementation Notes

- Candidate source must be `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`, not `screening/data/*_full/arxiv_metadata.full.json`.
- AppleDouble files `refs/*/mds/._*.md` must be ignored.
- `2601.19926` requires normalized filename fallback because exact `<key>.md` misses 29 keys that resolve cleanly after normalization.
