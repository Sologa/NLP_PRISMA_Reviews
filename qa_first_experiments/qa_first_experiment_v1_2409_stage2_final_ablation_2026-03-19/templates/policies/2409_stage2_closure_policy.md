# 2409 Stage 2 Final Ablation Policy

Applies only to:

- `paper_id = 2409.13738`
- `stage = stage2`
- `arm = qa+synthesis`

This is a workflow-layer ablation note. It does not rewrite the formal criteria.

## Focus

- Isolate publication-form closure from the prior over-tight target-boundary wording.
- Keep publication-form, target-family, primary-research, concrete-method, and empirical-validation judgments separate.

## Closure Rules

- Do not let strong method or validation evidence erase an explicit failure on publication form.
- Do not use broad BPM relevance by itself as positive target evidence.
- But do not create a new direct negative merely because a paper also discusses adjacent BPM, IE, or LLM tasks.
- If the supplied evidence directly shows extracting process knowledge, process models, declarative constraints, or related process structure from natural-language text, keep target fit open and let the criterion evidence decide.
- Multi-task framing alone is not a contradiction.
- Auxiliary, upstream, downstream, or incidental wording alone is not enough for direct negative target evidence unless the paper explicitly states that process extraction or process-model generation is outside the actual contribution or evaluation.

## Publication-Form Handling

- If the full text or metadata explicitly identifies the work as an `arXiv` preprint, non-peer-reviewed preprint, or otherwise outside a peer-reviewed conference or journal article, treat that as direct negative evidence for publication-form closure.
- Do not downgrade that explicit publication-form conflict into a minor deferred detail.
- Book-chapter or edited-volume wording alone is not enough to create direct negative evidence unless the supplied evidence also explicitly shows non-peer-reviewed or otherwise non-eligible publication status.

## Output Discipline

- Preserve closure disagreements as separate field records or criterion mappings instead of merging them into a blanket include.
- If publication form is explicit direct negative, keep it in `direct_negative_evidence_ids`.
- If target-boundary remains uncertain but not contradicted, keep it unresolved or evidence-bound rather than converting it into direct negative.
- If publication form is explicitly disqualifying, keep it in `direct_negative_evidence_ids` and do not present the case as clean include.
