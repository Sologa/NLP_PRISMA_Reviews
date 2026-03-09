# Prompt 6 — Evaluation（可選：計算 Stage1/Stage2 的 F1、coverage、錯誤分析，並生成報告）

> **使用情境**  
> 你已經跑完 Stage 1.1/1.2/2，現在要評估 screening 結果。  
> 這個 prompt 會：
> - 若有 gold label：計算 F1 / precision / recall / confusion matrix / stage-wise coverage
> - 若沒有 gold label：只做資料分布與錯誤/不確定來源統計
> - 生成 PDF 報告 + CSV/JSON 輸出，供下載

```text
我會上傳（至少）：
1) stage1_2_screening_decisions.jsonl
2) stage2_final_decisions.jsonl

（可選，用於計算 F1）
3) title_abstracts_metadata-annotated.jsonl
   - 其中包含 ground-truth（gold）欄位，例如 is_evidence_base / gold_label / ground_truth 等

你的任務：用 Python 讀取這些 JSONL，計算評估指標並生成可下載報告。

【硬性要求】
1) 只能用 key（bibkey）做 join。
2) 不准上網。
3) 不要更動輸入檔內容；只輸出新檔案。

--------------------------------
A) 欄位偵測與正規化
--------------------------------
1) 對每個輸入檔掃描 top-level keys，列出欄位出現率。
2) 偵測 prediction 欄位：
   - Stage1 pred：stage1_2_decision（include/exclude/maybe）
   - Stage2 pred：final_decision（include/exclude）
3) 偵測 gold 欄位（若提供 annotated.jsonl）：
   - 候選欄位名（按優先序）：is_evidence_base, gold, gold_label, ground_truth, y_true, label
4) 正規化：
   - include → positive
   - exclude → negative
   - maybe（Stage1）：
     * 版本A（liberal）：maybe 視為 include
     * 版本B（conservative）：maybe 視為 exclude
     * 版本C（abstain）：maybe 視為 abstain（不計入 confusion matrix），額外報 coverage

--------------------------------
B) 指標（若有 gold）
--------------------------------
1) Stage2（final）binary metrics（positive=include）：
   - TP/FP/TN/FN
   - precision/recall/F1
   - accuracy, specificity, MCC
   - 95% bootstrap CI（可選）

2) Stage1（title/abstract）：
   - 在三種 maybe 處理方式（A/B/C）下各算一次 precision/recall/F1
   - coverage（C 版本）

3) Stage-wise funnel metrics：
   - Stage1 通過率：(#include + #maybe)/N
   - Stage2 最終 include 率：#include/N
   - 若有 gold：Stage1 的 recall（把 maybe 視為保留）、Stage2 的 precision/recall/F1

--------------------------------
C) 錯誤分析與切片（若有 gold）
--------------------------------
1) 列出 Stage2 的 FP/FN：
   - key, title(若可), gold, pred, exclude_reasons（若有）, decision_reason（若有）
2) 針對 exclude_reasons 做統計（例如 E5 secondary / E3 extractive / E2 multimodal …）
   - FP/FN 中最常見的原因碼
3) 若存在 needs_manual_review：
   - 報告其比例，以及在 FP/FN 中的占比

--------------------------------
D) 若無 gold：仍要做的統計
--------------------------------
- Stage1 include/maybe/exclude 分布
- Stage2 include/exclude 分布
- exclude_reasons 的分布（Stage1 與 Stage2 分別算）
- needs_manual_review 的比例與 key 清單（前 50 個，完整另存檔）

--------------------------------
E) 輸出檔案（必須提供下載）
--------------------------------
1) evaluation_metrics.json
2) stage2_confusion_matrix.csv（若有 gold）
3) stage1_metrics_maybe_handling.csv（若有 gold）
4) false_positives.csv / false_negatives.csv（若有 gold）
5) needs_manual_review_keys.txt（若有）
6) screening_evaluation_report.pdf
   - 報告內容：資料概覽、欄位偵測、stage-wise funnel、主要指標、confusion matrix、error analysis、limitations
   - 排版注意：不要使用圓點 bullet（改用 "-" 或 (1)(2)）；表格要自動換行不溢出；文字不超右界。

最後請把所有輸出檔案提供下載連結，並在回覆文字中給 summary（包含 Stage2 F1 若有）。
```