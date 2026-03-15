#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <paper_id> [--runs N]" >&2
  echo "  --runs, --repeats: number of repeated runs (default: 3)" >&2
  exit 1
fi

PAPER_ID=""
REPEATS="${REPEATS:-3}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runs|--repeats)
      if [[ $# -lt 2 ]]; then
        echo "[error] Missing value for $1" >&2
        exit 1
      fi
      REPEATS="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 <paper_id> [--runs N]" >&2
      echo "  --runs, --repeats: number of repeated runs (default: 3)" >&2
      exit 0
      ;;
    --*)
      echo "[error] Unknown option: $1" >&2
      exit 1
      ;;
    *)
      if [[ -z "${PAPER_ID}" ]]; then
        PAPER_ID="$1"
      else
        echo "[error] Unexpected argument: $1" >&2
        echo "Usage: $0 <paper_id> [--runs N]" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "${PAPER_ID}" ]]; then
  echo "[error] PAPER_ID is required." >&2
  exit 1
fi

if ! [[ "${REPEATS}" =~ ^[0-9]+$ ]] || [[ "${REPEATS}" -eq 0 ]]; then
  echo "[error] --runs must be a positive integer: ${REPEATS}" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

SOURCE_METADATA_PATH_REVIEW="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata.jsonl"
SOURCE_METADATA_PATH_REVIEW_ANNO="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata-annotated.jsonl"
CRITERIA_STAGE1_PATH="${ROOT_DIR}/criteria_stage1/${PAPER_ID}.json"
CRITERIA_STAGE2_PATH="${ROOT_DIR}/criteria_stage2/${PAPER_ID}.json"
GOLD_METADATA_PRIMARY="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata-annotated.jsonl"
GOLD_METADATA_FALLBACK="${ROOT_DIR}/refs/${PAPER_ID}/metadata/title_abstracts_metadata.jsonl"
RESULTS_DIR="${ROOT_DIR}/screening/results/${PAPER_ID}_full"

if [[ ! -f "${CRITERIA_STAGE1_PATH}" ]]; then
  echo "[error] Missing Stage 1 criteria file: ${CRITERIA_STAGE1_PATH}" >&2
  exit 1
fi

if [[ ! -f "${CRITERIA_STAGE2_PATH}" ]]; then
  echo "[error] Missing Stage 2 criteria file: ${CRITERIA_STAGE2_PATH}" >&2
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
export CRITERIA_SOURCE_PATH="${CRITERIA_STAGE1_PATH}"
export CRITERIA_STAGE1_SOURCE_PATH="${CRITERIA_STAGE1_PATH}"
export CRITERIA_STAGE2_SOURCE_PATH="${CRITERIA_STAGE2_PATH}"
export CRITERIA_STAGE1_PATH="${CRITERIA_STAGE1_PATH}"
export CRITERIA_STAGE2_PATH="${CRITERIA_STAGE2_PATH}"
export FORCE_PREPARE_INPUTS="${FORCE_PREPARE_INPUTS:-1}"
export INPUT_DIR="${ROOT_DIR}/screening/data/${PAPER_ID}_full"

mkdir -p "${RESULTS_DIR}"
REPORT_PATHS=()
for RUN_INDEX in $(seq 1 "${REPEATS}"); do
  RUN_TAG="run$(printf "%02d" "${RUN_INDEX}")"
  RUN_RESULTS_DIR="${RESULTS_DIR}/${RUN_TAG}"
  RUN_REPORT_FILE="${RUN_RESULTS_DIR}/latte_review_f1.json"
  mkdir -p "${RUN_RESULTS_DIR}"

  echo "[info] run=${RUN_TAG} paper=${PAPER_ID}"
  export OUTPUT_DIR="${RUN_RESULTS_DIR}"
  export RUN_TAG="${RUN_TAG}"
  export WORKSPACE_ROOT="${ROOT_DIR}/screening/workspaces/${PAPER_ID}_full/${RUN_TAG}"
  "${ROOT_DIR}/scripts/screening/run_review_smoke5.sh"

  python3 "${ROOT_DIR}/scripts/screening/evaluate_review_f1.py" \
    "${PAPER_ID}" \
    --results "${RUN_RESULTS_DIR}/latte_review_results.json" \
    --gold-metadata "${GOLD_METADATA_PATH}" \
    --annotate \
    --strip-metadata \
    --save-report "${RUN_REPORT_FILE}"

  REPORT_PATHS+=("${RUN_REPORT_FILE}")
  echo "[done] full review + F1 finished: ${RUN_RESULTS_DIR}/latte_review_results.json"
done

REPORT_PATHS_STR="$(printf "%s\n" "${REPORT_PATHS[@]}")"
export REPORT_PATHS_STR
python3 - <<PY
import os
from pathlib import Path
import json

paper_id = "${PAPER_ID}"
report_paths = os.environ["REPORT_PATHS_STR"].strip().splitlines()
if not report_paths:
  raise SystemExit("No run reports were produced.")

macro_precision = []
macro_recall = []
macro_f1 = []
sum_tp = 0
sum_fp = 0
sum_tn = 0
sum_fn = 0
run_reports = []

for report_path in report_paths:
    p = Path(report_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    metrics = data.get("metrics", {})
    precision = metrics.get("precision")
    recall = metrics.get("recall")
    f1 = metrics.get("f1")
    if precision is None or recall is None or f1 is None:
      continue
    if not isinstance(precision, (int, float)):
      continue
    if not isinstance(recall, (int, float)):
      continue
    if not isinstance(f1, (int, float)):
      continue
    macro_precision.append(float(precision))
    macro_recall.append(float(recall))
    macro_f1.append(float(f1))
    run_reports.append({
      "run_tag": p.parent.name,
      "report_path": str(p),
      "results_path": data.get("results_path"),
      "metrics": metrics,
      "verdict_counts": data.get("verdict_counts", {}),
      "gold_only_count": data.get("gold_only_count"),
      "extra_result_only_count": data.get("extra_result_only_count"),
    })
    sum_tp += int(metrics.get("tp", 0) or 0)
    sum_fp += int(metrics.get("fp", 0) or 0)
    sum_tn += int(metrics.get("tn", 0) or 0)
    sum_fn += int(metrics.get("fn", 0) or 0)

if not macro_precision:
  raise SystemExit("No valid metrics found in reports.")

macro = {
    "precision": sum(macro_precision) / len(macro_precision),
    "recall": sum(macro_recall) / len(macro_recall),
    "f1": sum(macro_f1) / len(macro_f1),
}

micro_total = sum_tp + sum_fp + sum_tn + sum_fn
if micro_total:
  micro = {
      "precision": sum_tp / (sum_tp + sum_fp) if (sum_tp + sum_fp) else 0.0,
      "recall": sum_tp / (sum_tp + sum_fn) if (sum_tp + sum_fn) else 0.0,
  }
  denom = micro["precision"] + micro["recall"]
  micro["f1"] = 0.0 if denom == 0 else 2 * micro["precision"] * micro["recall"] / denom
  micro["tp"] = sum_tp
  micro["fp"] = sum_fp
  micro["tn"] = sum_tn
  micro["fn"] = sum_fn
  micro["accuracy"] = (sum_tp + sum_tn) / micro_total
else:
  micro = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "tn": 0, "fn": 0, "accuracy": 0.0}

summary = {
  "paper_id": paper_id,
  "runs": "${REPEATS}",
  "run_reports": run_reports,
  "macro_average": macro,
  "micro_average": micro,
}
summary_path = Path("${RESULTS_DIR}/avg_review_f1_${REPEATS}x.json")
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[done] average_f1 saved: {summary_path}")
print(f"[done] macro avg: precision={macro['precision']:.4f}, recall={macro['recall']:.4f}, f1={macro['f1']:.4f}")
print(f"[done] micro avg: precision={micro['precision']:.4f}, recall={micro['recall']:.4f}, f1={micro['f1']:.4f}, accuracy={micro['accuracy']:.4f}")
PY
