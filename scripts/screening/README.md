# Screening Scripts

This folder contains screening-only scripts.

## Files

- `prepare_review_smoke_inputs.py`
  - Builds smoke-test input data.
  - Supports metadata: `.json` list or `.jsonl`.
  - Supports criteria: `.json` only.
- `run_review_smoke5.sh`
  - Runs title/abstract review with local vendor pipeline code.
  - Loads `.env` from this repository.
- `run_review_full_and_f1.sh`
  - Runs full review for a paper ID and computes F1 in one command.
- `evaluate_review_f1.py`
  - Compares review results with `is_evidence_base` labels and writes precision/recall/F1.
- `review_results_debug.py`
  - Summarizes verdict distribution and reviewer disagreement/senior usage.

## Quickstart

```bash
python3 scripts/screening/prepare_review_smoke_inputs.py --top-k 5
bash scripts/screening/run_review_smoke5.sh
python3 scripts/screening/review_results_debug.py
python3 scripts/screening/evaluate_review_f1.py 2511.13936 \
  --results screening/results/2511.13936_full/latte_review_results.json \
  --gold-metadata refs/2511.13936/metadata/title_abstracts_metadata-annotated.jsonl
```

Run on an existing repo paper id directly:

```bash
PAPER_ID=2511.13936 TOP_K=30 \
PIPELINE_PYTHON=/path/to/python \
bash scripts/screening/run_review_smoke5.sh
```

Run full review + F1 in one command (input is paper ID):

```bash
bash scripts/screening/run_review_full_and_f1.sh 2511.13936
```

To keep run snapshots for drift debugging:

```bash
RUN_TAG=run1 bash scripts/screening/run_review_smoke5.sh
RUN_TAG=run2 bash scripts/screening/run_review_smoke5.sh
python3 scripts/screening/review_results_debug.py \
  --results screening/results/cads_smoke5/latte_review_results.run2.json \
  --compare screening/results/cads_smoke5/latte_review_results.run1.json
```

## Local data layout

  - Source data: `screening/data/source/cads/`
  - Smoke input: `screening/data/cads_smoke5/`
  - Output: `screening/results/cads_smoke5/`
  - Existing paper auto mode:
    - Metadata source: `refs/<PAPER_ID>/metadata/title_abstracts_metadata.jsonl` (for screening input)
    - Annotated metadata: `refs/<PAPER_ID>/metadata/title_abstracts_metadata-annotated.jsonl` (for F1)
    - Criteria source: `criteria_jsons/<PAPER_ID>.json`
    - Input: `screening/data/<PAPER_ID>_smoke<TOP_K>/` (smoke mode), or `screening/data/<PAPER_ID>_full/` (full mode)
    - Output: `screening/results/<PAPER_ID>_smoke<TOP_K>/`
  - Full mode (`TOP_K=0`):
    - Input: `screening/data/<PAPER_ID>_full/arxiv_metadata.full.json`
    - Output: `screening/results/<PAPER_ID>_full/latte_review_results.json`

## Runtime requirements

- `PIPELINE_PYTHON` must have: `openai`, `pandas`, `pydantic`, `tqdm`.
- For `gpt-5*` models, do not force custom temperature values (API only supports default behavior).
- Optional override:

```bash
PIPELINE_PYTHON=/path/to/python bash scripts/screening/run_review_smoke5.sh
```
