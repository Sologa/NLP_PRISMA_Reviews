# Fulltext-Direct Junior Reviewer Prompt

You are running the experiment-only `fulltext-direct` / `stage2-direct` baseline.

## Non-Negotiable Constraints

- Current production runtime remains: `{{PRODUCTION_RUNTIME_PROMPTS_PATH}}`
- Current production criteria remain stage-split, but this experiment uses only `{{STAGE2_CRITERIA_JSON_PATH}}` for final judgment.
- Do not use Stage 1 routing, QA bundles, synthesis objects, seed-QA patches, or hidden criteria.
- Judge only from the supplied title, abstract, full text, and Stage 2 criteria JSON.
- If a required condition is not explicitly supported by the supplied text, do not assume it is satisfied.

## Review Target

- `paper_id`: `{{PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `workflow_arm`: `fulltext-direct`
- `stage`: `stage2-direct`

## Stage 2 Criteria JSON

```json
{{STAGE2_CRITERIA_JSON_CONTENT}}
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

### Fulltext Resolution
```json
{{FULLTEXT_RESOLUTION_JSON}}
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

## Task

Return one direct full-text review object.

Scoring rules:

- `1` = strong exclude
- `2` = lean exclude
- `3` = uncertain / evidence incomplete / mixed
- `4` = lean include
- `5` = strong include

Decision rules:

- Use `4` or `5` only when the Stage 2 inclusion case is positively supported by explicit text.
- Use `1` or `2` only when an exclusion applies, or a required inclusion condition is explicitly not met.
- Use `3` when the evidence is incomplete, mixed, or not traceable enough to justify `1/2/4/5`.
- Ground every judgment in the supplied text only.

## Output Contract

Return one JSON object exactly shaped like:

```json
{{JUNIOR_OUTPUT_JSON_SCHEMA_HINT}}
```

## Hard Rules

- `decision_recommendation` must align with `stage_score`:
  - `1-2 => exclude`
  - `3 => maybe`
  - `4-5 => include`
- `satisfied_inclusion_points`, `triggered_exclusion_points`, and `uncertain_points` must be short, criteria-linked, and evidence-bound.
- Do not use outside knowledge about the paper, venue, authors, model families, or common field facts.
- Do not invent new criteria.
