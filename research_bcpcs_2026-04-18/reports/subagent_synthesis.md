# Subagent Synthesis

This report summarizes the read-only subagent work used to ground the BCPCS scaffold. No subagent wrote files or modified production artifacts.

## Shared Conclusions

All subagents converged on the same central diagnosis:

- The current repository already uses stage-specific criteria and topic definitions.
- Title/abstract plus criteria plus definitions are necessary but insufficient for stable near-perfect screening.
- The missing layer is not another formal criteria rewrite. The missing layer is a stable evidence interface: typed criterion claims, support/refute spans, stage-aware missingness, calibrated routing, and auditable graph-derived verdicts.
- A universal "100% F1" claim is not defensible. The defensible claim is bounded-risk, proof-carrying screening with explicit coverage, routing, evidence quality, and residual uncertainty.

## Literature Review Agent

The literature review pass identified the relevant neighboring work:

- LLM screening can be strong, but direct prompt workflows show sensitivity/specificity tradeoffs and retrospective benchmark risks.
- QA-based abstract screening, especially Akinseloyin et al., supports criteria decomposition but does not by itself solve evidence localization or decision calculus.
- ASReview and TAR provide strong ranking/work-saving baselines but usually do not produce criterion-level proof objects.
- FEVER-style evidence verification supports the claim/evidence framing, but systematic-review eligibility has stage-specific observability and source-criteria constraints that generic fact verification does not model.
- Calibration, abstention, and human-in-the-loop adjudication are necessary to make high-recall screening deployable.

## Repo-Forensics Agent

The repo-forensics pass confirmed the current-state anchors:

- Current runtime prompts are in `scripts/screening/runtime_prompts/runtime_prompts.json`.
- Current production criteria are `criteria_stage1/<paper_id>.json` and `criteria_stage2/<paper_id>.json`.
- `criteria_jsons/*.json` are historical only.
- The current `2409.13738` combined authority is `0.7500`, not the older stale `0.8235` mention.
- Current residual errors are not uniform:
  - `2409.13738` is FP-heavy around target-object/process-extraction boundaries.
  - `2511.13936` has preference-learning versus evaluation-only boundary errors.
  - `2307.05527` is already strong and should not be destabilized.
  - `2601.19926` needs retrieval/failure-aware handling and should not be made globally stricter.

## Brainstorming Agent

The brainstorming pass shortlisted BCPCS as the most defensible conference framing:

1. Compile source-faithful criteria into typed eligibility claims.
2. Retrieve support and refute evidence for each claim.
3. Maintain a claim-level evidence ledger with quote, location, source field, confidence, and missingness.
4. Add a leakage-controlled counterfactual boundary atlas.
5. Route uncertain cases through SeniorLead/human adjudication.
6. Derive final verdicts from an auditable graph/lattice instead of free-form reasoning.

## Reviewer-Critique Agent

The reviewer-critique pass identified the highest-risk rejection points:

- "100% F1" reads as benchmark gaming unless reframed.
- Boundary atlas construction is a leakage risk unless split rules are frozen before evaluation.
- Typed claims can become hidden criteria rewriting if they encode operational hardening.
- Evidence quotes need independent span validation; quote presence alone is not grounding.
- Selective routing must report auto-only F1, final selective F1, senior/human-assisted F1, coverage, route rate, and cost separately.
- Four repo papers are diagnostic, not sufficient as the sole conference evidence.

## Integration Decision

The implemented scaffold follows the subagent consensus:

- `method_spec.md` defines BCPCS as a method, not a TRACE-SR artifact.
- `protocol/leakage_control.md` freezes the anti-leakage rules before benchmark execution.
- The schemas require typed claims, support/refute ledgers, and boundary atlas provenance.
- Prototype scripts are structural only and do not claim performance improvement.
