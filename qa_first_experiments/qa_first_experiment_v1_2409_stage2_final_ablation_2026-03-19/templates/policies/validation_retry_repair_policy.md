## Validation Retry Repair Policy

- The previous attempt failed validator checks. Correct the specific invalid pattern instead of repeating the same structure.
- If the failure says `Stage 1 score 3 cannot keep direct negative evidence ids`, either:
  - remove those ids from `direct_negative_evidence_ids` and support a genuine unresolved-positive defer with `positive_fit_evidence_ids`, or
  - keep the direct negative evidence and change the score to `1` or `2`.
- If the failure says `Stage 1 score 3 requires positive fit evidence`, do not use `3` unless `positive_fit_evidence_ids` is non-empty.
- If the failure says `Stage 1 score 3 requires unresolved or deferred core evidence`, do not use `3` unless unresolved or deferred closure truly remains.
- If the failure says a review-level phrase leaked, remove the exact protected literal and paraphrase or cite candidate evidence without repeating that literal.
- Return one corrected JSON object that satisfies the stated validator failure. Do not argue with the validator inside the output.
