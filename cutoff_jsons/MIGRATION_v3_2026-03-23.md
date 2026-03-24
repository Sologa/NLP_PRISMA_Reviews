# cutoff_jsons v3 Migration Notes

Date: 2026-03-23

This folder was replaced with the contents from:

- `docs/cutoff/cutoff_jsons_v3_proposed/`

The proposal source is:

- `docs/cutoff/nlp_prisma_cutoff_time_audit_v4_2026-03-23.md`

## What changed

The old `cutoff_jsons/*.json` files stored a single `time_policy` plus minimal evidence and notes.

The new v3 schema stores three separate layers:

1. `source_faithful_screening_publication_policy`
   - The paper-literal publication-time screening rule.
2. `time_clauses`
   - All extracted time-related clauses, including retrieval windows, search execution dates, manuscript horizons, fallback bounds, and non-window rules.
3. `time_policy`
   - The compiled, program-readable early prefilter used by the pipeline.

This means a file can now say both:

- the source-faithful screening rule has no explicit publication-time restriction; and
- the compiled early prefilter still has a binding upper bound because the paper reports a concrete search date.

## New derivation rule

`time_policy` is now derived as the intersection of all clauses in `time_clauses` that are:

- `project_to_time_policy = true`
- `hardness in {"hard", "fallback"}`

Operationally:

- `start_date` is the tightest lower bound among projected clauses.
- `end_date` is the tightest upper bound among projected clauses.
- `binding_clause_ids` records which clauses actually determine the final window.
- `fallback_applied` records whether an SR publication-date fallback remained necessary.

Non-window time logic is preserved in `time_clauses` but does not directly tighten `time_policy`. Examples:

- per-year citation thresholds
- per-year record caps
- per-year top-k sampling
- keep-most-recent-for-same-contribution rules
- descriptive observed corpus spans

## Files whose numeric `time_policy` changed

Only 3 of 16 papers changed the actual numeric `time_policy`.

1. `2401.09244`
   - old: `end_date = 2024-01-17`
   - new: `end_date = 2023-07-29`
   - reason: the reported search date is tighter than the old SR-publication fallback.

2. `2407.17844`
   - old: `2020-01-01 .. +inf`
   - new: `2020-01-01 .. 2024-04-30`
   - reason: the reported search month (`April 2024`) is now projected into an effective upper bound.

3. `2409.13738`
   - old: `enabled = false`
   - new: `end_date = 2023-06-30`
   - reason: source-faithful screening still says "no publication-year restriction", but the reported search execution month (`June 2023`) is now treated as a hard effective upper bound for the early compiled prefilter.

## Files whose numeric `time_policy` stayed the same

The remaining 13 papers keep the same numeric `time_policy`, but all of them gained richer audit structure.

### Explicit source-faithful screening windows

- `2303.13365`
- `2307.05527`
- `2312.05172`
- `2405.15604`
- `2503.04799`
- `2507.07741`
- `2510.01145`

These now explicitly separate:

- literal screening window
- all extracted time clauses
- compiled `time_policy`

### Not explicitly stated in screening, but compiled prefilter remains enabled

- `2306.12834`
- `2310.07264`
- `2401.09244`
- `2407.17844`
- `2507.18910`
- `2509.11446`
- `2511.13936`
- `2601.19926`

For these files, the important change is semantic:

- `source_faithful_screening_publication_policy` now records that no explicit Stage 2 screening publication window was stated, or that the usable time rule exists only in retrieval-stage material.
- `time_policy` may still remain enabled because the pipeline intentionally compiles retrieval/search/fallback clauses into a one-shot early prefilter.

## Important paper-specific notes

### `2312.05172`

The numeric window is unchanged, but the file now preserves:

- Stage 2 E4 citation-dependent time logic
- Stage 1 per-year record caps

These are stored in `time_clauses` as non-projectable or conditional rules.

### `2405.15604`

The numeric window is unchanged, but the file now preserves:

- Stage 1 lower bound
- per-year top-k sampling
- year-conditioned citation rules
- Stage 2 binding analysis window

### `2507.07741`

The numeric window is unchanged, but the file now records both:

- broader Stage 1 retrieval window
- tighter Stage 2 final analysis-set window

The derived `time_policy` is still bound by the tighter Stage 2 clause.

### `2511.13936`

The numeric window is unchanged, but the file now records:

- lower bound from Stage 1 retrieval scope (`2020 onward`)
- arXiv-only year-specific citation thresholds
- fallback SR publication-date upper bound

This is the clearest example of why `time_clauses` had to be introduced.

### `2409.13738`

This is the most important folder-wide correction.

The new file preserves both:

- `source_faithful_screening_publication_policy.enabled = false`
- compiled `time_policy.end_date = 2023-06-30`

This means:

- the paper-literal rule remains faithful; and
- the early pipeline prefilter still gets the real candidate-pool constraint implied by the search month.

## Per-paper migration summary

| Paper | Source-faithful status | Numeric `time_policy` changed? | Main migration effect |
| --- | --- | --- | --- |
| `2303.13365` | `explicit_window` | no | Schema expansion only; Stage 2 window remains binding. |
| `2306.12834` | `not_explicitly_stated` | no | Retrieval window remains compiled, but no longer pretends to be literal Stage 2 screening policy. |
| `2307.05527` | `explicit_window` | no | Adds explicit Stage 1 and Stage 2 clause tracking; same compiled window. |
| `2310.07264` | `not_explicitly_stated` | no | Fallback upper bound remains compiled, now explicit as fallback clause rather than implicit evidence shortcut. |
| `2312.05172` | `explicit_window` | no | Preserves citation-conditioned and per-year-cap logic in `time_clauses`. |
| `2401.09244` | `not_explicitly_stated` | yes | Search date overrides the looser SR-publication fallback. |
| `2405.15604` | `explicit_window` | no | Preserves top-k and citation-conditioned time logic. |
| `2407.17844` | `not_explicitly_stated` | yes | Search month adds a new effective upper bound. |
| `2409.13738` | `explicit_no_publication_restriction` | yes | Source-faithful rule stays open, but compiled prefilter gets a June 2023 upper bound. |
| `2503.04799` | `explicit_window` | no | Schema expansion only; Stage 2 window remains binding. |
| `2507.07741` | `explicit_window` | no | Records both retrieval and final analysis windows; Stage 2 remains binding. |
| `2507.18910` | `not_explicitly_stated` | no | Retrieval coverage window remains compiled with clearer provenance. |
| `2509.11446` | `not_explicitly_stated` | no | Fallback upper bound remains compiled with explicit fallback labeling. |
| `2510.01145` | `explicit_window` | no | Schema expansion only; Stage 2 window remains binding. |
| `2511.13936` | `not_explicitly_stated` | no | Preserves lower bound, fallback upper bound, and arXiv-only citation gates together. |
| `2601.19926` | `not_explicitly_stated` | no | Retrieval cutoff date remains compiled with clearer source-faithful separation. |

## Migration intent

This migration adopts the v3 proposal exactly as the new baseline inside `cutoff_jsons/`.

From this point forward:

- treat `cutoff_jsons/*.json` as a compiled time-logic layer, not as a plain natural-language summary;
- read `source_faithful_screening_publication_policy` when you want the literal paper-level rule;
- read `time_policy` when you want the executable early prefilter;
- inspect `time_clauses` when a paper contains time logic that does not collapse into one global publication-date interval.
