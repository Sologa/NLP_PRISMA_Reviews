# NLP_PRISMA_Reviews cutoff_jsons audit and redesign report (v4)

Date: 2026-03-23

## What this report does

This version is intentionally more detailed than the previous report because the target reader is Codex. It does four things at once.

1. It re-reads the role of `cutoff_jsons/` in the current repository.
2. It reconciles that current role with your actual pipeline, which applies publication-time filtering early as a hard constraint.
3. It proposes a richer schema that records **all** time-related clauses but still emits a single derived `time_policy` for fast prefiltering.
4. It provides the **full proposed new contents** of every file inside `cutoff_jsons/`, including a replacement `README.md`.

## Direct answer to the 2409.13738 dispute

Your objection was correct.

For `2409.13738`, the statement "there was no restriction on time period" is only the paper-literal screening rule. It is **not** sufficient for your pipeline, because the paper also states that the search queries were executed in **June 2023**, and that objectively constrains the candidate pool. In your pipeline, that June 2023 search date must be treated as a **hard effective upper bound** when deriving the early publication-time prefilter.

So the right representation is not:

1. "no time limit";
2. "a single source-faithful screening cutoff".

The right representation is:

1. preserve the source-faithful screening rule separately;
2. record all time-related clauses;
3. derive `time_policy` as the intersection of all projectable hard clauses.

Under that rule, `2409.13738` ends up with:

1. `source_faithful_screening_publication_policy.enabled = false`
2. derived `time_policy.end_date = 2023-06-30`

That is the most important correction in the folder.

## Current repository role of `cutoff_jsons/`

| Item | Finding |
| --- | --- |
| Repo runtime today | Current runtime uses `criteria_stage1/*.json` and `criteria_stage2/*.json` as the active screening criteria. `cutoff_jsons` is not the canonical runtime criteria source. |
| Stage split intent | The stage split was introduced to keep Stage 2 source-faithful and Stage 1 title/abstract-observable, without adding a third guidance layer. |
| Current cutoff_jsons semantics | The current `cutoff_jsons/README.md` defines the folder as publication-time constraints only, with Stage 2 priority, Stage 1 fallback, and manual validation before runtime mapping. |
| Gap for this pipeline | Your actual pipeline wants a one-shot early time prefilter. That requires a richer artifact than the current README semantics because search dates, manuscript horizons, and other time clauses can materially change the candidate pool. |

## Why the old split is insufficient for your pipeline

The current repo design is stage-aware and source-faithful. That is good for reproducing the review logic stage by stage, but it is not yet the same thing as the **lazy one-shot early prefilter** you actually want.

Your pipeline assumption is:

1. collect every time-related condition that can exclude a paper;
2. normalize them into publication-date-compatible form whenever possible;
3. intersect them;
4. apply the result immediately before spending time on deeper screening.

That is a valid operational design if your objective is speed and high precision. It will sometimes be stricter than a literal stage-by-stage replay, but that is exactly the point of the artifact.

## Recommended semantics for the new cutoff_jsons layer

### Core rule

`time_policy` should be defined as the intersection of all clauses that are both:

1. hard enough to exclude papers in practice; and
2. projectable into a single publication-date interval.

### What must still be recorded even if it is not projectable

Not every time-related rule becomes a single publication-date window. The following still matter and should remain in the file:

1. per-year citation thresholds;
2. per-year record caps;
3. top-k-by-year retrieval rules;
4. "keep the most recent paper for the same contribution" rules;
5. descriptive observed corpus spans.

These should live in `time_clauses` with `project_to_time_policy = false`.

### Union vs intersection

Default logic is intersection. A union should appear only if the paper explicitly defines alternative admissible branches. No such union case was found in the current folder.

### Fallback

When no stronger upper bound exists, use the SR's own publication date as a fallback upper bound. This should stay explicit in the file, not hidden in an external note.

## Proposed schema

Top-level keys:

1. `paper_id`
2. `source_md`
3. `schema_version`
4. `source_faithful_screening_publication_policy`
5. `time_clauses`
6. `time_policy`
7. `evidence`
8. `normalization_notes`
9. optional `warnings`

This lets Codex do two different things from one file:

1. inspect what the paper literally said;
2. execute the compiled prefilter immediately.

## Derivation procedure for Codex

```text
Input: time_clauses[]
Goal: derive time_policy

1. Start with the universal interval (-inf, +inf).
2. For each clause:
   a. keep it for audit no matter what;
   b. if project_to_time_policy == true and hardness in {hard, fallback}, project it to a publication-date interval;
   c. intersect that interval with the running interval.
3. If no finite bound was introduced, set enabled = false.
4. Otherwise set enabled = true and emit the final interval.
5. Record:
   - projected_clause_ids
   - binding_clause_ids
   - whether fallback was needed
6. Do not discard non-projectable time clauses; they remain part of the file.
```

## Folder-wide summary

| Paper | Current repo | Proposed time_policy | Source-faithful policy | Main reason |
| --- | --- | --- | --- | --- |
| 2303.13365 | 2012-01-01 .. 2022-03-31 | 2012-01-01 .. 2022-03-31 | explicit_window | This paper has a direct Stage 2 screening-time window; no fallback is needed. |
| 2306.12834 | 2016-01-01 .. 2022-12-31 | 2016-01-01 .. 2022-12-31 | not_explicitly_stated | The paper does not state a publication-time screening rule in Stage 2. |
| 2307.05527 | 2018-02-01 .. 2023-02-01 | 2018-02-01 .. 2023-02-01 | explicit_window | This file already encoded the correct window numerically, but the revised schema now records both the Stage... |
| 2310.07264 | -inf .. 2023-10-11 | -inf .. 2023-10-11 | not_explicitly_stated | There is no extracted Stage 1 or Stage 2 publication-time rule in the repo criteria file. |
| 2312.05172 | 2000-01-01 .. 2025-12-31 | 2000-01-01 .. 2025-12-31 | explicit_window | Only Stage 2 I1 can be projected to a global publication-date window. |
| 2401.09244 | -inf .. 2024-01-17 | -inf .. 2023-07-29 | not_explicitly_stated | This is a substantive correction relative to the current file: the existing JSON only records the fallback ... |
| 2405.15604 | 2017-01-01 .. 2023-12-31 | 2017-01-01 .. 2023-12-31 | explicit_window | The current file already lands on the right global window, but it drops important non-window time logic: pe... |
| 2407.17844 | 2020-01-01 .. +inf | 2020-01-01 .. 2024-04-30 | not_explicitly_stated | This is another substantive correction relative to the current file: the existing JSON keeps only the lower... |
| 2409.13738 | disabled | -inf .. 2023-06-30 | explicit_no_publication_restriction | This is the most important correction in the whole folder. The current file disables time filtering entirel... |
| 2503.04799 | 2016-01-01 .. 2024-12-31 | 2016-01-01 .. 2024-12-31 | explicit_window | This file only needs schema expansion; the numeric window is already correct. |
| 2507.07741 | 2018-01-01 .. 2024-12-31 | 2018-01-01 .. 2024-12-31 | explicit_window | The current JSON reaches the same numeric result by Stage-2 priority. The revised file records the stronger... |
| 2507.18910 | 2017-01-01 .. 2025-06-30 | 2017-01-01 .. 2025-06-30 | not_explicitly_stated | The current JSON already captures the numeric window correctly; the main revision is schema expansion and c... |
| 2509.11446 | -inf .. 2025-09-14 | -inf .. 2025-09-14 | not_explicitly_stated | This file still needs fallback because the current extracted criteria do not contain any projectable time c... |
| 2510.01145 | 2020-01-01 .. 2025-07-31 | 2020-01-01 .. 2025-07-31 | explicit_window | The current JSON already has the right numeric window. |
| 2511.13936 | 2020-01-01 .. 2025-11-17 | 2020-01-01 .. 2025-11-17 | not_explicitly_stated | The current JSON already gives the same window [2020-01-01, 2025-11-17], but it does not record the arXiv-o... |
| 2601.19926 | -inf .. 2025-07-31 | -inf .. 2025-07-31 | not_explicitly_stated | The current JSON already captures the corrected cut-off date correctly. |

## Per-file detailed diagnosis

## 2303.13365

### Current repo reading
`time_policy`: start=2012-01-01, end=2022-03-31. Current repo already matches explicit Stage 2 window.

### Proposed source-faithful screening publication policy
- status: `explicit_window`
- enabled: `True`
- start_date: `2012-01-01`
- end_date: `2022-03-31`
- evidence_clause_ids: `stage2_i1`

### All time clauses

1. `stage2_i1`
   - stage: `stage2`
   - scope: `screening`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2012-01-01`
   - end_date: `2022-03-31`
   - notes: Month-level bounds normalized to the first day of January 2012 and the last day of March 2022.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2012-01-01`
- end_date: `2022-03-31`
- projected_clause_ids: `stage2_i1`
- binding_clause_ids: `stage2_i1`
- fallback_applied: `False`

### Why this file should change

1. This paper has a direct Stage 2 screening-time window; no fallback is needed.
1. Because the only projectable clause is Stage 2 I1, the operational time_policy is identical to the source-faithful screening policy.

### Evidence snippets

1. `criteria_mds/2303.13365.md` | `Stage 2 Screening Criteria` | `I1`
   - Published between January 2012 and March 2022.

## 2306.12834

### Current repo reading
`time_policy`: start=2016-01-01, end=2022-12-31. Current repo uses Stage 1 R1 search period because no explicit Stage 2 time rule.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `False`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `(none)`

### All time clauses

1. `stage1_r1`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2016-01-01`
   - end_date: `2022-12-31`
   - notes: Stage 1 search period is operationalized as a publication-date window because the one-shot prefilter applies all projectable time bounds up front.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2016-01-01`
- end_date: `2022-12-31`
- projected_clause_ids: `stage1_r1`
- binding_clause_ids: `stage1_r1`
- fallback_applied: `False`

### Why this file should change

1. The paper does not state a publication-time screening rule in Stage 2.
1. Under the proposed cutoff_jsons semantics, the Stage 1 retrieval period is still projected into time_policy because the program applies the intersection of projectable hard time clauses before later-stage review.

### Evidence snippets

1. `criteria_mds/2306.12834.md` | `Stage 1 Retrieval Criteria` | `R1`
   - Search period: 2016–2022.

## 2307.05527

### Current repo reading
`time_policy`: start=2018-02-01, end=2023-02-01. Current repo already matches corrected Stage 2 window.

### Proposed source-faithful screening publication policy
- status: `explicit_window`
- enabled: `True`
- start_date: `2018-02-01`
- end_date: `2023-02-01`
- evidence_clause_ids: `stage2_i5`

### All time clauses

1. `stage1_r2`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2018-02-01`
   - end_date: `2023-02-01`
   - notes: The paper explicitly states that the search-space definition uses the same lower and upper date bounds as the eligibility window.

1. `stage2_i5`
   - stage: `stage2`
   - scope: `screening`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2018-02-01`
   - end_date: `2023-02-01`
   - notes: This is the literal source-faithful screening-time window.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2018-02-01`
- end_date: `2023-02-01`
- projected_clause_ids: `stage1_r2, stage2_i5`
- binding_clause_ids: `stage1_r2, stage2_i5`
- fallback_applied: `False`

### Why this file should change

1. This file already encoded the correct window numerically, but the revised schema now records both the Stage 1 and Stage 2 clauses explicitly.
1. Because the retrieval and screening windows are identical, the operational intersection is unchanged.

### Evidence snippets

1. `criteria_corrected_3papers/2307.05527.md` | `Stage 1 Retrieval / Search-space definition` | `R2`
   - Temporal window (search and eligibility window): 2018-02-01 to 2023-02-01.
1. `criteria_corrected_3papers/2307.05527.md` | `Stage 2 Eligibility / Screening Criteria` | `I5`
   - Temporal window: submitted/published within 2018-02-01 to 2023-02-01.

## 2310.07264

### Current repo reading
`time_policy`: start=null, end=2023-10-11. Current repo uses manual fallback to SR publication date.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `False`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `(none)`

### All time clauses

1. `operational_fallback_sr_publication_date`
   - stage: `fallback`
   - scope: `fallback`
   - kind: `sr_publication_date_upper_bound`
   - hardness: `fallback`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2023-10-11`
   - notes: No explicit time clause was extracted from the paper. The one-shot pipeline records the SR's own publication date as the fallback upper bound.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `None`
- end_date: `2023-10-11`
- projected_clause_ids: `operational_fallback_sr_publication_date`
- binding_clause_ids: `operational_fallback_sr_publication_date`
- fallback_applied: `True`

### Why this file should change

1. There is no extracted Stage 1 or Stage 2 publication-time rule in the repo criteria file.
1. The fallback remains necessary if the program requires a deterministic upper bound for early time-based prefiltering.

### Evidence snippets

1. `cutoff_jsons/2310.07264.json` | `Operational fallback` | `N/A`
   - No explicit publication-time restriction in criteria. Applied the review paper's own publication date as the upper bound: 2023-10-11T07:40:46Z in refs/2310.07264/metadata.json.

## 2312.05172

### Current repo reading
`time_policy`: start=2000-01-01, end=2025-12-31. Current repo keeps Stage 2 I1 window only.

### Proposed source-faithful screening publication policy
- status: `explicit_window`
- enabled: `True`
- start_date: `2000-01-01`
- end_date: `2025-12-31`
- evidence_clause_ids: `stage2_i1`

### All time clauses

1. `stage2_i1`
   - stage: `stage2`
   - scope: `screening`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2000-01-01`
   - end_date: `2025-12-31`
   - notes: Year-only bounds were normalized to a full-year inclusive range.

1. `stage2_e4`
   - stage: `stage2`
   - scope: `screening`
   - kind: `conditional_time_citation_rule`
   - hardness: `conditional`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - conditional_on: `publication_year < 2017 AND citation_count < 10`
   - notes: This rule is time-related but cannot be collapsed into a single global publication window because it depends jointly on publication year and citation count.

1. `stage1_r13`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `per_year_record_cap`
   - hardness: `hard`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - details: `{"year_range": "2000-2022", "per_database_limit": 300}`
   - notes: Limit screening to the first 300 records in each database for years 2000–2022.

1. `stage1_r14`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `per_year_record_cap`
   - hardness: `hard`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - details: `{"year_range": "2023-2025", "per_database_limit": 30}`
   - notes: Limit screening to 30 records per database for years 2023–2025.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2000-01-01`
- end_date: `2025-12-31`
- projected_clause_ids: `stage2_i1`
- binding_clause_ids: `stage2_i1`
- fallback_applied: `False`

### Why this file should change

1. Only Stage 2 I1 can be projected to a global publication-date window.
1. The citation rule (E4) and per-year record caps (R13/R14) must be preserved as non-window time logic; they should not be silently dropped.

### Warnings

1. The extracted criteria use a forward upper bound of 2025 even though the arXiv identifier begins with 2312; keep the repo-extracted value for deterministic reproduction, but manual paper verification is recommended if chronology matters.

### Evidence snippets

1. `criteria_mds/2312.05172.md` | `Stage 2 Screening Criteria` | `I1`
   - Publication date between 2000 and 2025.
1. `criteria_mds/2312.05172.md` | `Stage 2 Screening Criteria` | `E4`
   - For studies published prior to 2017: has fewer than 10 citations in total.
1. `criteria_mds/2312.05172.md` | `Stage 1 Retrieval Criteria` | `R13`
   - For years 2000–2022: limit screening to the first 300 records in each database.
1. `criteria_mds/2312.05172.md` | `Stage 1 Retrieval Criteria` | `R14`
   - For years 2023–2025: limit screening to 30 records per database (no relevant results found beyond this threshold).

## 2401.09244

### Current repo reading
`time_policy`: start=null, end=2024-01-17. Current repo uses only fallback SR publication date; misses tighter search date.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `False`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `(none)`

### All time clauses

1. `stage1_r1`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `search_execution_date_projection`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2023-07-29`
   - notes: The paper states that the search was conducted on July 29, 2023. In the one-shot prefilter, this is projected to an upper bound on publication date.

1. `operational_fallback_sr_publication_date`
   - stage: `fallback`
   - scope: `fallback`
   - kind: `sr_publication_date_upper_bound`
   - hardness: `fallback`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2024-01-17`
   - notes: Fallback to the SR's own publication date. This clause is kept for auditability but is looser than the search-execution upper bound.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `None`
- end_date: `2023-07-29`
- projected_clause_ids: `stage1_r1, operational_fallback_sr_publication_date`
- binding_clause_ids: `stage1_r1`
- fallback_applied: `False`

### Why this file should change

1. This is a substantive correction relative to the current file: the existing JSON only records the fallback upper bound, but misses the tighter search-execution date.
1. Under the proposed semantics, the final time_policy uses the intersection of all projectable clauses, so the binding upper bound becomes 2023-07-29, not 2024-01-17.

### Evidence snippets

1. `criteria_mds/2401.09244.md` | `Stage 1 Retrieval Criteria` | `R1`
   - Search conducted on July 29, 2023.
1. `cutoff_jsons/2401.09244.json` | `Operational fallback` | `N/A`
   - No explicit publication-time restriction in criteria. Applied the review paper's own publication date as the upper bound: 2024-01-17T14:44:27Z in refs/2401.09244/metadata.json.

## 2405.15604

### Current repo reading
`time_policy`: start=2017-01-01, end=2023-12-31. Current repo uses Stage 2 I1, with note that it overrides broader Stage 1 lower-bound.

### Proposed source-faithful screening publication policy
- status: `explicit_window`
- enabled: `True`
- start_date: `2017-01-01`
- end_date: `2023-12-31`
- evidence_clause_ids: `stage2_i1`

### All time clauses

1. `stage1_r3`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_lower_bound`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2017-01-01`
   - end_date: `None`
   - notes: Stage 1 retrieval excludes papers from 2016 or older.

1. `stage1_r5`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `per_year_top_k_sampling`
   - hardness: `hard`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - details: `{"per_query_per_year_top_k": 5}`
   - notes: To even out yearly coverage, the review samples the top 5 papers per query and year by influential citations.

1. `stage1_r6`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `conditional_time_citation_rule`
   - hardness: `conditional`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - conditional_on: `publication_year <= 2021 AND influential_citations >= 2`
   - notes: This rule applies only to papers up to and including 2021.

1. `stage1_r7`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `time_condition_relaxation`
   - hardness: `descriptive`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - notes: For years 2022 and 2023, the citation threshold is relaxed and papers with fewer than two influential citations are not removed.

1. `stage2_i1`
   - stage: `stage2`
   - scope: `screening`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2017-01-01`
   - end_date: `2023-12-31`
   - notes: Manual assessment for relevance is restricted to candidate works within 2017 to 2023.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2017-01-01`
- end_date: `2023-12-31`
- projected_clause_ids: `stage1_r3, stage2_i1`
- binding_clause_ids: `stage1_r3, stage2_i1`
- fallback_applied: `False`

### Why this file should change

1. The current file already lands on the right global window, but it drops important non-window time logic: per-year top-k balancing and year-conditioned citation thresholds.
1. The revised file keeps those clauses explicit so Codex can choose whether to implement them later.

### Evidence snippets

1. `criteria_mds/2405.15604.md` | `Stage 1 Retrieval Criteria` | `R3`
   - Temporal filter: exclude papers from 2016 or older (i.e., focus on publications from 2017 onwards).
1. `criteria_mds/2405.15604.md` | `Stage 1 Retrieval Criteria` | `R5`
   - To even out yearly coverage, sample the top 5 papers per query and year by influential citations.
1. `criteria_mds/2405.15604.md` | `Stage 1 Retrieval Criteria` | `R6`
   - For papers up to (and including) year 2021: exclude papers with fewer than 2 citations (as stated in the pipeline figure).
1. `criteria_mds/2405.15604.md` | `Stage 1 Retrieval Criteria` | `R7`
   - For years 2022 and 2023: relax restrictions and do not remove papers with less than two influential citations.
1. `criteria_mds/2405.15604.md` | `Stage 2 Screening Criteria` | `I1`
   - Manually assessed candidate works are within years 2017 to 2023 (titles and abstracts manually assessed for relevance).

## 2407.17844

### Current repo reading
`time_policy`: start=2020-01-01, end=null. Current repo keeps lower bound only; misses search-month upper bound.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `False`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `(none)`

### All time clauses

1. `stage1_r1`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `search_execution_date_projection`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2024-04-30`
   - notes: The search is reported as having been performed in April 2024. Month-only search execution is normalized to the month-end upper bound for publication-date projection.

1. `stage1_r5`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_lower_bound`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2020-01-01`
   - end_date: `None`
   - notes: The Stage 1 year filter keeps studies from 2020 onwards.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2020-01-01`
- end_date: `2024-04-30`
- projected_clause_ids: `stage1_r1, stage1_r5`
- binding_clause_ids: `stage1_r1, stage1_r5`
- fallback_applied: `False`

### Why this file should change

1. This is another substantive correction relative to the current file: the existing JSON keeps only the lower bound and misses the effective upper bound implied by the search month.
1. Using 2024-04-30 is an operational projection of the latest possible date inside the reported search month; if you later want a stricter interpretation, this can be replaced by a separate exact search timestamp when available.

### Evidence snippets

1. `criteria_mds/2407.17844.md` | `Stage 1 Retrieval Criteria` | `R1`
   - Search performed in April 2024.
1. `criteria_mds/2407.17844.md` | `Stage 1 Retrieval Criteria` | `R5`
   - Year filter: 2020 onwards.

## 2409.13738

### Current repo reading
`time_policy`: disabled. Current repo disables time filtering due to explicit no-publication-year restriction.

### Proposed source-faithful screening publication policy
- status: `explicit_no_publication_restriction`
- enabled: `False`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `stage2_i8_no_publication_restriction`
- notes: The paper explicitly says there is no publication-year restriction in the screening criteria.

### All time clauses

1. `stage2_i8_no_publication_restriction`
   - stage: `stage2`
   - scope: `screening`
   - kind: `explicit_no_publication_restriction`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `None`
   - notes: This contributes the universal interval and therefore does not tighten the intersection.

1. `paper_results_search_executed_june_2023`
   - stage: `paper_results`
   - scope: `retrieval`
   - kind: `search_execution_date_projection`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2023-06-30`
   - notes: The paper states that search queries were executed in June 2023. For the one-shot publication-time prefilter, month-only search execution is projected to a month-end upper bound.

1. `paper_results_observed_corpus_span`
   - stage: `paper_results`
   - scope: `descriptive`
   - kind: `observed_included_corpus_span`
   - hardness: `descriptive`
   - project_to_time_policy: `False`
   - start_date: `2011-01-01`
   - end_date: `2023-12-31`
   - notes: Descriptive span of found/reviewed papers; kept for audit but not used as an independent window because it is an observed outcome rather than a primary rule.

1. `paper_methods_same_contribution_latest_version`
   - stage: `paper_methods`
   - scope: `screening`
   - kind: `same_contribution_latest_version_rule`
   - hardness: `conditional`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - notes: If multiple papers relate to the same contribution, the review keeps the most recent paper. This is time-related but cannot be collapsed into a single global publication-date window.

1. `paper_limitations_manuscript_horizon_aug_2024`
   - stage: `paper_limitations`
   - scope: `reporting`
   - kind: `manuscript_horizon_upper_bound`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2024-08-31`
   - notes: The paper states that publications after the preparation of the manuscript (August 2024) will not be included. This is recorded as a looser upper bound than the search-execution date.

1. `operational_fallback_sr_publication_date`
   - stage: `fallback`
   - scope: `fallback`
   - kind: `sr_publication_date_upper_bound`
   - hardness: `fallback`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2024-09-10`
   - notes: Fallback to the SR's own arXiv publication date. It remains non-binding because the June 2023 search-execution upper bound is tighter.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `None`
- end_date: `2023-06-30`
- projected_clause_ids: `stage2_i8_no_publication_restriction, paper_results_search_executed_june_2023, paper_limitations_manuscript_horizon_aug_2024, operational_fallback_sr_publication_date`
- binding_clause_ids: `paper_results_search_executed_june_2023`
- fallback_applied: `False`

### Why this file should change

1. This is the most important correction in the whole folder. The current file disables time filtering entirely because it follows the source-faithful Stage 2 rule only.
1. For the lazy one-shot prefilter you described, that is too weak: the June 2023 search-execution date is a real time constraint on the candidate pool and therefore must be projected into time_policy.
1. The August 2024 manuscript horizon and the SR publication-date fallback are kept for completeness, but neither is binding once the June 2023 clause is included.
1. The explicit 'no publication-year restriction' is still preserved under source_faithful_screening_publication_policy, so the file now cleanly records both the paper-literal rule and your operational prefilter.

### Evidence snippets

1. `criteria_corrected_3papers/2409.13738.md` | `Stage 2 Eligibility / Screening Criteria` | `I8`
   - No publication-year restriction (i.e., do not exclude by year).
1. `paper: arxiv html 2409.13738v1` | `Results` | `N/A`
   - Our search queries were executed in June 2023 and the found papers span a time period from 2011 to 2023.
1. `paper: arxiv html 2409.13738v1` | `Results / Table 2 metadata` | `N/A`
   - From 2011 to 2023.
1. `paper: arxiv html 2409.13738v1` | `Methods / Inclusion Criteria footnote` | `IC.2 footnote`
   - In case of multiple papers related to the same contribution, we reviewed the most recent paper.
1. `paper: arxiv html 2409.13738v1` | `Threats to Validity and Limitations` | `N/A`
   - Publications after the preparation of this manuscript (August 2024) will also not be included.
1. `paper: arxiv abs metadata` | `Operational fallback` | `N/A`
   - Fallback upper bound uses the SR's own arXiv publication date (2024-09-10).

## 2503.04799

### Current repo reading
`time_policy`: start=2016-01-01, end=2024-12-31. Current repo already matches Stage 2 I2 window.

### Proposed source-faithful screening publication policy
- status: `explicit_window`
- enabled: `True`
- start_date: `2016-01-01`
- end_date: `2024-12-31`
- evidence_clause_ids: `stage2_i2`

### All time clauses

1. `stage2_i2`
   - stage: `stage2`
   - scope: `screening`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2016-01-01`
   - end_date: `2024-12-31`
   - notes: Year-only bounds normalized to a full-year inclusive range.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2016-01-01`
- end_date: `2024-12-31`
- projected_clause_ids: `stage2_i2`
- binding_clause_ids: `stage2_i2`
- fallback_applied: `False`

### Why this file should change

1. This file only needs schema expansion; the numeric window is already correct.

### Evidence snippets

1. `criteria_mds/2503.04799.md` | `Stage 2 Screening Criteria` | `I2`
   - Published between 2016 and 2024.

## 2507.07741

### Current repo reading
`time_policy`: start=2018-01-01, end=2024-12-31. Current repo reaches same result via Stage 2 priority over broader Stage 1 range.

### Proposed source-faithful screening publication policy
- status: `explicit_window`
- enabled: `True`
- start_date: `2018-01-01`
- end_date: `2024-12-31`
- evidence_clause_ids: `stage2_i3`

### All time clauses

1. `stage1_r3`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2014-01-01`
   - end_date: `2025-02-27`
   - notes: Stage 1 retrieval publication-date range.

1. `stage2_i3`
   - stage: `stage2`
   - scope: `screening`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2018-01-01`
   - end_date: `2024-12-31`
   - notes: The final analysis set focuses on papers published between 2018 and 2024.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2018-01-01`
- end_date: `2024-12-31`
- projected_clause_ids: `stage1_r3, stage2_i3`
- binding_clause_ids: `stage2_i3`
- fallback_applied: `False`

### Why this file should change

1. The current JSON reaches the same numeric result by Stage-2 priority. The revised file records the stronger derivation explicitly as an intersection of Stage 1 and Stage 2 windows.
1. Stage 2 I3 is binding because it tightens both the lower and the upper bound.

### Evidence snippets

1. `criteria_mds/2507.07741.md` | `Stage 1 Retrieval Criteria` | `R3`
   - Retrieval publication-date range: 2014 until February 27, 2025.
1. `criteria_mds/2507.07741.md` | `Stage 2 Screening Criteria` | `I3`
   - Analysis set focuses on papers published between 2018 and 2024 (the resulting eligible set for analysis).

## 2507.18910

### Current repo reading
`time_policy`: start=2017-01-01, end=2025-06-30. Current repo already matches Stage 1 R6 window.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `None`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `stage1_r6`
- notes: No explicit publication-time eligibility rule is stated in the final screening criteria. The usable window appears in the retrieval criteria.

### All time clauses

1. `stage1_r6`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2017-01-01`
   - end_date: `2025-06-30`
   - notes: The review searches papers from 2017 to the end of mid-2025. The phrase 'end of mid-2025' is normalized to 2025-06-30 for deterministic execution.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2017-01-01`
- end_date: `2025-06-30`
- projected_clause_ids: `stage1_r6`
- binding_clause_ids: `stage1_r6`
- fallback_applied: `False`

### Why this file should change

1. The current JSON already captures the numeric window correctly; the main revision is schema expansion and clearer documentation that this is a retrieval-stage window rather than an explicit Stage 2 eligibility rule.
1. The phrase 'end of mid-2025' is normalized to 2025-06-30.

### Evidence snippets

1. `criteria_mds/2507.18910.md` | `Stage 1 Retrieval Criteria` | `R6`
   - Publication year from 2017 to end of mid-2025.

## 2509.11446

### Current repo reading
`time_policy`: start=null, end=2025-09-14. Current repo uses manual fallback to SR publication date.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `None`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `(none)`
- notes: No explicit publication-time constraint appears in the extracted criteria.

### All time clauses

1. `operational_fallback_sr_publication_date`
   - stage: `fallback`
   - scope: `fallback`
   - kind: `sr_publication_date_upper_bound`
   - hardness: `fallback`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2025-09-14`
   - notes: No explicit time clause was found in the criteria, so the operational fallback uses the SR's own arXiv publication date as the upper bound.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `None`
- end_date: `2025-09-14`
- projected_clause_ids: `operational_fallback_sr_publication_date`
- binding_clause_ids: `operational_fallback_sr_publication_date`
- fallback_applied: `True`

### Why this file should change

1. This file still needs fallback because the current extracted criteria do not contain any projectable time clause.
1. The fallback is intentionally weak and should be replaced if a future criteria correction file adds a search date or an explicit publication window.

### Evidence snippets

1. `paper: arxiv abs metadata` | `Operational fallback` | `N/A`
   - Fallback upper bound uses the SR's own arXiv publication date (2025-09-14).

## 2510.01145

### Current repo reading
`time_policy`: start=2020-01-01, end=2025-07-31. Current repo already matches identical Stage 1 and Stage 2 windows.

### Proposed source-faithful screening publication policy
- status: `explicit_window`
- enabled: `True`
- start_date: `2020-01-01`
- end_date: `2025-07-31`
- evidence_clause_ids: `stage2_i2`
- notes: The paper states the same publication window in both retrieval and screening criteria.

### All time clauses

1. `stage1_r7`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2020-01-01`
   - end_date: `2025-07-31`
   - notes: Retrieval window from January 2020 through July 2025.

1. `stage2_i2`
   - stage: `stage2`
   - scope: `screening`
   - kind: `publication_window`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2020-01-01`
   - end_date: `2025-07-31`
   - notes: Screening eligibility repeats the same window as Stage 1.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2020-01-01`
- end_date: `2025-07-31`
- projected_clause_ids: `stage1_r7, stage2_i2`
- binding_clause_ids: `stage1_r7, stage2_i2`
- fallback_applied: `False`

### Why this file should change

1. The current JSON already has the right numeric window.
1. The revised file makes the duplication explicit so Codex can see that Stage 1 and Stage 2 agree rather than inferring a hidden priority rule.

### Evidence snippets

1. `criteria_mds/2510.01145.md` | `Stage 1 Retrieval Criteria` | `R7`
   - Published from January 2020 to July 2025.
1. `criteria_mds/2510.01145.md` | `Stage 2 Eligibility / Screening Criteria` | `I2`
   - Published from January 2020 to July 2025.

## 2511.13936

### Current repo reading
`time_policy`: start=2020-01-01, end=2025-11-17. Current repo uses lower bound plus fallback SR publication date; does not preserve arXiv-only citation gates.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `None`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `stage1_r3`
- notes: No explicit Stage 2 publication window is stated, but the retrieval criteria impose a global lower bound from 2020 onward.

### All time clauses

1. `stage1_r3`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_lower_bound`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `2020-01-01`
   - end_date: `None`
   - notes: The review includes papers published from 2020 onward.

1. `stage1_r6`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `conditional_time_citation_rule`
   - hardness: `conditional`
   - project_to_time_policy: `False`
   - start_date: `None`
   - end_date: `None`
   - applies_to_subset: `arxiv_only`
   - details: `{"per_year_minimum_citations": {"2020": 28, "2021": 22, "2022": 32, "2023": 90, "2024": 13, "2025": 1}}`
   - notes: For arXiv papers only, the review further requires year-specific citation thresholds. This is time-related but cannot be collapsed into one global publication-date window.

1. `operational_fallback_sr_publication_date`
   - stage: `fallback`
   - scope: `fallback`
   - kind: `sr_publication_date_upper_bound`
   - hardness: `fallback`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2025-11-17`
   - notes: Because no explicit upper bound is stated in the criteria, the operational fallback uses the SR's own arXiv publication date.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `2020-01-01`
- end_date: `2025-11-17`
- projected_clause_ids: `stage1_r3, operational_fallback_sr_publication_date`
- binding_clause_ids: `stage1_r3, operational_fallback_sr_publication_date`
- fallback_applied: `True`

### Why this file should change

1. The current JSON already gives the same window [2020-01-01, 2025-11-17], but it does not record the arXiv-only year-by-year citation gates that materially affect retrieval.
1. Those citation thresholds are subset-specific and non-window-like, so they stay in time_clauses with project_to_time_policy=false.

### Evidence snippets

1. `criteria_mds/2511.13936.md` | `Stage 1 Retrieval Criteria` | `R3`
   - Published from 2020 onward.
1. `criteria_mds/2511.13936.md` | `Stage 1 Retrieval Criteria` | `R6`
   - For arXiv papers, the citation count must meet year-specific thresholds (2020: 28, 2021: 22, 2022: 32, 2023: 90, 2024: 13, 2025: 1).
1. `paper: arxiv abs metadata` | `Operational fallback` | `N/A`
   - Fallback upper bound uses the SR's own arXiv publication date (2025-11-17).

## 2601.19926

### Current repo reading
`time_policy`: start=null, end=2025-07-31. Current repo already matches corrected cut-off date.

### Proposed source-faithful screening publication policy
- status: `not_explicitly_stated`
- enabled: `None`
- start_date: `None`
- end_date: `None`
- evidence_clause_ids: `stage1_r1`
- notes: The corrected criteria state only an upper cut-off date and do not add a separate Stage 2 publication window.

### All time clauses

1. `stage1_r1`
   - stage: `stage1`
   - scope: `retrieval`
   - kind: `publication_upper_bound`
   - hardness: `hard`
   - project_to_time_policy: `True`
   - start_date: `None`
   - end_date: `2025-07-31`
   - notes: The corrected criteria state a cut-off date of July 31, 2025.

### Derived program-readable time_policy

- enabled: `True`
- start_date: `None`
- end_date: `2025-07-31`
- projected_clause_ids: `stage1_r1`
- binding_clause_ids: `stage1_r1`
- fallback_applied: `False`

### Why this file should change

1. The current JSON already captures the corrected cut-off date correctly.
1. The revised file mainly upgrades the schema so the file is consistent with the rest of the folder.

### Evidence snippets

1. `criteria_corrected_3papers/2601.19926.md` | `Stage 1 Retrieval Criteria (corrected)` | `R1`
   - Cut-off date: 31 July 2025.

## Full proposed new file contents

# Proposed new contents for `cutoff_jsons/README.md`


```md
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
```


# Proposed new contents for `cutoff_jsons/2303.13365.json`


```json
{
  "paper_id": "2303.13365",
  "source_md": "criteria_mds/2303.13365.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_window",
    "enabled": true,
    "date_field": "published",
    "start_date": "2012-01-01",
    "start_inclusive": true,
    "end_date": "2022-03-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i1"
    ]
  },
  "time_clauses": [
    {
      "clause_id": "stage2_i1",
      "stage": "stage2",
      "scope": "screening",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2012-01-01",
      "start_inclusive": true,
      "end_date": "2022-03-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Month-level bounds normalized to the first day of January 2012 and the last day of March 2022."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2012-01-01",
    "start_inclusive": true,
    "end_date": "2022-03-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage2_i1"
    ],
    "binding_clause_ids": [
      "stage2_i1"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage2_i1",
      "section": "Stage 2 Screening Criteria",
      "criterion_id": "I1",
      "text": "Published between January 2012 and March 2022.",
      "source": "criteria_mds/2303.13365.md"
    }
  ],
  "normalization_notes": [
    "This paper has a direct Stage 2 screening-time window; no fallback is needed.",
    "Because the only projectable clause is Stage 2 I1, the operational time_policy is identical to the source-faithful screening policy."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2306.12834.json`


```json
{
  "paper_id": "2306.12834",
  "source_md": "criteria_mds/2306.12834.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": false,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": []
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r1",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2016-01-01",
      "start_inclusive": true,
      "end_date": "2022-12-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Stage 1 search period is operationalized as a publication-date window because the one-shot prefilter applies all projectable time bounds up front."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2016-01-01",
    "start_inclusive": true,
    "end_date": "2022-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r1"
    ],
    "binding_clause_ids": [
      "stage1_r1"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r1",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R1",
      "text": "Search period: 2016–2022.",
      "source": "criteria_mds/2306.12834.md"
    }
  ],
  "normalization_notes": [
    "The paper does not state a publication-time screening rule in Stage 2.",
    "Under the proposed cutoff_jsons semantics, the Stage 1 retrieval period is still projected into time_policy because the program applies the intersection of projectable hard time clauses before later-stage review."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2307.05527.json`


```json
{
  "paper_id": "2307.05527",
  "source_md": "criteria_corrected_3papers/2307.05527.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_window",
    "enabled": true,
    "date_field": "published",
    "start_date": "2018-02-01",
    "start_inclusive": true,
    "end_date": "2023-02-01",
    "end_inclusive": true,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i5"
    ]
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r2",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2018-02-01",
      "start_inclusive": true,
      "end_date": "2023-02-01",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The paper explicitly states that the search-space definition uses the same lower and upper date bounds as the eligibility window."
    },
    {
      "clause_id": "stage2_i5",
      "stage": "stage2",
      "scope": "screening",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2018-02-01",
      "start_inclusive": true,
      "end_date": "2023-02-01",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "This is the literal source-faithful screening-time window."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2018-02-01",
    "start_inclusive": true,
    "end_date": "2023-02-01",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r2",
      "stage2_i5"
    ],
    "binding_clause_ids": [
      "stage1_r2",
      "stage2_i5"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r2",
      "section": "Stage 1 Retrieval / Search-space definition",
      "criterion_id": "R2",
      "text": "Temporal window (search and eligibility window): 2018-02-01 to 2023-02-01.",
      "source": "criteria_corrected_3papers/2307.05527.md"
    },
    {
      "clause_id": "stage2_i5",
      "section": "Stage 2 Eligibility / Screening Criteria",
      "criterion_id": "I5",
      "text": "Temporal window: submitted/published within 2018-02-01 to 2023-02-01.",
      "source": "criteria_corrected_3papers/2307.05527.md"
    }
  ],
  "normalization_notes": [
    "This file already encoded the correct window numerically, but the revised schema now records both the Stage 1 and Stage 2 clauses explicitly.",
    "Because the retrieval and screening windows are identical, the operational intersection is unchanged."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2310.07264.json`


```json
{
  "paper_id": "2310.07264",
  "source_md": "criteria_mds/2310.07264.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": false,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": []
  },
  "time_clauses": [
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "stage": "fallback",
      "scope": "fallback",
      "kind": "sr_publication_date_upper_bound",
      "hardness": "fallback",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2023-10-11",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "No explicit time clause was extracted from the paper. The one-shot pipeline records the SR's own publication date as the fallback upper bound."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": "2023-10-11",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "operational_fallback_sr_publication_date"
    ],
    "binding_clause_ids": [
      "operational_fallback_sr_publication_date"
    ],
    "fallback_applied": true
  },
  "evidence": [
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "section": "Operational fallback",
      "criterion_id": "N/A",
      "text": "No explicit publication-time restriction in criteria. Applied the review paper's own publication date as the upper bound: 2023-10-11T07:40:46Z in refs/2310.07264/metadata.json.",
      "source": "cutoff_jsons/2310.07264.json"
    }
  ],
  "normalization_notes": [
    "There is no extracted Stage 1 or Stage 2 publication-time rule in the repo criteria file.",
    "The fallback remains necessary if the program requires a deterministic upper bound for early time-based prefiltering."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2312.05172.json`


```json
{
  "paper_id": "2312.05172",
  "source_md": "criteria_mds/2312.05172.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_window",
    "enabled": true,
    "date_field": "published",
    "start_date": "2000-01-01",
    "start_inclusive": true,
    "end_date": "2025-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i1"
    ]
  },
  "time_clauses": [
    {
      "clause_id": "stage2_i1",
      "stage": "stage2",
      "scope": "screening",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2000-01-01",
      "start_inclusive": true,
      "end_date": "2025-12-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Year-only bounds were normalized to a full-year inclusive range."
    },
    {
      "clause_id": "stage2_e4",
      "stage": "stage2",
      "scope": "screening",
      "kind": "conditional_time_citation_rule",
      "hardness": "conditional",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": "publication_year < 2017 AND citation_count < 10",
      "notes": "This rule is time-related but cannot be collapsed into a single global publication window because it depends jointly on publication year and citation count."
    },
    {
      "clause_id": "stage1_r13",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "per_year_record_cap",
      "hardness": "hard",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Limit screening to the first 300 records in each database for years 2000–2022.",
      "details": {
        "year_range": "2000-2022",
        "per_database_limit": 300
      }
    },
    {
      "clause_id": "stage1_r14",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "per_year_record_cap",
      "hardness": "hard",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Limit screening to 30 records per database for years 2023–2025.",
      "details": {
        "year_range": "2023-2025",
        "per_database_limit": 30
      }
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2000-01-01",
    "start_inclusive": true,
    "end_date": "2025-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage2_i1"
    ],
    "binding_clause_ids": [
      "stage2_i1"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage2_i1",
      "section": "Stage 2 Screening Criteria",
      "criterion_id": "I1",
      "text": "Publication date between 2000 and 2025.",
      "source": "criteria_mds/2312.05172.md"
    },
    {
      "clause_id": "stage2_e4",
      "section": "Stage 2 Screening Criteria",
      "criterion_id": "E4",
      "text": "For studies published prior to 2017: has fewer than 10 citations in total.",
      "source": "criteria_mds/2312.05172.md"
    },
    {
      "clause_id": "stage1_r13",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R13",
      "text": "For years 2000–2022: limit screening to the first 300 records in each database.",
      "source": "criteria_mds/2312.05172.md"
    },
    {
      "clause_id": "stage1_r14",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R14",
      "text": "For years 2023–2025: limit screening to 30 records per database (no relevant results found beyond this threshold).",
      "source": "criteria_mds/2312.05172.md"
    }
  ],
  "warnings": [
    "The extracted criteria use a forward upper bound of 2025 even though the arXiv identifier begins with 2312; keep the repo-extracted value for deterministic reproduction, but manual paper verification is recommended if chronology matters."
  ],
  "normalization_notes": [
    "Only Stage 2 I1 can be projected to a global publication-date window.",
    "The citation rule (E4) and per-year record caps (R13/R14) must be preserved as non-window time logic; they should not be silently dropped."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2401.09244.json`


```json
{
  "paper_id": "2401.09244",
  "source_md": "criteria_mds/2401.09244.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": false,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": []
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r1",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "search_execution_date_projection",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2023-07-29",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The paper states that the search was conducted on July 29, 2023. In the one-shot prefilter, this is projected to an upper bound on publication date."
    },
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "stage": "fallback",
      "scope": "fallback",
      "kind": "sr_publication_date_upper_bound",
      "hardness": "fallback",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2024-01-17",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Fallback to the SR's own publication date. This clause is kept for auditability but is looser than the search-execution upper bound."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": "2023-07-29",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r1",
      "operational_fallback_sr_publication_date"
    ],
    "binding_clause_ids": [
      "stage1_r1"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r1",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R1",
      "text": "Search conducted on July 29, 2023.",
      "source": "criteria_mds/2401.09244.md"
    },
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "section": "Operational fallback",
      "criterion_id": "N/A",
      "text": "No explicit publication-time restriction in criteria. Applied the review paper's own publication date as the upper bound: 2024-01-17T14:44:27Z in refs/2401.09244/metadata.json.",
      "source": "cutoff_jsons/2401.09244.json"
    }
  ],
  "normalization_notes": [
    "This is a substantive correction relative to the current file: the existing JSON only records the fallback upper bound, but misses the tighter search-execution date.",
    "Under the proposed semantics, the final time_policy uses the intersection of all projectable clauses, so the binding upper bound becomes 2023-07-29, not 2024-01-17."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2405.15604.json`


```json
{
  "paper_id": "2405.15604",
  "source_md": "criteria_mds/2405.15604.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_window",
    "enabled": true,
    "date_field": "published",
    "start_date": "2017-01-01",
    "start_inclusive": true,
    "end_date": "2023-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i1"
    ]
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r3",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_lower_bound",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2017-01-01",
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Stage 1 retrieval excludes papers from 2016 or older."
    },
    {
      "clause_id": "stage1_r5",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "per_year_top_k_sampling",
      "hardness": "hard",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "To even out yearly coverage, the review samples the top 5 papers per query and year by influential citations.",
      "details": {
        "per_query_per_year_top_k": 5
      }
    },
    {
      "clause_id": "stage1_r6",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "conditional_time_citation_rule",
      "hardness": "conditional",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": "publication_year <= 2021 AND influential_citations >= 2",
      "notes": "This rule applies only to papers up to and including 2021."
    },
    {
      "clause_id": "stage1_r7",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "time_condition_relaxation",
      "hardness": "descriptive",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "For years 2022 and 2023, the citation threshold is relaxed and papers with fewer than two influential citations are not removed."
    },
    {
      "clause_id": "stage2_i1",
      "stage": "stage2",
      "scope": "screening",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2017-01-01",
      "start_inclusive": true,
      "end_date": "2023-12-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Manual assessment for relevance is restricted to candidate works within 2017 to 2023."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2017-01-01",
    "start_inclusive": true,
    "end_date": "2023-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r3",
      "stage2_i1"
    ],
    "binding_clause_ids": [
      "stage1_r3",
      "stage2_i1"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r3",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R3",
      "text": "Temporal filter: exclude papers from 2016 or older (i.e., focus on publications from 2017 onwards).",
      "source": "criteria_mds/2405.15604.md"
    },
    {
      "clause_id": "stage1_r5",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R5",
      "text": "To even out yearly coverage, sample the top 5 papers per query and year by influential citations.",
      "source": "criteria_mds/2405.15604.md"
    },
    {
      "clause_id": "stage1_r6",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R6",
      "text": "For papers up to (and including) year 2021: exclude papers with fewer than 2 citations (as stated in the pipeline figure).",
      "source": "criteria_mds/2405.15604.md"
    },
    {
      "clause_id": "stage1_r7",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R7",
      "text": "For years 2022 and 2023: relax restrictions and do not remove papers with less than two influential citations.",
      "source": "criteria_mds/2405.15604.md"
    },
    {
      "clause_id": "stage2_i1",
      "section": "Stage 2 Screening Criteria",
      "criterion_id": "I1",
      "text": "Manually assessed candidate works are within years 2017 to 2023 (titles and abstracts manually assessed for relevance).",
      "source": "criteria_mds/2405.15604.md"
    }
  ],
  "normalization_notes": [
    "The current file already lands on the right global window, but it drops important non-window time logic: per-year top-k balancing and year-conditioned citation thresholds.",
    "The revised file keeps those clauses explicit so Codex can choose whether to implement them later."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2407.17844.json`


```json
{
  "paper_id": "2407.17844",
  "source_md": "criteria_mds/2407.17844.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": false,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": []
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r1",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "search_execution_date_projection",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2024-04-30",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The search is reported as having been performed in April 2024. Month-only search execution is normalized to the month-end upper bound for publication-date projection."
    },
    {
      "clause_id": "stage1_r5",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_lower_bound",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2020-01-01",
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The Stage 1 year filter keeps studies from 2020 onwards."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2020-01-01",
    "start_inclusive": true,
    "end_date": "2024-04-30",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r1",
      "stage1_r5"
    ],
    "binding_clause_ids": [
      "stage1_r1",
      "stage1_r5"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r1",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R1",
      "text": "Search performed in April 2024.",
      "source": "criteria_mds/2407.17844.md"
    },
    {
      "clause_id": "stage1_r5",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R5",
      "text": "Year filter: 2020 onwards.",
      "source": "criteria_mds/2407.17844.md"
    }
  ],
  "normalization_notes": [
    "This is another substantive correction relative to the current file: the existing JSON keeps only the lower bound and misses the effective upper bound implied by the search month.",
    "Using 2024-04-30 is an operational projection of the latest possible date inside the reported search month; if you later want a stricter interpretation, this can be replaced by a separate exact search timestamp when available."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2409.13738.json`


```json
{
  "paper_id": "2409.13738",
  "source_md": "criteria_corrected_3papers/2409.13738.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_no_publication_restriction",
    "enabled": false,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i8_no_publication_restriction"
    ],
    "notes": "The paper explicitly says there is no publication-year restriction in the screening criteria."
  },
  "time_clauses": [
    {
      "clause_id": "stage2_i8_no_publication_restriction",
      "stage": "stage2",
      "scope": "screening",
      "kind": "explicit_no_publication_restriction",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "This contributes the universal interval and therefore does not tighten the intersection."
    },
    {
      "clause_id": "paper_results_search_executed_june_2023",
      "stage": "paper_results",
      "scope": "retrieval",
      "kind": "search_execution_date_projection",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2023-06-30",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The paper states that search queries were executed in June 2023. For the one-shot publication-time prefilter, month-only search execution is projected to a month-end upper bound."
    },
    {
      "clause_id": "paper_results_observed_corpus_span",
      "stage": "paper_results",
      "scope": "descriptive",
      "kind": "observed_included_corpus_span",
      "hardness": "descriptive",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": "2011-01-01",
      "start_inclusive": true,
      "end_date": "2023-12-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Descriptive span of found/reviewed papers; kept for audit but not used as an independent window because it is an observed outcome rather than a primary rule."
    },
    {
      "clause_id": "paper_methods_same_contribution_latest_version",
      "stage": "paper_methods",
      "scope": "screening",
      "kind": "same_contribution_latest_version_rule",
      "hardness": "conditional",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "If multiple papers relate to the same contribution, the review keeps the most recent paper. This is time-related but cannot be collapsed into a single global publication-date window."
    },
    {
      "clause_id": "paper_limitations_manuscript_horizon_aug_2024",
      "stage": "paper_limitations",
      "scope": "reporting",
      "kind": "manuscript_horizon_upper_bound",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2024-08-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The paper states that publications after the preparation of the manuscript (August 2024) will not be included. This is recorded as a looser upper bound than the search-execution date."
    },
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "stage": "fallback",
      "scope": "fallback",
      "kind": "sr_publication_date_upper_bound",
      "hardness": "fallback",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2024-09-10",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Fallback to the SR's own arXiv publication date. It remains non-binding because the June 2023 search-execution upper bound is tighter."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": "2023-06-30",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage2_i8_no_publication_restriction",
      "paper_results_search_executed_june_2023",
      "paper_limitations_manuscript_horizon_aug_2024",
      "operational_fallback_sr_publication_date"
    ],
    "binding_clause_ids": [
      "paper_results_search_executed_june_2023"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage2_i8_no_publication_restriction",
      "section": "Stage 2 Eligibility / Screening Criteria",
      "criterion_id": "I8",
      "text": "No publication-year restriction (i.e., do not exclude by year).",
      "source": "criteria_corrected_3papers/2409.13738.md"
    },
    {
      "clause_id": "paper_results_search_executed_june_2023",
      "section": "Results",
      "criterion_id": "N/A",
      "text": "Our search queries were executed in June 2023 and the found papers span a time period from 2011 to 2023.",
      "source": "paper: arxiv html 2409.13738v1"
    },
    {
      "clause_id": "paper_results_observed_corpus_span",
      "section": "Results / Table 2 metadata",
      "criterion_id": "N/A",
      "text": "From 2011 to 2023.",
      "source": "paper: arxiv html 2409.13738v1"
    },
    {
      "clause_id": "paper_methods_same_contribution_latest_version",
      "section": "Methods / Inclusion Criteria footnote",
      "criterion_id": "IC.2 footnote",
      "text": "In case of multiple papers related to the same contribution, we reviewed the most recent paper.",
      "source": "paper: arxiv html 2409.13738v1"
    },
    {
      "clause_id": "paper_limitations_manuscript_horizon_aug_2024",
      "section": "Threats to Validity and Limitations",
      "criterion_id": "N/A",
      "text": "Publications after the preparation of this manuscript (August 2024) will also not be included.",
      "source": "paper: arxiv html 2409.13738v1"
    },
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "section": "Operational fallback",
      "criterion_id": "N/A",
      "text": "Fallback upper bound uses the SR's own arXiv publication date (2024-09-10).",
      "source": "paper: arxiv abs metadata"
    }
  ],
  "normalization_notes": [
    "This is the most important correction in the whole folder. The current file disables time filtering entirely because it follows the source-faithful Stage 2 rule only.",
    "For the lazy one-shot prefilter you described, that is too weak: the June 2023 search-execution date is a real time constraint on the candidate pool and therefore must be projected into time_policy.",
    "The August 2024 manuscript horizon and the SR publication-date fallback are kept for completeness, but neither is binding once the June 2023 clause is included.",
    "The explicit 'no publication-year restriction' is still preserved under source_faithful_screening_publication_policy, so the file now cleanly records both the paper-literal rule and your operational prefilter."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2503.04799.json`


```json
{
  "paper_id": "2503.04799",
  "source_md": "criteria_mds/2503.04799.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_window",
    "enabled": true,
    "date_field": "published",
    "start_date": "2016-01-01",
    "start_inclusive": true,
    "end_date": "2024-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i2"
    ]
  },
  "time_clauses": [
    {
      "clause_id": "stage2_i2",
      "stage": "stage2",
      "scope": "screening",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2016-01-01",
      "start_inclusive": true,
      "end_date": "2024-12-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Year-only bounds normalized to a full-year inclusive range."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2016-01-01",
    "start_inclusive": true,
    "end_date": "2024-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage2_i2"
    ],
    "binding_clause_ids": [
      "stage2_i2"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage2_i2",
      "section": "Stage 2 Screening Criteria",
      "criterion_id": "I2",
      "text": "Published between 2016 and 2024.",
      "source": "criteria_mds/2503.04799.md"
    }
  ],
  "normalization_notes": [
    "This file only needs schema expansion; the numeric window is already correct."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2507.07741.json`


```json
{
  "paper_id": "2507.07741",
  "source_md": "criteria_mds/2507.07741.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_window",
    "enabled": true,
    "date_field": "published",
    "start_date": "2018-01-01",
    "start_inclusive": true,
    "end_date": "2024-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i3"
    ]
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r3",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2014-01-01",
      "start_inclusive": true,
      "end_date": "2025-02-27",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Stage 1 retrieval publication-date range."
    },
    {
      "clause_id": "stage2_i3",
      "stage": "stage2",
      "scope": "screening",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2018-01-01",
      "start_inclusive": true,
      "end_date": "2024-12-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The final analysis set focuses on papers published between 2018 and 2024."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2018-01-01",
    "start_inclusive": true,
    "end_date": "2024-12-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r3",
      "stage2_i3"
    ],
    "binding_clause_ids": [
      "stage2_i3"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r3",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R3",
      "text": "Retrieval publication-date range: 2014 until February 27, 2025.",
      "source": "criteria_mds/2507.07741.md"
    },
    {
      "clause_id": "stage2_i3",
      "section": "Stage 2 Screening Criteria",
      "criterion_id": "I3",
      "text": "Analysis set focuses on papers published between 2018 and 2024 (the resulting eligible set for analysis).",
      "source": "criteria_mds/2507.07741.md"
    }
  ],
  "normalization_notes": [
    "The current JSON reaches the same numeric result by Stage-2 priority. The revised file records the stronger derivation explicitly as an intersection of Stage 1 and Stage 2 windows.",
    "Stage 2 I3 is binding because it tightens both the lower and the upper bound."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2507.18910.json`


```json
{
  "paper_id": "2507.18910",
  "source_md": "criteria_mds/2507.18910.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": null,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage1_r6"
    ],
    "notes": "No explicit publication-time eligibility rule is stated in the final screening criteria. The usable window appears in the retrieval criteria."
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r6",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2017-01-01",
      "start_inclusive": true,
      "end_date": "2025-06-30",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The review searches papers from 2017 to the end of mid-2025. The phrase 'end of mid-2025' is normalized to 2025-06-30 for deterministic execution."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2017-01-01",
    "start_inclusive": true,
    "end_date": "2025-06-30",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r6"
    ],
    "binding_clause_ids": [
      "stage1_r6"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r6",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R6",
      "text": "Publication year from 2017 to end of mid-2025.",
      "source": "criteria_mds/2507.18910.md"
    }
  ],
  "normalization_notes": [
    "The current JSON already captures the numeric window correctly; the main revision is schema expansion and clearer documentation that this is a retrieval-stage window rather than an explicit Stage 2 eligibility rule.",
    "The phrase 'end of mid-2025' is normalized to 2025-06-30."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2509.11446.json`


```json
{
  "paper_id": "2509.11446",
  "source_md": "criteria_mds/2509.11446.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": null,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": [],
    "notes": "No explicit publication-time constraint appears in the extracted criteria."
  },
  "time_clauses": [
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "stage": "fallback",
      "scope": "fallback",
      "kind": "sr_publication_date_upper_bound",
      "hardness": "fallback",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2025-09-14",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "No explicit time clause was found in the criteria, so the operational fallback uses the SR's own arXiv publication date as the upper bound."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": "2025-09-14",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "operational_fallback_sr_publication_date"
    ],
    "binding_clause_ids": [
      "operational_fallback_sr_publication_date"
    ],
    "fallback_applied": true
  },
  "evidence": [
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "section": "Operational fallback",
      "criterion_id": "N/A",
      "text": "Fallback upper bound uses the SR's own arXiv publication date (2025-09-14).",
      "source": "paper: arxiv abs metadata"
    }
  ],
  "normalization_notes": [
    "This file still needs fallback because the current extracted criteria do not contain any projectable time clause.",
    "The fallback is intentionally weak and should be replaced if a future criteria correction file adds a search date or an explicit publication window."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2510.01145.json`


```json
{
  "paper_id": "2510.01145",
  "source_md": "criteria_mds/2510.01145.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "explicit_window",
    "enabled": true,
    "date_field": "published",
    "start_date": "2020-01-01",
    "start_inclusive": true,
    "end_date": "2025-07-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage2_i2"
    ],
    "notes": "The paper states the same publication window in both retrieval and screening criteria."
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r7",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2020-01-01",
      "start_inclusive": true,
      "end_date": "2025-07-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Retrieval window from January 2020 through July 2025."
    },
    {
      "clause_id": "stage2_i2",
      "stage": "stage2",
      "scope": "screening",
      "kind": "publication_window",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2020-01-01",
      "start_inclusive": true,
      "end_date": "2025-07-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Screening eligibility repeats the same window as Stage 1."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2020-01-01",
    "start_inclusive": true,
    "end_date": "2025-07-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r7",
      "stage2_i2"
    ],
    "binding_clause_ids": [
      "stage1_r7",
      "stage2_i2"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r7",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R7",
      "text": "Published from January 2020 to July 2025.",
      "source": "criteria_mds/2510.01145.md"
    },
    {
      "clause_id": "stage2_i2",
      "section": "Stage 2 Eligibility / Screening Criteria",
      "criterion_id": "I2",
      "text": "Published from January 2020 to July 2025.",
      "source": "criteria_mds/2510.01145.md"
    }
  ],
  "normalization_notes": [
    "The current JSON already has the right numeric window.",
    "The revised file makes the duplication explicit so Codex can see that Stage 1 and Stage 2 agree rather than inferring a hidden priority rule."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2511.13936.json`


```json
{
  "paper_id": "2511.13936",
  "source_md": "criteria_mds/2511.13936.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": null,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage1_r3"
    ],
    "notes": "No explicit Stage 2 publication window is stated, but the retrieval criteria impose a global lower bound from 2020 onward."
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r3",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_lower_bound",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": "2020-01-01",
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The review includes papers published from 2020 onward."
    },
    {
      "clause_id": "stage1_r6",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "conditional_time_citation_rule",
      "hardness": "conditional",
      "project_to_time_policy": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "applies_to_subset": "arxiv_only",
      "conditional_on": null,
      "notes": "For arXiv papers only, the review further requires year-specific citation thresholds. This is time-related but cannot be collapsed into one global publication-date window.",
      "details": {
        "per_year_minimum_citations": {
          "2020": 28,
          "2021": 22,
          "2022": 32,
          "2023": 90,
          "2024": 13,
          "2025": 1
        }
      }
    },
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "stage": "fallback",
      "scope": "fallback",
      "kind": "sr_publication_date_upper_bound",
      "hardness": "fallback",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2025-11-17",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "Because no explicit upper bound is stated in the criteria, the operational fallback uses the SR's own arXiv publication date."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": "2020-01-01",
    "start_inclusive": true,
    "end_date": "2025-11-17",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r3",
      "operational_fallback_sr_publication_date"
    ],
    "binding_clause_ids": [
      "stage1_r3",
      "operational_fallback_sr_publication_date"
    ],
    "fallback_applied": true
  },
  "evidence": [
    {
      "clause_id": "stage1_r3",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R3",
      "text": "Published from 2020 onward.",
      "source": "criteria_mds/2511.13936.md"
    },
    {
      "clause_id": "stage1_r6",
      "section": "Stage 1 Retrieval Criteria",
      "criterion_id": "R6",
      "text": "For arXiv papers, the citation count must meet year-specific thresholds (2020: 28, 2021: 22, 2022: 32, 2023: 90, 2024: 13, 2025: 1).",
      "source": "criteria_mds/2511.13936.md"
    },
    {
      "clause_id": "operational_fallback_sr_publication_date",
      "section": "Operational fallback",
      "criterion_id": "N/A",
      "text": "Fallback upper bound uses the SR's own arXiv publication date (2025-11-17).",
      "source": "paper: arxiv abs metadata"
    }
  ],
  "normalization_notes": [
    "The current JSON already gives the same window [2020-01-01, 2025-11-17], but it does not record the arXiv-only year-by-year citation gates that materially affect retrieval.",
    "Those citation thresholds are subset-specific and non-window-like, so they stay in time_clauses with project_to_time_policy=false."
  ]
}
```


# Proposed new contents for `cutoff_jsons/2601.19926.json`


```json
{
  "paper_id": "2601.19926",
  "source_md": "criteria_corrected_3papers/2601.19926.md",
  "schema_version": "3.0",
  "source_faithful_screening_publication_policy": {
    "status": "not_explicitly_stated",
    "enabled": null,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": null,
    "end_inclusive": false,
    "timezone": "UTC",
    "evidence_clause_ids": [
      "stage1_r1"
    ],
    "notes": "The corrected criteria state only an upper cut-off date and do not add a separate Stage 2 publication window."
  },
  "time_clauses": [
    {
      "clause_id": "stage1_r1",
      "stage": "stage1",
      "scope": "retrieval",
      "kind": "publication_upper_bound",
      "hardness": "hard",
      "project_to_time_policy": true,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": "2025-07-31",
      "end_inclusive": true,
      "applies_to_subset": null,
      "conditional_on": null,
      "notes": "The corrected criteria state a cut-off date of July 31, 2025."
    }
  ],
  "time_policy": {
    "enabled": true,
    "date_field": "published",
    "start_date": null,
    "start_inclusive": true,
    "end_date": "2025-07-31",
    "end_inclusive": true,
    "timezone": "UTC",
    "derivation_mode": "intersection_of_projectable_time_clauses",
    "projected_clause_ids": [
      "stage1_r1"
    ],
    "binding_clause_ids": [
      "stage1_r1"
    ],
    "fallback_applied": false
  },
  "evidence": [
    {
      "clause_id": "stage1_r1",
      "section": "Stage 1 Retrieval Criteria (corrected)",
      "criterion_id": "R1",
      "text": "Cut-off date: 31 July 2025.",
      "source": "criteria_corrected_3papers/2601.19926.md"
    }
  ],
  "normalization_notes": [
    "The current JSON already captures the corrected cut-off date correctly.",
    "The revised file mainly upgrades the schema so the file is consistent with the rest of the folder."
  ]
}
```

