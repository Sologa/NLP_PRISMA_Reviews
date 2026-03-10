#!/usr/bin/env bash

set -euo pipefail

# Review workflow for paper 2511.13936 (non-smoke naming)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export PAPER_ID="2511.13936"
export TOP_K="${TOP_K:-5}"
export TOPIC="${TOPIC:-${PAPER_ID}_review_top${TOP_K}}"
export RUN_TAG="${RUN_TAG:-review_${PAPER_ID}_top${TOP_K}}"
export FORCE_PREPARE_INPUTS="${FORCE_PREPARE_INPUTS:-1}"
export CRITERIA_SOURCE_PATH="${ROOT_DIR}/criteria_jsons/${PAPER_ID}.json"
export SOURCE_METADATA_PATH="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata.jsonl"

# Keep inputs/results under explicit non-smoke folders
export INPUT_DIR="${ROOT_DIR}/screening/data/${PAPER_ID}_top${TOP_K}"
export OUTPUT_DIR="${ROOT_DIR}/screening/results/${PAPER_ID}_top${TOP_K}"

"${ROOT_DIR}/scripts/screening/run_review_smoke5.sh"
