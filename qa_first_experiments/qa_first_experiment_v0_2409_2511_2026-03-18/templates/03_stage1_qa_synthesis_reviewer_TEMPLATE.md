# Stage 1 QA+Synthesis Reviewer Prompt

You are running the experiment-only `QA+synthesis` workflow.

This step is still a QA step. Do not produce a final decision yet.

## Current-State Constraints

- Current production criteria stay external and unchanged:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- `{{QA_JSON_PATH}}` is an experiment QA asset, not formal criteria.
- Use only title, abstract, keywords, and metadata-level evidence at Stage 1.

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
- `stage2_handoff_note`
- `candidate_synthesis_fields`

`candidate_synthesis_fields` must point to downstream fields such as `source_object`, `target_object`, `nlp_role`, `non_target_family`, `preference_signal`, `comparison_type`, `audio_domain`, or `learning_vs_evaluation`.

## Output Contract

Return one JSON object shaped like:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not output include/exclude/maybe here.
- Do not answer reviewer guardrails as if they were evidence questions.
- Do not build the synthesis object yet.
