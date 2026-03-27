# Cutoff-Only Audit Against Gold

- Generated at: `2026-03-26T11:32:21.413693+00:00`
- Output dir: `screening/results/cutoff_only_audit_2026-03-26_rerun_2511_2601_new_cutoff`
- Decision rule: `cutoff_pass=true => include/keep`, `cutoff_pass=false => exclude`
- Gold label: `is_evidence_base=true`
- Candidate universe: unique `key` values from `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`

## Summary

| Paper | Total | Gold+ | Gold+ cutoffed | Correct via cutoff exclude | Correct via cutoff pass | All correct cutoffed? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `2511.13936` | 88 | 30 | 0 | 11 | 30 | no |
| `2601.19926` | 360 | 336 | 0 | 0 | 336 | no |

## 2511.13936

- Core question answer: No. Some correct predictions remain after cutoff (30 pass-and-correct, 0 gold-positive cutoffed).
- Key consistency verified: `True`
- Cutoff status counts: `{"before_start": 11, "passed": 77}`
- Confusion matrix: `{"tp": 30, "fp": 47, "tn": 11, "fn": 0}`
- Gold-positive papers removed by cutoff: `0`

- `(none)`

## 2601.19926

- Core question answer: No. Some correct predictions remain after cutoff (336 pass-and-correct, 0 gold-positive cutoffed).
- Key consistency verified: `True`
- Cutoff status counts: `{"passed": 360}`
- Confusion matrix: `{"tp": 336, "fp": 24, "tn": 0, "fn": 0}`
- Gold-positive papers removed by cutoff: `0`

- `(none)`
