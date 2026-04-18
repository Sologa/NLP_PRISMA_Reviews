# Reviewer Critique And Risk Register

## Acceptability Assessment

BCPCS is plausible as an NLP/IR methods paper only if it is framed as
bounded-risk, evidence-grounded, selectively automated screening. It is not
acceptable if framed as a universal 100% F1 system.

The publishable unit is not a larger prompt pipeline. Nearby prior work already
covers criteria-to-QA screening, LLM-guided ranking, active learning, RAG,
claim verification, multi-agent adjudication, and high-recall screening. The
paper must show that a systematic-review-specific decision calculus adds value:
typed claims, support/refute ledgers, stage-aware missingness, leakage control,
and selective routing.

## Top Reviewer Objections

1. **100% F1 is not a scientific claim.**
   A universal perfect-screening claim will look like benchmark gaming.

2. **The method may be a composition of known modules.**
   The paper must show what is new in the interface and decision calculus.

3. **Boundary Atlas can leak test errors.**
   If the atlas is built from held-out FP/FN cases, the evaluation is invalid.

4. **Typed graph nodes can become hidden criteria rewriting.**
   Nodes must trace to source-faithful criteria and cannot encode unsupported
   operational hardening.

5. **Evidence quotes do not guarantee grounding.**
   Span-level validation is required.

6. **Selective routing can hide failures.**
   Auto-only, selective, and human/senior-assisted scores must be separated.

7. **Repo-only evaluation is too small.**
   Four internal reviews are diagnostic, not sufficient for conference claims.

8. **Existing internal QA experiments are mixed.**
   The method must explain why it avoids QA-answer reinterpretation and
   cross-paper instability.

9. **Baselines may be underpowered.**
   Strong direct review, QA, merged QA+criteria, multi-agent, RAG, and ranking
   baselines are required.

10. **API drift threatens reproducibility.**
    Prompts, model IDs, timestamps, raw outputs, costs, and repeated runs must
    be logged.

## Required Mitigations

- Replace the universal 100% F1 claim with bounded-risk selective screening.
- Freeze leakage protocol before any benchmark run.
- Use leave-one-review-out or review-level splits.
- Add at least one public benchmark or clearly document why external validation
  is blocked.
- Report auto-only, selective final, and senior/human-assisted metrics.
- Add evidence-span support/refute validation.
- Ablate every claimed module.
- Freeze an error taxonomy before final test analysis.
- Report criteria/gold tension as a separate slice.
- Run repeated trials or robustness checks when proprietary LLM calls are used.

## Hard No-Go Conditions

- No universal perfect-F1 claim.
- No hidden operational hardening in graph nodes.
- No modification of production criteria or prompts.
- No use of `criteria_jsons/*.json` as current criteria.
- No Boundary Atlas construction from held-out final evaluation errors.
- No reporting human-assisted F1 as automated F1.
- No accepting quote evidence without quote/location and validation.
- No repo-only conference claim.
- No premature TRACE-SR artifact.

