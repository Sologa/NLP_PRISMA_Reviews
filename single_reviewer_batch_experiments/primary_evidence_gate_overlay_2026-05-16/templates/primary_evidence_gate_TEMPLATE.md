# Primary Evidence Gate

You are running an experiment-only pre-review gate. Classify the candidate's
publication form using only title/abstract-visible metadata and the supplied
criteria policy.

The criteria JSON and policy describe the systematic review's screening rules,
not the candidate paper. Never quote the review topic, review title, criteria
source, or criteria wording as evidence about the candidate's publication form.
Candidate evidence must come from the Candidate Metadata block, especially the
candidate `title` and `abstract`.

## Decision Boundary

The default gate is active unless the criteria policy says secondary or survey
papers are explicitly allowed.

Return `exclude_non_primary` only when the candidate title, abstract, or
metadata clearly shows that the candidate is not a primary empirical/original
research study. Examples include survey, review, systematic review, scoping
review, position paper, editorial/commentary, reporting guideline,
standards/specification document, or dataset/tool documentation without an
empirical analysis.

Return `pass_primary` when the title/abstract indicates an original empirical,
experimental, methodological, dataset-with-evaluation, or analytic study.
Replication or reproduction studies with experiments/analysis should pass.
Book chapters or proceedings chapters should pass when the abstract reports
original experiments, analyses, or empirical results.

Return `unclear_pass` when the publication form is ambiguous from title and
abstract. Do not exclude merely because the abstract is short or the empirical
component is not fully proven from the abstract.

For every `exclude_non_primary` decision, include at least one
`title_abstract_quotes` item that is copied from the candidate title or abstract
and directly signals the non-primary publication form. If you cannot quote such
a candidate-specific signal, return `unclear_pass`.

If `criteria_exception_allows_secondary` is true, do not exclude a candidate
only for being a secondary/survey/review paper. In that case, set
`criteria_exception_applied` to true and use `pass_primary` or `unclear_pass`
as appropriate.

## Required JSON Output

Return only the strict JSON object requested by the response schema.

## Paper

`{{PAPER_ID}}`

## Candidate Metadata

```json
{{METADATA_JSON}}
```

## Criteria Primary-Gate Policy

```json
{{CRITERIA_PRIMARY_GATE_POLICY_JSON}}
```

## Stage 1 Criteria

```json
{{STAGE1_CRITERIA_JSON}}
```
