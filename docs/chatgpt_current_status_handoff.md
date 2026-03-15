# NLP PRISMA Screening: Canonical Current Status Handoff

Date: 2026-03-16
Status: authoritative current-state handoff

This is the single canonical handoff for future external conversations.

Use this file together with:

- `AGENTS.md`
- `screening/results/results_manifest.json`

Do not infer current state from older reports before reading this file.

## 1. Purpose

This file exists to stop new conversations from confusing:

- active criteria files with historical criteria files
- current metrics with historical benchmark metrics
- candidate next experiments with current adopted architecture

The current repository state is the result of multiple prompt, adjudication, replay, criteria, and criteria-migration experiments. Only part of that history remains current production state.

## 2. Current State Verification

### 2.1 Runtime paths

Current runtime uses:

- runtime prompts from `scripts/screening/runtime_prompts/runtime_prompts.json`
- Stage 1 criteria from `criteria_stage1/<paper_id>.json`
- Stage 2 criteria from `criteria_stage2/<paper_id>.json`

Current runtime must not be described as using:

- `criteria_jsons/*.json`
- removed markdown prompt templates
- old prompt-only / no-marker / operational-v2 reports as current state

### 2.2 Current active criteria files for the two most fragile reviews

#### `2409.13738`

- Stage 1: `criteria_stage1/2409.13738.json`
- Stage 2: `criteria_stage2/2409.13738.json`

#### `2511.13936`

- Stage 1: `criteria_stage1/2511.13936.json`
- Stage 2: `criteria_stage2/2511.13936.json`

### 2.3 Current active metrics authority

#### `2409.13738`

- Stage 1 metrics authority: `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
- Combined metrics authority: `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`

#### `2511.13936`

- Stage 1 metrics authority: `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
- Combined metrics authority: `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`

#### `2307.05527`

Current stable reference remains:

- Stage 1: `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json`

#### `2601.19926`

Current stable reference remains:

- Stage 1: `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json`

### 2.4 Current metrics table

| Paper | Stage 1 criteria path | Stage 2 criteria path | Stage 1 F1 | Combined F1 | Metrics file path |
| --- | --- | --- | ---: | ---: | --- |
| `2307.05527` | `criteria_stage1/2307.05527.json` | `criteria_stage2/2307.05527.json` | `0.9621` | `0.9581` | `review_after_stage1_senior_no_marker_report.json`, `combined_after_fulltext_senior_no_marker_report.json` |
| `2409.13738` | `criteria_stage1/2409.13738.json` | `criteria_stage2/2409.13738.json` | `0.7500` | `0.7843` | `stage1_f1.stage_split_criteria_migration.json`, `combined_f1.stage_split_criteria_migration.json` |
| `2511.13936` | `criteria_stage1/2511.13936.json` | `criteria_stage2/2511.13936.json` | `0.8657` | `0.8814` | `stage1_f1.stage_split_criteria_migration.json`, `combined_f1.stage_split_criteria_migration.json` |
| `2601.19926` | `criteria_stage1/2601.19926.json` | `criteria_stage2/2601.19926.json` | `0.9792` | `0.9733` | `review_after_stage1_senior_no_marker_report.json`, `combined_after_fulltext_senior_no_marker_report.json` |

## 3. Current workflow invariants

These are settled and should be treated as background assumptions.

### Stage 1 routing

- two junior reviewers at title + abstract stage
- if both scores are `>= 4`, final verdict is `include`
- if both scores are `<= 2`, final verdict is `exclude`
- otherwise route to `SeniorLead`

### Senior behavior

- `SeniorLead` remains mandatory
- `SeniorLead` can single-score decide the final Stage 1 verdict once invoked

### Removed and rejected policy

- marker heuristic removed
- global strict senior prompt is not a universal solution
- no return to junior-reasoning marker logic

## 4. Experiment timeline and what each experiment established

### 4.1 Runtime prompt externalization

- runtime prompt source moved to `scripts/screening/runtime_prompts/runtime_prompts.json`
- prompt equivalence check established that externalization itself was not the main confound

Historical references:

- `docs/prompt_only_runtime_realignment_report.md`
- `screening/results/runtime_prompt_externalization/`

### 4.2 Stage 1 aggregation convergence

Experiments across recall-redesign, senior-adjudication, and no-marker established the current aggregation rule:

- double-high include
- double-low exclude
- else senior

Historical references:

- `docs/stage1_recall_redesign_report.md`
- `docs/stage1_senior_adjudication_redesign_report.md`
- `docs/stage1_senior_no_marker_report.md`

### 4.3 Strict senior prompt tuning

This line of work showed:

- better precision on `2409`
- partial help on `2511`
- severe damage to `2601`

This line is historical and should not be treated as the current general solution.

Historical reference:

- `docs/stage1_senior_prompt_tuning_report.md`

### 4.4 Frozen senior replay

This established that the senior prompt effect was real and not mostly junior rerun noise.

Key historical conclusion:

- the effect of stricter senior prompting is review-specific
- this makes global strict senior tuning a poor universal direction

Historical reference:

- `docs/frozen_senior_replay_report.md`

### 4.5 `2511` operationalization v2

This was an important historical experiment because it showed that `2511` performance could improve strongly if criteria were operationally hardened.

But that experiment later became methodologically unacceptable because the criteria contained derived hardening beyond the source-faithful paper boundary.

Historical reference:

- `docs/criteria_2511_operationalization_v2_report.md`

### 4.6 `2409` stage split wording experiment

This was an important historical step because it showed that `2409` had stage-mixing problems.

But this was still earlier than the repo-wide migration to true stage-specific criteria files.

Historical reference:

- `docs/criteria_2409_stage_split_report.md`

### 4.7 Source-faithful vs operational comparison

This historical comparison established:

- operational criteria often produced better F1
- but those gains partly came from unacceptable criteria supertranslation

Historical reference:

- `docs/source_faithful_vs_operational_2409_2511_report.md`

### 4.8 Stage-split criteria migration

This is the current architecture.

What changed:

- criteria were formally split into `criteria_stage1/` and `criteria_stage2/`
- runtime was changed to read stage-specific criteria
- current criteria semantics became much cleaner
- current-state metrics for `2409` and `2511` are now defined by the stage-split migration outputs

Current-state reference:

- `docs/stage_split_criteria_migration_report.md`

## 5. Per-review current state

### 5.1 `2307.05527`

#### Active files

- `criteria_stage1/2307.05527.json`
- `criteria_stage2/2307.05527.json`

#### Current score authority

- Stage 1: `screening/results/2307.05527_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2307.05527_full/combined_after_fulltext_senior_no_marker_report.json`

#### Current metrics

- Stage 1 F1: `0.9621`
- Combined F1: `0.9581`

#### Main current issue

- not the current battleground
- do not destabilize with new global strategy changes

#### Current do-not-touch guidance

- do not revisit global strict senior prompting for this paper
- do not invent new criteria-only changes without a paper-specific reason

### 5.2 `2409.13738`

#### Active files

- `criteria_stage1/2409.13738.json`
- `criteria_stage2/2409.13738.json`

#### Current score authority

- Stage 1: `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
- Combined: `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`

#### Current metrics

- Stage 1 F1: `0.7500`
- Combined F1: `0.7843`

#### Main current issue

- residual hard FP and evidence interpretation under source-faithful constraints
- no longer acceptable to solve this by writing derived hardening back into criteria

#### Current do-not-touch guidance

- do not describe `criteria_jsons/2409.13738.json` as current
- do not treat `criteria_2409_stage_split` historical report as current score authority
- do not label `evidence_qa_feasibility_analysis` as adopted architecture

### 5.3 `2511.13936`

#### Active files

- `criteria_stage1/2511.13936.json`
- `criteria_stage2/2511.13936.json`

#### Current score authority

- Stage 1: `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
- Combined: `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`

#### Current metrics

- Stage 1 F1: `0.8657`
- Combined F1: `0.8814`

#### Main current issue

- performance is lower than the old operational-v2 result
- current criteria semantics are cleaner and must not be polluted again
- future improvements must come from non-criteria layers

#### Current do-not-touch guidance

- do not describe `criteria_jsons/2511.13936.json` as current
- do not treat `criteria_2511_opv2` report as current score authority
- do not reinsert old operational hardening into criteria

### 5.4 `2601.19926`

#### Active files

- `criteria_stage1/2601.19926.json`
- `criteria_stage2/2601.19926.json`

#### Current score authority

- Stage 1: `screening/results/2601.19926_full/review_after_stage1_senior_no_marker_report.json`
- Combined: `screening/results/2601.19926_full/combined_after_fulltext_senior_no_marker_report.json`

#### Current metrics

- Stage 1 F1: `0.9792`
- Combined F1: `0.9733`

#### Main current issue

- highly sensitive to stricter senior behavior
- avoid global changes that sacrifice recall

#### Current do-not-touch guidance

- do not globalize stricter senior prompt rules from `2409`
- do not use `2601` as a justification for criteria hardening that is not source-faithful

## 6. Do-not-confuse rules

These rules exist specifically to stop file confusion in new threads.

1. Do not describe `criteria_jsons/*.json` as active production criteria.
2. Do not use historical operational reports as current score authority.
3. Do not describe `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md` as adopted architecture.
4. Do not assume all four papers share the same kind of current score provenance.
5. For `2409` and `2511`, current score authority is the stage-split migration metrics files.
6. For `2307` and `2601`, current stable reference remains the latest fully benchmarked `senior_no_marker` reports.

## 7. Results read order

When reading per-paper results, use this order.

1. `screening/results/results_manifest.json`
2. the relevant `screening/results/<paper>_full/CURRENT.md`
3. only then, raw or historical result files

This is required because many old files remain in each result directory for comparison, and the filename that looks newest is not always the current score authority.

## 8. Prompt boilerplate for future external chats

Use this block when opening a new external conversation:

```text
Before analyzing this repository, treat the current active criteria as stage-specific:
- Stage 1: criteria_stage1/<paper_id>.json
- Stage 2: criteria_stage2/<paper_id>.json
Do not use criteria_jsons/*.json as current production criteria.
Current score authority is:
- 2409 / 2511: stage_split_criteria_migration metrics
- 2307 / 2601: latest fully benchmarked senior_no_marker reports
Read AGENTS.md, docs/chatgpt_current_status_handoff.md, and screening/results/results_manifest.json first.
Do not infer current state from historical reports.
```

## 9. Candidate next experiment (separate thread only)

The following file is a candidate direction for a future experiment, not the current architecture:

- `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md`

If pursued, it must be handled as a separate experiment thread.

It must not be described as:

- current criteria
- current workflow
- current metrics basis
- current runtime architecture

## 10. K-Dense note

If many future experiment tracks need to be coordinated without repeatedly rewriting background, use `www.k-dense.ai` as an external workflow manager.
