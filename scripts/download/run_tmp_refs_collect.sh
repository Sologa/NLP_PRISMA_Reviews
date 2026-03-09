#!/usr/bin/env bash

set -u

INPUT_ROOT="${INPUT_ROOT:-tmp_refs}"
OUTPUT_ROOT="${OUTPUT_ROOT:-tmp_refs}"
PAPER_IDS=()
COLLECTOR_ARGS=()

PYTHON="${PYTHON:-python3}"
COLLECT_SCRIPT="${COLLECT_SCRIPT:-scripts/download/collect_title_abstracts_priority.py}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-1}"
RESUME="${RESUME:-true}"
INCLUDE_FULL_METADATA="${INCLUDE_FULL_METADATA:-true}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input-root)
      INPUT_ROOT="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --paper-id)
      PAPER_IDS+=("$2")
      shift 2
      ;;
    --checkpoint-every)
      CHECKPOINT_EVERY="$2"
      shift 2
      ;;
    --resume)
      RESUME="$2"
      shift 2
      ;;
    --include-full-metadata)
      INCLUDE_FULL_METADATA="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    --help|-h)
      echo "Usage: $(basename "$0") [--input-root DIR] [--output-root DIR] [--paper-id ID ...] [collector args...]"
      echo "Env vars can also be used: INPUT_ROOT, OUTPUT_ROOT, PYTHON, COLLECT_SCRIPT, CHECKPOINT_EVERY, RESUME, INCLUDE_FULL_METADATA"
      exit 0
      ;;
    *)
      COLLECTOR_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ ! -d "$INPUT_ROOT" ]]; then
  echo "[error] input root not found: $INPUT_ROOT" >&2
  exit 1
fi

if [[ ! -f "$COLLECT_SCRIPT" ]]; then
  echo "[error] collector script not found: $COLLECT_SCRIPT" >&2
  exit 1
fi

if [[ ! -d "$OUTPUT_ROOT" ]]; then
  mkdir -p "$OUTPUT_ROOT"
fi

FAILURES=0

in_array() {
  local needle="$1"
  shift
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

for paper_dir in "$INPUT_ROOT"/*; do
  if [[ ! -d "$paper_dir" ]]; then
    continue
  fi

  paper_name="$(basename "$paper_dir")"
  if [[ ${#PAPER_IDS[@]} -gt 0 ]] && ! in_array "$paper_name" "${PAPER_IDS[@]}"; then
    continue
  fi

  oracle_file="$paper_dir/reference_oracle.jsonl"
  if [[ ! -f "$oracle_file" ]]; then
    echo "[skip] $paper_name: no reference_oracle.jsonl"
    continue
  fi

  echo "[start] $paper_name"
  set +e
  if [[ ${#COLLECTOR_ARGS[@]} -gt 0 ]]; then
    "$PYTHON" -u "$COLLECT_SCRIPT" \
      --input-root "$INPUT_ROOT" \
      --output-root "$OUTPUT_ROOT" \
      --paper-name "$paper_name" \
      --checkpoint-every "$CHECKPOINT_EVERY" \
      --resume "$RESUME" \
      --include-full-metadata "$INCLUDE_FULL_METADATA" \
      "${COLLECTOR_ARGS[@]}"
  else
    "$PYTHON" -u "$COLLECT_SCRIPT" \
      --input-root "$INPUT_ROOT" \
      --output-root "$OUTPUT_ROOT" \
      --paper-name "$paper_name" \
      --checkpoint-every "$CHECKPOINT_EVERY" \
      --resume "$RESUME" \
      --include-full-metadata "$INCLUDE_FULL_METADATA"
  fi
  status=$?
  set -e

  if [[ $status -ne 0 ]]; then
    echo "[fail] $paper_name: collector exited with $status"
    ((FAILURES += 1))
  else
    echo "[done] $paper_name"
  fi
done

if [[ $FAILURES -gt 0 ]]; then
  echo "[summary] completed with $FAILURES failed paper(s)"
  exit 1
fi

echo "[summary] all papers completed"
exit 0
