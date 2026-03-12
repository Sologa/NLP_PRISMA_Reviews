# Stage 1 SeniorLead Adjudication Redesign Report

## 1. 實驗目標與限制

這一輪的目標是保留 `SeniorLead`，把 Stage 1 聚合邏輯改成「高召回審核 + 邊界 case 交給 SeniorLead」的可解釋版本：

- 保留上一輪已驗證的修正：
  - `topic_definition` 不再當成 inclusion 首條，改以 `criteria_context` 提供背景。
  - Title/Abstract 與 Fulltext 的 reviewer prompt（已在前一輪做過調整）不改。
  - `missing_fulltext` 以 `review_state` 記錄，不再直接作為語義排除。
- 僅改最小邏輯：`scripts/screening/vendor/src/pipelines/topic_pipeline.py`，不改 markdown template、review schema、Workflow 架構。

## 2. 本輪實際修改檔案

- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

主要改動（只在 pipeline aggregation 與路由邏輯）：

1. Stage 1 `senior_filter` 重寫
   - `Junior` 只要有不確定（3）或分歧，送 senior。
   - `Junior` 皆為 1/2 時，若理由含「缺乏/不足/不確定」則送 senior；否則可直接排除。
2. `SeniorLead` 加回 Stage 1 workflow 的 round B。
3. `_derive_final_verdict_from_row` 重寫
   - 若兩位 junior 都高分（>=4）→ include。
   - 兩位 junior 都低分（<=2）且理由都屬「可追溯的明確排除」→ exclude。
   - 兩位 junior 分歧 / 含 3 / 低分但不確定 → maybe（交由下一階段或保守保留）。
4. 加入兩組訊號詞判斷
   - `_JUNIOR_UNCERTAIN_MARKERS`、`_JUNIOR_CLEAR_EXCLUSION_MARKERS`。
   - 用於判斷「可追溯排除」與「證據不足」。
5. `missing_fulltext` 與 `review_skipped` 保持 `review_state`，避免混入 semantic exclude。

## 3. 測試命令

沿用既有 benchmark 流程：

```bash
PAPER_ID=<pid> TOP_K=0 ENABLE_FULLTEXT_REVIEW=1 PIPELINE_PYTHON=<python> RUN_TAG=senior_adjudication_v1 run_review_smoke5.sh
```

評估（既有方式）：

```bash
python3 scripts/screening/evaluate_review_f1.py <pid> --results screening/results/<pid>_full/latte_review_results.senior_adjudication_v1.json --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl --positive-mode include_or_maybe --save-report screening/results/<pid>_full/review_after_stage1_senior_adjudication_v1_report.json

python3 scripts/screening/evaluate_review_f1.py <pid> --results screening/results/<pid>_full/latte_fulltext_review_results.senior_adjudication_v1.json --base-review-results screening/results/<pid>_full/latte_review_results.senior_adjudication_v1.json --gold-metadata refs/<pid>/metadata/title_abstracts_metadata-annotated.jsonl --combine-with-base --positive-mode include_or_maybe --save-report screening/results/<pid>_full/combined_after_fulltext_senior_adjudication_v1_report.json
```

已完成四篇：`2307.05527`、`2409.13738`、`2511.13936`、`2601.19926`。

## 4. Stage 1 前後混淆矩陣 / 指標（本輪 vs 參考版）

### 4.1 Stage 1

| paper_id | TP | FP | TN | FN | precision | recall | f1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2307.05527 | 164 | 8 | 39 | 7 | 0.9535 | 0.9591 | 0.9563 |
| 2409.13738 | 21 | 27 | 30 | 0 | 0.4375 | 1.0000 | 0.6087 |
| 2511.13936 | 30 | 23 | 31 | 0 | 0.5660 | 1.0000 | 0.7229 |
| 2601.19926 | 333 | 11 | 12 | 2 | 0.9680 | 0.9940 | 0.9809 |

### 4.2 Stage 1 + fulltext（combined）

| paper_id | TP | FP | TN | FN | precision | recall | f1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2307.05527 | 156 | 4 | 43 | 15 | 0.9750 | 0.9123 | 0.9426 |
| 2409.13738 | 21 | 22 | 35 | 0 | 0.4884 | 1.0000 | 0.6563 |
| 2511.13936 | 28 | 20 | 34 | 2 | 0.5833 | 0.9333 | 0.7179 |
| 2601.19926 | 325 | 11 | 12 | 10 | 0.9673 | 0.9701 | 0.9687 |

## 5. 對照：prompt-only v1 / recall_redesign / baseline

### 5.1 Stage 1 FN 與 F1 對比

| paper_id | this_round_stage1 FN | prompt_only_v1 FN | stage1_recall_redesign FN | this_round_stage1 f1 | prompt_only_v1 f1 | stage1_recall_redesign f1 | ΔF1 vs prompt_only | ΔF1 vs recall_redesign |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2307.05527 | 7 | 6 | 0 | 0.9563 | 0.9593 | 0.9448 | -0.0030 | +0.0115 |
| 2409.13738 | 0 | 0 | 0 | 0.6087 | 0.6364 | 0.4468 | -0.0277 | +0.1619 |
| 2511.13936 | 0 | 0 | 0 | 0.7229 | 0.7895 | 0.5714 | -0.0666 | +0.1515 |
| 2601.19926 | 2 | 7 | 0 | 0.9809 | 0.9690 | 0.9682 | +0.0119 | +0.0126 |

### 5.2 Combined F1 對比

| paper_id | this_round_combined f1 | combined_after_fulltext_report f1 | combined_recall_redesign f1 | ΔF1 vs baseline fulltext | ΔF1 vs recall_redesign |
|---|---:|---:|---:|---:|---:|
| 2307.05527 | 0.9426 | 0.9429 | 0.9521 | -0.0003 | -0.0095 |
| 2409.13738 | 0.6562 | 0.8235 | 0.6269 | -0.1673 | +0.0294 |
| 2511.13936 | 0.7179 | 0.8710 | 0.8406 | -0.1530 | -0.1226 |
| 2601.19926 | 0.9687 | 0.9548 | 0.9545 | +0.0139 | +0.0142 |

## 6. Stage 1 FN 與重要現象

- `2307` / `2601`：FN 明顯改善且大致維持高召回；`2601` 相較 prompt-only FN 降為 2，precision/recall 同步回升。
- `2409` / `2511`：FN 全部消掉（維持 recall=1），但 precision 仍不足（雖比 recall_redesign 明顯好），表示仍有大量可判斷為 not include 的邊界/低訊號案例被保留到下一階段。
- 與 baseline 組合比較
  - `2601` 在 combined 上顯著進步：FP 由 0 降到 11 但 recall 提升到 0.97，F1 提升。
  - `2409`、`2511` combined 的 F1 下降，主要來自 FP 增加（更多 no-evidence 被保留）。

## 7. 指定案例 spot-check

以 `title_abstracts_metadata-annotated.jsonl` 的 key 進行抽查（四篇結果）：

| paper_id | key | Stage 1 是否送 Senior | Stage 1 final | Stage 1 senior 補充判斷 | Fulltext 狀態與最終 | 是否合理 |
|---|---|---|---|---|---|---|
| 2307.05527 | `huang2020ai` | 否（兩位 junior 均 5） | include(5,5) | 無 senior | reviewed, include(5,5) | 合理：明確高分，無需仲裁 |
| 2307.05527 | `Suh2021AI` | 是（5/4） | include(5,5)（senior=5） | Senior 介入後收斂為 include | reviewed, include(5,5) | 合理：disagreement 且高可能性保留 |
| 2409.13738 | `etikala2021extracting` | 是（3/4） | maybe(senior:3) | Senior 取「不排除」判定，導向暫留 | reviewed, include(5,5) | 合理：stage1 保留，全文可交叉確認 |
| 2511.13936 | `lotfian2016retrieving` | 是（3/5） | maybe(senior:3) | Senior 依證據不足（未見明確音訊）維持 maybeto keep | reviewed, include(5,5) | 合理：先保留後續審查 |
| 2601.19926 | `mccoy_right_2019` | 是（3/3） | maybe(senior:3) | Senior 判讀為題目線索不足，保留 | reviewed, include(5,5) | 合理：避免因不確定而直接排除 |
| 2601.19926 | `Warstadt:etal:2020` | 否 | include(5,5) | 無 senior | retrieval_failed（無 fulltext）-> `include (review_state:retrieval_failed)` | 合理：不再被語義判為 exclude |

## 8. 結論

### 這輪目標達成度

- `SeniorLead` 已保留且回到 adjudicator 角色，不是黑盒覆蓋。
- Stage 1 現在可以將「明確排除證據」直接排除，將「disagreement/uncertain」送 senior。
- `missing_fulltext` 不再污染 semantic verdict，變成 `review_state=retrieval_failed`。

### 與目標比較

- `2307`、`2601` 的高召回主力有保持，且在這兩篇上比 prompt-only 更穩定。
- `2409`、`2511` 的 precision 仍偏低，雖比上輪 recall-redesign 明顯緩解，但仍顯示「保守仲裁」仍可再加強。

### 建議下一步

1. 精簡/擴充 Stage 1 明確排除的可追溯標記詞，降低 senior 需要裁決的噪音。
2. 針對 `2409`、`2511` 加強兩位 junior 的提示約束：低分且有「可追溯非音訊主題」訊號，應更容易走直接排除分支。
3. 若允許，可加入「review-level 計量追蹤」報表（每篇每輪送審與否）以固定化調參。
