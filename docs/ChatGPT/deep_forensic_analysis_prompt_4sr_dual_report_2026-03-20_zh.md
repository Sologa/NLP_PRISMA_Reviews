# ChatGPT 深入 Forensic Analysis Prompt（四篇 SR，雙報告版）

以下 prompt 是給外部 ChatGPT 用的。
目的不是重做實驗，也不是重寫 criteria，而是要它對目前 repo 裡已整理出的 error cases 再做一層「讀原文 + 上網核對 + 深入說清楚」的分析。

建議直接把下面整段貼給 ChatGPT。

---

你現在要做的不是設計新 prompt、不是重寫 criteria、不是做新的 repair plan。

你現在要做的是：

**針對 repo 裡已整理出的 error cases，做一輪更深入的 forensic error analysis，而且這一輪一定要上網搜尋並讀取那些 error case 對應 paper 的原文。**

你的任務不是只複述 repo 內已經寫好的 dossier。
你的任務是：

1. 先讀 repo 內既有 dossier / recap / current-state files  
2. 再針對那些 error cases，上網搜尋 paper 原始來源  
3. 打開 paper 原文 PDF / HTML / publisher page / arXiv / ACL Anthology 等 primary source  
4. 直接核對：
   - repo 內 local markdown evidence
   - 原始 paper evidence
   - gold label
   - predicted verdict
5. 把「到底是模型錯、gold 邊界張力、還是 local fulltext mismatch」講清楚

## 一、這次必須遵守的硬規則

### Rule 1
**你必須使用網路搜尋。**

這不是 optional。
你必須真的去搜尋並打開那些 error case paper 的原始來源。

### Rule 2
**不能只依賴 repo 內的 local markdown。**

repo 內 `refs/<paper>/mds/*.md` 很重要，但它只能當 local evidence base。
你必須再用 web 去核對原始論文。

### Rule 3
**每個 error case 至少要有一個 web primary source。**

優先順序：

1. publisher / conference official PDF
2. arXiv PDF / HTML
3. ACL Anthology / OpenReview / official proceedings page
4. 其他可靠全文鏡像

如果真的找不到全文：

- 你要明說找不到
- 說清楚你找到的是什麼
- 不要假裝你已經看過原文全文

### Rule 4
**如果 local markdown 與網路原文不一致，你要直接點出來。**

例如：

- OCR 問題
- metadata 錯配
- fulltext file 指到錯的文檔
- local markdown 遺漏 abstract / title / sections

### Rule 5
**不要把 workflow guess 偽裝成 paper fact。**

你可以推論，但要標明這是 inference，不是原文明說。

### Rule 6
**這次不是要你幫我改 code。**

你是來做更深的 diagnosis，不是來提 patch plan。
如果你想到修法，可以放在最後「給 Codex 參考」，但不是主體。

## 二、你必須先讀的 local repo files

請先依序讀：

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. `screening/results/2307.05527_full/CURRENT.md`
5. `screening/results/2409.13738_full/CURRENT.md`
6. `screening/results/2511.13936_full/CURRENT.md`
7. `screening/results/2601.19926_full/CURRENT.md`
8. `criteria_stage1/2307.05527.json`
9. `criteria_stage2/2307.05527.json`
10. `criteria_stage1/2409.13738.json`
11. `criteria_stage2/2409.13738.json`
12. `criteria_stage1/2511.13936.json`
13. `criteria_stage2/2511.13936.json`
14. `criteria_stage1/2601.19926.json`
15. `criteria_stage2/2601.19926.json`
16. `scripts/screening/runtime_prompts/runtime_prompts.json`
17. `docs/pre_qa_experiment_summary_zh-報告用.md`
18. `docs/qa_forensic_error_analysis-報告用.md`

## 三、這次要你深挖的 error cases

請以 `docs/qa_forensic_error_analysis-報告用.md` 裡已經列出的 dossier 為主體。

### `2409`

- `azevedo2018bpmn`
- `bellan2022extracting`
- `robeer2016`
- `goossens2023extracting`
- `qian2020approach`
- `vda_extracting_declarative_process`

### `2511`

- `manocha2020differentiable`
- `wu2023interval`
- `chumbalov2020scalable`
- `jayawardena2020ordinal`
- `parthasarathy2018preference`
- `huang2025step`

### `2307`

- `ghose2020autofoley`
- `serra_universal_2022`
- `Li2021Robust`
- `zhao_review_2022`
- `liang_midi-sandwich_2019`

### `2601`

- `baucells-etal-2025-iberobench`
- `arehalli_neural_2024`
- `marecek_balustrades_2019`
- `wilcox_2022_chapter`
- `zhang_closer_2023`

## 四、你要怎麼做

### Step 1. 建立 local-vs-web 對照框架

對每個 case，先從 local repo 取出：

- paper_key
- title
- abstract
- gold label
- predicted final verdict
- current dossier 中的 error-family 與 claim

### Step 2. 逐案上網搜尋原文

每個 case 都必須：

1. 用 title / DOI / arXiv / venue 去搜尋
2. 打開原始 paper 來源
3. 讀原文的 abstract、introduction、method、discussion、publication metadata
4. 找出真正支持或反駁 local dossier claim 的段落

### Step 3. 核對這三件事

你要分開判斷：

1. **local dossier 是否有抓準 paper 本身**
2. **model verdict 是否真的錯**
3. **gold label 是否本身就比較寬、比較舊、或與 current source-faithful criteria 有張力**

### Step 4. 特別注意這幾種情況

- local markdown OCR / parsing mismatch
- fulltext file 可能對錯 paper
- title/abstract 與 fulltext 重心不同
- symbolic vs audio
- video-conditioned audio vs audio-only
- enhancement vs generation
- defense paper vs target-model paper
- MT / encoder-decoder exclusion 是否過頭
- benchmark / survey / chapter / proceedings / preprint 的 publication-form 辨識

### Step 5. 對 `wilcox_2022_chapter` 特別強制核對

這個 case 必須特別確認：

- local markdown 是不是錯文檔
- 原始 paper 是不是 GPT-2 syntax chapter
- local dossier 指出的 mismatch 是否成立

你要明確說出：

- `local file says X`
- `web original says Y`
- `therefore this is / is not a retrieval mismatch`

## 五、每個 case 你至少要回答的欄位

對每個 case，請維持 dossier 風格，但你現在要做的是「web-verified extended dossier」。

每個 case 至少要有：

1. `paper_key`
2. `title`
3. `gold label`
4. `predicted final verdict`
5. `local dossier claim`
6. `web primary source(s)`
7. `original-paper evidence`
8. `local markdown vs web original: consistent / partially inconsistent / inconsistent`
9. `真正的錯誤層級`
   - `Stage 1 early exclude`
   - `Stage 2 closure`
   - `senior adjudication`
   - `synthesis distortion`
   - `publication-form overreach`
   - `target-boundary confusion`
   - `preference-signal under-detection`
   - `fulltext retrieval mismatch`
   - `gold-boundary tension`
   - `other`
10. `這到底是 clean model error、borderline ambiguity、還是 gold/criteria tension`
11. `一句最核心的 take`

## 六、你要產出兩份報告

這是硬要求。

### Deliverable A：給我看的報告

你要生成一份**口語化、解釋型、給人類直接閱讀**的報告。

要求：

- 中文撰寫
- 口語化，但不能失真
- 每個專有名詞第一次出現時都要解釋
- 假設讀者不是 repo 內的人
- 要有明確的「白話解釋」
- 不要只寫 reviewer-style shorthand
- 要說清楚：
  - 這篇 paper 在做什麼
  - 為什麼當初會被判錯
  - 看完原文後，真正的問題是什麼

#### Deliverable A 格式

請生成：

1. 一份 **PDF 檔**
2. 同時給出一份與 PDF 同內容的可檢查正文（例如 markdown / html / structured text）

PDF 檔名請命名為：

`chatgpt_deep_forensic_report_for_human.pdf`

如果你的執行環境無法直接產生 binary PDF，則你必須：

- 明確說明無法直接輸出 binary PDF
- 但仍要產出一份 **PDF-ready** 的完整 markdown 或 html 版本
- 檔名請命名為：
  - `chatgpt_deep_forensic_report_for_human.md`
  或
  - `chatgpt_deep_forensic_report_for_human.html`

這份給我看的報告，請至少包含：

1. `先講人話摘要`
2. `四篇 SR 各自最重要的錯誤類型`
3. `每個 case 的白話解釋`
4. `哪些是模型真的判錯`
5. `哪些其實是邊界本來就難`
6. `哪些是 local fulltext 或 metadata 問題`
7. `名詞小字典`

### Deliverable B：給 Codex 看的報告

你要再生成一份**技術版、偏 machine-readable、讓 Codex 可以接手**的報告。

檔名請命名為：

`chatgpt_deep_forensic_report_for_codex.md`

這份報告要：

- 技術化
- 精簡但完整
- 每個 case 都要有 source links
- 要明確區分：
  - `repo-local evidence`
  - `web-original evidence`
  - `mismatch status`
  - `error family`
  - `confidence`

#### Deliverable B 建議格式

每個 case 盡量包含這些欄位：

- `paper_key`
- `sr_id`
- `gold_label`
- `predicted_stage1`
- `predicted_combined`
- `local_fulltext_path`
- `web_source_urls`
- `local_vs_web_status`
- `decision_after_web_check`
- `error_family`
- `confidence`
- `notes_for_codex`

而且請加上一個總表：

- 哪些 case 在 web check 後，仍支持目前 dossier
- 哪些 case 需要修 dossier
- 哪些 case 看起來是 gold-boundary tension
- 哪些 case 看起來是 local file retrieval mismatch

## 七、語氣與寫法要求

### 對 Deliverable A

- 用人話講
- 不要把 repo jargon 當成讀者已知
- 每個縮寫第一次都解釋
- 每個 case 最好有一句：
  - `白話說，這篇其實是在……`

### 對 Deliverable B

- 技術化
- 直接
- 不需要客套
- 對 Codex 友善

## 八、禁止事項

不要做這些事：

1. 不要只看 repo local markdown 就下結論
2. 不要只看 abstract 就說你讀過 paper 原文
3. 不要把 review JSON 的 reasoning 當成 paper fact
4. 不要跳過 web source validation
5. 不要把兩份報告混成一份
6. 不要把「可修建議」寫成主體，主體仍是 forensic analysis

## 九、你最後的輸出順序

請按照這個順序輸出：

1. `What I Read Locally`
2. `What I Opened On The Web`
3. `Coverage Check`
4. `Deliverable A`
5. `Deliverable B`
6. `Short Final Note For Codex`

## 十、最後一句最重要

這次最重要的不是再講高層 diagnosis。

這次最重要的是：

**你必須真的上網把那些 error case 的 paper 原文打開來讀，然後把 local dossier、web 原文、gold label、predicted verdict 之間的關係講清楚。**

---

## 補充建議

如果 ChatGPT 的回覆長度或檔案輸出能力有限，建議你在同一個 thread 再補一句：

```text
如果篇幅太大，請先完成 Deliverable B，再分批完成 Deliverable A。
但無論如何，每個 case 都必須先做 web 原文核對，不能省略。
```
