# Cutoff-Only Audit Against Gold

- Generated at: `2026-03-26T07:09:40.419221+00:00`
- Output dir: `screening/results/cutoff_only_audit_2026-03-26`
- Decision rule: `cutoff_pass=true => include/keep`, `cutoff_pass=false => exclude`
- Gold label: `is_evidence_base=true`
- Candidate universe: unique `key` values from `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`

## Summary

| Paper | Total | Gold+ | Gold+ cutoffed | Correct via cutoff exclude | Correct via cutoff pass | All correct cutoffed? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `2307.05527` | 222 | 171 | 16 | 14 | 155 | no |
| `2409.13738` | 84 | 21 | 0 | 19 | 21 | no |
| `2511.13936` | 88 | 30 | 9 | 28 | 21 | no |
| `2601.19926` | 360 | 336 | 3 | 3 | 333 | no |

## 2307.05527

- Core question answer: No. Some correct predictions remain after cutoff (155 pass-and-correct, 16 gold-positive cutoffed).
- Key consistency verified: `True`
- Cutoff status counts: `{"before_start": 29, "passed": 192, "unparseable_published_date": 1}`
- Confusion matrix: `{"tp": 155, "fp": 37, "tn": 14, "fn": 16}`
- Gold-positive papers removed by cutoff: `16`

- `arik_neural_2018`
- `bando_statistical_2018`
- `bitton_modulated_2018`
- `brunner_symbolic_2018`
- `chen_musicality-novelty_2018`
- `dieleman_challenge_2018`
- `gu_multi-task_2018`
- `hsu_hierarchical_2018`
- `juvela_speaker-independent_2018`
- `kameoka_convs2s-vc_2020`
- `koh_rethinking_2018`
- `lee_conditional_2018`
- `wang_neural_2019-1`
- `wilkinson_generative_2019`
- `yoshimura_mel-cepstrum-based_2018`
- `zhou2018voice`

## 2409.13738

- Core question answer: No. Some correct predictions remain after cutoff (21 pass-and-correct, 0 gold-positive cutoffed).
- Key consistency verified: `True`
- Cutoff status counts: `{"after_end": 14, "passed": 65, "unparseable_published_date": 5}`
- Confusion matrix: `{"tp": 21, "fp": 44, "tn": 19, "fn": 0}`
- Gold-positive papers removed by cutoff: `0`

- `(none)`

## 2511.13936

- Core question answer: No. Some correct predictions remain after cutoff (21 pass-and-correct, 9 gold-positive cutoffed).
- Key consistency verified: `True`
- Cutoff status counts: `{"before_start": 32, "passed": 51, "unparseable_published_date": 5}`
- Confusion matrix: `{"tp": 21, "fp": 30, "tn": 28, "fn": 9}`
- Gold-positive papers removed by cutoff: `9`

- `cao2012combining`
- `cao2015speaker`
- `lopes2017modelling`
- `lotfian2016practical`
- `lotfian2016retrieving`
- `parthasarathy2016using`
- `parthasarathy2017ranking`
- `parthasarathy2018preference`
- `yang2010ranking`

## 2601.19926

- Core question answer: No. Some correct predictions remain after cutoff (333 pass-and-correct, 3 gold-positive cutoffed).
- Key consistency verified: `True`
- Cutoff status counts: `{"passed": 354, "unparseable_published_date": 6}`
- Confusion matrix: `{"tp": 333, "fp": 21, "tn": 3, "fn": 3}`
- Gold-positive papers removed by cutoff: `3`

- `Warstadt:etal:2020`
- `ettinger_what_2020`
- `kuncoro-etal-2020-syntactic`
