# Screening Scripts

Current-state note:

- Active criteria paths are stage-specific:
  - `criteria_stage1/<PAPER_ID>.json`
  - `criteria_stage2/<PAPER_ID>.json`
- `criteria_jsons/*.json` are historical/reference only and must not be treated as current production criteria.
- For current-state orientation, read:
  - repo root `AGENTS.md`
  - `docs/chatgpt_current_status_handoff.md`
  - `screening/results/results_manifest.json`

This folder contains screening-only scripts.

## Files

- `prepare_review_smoke_inputs.py`
  - Builds smoke-test input data.
  - Supports metadata: `.json` list or `.jsonl`.
  - Supports criteria: `.json` only.
- `run_review_smoke5.sh`
  - Runs title/abstract review with local vendor pipeline code.
  - Optional: run a second-stage fulltext review (`ENABLE_FULLTEXT_REVIEW=1`).
  - Optional: limit smoke inputs to specific keys (`KEYS_FILE=/path/to/keys.txt`).
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

Fulltext stage on top of base review:

```bash
PAPER_ID=2307.05527 TOP_K=0 \
ENABLE_FULLTEXT_REVIEW=1 \
FULLTEXT_REVIEW_MODE=inline \
FULLTEXT_ROOT=refs/2307.05527/mds \
bash scripts/screening/run_review_smoke5.sh
```

Evaluate fulltext results as base + fulltext merged:

```bash
python3 scripts/screening/evaluate_review_f1.py 2409.13738 \
  --results screening/results/2409.13738_full/latte_fulltext_review_from_run01.json \
  --base-review-results screening/results/2409.13738_full/run01/latte_review_results.run01.json \
  --gold-metadata refs/2409.13738/metadata/title_abstracts_metadata-annotated.jsonl \
  --combine-with-base \
  --positive-mode include_or_maybe \
  --save-report screening/results/2409.13738_full/latte_fulltext_from_run01_combined_f1.json
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

Run a fixed-key smoke subset and evaluate only that subset:

```bash
PAPER_ID=2307.05527 TOP_K=0 \
KEYS_FILE=scripts/screening/smoke5_2307.05527_keys.txt \
ENABLE_FULLTEXT_REVIEW=1 \
FULLTEXT_REVIEW_MODE=inline \
bash scripts/screening/run_review_smoke5.sh

python3 scripts/screening/evaluate_review_f1.py 2307.05527 \
  --results screening/results/2307.05527_full/latte_fulltext_review_results.json \
  --gold-metadata refs/2307.05527/metadata/title_abstracts_metadata-annotated.jsonl \
  --keys-file scripts/screening/smoke5_2307.05527_keys.txt \
  --save-report screening/results/2307.05527_full/fulltext_smoke5_f1.json
```

## Local data layout

  - Source data: `screening/data/source/cads/`
  - Smoke input: `screening/data/cads_smoke5/`
  - Output: `screening/results/cads_smoke5/`
  - Existing paper auto mode:
    - Metadata source: `refs/<PAPER_ID>/metadata/title_abstracts_metadata.jsonl` (for screening input)
    - Annotated metadata: `refs/<PAPER_ID>/metadata/title_abstracts_metadata-annotated.jsonl` (for F1)
    - Fulltext source: `refs/<PAPER_ID>/mds/*.md`
    - Stage 1 criteria source: `criteria_stage1/<PAPER_ID>.json`
    - Stage 2 criteria source: `criteria_stage2/<PAPER_ID>.json`
    - Input: `screening/data/<PAPER_ID>_smoke<TOP_K>/` (smoke mode), or `screening/data/<PAPER_ID>_full/` (full mode)
    - Output: `screening/results/<PAPER_ID>_top<TOP_K>/`
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

## `run_review_smoke5.sh` env flags

- `KEYS_FILE`: newline key list to pick exact records (overrides top-k selection order).
- `CRITERIA_STAGE1_PATH`: Stage 1 criteria path（預設 `criteria_stage1/<PAPER_ID>.json`）。
- `CRITERIA_STAGE2_PATH`: Stage 2 criteria path（預設 `criteria_stage2/<PAPER_ID>.json`）。
- `ENABLE_FULLTEXT_REVIEW`: `1` to run stage-2 fulltext review after base review.
- `FULLTEXT_REVIEW_MODE`: `inline|file_search|hybrid` (`inline` implemented).
- `FULLTEXT_ROOT`: fulltext root directory (usually `refs/<PAPER_ID>/mds`).
- `FULLTEXT_OUTPUT_PATH`: output JSON path for stage-2 review.
- `FULLTEXT_INLINE_HEAD_CHARS`, `FULLTEXT_INLINE_TAIL_CHARS`: context budget controls for inline mode.
