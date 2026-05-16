# Primary Evidence Gate Overlay 2026-05-16

Experiment-only bundle for running a pre-review `primary_evidence_gate` on
`2409.13738`, `2511.13936`, and `2601.19926`. It excludes `2307.05527` from
the gate run and does not modify production pipeline code or criteria files.

The gate input is the reviewed, post-cutoff/post-artifact set from the latest
role-review corrected run: 65 + 75 + 359 = 499 rows.

## Commands

Prepare/serialize requests without submitting:

```bash
./.venv/bin/python single_reviewer_batch_experiments/primary_evidence_gate_overlay_2026-05-16/tools/run_experiment.py \
  --mode prepare \
  --run-id 20260516_gpt5nano_high_primary_gate_3papers
```

Submit, wait for terminal batch status, collect, overlay, and report:

```bash
./.venv/bin/python single_reviewer_batch_experiments/primary_evidence_gate_overlay_2026-05-16/tools/run_experiment.py \
  --mode run \
  --run-id 20260516_gpt5nano_high_primary_gate_3papers
```

Overlay only after a completed collect:

```bash
./.venv/bin/python single_reviewer_batch_experiments/primary_evidence_gate_overlay_2026-05-16/tools/run_experiment.py \
  --mode overlay \
  --run-id 20260516_gpt5nano_high_primary_gate_3papers
```
