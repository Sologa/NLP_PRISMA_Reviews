# Boundary-Calibrated Proof-Carrying Screening

This folder is an isolated research workspace for the proposed NLP/IR method:

**Boundary-Calibrated Proof-Carrying Screening for Systematic Reviews**.

The method reframes systematic-review screening as bounded-risk evidence
verification rather than free-form LLM classification. Source-faithful review
criteria are compiled into typed eligibility claims; each claim requires
support, refutation, or explicit missingness evidence; and final decisions are
derived from an auditable decision graph with selective senior or human routing.

## Scope

This workspace contains research documents, schemas, configs, prototype code,
and generated run outputs for BCPCS only.

It may read existing repo inputs by path:

- `AGENTS.md`
- `docs/chatgpt_current_status_handoff.md`
- `screening/results/results_manifest.json`
- `screening/results/<paper>_full/CURRENT.md`
- `criteria_stage1/<paper_id>.json`
- `criteria_stage2/<paper_id>.json`
- `cutoff_jsons/<paper_id>.json`
- `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- `refs/<paper_id>/metadata/title_abstracts_metadata-annotated.jsonl`
- current authoritative screening result files

It must write outputs only inside `research_bcpcs_2026-04-18/`.

## Non-Goals

- This is not a TRACE-SR artifact.
- This is not a production workflow replacement.
- This does not rewrite current production criteria.
- This does not add a hidden guidance layer to the repo.
- This does not claim universal fully automatic 100% F1.
- This does not use `criteria_jsons/*.json` as current criteria.

## Isolation Rule

Do not modify these existing paths while working on this research packet:

- `criteria_stage1/`
- `criteria_stage2/`
- `cutoff_jsons/`
- `scripts/screening/runtime_prompts/runtime_prompts.json`
- `screening/results/results_manifest.json`
- existing `docs/`
- existing experiment bundles and historical result directories

Prototype code under `src/` must write generated outputs under `runs/` or
`reports/`.

## Current-State Assumptions

The repo-current state is anchored by `AGENTS.md`,
`docs/chatgpt_current_status_handoff.md`, and
`screening/results/results_manifest.json`.

The active runtime prompt source is:

- `scripts/screening/runtime_prompts/runtime_prompts.json`

The active criteria source is stage-specific:

- Stage 1: `criteria_stage1/<paper_id>.json`
- Stage 2: `criteria_stage2/<paper_id>.json`

The current `2409.13738` authoritative metric artifacts report combined F1
`0.7500`. Any older `0.8235` mention is treated as state drift, not active
score authority.

## Folder Contents

- `literature_review.md`: field map and source-backed research gap.
- `reviewer_critique.md`: harsh NLP/IR reviewer risks and mitigations.
- `method_spec.md`: frozen BCPCS method definition.
- `novelty_claims.md`: exact contribution claims and non-claims.
- `protocol/`: leakage, evaluation, and annotation rules.
- `schemas/`: JSON schemas for graph, ledger, and boundary atlas.
- `configs/experiment_matrix.yaml`: datasets, baselines, ablations, and model settings.
- `src/`: isolated prototype utilities.
- `runs/`: generated smoke and dry-run outputs.
- `reports/`: generated checks and analysis reports.

