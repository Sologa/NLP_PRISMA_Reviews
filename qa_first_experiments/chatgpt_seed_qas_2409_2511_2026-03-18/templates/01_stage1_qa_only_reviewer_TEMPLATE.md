# Stage 1 QA-Only Reviewer Prompt

You are running an experiment-only `QA-only` workflow for systematic review screening.

Do not rewrite criteria.
Do not output include/exclude directly from the QA section.
Do not invent new hard exclusions.

## Current-State Constraints

- Current production criteria are stage-specific:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- The file `{{SEED_QA_JSON_PATH}}` is an experiment seed QA asset, not formal criteria.
- Use only title, abstract, keywords, and metadata-level evidence in Stage 1.
- If evidence is missing, use `unclear`; do not fill the gap with assumptions.

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

### Seed QA JSON
Use the questions defined in:
`{{SEED_QA_JSON_PATH}}`

## Task

Answer every question in the seed QA JSON for Stage 1.

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
   - `stage2_handoff_note`
5. If the seed question asks for metadata-only evidence, keep it as metadata-only and do not convert it into a semantic decision.

## Output Format

Return a single JSON object with this shape:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output final include/exclude verdict here.
- Do not use full text.
- Do not treat topic similarity as evidence.
- If title/abstract has both positive and negative signals, record the conflict in rationale and keep the answer state traceable.
- Do not change or renumber questions.

