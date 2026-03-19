# Stage 1 QA+Synthesis Reviewer Prompt

You are running the experiment-only `QA+synthesis` workflow.

This step is still a QA step. Do not produce a final decision yet.

## Current-State Constraints

- Current production criteria stay external and unchanged:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- `{{QA_JSON_PATH}}` is an experiment QA asset, not formal criteria.
- Use only title, abstract, keywords, and metadata-level evidence at Stage 1.

## Review Target

- `paper_id`: `{{PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `stage`: `stage1`
- `workflow_arm`: `qa+synthesis`

### Global Identity And Hygiene Policy
{{GLOBAL_IDENTITY_HYGIENE_POLICY_MD}}

### Global Stage 1 Defer Policy
{{GLOBAL_STAGE1_DEFER_POLICY_MD}}

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

### Source Record Provenance
```json
{{SOURCE_RECORD_PROVENANCE_JSON}}
```

### Protected Review-Level Phrases
```json
{{PROTECTED_REVIEW_PHRASES_JSON}}
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

### QA Prompt Payload
Path: `{{QA_JSON_PATH}}`

```json
{{QA_PROMPT_PAYLOAD_JSON}}
```

### Output Identity Contract
```json
{{OUTPUT_IDENTITY_CONTRACT_JSON}}
```

## Task

Answer every answerable question in a synthesis-friendly form.

For each answer return:

- `qid`
- `criterion_family`
- `answer_state`
- `state_basis`
- `answer_rationale`
- `supporting_quotes`
- `locations`
- `missingness_reason`
- `stage2_handoff_note`
- `candidate_synthesis_fields`

## Output Contract

Return one JSON object shaped like:

```json
{{QA_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Copy the identity contract exactly into the top-level output fields.
- Never use review-level phrases as candidate evidence or supporting quotes.
- Never repeat any literal from `PROTECTED_REVIEW_PHRASES_JSON` anywhere in the output, even when restating a criterion family.
- `absent` is only for direct counterevidence or direct non-fit.
- If Stage 1 evidence is incomplete but still plausibly compatible with inclusion, use `unclear` with `state_basis = insufficient_signal`.
- Do not output include/exclude/maybe here.
- Do not answer reviewer guardrails as if they were evidence questions.
- Do not build the synthesis object yet.
