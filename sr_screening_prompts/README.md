# SR test-time screening prompts (v2)

這個資料夾提供兩套 prompts（**SR 專用版**、**General Template 版**），用來在 **test-time** 情境下做兩階段（Stage 1 / Stage 2）screening：

- 你**沒有** SR 的 tex source、也**不知道**最後應該入選幾篇。
- 你只有：
  - `title_abstracts_metadata.jsonl`（含 key/title/abstract/日期等 metadata）
  - `fulltexts_text_only.zip`（只在 Stage 2 才會用到；Stage 1 不讀 full text）
- 你要模擬實際 SR screening：
  - Stage 1.1：只用 metadata 中可程式化判斷的條件（例如年份、paper language、short/long 類型）
  - Stage 1.2：只讀 title+abstract 做資訊抽取（**不判定**）→ 再依 criteria 做初判（include/exclude/maybe）
  - Stage 2：只對 Stage 1.2 的 include/maybe 讀 full text 做資訊抽取（**不判定**）→ 再依 criteria 做最終判定（include/exclude）

---

## v2 重要更新

### 1) 新增「Secondary research」辨識與排除（避免 evidence base 混入次級研究）
很多 evidence-base 目標都是 **primary studies**；只靠標題含不含 “review” 會漏掉大量次級研究（例如 SoK、taxonomy、tutorial、roadmap、position/vision/perspective 等）。

因此 v2 在 Stage 1.2 與 Stage 2 都新增 **Secondary research signals** 的資訊抽取（不做判定），並在 criteria review 增加一條 **Exclusion：Secondary research**（可在模板中選擇啟用/停用）。

Secondary research 常見兩大群（僅作操作性定義，用於 screening）：
- A. evidence synthesis / review methodologies：systematic review / mapping / scoping / rapid review / realist synthesis / integrative review / mixed methods review / meta-analysis / qualitative evidence synthesis（meta-synthesis, meta-ethnography, meta-narrative…）/ concept analysis / critical interpretive synthesis / best evidence synthesis / meta-study / meta-summary …  
- B. CS/NLP 常見的綜整型文章命名：survey / overview / tutorial / primer / taxonomy / conceptual framework / **SoK (Systematization of Knowledge)** / roadmap / research agenda / future directions / perspective / position paper / vision paper / opinion / commentary …

> 注意：有些 survey/SoK 也會釋出新 dataset/benchmark/metric，但如果你的 evidence base 定義是 primary studies，通常仍會把它們當 secondary 排除；同時它們仍可被引用作 background / related work。

---

### 2) 語言限制拆成兩層（v2 強化）
- **Paper language（論文本身語言）**：預設只納入英文論文（常見 SR 設定）。在 v2 中放到 **Stage 1.1**（可程式化：用 metadata 的 language 欄位或對 title+abstract 做語言偵測）。  
- **Primary dataset language（主要資料集語言）**：屬於 SR 的精細排除條件（CADS 類型常見）。v2 強化「**若 paper 未明說 dataset 語言 → 依規則直接視為 English**」，並在 criteria review 中把這視為 **高確定度 not-excluded**（除非 paper 明確寫 non-English/multilingual/cross-lingual/translation 等與 primary dataset 語言直接相關的證據）。

---

### 3) Criteria 不再用 1–5 分逐條打分（改成 Yes/No/Unclear）
SR screening 常見記法是對每條 criterion 記錄：
- Inclusion：YES / NO / UNCLEAR  
- Exclusion：YES(triggered) / NO(not triggered) / UNCLEAR  

v2 只保留（可選的）整體決策信心 `decision_confidence_1to5`，**不對每條 criterion 打 1–5 分**，避免誤用量表。

---

### 4) Verdict 的硬規則（v2 反覆強調）
- **Exclusion**：只要任一條 Exclusion==YES → verdict **EXCLUDE**
- **Inclusion**：只要任一條 Inclusion==NO → verdict **EXCLUDE**
- Stage 1.2 允許 MAYBE（只要還有任何 UNCLEAR）
- Stage 2 不允許 MAYBE：若仍有任何 UNCLEAR，採保守策略 → verdict EXCLUDE 並標 `needs_manual_review=true`

---

## 檔案結構

- `sr_specific/`：針對「CADS 類型 criteria（2019+ Transformer summarization；排除 non-English primary dataset / multimodal / extractive / non-transformer）」填好的版本，並額外加入 Secondary research exclusion（作為 evidence base=primary studies 的通用政策）。
- `template/`：General 模板版；年份門檻、criteria、是否啟用 secondary exclusion 等都用 `{{PLACEHOLDER}}` 挖空。

每套各包含 6 個 prompts：
1. Stage 1.1 metadata screening
2. Stage 1.2 title+abstract extraction（Q0–Q10；不判定）
3. Stage 1.2 criteria review（include/exclude/maybe）
4. Stage 2 full-text extraction（Q0–Q10；不判定）
5. Stage 2 criteria review（include/exclude）
6. Evaluation / metrics report（可選，用於算 screening 模型的 F1、coverage、error analysis 等）

