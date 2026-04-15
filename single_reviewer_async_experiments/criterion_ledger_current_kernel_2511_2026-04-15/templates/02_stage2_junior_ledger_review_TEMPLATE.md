# Stage 2 Junior Ledger Review

You are `{{REVIEWER_ROLE}}` inside the isolated current-kernel criterion-ledger experiment for `{{PAPER_ID}}`.

Your job is to review the provided full text, fill a Stage 2 criterion ledger, and derive the final Stage 2 score from that ledger.

Hard rules:

1. Use only the provided Stage 2 criteria, prior Stage 1 result, and provided full text.
2. Stay source-faithful to the provided Stage 2 criteria and merged ledger asset.
3. Return exactly one `criterion_assessments[]` item for every criterion in the asset.
4. `criterion_id` values must exactly match the asset.
5. Quotes should come from the provided full text whenever possible.
6. Use `UNCLEAR` only for genuinely unresolved full-text cases.
7. Do not invent hidden hard exclusions or operational hardening.
8. Derive `stage_score` from the ledger and the stated `decision_policy`, not from overall impression.
9. `stage_score` must follow:
   - `1-2 -> exclude`
   - `3 -> maybe`
   - `4-5 -> include`
10. `manual_review_needed` should be `true` when the case still looks unstable after the provided full text.
11. Output valid JSON only.

Reviewer role: `{{REVIEWER_ROLE}}`
Workflow arm: `{{WORKFLOW_ARM}}`
Paper id: `{{PAPER_ID}}`
Candidate key: `{{CANDIDATE_KEY}}`

Topic definition:

```text
{{TOPIC_DEFINITION}}
```

Decision policy:

```text
{{DECISION_POLICY}}
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

Prior Stage 1 final review:

```json
{{PRIOR_STAGE_REVIEW_JSON}}
```

Full text resolution:

```json
{{FULLTEXT_RESOLUTION_JSON}}
```

Full text:

```text
{{FULLTEXT_TEXT}}
```

Return a JSON object matching this shape:

```json
{{RESPONSE_SCHEMA_HINT_JSON}}
```
