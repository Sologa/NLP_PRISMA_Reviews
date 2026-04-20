# BCPCS Recall Repair V3 Report

這是 failure-slice dev diagnostic，不是 full benchmark，也不是 production workflow replacement。

## Promotion Requirements

- `gpt-5-nano` pure full127 auto F1 must be > `0.8000`.
- `gpt-5.4-nano` pure full127 auto F1 must be > `0.8000`.
- coverage must be >= `98.00%`; runtime failures must be `0`.
- primary22 is smoke-only; hybrid / reused-baseline / sentinel rows are not promotable.

## Results

| run_id | model | scope | auto F1 | precision | recall | TP/FP/TN/FN | coverage | decisions | status | cost |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- | --- | ---: |
| `bcpcs_recall_v3_canary5_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1` | `gpt-5-nano` | primary22 | 1.0000 | 1.0000 | 1.0000 | 5/0/0/0 | 100.00% | `{"include": 2, "maybe": 3}` | canary_passed | $0.002633 |
| `bcpcs_recall_v3_primary22_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1` | `gpt-5-nano` | primary22 | 0.9767 | 0.9545 | 1.0000 | 21/1/0/0 | 100.00% | `{"include": 8, "maybe": 14}` | guardrail_passed | $0.011181 |
| `bcpcs_recall_v3_full127_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1` | `gpt-5-nano` | full127 | 0.9328 | 0.8952 | 0.9737 | 111/13/0/3 | 100.00% | `{"exclude": 3, "include": 50, "maybe": 74}` | guardrail_passed | $0.063954 |
| `bcpcs_recall_v3_canary5_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1` | `gpt-5.4-nano` | primary22 | 1.0000 | 1.0000 | 1.0000 | 5/0/0/0 | 100.00% | `{"maybe": 5}` | canary_passed | $0.006645 |
| `bcpcs_recall_v3_primary22_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1` | `gpt-5.4-nano` | primary22 | 0.9767 | 0.9545 | 1.0000 | 21/1/0/0 | 100.00% | `{"include": 4, "maybe": 18}` | guardrail_passed | $0.030170 |
| `bcpcs_recall_v3_full127_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1` | `gpt-5.4-nano` | full127 | 0.9461 | 0.8976 | 1.0000 | 114/13/0/0 | 100.00% | `{"include": 23, "maybe": 104}` | guardrail_passed | $0.170313 |

## Queue Status

```json
{
  "created_at": "2026-04-20T07:50:09+00:00",
  "policy_version": "pure_model_full127_gt_0p8_v3_recall_repair",
  "statuses": [
    {
      "run_id": "bcpcs_recall_v3_canary5_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1",
      "model": "gpt-5-nano",
      "kind": "canary5",
      "status": "canary_passed",
      "guardrail": {
        "created_at": "2026-04-20T07:50:20+00:00",
        "scope": "primary22",
        "canary": true,
        "threshold_name": "canary_runtime_only",
        "passed": true,
        "observed_auto_f1": 1.0,
        "observed_conservative_f1": 1.0,
        "observed_coverage": 1.0,
        "observed_runtime_failure_count": 0,
        "thresholds": {
          "auto_f1_must_be_greater_than": 0.8,
          "coverage_min": 0.98,
          "runtime_failure_max": 0,
          "hybrid_or_reused_baseline_runs_promotable": false
        }
      }
    },
    {
      "run_id": "bcpcs_recall_v3_primary22_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1",
      "model": "gpt-5-nano",
      "kind": "primary22",
      "status": "guardrail_passed",
      "guardrail": {
        "created_at": "2026-04-20T07:50:44+00:00",
        "scope": "primary22",
        "canary": false,
        "threshold_name": "primary22_smoke_v3",
        "passed": true,
        "observed_auto_f1": 0.9767441860465117,
        "observed_conservative_f1": 0.9767441860465117,
        "observed_coverage": 1.0,
        "observed_runtime_failure_count": 0,
        "thresholds": {
          "auto_f1_must_be_greater_than": 0.8,
          "coverage_min": 0.98,
          "runtime_failure_max": 0,
          "hybrid_or_reused_baseline_runs_promotable": false
        }
      }
    },
    {
      "run_id": "bcpcs_recall_v3_full127_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1",
      "model": "gpt-5-nano",
      "kind": "full127",
      "status": "guardrail_passed",
      "guardrail": {
        "created_at": "2026-04-20T07:52:51+00:00",
        "scope": "full127",
        "canary": false,
        "threshold_name": "pure_model_full127_v3",
        "passed": true,
        "observed_auto_f1": 0.9327731092436974,
        "observed_conservative_f1": 0.9327731092436974,
        "observed_coverage": 1.0,
        "observed_runtime_failure_count": 0,
        "thresholds": {
          "auto_f1_must_be_greater_than": 0.8,
          "coverage_min": 0.98,
          "runtime_failure_max": 0,
          "hybrid_or_reused_baseline_runs_promotable": false
        }
      }
    },
    {
      "run_id": "bcpcs_recall_v3_canary5_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1",
      "model": "gpt-5.4-nano",
      "kind": "canary5",
      "status": "canary_passed",
      "guardrail": {
        "created_at": "2026-04-20T07:52:54+00:00",
        "scope": "primary22",
        "canary": true,
        "threshold_name": "canary_runtime_only",
        "passed": true,
        "observed_auto_f1": 1.0,
        "observed_conservative_f1": 1.0,
        "observed_coverage": 1.0,
        "observed_runtime_failure_count": 0,
        "thresholds": {
          "auto_f1_must_be_greater_than": 0.8,
          "coverage_min": 0.98,
          "runtime_failure_max": 0,
          "hybrid_or_reused_baseline_runs_promotable": false
        }
      }
    },
    {
      "run_id": "bcpcs_recall_v3_primary22_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1",
      "model": "gpt-5.4-nano",
      "kind": "primary22",
      "status": "guardrail_passed",
      "guardrail": {
        "created_at": "2026-04-20T07:53:09+00:00",
        "scope": "primary22",
        "canary": false,
        "threshold_name": "primary22_smoke_v3",
        "passed": true,
        "observed_auto_f1": 0.9767441860465117,
        "observed_conservative_f1": 0.9767441860465117,
        "observed_coverage": 1.0,
        "observed_runtime_failure_count": 0,
        "thresholds": {
          "auto_f1_must_be_greater_than": 0.8,
          "coverage_min": 0.98,
          "runtime_failure_max": 0,
          "hybrid_or_reused_baseline_runs_promotable": false
        }
      }
    },
    {
      "run_id": "bcpcs_recall_v3_full127_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1",
      "model": "gpt-5.4-nano",
      "kind": "full127",
      "status": "guardrail_passed",
      "guardrail": {
        "created_at": "2026-04-20T07:54:14+00:00",
        "scope": "full127",
        "canary": false,
        "threshold_name": "pure_model_full127_v3",
        "passed": true,
        "observed_auto_f1": 0.946058091286307,
        "observed_conservative_f1": 0.946058091286307,
        "observed_coverage": 1.0,
        "observed_runtime_failure_count": 0,
        "thresholds": {
          "auto_f1_must_be_greater_than": 0.8,
          "coverage_min": 0.98,
          "runtime_failure_max": 0,
          "hybrid_or_reused_baseline_runs_promotable": false
        }
      }
    }
  ],
  "promoted_run_ids_by_model": {
    "gpt-5-nano": "bcpcs_recall_v3_full127_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1",
    "gpt-5.4-nano": "bcpcs_recall_v3_full127_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1"
  },
  "overall_passed": true,
  "completed_at": "2026-04-20T07:54:14+00:00",
  "run_ids": [
    "bcpcs_recall_v3_canary5_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1",
    "bcpcs_recall_v3_primary22_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1",
    "bcpcs_recall_v3_full127_gpt-5-nano_recall_boundary_maybe_v1_2026-04-20_v1",
    "bcpcs_recall_v3_canary5_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1",
    "bcpcs_recall_v3_primary22_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1",
    "bcpcs_recall_v3_full127_gpt-54-nano_recall_boundary_maybe_v1_2026-04-20_v1"
  ],
  "stop_reason": "all_required_pure_models_passed_v3"
}
```

## Threshold Math

```json
{
  "positive_count": 114,
  "negative_count": 13,
  "rows": [
    {
      "fp": 0,
      "min_tp_for_f1_gt_0.8": 77,
      "min_recall": 0.6754385964912281
    },
    {
      "fp": 1,
      "min_tp_for_f1_gt_0.8": 77,
      "min_recall": 0.6754385964912281
    },
    {
      "fp": 2,
      "min_tp_for_f1_gt_0.8": 78,
      "min_recall": 0.6842105263157895
    },
    {
      "fp": 3,
      "min_tp_for_f1_gt_0.8": 79,
      "min_recall": 0.6929824561403509
    },
    {
      "fp": 4,
      "min_tp_for_f1_gt_0.8": 79,
      "min_recall": 0.6929824561403509
    },
    {
      "fp": 5,
      "min_tp_for_f1_gt_0.8": 80,
      "min_recall": 0.7017543859649122
    },
    {
      "fp": 6,
      "min_tp_for_f1_gt_0.8": 81,
      "min_recall": 0.7105263157894737
    },
    {
      "fp": 7,
      "min_tp_for_f1_gt_0.8": 81,
      "min_recall": 0.7105263157894737
    },
    {
      "fp": 8,
      "min_tp_for_f1_gt_0.8": 82,
      "min_recall": 0.7192982456140351
    },
    {
      "fp": 9,
      "min_tp_for_f1_gt_0.8": 83,
      "min_recall": 0.7280701754385965
    },
    {
      "fp": 10,
      "min_tp_for_f1_gt_0.8": 83,
      "min_recall": 0.7280701754385965
    },
    {
      "fp": 11,
      "min_tp_for_f1_gt_0.8": 84,
      "min_recall": 0.7368421052631579
    },
    {
      "fp": 12,
      "min_tp_for_f1_gt_0.8": 85,
      "min_recall": 0.7456140350877193
    },
    {
      "fp": 13,
      "min_tp_for_f1_gt_0.8": 85,
      "min_recall": 0.7456140350877193
    }
  ],
  "all_positive_f1_ceiling": 0.946058091286307
}
```

## Interpretation

- Direct API cost for this V3 recall repair queue: `$0.284896`.
- The V3 profile is recall-biased by design: boundary/incomplete cases are compiled to `maybe` rather than `exclude`.
- `maybe` is positive under repo default `include_or_maybe`; maybe counts are therefore reported explicitly as regression-risk context.
- Gold/prior verdict/error taxonomy did not enter reviewer prompts; gold is only used after completion for evaluation and taxonomy.
