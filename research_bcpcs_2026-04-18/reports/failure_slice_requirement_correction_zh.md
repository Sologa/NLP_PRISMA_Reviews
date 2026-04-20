# BCPCS Failure-Slice >0.8 Promotion Correction

這是 corrective status report。它覆蓋先前 direct repair report 中把 hybrid row 視為 promoted 的說法。

## V2 Promotion Rule

- `gpt-5-nano` 和 `gpt-5.4-nano` 都必須各自以純模型 full127 run 達到 `auto_decidable_f1 > 0.8`。
- primary22 只能當 smoke gate，不能替代 full127。
- hybrid / reused-baseline / mixed-model result 只能是 diagnostic，不可 promotion。
- coverage 必須 `>= 98%`，runtime failures 必須 `0`。

## Current Status

- overall_passed：`true`
- promoted_run_ids：`['bcpcs_recall_v3_full127_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1', 'bcpcs_recall_v3_full127_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1']`

| model | best pure full127 run | auto F1 | coverage | runtime failures | passes v2 |
| --- | --- | ---: | ---: | ---: | --- |
| `gpt-5-nano` | `bcpcs_recall_v3_full127_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1` | 0.9328 | 100.00% | 0 | yes |
| `gpt-5.4-nano` | `bcpcs_recall_v3_full127_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1` | 0.9461 | 100.00% | 0 | yes |

## Corrected Interpretation

- 目前兩個 required pure-model full127 runs 都達到 `auto_decidable_f1 > 0.8`。
- 達標 run 來自 V3 recall repair profile；它是 recall-biased failure-slice diagnostic，不是 full benchmark 或 production replacement。
- `maybe` 在 repo default `include_or_maybe` metric 下計為 positive，因此必須和 maybe counts / regression risk 一起解讀。
- `bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1` 仍是 `diagnostic_only_not_promoted`，因為它混用了 direct primary rows 與 locked-baseline secondary rows。
- primary22 表現只能作 smoke success，不能替代 full127 promotion。
