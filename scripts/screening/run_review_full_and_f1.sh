#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <paper_id>" >&2
  exit 1
fi

PAPER_ID="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

SOURCE_METADATA_PATH_REVIEW="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata.jsonl"
SOURCE_METADATA_PATH_REVIEW_ANNO="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata-annotated.jsonl"
CRITERIA_PATH="${ROOT_DIR}/criteria_jsons/${PAPER_ID}.json"
GOLD_METADATA_PRIMARY="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata-annotated.jsonl"
GOLD_METADATA_FALLBACK="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata.jsonl"
RESULTS_DIR="${ROOT_DIR}/screening/results/${PAPER_ID}_full"
RESULTS_FILE="${RESULTS_DIR}/latte_review_results.json"
REPORT_FILE="${RESULTS_DIR}/latte_review_f1.json"

if [[ ! -f "${CRITERIA_PATH}" ]]; then
  echo "[error] Missing criteria file: ${CRITERIA_PATH}" >&2
  exit 1
fi

if [[ -f "${SOURCE_METADATA_PATH_REVIEW}" ]]; then
  SOURCE_METADATA_PATH="${SOURCE_METADATA_PATH_REVIEW}"
elif [[ -f "${SOURCE_METADATA_PATH_REVIEW_ANNO}" ]]; then
  SOURCE_METADATA_PATH="${SOURCE_METADATA_PATH_REVIEW_ANNO}"
else
  echo "[error] Missing review metadata file for ${PAPER_ID}" >&2
  echo "[error] Checked:" >&2
  echo "  - ${SOURCE_METADATA_PATH_REVIEW}" >&2
  echo "  - ${SOURCE_METADATA_PATH_REVIEW_ANNO}" >&2
  exit 1
fi

if [[ -f "${GOLD_METADATA_PRIMARY}" ]]; then
  GOLD_METADATA_PATH="${GOLD_METADATA_PRIMARY}"
elif [[ -f "${GOLD_METADATA_FALLBACK}" ]]; then
  GOLD_METADATA_PATH="${GOLD_METADATA_FALLBACK}"
else
  echo "[error] Missing gold metadata file for ${PAPER_ID}" >&2
  echo "[error] Checked:" >&2
  echo "  - ${GOLD_METADATA_PRIMARY}" >&2
  echo "  - ${GOLD_METADATA_FALLBACK}" >&2
  exit 1
fi

export PAPER_ID
export TOP_K=0
export TOPIC="${PAPER_ID}_screening_full"
export SOURCE_METADATA_PATH
export CRITERIA_SOURCE_PATH="${CRITERIA_PATH}"
export CRITERIA_PATH="${CRITERIA_PATH}"
export FORCE_PREPARE_INPUTS="${FORCE_PREPARE_INPUTS:-1}"
export INPUT_DIR="${ROOT_DIR}/screening/data/${PAPER_ID}_full"
export OUTPUT_DIR="${RESULTS_DIR}"

"${ROOT_DIR}/scripts/screening/run_review_smoke5.sh"

python3 "${ROOT_DIR}/scripts/screening/evaluate_review_f1.py" \
  "${PAPER_ID}" \
  --results "${RESULTS_FILE}" \
  --gold-metadata "${GOLD_METADATA_PATH}" \
  --annotate \
  --strip-metadata \
  --save-report "${REPORT_FILE}"

echo "[done] full review + F1 finished: ${RESULTS_FILE}"
