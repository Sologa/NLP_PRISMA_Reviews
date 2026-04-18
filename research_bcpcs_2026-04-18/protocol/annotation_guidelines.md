# Annotation Guidelines

## Annotation Units

Annotate claim-level evidence, not only final verdicts.

Each row should answer:

- Which candidate is being reviewed?
- Which stage is being evaluated?
- Which claim is being assessed?
- Does the cited span support, refute, or fail to resolve the claim?
- Is the quote exact and locatable?
- Does the verdict follow from the ledger?

## Evidence Status Labels

- `support`: the span directly supports the claim.
- `refute`: the span directly contradicts the claim or triggers an exclusion.
- `unknown`: the available input does not resolve the claim.
- `not_applicable`: the claim is not active for this stage or candidate.

## Missingness Reasons

Use one reason when `evidence_status` is `unknown`:

- `not_observable_stage1`
- `fulltext_missing`
- `metadata_ambiguous`
- `retrieval_failure`
- `evidence_incomplete`
- `criteria_gold_tension`
- `semantic_nonfit`

## Span Validation

A valid span must have:

- exact quote;
- source field or path;
- location string;
- enough context to verify support or refutation.

Reject spans that:

- only repeat the criterion;
- are topic-adjacent but not claim-specific;
- quote review-level language instead of candidate evidence;
- support a different claim than the ledger row says.

## Verdict Validation

The verdict is valid only if:

- every decisive inclusion claim is supported or appropriately deferred;
- no active refutation claim is ignored;
- Stage 1 unknown is not treated as Stage 2 exclusion;
- routed cases are counted as routed, not silently automated;
- cutoff-failed rows remain authoritative excludes.

