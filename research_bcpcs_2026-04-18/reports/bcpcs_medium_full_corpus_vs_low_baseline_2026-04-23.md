# BCPCS Medium Full-Corpus Result

Date: `2026-04-23`

## Scope

- Medium aggregate: `bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate`
- Summary: `research_bcpcs_2026-04-18/runs/bcpcs_full_corpus_split_batch_gpt54mini_medium_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate/evaluation_summary_full_corpus_split.json`
- Low aggregate comparator: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate`
- Original `full127` reference gate: `bcpcs_recall_v4g_full127_gpt54mini_globalcheck_claimpackets_compilerrelaxcov_2026-04-23_v1`
- Baseline comparator: current best `gpt-5.4-mini` two-stage single-reviewer bundle used in the existing BCPCS comparison report

## Overall

- Medium repo-compatible F1: `0.8654`
- Medium precision / recall: `0.8065 / 0.9337`
- Medium TP / FP / TN / FN: `521 / 125 / 71 / 37`
- Medium total cost: `$4.808946`

## Comparison

- Versus low BCPCS: F1 `0.8654` vs `0.8864` (`-0.0209`), cost `$4.808946` vs `$2.726664` (`+2.082282`)
- Versus best current two-stage baseline: F1 `0.8654` vs `0.8715` (`-0.0061`)

| paper_id | medium F1 | low F1 | best two-stage baseline F1 | medium vs baseline |
| --- | ---: | ---: | ---: | ---: |
| `2307.05527` | 0.8760 | 0.9072 | 0.8673 | +0.0087 |
| `2409.13738` | 0.5250 | 0.5122 | 0.8095 | -0.2845 |
| `2511.13936` | 0.5979 | 0.6105 | 0.9123 | -0.3144 |
| `2601.19926` | 0.9398 | 0.9587 | 0.8742 | +0.0656 |

## Original 127 Slice Inside Full-Corpus

- This slice reuses the exact `failure_slice_keys.json` from the promoted `full127` gate and evaluates those same keys inside the all4 full-corpus runs.
- Medium `127`-slice F1: `0.8279`
- Low `127`-slice F1: `0.8957`
- Reference pure-model `full127` gate auto F1: `0.8700`
- Medium `127`-slice precision / recall: `0.8812 / 0.7807`
- Medium `127`-slice TP / FP / TN / FN: `89 / 12 / 1 / 25`

| paper_id | `127` count | medium `127`-slice F1 |
| --- | ---: | ---: |
| `2307.05527` | 41 | 0.8451 |
| `2409.13738` | 5 | 0.3333 |
| `2511.13936` | 5 | 0.7500 |
| `2601.19926` | 76 | 0.8462 |

## Notes

- The medium run finished only after split-batch fallback plus sync last-mile completion for the stuck `2307` and `2409` shards.
- The medium aggregate cost above includes the full-rate sync correction for the rows completed outside Batch pricing.
- Result-wise, medium did not improve BCPCS. It costs more than low, loses overall to low, and still remains below the best current `gpt-5.4-mini` two-stage baseline.
