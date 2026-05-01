# BCPCS Full-Corpus vs `gpt-5.4-mini` Two-Stage Baseline

Date: `2026-04-23`

## Scope

- BCPCS run:
  - aggregate: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate`
  - summary: `research_bcpcs_2026-04-18/runs/bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate/evaluation_summary_full_corpus_split.json`
- Baseline:
  - family: `current_two_stage_direct_review`
  - model: `gpt-5.4-mini`
  - selection rule: per paper, choose the completed `gpt-5.4-mini` two-stage run with the highest combined F1 from `docs/single_reviewer_baseline/single_reviewer_runs_summary.csv`

## Overall

- BCPCS repo-compatible F1: `0.8864`
- Baseline combined F1: `0.8715`
- Delta: `+0.0148`
- BCPCS precision / recall: `0.8101 / 0.9785`
- Baseline precision / recall: `0.9714 / 0.7903`
- BCPCS TP / FP / TN / FN: `546 / 128 / 68 / 12`
- Baseline TP / FP / TN / FN: `441 / 13 / 183 / 117`
- BCPCS total cost: `$2.726664`

Interpretation:

- BCPCS wins on overall F1 because it recovers many more positives (`FN 117 -> 12`).
- The gain comes from a large precision tradeoff (`FP 13 -> 128`), not from dominating the baseline on all papers.

## Per Paper

| paper | BCPCS F1 | baseline F1 | delta | BCPCS P/R | baseline P/R | BCPCS TP/FP/TN/FN | baseline TP/FP/TN/FN | baseline run |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| `2307.05527` | 0.9072 | 0.8673 | +0.0398 | 0.8301 / 1.0000 | 0.9710 / 0.7836 | 171 / 35 / 16 / 0 | 134 / 4 / 47 / 37 | `20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601` |
| `2409.13738` | 0.5122 | 0.8095 | -0.2973 | 0.3443 / 1.0000 | 0.8095 / 0.8095 | 21 / 40 / 23 / 0 | 17 / 4 / 59 / 4 | `20260408_full_gpt54mini_low_2stagedirect_2409_2511` |
| `2511.13936` | 0.6105 | 0.9123 | -0.3018 | 0.4462 / 0.9667 | 0.9630 / 0.8667 | 29 / 36 / 22 / 1 | 26 / 1 / 57 / 4 | `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511` |
| `2601.19926` | 0.9587 | 0.8742 | +0.0845 | 0.9503 / 0.9673 | 0.9851 / 0.7857 | 325 / 17 / 7 / 11 | 264 / 4 / 20 / 72 | `20260417_retry1_gpt54mini_xhigh_2stagedirect_2307_2601` |

## Notes

- `2307` and `2601` benefit materially from the BCPCS recall-first behavior.
- `2409` and `2511` remain the main failure papers for this BCPCS full-corpus configuration; recall stays high, but precision collapses.
- The final aggregate uses the original completed child runs for `2307` / `2409` / `2511`, plus fallback run `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926_fallback_shard90b` for `2601`.
- The original `2601` child run `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1__2601_19926` was not used in the final aggregate because its 359-request batch remained stuck at `357 / 359` completed for an extended period.
