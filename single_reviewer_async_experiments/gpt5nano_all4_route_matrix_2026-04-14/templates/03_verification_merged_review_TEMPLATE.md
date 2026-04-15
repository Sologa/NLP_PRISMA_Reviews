# Verification Review

You are running a single-reviewer verification pass inside `{{WORKFLOW_ARM}}`.

Your job is to revisit a routed case and return a corrected criterion ledger plus a fresh stage score.

Hard rules:

1. Stay source-faithful to the provided criteria and QA asset.
2. Use only the provided inputs.
3. Do not invent new hard exclusions or operational hardening.
4. Re-evaluate every criterion in the asset; return exactly one `criterion_assessments[]` item per criterion.
5. `criterion_id` values must exactly match the asset.
6. If the routed issue is a semantic trap, explicitly resolve that trap in `decision_rationale`.
7. `stage_score` must follow:
   - `1-2 -> exclude`
   - `3 -> maybe`
   - `4-5 -> include`
8. Output valid JSON only.

Workflow arm: `{{WORKFLOW_ARM}}`
Paper id: `{{PAPER_ID}}`
Candidate key: `{{CANDIDATE_KEY}}`
Verification source phase: `{{VERIFICATION_SOURCE_PHASE}}`
Verification input kind: `{{VERIFICATION_INPUT_KIND}}`

Topic definition:

```text
{{TOPIC_DEFINITION}}
```

Decision policy:

```text
{{DECISION_POLICY}}
```

Paper profile:

```json
{{PAPER_PROFILE_JSON}}
```

Routing decision:

```json
{{ROUTING_DECISION_JSON}}
```

Merged criterion asset:

```json
{{QA_ASSET_JSON}}
```

Stage criteria JSON:

```json
{{STAGE_CRITERIA_JSON_CONTENT}}
```

Candidate metadata:

```json
{{METADATA_JSON}}
```

Prior review output:

```json
{{PRIOR_REVIEW_JSON}}
```

Source provenance:

```json
{{SOURCE_RECORD_PROVENANCE_JSON}}
```

Verification evidence payload:

```text
{{VERIFICATION_EVIDENCE_TEXT}}
```

Return a JSON object matching this shape:

```json
{{RESPONSE_SCHEMA_HINT_JSON}}
```
