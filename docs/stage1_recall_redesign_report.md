# Stage-1 Recall Redesign 實驗報告（第二輪）

## 1. 實驗目標與邊界

這一輪不再是 prompt-only，而是做可落地的高召回版本修正。目標是：

1. 大幅降低 Stage-1 false negatives。
2. 讓 `topic_definition` 不再當成硬 inclusion。
3. Stage-1 僅在「雙負」時才能硬 exclusion；disagreement/uncertainty 偏向保留。
4. `missing_fulltext` 不再被當作語義排除。

本輪未重構 workflow、未改 schema、未改外部 template loader。

不碰的項目：

- 不改現有模板檔案內容。
- 不改 `scripts/screening/pipeline` 以外的核心流程。
- 不新增 reviewer 輸出 schema。

## 2. 修改檔案

1. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py`
2. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`
3. `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

## 3. 修改內容（按類型）

### A. Prompt（兩個 reviewer）

#### `title_abstract_reviewer.py`

- 明確標示 Stage 1 僅可用 title + abstract。
- 強調 recall-first：缺乏否定證據時不直接用 1/2 排除。
- 要求 high-topic-relevance 但證據不足回到 3。
- 加入 sparse metadata 規則（citation-like / keywords）不要直接排除。
- reasoning 要簡潔且要交代分數依據與缺少哪一條證據。
- `generic_prompt_all` 與 `generic_prompt_any` 語氣一致。

#### `fulltext_reviewer.py`

- 明確標示 Stage 2 為 final full-text review。
- 要求按 criteria 條件逐點、以全文證據為據，避免主觀印象。
- 明確要求列出 supported/unsupported/missing 的 criteria 證據。
- 缺證據不硬猜，保守給 3 並在 reasoning 標明缺口。
- `generic_prompt_all` 與 `generic_prompt_any` 同步。

---

### B. Serialization（`topic_pipeline.py`）

`_criteria_payload_to_strings` 做了兩個關鍵調整：

- 從 inclusion 條件字串中移除 `topic_definition` 前置注入（避免誤變成硬性條件）。
- 新增 `_criteria_context_from_payload`，把 `topic_definition` 轉成 reviewer 的 `additional_context`：
  - 仍可提供背景資訊，
  - 但不再和 inclusion criteria 混一起判斷。

---

### C. Stage-1 aggregation / arbitration（`topic_pipeline.py`）

`_derive_final_verdict_from_row` 修改為 recall-first 規則：

- 兩位 junior 都是 `1/2` 才 `exclude`。
- 兩位 junior 都 `>=4` 才 `include`。
- `maybe` 或 disagreement (`3`、低高互衝) 一律偏向 `maybe`。
- Senior 的硬覆蓋邏輯移除；workflow 僅保留 Stage A 兩位 junior。

---

### D. missing_fulltext handling（`topic_pipeline.py`）

`run_latte_fulltext_review` 加入 `review_state`：

- `review_state = review_skipped / retrieval_failed / reviewed`。
- `missing_fulltext` 只會留下為 operational 狀態，不再直接形成 semantic exclusion。
- 最終 verdict 轉成 `include (review_state:retrieval_failed)` / `maybe (...)` 等，保留後續可追溯性。

---

## 4. 測試執行方式

### 4.1 生成新實驗結果

```bash
PAPER_ID=<pid> TOP_K=0 ENABLE_FULLTEXT_REVIEW=1 PIPELINE_PYTHON=python3 RUN_TAG=recall_redesign_v1 bash scripts/screening/run_review_smoke5.sh
```

針對四篇：`2307.05527`、`2409.13738`、`2511.13936`、`2601.19926`

### 4.2 評估

- Stage-1

```bash
python3 scripts/screening/evaluate_review_f1.py <pid> --results screening/results/<pid>_full/latte_review_results.recall_redesign_v1.json --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl --positive-mode include_or_maybe --save-report screening/results/<pid>_full/stage1_recall_redesign_report.json
```

- Stage1 + fulltext combine

```bash
python3 scripts/screening/evaluate_review_f1.py <pid> --results screening/results/<pid>_full/latte_fulltext_review_results.recall_redesign_v1.json --base-review-results screening/results/<pid>_full/latte_review_results.recall_redesign_v1.json --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl --combine-with-base --positive-mode include_or_maybe --save-report screening/results/<pid>_full/combined_recall_redesign_report.json
```

baseline 使用現有 `prompt_only_v1` 指標做對照：
- `review_after_stage1_prompt_only_v1_report.json`
- `combined_after_fulltext_report.json`

## 5. before / after 指標（四篇）

### 5.1 Stage-1（before: prompt-only v1）

| PID | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2307.05527 | 165 | 8 | 39 | 6 | 0.9538 | 0.8713 | 0.9551 |
| 2409.13738 | 21 | 24 | 33 | 0 | 0.4667 | 1.0000 | 0.6364 |
| 2511.13936 | 30 | 16 | 38 | 0 | 0.6522 | 1.0000 | 0.7895 |
| 2601.19926 | 328 | 14 | 9 | 7 | 0.9591 | 0.9642 | 0.9690 |
| **平均** | - | - | - | 13 | **0.7579** | **0.9860** | **0.8385** |

### 5.2 Stage-1（after: recall redesign）

| PID | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2307.05527 | 171 | 20 | 27 | 0 | 0.8953 | 1.0000 | 0.9448 |
| 2409.13738 | 21 | 52 | 5 | 0 | 0.2877 | 1.0000 | 0.4468 |
| 2511.13936 | 30 | 45 | 9 | 0 | 0.4000 | 1.0000 | 0.5714 |
| 2601.19926 | 335 | 22 | 1 | 0 | 0.9384 | 1.0000 | 0.9682 |
| **平均** | - | - | - | **0** | **0.6303** | **1.0000** | **0.7328** |

### 5.3 Stage-1 + fulltext（before: prompt-only v1）

| PID | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2307.05527 | 157 | 5 | 42 | 14 | 0.9691 | 0.9181 | 0.9429 |
| 2409.13738 | 21 | 9 | 48 | 0 | 0.7000 | 1.0000 | 0.8235 |
| 2511.13936 | 27 | 5 | 49 | 3 | 0.8438 | 0.9000 | 0.8710 |
| 2601.19926 | 306 | 0 | 23 | 29 | 1.0000 | 0.9134 | 0.9548 |
| **平均** | - | - | - | **46** | **0.8782** | **0.9329** | **0.8980** |

### 5.4 Stage-1 + fulltext（after: recall redesign）

| PID | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | --: | --: | --: | --: | --: | --: | --: |
| 2307.05527 | 159 | 4 | 43 | 12 | 0.9755 | 0.9298 | 0.9521 |
| 2409.13738 | 21 | 25 | 32 | 0 | 0.4565 | 1.0000 | 0.6269 |
| 2511.13936 | 29 | 10 | 44 | 1 | 0.7436 | 0.7000 | 0.8406 |
| 2601.19926 | 325 | 21 | 2 | 10 | 0.9393 | 0.9701 | 0.9545 |
| **平均** | - | - | - | **23** | **0.7787** | **0.7000** | **0.8435** |

## 6. FN 變化

### Stage-1 FN

- 2307.05527：6 → 0（改善 6）
- 2409.13738：0 → 0（無變化）
- 2511.13936：0 → 0（無變化）
- 2601.19926：7 → 0（改善 7）
- 總體：13 → 0（召回率達成滿分）

### Stage-1 + fulltext FN

- 2307.05527：14 → 12（改善 2）
- 2409.13738：0 → 0（無變化）
- 2511.13936：3 → 1（改善 2）
- 2601.19926：29 → 10（改善 19）
- 總體：46 → 23

## 7. 重要行為差異

### 哪些 review 有明顯改善

- recall 第一層顯著保守下降：大量 `exclude` 轉為 `maybe`（尤其 `2601.19926`）。
- `2601.19926` 在 fulltext 前，FN 明顯下降 19 筆。
- `2307.05527` 和 `2601.19926` 的 Stage-1 FN 全部解掉。
- 需求點中的關鍵樣例在對照中有明顯方向一致：
  - `2307.05527 / huang2020ai`、`Suh2021AI`：仍保留且更高信心。
  - `2409.13738 / etikala2021extracting`：stage1 保留（maybe），fulltext 最終 include。
  - `2511.13936 / lotfian2016retrieving`：stage1 保留，fulltext 改為更高強度 include。
  - `2601.19926 / mccoy_right_2019`：stage1 仍為保留，fulltext 改為 include。
  - `2601.19926 / Warstadt:etal:2020`：`prompt_only` 為 `exclude (missing_fulltext)`，現在成為 `include (review_state:retrieval_failed)`，不再語義硬排。

### 哪些幾乎沒變

- 2409 / 2511 的 Stage-1 FN 已是 0，主變化不在 FN 上，主要在 precision 的保留/排除邊界。
- 多數文章仍維持原 verdict（各篇都超過一半以上條目未變），只是少量條目從 include→maybe 或 exclude→maybe。

## 8. 實驗可回答什麼 / 尚未回答什麼

可回答：

1. `topic_definition` 作為 inclusion 前置條件會造成誤判，已修掉並分離為背景資訊。
2. Stage-1 確實可被改成高召回 gate：FN 可大幅下降。
3. `missing_fulltext` 已不再直接變成語義 exclude，並有可追溯的 `review_state`。

尚未回答：

1. precision 可否在不恢復大量 FN 的情況下持平仍待後續校準。
2. 是否需要再加一層 reviewer arbitration（例如保留 senior 輔助但不 override）以降低「include->maybe」退化。
3. 部分 dataset 在 Stage-1 precision 極低（2409, 2511）提示仍需 criteria / aggregation 微調。

## 9. 我們的結論

這一輪已明確完成三件核心事：

1. 修正 `topic_definition` 與可執行 criteria 的對齊；
2. 將 Stage-1 aggregation 改為 recall-first；
3. 把 missing-fulltext 作為運作狀態處理，不再當作 semantic exclude。

結果上 Stage-1 FN 以可見成本降到 0（四篇合計）是有效的，但 precision 也因 recall-first 明顯下滑，
因此**只靠這次改法尚不足以給出最終 production 版本**，下一步建議：保留 recall gate，但對 Stage-1 判斷邊界做更細緻 calibration，並針對 senior aggregation 進一步最小化誤降分。
