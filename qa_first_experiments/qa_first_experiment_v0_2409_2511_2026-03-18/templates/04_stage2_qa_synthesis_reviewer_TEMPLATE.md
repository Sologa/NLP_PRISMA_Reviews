# Stage 2 QA+Synthesis Reviewer Prompt

You are running the experiment-only `QA+synthesis` workflow.

This step is still a QA step. Do not produce a final decision yet.

## Current-State Constraints

- Current production criteria stay external and unchanged:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- `{{QA_JSON_PATH}}` is an experiment QA asset, not formal criteria.
- Stage 2 may use full text and prior Stage 1 outputs.

### Current Stage 1 Criteria JSON
```json
{{CURRENT_STAGE1_CRITERIA_JSON_CONTENT}}
```

### Current Stage 2 Criteria JSON
```json
{{CURRENT_STAGE2_CRITERIA_JSON_CONTENT}}
```

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

Answer every answerable question in a synthesis-friendly form.

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
- `candidate_synthesis_fields`

## Output Contract

Return one JSON object shaped like:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output include/exclude here.
- Do not answer reviewer guardrails as if they were evidence questions.
- Do not build the synthesis object yet.
- Preserve unresolved conflicts.
