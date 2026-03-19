# 2409 Stage 2 Closure Follow-up Policy

Applies only to:

- `paper_id = 2409.13738`
- `stage = stage2`
- `arm = qa+synthesis`

This is a workflow-layer follow-up note. It does not rewrite the formal criteria.

## Focus

- Stabilize Stage 2 closure for candidates that show plausible process-extraction or process-modeling fit from natural-language text.
- Keep target-boundary, publication-form, primary-research, concrete-method, and empirical-validation judgments separate.

## Closure Rules

- Do not let strong method or validation evidence erase an explicit failure on target family or publication form.
- Do not treat generic BPM relevance, generic LLM usefulness, or generic information extraction as sufficient target fit by themselves.
- A paper is not target-satisfied merely because it helps an upstream or downstream subtask. The central contribution must itself address extracting or generating process models from natural-language text.
- When a paper presents several BPM tasks, treat process extraction/model generation as satisfied only if it is a principal evaluated task, not just one incidental demonstration among broader BPM capabilities.

## Publication-Form Handling

- If the full text or metadata explicitly identifies the work as an `arXiv` preprint, non-peer-reviewed preprint, or otherwise outside a peer-reviewed conference or journal article, treat that as direct negative evidence for publication-form closure.
- Do not downgrade that explicit publication-form conflict into a minor deferred detail.
- Book-chapter or edited-volume wording alone is not enough to create direct negative evidence unless the supplied evidence also explicitly shows non-peer-reviewed or otherwise non-eligible publication status.

## Output Discipline

- Preserve closure disagreements as separate field records or criterion mappings instead of merging them into a blanket include.
- If target fit remains only auxiliary, broad, or incidental, record that as not satisfied or unresolved on the target criterion even when method and evaluation are strong.
- If publication form is explicitly disqualifying, keep it in `direct_negative_evidence_ids` and do not present the case as clean include.
