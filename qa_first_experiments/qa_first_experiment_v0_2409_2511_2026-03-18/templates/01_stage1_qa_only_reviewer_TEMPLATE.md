# Stage 1 QA-Only Reviewer Prompt

You are running the experiment-only `QA-only` workflow.

## Current-State Constraints

- Current production criteria stay external and unchanged:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- `{{QA_JSON_PATH}}` is an experiment QA asset, not formal criteria.
- Use only title, abstract, keywords, and metadata-level evidence available at Stage 1.
- If evidence is missing, answer `unclear`. Do not invent a new hard exclusion.

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
- `stage`: `stage1`
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

For each answer:

1. Keep the original `qid`.
2. Keep the original `criterion_family`.
3. Use only `present`, `absent`, or `unclear`.
4. Return:
   - `answer_state`
   - `answer_rationale`
   - `supporting_quotes`
   - `locations`
   - `missingness_reason`
   - `stage2_handoff_note`

## Output Contract

Return one JSON object shaped like:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output include/exclude/maybe here.
- Do not answer reviewer guardrails as if they were evidence questions.
- Do not use full text.
- Do not renumber or rewrite questions.
