# BCPCS Direct Repair Report

這是 failure-slice dev diagnostic，不是 full benchmark，也不是 unbiased improvement claim。

**Correction 2026-04-20**：先前版本把 hybrid row 標成 promoted；這在 V2 promotion rule 下是錯的。Hybrid / reused-baseline / mixed-model result 只能作 diagnostic，不能代表 `gpt-5-nano` 或 `gpt-5.4-nano` 任一純模型達標。

**Superseded by V3 recall repair**：後續 `recall_boundary_maybe_v1` pure-model full127 runs 已另行記錄於 `failure_slice_recall_repair_zh.md` 和 `failure_slice_promotion_status_v3.json`。本報告只描述 direct local-packet profile 的 failed diagnostic。

## Promotion Requirements V2

- `gpt-5-nano` full127 pure-model auto F1 must be > `0.8000`
- `gpt-5.4-nano` full127 pure-model auto F1 must be > `0.8000`
- primary22 auto F1 must be > `0.8000`, but primary22 is smoke-only
- coverage must be >= `98.00%`
- runtime failures must be `0`
- hybrid / reused-baseline / mixed-model rows cannot be promoted

## Run Results

| run_id | scope | model | effort | auto F1 | conservative F1 | coverage | runtime failures | V2 status | cost |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| `bcpcs_direct_canary5_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1` | primary22 | `gpt-5.4-nano` | `xhigh` | 0.7500 | 0.7500 | 100.00% | 0 | smoke_failed | $0.039764 |
| `bcpcs_direct_primary22_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1` | primary22 | `gpt-5.4-nano` | `xhigh` | 0.8108 | 0.8108 | 100.00% | 0 | smoke_passed_only | $0.134214 |
| `bcpcs_direct_full127_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1` | full127 | `gpt-5.4-nano` | `xhigh` | 0.5955 | 0.5889 | 98.43% | 0 | failed_full127_f1 | $0.668162 |
| `bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1` | full127 | `hybrid:gpt-5.4-nano-direct-primary+gpt-5-nano-locked-baseline-secondary` | `None` | 0.6806 | 0.6806 | 100.00% | 0 | diagnostic_only_not_promoted | $0.668162 |

## Corrected Interpretation

- Direct repair actual API cost from non-reused runs: `$0.842139`.
- The pure `gpt-5.4-nano` direct full127 run did not meet the `>0.8` requirement.
- The earlier hybrid row made no API calls and mixed direct primary rows with locked-baseline secondary rows; it is invalid as promoted evidence under V2.
- Existing `gpt-5-nano` full127 runs are also below `>0.8`, with best observed full127 auto F1 `0.6378`.
- No current pure-model full127 run is promoted.
- Direct prompts used deterministic evidence packets; gold/prior verdict/error taxonomy did not enter reviewer prompts.
- Global output path audit may remain false if pre-existing dirty files outside research are present; direct run uses pre/post path audit for new writes.

See also:

- `reports/failure_slice_requirement_correction_zh.md`
- `reports/failure_slice_promotion_status_v2.json`
