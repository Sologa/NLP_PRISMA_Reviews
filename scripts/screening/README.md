# Screening Scripts

This folder contains screening-only scripts.

## Files

- `prepare_review_smoke_inputs.py`
  - Builds smoke-test input data.
  - Supports metadata: `.json` list or `.jsonl`.
  - Supports criteria: `.json` or `criteria_mds/*.md`.
- `run_review_smoke5.sh`
  - Runs title/abstract review with local vendor pipeline code.
  - Loads `.env` from this repository.
- `review_results_debug.py`
  - Summarizes verdict distribution and reviewer disagreement/senior usage.

## Quickstart

```bash
python3 scripts/screening/prepare_review_smoke_inputs.py --top-k 5
bash scripts/screening/run_review_smoke5.sh
python3 scripts/screening/review_results_debug.py
```

Run on an existing repo paper id directly:

```bash
PAPER_ID=2511.13936 TOP_K=30 \
PIPELINE_PYTHON=/path/to/python \
bash scripts/screening/run_review_smoke5.sh
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
  - Metadata source: `refs/<PAPER_ID>/metadata/title_abstracts_metadata.jsonl`
  - Criteria source: `criteria_corrected_3papers/<PAPER_ID>.md` (fallback: `criteria_mds/<PAPER_ID>.md`)
  - Input: `screening/data/<PAPER_ID>_smoke<TOP_K>/`
  - Output: `screening/results/<PAPER_ID>_smoke<TOP_K>/`

## Runtime requirements

- `PIPELINE_PYTHON` must have: `openai`, `pandas`, `pydantic`, `tqdm`.
- For `gpt-5*` models, do not force custom temperature values (API only supports default behavior).
- Optional override:

```bash
PIPELINE_PYTHON=/path/to/python bash scripts/screening/run_review_smoke5.sh
```
