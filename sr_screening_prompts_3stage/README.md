# AUTOSR-SDSE 風格（單 Agent）— 3 階段 SR Screening Prompts（Test-time）

這份 prompts 套件是「**單一 ChatGPT agent**」可直接跑的 test-time screening 流程，**不需要** SR 的 tex source（沒有 arXiv tar），只依賴你提供的：

- `title_abstracts_metadata.jsonl`
- `fulltexts_text_only.zip`（第二階段才用）

並遵守「SR screening 兩階段」的精神：

- **Stage 1.1**：只做 metadata 可程式化判斷（年份 + long/short）
- **Stage 1.2**：只看 **Title + Abstract**，直接做 criteria review（1～5 分）
- **Stage 2**：讀 **Full text**，再做一次 criteria review（1～5 分）並輸出最終 include/exclude

> 注意：本套件是「3 個 prompt」，但保留原本 5 階段命名中的 **Prompt 1 / 3 / 5**：
> - Prompt 2（title/abstract 抽取）與 Prompt 4（fulltext 抽取）已移除（你要求不需要）。

---

## 使用順序

### SR 專用版（`sr_specific/`）
1. `01_stage1_1_metadata_screening.md`
2. `03_stage1_2_criteria_review.md`
3. `05_stage2_criteria_review.md`

### 通用模板版（`template/`）
同樣順序，但你要先把模板中的 `{{PLACEHOLDER}}` 依你的 SR 改掉。

---

## 共同輸出（建議檔名）

- Stage 1.1：`stage1_1_metadata_screening.jsonl` + `.csv`
- Stage 1.2：`stage1_2_screening_decisions.jsonl` + `.csv`
- Stage 2：`stage2_final_decisions.jsonl` + `.csv` + `included_keys.txt` / `excluded_keys.txt`

---

## 1～5 分數定義（本套件統一使用）

對 **Inclusion**（是否符合納入）：
- 5 = 明確符合（文字直接寫出）
- 4 = 大概率符合（有強烈線索）
- 3 = 不確定（資訊不足 / 兩可）
- 2 = 大概率不符合
- 1 = 明確不符合（文字直接否定或明顯相反）

對 **Exclusion**（是否觸發排除）：
- 5 = 明確觸發排除（文字直接寫出）
- 4 = 大概率觸發排除
- 3 = 不確定
- 2 = 大概率不觸發
- 1 = 明確不觸發（或有文字支持相反）

並用以下映射轉成狀態：
- Inclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR
- Exclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR

---

## Verdict 硬規則（兩個 review prompt 都必須遵守）

- 只要任一條 **Exclusion == YES** → **EXCLUDE**
- 只要任一條 **Inclusion == NO** → **EXCLUDE**
- Stage 1.2：若未觸發 EXCLUDE，但有任何 UNCLEAR → **MAYBE**
- Stage 2：不允許 MAYBE；若仍有 UNCLEAR → **EXCLUDE（保守）** + `needs_manual_review=true`
