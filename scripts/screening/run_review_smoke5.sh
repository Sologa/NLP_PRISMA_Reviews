#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

TOP_K="${TOP_K:-5}"
if ! [[ "${TOP_K}" =~ ^[0-9]+$ ]]; then
  echo "[error] TOP_K must be a non-negative integer: ${TOP_K}" >&2
  exit 1
fi

PAPER_ID="${PAPER_ID:-}"
TOPIC="${TOPIC:-}"
FORCE_PREPARE_INPUTS="${FORCE_PREPARE_INPUTS:-1}"
STRIP_METADATA="${STRIP_METADATA:-1}"
RUN_TAG="${RUN_TAG:-}"
TOP_K_SUFFIX="full"
TOP_K_ARG=""
if [[ "${TOP_K}" != "0" ]]; then
  TOP_K_SUFFIX="top${TOP_K}"
  TOP_K_ARG="${TOP_K}"
fi

if [[ -n "${PAPER_ID}" ]]; then
  if [[ "${TOP_K}" == "0" ]]; then
    TOPIC="${TOPIC:-${PAPER_ID}_screening_full}"
    INPUT_DIR="${INPUT_DIR:-${ROOT_DIR}/screening/data/${PAPER_ID}_full}"
    OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/screening/results/${PAPER_ID}_full}"
  else
    TOPIC="${TOPIC:-${PAPER_ID}_screening_smoke${TOP_K}}"
    INPUT_DIR="${INPUT_DIR:-${ROOT_DIR}/screening/data/${PAPER_ID}_smoke${TOP_K}}"
    OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/screening/results/${PAPER_ID}_top${TOP_K}}"
  fi
  SOURCE_METADATA_PATH="${SOURCE_METADATA_PATH:-${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata.jsonl}"
  CRITERIA_SOURCE_PATH="${CRITERIA_SOURCE_PATH:-${ROOT_DIR}/criteria_jsons/${PAPER_ID}.json}"
  CRITERIA_PATH="${CRITERIA_SOURCE_PATH}"
else
  if [[ "${TOP_K}" == "0" ]]; then
    TOPIC="${TOPIC:-cads_full_local}"
    INPUT_DIR="${INPUT_DIR:-${ROOT_DIR}/screening/data/cads_full}"
    OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/screening/results/cads_full}"
  else
    TOPIC="${TOPIC:-cads_smoke5_local}"
    INPUT_DIR="${INPUT_DIR:-${ROOT_DIR}/screening/data/cads_smoke5}"
    OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/screening/results/cads_smoke5}"
  fi
  SOURCE_METADATA_PATH="${SOURCE_METADATA_PATH:-${ROOT_DIR}/screening/data/source/cads/arxiv_metadata.json}"
  CRITERIA_SOURCE_PATH="${CRITERIA_SOURCE_PATH:-${ROOT_DIR}/screening/data/source/cads/criteria.json}"
  CRITERIA_PATH="${CRITERIA_SOURCE_PATH}"
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-${ROOT_DIR}/screening/workspaces}"

DEFAULT_METADATA_PATH="${INPUT_DIR}/arxiv_metadata.${TOP_K_SUFFIX}.json"
METADATA_PATH="${METADATA_PATH:-${DEFAULT_METADATA_PATH}}"
OUTPUT_PATH="${OUTPUT_PATH:-${OUTPUT_DIR}/latte_review_results.json}"

PIPELINE_ENTRY="${PIPELINE_ENTRY:-${ROOT_DIR}/scripts/screening/vendor/scripts/topic_pipeline.py}"
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PIPELINE_PYTHON="${PIPELINE_PYTHON:-${ROOT_DIR}/.venv/bin/python}"
else
  PIPELINE_PYTHON="${PIPELINE_PYTHON:-python3}"
fi

if [[ "${FORCE_PREPARE_INPUTS}" == "1" || ! -f "${METADATA_PATH}" || ! -f "${CRITERIA_PATH}" ]]; then
  python3 "${ROOT_DIR}/scripts/screening/prepare_review_smoke_inputs.py" \
    --source-metadata "${SOURCE_METADATA_PATH}" \
    --criteria "${CRITERIA_SOURCE_PATH}" \
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

echo "[info] topic=${TOPIC}"
echo "[info] source_metadata_path=${SOURCE_METADATA_PATH}"
echo "[info] source_criteria_path=${CRITERIA_SOURCE_PATH}"
echo "[info] input_dir=${INPUT_DIR}"
echo "[info] output_dir=${OUTPUT_DIR}"
echo "[info] metadata_path=${METADATA_PATH}"
echo "[info] criteria_path=${CRITERIA_PATH}"
echo "[info] force_prepare_inputs=${FORCE_PREPARE_INPUTS}"

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
  ${TOP_K_ARG:+--top-k "${TOP_K_ARG}"}

echo "[done] output=${OUTPUT_PATH}"
if [[ "${STRIP_METADATA}" == "1" ]]; then
  "${PIPELINE_PYTHON}" - <<PY
import json
from pathlib import Path

paths = [
    Path("${OUTPUT_PATH}"),
]
run_tag = "${RUN_TAG}"
tagged_output_path = Path(f"{'${OUTPUT_DIR}'}/latte_review_results{('.' + run_tag) if run_tag else ''}.json")
if tagged_output_path.exists():
    paths.append(tagged_output_path)

for path in paths:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Unable to load {path}: {exc}")
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                row.pop("metadata", None)
    else:
        continue
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
PY
fi

if [[ "${STRIP_METADATA}" == "1" ]]; then
  echo "[done] stripped metadata from output"
fi

if [[ -n "${RUN_TAG:-}" ]]; then
  TAGGED_OUTPUT_PATH="${OUTPUT_DIR}/latte_review_results.${RUN_TAG}.json"
  cp "${OUTPUT_PATH}" "${TAGGED_OUTPUT_PATH}"
  echo "[done] tagged_output=${TAGGED_OUTPUT_PATH}"
fi
