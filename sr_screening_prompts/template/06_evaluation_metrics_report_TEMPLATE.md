# TEMPLATE Prompt 6 — Evaluation（可選：計算 F1/coverage/錯誤分析並生成報告）

> **General Template**  
> 若你有 gold labels，就算 F1；沒有就做描述性統計與報告。

```text
我會上傳：
1) stage1_2_screening_decisions.jsonl
2) stage2_final_decisions.jsonl
（可選）3) {{GOLD_LABEL_FILE}}（例如 title_abstracts_metadata-annotated.jsonl）

你的任務：用 Python 計算 stage-wise 指標並生成 PDF 報告。

硬性要求：
- 只能用 key join
- 不准上網
- 不改輸入檔，只輸出新檔

若有 gold：
- Stage2 binary metrics：precision/recall/F1 + confusion matrix
- Stage1：maybe 的三種處理方式（liberal/conservative/abstain）各算一次
- funnel/coverage 統計
- error analysis（FP/FN）與 exclude_reasons 分布

若無 gold：
- decision 分布（Stage1 include/maybe/exclude；Stage2 include/exclude）
- needs_manual_review 分布
- exclude_reasons 分布

輸出：
- evaluation_metrics.json
- confusion_matrix*.csv（若有 gold）
- false_positives.csv / false_negatives.csv（若有 gold）
- screening_evaluation_report.pdf
並提供下載連結與 summary。
```