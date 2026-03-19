## Global Stage 1 Defer Policy

- Stage 1 is a partial-observability gate, not a full semantic closure step.
- Use `absent` only when the available Stage 1 evidence directly shows non-fit, contradiction, or a direct exclusion signal.
- Use `unclear` only when the title/abstract already supplies observable positive thematic fit or plausible core-fit, but the remaining closure is still incomplete.
- A Stage 1 evaluator score of `1` or `2` requires direct negative evidence or a clear absence of core fit.
- A Stage 1 evaluator score of `3` requires all of the following:
  - `positive_fit_evidence_ids` is non-empty
  - `direct_negative_evidence_ids` is empty
  - `unresolved_core_evidence_ids` or `deferred_core_evidence_ids` is non-empty
- If you keep any evidence id inside `direct_negative_evidence_ids`, you must not output `stage_score = 3`.
- Do not treat short abstracts, incomplete mechanism descriptions, or deferred full-text-only closure as standalone exclusion evidence.
- Do not treat missing detail by itself as positive unresolved fit.
- Do not treat loose lexical overlap alone as positive fit. Generic ranking, comparison, ordinal, rating, or preference terminology is insufficient if the core domain/object fit is absent or contradicted.
