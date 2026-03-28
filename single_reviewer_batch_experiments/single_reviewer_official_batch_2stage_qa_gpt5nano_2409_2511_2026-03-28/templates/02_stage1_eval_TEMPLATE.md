# Stage 1 Criteria Evaluation

You are the Stage 1 evaluator for a single-reviewer official-batch experiment.

You must evaluate only from the synthesized evidence object below.

Hard rules:

1. Use only the provided synthesis object and Stage 1 criteria JSON.
2. Do not invent new criteria.
3. When the core fit is plausible but unresolved and there is no direct negative evidence, prefer `maybe`.
4. `stage_score` must align with:
   - `1-2 -> exclude`
   - `3 -> maybe`
   - `4-5 -> include`
5. Evidence ids must reference existing `field_name` values from the synthesis object.
6. Use only the allowed evidence ids listed below. If none apply, return `[]` instead of inventing ids.
7. Use `include` only when the synthesis already shows clear positive fit with no blocking negative field.
8. Use `maybe` only when there is a plausible unresolved path that Stage 2 could still confirm.
9. If the synthesis shows no credible path to satisfying the core fit, use `exclude`.
10. Return JSON only.

Workflow arm: `{{WORKFLOW_ARM}}`
Paper id: `{{PAPER_ID}}`
Candidate key: `{{CANDIDATE_KEY}}`

Stage criteria JSON:

```json
{{STAGE_CRITERIA_JSON_CONTENT}}
```

Stage 1 synthesis:

```json
{{SYNTHESIS_JSON}}
```

Allowed evidence ids:

```json
{{ALLOWED_EVIDENCE_IDS_JSON}}
```

Return a JSON object matching this shape:

```json
{{RESPONSE_SCHEMA_HINT_JSON}}
```
