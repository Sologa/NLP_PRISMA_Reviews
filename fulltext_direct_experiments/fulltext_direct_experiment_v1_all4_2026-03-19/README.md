# Fulltext-Direct Experiment Bundle

This bundle implements the four-paper `fulltext-direct` / `stage2-direct` non-QA baseline.

## Scope

- `2307.05527`
- `2409.13738`
- `2511.13936`
- `2601.19926`

## Workflow

- load candidates from `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- dedupe by `key`
- resolve full text from `refs/<paper_id>/mds`
- judge directly with `criteria_stage2/<paper_id>.json`
- run `JuniorNano` + `JuniorMini`
- route mixed cases to `SeniorLead`
- evaluate directly against gold labels with `scripts/screening/evaluate_review_f1.py`

## Commands

Validate bundle:

```bash
./.venv/bin/python fulltext_direct_experiments/fulltext_direct_experiment_v1_all4_2026-03-19/tools/validate_bundle.py
```

Smoke run:

```bash
./.venv/bin/python fulltext_direct_experiments/fulltext_direct_experiment_v1_all4_2026-03-19/tools/run_experiment.py \
  --papers 2307.05527 2409.13738 2511.13936 2601.19926 \
  --max-records 2 \
  --concurrency 4
```

Full run:

```bash
./.venv/bin/python fulltext_direct_experiments/fulltext_direct_experiment_v1_all4_2026-03-19/tools/run_experiment.py \
  --papers 2307.05527 2409.13738 2511.13936 2601.19926 \
  --concurrency 6 \
  --record-batch-size 6
```

Optional key filter:

```bash
./.venv/bin/python fulltext_direct_experiments/fulltext_direct_experiment_v1_all4_2026-03-19/tools/run_experiment.py \
  --papers 2601.19926 \
  --keys Belinkov:2022 Peters:etal:2018 \
  --concurrency 2
```
