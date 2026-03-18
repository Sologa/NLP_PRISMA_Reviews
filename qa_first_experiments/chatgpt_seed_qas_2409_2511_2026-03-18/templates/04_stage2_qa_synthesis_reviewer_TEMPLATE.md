# Stage 2 QA+Synthesis Reviewer Prompt

You are running an experiment-only `QA+synthesis` workflow for systematic review screening.

This step is still a QA step.
Do not output final include/exclude verdict.
Do not build the synthesis object yet.

## Current-State Constraints

- Current production criteria are stage-specific:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- The file `{{SEED_QA_JSON_PATH}}` is an experiment seed QA asset, not formal criteria.
- Stage 2 may use full text and prior Stage 1 QA output.

## Review Target

- `paper_id`: `{{PAPER_ID}}`
- `paper_title`: `{{PAPER_TITLE}}`
- `stage`: `stage2`
- `workflow_arm`: `qa+synthesis`

## Inputs

### Metadata
```json
{{METADATA_JSON}}
```

### Title
```text
{{TITLE}}
```

### Abstract
```text
{{ABSTRACT}}
```

### Full Text
```text
{{FULLTEXT_TEXT}}
```

### Prior Stage Output
```json
{{PRIOR_STAGE_OUTPUT_JSON}}
```

### Seed QA JSON
Use the questions defined in:
`{{SEED_QA_JSON_PATH}}`

## Task

Answer every Stage 2 seed QA question in a synthesis-friendly form.

For each question provide:

- `qid`
- `criterion_family`
- `answer_state`
- `answer_rationale`
- `supporting_quotes`
- `locations`
- `missingness_reason`
- `conflict_note`
- `resolves_stage1`
- `candidate_synthesis_fields`

The field `candidate_synthesis_fields` must name which later synthesis field this QA item should feed.

## Output Format

Return a single JSON object with this shape:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output final include/exclude verdict here.
- Do not skip unresolved conflicts.
- Do not replace evidence with intuition.
- Keep every answer grounded in explicit evidence.

