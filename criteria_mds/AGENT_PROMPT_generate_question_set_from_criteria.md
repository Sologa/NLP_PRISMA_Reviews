# Prompt: Criteria → Screening Question Set Generator（給「產生問題集」的 agent）

你將收到一篇 Systematic Review / Survey 的「Eligibility / Inclusion / Exclusion criteria」（可能還包含 Retrieval criteria、Quality assessment criteria）。
你的任務是：**把 criteria 轉成一份「抽取型問題集」**，用於讓另一個 extraction agent 去讀候選 paper（title+abstract+必要時全文片段）並回答問題；之後我們再依照答案用程式/規則判定是否符合 criteria。

---

## 輸入（Input）
- 一份 criteria 清單（可能已經被拆成 I1/I2…、E1/E2… 的 atomic single-condition；若沒有，請你先拆）。
- 可能含：
  - Stage 1: Retrieval criteria（搜尋策略）
  - Stage 2: Screening criteria（inclusion/exclusion）
  - Quality assessment criteria（QA1…）

---

## 輸出（Output）
請輸出一段 Markdown，包含兩個主要區塊：

### A. 可程式化判定的條件（Metadata-only）
只標注「完全可以寫程式，不需要 LLM 判定」的條件，至少要覆蓋下列 4 類（若該 SR 沒有就寫 None）：
1) 出版時間（publication year / date window）
2) peer-reviewed 與否（以及 venue 類型：journal/conference/workshop/preprint）
3) paper 長度（頁數門檻、short/long paper）
4) open-access / full-text availability（是否可取得全文）

格式建議：
- Publication time: I? / E? …
- Peer-reviewed: I? / E? …
- Paper length: I? / E? …
- Open-access / Full-text: I? / E? …

> 注意：這一區只需要列出 criterion ID 與它對應的 metadata 欄位/判定方式（例如 `year >= 2019`、`pages >= 5`、`is_open_access == true`、`venue_peer_reviewed == true`），不要改寫 criteria 原文。

### B. Screening Question Set（給抽取型 agent）
- 只設計「抽取型」問題：要求對方**摘錄原文 quote + 定位（Abstract/Section/Table/Appendix/Page）**。
- **不要**叫對方判定 “符合/不符合 criteria”；也不要寫 “must/should include/exclude” 這種規則語氣。
- 每個 criteria 的資訊需求都要被覆蓋：
  - 如果是 metadata-only（上面的 A 區），就不一定要出現在問題集（可選擇放一個 Q0 要對方抄錄 paper 內可見的證據，但註明「最終以 metadata 為準」）。
  - 其餘需要內容判定的 criteria：至少要有一個問題（或一組子問題）能抽取到足夠資訊來判定該條件。

---

## 生成問題集的規則（Hard constraints）
1. **完整性**：不能漏掉任何 screening criteria（含 appendix 提到的 eligibility filters）。
2. **原文證據**：每個問題都要要求 quote；若找不到，回答規則必須明確（例如「未明說」）。
3. **原子性**：不要把多個條件塞進同一個 YES/NO；必要時用子題拆開，讓每一子題對應單一可判定屬性。
4. **避免 outcome 當條件**：不要把 “最後剩下 N 篇” 這類結果當成 criteria，也不要生成相關問題。
5. **避免重複反面條件**：若某個 exclusion 只是 inclusion 的反面（完全等價），在「問題設計」層面可以共用同一個問題，不需要兩套問題重複問。
6. **定位要求**：每題至少要求提供位置（Abstract/Intro/Method/Experiments/Table/Figure/Appendix）。

---

## 問題集結構建議（可套用的 skeleton）
- Q0. Metadata 摘錄（年份、venue、頁數、open-access；註明以 metadata 為準）
- Q1. 任務定義（Task definition：input/output/目標；關鍵字與段落位置）
- Q2. 方法/模型屬性（architecture/backbone/是否 end-to-end/是否 retrieval+generation…）
- Q3. 資料/語言/模態（datasets、語言、text/audio/image…）
- Q4. 實驗/評估（是否有 experiments、metrics、baselines）
- Q5. 研究類型/出版型態排除訊號（survey/review/editorial/dissertation/competition report…）
- Q6.（若有）Quality assessment evidence（對應 QA1…）

> 依不同 SR 的 criteria 自行裁剪/重排；但務必讓每條 criteria 都能從回答中被判定。