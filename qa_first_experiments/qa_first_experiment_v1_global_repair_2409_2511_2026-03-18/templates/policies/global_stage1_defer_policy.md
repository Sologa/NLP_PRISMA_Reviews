## Global Stage 1 Defer Policy

- Stage 1 is a partial-observability gate, not a full semantic closure step.
- Use `absent` only when the available Stage 1 evidence directly shows non-fit, contradiction, or a direct exclusion signal.
- Use `unclear` when the abstract/title does not fully expose a core condition but remains plausibly compatible with inclusion.
- A Stage 1 evaluator score of `1` or `2` requires direct negative evidence or a clear absence of core fit.
- If `unresolved_core_evidence_ids` is non-empty and `direct_negative_evidence_ids` is empty, default to `stage_score = 3` and route to `SeniorLead`.
- Do not treat short abstracts, incomplete mechanism descriptions, or deferred full-text-only closure as standalone exclusion evidence.
