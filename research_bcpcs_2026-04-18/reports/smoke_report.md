# Smoke Report

This smoke run checks that the BCPCS graph and ledger interfaces can be populated from current repo inputs without touching production paths.

It uses a lexical stub, not an LLM retriever/verifier. The run is deliberately non-claim-bearing.

- Papers: 2409.13738, 2511.13936
- Candidates: 6
- Ledger rows: 24
- Routed cases: 3
- Auto include cases: 3
- Auto exclude cases: 0

Artifacts:

- `runs/smoke/smoke_ledger.jsonl`
- `runs/smoke/smoke_decisions.jsonl`
- `runs/smoke/smoke_summary.json`
