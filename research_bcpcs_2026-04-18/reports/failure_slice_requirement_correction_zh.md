# BCPCS Failure-Slice >0.8 Promotion Correction

這是 corrective status report。它覆蓋先前 direct repair report 中把 hybrid row 視為 promoted 的說法。

## V2 Promotion Rule

- `gpt-5-nano` 和 `gpt-5.4-nano` 都必須各自以純模型 full127 run 達到 `auto_decidable_f1 > 0.8`。
- primary22 只能當 smoke gate，不能替代 full127。
- hybrid / reused-baseline / mixed-model result 只能是 diagnostic，不可 promotion。
- coverage 必須 `>= 98%`，runtime failures 必須 `0`。

## Current Status

- overall_passed：`false`
- promoted_run_ids：`[]`

| model | best pure full127 run | auto F1 | coverage | runtime failures | passes v2 |
| --- | --- | ---: | ---: | ---: | --- |
| `gpt-5-nano` | `bcpcs_failure_slice_gpt5nano_2stage_async_2026-04-18_full127_v1` | 0.6378 | 100.00% | 0 | no |
| `gpt-5.4-nano` | `bcpcs_direct_full127_direct_gpt54nano_xhigh_localpacket_compactdecision_v1_2026-04-20_v1` | 0.5955 | 98.43% | 0 | no |

## Corrected Interpretation

- 目前沒有任何純模型 full127 run 達到 `>0.8`。
- `bcpcs_direct_hybrid_primary22_gpt54nano_xhigh_secondary_lockedbaseline_2026-04-20_v1` 是 `diagnostic_only_not_promoted`，因為它混用了 direct primary rows 與 locked-baseline secondary rows。
- `gpt-5.4-nano` direct profile 的 primary22 表現可作 smoke success，但 secondary105 regression 使 full127 不達標。
- 下一步應先做 FN/FP taxonomy 與 criteria/evidence-window coverage 分析，不應把目前 local-packet profile 直接擴大或宣稱成功。
