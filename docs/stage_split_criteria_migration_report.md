# Stage-Split Criteria Migration Report

This report reflects the cutoff-corrected repository state after enforcing pre-review cutoff-first semantics.

## Adopted production rules

- Runtime prompts: `scripts/screening/runtime_prompts/runtime_prompts.json`
- Criteria authority: `criteria_stage1/<paper_id>.json` and `criteria_stage2/<paper_id>.json`
- Cutoff authority: `cutoff_jsons/<paper_id>.json` is applied before reviewer routing

## Current authority metrics

| Paper | Stage 1 F1 | Combined F1 | Cutoff excluded |
| --- | ---: | ---: | ---: |
| `2409.13738` | 0.7500 | 0.8235 | 19 |
| `2511.13936` | 0.7407 | 0.7692 | 37 |

## Interpretation

- The adopted authority files remain the stage-split migration metrics for `2409` and `2511`.
- The numbers above supersede all pre-cutoff stage-split references elsewhere in the repository.
- Historical comparisons remain useful, but they must now be interpreted through cutoff-first semantics.
