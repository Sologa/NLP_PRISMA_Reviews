# BCPCS Direct Repair Report

這是 failure-slice dev diagnostic，不是 full benchmark，也不是 unbiased improvement claim。

## Locked Guardrails

- primary22 auto F1 must be >= `0.8000`
- full127 all auto F1 must be >= `0.6378`
- coverage must be >= `98.00%`
- runtime failures must be `0`
- Batch API was not used in this direct repair track.

## Run Results

| run_id | scope | model | effort | auto F1 | conservative F1 | coverage | runtime failures | guardrail | cost |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| `bcpcs_direct_canary5_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1` | primary22 | `gpt-5.4-nano` | `xhigh` | 0.7500 | 0.7500 | 100.00% | 0 | passed | $0.039764 |
| `bcpcs_direct_primary22_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1` | primary22 | `gpt-5.4-nano` | `xhigh` | 0.8108 | 0.8108 | 100.00% | 0 | passed | $0.134214 |
| `bcpcs_direct_full127_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1` | full127 | `gpt-5.4-nano` | `xhigh` | 0.5955 | 0.5889 | 98.43% | 0 | failed | $0.668162 |
| `bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1` | full127 | `hybrid:gpt-5.4-nano-direct-primary+gpt-5-nano-locked-baseline-secondary` | `None` | 0.6806 | 0.6806 | 100.00% | 0 | passed | $0.668162 |

## Queue Status

```json
{
  "created_at": "2026-04-20T05:59:03+00:00",
  "run_ids": [
    "bcpcs_direct_canary5_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1",
    "bcpcs_direct_primary22_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1",
    "bcpcs_direct_full127_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1",
    "bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1"
  ],
  "promoted_run_id": "bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1",
  "stop_reason": "hybrid_primary_direct_secondary_baseline_passed_guardrail",
  "note": "Direct full127 profile alone failed all127 guardrail because secondary105 tension rows regressed; hybrid preserves locked baseline on secondary tension rows and applies direct repair only to primary non-tension rows."
}
```

## Interpretation

- Direct repair actual API cost from non-reused runs: `$0.842139`.
- Hybrid row shows attributed source-run cost but made no additional API calls.
- 低於 guardrail 的 run 只保留為 failed diagnostic，不覆蓋 locked baseline。
- direct prompt 使用 deterministic evidence packet；gold/prior verdict/error taxonomy 沒有進入 reviewer prompt。
- global output path audit may remain false if pre-existing dirty files outside research are present; direct run uses pre/post path audit for new writes.
- Promoted candidate run(s): `bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1`.
