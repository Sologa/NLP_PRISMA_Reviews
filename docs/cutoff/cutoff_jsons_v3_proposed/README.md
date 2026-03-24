# cutoff_jsons v3 proposal

## Purpose

This folder is not the canonical source of review criteria. The current repository runtime uses stage-specific criteria files under `criteria_stage1/*.json` and `criteria_stage2/*.json`, while `cutoff_jsons/*.json` is currently a manually validated intermediate artifact for publication-time logic and related audit metadata.

For the automatic survey generation pipeline described in this report, `cutoff_jsons` should be upgraded into a deterministic **time-logic compilation layer** with two simultaneous goals:

1. **Audit fidelity**: preserve what the paper literally says about publication-time screening.
2. **Execution convenience**: expose a single program-readable `time_policy` that can be applied as an early hard prefilter before later screening stages.

The key design choice is:

- record **all** time-related clauses found in the paper, corrected criteria, or validated fallback sources;
- then derive `time_policy` as the **intersection of all projectable hard publication-date clauses**.

This matches the intended one-shot pipeline behavior: filter early, save time, and avoid reading papers that would eventually fail on time anyway.

## Important distinction

`time_policy` is **not** a natural-language summary of the paper. It is the output of a deterministic compilation step.

The file therefore keeps both:

- `source_faithful_screening_publication_policy`: what the paper literally states as screening-time publication policy;
- `time_policy`: the program-readable intersection used by the pipeline;
- `time_clauses`: the full set of time-related clauses from which `time_policy` was derived.

This avoids the old failure mode where a paper such as `2409.13738` looked like it had "no time limit" even though the reported search execution month still imposed a real upper bound on the candidate pool.

## Default derivation rule

Let `C` be the set of all entries in `time_clauses` with:

- `project_to_time_policy = true`, and
- `hardness in {"hard", "fallback"}`.

Then:

- `time_policy.start_date` = the maximum of all defined lower bounds in `C`;
- `time_policy.end_date` = the minimum of all defined upper bounds in `C`;
- `time_policy.enabled = true` if at least one finite lower/upper bound remains after projection, otherwise `false`.

Default logic is **intersection**, not union.

Use a union only if the source paper explicitly encodes alternative admissible branches such as:
- `(published in range A) OR (published in range B)`,
- or different windows for mutually exclusive, fully specified cohorts that are all admitted.

No such union case was found in the current `cutoff_jsons` corpus.

## Clause taxonomy

### Projectable clause kinds

These can tighten `time_policy` directly because they can be represented as a single monotonic publication-date interval:

- `publication_window`
- `publication_lower_bound`
- `publication_upper_bound`
- `search_execution_date_projection`
- `manuscript_horizon_upper_bound`
- `sr_publication_date_upper_bound`
- `explicit_no_publication_restriction` (projects to the universal interval and therefore does not tighten the intersection)

### Non-projectable clause kinds

These are still time-related and must be preserved, but they do **not** collapse cleanly into a single global publication-date window:

- `conditional_time_citation_rule`
- `per_year_record_cap`
- `per_year_top_k_sampling`
- `time_condition_relaxation`
- `same_contribution_latest_version_rule`
- `observed_included_corpus_span`

These clauses remain in `time_clauses` for auditability and for future specialized filtering modules, but they do not directly modify `time_policy`.

## Fallback policy

Use `sr_publication_date_upper_bound` only when no better projectable upper bound is available from the paper or criteria extraction.

Priority by informativeness is:

1. explicit publication window or bound from criteria;
2. reported search execution date/month;
3. manuscript preparation horizon if the paper explicitly states that later publications were not included;
4. SR's own publication date fallback.

This is stricter and operationally more useful than the current README rule that prioritizes Stage 2 and uses Stage 1 only as fallback. The proposed rule is designed for a pipeline that does **early intersection-based pruning** rather than stage-by-stage replay.

## Recommended schema

Each file should have the following top-level keys:

- `paper_id`
- `source_md`
- `schema_version`
- `source_faithful_screening_publication_policy`
- `time_clauses`
- `time_policy`
- `evidence`
- `normalization_notes`
- optional `warnings`

### `source_faithful_screening_publication_policy`

This records only the paper-literal screening-time publication rule.

Recommended `status` values:

- `explicit_window`
- `explicit_lower_bound`
- `explicit_upper_bound`
- `explicit_no_publication_restriction`
- `not_explicitly_stated`

### `time_clauses`

Every time-related clause found in the paper should be represented here, even if it is not projectable into `time_policy`.

Minimum fields per clause:

- `clause_id`
- `stage`
- `scope`
- `kind`
- `hardness`
- `project_to_time_policy`
- `date_field`
- `start_date`
- `start_inclusive`
- `end_date`
- `end_inclusive`
- `applies_to_subset`
- `conditional_on`
- optional `details`
- optional `notes`

### `time_policy`

This is the value actually consumed by the pipeline.

Required fields:

- `enabled`
- `date_field`
- `start_date`
- `start_inclusive`
- `end_date`
- `end_inclusive`
- `timezone`
- `derivation_mode`
- `projected_clause_ids`
- `binding_clause_ids`
- `fallback_applied`

## Normalization rules

Use the following normalization defaults:

- year-only lower bound `YYYY` -> `YYYY-01-01`
- year-only upper bound `YYYY` -> `YYYY-12-31`
- month-only upper bound `YYYY-MM` -> last day of that month
- "mid-2025" -> `2025-06-30`
- "up to 2023" -> `2023-12-31`
- search performed in `Month YYYY` -> upper bound at month end unless a precise day is given
- fallback SR publication date -> the first public date of the review artifact actually being reproduced (for arXiv SRs, normally the arXiv v1 date)

## 2409.13738 example

This paper explicitly says there is **no publication-year restriction** in screening, but it also states that the search queries were executed in **June 2023**, and later says that publications after **August 2024** would not be included.

Under this schema:

- `source_faithful_screening_publication_policy.enabled = false`
- `time_clauses` contains all three clauses
- `time_policy.end_date = 2023-06-30` because the June 2023 search execution date is the tightest projectable upper bound

This lets the artifact remain faithful to the paper while still supporting the early-pruning pipeline.

## Implementation guidance for Codex

1. Parse every `time_clauses` entry.
2. Keep all entries for audit.
3. Select entries with `project_to_time_policy = true`.
4. Intersect their publication-date bounds.
5. Preserve non-projectable clauses in memory for later optional filters.
6. Only use fallback clauses if they remain binding after intersection, or if no stronger upper bound exists.

## Why this change is needed

The current folder is good enough for a narrow "publication-year cutoff only" interpretation, but it loses important time logic in several papers:

- `2401.09244` misses the tighter search date (`2023-07-29`) and keeps only the weaker fallback upper bound.
- `2407.17844` misses the search-month upper bound from April 2024.
- `2409.13738` disables time filtering completely even though the search month makes a large difference.
- several files with non-window time logic currently drop that logic entirely.

The v3 proposal fixes this without breaking the convenience of a one-shot prefilter.
