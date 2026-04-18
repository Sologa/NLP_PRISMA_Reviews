# Schema Validation

Validation used local Draft-2020-12-style schemas plus a minimal in-repo validator for the schema features used here.

| Artifact | Case | Status | Reason |
| --- | --- | --- | --- |
| eligibility_graph | valid_sample | passed |  |
| evidence_ledger | valid_sample | passed |  |
| boundary_atlas | valid_sample | passed |  |
| eligibility_graph | invalid_sample | rejected | $.claims[0]: missing required property 'claim_text' |
| evidence_ledger | invalid_sample | rejected | $.confidence: 1.5 above maximum 1 |
| boundary_atlas | invalid_sample | rejected | $.archetypes[0].source_provenance.built_before_eval: expected boolean, got str |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2307.05527.stage1.eligibility_graph.json | passed |  |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2307.05527.stage2.eligibility_graph.json | passed |  |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2409.13738.stage1.eligibility_graph.json | passed |  |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2409.13738.stage2.eligibility_graph.json | passed |  |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2511.13936.stage1.eligibility_graph.json | passed |  |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2511.13936.stage2.eligibility_graph.json | passed |  |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2601.19926.stage1.eligibility_graph.json | passed |  |
| eligibility_graph | runs/dry_run_loader/stub_graphs/2601.19926.stage2.eligibility_graph.json | passed |  |
| evidence_ledger | runs/dry_run_loader/sample_stage1_ledger.jsonl | passed | 24 records |
| evidence_ledger | runs/smoke/smoke_ledger.jsonl | passed | 24 records |
