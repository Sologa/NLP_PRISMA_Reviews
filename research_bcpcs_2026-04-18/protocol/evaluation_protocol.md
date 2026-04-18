# Evaluation Protocol

## Evaluation Roles

The four repo reviews are internal diagnostic cases. They are not sufficient as
the only evidence for an NLP/IR conference claim.

Use them to test whether BCPCS closes known error modes:

- `2409.13738`: FP-heavy process-extraction boundary.
- `2511.13936`: preference-learning versus evaluation-only boundary.
- `2307.05527`: generative-audio boundary without destabilizing strong baseline.
- `2601.19926`: retrieval/fulltext failure and syntax-specific strictness.

## Dataset Splits

Preferred internal split:

- Leave-one-review-out.
- Development review(s) may be used for graph compiler and atlas design.
- Held-out review may not contribute FP/FN examples to Boundary Atlas.

Minimum split documentation:

- `train_reviews`
- `development_reviews`
- `heldout_reviews`
- `atlas_allowed_reviews`
- `atlas_forbidden_eval_keys`

## Baselines

Report all available baselines:

1. Current production authority from `screening/results/results_manifest.json`.
2. Current two-stage direct-review baseline.
3. Historical QA-first.
4. Merged QA+criteria.
5. Direct single-reviewer prompt.
6. Multi-agent vote/debate.
7. Support-only RAG.
8. Active-learning or ranking baseline where feasible.

## Ablations

Run with identical splits:

- full BCPCS;
- no typed graph;
- no refute retrieval;
- no Boundary Atlas;
- no selective abstention;
- no stage-aware missingness;
- no SeniorLead evidence handoff;
- free-form LLM verdict;
- support-only retrieval.

## Metrics

Verdict-level:

- precision;
- recall;
- F1;
- TP, FP, TN, FN.

Selective automation:

- auto-only F1;
- selective final F1;
- senior/human-assisted F1;
- coverage;
- abstention rate;
- senior route rate;
- cost.

Evidence-level:

- support-span precision;
- support-span recall;
- refute-span precision;
- unsupported-verdict rate;
- hallucinated or irrelevant quote rate.

Error taxonomy:

- `semantic_gap`;
- `stage_observability_failure`;
- `retrieval_failure`;
- `criteria_gold_tension`;
- `evidence_incomplete`;
- `model_overgeneralization`.

## Repeated Runs

For proprietary LLM runs, log:

- model ID;
- endpoint;
- timestamp;
- prompt hash;
- schema hash;
- cost estimate;
- retry count;
- raw output path.

Run repeated prompt paraphrase or model-family checks before making stability
claims.

## Required Reports

- `reports/baseline_recheck.md`
- `reports/smoke_report.md`
- `reports/results.md`

