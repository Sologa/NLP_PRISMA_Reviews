# Novelty Claims And Non-Claims

## Claims

1. **Proof-carrying screening interface.**
   BCPCS defines a typed evidence ledger for systematic-review screening in
   which each criterion-derived claim carries support, refutation, or explicit
   missingness evidence.

2. **Stage-aware decision calculus.**
   BCPCS distinguishes Stage 1 unobservability from Stage 2 unresolved evidence,
   retrieval failure, metadata ambiguity, semantic non-fit, and criteria/gold
   tension.

3. **Refutation-first retrieval for eligibility.**
   BCPCS explicitly searches for disqualifying evidence before allowing
   inclusion, reducing topic-adjacent false positives.

4. **Leakage-controlled boundary calibration.**
   BCPCS uses contrastive positive and hard-negative archetypes only under
   frozen split restrictions, so boundary support does not become test repair.

5. **Selective-risk reporting.**
   BCPCS separates automated, selective, and senior/human-assisted performance
   instead of hiding difficult cases inside a single F1 number.

## Non-Claims

- BCPCS does not claim universal fully automatic 100% F1.
- BCPCS does not claim that LLMs replace expert reviewers.
- BCPCS does not claim that evidence quotes are correct without validation.
- BCPCS does not claim production authority over current repo workflows.
- BCPCS does not rewrite source review criteria.
- BCPCS does not convert operational hardening into formal eligibility rules.
- BCPCS is not TRACE-SR.

## Conference-Ready Framing

Preferred paper title:

**Boundary-Calibrated Proof-Carrying Screening for Systematic Reviews**

Preferred abstract-level claim:

> Criteria and definitions are necessary but insufficient for reliable
> systematic-review screening. We introduce an evidence-grounded decision
> interface that compiles source-faithful criteria into typed claims, verifies
> support and refutation evidence, calibrates near-miss boundaries under
> leakage control, and reports selective automation under explicit risk.

