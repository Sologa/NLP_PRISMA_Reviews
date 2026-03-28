# CURRENT AUTHORITY

Date: 2026-03-28
Status: authoritative current-state summary for runtime paths, score authority, and comparison baselines

This file is the single obvious authority summary in `docs/`.

If an older report, slide deck, or table conflicts with this file, follow this file together with:

1. `docs/chatgpt_current_status_handoff.md`
2. `screening/results/results_manifest.json`
3. the listed JSON metrics files in this document

This file does two things:

1. states the current production authority
2. states the non-production comparison conventions that are still useful for QA / non-QA discussions

## 1. Runtime And Workflow Authority

Current runtime authority:

- Runtime prompts: `scripts/screening/runtime_prompts/runtime_prompts.json`
- Stage 1 criteria: `criteria_stage1/<paper_id>.json`
- Stage 2 criteria: `criteria_stage2/<paper_id>.json`
- Pre-review cutoff: `cutoff_jsons/<paper_id>.json`

Current workflow invariants:

- cutoff is applied before reviewer routing
- cutoff-failed rows are authoritative `exclude (cutoff_time_window)` outputs
- Stage 1 routing remains: double-high include, double-low exclude, otherwise `SeniorLead`
- `SeniorLead` remains mandatory once invoked

## 2. Current Production Score Authority

Important clarification:

- `senior_no_marker` is still current authority for `2307.05527` and `2601.19926`
- `stage_split_criteria_migration` is current authority for `2409.13738` and `2511.13936`
- there is no current production QA authority

### 2.1 Authority Table

| Paper | Current authority label | Stage 1 authority file | Combined authority file | Stage 1 F1 | Combined F1 | Status |
| --- | --- | --- | --- | ---: | ---: | --- |
| `2307.05527` | `latest_fully_benchmarked_senior_no_marker` | `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json` | `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json` | `0.9621` | `0.9621` | current stable reference |
| `2409.13738` | `stage_split_criteria_migration` | `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json` | `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json` | `0.7500` | `0.7500` | current authority |
| `2511.13936` | `stage_split_criteria_migration` | `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json` | `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json` | `0.8788` | `0.9062` | current authority |
| `2601.19926` | `latest_fully_benchmarked_senior_no_marker` | `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json` | `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json` | `0.9792` | `0.9731` | current stable reference |

### 2.2 Current Authority Metrics

#### `2307.05527`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.9593` | `0.9649` | `0.9621` | `165` | `7` | `40` | `6` |
| Combined | `0.9593` | `0.9649` | `0.9621` | `165` | `7` | `40` | `6` |

#### `2409.13738`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.6000` | `1.0000` | `0.7500` | `21` | `14` | `45` | `0` |
| Combined | `0.6000` | `1.0000` | `0.7500` | `21` | `14` | `45` | `0` |

#### `2511.13936`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.8056` | `0.9667` | `0.8788` | `29` | `7` | `50` | `1` |
| Combined | `0.8529` | `0.9667` | `0.9062` | `29` | `5` | `52` | `1` |

#### `2601.19926`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.9735` | `0.9851` | `0.9792` | `330` | `9` | `14` | `5` |
| Combined | `0.9731` | `0.9731` | `0.9731` | `326` | `9` | `14` | `9` |

## 3. Exact Position Of `senior_no_marker`

`senior_no_marker` has two different roles in the repo. It must not be described as one uniform thing.

| Paper | Role of `senior_no_marker` | Stage 1 F1 | Combined F1 |
| --- | --- | ---: | ---: |
| `2307.05527` | current stable reference | `0.9621` | `0.9621` |
| `2409.13738` | historical baseline only | `0.6774` | `0.6774` |
| `2511.13936` | historical baseline only | `0.7436` | `0.7500` |
| `2601.19926` | current stable reference | `0.9792` | `0.9731` |

Historical `senior_no_marker` metrics:

### `2409.13738`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.5122` | `1.0000` | `0.6774` | `21` | `20` | `39` | `0` |
| Combined | `0.5122` | `1.0000` | `0.6774` | `21` | `20` | `39` | `0` |

### `2511.13936`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.6042` | `0.9667` | `0.7436` | `29` | `19` | `38` | `1` |
| Combined | `0.6429` | `0.9000` | `0.7500` | `27` | `15` | `42` | `3` |

## 4. QA Authority Convention

There is currently no QA production authority.

QA runs remain experiment-only comparison tracks.

For QA discussion, use the following two conventions.

### 4.1 Canonical QA Comparison Line

When a discussion needs one canonical QA comparison line, use:

- run family: `qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19`
- arm: `qa+synthesis`

This is the canonical QA comparison line because it is the repo's stabilized cutoff-corrected QA reference used in later summary docs.

Canonical QA metrics:

| Paper | Arm | Stage 1 F1 | Combined F1 | Precision / Recall (Combined) | Role |
| --- | --- | ---: | ---: | --- | --- |
| `2409.13738` | `qa+synthesis` | `0.7368` | `0.7368` | `0.5833 / 1.0000` | canonical QA comparison line |
| `2511.13936` | `qa+synthesis` | `0.8772` | `0.8571` | `0.9231 / 0.8000` | canonical QA comparison line |

### 4.2 Best Completed Historical QA By Paper

If the discussion is specifically about "best completed QA result" rather than "canonical QA comparison line", use this table.

| Paper | Best completed QA run family | Arm | Stage 1 F1 | Combined F1 | Notes |
| --- | --- | --- | ---: | ---: | --- |
| `2409.13738` | `qa_first_v0_2409_2511_2026-03-18` | `qa-only` | `0.7925` | `0.7925` | best completed historical QA for `2409`; not canonical QA comparison line |
| `2511.13936` | `qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19` | `qa+synthesis` | `0.8772` | `0.8571` | best completed historical QA for `2511`; also the canonical QA comparison line |

Detailed metrics for the best completed QA runs:

### `2409.13738` best historical QA

- run family: `qa_first_v0_2409_2511_2026-03-18`
- arm: `qa-only`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.6562` | `1.0000` | `0.7925` | `21` | `11` | `48` | `0` |
| Combined | `0.6562` | `1.0000` | `0.7925` | `21` | `11` | `48` | `0` |

### `2511.13936` best historical QA

- run family: `qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19`
- arm: `qa+synthesis`

| Split | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 1 | `0.9259` | `0.8333` | `0.8772` | `25` | `2` | `55` | `5` |
| Combined | `0.9231` | `0.8000` | `0.8571` | `24` | `2` | `55` | `6` |

## 5. Single-Reviewer QA / Non-QA Status

These are not production authority. They are comparison tracks only.

### 5.1 Best Completed Single-Reviewer Non-QA Runs

| Paper | Workflow | Run ID | F1 | Precision | Recall | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `2409.13738` | direct review, no QA | `20260324_2409_rerun2_gpt54_low` | `0.9130` | `0.8400` | `1.0000` | best completed single-reviewer non-QA run for `2409` |
| `2511.13936` | direct review, no QA | `20260326_gpt5_low_2511_sep` | `0.9000` | `0.9000` | `0.9000` | best completed single-reviewer non-QA run for `2511` |

### 5.2 Current Single-Reviewer 2-Stage QA Status

Current 2-stage QA bundle:

- bundle family: `single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28`

Current status:

- full run `20260328_full_gpt5nano_low_2stageqa_2409_2511` is not finished
- `stage2_eval` is still `validating`
- therefore this line is not an authority line

Completed smoke result with the highest finished score in that bundle:

| Run ID | Paper | F1 | Precision | Recall | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| `20260328_smoke_gpt5nano_low_2stageqa_2409_2511_v3` | `2409.13738` | `0.0000` | `0.0000` | `0.0000` | completed smoke only |
| `20260328_smoke_gpt5nano_low_2stageqa_2409_2511_v3` | `2511.13936` | `0.6667` | `0.5000` | `1.0000` | completed smoke only |

## 6. Do-Not-Confuse Rules

- do not describe `criteria_jsons/*.json` as current production criteria
- do not describe historical `senior_no_marker` scores for `2409` or `2511` as current authority
- do not describe any QA run as current production authority
- do not describe single-reviewer runs as production authority
- if you need one canonical QA comparison line, use `qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19 / qa+synthesis`
- if you need one production authority line per paper, use the table in Section 2

## 7. Primary Source Files

### Current production authority

- `docs/chatgpt_current_status_handoff.md`
- `screening/results/results_manifest.json`
- `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json`
- `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json`
- `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
- `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
- `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
- `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
- `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json`
- `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json`

### Historical `senior_no_marker` baselines used for comparison

- `screening/results/2409.13738_full/review_after_stage1_senior_no_marker_report.json`
- `screening/results/2409.13738_full/combined_after_fulltext_senior_no_marker_report.json`
- `screening/results/2511.13936_full/review_after_stage1_senior_no_marker_report.json`
- `screening/results/2511.13936_full/combined_after_fulltext_senior_no_marker_report.json`

### QA comparison lines

- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/stage1_f1.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/combined_f1.json`
- `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa-only/stage1_f1.json`
- `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa-only/combined_f1.json`

### Single-reviewer comparison lines

- `screening/results/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/runs/20260324_2409_rerun2_gpt54_low/papers/2409.13738/single_reviewer_batch_f1.json`
- `screening/results/single_reviewer_official_batch_gpt5_all4_2026-03-22/runs/20260326_gpt5_low_2511_sep/papers/2511.13936/single_reviewer_batch_f1.json`
- `screening/results/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/runs/20260328_full_gpt5nano_low_2stageqa_2409_2511/run_manifest.json`
- `screening/results/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/runs/20260328_smoke_gpt5nano_low_2stageqa_2409_2511_v3/papers/2409.13738/single_reviewer_batch_f1.json`
- `screening/results/single_reviewer_official_batch_2stage_qa_gpt5nano_2409_2511_2026-03-28/runs/20260328_smoke_gpt5nano_low_2stageqa_2409_2511_v3/papers/2511.13936/single_reviewer_batch_f1.json`
