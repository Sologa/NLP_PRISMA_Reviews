#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_metadata_repair_pipeline.sh [options]

Run the full missing-metadata repair pipeline on refs/arXiv paper IDs.

Options:
  --refs-root PATH             refs root (default: refs)
  --oracle-root PATH           oracle root (default: bib/per_SR_cleaned)
  --tmp-root PATH              tmp root (default: tmp_refs)
  --paper-id ID                Limit to one or more arXiv IDs (repeatable)
  --include-absent-keys BOOL   Include metadata-missing keys absent in metadata file (default: true)
  --cleanup-query-title BOOL    Cleanup LaTeX residual in query title (default: true)
  --checkpoint-every N         Collector checkpoint setting (default: 1)
  --resume BOOL                Collector resume flag (default: true)
  --include-full-metadata BOOL  Collector include-full-metadata (default: true)
  --require-full-metadata BOOL  Require full metadata file to resolve keys (default: true)
  --manifest-filename NAME     Manifest filename (default: missing_manifest.jsonl)
  --skip-collect               Skip collector stage
  --apply                      Apply merge result to refs (default is dry-run)
  --help                       Show this help and exit
EOF
}

REFS_ROOT="refs"
ORACLE_ROOT="bib/per_SR_cleaned"
TMP_ROOT="tmp_refs"
CHECKPOINT_EVERY=1
RESUME=true
INCLUDE_FULL_METADATA=true
INCLUDE_ABSENT_KEYS=true
CLEANUP_QUERY_TITLE=true
MANIFEST_FILENAME="missing_manifest.jsonl"
REQUIRE_FULL_METADATA=true
SKIP_COLLECT=false
APPLY=false

PAPER_IDS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --refs-root)
      REFS_ROOT="$2"
      shift 2
      ;;
    --oracle-root)
      ORACLE_ROOT="$2"
      shift 2
      ;;
    --tmp-root)
      TMP_ROOT="$2"
      shift 2
      ;;
    --paper-id)
      PAPER_IDS+=("$2")
      shift 2
      ;;
    --include-absent-keys)
      INCLUDE_ABSENT_KEYS="$2"
      shift 2
      ;;
    --cleanup-query-title)
      CLEANUP_QUERY_TITLE="$2"
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
    --require-full-metadata)
      REQUIRE_FULL_METADATA="$2"
      shift 2
      ;;
    --manifest-filename)
      MANIFEST_FILENAME="$2"
      shift 2
      ;;
    --skip-collect)
      SKIP_COLLECT=true
      shift
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

TS="$(date -u +%Y%m%d_%H%M%S)"
REPORT_DIR="issues"
VALIDATE_JSON="${REPORT_DIR}/validate_tmp_refs_${TS}.json"
VALIDATE_MD="${REPORT_DIR}/validate_tmp_refs_${TS}.md"
MERGE_JSON="${REPORT_DIR}/metadata_repair_report_${TS}.json"
MERGE_MD="${REPORT_DIR}/metadata_repair_report_${TS}.md"

mkdir -p "$REPORT_DIR"

build_cmd=(
  python3 scripts/metadata/build_tmp_refs_from_missing.py
  --refs-root "$REFS_ROOT"
  --oracle-root "$ORACLE_ROOT"
  --tmp-root "$TMP_ROOT"
  --include-absent-keys "$INCLUDE_ABSENT_KEYS"
  --cleanup-query-title "$CLEANUP_QUERY_TITLE"
  --write-manifest true
)
for paper_id in "${PAPER_IDS[@]:-}"; do
  build_cmd+=(--paper-ids "$paper_id")
done

collect_cmd=(
  bash scripts/download/run_tmp_refs_collect.sh
  --input-root "$TMP_ROOT"
  --output-root "$TMP_ROOT"
  --checkpoint-every "$CHECKPOINT_EVERY"
  --resume "$RESUME"
  --include-full-metadata "$INCLUDE_FULL_METADATA"
)
for paper_id in "${PAPER_IDS[@]:-}"; do
  collect_cmd+=(--paper-id "$paper_id")
done

validate_cmd=(
  python3 scripts/metadata/validate_tmp_refs.py
  --tmp-root "$TMP_ROOT"
  --output-json "$VALIDATE_JSON"
  --output-markdown "$VALIDATE_MD"
)
for paper_id in "${PAPER_IDS[@]:-}"; do
  validate_cmd+=(--paper-ids "$paper_id")
done

merge_cmd=(
  python3 scripts/metadata/merge_tmp_refs_back.py
  --refs-root "$REFS_ROOT"
  --tmp-root "$TMP_ROOT"
  --manifest-filename "$MANIFEST_FILENAME"
  --require-full-metadata "$REQUIRE_FULL_METADATA"
  --report-json "$MERGE_JSON"
  --report-markdown "$MERGE_MD"
)
for paper_id in "${PAPER_IDS[@]:-}"; do
  merge_cmd+=(--paper-ids "$paper_id")
done

if [[ "$APPLY" == "true" ]]; then
  merge_cmd+=(--apply)
else
  merge_cmd+=(--dry-run)
fi

echo "[step] 1) build tmp refs"
"${build_cmd[@]}"

if [[ "$SKIP_COLLECT" == "true" ]]; then
  echo "[step] skip collect (--skip-collect)"
else
  echo "[step] 2) run collector on tmp_refs"
  "${collect_cmd[@]}"
fi

echo "[step] 3) validate tmp result"
"${validate_cmd[@]}"

echo "[step] 4) merge back (${APPLY:+apply}${APPLY:-dry-run})"
"${merge_cmd[@]}"

echo "[done] reports:"
echo "  validate: ${VALIDATE_JSON}"
echo "  validate: ${VALIDATE_MD}"
echo "  merge:    ${MERGE_JSON}"
echo "  merge:    ${MERGE_MD}"

if [[ "$APPLY" != "true" ]]; then
  echo "[note] dry-run mode only. add --apply to write back to refs."
fi
