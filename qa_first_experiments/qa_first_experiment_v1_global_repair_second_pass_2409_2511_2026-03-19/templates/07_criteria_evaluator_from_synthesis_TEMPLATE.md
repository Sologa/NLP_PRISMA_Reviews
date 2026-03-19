# Criteria Evaluator From Synthesis Prompt

You are evaluating the current stage-specific criteria from a synthesis object.

## Current-State Constraints

- Use only:
  - `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- Do not invent hidden criteria or new exclusions.
- Use only the synthesis object evidence supplied here.

## Review Target

- `paper_id`: `{{PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `stage`: `{{STAGE}}`
- `arm`: `qa+synthesis`

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

## Scoring Rubric

- `5`: all core evidence satisfied, no live exclusion signal
- `4`: strong positive fit with only stage-appropriate deferred or minor uncertainty
- `3`: mixed or unresolved evidence that truly needs adjudication
- `2`: exclusion-leaning with direct negative evidence or a clear absence of core fit
- `1`: clear exclusion or clear absence of core fit with direct negative support

## Inputs

### Source Record Provenance
```json
{{SOURCE_RECORD_PROVENANCE_JSON}}
```

### Protected Review-Level Phrases
```json
{{PROTECTED_REVIEW_PHRASES_JSON}}
```

### Output Identity Contract
```json
{{OUTPUT_IDENTITY_CONTRACT_JSON}}
```

### Synthesis Object
```json
{{SYNTHESIS_OBJECT_JSON}}
```

### Stage-Specific Policy
{{STAGE_SPECIFIC_POLICY_MD}}

## Task

Produce a decision-ready evaluation record with:

- `stage_score`
- `scoring_basis`
- `decision_recommendation`
- `positive_fit_evidence_ids`
- `direct_negative_evidence_ids`
- `unresolved_core_evidence_ids`
- `deferred_core_evidence_ids`
- `criterion_mapping`
- `criterion_conflicts`
- `decision_rationale`
- `manual_review_needed`
- `routing_note`

Stage 1 routing:

- `stage_score >= 4` -> `include`
- `stage_score <= 2` -> `exclude`
- `stage_score = 3` -> `maybe` and route to `SeniorLead`

Stage 2 routing:

- `stage_score >= 4` -> `include`
- `stage_score <= 2` -> `exclude`
- `stage_score = 3` -> `manual_review_needed`

## Output Contract

Return one JSON object shaped like:

```json
{{CRITERIA_EVAL_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Copy the identity contract exactly into the top-level output fields and include `source_record_provenance`.
- Never repeat any literal from `PROTECTED_REVIEW_PHRASES_JSON` anywhere in the output, including literals already present in upstream synthesis objects.
- For Stage 1, do not assign `1` or `2` unless there is direct negative evidence or a clear absence of core fit.
- For Stage 1, only assign `stage_score = 3` when `positive_fit_evidence_ids` is non-empty, `direct_negative_evidence_ids` is empty, and unresolved or deferred core closure still remains.
- For Stage 1, if any evidence id remains in `direct_negative_evidence_ids`, change the score to `1` or `2`; do not keep `3` just because some positive-fit signal is also present.
- For Stage 1, if there is positive thematic fit but no unresolved or deferred core closure, do not use `3`; choose the supported non-defer score instead.
- For Stage 1, do not build `positive_fit_evidence_ids` from loose lexical overlap alone. Generic ranking, comparison, ordinal, rating, or preference wording is not enough when the core domain/object fit is absent or contradicted.
