# Stage 1 QA+Synthesis Reviewer Prompt

You are running an experiment-only `QA+synthesis` workflow for systematic review screening.

This step is still a QA step.
Do not output final include/exclude verdict.
Do not build the synthesis object yet.

## Current-State Constraints

- Current production criteria are stage-specific:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- The file `{{SEED_QA_JSON_PATH}}` is an experiment seed QA asset, not formal criteria.
- Use only title, abstract, keywords, and metadata-level evidence in Stage 1.

## Review Target

- `paper_id`: `{{PAPER_ID}}`
- `paper_title`: `{{PAPER_TITLE}}`
- `stage`: `stage1`
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

### Seed QA JSON
Use the questions defined in:
`{{SEED_QA_JSON_PATH}}`

## Task

Answer every Stage 1 seed QA question in a synthesis-friendly form.

For each question provide:

- `qid`
- `criterion_family`
- `answer_state`
- `answer_rationale`
- `supporting_quotes`
- `locations`
- `missingness_reason`
- `stage2_handoff_note`
- `candidate_synthesis_fields`

The field `candidate_synthesis_fields` must name which later synthesis field this QA item should feed, such as:

- `source_object`
- `target_object`
- `nlp_role`
- `non_target_family`
- `preference_signal`
- `comparison_type`
- `audio_domain`
- `learning_vs_evaluation`

## Output Format

Return a single JSON object with this shape:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output final include/exclude verdict here.
- Do not synthesize multiple questions into one field yet.
- Do not use full text.
- Keep every answer grounded in explicit evidence.

