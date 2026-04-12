# Token / Cost Summary

- run_id: `20260408_full_gpt54mini_low_2stagedirect_2409_2511`
- model: `gpt-5.4-mini`
- reasoning_effort: `low`
- workflow: `single-reviewer-official-batch-2stage-direct-review`

## Low: Actual Batch Usage

### stage1_review

- requests: `146`
- input_tokens: `340901`
- cached_input_tokens: `0`
- output_tokens: `44791`
- reasoning_tokens: `8066`
- visible_output_tokens: `36725`
- estimated_batch_cost_usd: `0.228618`

### stage2_review

- requests: `45`
- input_tokens: `462082`
- cached_input_tokens: `0`
- output_tokens: `16814`
- reasoning_tokens: `2892`
- visible_output_tokens: `13922`
- estimated_batch_cost_usd: `0.211112`

### total

- input_tokens: `802983`
- cached_input_tokens: `0`
- output_tokens: `61605`
- reasoning_tokens: `10958`
- visible_output_tokens: `50647`
- total_tokens: `864588`
- estimated_batch_cost_usd: `0.439730`

## Pricing Assumption

- official pricing page: `https://openai.com/api/pricing/`
- standard price shown there for `gpt-5.4 mini`: input `$0.750 / 1M`, output `$4.500 / 1M`
- Batch API page note: `Save 50% on inputs and outputs with the Batch API`
- therefore this summary uses effective Batch rates:
- input `$0.375 / 1M`
- output `$2.250 / 1M`
- cached input not used in this run

## XHigh Estimate

No `xhigh` run exists in this repo for this workflow, so the estimate below is not an observed value.

Estimation method:

1. Keep current run input tokens fixed.
2. Keep visible output tokens fixed.
3. Scale only reasoning tokens.
4. Use the same-workflow-family historical low/high reasoning-token multiplier from:
   - `screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260322_041730Z/...`
   - `screening/results/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/runs/20260322_023703Z/...`
5. Historical `high / low` reasoning-token ratio on that reference run: `13.8166x`

### conservative xhigh proxy

- assumption: xhigh behaves roughly like the historical low->high reasoning jump
- estimated_output_tokens: `202049`
- estimated_total_tokens: `1005032`
- estimated_batch_cost_usd: `0.755729`

### stress xhigh proxy

- assumption: xhigh uses `25%` more reasoning tokens than the conservative proxy
- estimated_output_tokens: `239900`
- estimated_total_tokens: `1042883`
- estimated_batch_cost_usd: `0.840894`

## Notes

- `reasoning_tokens` are already included inside `output_tokens`; do not price them twice.
- Low run report: `REPORT_zh.md`
- Low run manifest: `run_manifest.json`
