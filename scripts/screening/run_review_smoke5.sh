#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

TOP_K="${TOP_K:-5}"
PAPER_ID="${PAPER_ID:-}"
TOPIC="${TOPIC:-}"

if [[ -n "${PAPER_ID}" ]]; then
  TOPIC="${TOPIC:-${PAPER_ID}_screening_smoke${TOP_K}}"
  SOURCE_METADATA_PATH="${SOURCE_METADATA_PATH:-${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata.jsonl}"
  if [[ -f "${ROOT_DIR}/criteria_corrected_3papers/${PAPER_ID}.md" ]]; then
    SOURCE_CRITERIA_PATH="${SOURCE_CRITERIA_PATH:-${ROOT_DIR}/criteria_corrected_3papers/${PAPER_ID}.md}"
  else
    SOURCE_CRITERIA_PATH="${SOURCE_CRITERIA_PATH:-${ROOT_DIR}/criteria_mds/${PAPER_ID}.md}"
  fi
  INPUT_DIR="${INPUT_DIR:-${ROOT_DIR}/screening/data/${PAPER_ID}_smoke${TOP_K}}"
  OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/screening/results/${PAPER_ID}_smoke${TOP_K}}"
else
  TOPIC="${TOPIC:-cads_smoke5_local}"
  SOURCE_METADATA_PATH="${SOURCE_METADATA_PATH:-${ROOT_DIR}/screening/data/source/cads/arxiv_metadata.json}"
  SOURCE_CRITERIA_PATH="${SOURCE_CRITERIA_PATH:-${ROOT_DIR}/screening/data/source/cads/criteria.json}"
  INPUT_DIR="${INPUT_DIR:-${ROOT_DIR}/screening/data/cads_smoke5}"
  OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/screening/results/cads_smoke5}"
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-${ROOT_DIR}/screening/workspaces}"

DEFAULT_METADATA_PATH="${INPUT_DIR}/arxiv_metadata.top${TOP_K}.json"
METADATA_PATH="${METADATA_PATH:-${DEFAULT_METADATA_PATH}}"
CRITERIA_PATH="${CRITERIA_PATH:-${INPUT_DIR}/criteria.json}"
OUTPUT_PATH="${OUTPUT_PATH:-${OUTPUT_DIR}/latte_review_results.json}"

PIPELINE_ENTRY="${PIPELINE_ENTRY:-${ROOT_DIR}/scripts/screening/vendor/scripts/topic_pipeline.py}"
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PIPELINE_PYTHON="${PIPELINE_PYTHON:-${ROOT_DIR}/.venv/bin/python}"
else
  PIPELINE_PYTHON="${PIPELINE_PYTHON:-python3}"
fi

if [[ ! -f "${METADATA_PATH}" || ! -f "${CRITERIA_PATH}" ]]; then
  python3 "${ROOT_DIR}/scripts/screening/prepare_review_smoke_inputs.py" \
    --source-metadata "${SOURCE_METADATA_PATH}" \
    --source-criteria "${SOURCE_CRITERIA_PATH}" \
    --output-dir "${INPUT_DIR}" \
    --top-k "${TOP_K}"
fi

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env"
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "[error] OPENAI_API_KEY is missing. Check ${ROOT_DIR}/.env" >&2
  exit 1
fi

if [[ ! -f "${PIPELINE_ENTRY}" ]]; then
  echo "[error] Missing review pipeline entry: ${PIPELINE_ENTRY}" >&2
  exit 1
fi

if ! "${PIPELINE_PYTHON}" -c "import openai, pandas, pydantic, tqdm" >/dev/null 2>&1; then
  echo "[error] Missing Python dependencies in ${PIPELINE_PYTHON}." >&2
  echo "[error] Required: openai, pandas, pydantic, tqdm" >&2
  echo "[hint] Set PIPELINE_PYTHON to the environment where these packages are installed." >&2
  exit 1
fi

mkdir -p "${WORKSPACE_ROOT}" "${OUTPUT_DIR}"

"${PIPELINE_PYTHON}" "${PIPELINE_ENTRY}" review \
  --topic "${TOPIC}" \
  --workspace-root "${WORKSPACE_ROOT}" \
  --metadata "${METADATA_PATH}" \
  --criteria "${CRITERIA_PATH}" \
  --output "${OUTPUT_PATH}" \
  --top-k "${TOP_K}"

echo "[done] output=${OUTPUT_PATH}"

if [[ -n "${RUN_TAG:-}" ]]; then
  TAGGED_OUTPUT_PATH="${OUTPUT_DIR}/latte_review_results.${RUN_TAG}.json"
  cp "${OUTPUT_PATH}" "${TAGGED_OUTPUT_PATH}"
  echo "[done] tagged_output=${TAGGED_OUTPUT_PATH}"
fi
