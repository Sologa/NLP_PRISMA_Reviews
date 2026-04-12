# Token / Cost Summary

- run_id: `20260408_full_gpt54mini_xhigh_2stagedirect_2409_2511`
- model: `gpt-5.4-mini`
- reasoning_effort: `xhigh`
- workflow: `single-reviewer-official-batch-2stage-direct-review`

## XHigh: Actual Batch Usage

### stage1_review

- requests: `146`
- input_tokens: `340901`
- cached_input_tokens: `0`
- output_tokens: `274048`
- reasoning_tokens: `235761`
- visible_output_tokens: `38287`
- total_tokens: `614949`
- estimated_batch_cost_usd: `0.744446`

### stage2_review

- requests: `50`
- input_tokens: `516738`
- cached_input_tokens: `0`
- output_tokens: `105150`
- reasoning_tokens: `88464`
- visible_output_tokens: `16686`
- total_tokens: `621888`
- estimated_batch_cost_usd: `0.430364`

### total

- input_tokens: `857639`
- cached_input_tokens: `0`
- output_tokens: `379198`
- reasoning_tokens: `324225`
- visible_output_tokens: `54973`
- total_tokens: `1236837`
- estimated_batch_cost_usd: `1.174810`

## Low vs XHigh

- low total input_tokens: `802983`
- low total output_tokens: `61605`
- low total reasoning_tokens: `10958`
- low total_tokens: `864588`
- low estimated_batch_cost_usd: `0.439730`
- xhigh / low input_tokens: `1.068x`
- xhigh / low output_tokens: `6.156x`
- xhigh / low reasoning_tokens: `29.589x`
- xhigh / low total_tokens: `1.431x`
- xhigh / low cost: `2.672x`

## Pricing Assumption

- official pricing page: `https://openai.com/api/pricing/`
- standard price shown there for `gpt-5.4 mini`: input `$0.750 / 1M`, output `$4.500 / 1M`
- Batch API page note: `Save 50% on inputs and outputs with the Batch API`
- therefore this summary uses effective Batch rates:
- input `$0.375 / 1M`
- output `$2.250 / 1M`
- cached input not used in this run

## Notes

- `reasoning_tokens` are already included inside `output_tokens`; do not price them twice.
- This actual `xhigh` cost is materially above the earlier proxy estimate.
- XHigh run report: `REPORT_zh.md`
- XHigh run manifest: `run_manifest.json`
