# BCPCS `gpt-5.4-mini xhigh` Token-Budget Probe

## Scope

- Probe run: `bcpcs_xhigh_token_probe_2026-04-23_v1`
- Model / effort: `gpt-5.4-mini`, `xhigh`
- Mode: Batch API
- Source bodies: exact stage2 BCPCS request bodies copied from the failed all4 xhigh run; only `max_completion_tokens` was changed
- Sample rows:
  - `stage2_recall_repair_batch__2601.19926__rogers_primer_2020`
  - `stage2_recall_repair_batch__2601.19926__zhou_linguistic_2025`

Raw summary: [probe_summary.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/research_bcpcs_2026-04-18/runs/bcpcs_xhigh_token_probe_2026-04-23_v1/batch_jobs/probe_summary.json)

## Result

| budget | requests | parse successes | non-empty content | `length` finishes | total batch cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| `4096` | 2 | 0 | 0 | 2 | `$0.022468` |
| `12288` | 2 | 1 | 1 | 1 | `$0.045542` |
| `25000` | 2 | 2 | 2 | 0 | `$0.065425` |
| `32000` | 2 | 2 | 2 | 0 | `$0.042626` |
| `50000` | 2 | 2 | 2 | 0 | `$0.054996` |
| `65536` | 2 | 2 | 2 | 0 | `$0.043177` |

Thresholds:

- first budget with any non-empty content: `12288`
- first budget with any parse success: `12288`
- first budget with all parse successes: `25000`

Per-row threshold:

- `rogers_primer_2020`: first parse success at `12288`
- `zhou_linguistic_2025`: first parse success at `25000`

## Interpretation

- `4096` reproduces the original failure: both rows end with `finish_reason=length`, empty content, and `reasoning_tokens=4096`.
- `12288` is not enough as a stable BCPCS xhigh budget. One row succeeds, one row still burns the entire budget as reasoning and emits no JSON.
- `25000` is the first tested budget where both rows return valid parseable JSON.
- Higher caps do not imply proportionally higher realized cost. Once the model has enough headroom to finish, realized completion usage becomes non-monotonic:
  - `25000` average completion tokens on these two rows: `13642`
  - `32000` average completion tokens on these two rows: `8575.5`
- So the issue is headroom for hidden reasoning, not a need for a huge visible JSON payload.

## Cost Implication For All4 BCPCS

Current failed all4 xhigh run:

- reviewed rows: `707`
- actual prompt tokens: `4,002,046`
- actual output tokens: `2,803,341`
- actual total batch cost: `$7.808285`

If the full rerun used the same prompt inventory and needed a safe `25000` cap:

- empirical projection using this probe's realized `25000` average completion length: about `$23.20`
- hard ceiling if every reviewed row actually consumed the full `25000` output budget: about `$41.27`

If the full rerun used a `32000` cap:

- empirical projection using this probe's realized `32000` average completion length: about `$15.14`
- hard ceiling if every reviewed row actually consumed the full `32000` output budget: about `$52.40`

The empirical projections are only rough extrapolations from two `2601` rows. The ceiling figures are strict budget ceilings under Batch pricing.

## Bottom Line

- `4096` is definitely too small.
- `12288` is still not stable.
- The first tested budget that reliably worked on both sampled BCPCS xhigh rows was `25000`.
- For a serious all4 BCPCS xhigh rerun, `25000` is the first defensible starting point from this probe.
