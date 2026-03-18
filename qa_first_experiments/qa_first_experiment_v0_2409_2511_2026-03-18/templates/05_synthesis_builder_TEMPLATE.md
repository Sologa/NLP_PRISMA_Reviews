# Synthesis Builder Prompt

You are building a workflow-layer synthesis object from QA outputs.

This is not a criteria rewrite and not a final decision step.

## Current-State Constraints

- Current production criteria stay external and unchanged:
  - Stage 1: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
  - Stage 2: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- Synthesis exists only to normalize QA evidence for later evaluation.

### Current Stage 1 Criteria JSON
```json
{{CURRENT_STAGE1_CRITERIA_JSON_CONTENT}}
```

### Current Stage 2 Criteria JSON
```json
{{CURRENT_STAGE2_CRITERIA_JSON_CONTENT}}
```

## Inputs

- `paper_id`: `{{PAPER_ID}}`
- `paper_title`: `{{PAPER_TITLE}}`
- `target_stage`: `{{TARGET_STAGE}}`
- `arm`: `qa+synthesis`

### Prior Stage Output
```json
{{PRIOR_STAGE_OUTPUT_JSON}}
```

### Current QA Output
```json
{{CURRENT_QA_OUTPUT_JSON}}
```

### Synthesis Schema
Path: `{{SYNTHESIS_SCHEMA_PATH}}`

```yaml
{{SYNTHESIS_SCHEMA_CONTENT}}
```

## Task

Build a single synthesis object for `{{TARGET_STAGE}}`.

- If `{{TARGET_STAGE}}` is `stage1`, synthesize only from the current Stage 1 QA output.
- If `{{TARGET_STAGE}}` is `stage2`, carry forward any relevant Stage 1 evidence from the prior output and update it with Stage 2 evidence instead of erasing traceability.

Every field record must include:

- `field_name`
- `state`
- `normalized_value`
- `supporting_quotes`
- `locations`
- `missingness_reason`
- `conflict_note`
- `derived_from_qids`
- `stage_handoff_status`

## Output Contract

Return one JSON object shaped like:

```json
{{SYNTHESIS_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not add a new criterion.
- Do not collapse mixed evidence into false certainty.
- Keep `derived_from_qids` traceable.
