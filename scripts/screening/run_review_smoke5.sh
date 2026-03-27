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
KEYS_FILE="${KEYS_FILE:-}"

ENABLE_FULLTEXT_REVIEW="${ENABLE_FULLTEXT_REVIEW:-0}"
FULLTEXT_REVIEW_MODE="${FULLTEXT_REVIEW_MODE:-inline}"
FULLTEXT_INLINE_HEAD_CHARS="${FULLTEXT_INLINE_HEAD_CHARS:-24000}"
FULLTEXT_INLINE_TAIL_CHARS="${FULLTEXT_INLINE_TAIL_CHARS:-12000}"
REPO_CUTOFF_PREPRINT_SPLIT_SUBMITTED_DATE="${REPO_CUTOFF_PREPRINT_SPLIT_SUBMITTED_DATE:-}"

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
  CRITERIA_STAGE1_SOURCE_PATH="${CRITERIA_STAGE1_SOURCE_PATH:-${ROOT_DIR}/criteria_stage1/${PAPER_ID}.json}"
  CRITERIA_STAGE2_SOURCE_PATH="${CRITERIA_STAGE2_SOURCE_PATH:-${ROOT_DIR}/criteria_stage2/${PAPER_ID}.json}"
  CRITERIA_SOURCE_PATH="${CRITERIA_SOURCE_PATH:-${CRITERIA_STAGE1_SOURCE_PATH}}"
  CRITERIA_STAGE1_PATH="${CRITERIA_STAGE1_PATH:-${CRITERIA_SOURCE_PATH}}"
  CRITERIA_STAGE2_PATH="${CRITERIA_STAGE2_PATH:-${CRITERIA_STAGE2_SOURCE_PATH}}"
  FULLTEXT_ROOT="${FULLTEXT_ROOT:-${ROOT_DIR}/refs/${PAPER_ID}/mds}"
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
  CRITERIA_STAGE1_SOURCE_PATH="${CRITERIA_STAGE1_SOURCE_PATH:-${ROOT_DIR}/screening/data/source/cads/criteria.json}"
  CRITERIA_STAGE2_SOURCE_PATH="${CRITERIA_STAGE2_SOURCE_PATH:-${CRITERIA_STAGE1_SOURCE_PATH}}"
  CRITERIA_SOURCE_PATH="${CRITERIA_SOURCE_PATH:-${CRITERIA_STAGE1_SOURCE_PATH}}"
  CRITERIA_STAGE1_PATH="${CRITERIA_STAGE1_PATH:-${CRITERIA_SOURCE_PATH}}"
  CRITERIA_STAGE2_PATH="${CRITERIA_STAGE2_PATH:-${CRITERIA_STAGE2_SOURCE_PATH}}"
  FULLTEXT_ROOT="${FULLTEXT_ROOT:-}"
fi

CUTOFF_SPLIT_ARG=()
if [[ "${PAPER_ID:-}" == "2307.05527" ]]; then
  if [[ -z "${REPO_CUTOFF_PREPRINT_SPLIT_SUBMITTED_DATE}" ]]; then
    REPO_CUTOFF_PREPRINT_SPLIT_SUBMITTED_DATE="1"
  fi
  if [[ "${REPO_CUTOFF_PREPRINT_SPLIT_SUBMITTED_DATE}" == "1" ]]; then
    CUTOFF_SPLIT_ARG+=(--repo-cutoff-preprint-split-submitted-date)
  fi
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-${ROOT_DIR}/screening/workspaces}"

DEFAULT_METADATA_PATH="${INPUT_DIR}/arxiv_metadata.${TOP_K_SUFFIX}.json"
if [[ -n "${METADATA_PATH:-}" ]]; then
  METADATA_PATH="${METADATA_PATH}"
  METADATA_PATH_EXPLICIT=1
else
  METADATA_PATH="${DEFAULT_METADATA_PATH}"
  METADATA_PATH_EXPLICIT=0
fi

OUTPUT_PATH="${OUTPUT_PATH:-${OUTPUT_DIR}/latte_review_results.json}"
FULLTEXT_BASE_RESULTS_PATH="${FULLTEXT_BASE_RESULTS_PATH:-${OUTPUT_PATH}}"
FULLTEXT_OUTPUT_PATH="${FULLTEXT_OUTPUT_PATH:-${OUTPUT_DIR}/latte_fulltext_review_results.json}"

PIPELINE_ENTRY="${PIPELINE_ENTRY:-${ROOT_DIR}/scripts/screening/vendor/scripts/topic_pipeline.py}"
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PIPELINE_PYTHON="${PIPELINE_PYTHON:-${ROOT_DIR}/.venv/bin/python}"
else
  PIPELINE_PYTHON="${PIPELINE_PYTHON:-python3}"
fi

if [[ -n "${KEYS_FILE}" ]]; then
  if [[ ! -f "${KEYS_FILE}" ]]; then
    echo "[error] KEYS_FILE not found: ${KEYS_FILE}" >&2
    exit 1
  fi
fi

NEEDS_FULL_POOL_REBUILD=0
if [[ "${TOP_K}" == "0" && -f "${INPUT_DIR}/manifest.json" ]]; then
  NEEDS_FULL_POOL_REBUILD="$(${PIPELINE_PYTHON} - <<PY
import json
from pathlib import Path
manifest_path = Path("${INPUT_DIR}/manifest.json")
try:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
except Exception:
    print(1)
    raise SystemExit(0)
total_count = int(payload.get("metadata_total_available") or 0)
subset_count = int(payload.get("metadata_subset_count") or 0)
print(1 if subset_count < total_count else 0)
PY
)"
fi

if [[ "${FORCE_PREPARE_INPUTS}" == "1" || "${NEEDS_FULL_POOL_REBUILD}" == "1" || ! -f "${METADATA_PATH}" || ! -f "${CRITERIA_STAGE1_PATH}" ]]; then
  PREPARE_CMD=(
    python3 "${ROOT_DIR}/scripts/screening/prepare_review_smoke_inputs.py"
    --source-metadata "${SOURCE_METADATA_PATH}"
    --criteria "${CRITERIA_SOURCE_PATH}"
    --output-dir "${INPUT_DIR}"
    --top-k "${TOP_K}"
  )
  if [[ -n "${KEYS_FILE}" ]]; then
    PREPARE_CMD+=(--keys-file "${KEYS_FILE}")
  fi
  "${PREPARE_CMD[@]}"

  if [[ -n "${KEYS_FILE}" && "${METADATA_PATH_EXPLICIT}" == "0" ]]; then
    MANIFEST_PATH="${INPUT_DIR}/manifest.json"
    if [[ ! -f "${MANIFEST_PATH}" ]]; then
      echo "[error] Missing manifest after prepare: ${MANIFEST_PATH}" >&2
      exit 1
    fi
    METADATA_PATH="$(${PIPELINE_PYTHON} - <<PY
import json
from pathlib import Path
root = Path("${ROOT_DIR}").resolve()
manifest = Path("${MANIFEST_PATH}").resolve()
payload = json.loads(manifest.read_text(encoding="utf-8"))
rel = payload.get("output_metadata")
if not rel:
    raise SystemExit("manifest output_metadata is empty")
print((root / rel).resolve())
PY
)"
  fi
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
echo "[info] stage1_criteria_path=${CRITERIA_STAGE1_PATH}"
echo "[info] stage2_criteria_path=${CRITERIA_STAGE2_PATH}"
echo "[info] input_dir=${INPUT_DIR}"
echo "[info] output_dir=${OUTPUT_DIR}"
echo "[info] metadata_path=${METADATA_PATH}"
echo "[info] force_prepare_inputs=${FORCE_PREPARE_INPUTS}"
echo "[info] needs_full_pool_rebuild=${NEEDS_FULL_POOL_REBUILD}"
echo "[info] keys_file=${KEYS_FILE:-<none>}"

if [[ ! -f "${CRITERIA_STAGE1_PATH}" ]]; then
  echo "[error] Missing Stage 1 criteria file: ${CRITERIA_STAGE1_PATH}" >&2
  exit 1
fi

if ! "${PIPELINE_PYTHON}" -c "import openai, pandas, pydantic, tqdm" >/dev/null 2>&1; then
  echo "[error] Missing Python dependencies in ${PIPELINE_PYTHON}." >&2
  echo "[error] Required: openai, pandas, pydantic, tqdm" >&2
  echo "[hint] Set PIPELINE_PYTHON to the environment where these packages are installed." >&2
  exit 1
fi

mkdir -p "${WORKSPACE_ROOT}" "${OUTPUT_DIR}"

REVIEW_CMD=(
  "${PIPELINE_PYTHON}" "${PIPELINE_ENTRY}" review
  --topic "${TOPIC}"
  --workspace-root "${WORKSPACE_ROOT}"
  --metadata "${METADATA_PATH}"
  --criteria "${CRITERIA_STAGE1_PATH}"
  --output "${OUTPUT_PATH}"
)
if [[ -n "${TOP_K_ARG}" ]]; then
  REVIEW_CMD+=(--top-k "${TOP_K_ARG}")
fi
if [[ ${#CUTOFF_SPLIT_ARG[@]} -gt 0 ]]; then
  REVIEW_CMD+=("${CUTOFF_SPLIT_ARG[@]}")
fi
"${REVIEW_CMD[@]}"

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

if [[ "${ENABLE_FULLTEXT_REVIEW}" == "1" ]]; then
  if [[ -z "${FULLTEXT_ROOT}" ]]; then
    echo "[error] FULLTEXT_ROOT is required when ENABLE_FULLTEXT_REVIEW=1" >&2
    exit 1
  fi
  if [[ ! -f "${CRITERIA_STAGE2_PATH}" ]]; then
    echo "[error] Missing Stage 2 criteria file: ${CRITERIA_STAGE2_PATH}" >&2
    exit 1
  fi
  echo "[info] fulltext_review_mode=${FULLTEXT_REVIEW_MODE}"
  echo "[info] fulltext_root=${FULLTEXT_ROOT}"
  echo "[info] fulltext_output=${FULLTEXT_OUTPUT_PATH}"

  "${PIPELINE_PYTHON}" "${PIPELINE_ENTRY}" fulltext-review \
    --topic "${TOPIC}" \
    --workspace-root "${WORKSPACE_ROOT}" \
    --base-review-results "${FULLTEXT_BASE_RESULTS_PATH}" \
    --metadata "${METADATA_PATH}" \
    --criteria "${CRITERIA_STAGE2_PATH}" \
    --fulltext-root "${FULLTEXT_ROOT}" \
    --output "${FULLTEXT_OUTPUT_PATH}" \
    --fulltext-review-mode "${FULLTEXT_REVIEW_MODE}" \
    --fulltext-inline-head-chars "${FULLTEXT_INLINE_HEAD_CHARS}" \
    --fulltext-inline-tail-chars "${FULLTEXT_INLINE_TAIL_CHARS}" \
    "${CUTOFF_SPLIT_ARG[@]}"

  if [[ -n "${RUN_TAG:-}" ]]; then
    TAGGED_FULLTEXT_OUTPUT_PATH="${OUTPUT_DIR}/latte_fulltext_review_results.${RUN_TAG}.json"
    cp "${FULLTEXT_OUTPUT_PATH}" "${TAGGED_FULLTEXT_OUTPUT_PATH}"
    echo "[done] tagged_fulltext_output=${TAGGED_FULLTEXT_OUTPUT_PATH}"
  fi

  echo "[done] fulltext_output=${FULLTEXT_OUTPUT_PATH}"
fi
