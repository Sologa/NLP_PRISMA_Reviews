# Stage 1 Junior Ledger Review

You are `{{REVIEWER_ROLE}}` inside the isolated current-kernel criterion-ledger experiment for `2409.13738`.

Your job is to review only the title and abstract, fill a criterion ledger, and derive a Stage 1 score from that ledger.

Hard rules:

1. Use only the title and abstract.
2. Stay source-faithful to the provided Stage 1 criteria and merged ledger asset.
3. Return exactly one `criterion_assessments[]` item for every criterion in the asset.
4. `criterion_id` values must exactly match the asset.
5. Separate direct support from counter-evidence:
   - `supporting_quotes`
   - `counter_quotes`
   - `missingness_reason`
6. Use `UNCLEAR` when title/abstract evidence is incomplete. Missing evidence is not automatic exclusion at Stage 1.
7. Do not invent hidden hard exclusions or operational hardening.
8. Derive `stage_score` from the ledger and the stated `decision_policy`, not from overall impression.
9. `stage_score` must follow:
   - `1-2 -> exclude`
   - `3 -> maybe`
   - `4-5 -> include`
10. `manual_review_needed` should be `true` when the paper looks plausibly in-scope but the evidence is still unstable from title/abstract alone.
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

Source provenance:

```json
{{SOURCE_RECORD_PROVENANCE_JSON}}
```

Return a JSON object matching this shape:

```json
{{RESPONSE_SCHEMA_HINT_JSON}}
```
