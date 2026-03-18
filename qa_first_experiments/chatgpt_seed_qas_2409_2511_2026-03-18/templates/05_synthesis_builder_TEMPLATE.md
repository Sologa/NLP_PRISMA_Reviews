# Synthesis Builder Prompt

You are building an evidence synthesis object from QA outputs.

This is a workflow-layer synthesis step.
It is not a criteria rewrite.
It is not the final inclusion decision.

## Inputs

- `paper_id`: `{{PAPER_ID}}`
- `paper_title`: `{{PAPER_TITLE}}`
- `current_stage1_criteria`: `{{CURRENT_STAGE1_CRITERIA_JSON_PATH}}`
- `current_stage2_criteria`: `{{CURRENT_STAGE2_CRITERIA_JSON_PATH}}`
- `stage1_qa_output_json`
- `stage2_qa_output_json`

### Prior Stage QA Output
```json
{{PRIOR_STAGE_OUTPUT_JSON}}
```

## Task

Build a single synthesis object that compresses QA evidence into criterion-relevant fields.

Required base fields for every synthesis object:

- `paper_id`
- `paper_title`
- `field_name`
- `state`
- `supporting_quotes`
- `locations`
- `missingness_reason`
- `conflict_note`
- `derived_from_qids`
- `stage_handoff_status`

Paper-specific field expectations:

### For `2409.13738`
- `source_object`
- `target_object`
- `nlp_role`
- `non_target_family`
- `primary_research`
- `concrete_method`
- `empirical_validation`

### For `2511.13936`
- `preference_signal`
- `comparison_type`
- `ratings_conversion`
- `rl_loop`
- `audio_domain`
- `multimodal_audio_role`
- `learning_vs_evaluation`
- `survey_signal`

## Output Format

Return a single JSON object with this shape:

```json
{{SYNTHESIS_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- Do not add new formal criteria.
- Do not collapse conflicting evidence into a false certainty.
- If multiple QA items support the same synthesis field, aggregate them and preserve traceability via `derived_from_qids`.
- If evidence is still ambiguous, keep `state` as `unclear`.

