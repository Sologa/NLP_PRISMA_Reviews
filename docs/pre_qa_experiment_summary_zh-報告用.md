# QA 之前的實驗流程與結果整理報告

日期：2026-03-18  
範圍：本報告整理 `QA-first` 實驗啟動之前的主要實驗線，終點到 `stage_split_criteria_migration` 與目前 handoff 為止。  
不納入範圍：`docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md` 與 `qa_first_experiments/` 內的 QA-first 實驗資產。  

## 1. 一頁摘要

| 問題 | 結論 | 白話說明 |
| --- | --- | --- |
| QA 之前最後採用的架構是什麼？ | `runtime_prompts.json` + `criteria_stage1/` + `criteria_stage2/` + Stage 1 兩位 junior / 不一致送 `SeniorLead` | 系統最後不是靠一份通用 criteria 或一個超強 senior prompt，而是把 Stage 1 與 Stage 2 的規則正式拆開。 |
| 哪些規則被正式保留下來？ | `double-high include`、`double-low exclude`、其餘送 senior；移除 marker heuristic；保留 `SeniorLead` | 兩個初審都高分就收、都低分就拒；卡在中間才交給資深 reviewer。 |
| 哪些方向被否定？ | 全域嚴格 senior prompt、junior reasoning marker heuristic、把 operational hardening 偷寫回 criteria | 不能靠「更嚴格的資深裁決」或「看 junior 解釋文字關鍵字」吃遍四篇 paper。 |
| 哪些 paper 在 QA 前最麻煩？ | `2409.13738`、`2511.13936` | 這兩篇在 source-faithful 前提下，仍有 evidence interpretation / criteria observability 問題。 |
| 為什麼會走到 QA 前夕？ | criteria 與 routing 已經整理到相對乾淨，但 decision layer 仍常直接吃自由文本證據 | 白話說，規則本身已經比較乾淨了，但模型還是常常「看文章自己腦補」，所以才開始考慮先做 QA / evidence extraction。 |

### 1.1 QA 前的 current authority

| Paper | QA 前 current authority | Stage 1 F1 | Combined F1 | 狀態 | 白話說明 |
| --- | --- | ---: | ---: | --- | --- |
| `2307.05527` | `senior_no_marker` | 0.9621 | 0.9581 | stable reference | 目前穩定，不是主要戰場。 |
| `2409.13738` | `stage_split_criteria_migration` | 0.7500 | 0.7843 | current active | 已改成 stage-split source-faithful criteria，但還有 hard FP。 |
| `2511.13936` | `stage_split_criteria_migration` | 0.8657 | 0.8814 | current active | 語義更乾淨，但比歷史上最激進的 operational 版本低。 |
| `2601.19926` | `senior_no_marker` | 0.9792 | 0.9733 | stable reference | 對過嚴 senior 很脆弱，因此維持 no-marker。 |

### 1.2 QA 前最後的 production workflow

| 元件 | QA 前採用狀態 | 白話說明 |
| --- | --- | --- |
| Runtime prompt 來源 | `scripts/screening/runtime_prompts/runtime_prompts.json` | 真正執行時讀這個 JSON，不再依賴舊 markdown prompt 模板。 |
| Stage 1 criteria | `criteria_stage1/<paper_id>.json` | 給 title/abstract 用的「可觀測版」條件。 |
| Stage 2 criteria | `criteria_stage2/<paper_id>.json` | 給 full text 用的完整 canonical 條件。 |
| Stage 1 routing | 兩位 junior；雙高分直接 include；雙低分直接 exclude；其餘送 `SeniorLead` | 先讓便宜 reviewer 篩一遍，模糊的再交給資深 reviewer。 |
| Marker heuristic | 已移除 | 不再靠 reviewer 解釋文字裡有沒有某些關鍵字來決定流程。 |
| Guidance 第三層 | 不採用 | 不再額外加一層「隱藏規則說明」，避免規則來源變成三套。 |

### 1.3 QA 前 production workflow 概念流程圖

如果你的閱讀器不會把圖形渲染得很好，可以直接照著箭頭由上往下讀。

```text
候選論文
  |
  v
先看標題與摘要
（Stage 1：只做初篩）
  |
  +--> 兩位初審都偏高分
  |      -> 直接保留
  |
  +--> 兩位初審都偏低分
  |      -> 直接排除
  |
  +--> 兩位初審沒有明確共識
         -> 交給資深 reviewer
         -> 決定保留 / 排除 / 暫留
  |
  v
需要全文確認的論文
  |
  v
看全文
（Stage 2：用完整 criteria 再確認）
  |
  v
最終納入 或 最終排除
```

## 2. 四篇 SR 分別在做什麼

先說明：這裡的 `SR` 是 `systematic review`，也就是「系統性文獻回顧」。  
白話說，四篇 SR 各自都有一個明確主題，目標是從大量候選論文裡，找出真正屬於那個主題範圍的研究。

### 2.1 四篇 SR 的主題總表

| Paper | SR 題目 | 這篇 SR 在看什麼 | 白話說明 | 一個直覺例子 |
| --- | --- | --- | --- | --- |
| `2307.05527` | *The Ethical Implications of Generative Audio Models* | 生成式音訊模型的倫理問題 | 這篇不是在問「模型準不準」，而是在看「這類模型會帶來哪些道德、法律、社會風險」。 | 例如：一篇討論 deepfake 聲音、聲音版權、聲音模仿同意權的研究。 |
| `2409.13738` | *NLP4PBM: Process Extraction using NLP* | 用 NLP 從自然語言文字抽出流程模型 | 重點是「把文字敘述變成流程圖或流程結構」，不是一般 NLP 都算。 | 例如：把客服流程描述、醫療流程文件、作業手冊，自動轉成 process model。 |
| `2511.13936` | *Preference-Based Learning in Audio Applications* | 音訊領域中的偏好式學習 | 重點是「用偏好訊號來學習」，像 A/B 比較、排序、偏好回饋，而不是只拿偏好做最後評分。 | 例如：讓人比較兩段語音或音樂，模型再根據這些偏好更新訓練。 |
| `2601.19926` | *The Grammar of Transformers* | Transformer 語言模型裡的句法知識與可解釋性 | 重點是看 Transformer 內部到底有沒有學到文法結構，以及研究者怎麼證明這件事。 | 例如：分析 BERT/GPT 是否知道主詞動詞一致、依存關係、句法樹等結構。 |

### 2.2 每篇 SR 的「會收什麼」與「不收什麼」

說明：下面的例子是依目前 active criteria 整理出的白話例子，用來幫助理解範圍，不是正式 criteria 原文。

| Paper | 會收的研究 | 不收的研究 | 白話上的邊界 |
| --- | --- | --- | --- |
| `2307.05527` | 以生成式音訊為主題的完整研究論文，主軸是音訊生成模型或應用，並討論倫理、法律、社會議題。 | 純 ASR/轉錄、影像或影片生成、分類/預測模型、主輸出不是音訊的工作。 | 如果研究最後產生的是文字、影像、影片，而不是音訊，就通常不在這篇 SR 裡。 |
| `2409.13738` | 用 NLP 從自然語言文字抽出流程表示，且有具體方法與實驗驗證的原創研究。 | 流程預測、流程比對、流程重設計、情緒分析、只做一般 IE/分類但沒有真正抽出流程模型的工作。 | 不是「有用 NLP 處理流程相關文字」就算；要真的抽出 process model 才算。 |
| `2511.13936` | 在音訊領域裡，用 ranking、A/B 比較、偏好回饋或 RL loop 來訓練模型的研究。 | 只用偏好來做 evaluation、沒有 learning component 的工作；survey/review。 | 關鍵不是「有沒有問人喜不喜歡」，而是這個偏好有沒有真的拿來驅動學習。 |
| `2601.19926` | 研究 Transformer-based LM，並且實證分析它們的句法知識或文法結構。 | 非 Transformer 架構、只談模型但不分析 syntax、沒有實證內容的 survey / position paper。 | 不是所有 interpretability paper 都算；要明確碰到 syntax，且對象要是 Transformer LM。 |

### 2.3 這些主題裡常見的專有名詞

| 名詞 | 出現在哪篇 SR | 白話說明 | 例子 |
| --- | --- | --- | --- |
| Generative audio model | `2307` | 會「產生聲音」的模型，不只是辨識聲音 | 例如文字轉語音、音樂生成、聲音風格模仿。 |
| Ethical implications | `2307` | 技術帶來的倫理、法律、社會風險 | 例如未經同意模仿他人聲音、假語音詐騙。 |
| Process extraction | `2409` | 從自然語言描述中抽出流程步驟與結構 | 例如把 SOP 文字轉成流程圖。 |
| Process model | `2409` | 對流程的形式化表示 | 例如一張包含步驟、順序、分支條件的流程圖。 |
| Preference learning | `2511` | 不是直接給絕對分數，而是用「比較誰比較好」來學習 | 例如讓使用者在兩段音樂中選比較喜歡的一段。 |
| A/B comparison | `2511` | 把兩個候選音訊放在一起比較 | 例如比較兩種 TTS 聲音，選較自然的一個。 |
| RL training loop | `2511` | 模型根據回饋反覆更新策略的訓練流程 | 例如音訊生成模型根據偏好回饋逐步調整輸出。 |
| Syntactic knowledge | `2601` | 模型是否學到句法或文法結構 | 例如知道主詞和動詞要一致，或誰依附誰。 |
| Interpretability | `2601` | 研究模型裡哪些部分在做什麼 | 例如 probing 某些 layer / head 是否在編碼句法資訊。 |
| Transformer-based LM | `2601` | 以 Transformer 為核心的語言模型 | 例如 BERT、GPT 類模型。 |

## 3. 名詞速查

| 名詞 | Repo 內意思 | 白話說明 |
| --- | --- | --- |
| Stage 1 | 只看 title + abstract 的初篩階段 | 還沒讀全文，只先看標題與摘要。 |
| Stage 2 | full-text review 階段 | 會進一步看全文確認。 |
| Junior reviewer | `JuniorNano`、`JuniorMini` 這類前線 reviewer | 先做大批初篩的 reviewer。 |
| `SeniorLead` | Stage 1 仲裁 reviewer | 兩位 junior 沒有明確共識時，由資深 reviewer 做最後裁決。 |
| Aggregation | 多位 reviewer 的分數合成規則 | 怎麼把多人意見變成一個 final verdict。 |
| Marker heuristic | 依 junior reasoning 文字中的標記詞做流程判斷 | 白話就是「看解釋裡有沒有某些字」來偷走捷徑。 |
| Prompt tuning | 改 reviewer prompt 的措辭與偏好 | 透過改提示詞讓 reviewer 更保守或更積極。 |
| Frozen replay | 固定 junior 輸出，只重跑 senior | 用來分辨差異到底是 senior prompt 造成，還是 rerun noise。 |
| Operationalization | 把 criteria 改寫成更可執行的 decision table | 白話是把模糊規則改成模型更好做的硬規則。 |
| Source-faithful | 忠於原 review paper 原始定義 | 不偷加原文沒有的限制。 |
| Criteria supertranslation | 把「方便模型做判斷的規則」假裝成原 paper 規則 | 白話是把操作上的加嚴，偷偷寫回正式 criteria。 |
| Stage split | Stage 1 / Stage 2 使用不同版本的 criteria | 初篩與全文審查用不同粒度的規則。 |
| Combined F1 | Stage 1 加上 full-text review 之後的最終 F1 | 最接近整體 pipeline 最後成績。 |

## 4. 實驗主線時間表

### 4.1 實驗演進概念流程圖

```text
原始 baseline
  |
  v
先把 prompt 對齊
（先確認是不是 prompt 本身太偏）
  |
  v
再試 recall-first 路線
（先救漏掉的真陽性）
  |
  v
再調 senior 仲裁方式
（看資深 reviewer 怎麼介入比較合理）
  |
  v
拿掉 marker heuristic
（不要再靠看 junior 解釋文字裡的關鍵字）
  |
  v
檢查 strict senior 是否真的有效
（用 frozen replay 分清楚是真效果還是 noise）
  |
  v
把問題拆到 criteria 線
（特別處理 2409 / 2511）
  |
  v
正式改成 stage-split criteria migration
（Stage 1 / Stage 2 分開）
  |
  v
才走到 QA-first 的下一步構想
```

### 4.2 主要實驗時間表

原本的大表太寬，這裡改成兩張比較窄的表。

表 4.2A 主要改動與是否採用

| 順序 | 實驗 / 報告 | 核心改動 | QA 前是否採用 |
| --- | --- | --- | --- |
| 0 | `before` baseline | 舊版 prompt / workflow | 否 |
| 1 | `prompt_only_runtime_realignment` | 對齊 runtime reviewer prompt，不改 schema | 部分吸收 |
| 2 | `stage1_recall_redesign` | 強化 Stage 1 recall，並碰 serialization / aggregation / missing_fulltext | 否 |
| 3 | `stage1_senior_adjudication_redesign` | 重整 `SeniorLead` 介入規則 | 部分吸收 |
| 4 | `stage1_senior_no_marker` | 拿掉 marker heuristic，改純分數規則 | 是 |
| 5 | `stage1_senior_prompt_tuning` | 讓 senior prompt 更嚴格 | 否 |
| 6 | `nlp_prisma_screening_diagnosis` | 交叉核對 raw JSON、criteria、prompt、runtime | 不是 production 變更 |
| 7 | `frozen_senior_replay` | 固定 junior 輸入，重放 senior 決策 | 是，作為結論依據 |
| 8 | `criteria_2511_operationalization_v2` | 只改 `2511` criteria，做更硬的 decision table | 否 |
| 9 | `criteria_2409_stage_split` | 只改 `2409` criteria，先做 Stage 1 / Stage 2 分拆 | 部分吸收 |
| 10 | `source_faithful_vs_operational_2409_2511` | 正式比較 source-faithful 與 operational | 是，方法學結論被採納 |
| 11 | `stage_split_criteria_migration` | 正式改成 `criteria_stage1/` + `criteria_stage2/` | 是，QA 前最後採用架構 |

表 4.2B 每輪想回答什麼、結果如何

| 順序 | 想回答什麼 | 代表結果 |
| --- | --- | --- |
| 0 | 原始起點表現如何？ | 四篇平均 Combined F1 = `0.7991` |
| 1 | 單純 prompt 對齊能不能先把大問題修掉？ | 四篇平均 Combined F1 升到 `0.8980` |
| 2 | 若盡量不漏掉真陽性，整體會不會更好？ | Recall 幾乎滿分，但 precision 大掉；平均 Combined F1 降到 `0.8435` |
| 3 | 更積極的 senior 仲裁能否同時守住 precision 與 recall？ | 比 recall redesign 穩，但四篇平均 Combined F1 僅 `0.8214` |
| 4 | 不看 reasoning 關鍵字，只看分數，會不會更乾淨？ | `senior_no_marker` 全面優於 `senior_adjudication_v1` |
| 5 | 更保守的 senior 能否壓低 `2409/2511` 的 FP？ | `2409/2511` 進步，但 `2601` 大崩；`2601` Combined F1 掉到 `0.8860` |
| 6 | 真正瓶頸到底在哪？ | 指出問題是「criteria 可觀測性」+「senior prompt 不可移植」的組合 |
| 7 | 嚴格 senior 的效果是真效果，還是 rerun noise？ | 證明 effect 主要來自 senior prompt 本身，不是 noise |
| 8 | `2511` 問題是不是主要卡在 criteria？ | Combined F1 到 `0.9206`，但方法學上被否決 |
| 9 | `2409` 是否是 stage-mixing 問題？ | Combined F1 從 `0.6885` 升到 `0.7778` |
| 10 | 高分到底是合理優化，還是超譯 criteria？ | 證實有些高分來自 criteria supertranslation |
| 11 | 如何在不偷加規則下，把 stage 差異正式落地？ | `2409` Combined F1 = `0.7843`；`2511` Combined F1 = `0.8814` |

### 4.3 哪些版本真的是 prompt 差異

這裡先講清楚一件事：**不是所有版本之間都只差 prompt**。  
如果把 `senior_no_marker`、`stage1_recall_redesign` 這些版本也說成只是 prompt 差異，會不準。真正屬於「主要變因就是 prompt wording」的，主要是下面兩類：

| 版本 | 主要變因 | 是否屬於 prompt-only / prompt-dominant | 這節會不會列出 before / after prompt |
| --- | --- | --- | --- |
| `prompt_only_runtime_realignment` | Stage 1 reviewer prompt 與 Stage 2 reviewer prompt wording | 是，prompt-only | 會，重點列 Stage 1 reviewer before / after |
| `senior_prompt_tuned` | Stage 1 `SeniorLead` adjudicator wording | 是，prompt-only | 會，列 `senior_no_marker` vs `senior_prompt_tuned` |
| `senior_no_marker` | routing / aggregation 規則 + marker heuristic 移除 | 否，不是只有 prompt | 不用 before / after prompt 解釋 |
| `stage1_recall_redesign` | prompt + serialization + aggregation + missing_fulltext | 否，不是只有 prompt | 不用單靠 prompt 對照解釋 |

### 4.4 Prompt 對照一：Stage 1 reviewer 在 `prompt_only_runtime_realignment` 前後改了什麼

來源說明：
- 改動前：`title_abstract_reviewer.py` 的早期 generic prompt（git `e7df8f4`）
- 改動後：`title_abstract_reviewer.py` 的 stage-aware prompt（git `3689023`）
- 下方內容是**中文翻譯版**，方便直接放進中文報告閱讀

#### 4.4.1 改動前 prompt（中文翻譯）

<div style="background:#f3f4f6; border:1px solid #d1d5db; border-radius:8px; padding:12px 14px; margin:10px 0;">
<pre style="white-space:pre-wrap; margin:0;">
請審查下面的 title 與 abstract，並依據納入條件與排除條件判斷是否應該納入。
注意：只有在同時符合所有納入條件，且不符合任何排除條件時，才應納入。

輸入項目：
<<${item}$>>

納入條件：
${inclusion_criteria}$

排除條件：
${exclusion_criteria}$

指示：
1. 請輸出 1 到 5 的整數分數：
   - 1 = 絕對排除
   - 2 = 較傾向排除
   - 3 = 不確定是否納入或排除
   - 4 = 較傾向納入
   - 5 = 絕對納入

${reasoning}$
${additional_context}$
${examples}$
</pre>
</div>

#### 4.4.2 改動後 prompt（中文翻譯）

<div style="background:#f3f4f6; border:1px solid #d1d5db; border-radius:8px; padding:12px 14px; margin:10px 0;">
<pre style="white-space:pre-wrap; margin:0;">
Stage 1 審查（只看 title + abstract）

你現在只審查 title 與 abstract，目的是決定這篇 paper 是否應繼續往後送審。
不要使用、也不要假設任何 full text 內容。
這一階段採高召回篩選：只要證據不完整，就不要過早排除。

輸入項目：
<<${item}$>>

納入條件：
${inclusion_criteria}$

排除條件：
${exclusion_criteria}$

指示：
1. 請輸出 1 到 5 的整數分數：
   - 1 = 強烈不納入
   - 2 = 較可能不納入
   - 3 = 不確定 / 需要更多證據
   - 4 = 較可能納入
   - 5 = 強烈納入
2. 這是 Stage 1：
   - 只能使用 title 與 abstract。
   - 不可把「缺少細節」直接當成排除證據。
   - 如果資訊不足，通常應給 3，而不是 1 或 2。
3. 若 paper 主題相關，但 title/abstract 沒有提供足夠明確證據，應先保留為 3，不要提早排除。
4. 如果你不確定，請給 3，並說明缺的是什麼證據。
5. reasoning 必須簡短，並用一小段話說清楚你打分的關鍵依據。
6. 不要捏造任何輸入文字裡沒有出現的資訊。

${reasoning}$
${additional_context}$
${examples}$
</pre>
</div>

#### 4.4.3 這組 prompt 差在哪裡

| 面向 | 改動前 | 改動後 | 白話說明 |
| --- | --- | --- | --- |
| Stage awareness | 沒有明講這是 Stage 1 | 明講只看 `title + abstract` | reviewer 不再把 abstract 階段當成全文審查。 |
| 對 full text 的態度 | 沒有明確限制 | 明講不能假設 full text | 不准再腦補「也許全文會補齊」。 |
| 預設裁決傾向 | 比較像一般 include/exclude 判斷 | 明確偏高召回，資訊不足優先 `3` | 這直接把很多早期 `exclude` 拉回 `maybe`。 |
| 對證據缺漏的處理 | 沒特別說 | 缺證據不等於排除證據 | 白話：看不到，不代表沒有。 |
| reasoning 要求 | 幾乎只有輸出分數 | 要說明關鍵證據與缺什麼 | 讓後面比較容易分析為什麼被打成 `3`。 |

### 4.5 Prompt 對照二：Stage 1 `SeniorLead` 在 `senior_prompt_tuned` 前後改了什麼

來源說明：
- 改動前：`scripts/screening/runtime_prompts/runtime_prompts.json` 中的 `stage1_senior_no_marker`
- 改動後：同檔中的 `stage1_senior_prompt_tuned`
- 下方同樣是**中文翻譯 / 中文整理版**

#### 4.5.1 改動前 prompt（`stage1_senior_no_marker`）

<div style="background:#f3f4f6; border:1px solid #d1d5db; border-radius:8px; padding:12px 14px; margin:10px 0;">
<pre style="white-space:pre-wrap; margin:0;">
你是一位資深 reviewer，負責整合 junior reviewer 的回饋並做最後決定。

補充情境：
兩位 junior reviewer 已經給了初步判斷。
請先看他們的回饋，再做整合判斷。
</pre>
</div>

#### 4.5.2 改動後 prompt（`stage1_senior_prompt_tuned`）

<div style="background:#f3f4f6; border:1px solid #d1d5db; border-radius:8px; padding:12px 14px; margin:10px 0;">
<pre style="white-space:pre-wrap; margin:0;">
你是 Stage 1 的資深裁決 reviewer。
你的目標是：只根據 title + abstract 的證據，對關鍵邊界案件做出可追溯的裁決。
你只能使用：
- title
- abstract
- 兩位 junior 的 output 與 evaluation
你不能假設 full text 會補齊缺漏。

嚴格模式裁決規則：
1. 只能使用目前輸入裡明確出現的資訊，不可依賴看不到的全文。
2. 不能把主題相關、概念相似、方法相似、領域相鄰，當成足夠的納入證據。
3. 只有在以下條件同時成立時，才能給 `3 / maybe`：
   a. 至少有一條可追溯的核心正向納入訊號。
   b. 只缺一個關鍵條件。
   c. 而且那個缺口在目前的 title/abstract 真的無法直接判定。
4. 如果只是 topic-adjacent、method-related、metadata-like，或只是提到相關關鍵字但沒有核心正向證據，應偏向給 `1` 或 `2`。
5. 高相關不等於納入：除非核心資格條件有被明確支持，否則不要因為「看起來很像」就保留。
6. reasoning 必須明確寫出：
   - 看到了什麼正向證據
   - 缺了什麼關鍵條件
   - 為什麼這樣會導向排除或暫留
</pre>
</div>

#### 4.5.3 這組 prompt 差在哪裡

| 面向 | `no_marker` | `prompt_tuned` | 白話說明 |
| --- | --- | --- | --- |
| Senior 角色 | 只說「整合 junior 回饋」 | 改成「Stage 1 邊界裁決者」 | 從一般整合者變成偏嚴格的裁判。 |
| 可用證據 | 沒有寫得很死 | 明文限制只能用 `title + abstract + juniors` | 不准再把全文可能會說什麼算進來。 |
| `maybe = 3` 的門檻 | 幾乎沒限制 | 三條件同時成立才准給 `3` | 直接抑制 `maybe` 濫用。 |
| 對 topic-adjacent 的態度 | 沒有明確偏向 | 明確要求偏向 `1/2 exclude` | 讓 senior 更容易把沾邊但不夠核心的 case 排掉。 |
| reasoning | 普通整合說明 | 必須明講正向證據、缺口、排除理由 | 讓裁決更像 legal-style justification。 |

#### 4.5.4 這個 tuned prompt 的實際效果

| Paper | 主要效果 | 代價 |
| --- | --- | --- |
| `2409` | 壓掉很多 Stage 1 FP，precision 明顯上升 | Combined 仍沒有超過 `prompt_only_v1` |
| `2511` | 也能壓 FP | 同時犧牲了一部分 recall |
| `2601` | 幾乎沒有帶來值得的 precision 收益 | recall 明顯受傷，屬於負面效果 |

所以，`senior_prompt_tuned` 的本質不是「模型更聰明」，而是 **把 senior 改成更嚴格、更不願意給 maybe、更不願意因為主題相似就保留**。

## 5. 全域流程線：Stage 1 與 Combined 結果

說明：這一節只放「全域 pipeline / adjudication 線」的主要版本，還不包含後面針對 `2409/2511` 的 criteria 專案線。

### 5.1 Stage 1 F1 對照

| 實驗版本 | `2307` | `2409` | `2511` | `2601` | 四篇平均 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `before` | 0.8846 | 0.7391 | 0.7843 | 0.8760 | 0.8210 |
| `prompt_only_v1` | 0.9593 | 0.6364 | 0.7895 | 0.9690 | 0.8385 |
| `recall_redesign` | 0.9448 | 0.4468 | 0.5714 | 0.9682 | 0.7328 |
| `senior_adjudication_v1` | 0.9563 | 0.6087 | 0.7229 | **0.9809** | 0.8172 |
| `senior_no_marker` | **0.9621** | 0.6176 | 0.7160 | 0.9792 | 0.8188 |
| `senior_prompt_tuned` | 0.9489 | **0.7636** | **0.8387** | 0.8896 | **0.8602** |

### 5.2 Combined F1 對照

| 實驗版本 | `2307` | `2409` | `2511` | `2601` | 四篇平均 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `before` | 0.8000 | 0.7556 | 0.7843 | 0.8567 | 0.7991 |
| `prompt_only_v1` | 0.9429 | **0.8235** | 0.8710 | 0.9548 | **0.8980** |
| `recall_redesign` | 0.9521 | 0.6269 | 0.8406 | 0.9545 | 0.8435 |
| `senior_adjudication_v1` | 0.9426 | 0.6562 | 0.7179 | 0.9687 | 0.8214 |
| `senior_no_marker` | **0.9581** | 0.6885 | 0.7941 | **0.9733** | 0.8535 |
| `senior_prompt_tuned` | 0.9358 | 0.7778 | 0.8525 | 0.8860 | 0.8630 |

### 5.3 這組表格怎麼看

| 觀察 | 證據 | 白話說明 |
| --- | --- | --- |
| `prompt_only_v1` 是很強的早期跳升 | 平均 Combined F1 從 `0.7991` 升到 `0.8980` | 單純把 prompt 對齊，就先解掉了一大批明顯錯誤。 |
| `recall_redesign` 雖然把 FN 壓低，但 precision 代價太大 | 平均 Stage 1 F1 從 `0.8385` 掉到 `0.7328` | 「寧可全收」會讓太多假陽性衝進來。 |
| `senior_no_marker` 比 `senior_adjudication_v1` 更乾淨 | 四篇 combined 都是 no-marker 較好 | 代表 marker heuristic 不是好方向。 |
| `senior_prompt_tuned` 不能全域採用 | `2409/2511` 進步，但 `2601` Combined F1 掉到 `0.8860` | 更嚴格的 senior 不是萬靈丹。 |
| 四篇最佳版本不一致 | `2307/2601` 最好是 `senior_no_marker`；`2409/2511` 在這條線上最好是 `prompt_only_v1` | 同一套 global workflow 無法同時把四篇都推到最好。 |

## 6. 診斷與驗證：為什麼不是再繼續調 senior

### 6.1 `nlp_prisma_screening_diagnosis` 的主要結論

| 診斷題目 | 結論 | 白話說明 |
| --- | --- | --- |
| 主要瓶頸在哪？ | Stage 1 仍是主瓶頸，但成因不只一個 | 一部分是 criteria 在 title/abstract 階段太難觀測，一部分是 senior prompt 不能跨 paper 通用。 |
| `2409` 與 `2511` 問題一樣嗎？ | 不完全一樣 | `2409` 比較像 hard FP / topic-adjacent 判讀，`2511` 比較像 criteria boundary 與證據表述問題。 |
| `2601` 為什麼特別怕嚴格 senior？ | 因為很多真陽性只有弱訊號 | senior 一旦太保守，就會把本來該保留的文獻提早丟掉。 |
| 下一步最值得做什麼？ | frozen replay + criteria 線專案 | 先把 senior effect 與 criteria effect 分開驗證，不要再做混雜的大亂鬥 rerun。 |

### 6.2 `frozen_senior_replay` 的驗證結果

| 比較面向 | `replay no-marker` vs `replay tuned` 結果 | 白話說明 |
| --- | --- | --- |
| `2409` | F1 `0.6176 -> 0.7925` | 更嚴格 senior 確實能壓掉很多 FP。 |
| `2511` | F1 `0.7073 -> 0.8182` | 也有改善，但要付出一些 recall 代價。 |
| `2601` | F1 `0.9765 -> 0.8727` | 同樣的嚴格策略對 `2601` 幾乎是災難。 |
| 整體判斷 | tuned effect 不是 rerun noise | 問題不是「重跑剛好多了/壞了」，而是 senior prompt 真的改變了 decision 行為。 |

## 7. `2409` / `2511` 的 criteria 專案線

### 7.1 直接對照表

| Paper | 版本 | 方法立場 | Stage 1 F1 | Combined F1 | 相對 `senior_no_marker` 變化 | QA 前狀態 |
| --- | --- | --- | ---: | ---: | --- | --- |
| `2409` | `senior_no_marker` | no-marker 基準線 | 0.6176 | 0.6885 | baseline | 歷史基準 |
| `2409` | `senior_prompt_tuned` | 靠更嚴 senior 壓 FP | 0.7636 | 0.7778 | `+0.1460 / +0.0893` | 歷史比較，不採用為全域方案 |
| `2409` | `criteria_2409_stage_split` | 先把 2409 criteria 拆成 Stage 1 / Stage 2 | 0.6885 | 0.7778 | `+0.0709 / +0.0893` | 歷史前身 |
| `2409` | `stage_split_criteria_migration` | 正式 stage-split、source-faithful current architecture | 0.7500 | 0.7843 | `+0.1324 / +0.0958` | QA 前 current authority |
| `2511` | `senior_no_marker` | no-marker 基準線 | 0.7160 | 0.7941 | baseline | 歷史基準 |
| `2511` | `senior_prompt_tuned` | 靠更嚴 senior 壓 FP | 0.8387 | 0.8525 | `+0.1227 / +0.0583` | 歷史比較 |
| `2511` | `criteria_2511_opv2` | operational hardening decision table | 0.8788 | 0.9206 | `+0.1627 / +0.1265` | 歷史高分，但方法學上否決 |
| `2511` | `stage_split_criteria_migration` | 正式 stage-split、source-faithful current architecture | 0.8657 | 0.8814 | `+0.1496 / +0.0872` | QA 前 current authority |

### 7.2 `source-faithful` 與 `operational` 的歷史對照

說明：這張表來自 `docs/source_faithful_vs_operational_2409_2511_report.md`，是歷史比較，不是 current score authority。

| Paper | 版本立場 | Stage 1 F1（3 runs mean） | Combined F1（3 runs mean） | 解讀 |
| --- | --- | ---: | ---: | --- |
| `2409` | `operational` | 0.6923 | 0.7827 | operational 有幫助，但不是唯一可行方向。 |
| `2409` | `source-faithful` | **0.7999** | **0.8427** | 在 2409，上乾淨語義不一定比較差。 |
| `2511` | `operational` | **0.8984** | **0.9120** | 2511 的高分很大一部分來自更強的 operational hardening。 |
| `2511` | `source-faithful` | 0.8705 | 0.8784 | 語義較乾淨，但少了部分靠硬化規則換來的分數。 |

### 7.3 這組表格怎麼看

| 問題 | 結論 | 白話說明 |
| --- | --- | --- |
| `2409` 的核心問題是什麼？ | stage-mixing + hard FP/evidence interpretation | Stage 1 只能看摘要，卻常被迫做接近全文等級的判斷。 |
| `2511` 的核心問題是什麼？ | operational criteria 很能拿分，但容易越界 | 如果把模型友善的硬規則直接當成原 paper 規則，就會方法學失真。 |
| 為什麼 `criteria_2511_opv2` 不採用？ | 分數高，但屬於 criteria supertranslation | 白話是「雖然考高分，但有作弊嫌疑」。 |
| 為什麼最後選 `stage_split_criteria_migration`？ | 它把規則來源、stage 差異、方法學邊界都切乾淨 | 雖然不是所有 paper 都拿到歷史最高分，但最能作為可維護的正式架構。 |

### 7.4 `2409` / `2511` 的問題拆解概念流程圖

```text
舊狀態
一份 criteria 同時拿來管初篩和全文審查
  |
  v
問題 1：初篩常被迫做太細的判斷
  |
  +--> 在 2409
  |      容易把相近主題也看成符合
  |
  +--> 在 2511
         容易靠額外硬規則把分數拉高
  |
  v
改法
拆成兩份 criteria
  - Stage 1：只保留摘要看得到的條件
  - Stage 2：保留完整 canonical 條件
  |
  v
好處
規則來源更乾淨
stage 差異更清楚
  |
  v
剩下的問題
更像是證據怎麼被讀、怎麼被整理
而不只是 criteria 文字再改幾句
```

## 8. 哪些結論最後被寫進 current state

| 主題 | 最後採用結論 | 依據 | 白話說明 |
| --- | --- | --- | --- |
| Runtime prompt | 讀 `runtime_prompts.json` | prompt externalization + current handoff | Prompt 不再散在舊模板裡。 |
| Stage 1 routing | 雙高分 include；雙低分 exclude；其餘 senior | `senior_no_marker` 線 + `AGENTS.md` | routing 規則最後收斂成簡單、可解釋的數值規則。 |
| `SeniorLead` | 必須保留 | adjudication 線歷史 + `AGENTS.md` | 不是拿掉 senior，而是讓 senior 只處理真正模糊的案子。 |
| Marker heuristic | 移除 | `stage1_senior_no_marker_report.md` | 不再走「看 reasoning 關鍵字」的捷徑。 |
| Global strict senior | 不採用 | prompt tuning + frozen replay + 2601 崩盤 | 某些 paper 有用，但不能當全域答案。 |
| Criteria 結構 | Stage 1 / Stage 2 正式分檔 | `stage_split_criteria_migration_report.md` | 初篩版條件與全文版條件正式分開。 |
| `criteria_jsons/*.json` | 降級為 historical only | `AGENTS.md` | 舊 criteria 留著做歷史比較，不再當現行輸入。 |
| Guidance 第三層 | 不採用 | migration report + `AGENTS.md` | 不再額外塞一層半正式規則。 |

## 9. 代表性歷史高點 vs QA 前 current authority

這張表最重要，因為它說明「代表性歷史高點」不等於「QA 前正式採用版本」。  
這裡的「代表性歷史高點」指的是各 paper 在主要歷史實驗線中，最常被拿來比較、且最能代表當時方向的一個高點版本；它不等於所有歷史報告中任何聚合統計的絕對最大值。

| Paper | 代表性歷史高點 | Combined F1 | QA 前 current authority | Combined F1 | 為什麼不是直接採這個版本 |
| --- | --- | ---: | --- | ---: | --- |
| `2307` | `senior_no_marker` | 0.9581 | `senior_no_marker` | 0.9581 | 這篇剛好歷史高分與 current authority 一致。 |
| `2409` | `prompt_only_v1`（全域流程線） | 0.8235 | `stage_split_criteria_migration` | 0.7843 | current authority 追求的是 stage-specific、source-faithful 架構，不只是單次分數。 |
| `2511` | `criteria_2511_opv2` | 0.9206 | `stage_split_criteria_migration` | 0.8814 | `opv2` 有明顯 criteria supertranslation，因此方法學上不能升格成 current state。 |
| `2601` | `senior_no_marker` | 0.9733 | `senior_no_marker` | 0.9733 | 這篇對 strict senior 太敏感，所以維持 no-marker。 |

## 10. 為什麼 QA 會成為下一步

| QA 前觀察 | 證據 | 白話說明 |
| --- | --- | --- |
| `2409` 在 source-faithful current state 下仍有 residual FP | current Combined F1 = `0.7843` | 規則拆乾淨之後，剩下的問題更像是「證據怎麼被理解」，不是再加幾句 criteria 就能解。 |
| `2511` 在乾淨語義下仍低於歷史 `opv2` | current Combined F1 = `0.8814`；`opv2` = `0.9206` | 代表過去部分高分來自 hardening；若不想作弊，就得換別的方式穩住 evidence interpretation。 |
| 全域 strict senior 不能當解法 | `2601` tuned Combined F1 = `0.8860` | 不能再靠「把 senior 變更嚴」來救全部 paper。 |
| Stage-split 已把 criteria 邊界整理乾淨 | current architecture 已正式採用 `criteria_stage1/` + `criteria_stage2/` | 既然 criteria 本體已經相對乾淨，下一步自然會往 evidence QA / synthesis 移動。 |

## 11. 來源檔案索引

| 類型 | 檔案 | 用途 |
| --- | --- | --- |
| Current state | `AGENTS.md` | 定義 QA 前 current architecture、current authority、方法學邊界。 |
| Current state | `docs/chatgpt_current_status_handoff.md` | 提供目前正式 handoff 與實驗主線摘要。 |
| Current state | `screening/results/results_manifest.json` | 提供各 paper 的 current metrics authority 與歷史 baseline 索引。 |
| Per-paper current state | `screening/results/2307.05527_full/CURRENT.md` | 說明 `2307` 目前以 `senior_no_marker` 為 stable reference。 |
| Per-paper current state | `screening/results/2409.13738_full/CURRENT.md` | 說明 `2409` 目前以 `stage_split_criteria_migration` 為 authority。 |
| Per-paper current state | `screening/results/2511.13936_full/CURRENT.md` | 說明 `2511` 目前以 `stage_split_criteria_migration` 為 authority。 |
| Per-paper current state | `screening/results/2601.19926_full/CURRENT.md` | 說明 `2601` 目前以 `senior_no_marker` 為 stable reference。 |
| Global workflow history | `docs/prompt_only_runtime_realignment_report.md` | prompt 對齊實驗與 early jump。 |
| Global workflow history | `docs/stage1_recall_redesign_report.md` | recall-first 路線的得失。 |
| Global workflow history | `docs/stage1_senior_adjudication_redesign_report.md` | senior adjudication 路線。 |
| Global workflow history | `docs/stage1_senior_no_marker_report.md` | marker heuristic 移除的關鍵證據。 |
| Global workflow history | `docs/stage1_senior_prompt_tuning_report.md` | strict senior 的利弊。 |
| Diagnostic history | `docs/nlp_prisma_screening_diagnosis_report.md` | 問題分解與下一步建議。 |
| Validation history | `docs/frozen_senior_replay_report.md` | 驗證 senior prompt effect 不是 noise。 |
| Criteria history | `docs/criteria_2511_operationalization_v2_report.md` | `2511 opv2` 歷史高分與其方法學問題。 |
| Criteria history | `docs/criteria_2409_stage_split_report.md` | `2409` criteria stage-split 前身。 |
| Methodology history | `docs/source_faithful_vs_operational_2409_2511_report.md` | source-faithful vs operational 的關鍵比較。 |
| Current architecture adoption | `docs/stage_split_criteria_migration_report.md` | QA 前最後採用的正式架構。 |

## 12. 最後總結

| 問題 | 最後答案 |
| --- | --- |
| QA 前整條實驗線最後收斂到哪裡？ | 收斂到「score-based routing + no-marker + stage-specific criteria + source-faithful methodology」。 |
| 哪些方向被證明只是局部有效？ | strict senior prompt、`2511 opv2` 類的 operational hardening。 |
| 哪個轉折最關鍵？ | `frozen_senior_replay` 證明 senior prompt effect 是真的，`source_faithful_vs_operational` 則證明高分不一定方法學正當。 |
| 為什麼 QA 會變成下一步？ | 因為規則層已經清理得差不多，剩下的核心不穩定更像是 evidence extraction / synthesis 問題。 |
