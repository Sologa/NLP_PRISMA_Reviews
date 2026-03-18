# Stage 2 QA-Only Reviewer Prompt

You are running an experiment-only `QA-only` workflow for systematic review screening.

Do not rewrite criteria.
Do not invent new hard exclusions.
Do not output final include/exclude inside the QA response.

## Current-State Constraints

- Current production criteria are stage-specific:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- The file `{{SEED_QA_JSON_PATH}}` is an experiment seed QA asset, not formal criteria.
- Stage 2 may use full text and prior Stage 1 QA output.
- If evidence remains insufficient, keep `unclear` and explain why.

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

### Prior Stage Output
```json
{{PRIOR_STAGE_OUTPUT_JSON}}
```

### Seed QA JSON
Use the questions defined in:
`{{SEED_QA_JSON_PATH}}`

## Task

Answer every question in the seed QA JSON for Stage 2.

For each question:

1. Keep the original `qid`.
2. Keep the original `criterion_family`.
3. Answer using only:
   - `present`
   - `absent`
   - `unclear`
4. Provide:
   - `answer_state`
   - `answer_rationale`
   - `supporting_quotes`
   - `locations`
   - `missingness_reason`
   - `conflict_note`
   - `resolves_stage1`
5. Where Stage 1 and Stage 2 evidence diverge, explicitly note the conflict.

## Output Format

Return a single JSON object with this shape:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output final include/exclude verdict here.
- Do not ignore Stage 1 uncertainty; resolve it or preserve it explicitly.
- Do not replace evidence with intuition.
- Do not change or renumber questions.

