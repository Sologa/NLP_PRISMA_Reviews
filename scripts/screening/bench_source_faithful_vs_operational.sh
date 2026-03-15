#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REPEATS="${REPEATS:-3}"
if ! [[ "${REPEATS}" =~ ^[0-9]+$ ]] || [[ "${REPEATS}" -le 0 ]]; then
  echo "[error] REPEATS must be a positive integer: ${REPEATS}" >&2
  exit 1
fi

RESULTS_ROOT="${RESULTS_ROOT:-${ROOT_DIR}/screening/results/source_faithful_vs_operational_2409_2511}"
WORKSPACE_ROOT_BASE="${WORKSPACE_ROOT_BASE:-${ROOT_DIR}/screening/workspaces/source_faithful_vs_operational_2409_2511}"

PAPERS=("2511.13936" "2409.13738")
VARIANTS=("operational" "source_faithful")

criteria_path_for() {
  local paper_id="$1"
  local variant="$2"
  case "${variant}" in
    operational)
      echo "${ROOT_DIR}/criteria_stage1/${paper_id}.json"
      ;;
    source_faithful)
      echo "${ROOT_DIR}/docs/ChatGPT/${paper_id}.source_faithful_rewrite.json"
      ;;
    *)
      echo "[error] Unknown variant: ${variant}" >&2
      exit 1
      ;;
  esac
}

gold_path_for() {
  local paper_id="$1"
  echo "${ROOT_DIR}/refs/${paper_id}/metadata/title_abstracts_metadata-annotated.jsonl"
}

precheck() {
  for paper_id in "${PAPERS[@]}"; do
    local gold_path
    gold_path="$(gold_path_for "${paper_id}")"
    if [[ ! -f "${gold_path}" ]]; then
      echo "[error] Missing gold metadata: ${gold_path}" >&2
      exit 1
    fi
    for variant in "${VARIANTS[@]}"; do
      local criteria_path
      criteria_path="$(criteria_path_for "${paper_id}" "${variant}")"
      if [[ ! -f "${criteria_path}" ]]; then
        echo "[error] Missing criteria (${variant}): ${criteria_path}" >&2
        exit 1
      fi
    done
  done
}

run_one() {
  local paper_id="$1"
  local variant="$2"
  local run_tag="$3"

  local criteria_path
  criteria_path="$(criteria_path_for "${paper_id}" "${variant}")"
  local gold_path
  gold_path="$(gold_path_for "${paper_id}")"
  local fulltext_root="${ROOT_DIR}/refs/${paper_id}/mds"

  local run_dir="${RESULTS_ROOT}/${paper_id}/${variant}/${run_tag}"
  local ws_dir="${WORKSPACE_ROOT_BASE}/${paper_id}/${variant}/${run_tag}"

  mkdir -p "${run_dir}" "${ws_dir}"

  echo "============================================================"
  echo "[bench] paper=${paper_id} variant=${variant} run=${run_tag}"
  echo "[bench] criteria=${criteria_path}"
  echo "[bench] output_dir=${run_dir}"
  echo "[bench] workspace_root=${ws_dir}"
  echo "============================================================"

  if ! env \
    TQDM_DISABLE=1 \
    PAPER_ID="${paper_id}" \
    TOP_K=0 \
    FORCE_PREPARE_INPUTS=0 \
    ENABLE_FULLTEXT_REVIEW=1 \
    FULLTEXT_REVIEW_MODE=inline \
    FULLTEXT_ROOT="${fulltext_root}" \
    CRITERIA_SOURCE_PATH="${criteria_path}" \
    CRITERIA_PATH="${criteria_path}" \
    OUTPUT_DIR="${run_dir}" \
    WORKSPACE_ROOT="${ws_dir}" \
    RUN_TAG="${run_tag}" \
    bash "${ROOT_DIR}/scripts/screening/run_review_smoke5.sh" \
    >"${run_dir}/review.log" 2>&1; then
    echo "[error] review failed: ${paper_id} ${variant} ${run_tag}" >&2
    tail -n 80 "${run_dir}/review.log" >&2 || true
    return 1
  fi

  if ! python3 "${ROOT_DIR}/scripts/screening/evaluate_review_f1.py" \
    "${paper_id}" \
    --results "${run_dir}/latte_review_results.json" \
    --gold-metadata "${gold_path}" \
    --positive-mode include_or_maybe \
    --save-report "${run_dir}/stage1_f1.json" \
    >"${run_dir}/stage1_eval.log" 2>&1; then
    echo "[error] stage1 eval failed: ${paper_id} ${variant} ${run_tag}" >&2
    tail -n 80 "${run_dir}/stage1_eval.log" >&2 || true
    return 1
  fi

  if ! python3 "${ROOT_DIR}/scripts/screening/evaluate_review_f1.py" \
    "${paper_id}" \
    --results "${run_dir}/latte_fulltext_review_results.json" \
    --base-review-results "${run_dir}/latte_review_results.json" \
    --combine-with-base \
    --gold-metadata "${gold_path}" \
    --positive-mode include_or_maybe \
    --save-report "${run_dir}/combined_f1.json" \
    >"${run_dir}/combined_eval.log" 2>&1; then
    echo "[error] combined eval failed: ${paper_id} ${variant} ${run_tag}" >&2
    tail -n 80 "${run_dir}/combined_eval.log" >&2 || true
    return 1
  fi

  echo "[done] paper=${paper_id} variant=${variant} run=${run_tag}"
}

precheck

mkdir -p "${RESULTS_ROOT}" "${WORKSPACE_ROOT_BASE}"

for paper_id in "${PAPERS[@]}"; do
  for variant in "${VARIANTS[@]}"; do
    for run_idx in $(seq 1 "${REPEATS}"); do
      run_tag="run$(printf "%02d" "${run_idx}")"
      run_one "${paper_id}" "${variant}" "${run_tag}"
    done
  done
done

echo "[done] benchmark finished: ${RESULTS_ROOT}"
echo "[next] summarize with:"
echo "python3 ${ROOT_DIR}/scripts/screening/summarize_source_faithful_vs_operational.py --results-root ${RESULTS_ROOT}"
