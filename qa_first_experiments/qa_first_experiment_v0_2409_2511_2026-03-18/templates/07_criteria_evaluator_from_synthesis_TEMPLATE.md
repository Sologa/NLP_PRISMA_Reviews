# Criteria Evaluator From Synthesis Prompt

You are evaluating the current stage-specific criteria from a synthesis object.

## Current-State Constraints

- Use only:
  - `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- Do not invent hidden criteria or new exclusions.
- Use only the synthesis object evidence supplied here.

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
- `2`: exclusion-leaning with some residual ambiguity
- `1`: clear exclusion or clear absence of core fit

## Inputs

- `paper_id`: `{{PAPER_ID}}`
- `paper_title`: `{{PAPER_TITLE}}`
- `stage`: `{{STAGE}}`
- `arm`: `qa+synthesis`

### Synthesis Object
```json
{{SYNTHESIS_OBJECT_JSON}}
```

## Task

Produce a decision-ready evaluation record with:

- `stage_score`
- `decision_recommendation`
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
