# BCPCS Workspace Local Guide

Read this file after the repo-root `AGENTS.md` when the task is explicitly scoped to `research_bcpcs_2026-04-18/`.

## 1. Local graph

This workspace may maintain a local graph under:

- `graphify-out/`

Operational rules:

- Consult `graphify-out/GRAPH_REPORT.md` before broad raw-file search when the graph exists.
- Use `graphify-out/graph.html` for interactive navigation, `graphify-out/graph.json` for machine-readable graph data, and `graphify-out/GRAPH_REPORT.md` for the local audit summary.
- Treat `INFERRED` edges as leads rather than final truth; verify important claims against the underlying source files before relying on them.
- Rebuild the graph from inside `research_bcpcs_2026-04-18/` so outputs remain local to this workspace.
- Do not commit or push `graphify-out/` or transient `.graphify_*` files.

## 2. Authority boundary

- The BCPCS local graph is a workspace-scoped analysis artifact, not repo-wide source of truth.
- For current production criteria, score authority, runtime prompt authority, and production workflow truth, still rely on:
  - `../AGENTS.md`
  - `../docs/chatgpt_current_status_handoff.md`
  - `../screening/results/results_manifest.json`
- This workspace may read repo-root inputs by path, but new outputs must remain under `research_bcpcs_2026-04-18/`.

## 3. Scope reminder

- The main architecture/method graph for this workspace intentionally excludes `runs/` and `graphify-out/` via `.graphifyignore`.
- If the task is specifically run-forensics on generated artifacts, inspect `runs/` directly or build a separate run-scoped graph instead of folding run outputs back into the main workspace graph.

## 4. Git artifact boundary

- Treat `reports/`, `src/`, protocol/schema/config files, run-level `run_manifest.json`, aggregate evaluation/validation summaries, and aggregate `assembled_results.json` as the durable review surface for BCPCS experiment results.
- Treat batch payloads, uploaded/downloaded batch files, cost ledgers, logs, direct-call transcripts, private inventories, and per-paper duplicate/raw review JSON under `runs/**/papers/` as generated execution internals.
- The execution internals above should remain ignored by repo-level `.gitignore` unless a future task explicitly promotes a specific artifact into a documented report or aggregate result.
