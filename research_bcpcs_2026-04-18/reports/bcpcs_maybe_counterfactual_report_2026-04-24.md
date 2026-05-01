# BCPCS Maybe Counterfactual Report

Source run: `bcpcs_full_corpus_split_batch_gpt54mini_globalcheck_claimpackets_all4_2026-04-23_v1_fallback_aggregate`

這份報告驗證的不是 prompt 改寫，而是本地 counterfactual recompile：
- `display_all_maybe_to_exclude`: 純顯示層，把所有 `maybe` 都當成 `exclude`。
- `targeted_veto`: 只有當目前是 `maybe`，且 `proposed_decision=exclude`，並且已經有 inclusion `not_supported` 或 exclusion `supported` 時，才把 `maybe -> exclude`。
- `hard_veto`: 只要目前是 `maybe`，且有 inclusion `not_supported` 或 exclusion `supported`，就把 `maybe -> exclude`。

## Overall All4

| variant | F1 | precision | recall | TP / FP / TN / FN |
| --- | ---: | ---: | ---: | --- |
| `current_decision` | 0.8864 | 0.8101 | 0.9785 | 546 / 128 / 68 / 12 |
| `display_all_maybe_to_exclude` | 0.6753 | 0.9763 | 0.5161 | 288 / 7 / 189 / 270 |
| `targeted_veto` | 0.9188 | 0.9591 | 0.8817 | 492 / 21 / 175 / 66 |
| `hard_veto` | 0.9129 | 0.9679 | 0.8638 | 482 / 16 / 180 / 76 |

## 2409 and 2511

| paper_id | variant | F1 | precision | recall | TP / FP / TN / FN |
| --- | --- | ---: | ---: | ---: | --- |
| `2409.13738` | `current_decision` | 0.5122 | 0.3443 | 1.0000 | 21 / 40 / 23 / 0 |
| `2409.13738` | `display_all_maybe_to_exclude` | 0.6061 | 0.8333 | 0.4762 | 10 / 2 / 61 / 11 |
| `2409.13738` | `targeted_veto` | 0.8889 | 0.8333 | 0.9524 | 20 / 4 / 59 / 1 |
| `2409.13738` | `hard_veto` | 0.8636 | 0.8261 | 0.9048 | 19 / 4 / 59 / 2 |
| `2511.13936` | `current_decision` | 0.6105 | 0.4462 | 0.9667 | 29 / 36 / 22 / 1 |
| `2511.13936` | `display_all_maybe_to_exclude` | 0.5366 | 1.0000 | 0.3667 | 11 / 0 / 58 / 19 |
| `2511.13936` | `targeted_veto` | 0.8333 | 0.8333 | 0.8333 | 25 / 5 / 53 / 5 |
| `2511.13936` | `hard_veto` | 0.8571 | 0.9231 | 0.8000 | 24 / 2 / 56 / 6 |

## Flip Accounting

| variant | paper_id | flipped `maybe -> exclude` | gold-negative flips | gold-positive flips |
| --- | --- | ---: | ---: | ---: |
| `display_all_maybe_to_exclude` | `2409.13738` | 49 | 38 | 11 |
| `display_all_maybe_to_exclude` | `2511.13936` | 54 | 36 | 18 |
| `targeted_veto` | `2409.13738` | 37 | 36 | 1 |
| `targeted_veto` | `2511.13936` | 35 | 31 | 4 |
| `hard_veto` | `2409.13738` | 38 | 36 | 2 |
| `hard_veto` | `2511.13936` | 39 | 34 | 5 |

## Original 127 Slice

| variant | F1 | precision | recall | TP / FP / TN / FN |
| --- | ---: | ---: | ---: | --- |
| `current_decision` | 0.8957 | 0.8879 | 0.9035 | 103 / 13 / 0 / 11 |
| `display_all_maybe_to_exclude` | 0.3217 | 0.7931 | 0.2018 | 23 / 6 / 7 / 91 |
| `targeted_veto` | 0.6417 | 0.8219 | 0.5263 | 60 / 13 / 0 / 54 |
| `hard_veto` | 0.6000 | 0.8182 | 0.4737 | 54 / 12 / 1 / 60 |

## Verdict

- 有效方向不是 `exclude -> maybe`，而是把一部分本來就該排除的 `maybe` 收回成 `exclude`。
- 但也不是把所有 `maybe` 一刀切成 `exclude`。純顯示層 `display_all_maybe_to_exclude` 對 `2511` 反而更差，而且會重傷 `full127`。
- 這次 local verification 下，真正有用的是 `targeted_veto`：它明顯救回 `2409`，也大幅改善 `2511`，同時 overall all4 也優於 current。
