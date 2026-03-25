# Stage 1 Senior No-Marker Redesign Report (v3)

## 1. 本輪範圍與原則

本輪只調整 **Stage 1 聚合/仲裁規則**，不改 prompt、serialization、missing_fulltext 流程，也不移除 SeniorLead。

- 保留上一輪修正項目：
  - `topic_definition` 不再直接作為 inclusion 首條輸入。
  - `criteria_context` + `additional_context` 提供 reviewer 背景。
  - `missing_fulltext` 仍以 `review_state` 管理，不當作語義排除。
  - Stage1 仍兩位 junior（`JuniorNano`、`JuniorMini`）+  `SeniorLead` arbitration。
- 這輪核心：刪除 Stage 1 依 reasoning 文字判斷的 marker heuristic，改成純分數規則。

## 2. 修改檔案

### `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

- 新增 `_to_score`（純數值安全轉換 helper）。
- 重寫 `_derive_final_verdict_from_row`：
  - 有 `round-B_SeniorLead_evaluation` 時，直接以 SeniorLead 分數判定：
    - `>=4` -> `include`
    - `<=2` -> `exclude`
    - `3` -> `maybe`
  - 無 Senior 時，僅看兩位 junior 分數：
    - 兩分數皆在 4~5 -> `include`
    - 兩分數皆在 1~2 -> `exclude`
    - 其他 -> `maybe`
    - 單筆分數缺值保留現行 fallback（`需再評估`）
- 重寫 Stage 1 `_senior_filter`：
  - 任一 junior 分數缺值 -> 送 senior
  - 兩高分（>=4） -> 不送 senior
  - 兩低分（<=2） -> 不送 senior
  - 其他 -> 送 senior
- 刪除 Stage 1 marker heuristic 相關元素與路徑：
  - `_JUNIOR_UNCERTAIN_MARKERS`
  - `_JUNIOR_CLEAR_EXCLUSION_MARKERS`
  - `_normalize_reasoning_text`
  - `_contains_marker`
  - `_is_likely_uncertain_negative`
  - `_is_likely_clear_exclusion`

## 3. 測試執行方式

使用既有 workflow 重新跑四篇：

```bash
for pid in 2307.05527 2409.13738 2511.13936 2601.19926; do
  PAPER_ID=$pid TOP_K=0 ENABLE_FULLTEXT_REVIEW=1 PIPELINE_PYTHON=python3 RUN_TAG=senior_no_marker run_review_smoke5.sh
done
```

並計算 Stage 1 + final combined 指標：

- Stage 1：
  - `review_after_stage1_senior_no_marker_report.json`
- Final combined：
  - `combined_after_fulltext_senior_no_marker_report.json`

（都已輸出到對應 `screening/results/<pid>_full/`）

## 4. 指標比較（TP/FP/TN/FN，精準率/召回率/F1）

### Stage 1（`latte_review_results.senior_no_marker.json`）

| paper | no-marker (p / r / f1) | TP FP TN FN | prompt_only_v1 (p / r / f1) | stage1_recall_redesign/adj (p / r / f1) |
|---|---|---:|---|---|
| 2307.05527 | 0.9551 / 0.8713 / 0.9113 | 165 7 40 6 | 0.9538 / 0.8713 / 0.9551 (165 8 39 6) | 0.9535 / 0.9591 / 0.9563 (164 8 39 7) |
| 2409.13738 | 0.4468 / 1.0000 / 0.6176 | 21 26 31 0 | 0.4667 / 1.0000 / 0.6364 (21 24 33 0) | 0.4375 / 1.0000 / 0.6087 (21 27 30 0) |
| 2511.13936 | 0.5686 / 0.6667 / 0.7160 | 29 22 32 1 | 0.6522 / 1.0000 / 0.7895 (30 16 38 0) | 0.5660 / 1.0000 / 0.7229 (30 23 31 0) |
| 2601.19926 | 0.9761 / 0.9761 / 0.9761 | 330 9 14 5 | 0.9591 / 0.9642 / 0.9690 (328 14 9 7) | 0.9680 / 0.9940 / 0.9809 (333 11 12 2) |

### Combined Final（`latte_fulltext_review_results.senior_no_marker.json`）

| paper | no-marker (p / r / f1) | TP FP TN FN | baseline combined (p / r / f1) | recall_redesign combined (p / r / f1) | senior_adjudication_v1 combined (p / r / f1) |
|---|---|---:|---|---|---|
| 2307.05527 | 0.9796 / 0.8421 / 0.9057 | 160 3 44 11 | 0.9691 / 0.9181 / 0.9429 (157 5 42 14) | 0.9755 / 0.9298 / 0.9521 (159 4 43 12) | 0.9750 / 0.9123 / 0.9426 (156 4 43 15) |
| 2409.13738 | 0.5250 / 1.0000 / 0.6885 | 21 19 38 0 | 0.7000 / 1.0000 / 0.8235 (21 9 48 0) | 0.4565 / 1.0000 / 0.6269 (21 25 32 0) | 0.4884 / 1.0000 / 0.6562 (21 22 35 0) |
| 2511.13936 | 0.7105 / 0.9000 / 0.7941 | 27 11 43 3 | 0.8438 / 0.9000 / 0.8710 (27 5 49 3) | 0.7436 / 0.6667 / 0.8406 (29 10 44 1) | 0.5833 / 0.9333 / 0.7179 (28 20 34 2) |
| 2601.19926 | 0.9758 / 0.9642 / 0.9700 | 328 11 12 7 | 1.0000 / 0.9134 / 0.9548 (306 0 23 29) | 0.9393 / 0.9701 / 0.9545 (325 21 2 10) | 0.9673 / 0.9701 / 0.9687 (325 11 12 10) |

## 5. Stage1 流程診斷（no-marker）

- Stage 1 sent-to-senior 比例（`round-B_SeniorLead_evaluation` 非空）：
  - 2307.05527: `43 / 218 = 0.197`
  - 2409.13738: `55 / 78 = 0.705`
  - 2511.13936: `53 / 85 = 0.624`
  - 2601.19926: `215 / 358 = 0.601`
- Stage1 最終由 senior 裁決比例：
  - 與上方 sent-to-senior 比例一致（final 文字都含 `senior`）
- Stage1 verdict distribution（no-marker）：
  - 2307.05527：`include 167 / maybe 5 / exclude 46`
  - 2409.13738：`include 26 / maybe 21 / exclude 31`
  - 2511.13936：`include 23 / maybe 28 / exclude 34`
  - 2601.19926：`include 174 / maybe 165 / exclude 19`

### 規則落地核對

- 2307/2511/2601 高得分（兩位 >=4）多數直接通過。
- 兩低分（<=2）組合不送 senior。
- 所有其他交叉組（含 3/3、2/3、3/4）均送 senior。

## 6. 6 個 spot-check 案例

> 取 `latte_review_results.senior_no_marker.json` 的 stage1 judge 記錄。

1. `2307.05527 / huang2020ai`
   - Junior 分數: `5,5`
   - 規則: 雙高直接 include
   - Senior: 未送
   - Final: `include (junior:5,5)`（符合規則）
2. `2307.05527 / Suh2021AI`
   - Junior: `5,3`（非一致）
   - 規則: 送 senior
   - Senior 分數: `5`
   - Final: `include (senior:5)`（符合規則）
3. `2409.13738 / etikala2021extracting`
   - Junior: `3,4`（非一致）
   - 規則: 送 senior
   - Senior 分數: `3`
   - Final: `maybe (senior:3)`（保留）
4. `2511.13936 / lotfian2016retrieving`
   - Junior: `3,3`
   - 規則: 送 senior
   - Senior 分數: `3`
   - Final: `maybe (senior:3)`（保留）
5. `2601.19926 / mccoy_right_2019`
   - Junior: `3,3`
   - 規則: 送 senior
   - Senior 分數: `3`
   - Final: `maybe (senior:3)`（保留）
6. `2601.19926 / Warstadt:etal:2020`
   - Junior: `5,5`
   - 規則: 雙高直接 include
   - Senior: 未送
   - Final: `include (junior:5,5)`（符合規則）

## 7. 本輪結果解讀（能/不能回答）

### 這輪可回答的問題
- 已成功 **移除 marker heuristic**，Stage 1 routing/aggregation 變成純分數規則。
- SeniorLead 保留，且有明確「雙高放行、雙低排除，其餘仲裁」路徑。
- 2307 / 2601 的 Stage 1 recall 均未明顯下滑，且多數保留。

### 仍有問題的地方
- 2409 與 2511 的 combined precision 仍較前一輪/基線低，尤其 2409 從 0.700 降到 0.525，2511 降到 0.7105。
- `maybe` 佔比仍偏高（尤其 2409 / 2511 / 2601），代表 borderline 仍在高比例保留。
- 由於只刪 marker，未碰 prompt 與 fulltext workflow，若要進一步拉回 precision，需要下一輪再檢討 stage2 觸發與 senior 判斷策略。

## 8. 與下一步關係

- 這輪完成了「高槓桿、最小改」：純規則化的 Stage 1 adjudication。
- 下一步若要改善 2409 / 2511 precision，較可行方向是：
  - 保留 `SeniorLead` 但限制其對 `maybe` 的保守度（如分數上下限/關鍵條件）；
  - 或調整 fulltext 阶段對於 stage1 高不確定項的再審策略。

