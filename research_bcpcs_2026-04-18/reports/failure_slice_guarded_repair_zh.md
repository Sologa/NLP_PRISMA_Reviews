# BCPCS Guarded Repair Report

這是 failure-slice dev diagnostic，不是 full benchmark，也不是 unbiased improvement claim。

## Locked Guardrails

- primary22 auto F1 must be >= `0.8000`
- full127 all auto F1 must be >= `0.6378`
- coverage must be >= `98.00%`
- runtime failures must be `0`

## Run Results

| run_id | scope | model | auto F1 | conservative F1 | coverage | runtime failures | guardrail | cost |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| `bcpcs_guarded_primary22_smoke_gpt54nano_xhigh_allroute_evidencepacket_2026-04-20_v1` | primary22 | `gpt-5.4-nano` | 0.0000 | 0.0000 | 0.00% | 22 | failed | $0.407489 |
| `bcpcs_guarded_primary22_smoke_gpt5nano_high_allroute_evidencepacket_2026-04-20_v1` | primary22 | `gpt-5-nano` | 0.0000 | 0.0000 | 0.00% | 22 | failed | $0.120195 |

Guarded repair total cost: `$0.5276841`.

## Failure Signature

The queue stopped at primary22 smoke. No full127 guarded repair batch was submitted.

| run_id | phase | success | failure | missing | dominant failure |
| --- | --- | ---: | ---: | ---: | --- |
| `bcpcs_guarded_primary22_smoke_gpt54nano_xhigh_allroute_evidencepacket_2026-04-20_v1` | `stage1_review` | 22 | 0 | 0 | none |
| `bcpcs_guarded_primary22_smoke_gpt54nano_xhigh_allroute_evidencepacket_2026-04-20_v1` | `stage2_review_evidence_packet` | 8 | 14 | 0 | `JSONDecodeError`, empty assistant content |
| `bcpcs_guarded_primary22_smoke_gpt5nano_high_allroute_evidencepacket_2026-04-20_v1` | `stage1_review` | 22 | 0 | 0 | none |
| `bcpcs_guarded_primary22_smoke_gpt5nano_high_allroute_evidencepacket_2026-04-20_v1` | `stage2_review_evidence_packet` | 16 | 6 | 0 | `JSONDecodeError`, empty assistant content |

The sampled failed evidence-packet rows had the same failure mode:

- `finish_reason=length`
- assistant message content length `0`
- `completion_tokens=16384`
- `reasoning_tokens=16384`

This means the evidence-packet pass still exhausted the entire completion budget in reasoning before producing JSON. The two-pass protocol did not repair the core runtime failure; it moved the failure from final Stage 2 to the evidence extraction pass.

## Validation Notes

- Source inventory counts remained `127 / 22 / 105`.
- Forbidden prompt hit count was `0` for both smoke runs.
- StageReviewOutput schema failures were `0` for collected Stage 1 outputs.
- Cost ledger validation was OK.
- The output path audit reported unrelated modified files under `bib/per_SR_cleaned/.../reference_oracle.jsonl`; this guarded repair code did not write those paths. All new guarded repair artifacts are under `research_bcpcs_2026-04-18/`.

## Queue Status

```json
{
  "created_at": "2026-04-20T05:10:50+00:00",
  "primary_smoke_passed": false,
  "full127_submitted": false,
  "statuses": [
    {
      "run_id": "bcpcs_guarded_primary22_smoke_gpt54nano_xhigh_allroute_evidencepacket_2026-04-20_v1",
      "status": "parse_or_missing_failure",
      "guardrail": {
        "created_at": "2026-04-20T04:45:55+00:00",
        "scope": "primary22",
        "passed": false,
        "observed_auto_f1": 0.0,
        "observed_coverage": 0.0,
        "observed_runtime_failure_count": 22,
        "thresholds": {
          "primary22_auto_f1_min": 0.8,
          "full127_all_auto_f1_min": 0.6378,
          "coverage_min": 0.98,
          "runtime_failure_max": 0
        }
      }
    },
    {
      "run_id": "bcpcs_guarded_primary22_smoke_gpt5nano_high_allroute_evidencepacket_2026-04-20_v1",
      "status": "parse_or_missing_failure",
      "guardrail": {
        "created_at": "2026-04-20T05:10:50+00:00",
        "scope": "primary22",
        "passed": false,
        "observed_auto_f1": 0.0,
        "observed_coverage": 0.0,
        "observed_runtime_failure_count": 22,
        "thresholds": {
          "primary22_auto_f1_min": 0.8,
          "full127_all_auto_f1_min": 0.6378,
          "coverage_min": 0.98,
          "runtime_failure_max": 0
        }
      }
    }
  ],
  "stop_reason": "primary22_smoke_guardrail_failed"
}
```

## Interpretation

- 任何低於 locked guardrail 的 variant 都只能保留為 failed diagnostic，不得 promote。
- dev analyzer 可使用 gold 做錯誤分類，但 gold/error taxonomy 沒有進入 reviewer prompts。
- 如果 primary smoke 失敗，full127 不會提交。
- 這次 primary smoke 已失敗，因此沒有修好；不能宣稱分數提升。
- 下一輪若繼續修，應先在 synthetic/minimal fixtures 上解決 `reasoning_tokens == max_completion_tokens` 的空輸出問題，例如降低 evidence prompt 複雜度、改非 reasoning extraction、或把 evidence extraction 改成 deterministic/local prefilter 後再讓模型做短 decision JSON。
