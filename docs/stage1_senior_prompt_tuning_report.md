# Stage 1 SeniorLead Prompt Tuning（v4）實驗報告

## 1. 這輪實驗目標

在維持 Stage 1 路由不變（雙高直接 include、雙低直接 exclude、其他送 SeniorLead）的前提下，
只調整 Stage 1 `SeniorLead` 的 adjudicator wording，
目標是降低 `maybe` 濫用，提升 `2409.13738`、`2511.13936` 的 precision，
並盡量避免 `2307.05527`、`2601.19926` 的 recall 大幅掉落。

## 2. 這輪只修改哪些檔案

- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
  - 僅調整 `run_latte_review` 中 `SeniorLead` 的：
    - `backstory`
    - `additional_context`

其餘檔案（routing、aggregation、fulltext、pipeline 判斷邏輯、schema）未再變更。

## 3. Prompt 變更重點

### Stage 1 SeniorLead prompt（本輪）

- 明確加入：只能依據 `title + abstract + 兩位 junior output/evaluation`。
- 明確加入：不可假設 fulltext 補齊。
- 明確加入：`maybe (3)` 的門檻，條件為：
  1. 至少有一條可追溯核心 inclusion 正向訊號。
  2. 僅缺一個關鍵條件。
  3. 缺口在 title/abstract 無法直接判定。
- 明確加入：topic-adjacent/method/metadata-like 但無核心訊號時偏向 `exclude (1/2)`。
- 明確加入：reasoning 要包含「看得到什麼 / 缺什麼 / 為何排除」。

## 4. 測試方式

- Tag：`senior_prompt_tuned`
- 四篇：`2307.05527`, `2409.13738`, `2511.13936`, `2601.19926`
- 指令（已依序執行）：
  - Stage1：`run_review_smoke5.sh`
  - Stage1 評估：`evaluate_review_f1.py ... review_after_stage1_senior_prompt_tuned_report.json`
  - Combined 評估：`evaluate_review_f1.py ... combined_after_fulltext_senior_prompt_tuned_report.json`

## 5. 新版結果總覽（Stage1 與 Combined）

### Stage1 指標

| paper | prompt version | tp | fp | tn | fn | precision | recall | f1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2307.05527 | prompt_only_v1 | 165 | 8 | 39 | 6 | 0.9538 | 0.8713 | 0.9551 |
| 2307.05527 | senior_no_marker | 165 | 7 | 40 | 6 | 0.9551 | 0.8713 | 0.9113 |
| 2307.05527 | senior_prompt_tuned | **158** | **4** | **43** | **13** | **0.9753** | **0.9240** | **0.9489** |
| 2409.13738 | prompt_only_v1 | 21 | 24 | 33 | 0 | 0.4667 | 1.0000 | 0.6364 |
| 2409.13738 | senior_no_marker | 21 | 26 | 31 | 0 | 0.4468 | 1.0000 | 0.6176 |
| 2409.13738 | senior_prompt_tuned | **21** | **13** | **44** | 0 | **0.6176** | **1.0000** | **0.7636** |
| 2511.13936 | prompt_only_v1 | 30 | 16 | 38 | 0 | 0.6522 | 1.0000 | 0.7895 |
| 2511.13936 | senior_no_marker | 29 | 22 | 32 | 1 | 0.5686 | 0.7000 | 0.7160 |
| 2511.13936 | senior_prompt_tuned | **26** | **6** | **48** | **4** | **0.8125** | **0.7000** | **0.8387** |
| 2601.19926 | prompt_only_v1 | 328 | 14 | 9 | 7 | 0.9591 | 0.9642 | 0.9690 |
| 2601.19926 | senior_no_marker | 330 | 9 | 14 | 5 | 0.9761 | 0.9761 | 0.9761 |
| 2601.19926 | senior_prompt_tuned | **274** | **7** | **16** | **61** | **0.9751** | **0.8179** | **0.8896** |

### Combined 指標

| paper | prompt version | tp | fp | tn | fn | precision | recall | f1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2307.05527 | prompt_only_v1 | 157 | 5 | 42 | 14 | 0.9691 | 0.9181 | 0.9429 |
| 2307.05527 | senior_no_marker | 160 | 3 | 44 | 11 | 0.9796 | 0.8421 | 0.9057 |
| 2307.05527 | senior_prompt_tuned | **153** | **3** | **44** | **18** | **0.9808** | **0.8947** | **0.9358** |
| 2409.13738 | prompt_only_v1 | 21 | 9 | 48 | 0 | 0.7000 | 1.0000 | 0.8235 |
| 2409.13738 | senior_no_marker | 21 | 19 | 38 | 0 | 0.5250 | 1.0000 | 0.6885 |
| 2409.13738 | senior_prompt_tuned | **21** | **12** | **45** | **0** | **0.6364** | **1.0000** | **0.7778** |
| 2511.13936 | prompt_only_v1 | 27 | 5 | 49 | 3 | 0.8438 | 0.9000 | 0.8710 |
| 2511.13936 | senior_no_marker | 27 | 11 | 43 | 3 | 0.7105 | 0.9000 | 0.7941 |
| 2511.13936 | senior_prompt_tuned | **26** | **5** | **49** | **4** | **0.8387** | **0.7000** | **0.8525** |
| 2601.19926 | prompt_only_v1 | 306 | 0 | 23 | 29 | 1.0000 | 0.9134 | 0.9548 |
| 2601.19926 | senior_no_marker | 328 | 11 | 12 | 7 | 0.9758 | 0.9642 | 0.9700 |
| 2601.19926 | senior_prompt_tuned | **272** | **7** | **16** | **63** | **0.9749** | **0.8119** | **0.8860** |

## 6. Senior score 分佈（Stage1）

| paper | mode | sent-to-senior | sent % | score 1-2 | score 3 | score 4-5 | maybe(senior:3) | exclude(senior:1) | exclude(senior:2) | include(senior:4) | include(senior:5) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2307.05527 | senior_no_marker | 43 | 19.7% | 24 | 5 | 14 | 5 | 14 | 10 | 7 |
| 2307.05527 | senior_prompt_tuned | 47 | 21.6% | 32 | 10 | 5 | 10 | 24 | 8 | 0 |
| 2409.13738 | senior_no_marker | 55 | 70.5% | 27 | 21 | 7 | 21 | 11 | 16 | 2 |
| 2409.13738 | senior_prompt_tuned | 55 | 70.5% | 39 | 10 | 6 | 10 | 24 | 15 | 1 |
| 2511.13936 | senior_no_marker | 53 | 62.4% | 21 | 28 | 4 | 28 | 14 | 7 | 1 |
| 2511.13936 | senior_prompt_tuned | 58 | 68.2% | 45 | 9 | 4 | 9 | 23 | 22 | 1 |
| 2601.19926 | senior_no_marker | 215 | 60.1% | 16 | 165 | 34 | 165 | 10 | 6 | 22 |
| 2601.19926 | senior_prompt_tuned | 219 | 61.2% | 75 | 135 | 9 | 135 | 10 | 65 | 1 |

觀察：
- `maybe(senior:3)` 明顯下降，尤其在 2409 與 2511；
- 但在 2601 仍有大量 135 筆 `maybe`（主要是 review text 極薄/可讀性不足的長尾）。

## 7. 對比重點

### 2409.13738
- Stage1 precision：`0.4468 -> 0.6176`（較 `senior_no_marker` +17.1pp）
- Combined precision：`0.5250 -> 0.6364`
- recall 維持在 `1.0`
- no-marker 到 tuned 的 `maybe` 下降：21 -> 10；
  其中 14 筆由 `maybe` 轉為 `exclude`。

### 2511.13936
- Stage1 precision：`0.5686 -> 0.8125`（+24.4pp）
- Combined precision：`0.7105 -> 0.8387`（+12.8pp）
- recall：`0.7000 -> 0.7000`（有掉幅）
- no-marker 到 tuned 的 `maybe` 下降：28 -> 9；
  其中 20 筆由 `maybe` 轉為 `exclude`。

### 2307.05527
- precision 小幅上升（stage1 0.9551）但 recall下降（0.9240），F1 下降。
- 主要因更多 `maybe` 被壓到 `exclude`，但也伴隨多量 FN 擴大。

### 2601.19926
- recall 顯著下滑（stage1 0.8179、combined 0.8119），雖然 precision 還高。
- 主要掉法規來自大量曾為 `maybe` 的紀錄仍維持 maybe，但更多少數轉為 1/2 直接排除，造成 FN 增加 56。

## 8. Spot-check

| paper / key | old final | old senior | new final | new senior | 判定 |
|---|---|---|---|---|---|
| 2307.05527 / Suh2021AI | include (senior:5) | 5 | include (junior:4,5) | None（不送 senior） | 變成 juniors 直接通過，與新版 routing 一致，反而更穩健 |
| 2409.13738 / etikala2021extracting | maybe (senior:3) | 3 | maybe (senior:3) | 3 | 仍維持 3，理由改為更明確要求：非流程核心，不直接保留 |
| 2511.13936 / lotfian2016retrieving | maybe (senior:3) | 3 | maybe (senior:3) | 3 | 仍保持 3，但新版理由更明確：偏好學習證據不足以直接納入，因缺少 audio domain 明示 |
| 2511.13936 / han2020ordinal | include (senior:4) | 4 | include (junior:5,5) | None | 由 senior 覆核轉為 juniors 的高置信度 include，結果一致保留 |
| 2601.19926 / mccoy_right_2019 | maybe (senior:3) | 3 | maybe (senior:3) | 3 | 仍為 3；抽象僅 citation，缺可追溯方法細節，維持保留審閱 |

## 9. 結論（本輪回答）

- 對 `2409` 與 `2511` 的精準度有明顯改善，確實有回應「SeniorLead `maybe` 過多」問題。
- 但同時帶來明顯副作用：`2601.19926` recall 大幅下滑；`2307.05527` 也有小幅 recall 下降。
- 如果這輪目標是「可用 precision 提升且維持 recall」，仍需要下一步在 prompt 與路徑中加入更細緻的例外條件（例如：
  1) 對於訓練資料明顯 sparse 的 title-only/metadata-only，但有強語意聯繫的抽象，允許維持少量 `maybe`；
  2) 明確限制 `exclude` 的證據必要條件，避免把可補證性的 borderline 全部打掉）。

