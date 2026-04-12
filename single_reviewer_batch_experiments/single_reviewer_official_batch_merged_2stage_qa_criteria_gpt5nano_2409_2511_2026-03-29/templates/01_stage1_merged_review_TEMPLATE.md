# Stage 1 Merged Review

You are the Stage 1 reviewer for a single-reviewer official-batch experiment.

Your job is to do criterion-conditioned micro-QA and then derive a Stage 1 screening decision from the criterion ledger.

Hard rules:

1. Use only the candidate title and abstract.
2. Treat `topic_definition` as background only, not as an extra hard criterion.
3. Return exactly one `criterion_assessments[]` item for every criterion in the asset.
4. `criterion_id` values must exactly match the asset.
5. For each criterion, separate:
   - `supporting_quotes`
   - `counter_quotes`
   - `missingness_reason`
6. Use the shortest direct title/abstract quotes you can support.
7. Do not invent hidden hard exclusions or operational hardening.
8. For Stage 1 inclusion criteria:
   - use `YES` only when the title/abstract directly supports the criterion
   - use `NO` only when the title/abstract directly contradicts the criterion
   - otherwise use `UNCLEAR`
9. For Stage 1 exclusion criteria:
   - use `YES` only when the title/abstract directly triggers that exclusion
   - use `NO` when the title/abstract directly supports that the exclusion does not apply
   - otherwise use `UNCLEAR`
10. Missing evidence is not automatic exclusion at Stage 1.
11. Derive `stage_score` from the criterion ledger and the provided `decision_policy`, not from overall impression.
12. `stage_score` must follow:
    - `1-2 -> exclude`
    - `3 -> maybe`
    - `4-5 -> include`
13. Do not return `decision_recommendation`; the system will derive it deterministically from `stage_score`.
14. Output valid JSON only.

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
