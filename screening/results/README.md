# Screening Results Index

This directory contains both current and historical screening artifacts.

Do not infer current score authority from raw filenames alone. Use:

1. `screening/results/results_manifest.json`
2. the relevant per-paper `CURRENT.md`
3. only then, individual historical raw files and reports

## 1. Directory semantics

### Full review benchmark directories

These contain the main per-paper benchmark history:

- `2307.05527_full/`
- `2409.13738_full/`
- `2511.13936_full/`
- `2601.19926_full/`

Each of these directories contains:

- raw reviewer outputs
- full-text outputs
- stage-level reports
- multiple historical experimental baselines
- one `CURRENT.md` file that identifies the current score authority for that paper

### Replay / comparison / support directories

These are not per-paper current production result roots.

- `runtime_prompt_externalization/`
- `source_faithful_vs_operational_2409_2511/`
- `source_faithful_vs_operational_2409_2511_runA/`
- `<paper>_full/frozen_senior_replay/`

Treat these as supporting experiment artifacts.

### Smoke / subset directories

These are not authoritative current production score directories.

- `2409.13738_smoke3/`
- `2511.13936_top5/`
- `cads_smoke5/`

## 2. Current score authority by paper

| Paper | Current score authority | Stage 1 file | Combined file |
| --- | --- | --- | --- |
| `2307.05527` | latest fully benchmarked `senior_no_marker` | `2307.05527_full/review_after_stage1_senior_no_marker_report.json` | `2307.05527_full/combined_after_fulltext_senior_no_marker_report.json` |
| `2409.13738` | `stage_split_criteria_migration` | `2409.13738_full/stage1_f1.stage_split_criteria_migration.json` | `2409.13738_full/combined_f1.stage_split_criteria_migration.json` |
| `2511.13936` | `stage_split_criteria_migration` | `2511.13936_full/stage1_f1.stage_split_criteria_migration.json` | `2511.13936_full/combined_f1.stage_split_criteria_migration.json` |
| `2601.19926` | latest fully benchmarked `senior_no_marker` | `2601.19926_full/review_after_stage1_senior_no_marker_report.json` | `2601.19926_full/combined_after_fulltext_senior_no_marker_report.json` |

## 3. Current vs historical naming rules

### `2409` and `2511`

For these two papers, current state is defined by the stage-split criteria migration metrics files.

This means the following are historical baselines, not current score authority:

- `review_after_stage1_criteria_2409_stage_split_report.json`
- `combined_after_fulltext_criteria_2409_stage_split_report.json`
- `review_after_stage1_criteria_2511_opv2_report.json`
- `combined_after_fulltext_criteria_2511_opv2_report.json`
- any `latte_review_results.*.json` or `latte_fulltext_review_results.*.json` from older named baselines

### `2307` and `2601`

These two papers currently use the latest fully benchmarked `senior_no_marker` reports as the stable current reference.

This is because there is not yet a same-level stage-split migration rerun that supersedes those stable benchmark reports.

## 4. How to find the current answer quickly

If a new conversation asks, "what is the current score for paper X?", do this:

1. open `results_manifest.json`
2. open `<paper>_full/CURRENT.md`
3. use the exact authoritative metric file paths listed there

Do not scan the directory and guess.

## 5. Why this index exists

Many directories intentionally keep older raw and report files for comparison. That is useful for experimental history, but it is also the main reason new conversations confuse:

- active vs historical criteria
- current vs historical benchmarks
- old named baselines vs current architecture

This README and the manifest exist to stop that confusion.
