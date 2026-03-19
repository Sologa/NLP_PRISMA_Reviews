# QA 之前的實驗流程與結果整理報告

日期：2026-03-18  
範圍：本報告整理 `QA-first` 實驗啟動之前的主要實驗線，終點到 `stage_split_criteria_migration` 與目前 handoff 為止。  
不納入範圍：`docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md` 與 `qa_first_experiments/` 內的 QA-first 實驗資產。  

## 1. 四篇 SR 分別在做什麼

先說明：這裡的 `SR` 是 `systematic review`，也就是「系統性文獻回顧」。  
白話說，四篇 SR 各自都有一個明確主題，目標是從大量候選論文裡，找出真正屬於那個主題範圍的研究。

### 1.1 四篇 SR 的主題總表

| Paper | SR 題目 | 這篇 SR 在看什麼 | 白話說明 | 一個直覺例子 |
| --- | --- | --- | --- | --- |
| `2307.05527` | *The Ethical Implications of Generative Audio Models* | 生成式音訊模型的倫理問題 | 這篇不是在問「模型準不準」，而是在看「這類模型會帶來哪些道德、法律、社會風險」。 | 例如：一篇討論 deepfake 聲音、聲音版權、聲音模仿同意權的研究。 |
| `2409.13738` | *NLP4PBM: Process Extraction using NLP* | 用 NLP 從自然語言文字抽出流程模型 | 重點是「把文字敘述變成流程圖或流程結構」，不是一般 NLP 都算。 | 例如：把客服流程描述、醫療流程文件、作業手冊，自動轉成 process model。 |
| `2511.13936` | *Preference-Based Learning in Audio Applications* | 音訊領域中的偏好式學習 | 重點是「用偏好訊號來學習」，像 A/B 比較、排序、偏好回饋，而不是只拿偏好做最後評分。 | 例如：讓人比較兩段語音或音樂，模型再根據這些偏好更新訓練。 |
| `2601.19926` | *The Grammar of Transformers* | Transformer 語言模型裡的句法知識與可解釋性 | 重點是看 Transformer 內部到底有沒有學到文法結構，以及研究者怎麼證明這件事。 | 例如：分析 BERT/GPT 是否知道主詞動詞一致、依存關係、句法樹等結構。 |

### 1.2 每篇 SR 的「會收什麼」與「不收什麼」

說明：下面的例子是依目前 active criteria 整理出的白話例子，用來幫助理解範圍，不是正式 criteria 原文。

| Paper | 會收的研究 | 不收的研究 | 白話上的邊界 |
| --- | --- | --- | --- |
| `2307.05527` | 以生成式音訊為主題的完整研究論文，主軸是音訊生成模型或應用，並討論倫理、法律、社會議題。 | 純 ASR/轉錄、影像或影片生成、分類/預測模型、主輸出不是音訊的工作。 | 如果研究最後產生的是文字、影像、影片，而不是音訊，就通常不在這篇 SR 裡。 |
| `2409.13738` | 用 NLP 從自然語言文字抽出流程表示，且有具體方法與實驗驗證的原創研究。 | 流程預測、流程比對、流程重設計、情緒分析、只做一般 IE/分類但沒有真正抽出流程模型的工作。 | 不是「有用 NLP 處理流程相關文字」就算；要真的抽出 process model 才算。 |
| `2511.13936` | 在音訊領域裡，用 ranking、A/B 比較、偏好回饋或 RL loop 來訓練模型的研究。 | 只用偏好來做 evaluation、沒有 learning component 的工作；survey/review。 | 關鍵不是「有沒有問人喜不喜歡」，而是這個偏好有沒有真的拿來驅動學習。 |
| `2601.19926` | 研究 Transformer-based LM，並且實證分析它們的句法知識或文法結構。 | 非 Transformer 架構、只談模型但不分析 syntax、沒有實證內容的 survey / position paper。 | 不是所有 interpretability paper 都算；要明確碰到 syntax，且對象要是 Transformer LM。 |

### 1.3 這些主題裡常見的專有名詞

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

## 2. 一頁摘要

| 問題 | 結論 | 白話說明 |
| --- | --- | --- |
| QA 之前最後採用的架構是什麼？ | `runtime_prompts.json` + `criteria_stage1/` + `criteria_stage2/` + Stage 1 兩位 junior / 不一致送 `SeniorLead` | 系統最後不是靠一份通用 criteria 或一個超強 senior prompt，而是把 Stage 1 與 Stage 2 的規則正式拆開。 |
| 哪些規則被正式保留下來？ | `double-high include`、`double-low exclude`、其餘送 senior；移除 marker heuristic；保留 `SeniorLead` | 兩個初審都高分就收、都低分就拒；卡在中間才交給資深 reviewer。 |
| 哪些方向被否定？ | 全域嚴格 senior prompt、junior reasoning marker heuristic、把 operational hardening 偷寫回 criteria | 不能靠「更嚴格的資深裁決」或「看 junior 解釋文字關鍵字」吃遍四篇 paper。 |
| 哪些 paper 在 QA 前最麻煩？ | `2409.13738`、`2511.13936` | 這兩篇在 source-faithful 前提下，仍有 evidence interpretation / criteria observability 問題。 |
| 為什麼 `2409/2511` 都還不到 `0.9`？ | `2409` 主要卡 hard FP；`2511` 主要卡 boundary ambiguity | 前者比較像「太多看起來很像、其實不算」；後者比較像「同一句摘要到底算不算 preference learning，很容易解讀不一樣」。 |
| 為什麼會走到 QA 前夕？ | criteria 與 routing 已經整理到相對乾淨，但 decision layer 仍常直接吃自由文本證據 | 白話說，規則本身已經比較乾淨了，但模型還是常常「看文章自己腦補」，所以才開始考慮先做 QA / evidence extraction。 |

### 2.1 QA 前的 current authority

| Paper | QA 前 current authority | Stage 1 F1 | Combined F1 | 狀態 | 白話說明 |
| --- | --- | ---: | ---: | --- | --- |
| `2307.05527` | `senior_no_marker` | 0.9621 | 0.9581 | stable reference | 目前穩定，不是主要戰場。 |
| `2409.13738` | `stage_split_criteria_migration` | 0.7500 | 0.7843 | current active | 已改成 stage-split source-faithful criteria，但還有 hard FP。 |
| `2511.13936` | `stage_split_criteria_migration` | 0.8657 | 0.8814 | current active | 語義更乾淨，但比歷史上最激進的 operational 版本低。 |
| `2601.19926` | `senior_no_marker` | 0.9792 | 0.9733 | stable reference | 對過嚴 senior 很脆弱，因此維持 no-marker。 |

### 2.2 QA 前最後的 production workflow

| 元件 | QA 前採用狀態 | 白話說明 |
| --- | --- | --- |
| Runtime prompt 來源 | `scripts/screening/runtime_prompts/runtime_prompts.json` | 真正執行時讀這個 JSON，不再依賴舊 markdown prompt 模板。 |
| Stage 1 criteria | `criteria_stage1/<paper_id>.json` | 給 title/abstract 用的「可觀測版」條件。 |
| Stage 2 criteria | `criteria_stage2/<paper_id>.json` | 給 full text 用的完整 canonical 條件。 |
| Stage 1 routing | 兩位 junior；雙高分直接 include；雙低分直接 exclude；其餘送 `SeniorLead` | 先讓便宜 reviewer 篩一遍，模糊的再交給資深 reviewer。 |
| Marker heuristic | 已移除 | 不再靠 reviewer 解釋文字裡有沒有某些關鍵字來決定流程。 |
| Guidance 第三層 | 不採用 | 不再額外加一層「隱藏規則說明」，避免規則來源變成三套。 |

### 2.3 QA 前 production workflow 概念流程圖

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

先說明：下面這些名字大多是 repo 內的實驗 tag，不是讀者本來就該知道的正式術語。  
所以這裡改成「repo 名稱 + 中文稱呼」一起看。

表 4.2A 主要改動與是否採用

| 順序 | Repo 名稱 | 中文稱呼 | 核心改動 | QA 前是否採用 |
| --- | --- | --- | --- | --- |
| 0 | `before` baseline | 原始舊版起點 | 還沒做後續修正前的 prompt / workflow 基準線 | 否 |
| 1 | `prompt_only_runtime_realignment` | reviewer prompt 對齊版 | 把實際 runtime 用的 reviewer prompt 對齊，不改 schema | 部分吸收 |
| 2 | `stage1_recall_redesign` | Stage 1 高召回優先版 | 盡量不要漏掉真陽性，因此重設 Stage 1 流程，也動到 serialization、aggregation、missing_fulltext | 否 |
| 3 | `stage1_senior_adjudication_redesign` | SeniorLead 仲裁重整版 | 重整 `SeniorLead` 什麼時候進場、怎麼接手模糊案例 | 部分吸收 |
| 4 | `stage1_senior_no_marker` | 去掉 marker 規則版 | 拿掉 marker heuristic，改成純分數 routing，不再看 junior reasoning 關鍵字 | 是 |
| 5 | `stage1_senior_prompt_tuning` | 嚴格 senior prompt 版 | 不改流程，只把 senior prompt 調得更保守、更不願意給 maybe | 否 |
| 6 | `nlp_prisma_screening_diagnosis` | 全面診斷報告 | 交叉核對 raw JSON、criteria、prompt、runtime，找真正瓶頸 | 不是 production 變更 |
| 7 | `frozen_senior_replay` | 固定 junior、重放 senior 驗證 | junior 輸入固定不變，只重放 senior 決策，用來驗證 senior prompt effect 是不是真存在 | 是，作為結論依據 |
| 8 | `criteria_2511_operationalization_v2` | `2511` criteria 硬化決策表版 | 只改 `2511` criteria，把模糊語義寫成更硬、更像 decision table 的規則 | 否 |
| 9 | `criteria_2409_stage_split` | `2409` 先行分階段版 | 只改 `2409` criteria，先把 Stage 1 / Stage 2 邏輯拆開 | 部分吸收 |
| 10 | `source_faithful_vs_operational_2409_2511` | 忠於原文 vs 實務硬化對照 | 正式比較 source-faithful criteria 和 operational hardening criteria 的差別 | 是，方法學結論被採納 |
| 11 | `stage_split_criteria_migration` | 正式遷移到 stage-split criteria | 把系統正式改成 `criteria_stage1/` + `criteria_stage2/` 的架構 | 是，QA 前最後採用架構 |

表 4.2A 裡幾個容易看不懂的字，白話如下：

| 名詞 | 白話說明 |
| --- | --- |
| runtime realignment | 把「實際執行時真的在用的 prompt」對齊，不再讓文件版和程式版各講各的。 |
| recall redesign | 優先追求「不要漏掉該收的」，也就是 high recall 路線。 |
| adjudication | 仲裁。白話就是 junior 沒共識時，交給 senior 做最後裁決。 |
| no marker | 不再看 junior 解釋文字裡有沒有某些標記詞。 |
| prompt tuning | 不改模型參數，只改 prompt wording。 |
| frozen replay | 把前段輸入固定住，重播後段決策，看效果到底是不是那個 prompt 造成的。 |
| operationalization | 把抽象規則改寫成 reviewer 比較好執行的操作化規則。 |
| source-faithful | 盡量忠於原 paper 原本寫的 eligibility，不偷加 performance-oriented 硬規則。 |
| migration | 從舊架構正式搬到新架構，不只是做一個局部實驗。 |

表 4.2B 每輪想回答什麼、結果如何

| 順序 | 想回答什麼 | 代表結果 |
| --- | --- | --- |
| 0 | 原始起點表現如何？ | 四篇平均 Combined F1 = `0.7991` |
| 1 | 單純 prompt 對齊能不能先把大問題修掉？ | 四篇平均 Combined F1 升到 `0.8980` |
| 2 | 若盡量不漏掉真陽性，整體會不會更好？ | Recall 幾乎滿分，但 precision 大掉；平均 Combined F1 降到 `0.8435` |
| 3 | 更積極的 senior 仲裁能否同時守住 precision 與 recall？ | 比 recall redesign 穩，但四篇平均 Combined F1 僅 `0.8214` |
| 4 | 不看 reasoning 關鍵字，只看分數 routing，會不會更乾淨？ | 去掉 marker 規則版全面優於早期的 senior 仲裁重整版 |
| 5 | 更保守的 senior 能否壓低 `2409/2511` 的 FP？ | `2409/2511` 進步，但 `2601` 大崩；`2601` Combined F1 掉到 `0.8860` |
| 6 | 真正瓶頸到底在哪？ | 指出問題是「criteria 可觀測性」+「senior prompt 不可移植」的組合 |
| 7 | 嚴格 senior 的效果是真效果，還是 rerun noise？ | 證明 effect 主要來自 senior prompt 本身，不是 noise |
| 8 | `2511` 問題是不是主要卡在 criteria？ | Combined F1 到 `0.9206`，但方法學上被否決 |
| 9 | `2409` 是否是 stage-mixing 問題？ | Combined F1 從 `0.6885` 升到 `0.7778` |
| 10 | 高分到底是合理優化，還是超譯 criteria？ | 證實有些高分來自 criteria supertranslation |
| 11 | 如何在不偷加規則下，把 stage 差異正式落地？ | `2409` Combined F1 = `0.7843`；`2511` Combined F1 = `0.8814` |

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

### 5.3 Stage 1 / Stage 2（全文後）分開看

說明：repo 目前沒有一組獨立維護的「純 Stage 2 單獨 F1 authority」，因此這裡把

- `Stage 1`：title + abstract 初篩後的 F1
- `Stage 2 / 全文後`：經過 full-text review 後的最終 Combined F1

並排放在一起，讓讀者直接看出每個版本從初篩到全文確認後，分數是上升還是下降。

表 5.3A `2307` / `2409`

| 實驗版本 | `2307` Stage 1 | `2307` Stage 2 / 全文後 | `2409` Stage 1 | `2409` Stage 2 / 全文後 |
| --- | ---: | ---: | ---: | ---: |
| `before` | 0.8846 | 0.8000 | 0.7391 | 0.7556 |
| `prompt_only_v1` | 0.9593 | 0.9429 | 0.6364 | **0.8235** |
| `recall_redesign` | 0.9448 | 0.9521 | 0.4468 | 0.6269 |
| `senior_adjudication_v1` | 0.9563 | 0.9426 | 0.6087 | 0.6562 |
| `senior_no_marker` | **0.9621** | **0.9581** | 0.6176 | 0.6885 |
| `senior_prompt_tuned` | 0.9489 | 0.9358 | **0.7636** | 0.7778 |

表 5.3B `2511` / `2601`

| 實驗版本 | `2511` Stage 1 | `2511` Stage 2 / 全文後 | `2601` Stage 1 | `2601` Stage 2 / 全文後 |
| --- | ---: | ---: | ---: | ---: |
| `before` | 0.7843 | 0.7843 | 0.8760 | 0.8567 |
| `prompt_only_v1` | 0.7895 | **0.8710** | 0.9690 | 0.9548 |
| `recall_redesign` | 0.5714 | 0.8406 | 0.9682 | 0.9545 |
| `senior_adjudication_v1` | 0.7229 | 0.7179 | **0.9809** | 0.9687 |
| `senior_no_marker` | 0.7160 | 0.7941 | 0.9792 | **0.9733** |
| `senior_prompt_tuned` | **0.8387** | 0.8525 | 0.8896 | 0.8860 |

### 5.4 另外兩篇最佳 setting 的 confusion matrix

說明：`2307` 和 `2601` 在第 5 章這條全域流程線裡，最佳 setting 都是 `senior_no_marker`。  
這裡把它們在最佳 setting 下的 `TP / FP / TN / FN` 列出來，避免只看 F1 看不出失分結構。

表 5.4A `2307` 最佳 setting = `senior_no_marker`

| 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | ---: | ---: | ---: | ---: | --- |
| Stage 1 | 165 | 7 | 40 | 6 | 已經很平衡，只有少量 FP 與 FN。 |
| Stage 2 / 全文後 | 160 | 3 | 44 | 11 | 全文後 FP 更少，但 FN 增加一些，所以 recall 比 Stage 1 低。 |

表 5.4B `2601` 最佳 setting = `senior_no_marker`

| 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | ---: | ---: | ---: | ---: | --- |
| Stage 1 | 330 | 9 | 14 | 5 | 幾乎是高 TP、低 FP、低 FN 的穩定型。 |
| Stage 2 / 全文後 | 328 | 11 | 12 | 7 | 全文後略多一些 FP/FN，但整體仍非常穩。 |

直接說這兩篇的失分結構：

| Paper | 最佳 setting 下主要問題 | 白話說明 |
| --- | --- | --- |
| `2307` | 沒有單一嚴重崩盤；全文後是 **FN 稍多於 FP** | 代表它不是 precision 大崩，而是全文後有少數本來可保留的正例被洗掉。 |
| `2601` | 同樣沒有單一嚴重崩盤；全文後 **FP 與 FN 都很低** | 代表這篇本身就是比較容易做高分的 review。 |

### 5.5 這組表格怎麼看

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

## 10. 為什麼 `2409` / `2511` 都還不到 `0.9`，以及 `stage_split_criteria_migration` 到底改了什麼

這一章要先講清楚一件事：  
`2409/2511` 在 QA 前的後期改善，不只是在調 senior prompt。  
另一條非常關鍵的設定是：**把 Stage 1 與 Stage 2 用的 criteria 正式拆成兩份**。  

白話說，原本比較像是「同一份 criteria 在初篩和全文確認都硬套」；後來改成：

- Stage 1：只用摘要真的看得到的條件
- Stage 2：才用完整、忠於原 paper 的 canonical criteria

所以如果第 10 章只講「它們為什麼不到 `0.9`」，但不講這個設定到底改了什麼，會少掉一半重點。

### 10.1 先看 `senior_no_marker` vs `stage_split_criteria_migration`

這張表先回答最直接的問題：  
把 criteria 拆成 Stage 1 / Stage 2 兩份之後，和 `senior_no_marker` 基準線相比，分數到底有沒有變好？

| Paper | 設定 | Stage 1 F1 | Stage 2 / 全文後 Combined F1 | 相對 `senior_no_marker` 變化 | 白話解讀 |
| --- | --- | ---: | ---: | --- | --- |
| `2409` | `senior_no_marker` | 0.6176 | 0.6885 | baseline | 還沒正式拆開 stage-specific criteria 的基準線。 |
| `2409` | `stage_split_criteria_migration` | 0.7500 | 0.7843 | `+0.1324 / +0.0958` | 拆開後明顯變好，但仍不到 `0.9`。 |
| `2511` | `senior_no_marker` | 0.7160 | 0.7941 | baseline | 還沒正式拆開 stage-specific criteria 的基準線。 |
| `2511` | `stage_split_criteria_migration` | 0.8657 | 0.8814 | `+0.1496 / +0.0872` | 拆開後也明顯變好，但仍不到 `0.9`。 |

這張表的重點不是「拆完還是不夠高」，而是：

- 它**不是沒用**，因為 `2409/2511` 都比 `senior_no_marker` 明顯進步。
- 但它也**不是萬靈丹**，因為拆完後仍留下一批 hard case。

### 10.2 先看 confusion matrix：這兩篇主要卡 FP 還是 FN？

如果只看 `F1`，很容易看不出到底是 false positive 還是 false negative 在拖分。  
所以這裡直接把 `TP / FP / TN / FN` 列出來。

表 10.2A `2409` confusion matrix 對照

| 設定 | 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `senior_no_marker` | Stage 1 | 21 | 26 | 31 | 0 | 幾乎完全不是漏收問題，而是保留太多假陽性。 |
| `senior_no_marker` | Stage 2 / 全文後 | 21 | 19 | 38 | 0 | 全文後仍然是明顯 FP-heavy。 |
| `stage_split_criteria_migration` | Stage 1 | 21 | 14 | 43 | 0 | FP 明顯下降，但主要問題仍是 FP。 |
| `stage_split_criteria_migration` | Stage 2 / 全文後 | 20 | 10 | 47 | 1 | 仍以 FP 為主，只是比以前少很多。 |

表 10.2B `2511` confusion matrix 對照

| 設定 | 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `senior_no_marker` | Stage 1 | 29 | 22 | 32 | 1 | Stage 1 很明顯是 FP-heavy。 |
| `senior_no_marker` | Stage 2 / 全文後 | 27 | 11 | 43 | 3 | 全文後 FP 仍多，但已不像 Stage 1 那麼失衡。 |
| `stage_split_criteria_migration` | Stage 1 | 29 | 8 | 46 | 1 | Stage 1 的 FP 已大幅被壓下來。 |
| `stage_split_criteria_migration` | Stage 2 / 全文後 | 26 | 3 | 51 | 4 | 到 current state，FP 已不多，反而 FN 稍微比 FP 更突出。 |

直接回答「主要是在 FP 還是 FN」：

| Paper | 看哪個階段 | 主要問題 | 白話說明 |
| --- | --- | --- | --- |
| `2409` | Stage 1 與全文後都一樣 | **主要是 FP** | 不管拆分前後，它都比較像「把太多不該收的留下來」。 |
| `2511` | Stage 1 | **先是 FP** | 初篩時原本也很明顯是假陽性太多。 |
| `2511` | current state 的全文後 | **變成 FP / FN 都有，但 FN 稍微更突出** | 因為 FP 已壓到只剩 `3`，但 FN 變成 `4`。 |

所以更精確的結論是：

- `2409`：很明確是 **FP-dominant**。
- `2511`：不是單純一邊崩盤；在 `senior_no_marker` 時比較像 **FP-heavy**，但到了 `stage_split_criteria_migration` 的 current state，**FP 已被大幅修掉，剩下變成邊界案造成的 FN/recall 壓力也開始明顯**。

### 10.3 `stage1/2 criteria 分開` 這個設定，整體到底改了什麼

| 面向 | 拆開之前的問題 | `stage_split_criteria_migration` 之後 | 白話說明 |
| --- | --- | --- | --- |
| Criteria 結構 | 比較像同一套條件在不同 stage 共用 | 正式分成 `criteria_stage1/` 與 `criteria_stage2/` | 初篩和全文確認不再硬用同一份規則。 |
| Stage 1 角色 | 容易被迫提前判一些摘要看不穩的條件 | 只保留 title/abstract 可觀測投影 | 初篩只做它看得到的事。 |
| Stage 2 角色 | 容易和 Stage 1 混在一起 | 固定為 canonical、source-faithful 完整 eligibility | 全文階段才確認完整資格。 |
| Runtime 讀檔方式 | 舊路徑和 fallback 容易造成混用 | Stage 1 只讀 `criteria_stage1/`；Stage 2 只讀 `criteria_stage2/`；不使用 fallback | 避免系統偷偷讀回舊 criteria。 |
| Guidance 第三層 | 有機會再塞一層半正式規則 | 刻意不新增 guidance layer | 規則來源維持兩層，不變三層。 |
| 方法學定位 | 容易把 runtime 方便用的規則寫成正式 criteria | Stage 2 忠於原 paper；Stage 1 只做 observable projection | 不再把 performance hardening 偽裝成 paper 原本就有的條件。 |

一句話總結：  
這個設定的核心不是「再多加一些規則」，而是 **把該在 Stage 1 判的，和該在 Stage 2 判的，正式切乾淨**。

### 10.4 `2409` 在這個設定下，到底詳細改了哪些內容

先看 `2409` 拆開後，Stage 1 和 Stage 2 各自負責什麼：

| 面向 | Stage 1（摘要版 criteria） | Stage 2（全文版 criteria） | 白話說明 |
| --- | --- | --- | --- |
| 核心主題 | 只看摘要是否明確顯示「NLP for process extraction」 | 仍要求真的是 NLP for process extraction | 核心主題兩邊都看，但 Stage 1 只能用摘要證據判。 |
| 任務訊號 | 看摘要有沒有 text -> process representation / process model 的 observable signal | 用全文確認 paper 真正在做什麼任務 | Stage 1 只看「像不像這個任務」，Stage 2 再做完整確認。 |
| paper type / peer review / English / fulltext | 不在 Stage 1 硬判 | 放到 Stage 2 確認 | 這類條件摘要常看不穩，所以延後。 |
| primary research | 不在 Stage 1 硬判 | 放到 Stage 2 確認 | 避免初篩過早把「看不清楚」當成排除。 |
| concrete method + experiments | 不在 Stage 1 當硬門檻 | 放到 Stage 2 做完整確認 | 這是全文比較適合判的事。 |
| non-target examples | 在 Stage 1 保留明顯看得出的負例，如 redesign / matching / prediction / sentiment analysis | 在 Stage 2 用完整 EC.3 / EC.4 進一步排除 | 能在摘要確定不符的，先排；其餘留到後面。 |
| 遇到證據不完整時 | 明確寫成 keep `maybe`， defer to Stage 2 | Stage 2 再做 final confirmation | 這是拆分後很關鍵的一條。 |

這次還明確**移除了**一些不再寫進正式 criteria 的硬化內容：

| 被移除的東西 | 白話說明 |
| --- | --- |
| `Generic NLP/LLM/dataset/foundation-model paper -> exclude` | 不能因為看起來太泛就一刀切排掉。 |
| `Output-object mismatch: IE/NER/RE/classification/retrieval -> exclude` | 不能把某些方法名字直接當成硬排除規則。 |
| `compliance/recommendation/simulation` 等外擴 hard negatives | 不能把太多 operational 便利規則硬寫回正式 criteria。 |
| `executable extraction pipeline` 這類加嚴措辭 | 不能把 reviewer 想要的高標準直接偽裝成原 paper 明文條件。 |

白話總結 `2409` 的這次改動：

- 把「摘要只能看出大方向」和「全文才能確認的條件」切開。
- 讓 Stage 1 少做不該它做的確認題。
- 但即使這樣，`2409` 還是會留下很多 process-adjacent hard FP，所以分數仍上不去 `0.9`。

### 10.5 `2511` 在這個設定下，到底詳細改了哪些內容

`2511` 的拆法和 `2409` 不一樣，它不是把一堆 paper-type 條件往後丟而已，而是把「什麼算 preference-learning in audio」的可觀測邊界重新整理。

| 面向 | Stage 1（摘要版 criteria） | Stage 2（全文版 criteria） | 白話說明 |
| --- | --- | --- | --- |
| preference signal | 摘要看得到 ranking / A-B / comparative preference 就算正向訊號 | 全文以 canonical 定義確認 preference learning | Stage 1 先看有沒有偏好式學習的表面訊號。 |
| numeric ratings | 只有在摘要看得出 rating 被轉成 ranking / comparative preference 時才算 | Stage 2 確認它是否真的構成 preference learning | 單純打分數不等於偏好式學習。 |
| RL loop | 沒有 explicit comparison 也可保留，只要摘要顯示是 audio model 的 RL training loop | Stage 2 再確認它是否真的符合 final selection | 避免把沒有明寫 A/B 的 RL paper 直接漏掉。 |
| audio domain | Stage 1 保留 audio domain；multimodal including audio 也算 | Stage 2 仍維持 multimodal including audio 可納入 | 不把 audio-only 硬寫成唯一合法情況。 |
| evaluation-only preference | Stage 1 就可排除明顯只是拿 preferences 做 evaluation 的研究 | Stage 2 再用 canonical criteria 確認 | 這是 `2511` 最關鍵的負向邊界。 |
| survey / review | Stage 1 可排除明顯的 survey/review | Stage 2 繼續保留這條 | 這一條兩邊都相對直。 |

這次也明確**移除了**一些不再寫進正式 criteria 的硬化內容：

| 被移除的東西 | 白話說明 |
| --- | --- |
| `audio must be core` 強制門檻 | 不能偷把「audio 必須是唯一核心」寫成原 paper 明文規則。 |
| `training objective/loss/reward/model selection` 細粒度硬 gate | 不能把 reviewer 好判斷的細則直接升格為正式 criteria。 |
| `IEMOCAP/SEMAINE` 等資料集規則 | 不能把特定資料集經驗法則寫成 paper-grounded criteria。 |
| `SER/ordinal` 類額外硬化規則 | 不能把某些常見邊界案例直接硬編成 formal exclusion / inclusion。 |

白話總結 `2511` 的這次改動：

- 它不是單純把條件往後丟，而是把「摘要能看見的 preference-learning 訊號」整理成較乾淨的 Stage 1 投影。
- 同時把過去一些很會拿分、但方法學上站不住的 hardening 從正式 criteria 拿掉。
- 所以它的語義變乾淨了，但也少了那些「考試型捷徑」。

### 10.6 做完這些以後，為什麼還是不到 `0.9`

| Paper | 這個設定已經解掉什麼 | 這個設定還沒解掉什麼 | 所以為什麼還是不到 `0.9` |
| --- | --- | --- | --- |
| `2409` | 解掉 stage-mixing，也把很多不該在 Stage 1 硬判的條件往後移 | 沒解掉 process-adjacent / topic-adjacent hard FP | Stage 1 precision 仍只有 `0.6000`，全文後也只有 `0.6667`。 |
| `2511` | 解掉一部分方法學混亂，讓 Stage 1 與 Stage 2 的責任更清楚 | 沒解掉 abstract-level boundary ambiguity | 全文後 precision `0.8966` 已不差，但 recall `0.8667` 仍被邊界案拉住。 |

最白話的說法是：

- `2409`：現在比較像「規則拆乾淨了，但還是有很多看起來太像正例的假陽性」。
- `2511`：現在比較像「規則拆乾淨了，但很多摘要還是很難穩定判斷它到底是 learning 還是 evaluation」。

### 10.7 `2409/2511` 跟 `2307/2601` 最大差別是什麼

| 比較面向 | `2307 / 2601` | `2409` | `2511` |
| --- | --- | --- | --- |
| 核心 eligibility 訊號 | 相對直 | 很窄，而且鄰近主題很多 | 常藏在 preference / ranking / learning role 的語義裡 |
| 摘要可觀測性 | 較高 | 常只能看出 process-related | 常看到偏好訊號，但看不出是否真的進 learning |
| 最主要錯誤型態 | 零星邊界案 | hard FP | boundary ambiguity |
| 對 hardening 的依賴 | 不強 | 局部有幫助 | 很強，但容易越界 |

白話講，就是：

- `2307/2601` 比較像「摘要一看就知道大方向對不對」。
- `2409` 比較像「看起來很像，但其實差最後一條核心定義」。
- `2511` 比較像「同一句摘要，到底算 learning 還是 evaluation，很容易看法不同」。

### 10.8 這一章的最後結論

| 問題 | 最後答案 |
| --- | --- |
| `stage_split_criteria_migration` 有沒有幫助？ | 有，`2409/2511` 都比 `senior_no_marker` 明顯進步。 |
| 這個設定本質上改了什麼？ | 把 Stage 1 與 Stage 2 的 criteria 正式拆開，並強制 runtime 分流讀取。 |
| `2409` 拆開後為什麼還不到 `0.9`？ | 因為它仍然是明顯的 FP 問題，特別是 process-adjacent / topic-adjacent case。 |
| `2511` 拆開後為什麼還不到 `0.9`？ | 因為它已不再是單純 FP-heavy；在 current state 下 FP 已大幅下降，但 FN / recall 壓力變得更顯眼。 |
| 為什麼不能直接拿歷史更高分版本回來？ | 因為 `2511` 的 `>0.9` 高分很大一部分來自 operational hardening，而 current state 不接受把那種規則偽裝成正式 criteria。 |
| 為什麼這會把問題推向 QA？ | 因為 rules 已經比以前乾淨，剩下更像是 evidence extraction / evidence interpretation 問題。 |

## 11. 為什麼 QA 會成為下一步

| QA 前觀察 | 證據 | 白話說明 |
| --- | --- | --- |
| `2409` 在 source-faithful current state 下仍有 residual FP | current Combined F1 = `0.7843` | 規則拆乾淨之後，剩下的問題更像是「證據怎麼被理解」，不是再加幾句 criteria 就能解。 |
| `2511` 在乾淨語義下仍低於歷史 `opv2` | current Combined F1 = `0.8814`；`opv2` = `0.9206` | 代表過去部分高分來自 hardening；若不想作弊，就得換別的方式穩住 evidence interpretation。 |
| 全域 strict senior 不能當解法 | `2601` tuned Combined F1 = `0.8860` | 不能再靠「把 senior 變更嚴」來救全部 paper。 |
| Stage-split 已把 criteria 邊界整理乾淨 | current architecture 已正式採用 `criteria_stage1/` + `criteria_stage2/` | 既然 criteria 本體已經相對乾淨，下一步自然會往 evidence QA / synthesis 移動。 |

## 12. 來源檔案索引

| 類型 | 檔案 | 用途 |
| --- | --- | --- |
| Current state | `AGENTS.md` | 定義 QA 前 current architecture、current authority、方法學邊界。 |
| Current state | `docs/chatgpt_current_status_handoff.md` | 提供目前正式 handoff 與實驗主線摘要。 |
| Current state | `screening/results/results_manifest.json` | 提供各 paper 的 current metrics authority 與歷史 baseline 索引。 |
| Current criteria | `criteria_stage1/2409.13738.json` | 支撐 `2409` Stage 1 observable projection 的分析。 |
| Current criteria | `criteria_stage2/2409.13738.json` | 支撐 `2409` canonical full-eligibility 的分析。 |
| Current criteria | `criteria_stage1/2511.13936.json` | 支撐 `2511` Stage 1 boundary / observability 的分析。 |
| Current criteria | `criteria_stage2/2511.13936.json` | 支撐 `2511` preference-learning canonical boundary 的分析。 |
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

## 13. 最後總結

| 問題 | 最後答案 |
| --- | --- |
| QA 前整條實驗線最後收斂到哪裡？ | 收斂到「score-based routing + no-marker + stage-specific criteria + source-faithful methodology」。 |
| 哪些方向被證明只是局部有效？ | strict senior prompt、`2511 opv2` 類的 operational hardening。 |
| 哪個轉折最關鍵？ | `frozen_senior_replay` 證明 senior prompt effect 是真的，`source_faithful_vs_operational` 則證明高分不一定方法學正當。 |
| 為什麼 QA 會變成下一步？ | 因為規則層已經清理得差不多，剩下的核心不穩定更像是 evidence extraction / synthesis 問題。 |
