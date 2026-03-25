# Prompt-only Runtime Realignment 實驗報告

## 1. 實驗範圍
本輪是 **嚴格的 prompt-only 實驗**，只調整 runtime reviewer 的 prompt wording，保留既有輸入/輸出 schema：
- `reasoning`
- `evaluation`

不修改的項目：
- `topic_pipeline.py`
- aggregation policy
- senior override
- criteria serialization
- `missing_fulltext` 處理
- `criteria_jsons/*.json`
- markdown template 檔案
- 任何新 prompt loader 或輸出 schema

## 2. 本輪修改檔案
1. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py`
2. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`

`basic_reviewer.py` **未修改**。

## 3. Prompt 對齊到 template 精神（不改 schema）

### Stage 1 (`title_abstract_reviewer.py`)
- 明確宣告：**Stage 1、只看 title + abstract**。
- 明確禁止：不假設 full text。
- 增加高召回規則：證據不足不直接排除，優先回傳中性分數 `3`。
- 明確要求：主題相關但證據不足者保留為 `maybe`。
- 強化 reasoning 要求：`reasoning` 要簡潔，說明為何打該分數與缺什麼證據。
- `generic_prompt_any` 與 `generic_prompt_all` 文字語氣同步。

### Stage 2 (`fulltext_reviewer.py`)
- 明確宣告：**Stage 2、基於 full text**。
- 明確要求逐條使用全文證據作判斷，避免主觀印象。
- 要求 reasoning 指明關鍵依據（I/E criteria 級別）而非只講結論。
- 要求不可硬猜：找不到證據就保守降分。
- `generic_prompt_any` 與 `generic_prompt_all` 文字語氣同步。

輸出仍維持 `response_format`：`{"reasoning": str, "evaluation": int}`（無新增 JSON schema）。

## 4. 執行與測試指令

### 基礎基準輸出（before）
- Stage 1：
```bash
python3 scripts/screening/evaluate_review_f1.py <pid> \
  --results screening/results/<pid>_full/run01/latte_review_results.run01.json \
  --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl \
  --positive-mode include_or_maybe \
  --save-report screening/results/<pid>_full/review_before_stage1_report.json
```
- Stage 1 + fulltext（combine）：
```bash
python3 scripts/screening/evaluate_review_f1.py <pid> \
  --results screening/results/<pid>_full/latte_fulltext_review_from_run01.json \
  --base-review-results screening/results/<pid>_full/run01/latte_review_results.run01.json \
  --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl \
  --combine-with-base --positive-mode include_or_maybe \
  --save-report screening/results/<pid>_full/combined_before_fulltext_report.json
```

### 實驗重跑（after）
- 執行方式（四篇皆相同）：
```bash
PAPER_ID=<pid> TOP_K=0 ENABLE_FULLTEXT_REVIEW=1 PIPELINE_PYTHON=python3 RUN_TAG=prompt_only_v1 FULLTEXT_REVIEW_MODE=inline FULLTEXT_ROOT=refs/<pid>/mds bash scripts/screening/run_review_smoke5.sh
```

### 實驗結果評估（after）
- Stage 1：
```bash
python3 scripts/screening/evaluate_review_f1.py <pid> \
  --results screening/results/<pid>_full/latte_review_results.prompt_only_v1.json \
  --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl \
  --positive-mode include_or_maybe \
  --save-report screening/results/<pid>_full/review_after_stage1_prompt_only_v1_report.json
```
- Stage 1 + fulltext（combine）：
```bash
python3 scripts/screening/evaluate_review_f1.py <pid> \
  --results screening/results/<pid>_full/latte_fulltext_review_results.prompt_only_v1.json \
  --base-review-results screening/results/<pid>_full/latte_review_results.prompt_only_v1.json \
  --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl \
  --combine-with-base --positive-mode include_or_maybe \
  --save-report screening/results/<pid>_full/combined_after_fulltext_report.json
```

## 5. before / after 指標（含 confusion matrix）

### Stage 1

| PID | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2307.05527 before | 138 | 3 | 44 | 33 | 0.9787 | 0.8070 | 0.8846 |
| 2307.05527 after | 165 | 8 | 39 | 6 | 0.9538 | 0.8713 | 0.9551 |
| 2409.13738 before | 17 | 8 | 49 | 4 | 0.6800 | 0.8095 | 0.7391 |
| 2409.13738 after | 21 | 24 | 33 | 0 | 0.4667 | 1.0000 | 0.6364 |
| 2511.13936 before | 20 | 1 | 53 | 10 | 1.0000 | 0.7000 | 0.8235 |
| 2511.13936 after | 30 | 16 | 38 | 0 | 0.6522 | 1.0000 | 0.7895 |
| 2601.19926 before | 265 | 5 | 18 | 70 | 0.9815 | 0.7910 | 0.8760 |
| 2601.19926 after | 328 | 14 | 9 | 7 | 0.9591 | 0.9642 | 0.9690 |

### Stage 1 + fulltext

| PID | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2307.05527 before | 116 | 3 | 44 | 55 | 0.9748 | 0.6784 | 0.8000 |
| 2307.05527 after | 157 | 5 | 42 | 14 | 0.9691 | 0.9181 | 0.9429 |
| 2409.13738 before | 17 | 7 | 50 | 4 | 0.7083 | 0.8095 | 0.7556 |
| 2409.13738 after | 21 | 9 | 48 | 0 | 0.7000 | 1.0000 | 0.8235 |
| 2511.13936 before | 20 | 1 | 53 | 10 | 1.0000 | 0.7000 | 0.8235 |
| 2511.13936 after | 27 | 5 | 49 | 3 | 0.8438 | 0.9000 | 0.8710 |
| 2601.19926 before | 251 | 0 | 23 | 84 | 1.0000 | 0.7493 | 0.8567 |
| 2601.19926 after | 306 | 0 | 23 | 29 | 1.0000 | 0.9134 | 0.9548 |

## 6. Stage 1 FN 變化

- 2307.05527：33 → 6（改善 27）
- 2409.13738：4 → 0（改善 4）
- 2511.13936：10 → 0（改善 10）
- 2601.19926：70 → 7（改善 63）

這次明確顯示 Stage 1 FN 大幅下降。

Fulltext 併回 stage1 的 FN 也下降：
- 2307.05527：55 → 14（改善 41）
- 2409.13738：4 → 0（改善 4）
- 2511.13936：10 → 3（改善 7）
- 2601.19926：84 → 29（改善 55）

## 7. FN key 差異（主要）

### 改善最多
- Stage 1 改善最大：`2601.19926`（FN 下降 70→7）
- Fulltext 改善最大：`2601.19926`（FN 下降 84→29）

### 幾乎沒變（FN）
- Stage 1 幾乎沒變：
  - 2409.13738：0 個 FN，幾乎全部轉正
  - 2511.13936：0 個 FN，幾乎全部轉正
- Fulltext 幾乎沒變（仍為 FN）：
  - `2307.05527` 有 13 筆
  - `2409.13738` 有 0 筆
  - `2511.13936` 有 3 筆
  - `2601.19926` 有 29 筆

完整 FN key 前後差異（含 improved / regressed / unchanged）已另存為：
`docs/prompt_only_runtime_fn_diff_raw.json`

### 回歸
- 只有 `2307.05527` Stage 1 出現 1 筆 FN 回歸：`boulianne2020study`
- 其他篇無 FN 回歸；fulltext 無回歸。

## 8. 這次實驗可回答什麼
1. 只改 runtime prompt wording 即可顯著提升召回（FN 明顯下降），尤其在 Stage 1。
2. 高召回導向的 Stage 1 提示（偏向 `3`/maybe）對 FN 有直接正向影響。
3. Stage 2（fulltext）在保留高召回基礎上，仍能進一步回收部分 FN。

## 9. 這次實驗不能回答什麼
1. 是否要改 aggregation policy / serialization / missing_fulltext 還需更多實驗；此輪只驗證 prompt 對召回與 FN 的邊際影響。
2. 不能直接回答精準率提升方案是否足夠，因為 Stage 1 precision 在某篇（2409.13738, 2511.13936）明顯下降為可接受 trade-off，可能需要後續 workflow 決策。
3. 不能證明「最終最終品質上限」；尚需改 `topic_pipeline` 或後續策略比較才能結論最適結構。

## 10. 實驗結論
在「**不改流程、不改 schema**」的硬限制下，prompt-only realignment 成功回收大量 FN，特別是 2601.19926（Stage 1 FN 下降 63、fulltext FN 下降 55）。
目前看來，**僅靠 prompt 調整能顯著改善 FN，但 precision trade-off 仍存在**，若要在 F1 進一步穩定上升且保持誤殺可控，建議下一輪再驗證：
- 輕微調整 Stage 1 欠缺證據的保留邊界（何時用 3，何時用 2）
- 再討論是否需要 minimal aggregation 規則調整。
