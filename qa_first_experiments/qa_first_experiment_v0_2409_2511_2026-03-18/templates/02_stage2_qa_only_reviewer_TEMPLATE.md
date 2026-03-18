# Stage 2 QA-Only Reviewer Prompt

You are running the experiment-only `QA-only` workflow.

## Current-State Constraints

- Current production criteria stay external and unchanged:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- `{{QA_JSON_PATH}}` is an experiment QA asset, not formal criteria.
- Stage 2 may use full text and prior Stage 1 QA output.
- If evidence remains insufficient, answer `unclear` and explain why.

### Current Stage 1 Criteria JSON
```json
{{CURRENT_STAGE1_CRITERIA_JSON_CONTENT}}
```

### Current Stage 2 Criteria JSON
```json
{{CURRENT_STAGE2_CRITERIA_JSON_CONTENT}}
```

## Review Target

- `paper_id`: `{{PAPER_ID}}`
- `paper_title`: `{{PAPER_TITLE}}`
- `stage`: `stage2`
- `workflow_arm`: `qa-only`

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

### Prior Stage QA Output
```json
{{PRIOR_STAGE_OUTPUT_JSON}}
```

### Reviewer Guardrails
```json
{{REVIEWER_GUARDRAILS_JSON}}
```

### QA Asset
Path: `{{QA_JSON_PATH}}`

```json
{{QA_JSON_CONTENT}}
```

## Task

Answer every answerable question in the QA asset.

For each answer return:

- `qid`
- `criterion_family`
- `answer_state`
- `answer_rationale`
- `supporting_quotes`
- `locations`
- `missingness_reason`
- `conflict_note`
- `resolves_stage1`

## Output Contract

Return one JSON object shaped like:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output include/exclude here.
- Do not answer reviewer guardrails as if they were evidence questions.
- Preserve conflicts between Stage 1 and Stage 2 evidence.
- Do not renumber or rewrite questions.
