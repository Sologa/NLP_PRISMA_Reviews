# NLP_PRISMA_Reviews 詳細診斷報告：`2409` criteria boundary 深化分析與修正方案

Historical note:

- This report is a historical analysis document, not the current-state entrypoint.
- It was written before the current stage-split criteria migration became the authoritative state.
- References in this document to `criteria_jsons/*.json` and older score tables must not be treated as current production state.
- Current active files are:
  - `criteria_stage1/2409.13738.json`
  - `criteria_stage2/2409.13738.json`
  - `criteria_stage1/2511.13936.json`
  - `criteria_stage2/2511.13936.json`
- Current score authority is documented in:
  - `AGENTS.md`
  - `docs/chatgpt_current_status_handoff.md`
  - `screening/results/results_manifest.json`

## 0. 報告目的

本報告依照指定閱讀順序，重新整合以下九個核心檔案的結論，並在此基礎上對 `2409.13738` 的殘餘 hard false positives（hard FP）做更細的語義邊界拆解，提出一個**只改 criteria、不改 pipeline、不改 senior、不改 aggregation** 的可落地修正方案。

本報告主要依據的檔案如下：

1. `docs/chatgpt_current_status_handoff.md`
2. `docs/nlp_prisma_screening_diagnosis_report.md`
3. `docs/frozen_senior_replay_report.md`
4. `docs/criteria_2511_operationalization_v2_report.md`
5. `docs/criteria_2409_stage_split_report.md`
6. `criteria_jsons/2511.13936.json`
7. `criteria_jsons/2409.13738.json`
8. `scripts/screening/runtime_prompts/runtime_prompts.json`
9. `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

另外，我也參考了 `2409` 殘餘 hard FP 對應論文的摘要型資訊，以判斷目前 criteria 還漏掉哪些 paper-level boundary：

1. Kourani et al., **Process Modeling With Large Language Models**
2. Grohs et al., **Large Language Models can accomplish Business Process Management Tasks**
3. Bellan et al., **A Qualitative Analysis of the State of the Art in Process Extraction from Text**
4. Bellan et al., **Process Extraction from Text: Benchmarking the State of the Art and Paving the Way for Future Challenges**
5. López et al., **Challenges in Legal Process Discovery**

---

## 1. 執行摘要

### 1.1 我同意的總判斷

我同意目前的系統層總判斷，而且同意程度很高：

1. **系統層大方向已大致收斂。**
2. **現在不值得再追 global `SeniorLead` strict prompt。**
3. **`2409` 是目前最值得修的一篇。**
4. **`2511` 已經證明主要問題是 criteria operationalization，現在大致修好。**
5. **`2307` 與 `2601` 應維持現狀，避免全域策略副作用。**

這個結論不是主觀偏好，而是多份實驗報告共同收斂出的結果：

- handoff 已明確把 Stage 1 流程原則固定為：兩位 junior 都 `>=4` 直接 include、都 `<=2` 直接 exclude、其餘送 `SeniorLead`；並明寫 `SeniorLead` 必須保留、marker heuristic 已刪除，且「不要再追全域更好的 strict senior prompt」。
- diagnosis report 已指出：四篇 paper 的最佳 combined 版本分裂為兩組，`2307` / `2601` 最佳是 `senior_no_marker`，`2409` / `2511` 最佳更接近 prompt-only/criteria 問題，因此不存在一個簡單的全域 senior 解。
- frozen-input replay 已證明 strict senior prompt effect 是真的，但這個 effect 是 review-specific，不是全域可移植的。
- `2511` 只改 criteria 就同時提升 precision 與 recall，證明主問題確實在 criteria boundary。
- `2409` 只改 criteria stage split 後也有改善，但仍殘留 hard FP，說明剩餘問題更像 review-specific semantic boundary，而不是 senior calibration 沒調到位。

### 1.2 我不同意或保留的地方

我有兩個保留：

1. **我不會把 `2409` 的剩餘問題只描述成「target-object boundary」而已。**  
   我認為 target-object boundary 確實仍是最大塊，但不是全部。更完整的說法應該是：  
   **`2409` 剩餘 hard FP 是四類邊界疊加：**
   - target-object boundary
   - primary-objective boundary
   - contribution-type / paper-type boundary
   - source-input / directionality boundary

2. **我不認為再做一輪很小的 wording polishing 就一定能把 `2409` 全部修乾淨。**  
   最值得做的下一步仍然是 criteria surgery；但如果這一輪之後，同一族 hard FP 依然存活，我會把殘差判讀成：
   - title/abstract observability 極限，
   - 或 gold boundary 與 reviewer operational boundary 的張力，
   而不會再把責任歸給 global senior prompt。

### 1.3 最核心的解法

我建議的下一步是開一輪：

**`criteria_2409_boundary_v3`**

這一輪只做一件事：

> **只改 `criteria_jsons/2409.13738.json`，把目前的「core task + method-role + maybe 保留」改成一個像 `2511` 那樣的 ALL-gates decision table，並且把 hard negatives 寫成 paper-level、task-level、source-target-level 三層同時生效的排除規則。**

不應改動的東西：

1. 不改 `runtime_prompts.json`
2. 不改 `SeniorLead`
3. 不改 Stage 1 aggregation
4. 不改 pipeline code
5. 不動 marker heuristic
6. 不同時再碰 `2511`、`2307`、`2601`

成功標準：

1. `2409` combined precision 至少升到 `>= 0.70`
2. `2409` combined recall 維持 `1.0000`
3. combined FP 由 `12` 壓到 `<= 9`
4. `kourani_process_modelling_with_llm`、`grohs2023large`、`bellan2020qualitative`、`bellan2021process`、`lopez2021challenges` 這幾類 sentinel hard FP 必須明顯改善
5. `etikala2021extracting`、`honkisz2018concept`、`goncalves2011let` 這些已知 gold=true case 不能掉

---

## 2. 目前系統層判斷：我同意的部分與保留

### 2.1 我同意的部分

#### 2.1.1 Stage 1 流程原則已固定，不應再動大架構

目前 Stage 1 的固定原則是：

1. 兩 junior 都 `>=4`：直接 include
2. 兩 junior 都 `<=2`：直接 exclude
3. 其他：送 `SeniorLead`

而且：

1. `SeniorLead` 必須保留
2. `SeniorLead` 一旦介入，可單點裁決
3. marker heuristic 已刪除，不再回頭

這組原則已不只是暫時版本，而是 handoff 已明確列為「目前已收斂的流程原則」。因此任何下一輪設計，都應該把這一層視為固定底盤，而不是再重開 aggregation redesign。

#### 2.1.2 不值得再追 global senior prompt

frozen-input SeniorLead replay 的重要性，在於它把「senior prompt effect 是真的還是 rerun noise」這件事說清楚了。它證明了兩件事：

1. tuned senior 確實能幫 `2409`
2. tuned senior 也確實會明顯傷 `2601`

也就是說，**全域 strict senior 不是無效，而是不可移植。**

這意味著如果現在繼續把主力放在「找一個全域更好的 strict senior」，預期報酬很低，副作用很高。

#### 2.1.3 `2511` 現在可視為主問題已解

`2511` 這一輪最有力的證據，在於它是乾淨的單變因測試：

1. 只改 `criteria_jsons/2511.13936.json`
2. 不改 pipeline
3. 不改 runtime prompt
4. 不改 senior
5. 不改 aggregation

結果卻能同時提升 precision 與 recall，combined F1 來到 `0.9206`。  
這幾乎可以直接定性：**`2511` 的主問題確實是 criteria operationalization，不是 senior prompt。**

#### 2.1.4 `2307` 與 `2601` 現在不值得再冒全域退步風險

`2307` 已經很強，`2601` 更是高分且對 strict senior 極度敏感。  
因此，如果再做任何全域策略調整，都可能讓非瓶頸 paper 先退步。  
這在實驗優先順序上是不划算的。

### 2.2 我保留的部分

#### 2.2.1 `2409` 不只是 target-object boundary

handoff 把 `2409` 的剩餘問題濃縮成：

1. core target object boundary
2. process-adjacent 與 true text-to-process extraction 的語義邊界

我基本同意，但我會再往前拆一層：  
剩餘的 hard FP 其實不只是在問「產物是不是 process representation」，還在問：

1. 這篇 paper 的**核心研究目標**是不是 text-to-process extraction？
2. 這篇 paper 的**主要貢獻類型**是不是 extraction method，而不是 benchmark / challenge / qualitative analysis / LLM capability demo？
3. 它的**輸入物件**是不是 pre-existing natural-language process text？
4. 它的**方向性**是不是 text -> process representation，而不是 process-model authoring support、reverse generation、或其他 BPM 任務？

換句話說，`2409` 現在的問題應該被升級描述為：

> **一個 target-object 為核心，但被 primary-objective、paper-type、source-direction 邊界共同放大的 criteria boundary 問題。**

#### 2.2.2 再改一輪 criteria 很值得做，但不應預設一定收工

`criteria_2409_stage_split_report` 自己就已經提醒兩件事：

1. 這一輪 improvement 是真的
2. 但 pipeline 並不真正 hard-consume `stage_projection`
3. 剩餘 hard FP 裡有一部分帶有 dual interpretability / gold tension

因此，下一輪 criteria surgery 當然值得做，但成功標準要設得非常具體；若同一族 hard FP 仍存活，就應該停止「微調 wording」，轉向 hard-FP audit memo，而不是重回 senior tuning。

---

## 3. 目前證據總表

| 證據來源 | 已驗證結論 | 對下一步的含義 |
|---|---|---|
| `docs/chatgpt_current_status_handoff.md` | 系統層主方向已收斂；Stage 1 原則固定；`2409` 是主戰場；`2511` 可先停大改；`2307` / `2601` 不宜亂動 | 下一輪應聚焦 `2409` criteria，不碰 global policy |
| `docs/nlp_prisma_screening_diagnosis_report.md` | 最大 bottleneck 是 review-specific criteria observability 與 global SeniorLead non-portability | 不要再押注全域 senior tuning |
| `docs/frozen_senior_replay_report.md` | strict senior effect 為真，但對不同 review 方向相反 | Senior 只能當固定背景，不是本輪變因 |
| `docs/criteria_2511_operationalization_v2_report.md` | `2511` 只靠 criteria operationalization 就顯著變好 | `2409` 應仿照 `2511` 的 decision-table 化 |
| `docs/criteria_2409_stage_split_report.md` | `2409` criteria stage split 已提升 precision 並保住 recall，但還有殘餘 hard FP | 下一輪要把殘差拆成更硬的 semantic boundary |
| `criteria_jsons/2511.13936.json` | 成功範式是 ALL-gates + negative overrides | `2409` 也應改成 gate-based criteria |
| `criteria_jsons/2409.13738.json` | 目前仍用 core-task + method-role + maybe 的 recall-first wording | 現有 wording 太容易讓 topic-adjacent / paper-type-adjacent paper 留下 |
| `runtime_prompts.json` | strict senior prompt 仍是一個既有配置 | 下一輪應固定它，不可同時再調 senior |
| `topic_pipeline.py` + stage-split report caveat | `stage_projection` 不是可靠的唯一承載點；真正該吃到 reviewer 的 hard logic 必須落在主要 criteria 欄位 | 新規則不能只寫在 `stage_projection`，要直接落在 `topic_definition`、`inclusion_criteria.required`、`exclusion_criteria` |

**表 1 說明**  
表 1 的重點不是單純列文件，而是要說明「為什麼下一輪只能是 `2409` criteria surgery」。因為九個指定檔案合起來，已把可動變因縮小到很窄：只能動 `2409` criteria，而且應該像 `2511` 一樣做 gate 化，而不是再做 senior/pipeline/global prompt 的再設計。

---

## 4. 四篇 review 的現況與策略定位

| Review | 現行穩定版本 | Combined Precision | Combined Recall | Combined F1 | 策略定位 |
|---|---|---:|---:|---:|---|
| `2307.05527` | `senior_no_marker` | 0.9816 | 0.9357 | 0.9581 | 高分穩定，不是主戰場 |
| `2409.13738` | `criteria_2409_stage_split` | 0.6364 | 1.0000 | 0.7778 | 目前最大 bottleneck |
| `2511.13936` | `criteria_2511_opv2` | 0.8788 | 0.9667 | 0.9206 | 主問題大致已解 |
| `2601.19926` | `senior_no_marker` | 0.9676 | 0.9791 | 0.9733 | 很強且容易被 strict senior 修壞 |

**表 2 說明**  
表 2 告訴我們一件很簡單但很重要的事：如果現在要把實驗資源投在一個地方，唯一合理的主目標就是 `2409`。`2511` 已經跨過「大問題是否解掉」的門檻；`2307` 與 `2601` 則屬於高分穩態，任何全域調整都比較像是在冒不必要風險。

---



## 4A. 為什麼不應再追 global `SeniorLead`：frozen replay 的數值意義

| Review | frozen replay 對比 | Precision 變化 | Recall 變化 | 解讀 |
|---|---|---:|---:|---|
| `2409` | `senior_no_marker` -> `senior_prompt_tuned` | 0.4468 -> 0.6563 | 1.0000 -> 1.0000 | strict senior 對 `2409` 確實有幫助 |
| `2511` | `senior_no_marker` -> `senior_prompt_tuned` | 0.5577 -> 0.7500 | 0.9667 -> 0.9000 | 有幫助，但伴隨 recall 代價 |
| `2601` | `senior_no_marker` -> `senior_prompt_tuned` | 0.9623 -> 0.9778 | 0.9910 -> 0.7881 | precision 小升，但 recall 明顯受傷 |

**表 2A 說明**  
這張表說明了為什麼 `SeniorLead` 不能再作為全域主戰場。它不是「沒用」，而是「方向不一致」：  
對 `2409` 有利，對 `2601` 有害。也因此，下一輪若想讓實驗結論乾淨，最好的做法就是把 senior 視為固定背景，而不是再把它拉進變因集合。


## 5. 為什麼 `2409` 改完 stage split 仍有 hard FP

### 5.1 這一輪已經修掉了什麼

`criteria_2409_stage_split` 的主要貢獻有兩個：

1. 把 Stage 1 observable 與 Stage 2 confirmatory 的語言分開
2. 讓 generic NLP / 非核心 task / 沾邊 paper 比較不容易光靠 topic similarity 被留下

而且這一輪有一個很重要的實驗訊號：

1. precision 上升
2. recall 沒掉

所以不能說這輪只是 wording cosmetic change。它是真的抓到一部分 problem source。

### 5.2 為什麼還不夠

問題在於，現在的 `2409` wording 仍然以這種邏輯為中心：

1. 看有沒有 text-to-process 的 core task
2. 看 NLP/text processing 是不是 central
3. 如果 abstract 細節不夠，但 core task + method-role 看起來像，就保留 maybe

這種設計仍然會放進三種東西：

1. **paper-level objective 不對，但 task-level 看起來像**  
2. **研究類型不對，但摘要裡充滿 extraction / process / benchmark / BPM 詞彙**  
3. **輸入與輸出方向不夠明確，但 topic adjacency 很強**

也就是說，現有設計還是太依賴 reviewer 去自行判斷 paper-level intent。  
而 `2409` 剛好是最容易被這種模糊 intent 影響的一篇。

---

## 6. `2409` 殘餘 hard FP 的更細語義拆解

我認為 `2409` 剩餘的 hard FP 至少有六類。這六類不是互斥，而是會彼此重疊。

### 6.1 類型 A：target-object boundary 還不夠硬

這是 handoff 已點出的核心問題。  
目前 criteria 雖然提到「structured process representation/model」，但仍然不夠硬，原因是它還沒有把下面這件事寫成 reviewer 很難誤判的硬規則：

> **primary output 必須是 review 要的最終 process / decision-flow representation，而不是只抽出中間構件、元素、relation、fragment、constraint 或一般性 formalization。**

若沒有這一刀，paper 只要有：

1. process elements
2. process relations
3. formal semantics
4. partial mapping
5. declarative fragments

就容易被誤當成最終 target-object 已達成。

### 6.2 類型 B：primary-objective boundary 沒有寫硬

這一類是我認為 handoff 低估的一塊。  
有些 paper 的 abstract 看起來確實碰到 text -> process model，但那不等於**這篇 paper 的核心研究目標**就是 text-to-process extraction。

這正是 `grohs2023large` 類 paper 的問題：  
它的 paper-level framing 是「LLM 可以做多種 BPM task」，textual process model mining 只是其中一個示範 task。  
若 criteria 只看 task-level fit，就會把它收進來；但若 review 的 gold boundary 是「paper 的 primary contribution 應是 text-to-process extraction method」，那它就應該排除。

### 6.3 類型 C：contribution-type / paper-type boundary 沒有寫硬

這一類可以解釋：

1. `bellan2020qualitative`
2. `bellan2021process`
3. `lopez2021challenges`

它們都高度相關，甚至直接圍繞 process extraction from text。  
但問題是它們的主要貢獻型態比較像：

1. qualitative analysis
2. benchmarking
3. evaluation pipeline / future challenge
4. challenge agenda / resources / research roadmap

而不是**提出並驗證一個新的 text-to-process extraction method**。

如果 Stage 1 沒把這一類 meta / benchmark / challenge paper 擋掉，那 reviewer 只要看到 topic relevance 很高，就很容易放行。

### 6.4 類型 D：source-object / input-direction boundary 還不夠明確

目前 wording 雖然提到「from natural language text」，但沒有把「來源必須是 pre-existing textual process descriptions/documents/narratives」寫成非常硬的 input gate。

這會產生兩種風險：

1. 只要 paper 說 starting from textual descriptions，就可能被納入，即使它其實更像 authoring / modeling assistance system
2. reviewer 沒有被明確提醒「structured records、event logs、existing models、forms、database records」不算這個 review 要的 source object

換句話說，現在 criteria 有在說「text」，但還沒把 **source object** 與 **directionality** 鎖到 reviewer 很難走偏。

### 6.5 類型 E：intermediate-artifact 與 final-model 的邊界沒有寫成 hard negative

process extraction 這個題目天然會出現一堆中間層任務，例如：

1. activity extraction
2. actor / role extraction
3. gateway / relation extraction
4. event / constraint detection
5. process fragment recognition

如果 criteria 沒明寫：

> **只有中間產物，不等於最終納入**

那 reviewer 很容易把「對 process model construction 有幫助」誤判成「已完成 process representation extraction」。

### 6.6 類型 F：LLM-based modeling assistance 與 true extraction pipeline 的邊界沒有寫硬

這一類對 `kourani_process_modelling_with_llm` 最明顯。  
它的 abstract 裡面會出現非常危險的一組詞：

1. automated generation
2. iterative refinement
3. process models
4. starting from textual descriptions
5. BPMN / Petri nets

若現有 gate 是：

1. 有 text
2. 有 process model
3. 有 automation
4. 有 NLP / LLM

那它幾乎必進。  
但問題是它的 framing 更像：

1. process modeling assistance
2. LLM-driven authoring / refinement framework
3. generative BPM support

而不是典型的 systematic review target：  
**用 NLP method 從 text 中抽取並構建 process representation 的 extraction study。**

---

## 7. 具體到 paper family 的 hard FP 診斷

| sentinel case | 為何會被現在的 criteria 吸進來 | 真正應該擋它的邊界 |
|---|---|---|
| `kourani_process_modelling_with_llm` | abstract 同時出現 textual descriptions、automated generation、process models、BPMN、LLM | 應由「modeling assistance / iterative refinement 不等於 extraction paper」擋下 |
| `grohs2023large` | 包含從 textual descriptions mining process models，task-level 很像 in-scope | 應由「multi-task BPM capability paper；text-to-process 不是 primary contribution」擋下 |
| `bellan2020qualitative` | topic 完全對準 process extraction from text，且摘要會提 state-of-the-art tools 與限制 | 應由「qualitative analysis / state-of-the-art analysis 不等於 primary extraction method paper」擋下 |
| `bellan2021process` | abstract 中直接談 process extraction from text、benchmarking、evaluation pipeline、future challenges | 應由「benchmarking / evaluation pipeline / future challenge paper 不等於 target method paper」擋下 |
| `lopez2021challenges` | process discovery from text / legal domain 高度相關，容易被 topic relevance 帶進來 | 應由「challenge / agenda / roadmap paper 不等於 extraction method」擋下 |

**表 3 說明**  
表 3 的價值在於：它把殘餘 FP 從「一堆個案」整理成「幾個可操作的 paper family」。這樣下一輪 criteria 不是在針對個別 paper 打補丁，而是在補**會讓這些 paper family 同時被擋住的邏輯閘門**。

---

## 8. 現行 `2409` wording 到底哪裡還太鬆

### 8.1 問題句 1：`extraction or generation of a structured process representation/model`

這句話有兩個問題：

1. `generation` 太寬
2. 沒有限定 **paper 的 primary objective**

所以像 `kourani` 這種「LLM 協助生成與迭代修 process model」的 paper，會天然撞上這句。

### 8.2 問題句 2：`if core task + method-role evidence exists ... keep as maybe`

這會讓 reviewer 在 paper-level objective 尚不清楚時，傾向保留 topic-adjacent case。  
對 recall-first 來說這很合理；但 `2409` 的 FP 問題恰恰就是「topic-adjacent 太容易被當成 core fit」。

因此 `maybe` 的適用範圍必須被砍窄：

> **不是只要 core task 看起來像就 maybe，而是 source-text、target-object、primary-objective、method-role 四個 observable gate 都已經成立時，才可以因 full-text 細節不足而 maybe。**

### 8.3 問題句 3：`Generic NLP/LLM ... with no explicit text-to-process extraction task`

這句太弱，因為它只排除「完全沒有 explicit text-to-process extraction task」的 paper。  
但 `grohs2023large` 類 paper 的問題不是沒有 extraction task，而是：

1. 有 extraction task
2. 但那不是 paper 的 primary contribution
3. paper 本質是 broader BPM/LLM capability demonstration

所以這句要升級成 paper-level objective gate。

### 8.4 問題句 4：`stage_projection.negative_overrides`

這些 negative overrides 的方向其實是對的，但 stage-split report 已提醒：

1. 這不是 pipeline-level 真 stage split
2. pipeline 目前並不真正 hard-consume `stage_projection`

因此下一輪不能把關鍵新規則只放在 `stage_projection`。  
**必須直接寫進 `topic_definition`、`inclusion_criteria.required`、`exclusion_criteria`。**

---

## 9. 我建議的 `2409` criteria 重寫原則

下一輪如果只改 criteria，我會遵守五個原則。

### 9.1 原則一：仿照 `2511`，改成 ALL-gates decision table

`2511` 成功的關鍵，不是單純把文案變嚴，而是把 title/abstract 可觀測的 inclusion 條件改成：

1. audio-domain gate
2. preference-signal gate
3. learning-role gate
4. negative overrides

也就是只有當必要 gate 都過，才保留。  
`2409` 應採同樣策略。

### 9.2 原則二：`maybe` 只能保留 full-text 細節不明，不可保留 core semantic ambiguity

我主張把 `maybe` 用法縮到只剩一種：

> **source-text、target-object、primary-objective、method-role 四個 gate 都明確成立，但 abstract 對 full-paper type、方法完整度、或 empirical validation 曝露不足。**

若缺的是前三者任一個，就不應該 maybe，而應該 exclude。

### 9.3 原則三：把 task-level fit 升級成 paper-level fit

下一輪 criteria 不應只問：

1. 有沒有 text -> process task

還必須問：

1. 這篇 paper 的 primary contribution 是不是 text-to-process extraction method / system？

若只是：

1. task showcase
2. one example among several BPM tasks
3. modeling support framework
4. benchmark / challenge / qualitative analysis

就應該排除。

### 9.4 原則四：把 source object 與 target object 同時寫硬

不是只有 target object 要明確，source object 也要明確。  
這樣可以同時擋掉：

1. source 不明的 topic-adjacent case
2. structured input / reverse-direction case
3. authoring-support case

### 9.5 原則五：關鍵 hard negatives 必須落在主要 criteria 欄位

因為 `stage_projection` 不是可靠的唯一入口，所以真正會影響 reviewer 決策的關鍵規則，必須直接放在：

1. `topic_definition`
2. `inclusion_criteria.required`
3. `exclusion_criteria`

---

## 10. 建議直接採用的 `criteria_2409_boundary_v3` wording

以下內容是我建議可直接貼進 JSON 的修正版方向。  
這不是唯一寫法，但它的設計目標非常明確：**只修 `2409` hard FP，不去碰 system-level 其他穩定件。**

### 10.1 建議重寫的 `topic_definition`

```text
Stage 1 retains only papers whose primary research objective is automatic conversion from pre-existing natural-language process descriptions, documents, narratives, procedures, or requirements into an explicit structured process or decision-flow representation/model. Title+abstract retention requires positive observable evidence for ALL of the following: (A) a textual source object, (B) a process/decision-model target object, (C) text-to-model conversion as the paper's central task/contribution, and (D) NLP/text processing/LLM used to infer process structure from text. Topic relevance to BPM, process modeling, process mining, formalization, or LLMs is not sufficient. If any of (A)-(C) is missing or ambiguous in title/abstract, exclude rather than maybe. 'Maybe' is reserved only for cases where (A)-(D) are explicit but full-paper type, implementation completeness, or empirical validation cannot yet be confirmed until Stage 2. Stage 2 confirms article type, English/full-text availability, primary-research status, concrete method completeness, and empirical validation.
```

### 10.2 建議重寫的 Stage 1 required gates

```text
1. Source-text gate (required): the primary input must be pre-existing natural-language process descriptions/documents/narratives/procedures/requirements; not event logs, structured records, existing process models, forms, or databases.

2. Target-object gate (required): the primary output must be an explicit structured process or decision-flow representation/model, such as BPMN, DMN, declarative model, process graph, workflow net, Petri-net-like representation, or another comparable process representation. Intermediate artifacts alone do not satisfy this gate.

3. Primary-objective gate (required): the paper's main research task/contribution must be automatic derivation, extraction, mapping, or construction of the process/decision representation from text; it is not enough that text-to-process appears only as one subtask, one showcased capability, or one downstream use.

4. Method-role gate (required): NLP, parsing, information extraction, semantic analysis, sequence labeling, relation extraction, machine learning, deep learning, or LLM prompting/inference must be used to infer process structure from text, not merely as peripheral support for a broader BPM or modeling workflow.

5. Uncertainty handling (required): assign maybe only when Source-text + Target-object + Primary-objective + Method-role are all explicit in title/abstract but full-paper type, implementation completeness, or empirical validation remains unobservable before Stage 2.
```

### 10.3 建議新增或重寫的 Stage 1 strong negatives

```text
1. Negative override: papers about BPM, process modeling, process mining, formalization, or LLM support are out-of-scope unless the primary research contribution is explicit text-to-process/decision-model conversion from natural-language text.

2. Negative override: modeling assistance, interactive authoring, iterative refinement, or prompt-based generation frameworks are excluded when they facilitate human process modeling rather than evaluate a text-to-process extraction method as the paper's core contribution.

3. Negative override: multi-task BPM or general LLM capability papers are excluded when text-to-process extraction is only one showcased task/example and not the paper's central extraction contribution.

4. Negative override: qualitative analyses, benchmarking papers, evaluation pipelines, challenge papers, agenda papers, and state-of-the-art reviews about process extraction are excluded unless they themselves introduce and evaluate a novel extraction method as the primary contribution.

5. Negative override: extracting only activities, roles, entities, relations, constraints, process fragments, or other intermediate artifacts does not satisfy inclusion unless the paper explicitly constructs a final process/decision representation/model as the primary output.

6. Negative override: papers whose primary input is event logs, transactional records, structured tables, existing process models, or other non-textual/structured artifacts are out-of-scope.

7. Negative override: reverse or non-target directions are excluded, including process-model-to-text generation, process redesign, compliance monitoring, prediction, matching, recommendation, simulation, and general BPM decision support without text-to-model extraction as the core task.

8. Negative override: if title/abstract does not make both the textual source object and the process/decision-model target object explicit, topical similarity alone is insufficient; exclude rather than maybe.
```

### 10.4 建議補強的 Stage 2 confirmatory gate

```text
Stage 2 confirmatory gate: the primary contribution must be a concrete extraction method/system, not merely a benchmark, challenge statement, qualitative analysis, resource paper, or broader BPM/LLM discussion.
```

---

## 11. 我會如何重寫 negative overrides

這一節專門回答兩個目標：

1. 如何更能擋住 generic BPM / process / LLM papers
2. 如何更能擋住 process-adjacent but not text-to-process extraction papers

### 11.1 用來擋 generic BPM / process / LLM papers 的版本

建議直接採用下列 wording：

```text
Negative override: topic relevance to BPM, process modeling, process mining, formalization, workflow support, or LLM-based BPM assistance is insufficient unless the paper's primary research contribution is explicit automatic conversion from natural-language process text to a structured process/decision representation.

Negative override: multi-task BPM capability papers, general LLM-for-BPM papers, and prompt-based process modeling support papers are excluded when text-to-process extraction appears only as one demonstrated use case rather than the paper's central method contribution.

Negative override: iterative refinement or authoring-support systems are excluded when the contribution centers on helping users create or improve process models, rather than evaluating a dedicated extraction pipeline from pre-existing text.
```

### 11.2 用來擋 process-adjacent but not text-to-process extraction papers 的版本

建議直接採用下列 wording：

```text
Negative override: process-adjacent papers are out-of-scope when they extract only intermediate artifacts (activities, entities, relations, constraints, rules, process fragments) without explicitly constructing a final process/decision representation/model as the primary output.

Negative override: qualitative analyses, surveys, state-of-the-art reviews, benchmark papers, challenge papers, and evaluation-pipeline papers about process extraction are out-of-scope unless they introduce and validate a novel extraction method as the paper's main contribution.

Negative override: papers are excluded when title/abstract does not explicitly state both (a) a natural-language textual source object and (b) a process/decision-model target object; process-related terminology alone is not enough for retention.
```

### 11.3 為什麼這樣寫比現在更有效

因為它們做了目前 criteria 尚未做好的三件事：

1. 把 **topic relevance** 與 **paper-level primary contribution** 切開
2. 把 **中間產物** 與 **最終 target object** 切開
3. 把 **meta / benchmark / challenge 類 paper** 在 Stage 1 就提前擋掉

---

## 12. 新版 `2409` 為何有機會同時擋掉 hard FP 又保住 recall

### 12.1 它不是單純變嚴，而是變得更有結構

若只是把現有 criteria 寫得更 strict，風險是：

1. generic FP 下降
2. 但真正摘要較弱的 gold paper 也一起被砍掉

我提出的版本不是單純變嚴，而是把判斷拆成：

1. source-text gate
2. target-object gate
3. primary-objective gate
4. method-role gate
5. maybe 的窄化規則

這種設計比較像 `2511` 的成功模式：  
不是靠「更保守的 reviewer 心態」，而是靠「更可操作的 observable gate」。

### 12.2 它刻意保護了已修回來的 gold=true family

`criteria_2409_stage_split_report` 已指出以下 case 目前是重要的正向 sentinel：

1. `etikala2021extracting`
2. `honkisz2018concept`
3. `goncalves2011let`

因此下一輪 wording 不能把 target-object 寫得太窄，只允許 BPMN。  
這也是我為什麼建議 target-object gate 要明寫：

1. BPMN
2. DMN
3. declarative process model
4. process graph
5. workflow net / Petri-net-like representation
6. comparable structured process / decision representation

這樣才不會因為 target-object wording 過窄，誤傷 decision-model 或 declarative-model 類 gold paper。

### 12.3 它把 `maybe` 從 topic-adjacent 保留器，改回 full-text defer 機制

目前 `2409` 的問題之一，就是 `maybe` 太容易被 topic-adjacent case 吃到。  
我建議把 `maybe` 縮窄成：

1. A/B/C/D 四個 gate 都明確成立
2. 只是 implementation completeness / empirical validation / article type 尚未完全可觀測

這樣 `maybe` 就不再是「看起來可能有關」的保留器，而會變成真正的 Stage 1 -> Stage 2 defer 機制。

---

## 13. 建議的單輪實驗設計

### 13.1 實驗名稱

**`criteria_2409_boundary_v3`**

### 13.2 這一輪只應改什麼

只改：

1. `criteria_jsons/2409.13738.json`
2. 其中：
   1. `topic_definition`
   2. `inclusion_criteria.required`
   3. `exclusion_criteria`
   4. `stage_projection` 可以同步鏡像更新，但只能當 reviewer scaffold，不可視為唯一承載點

### 13.3 這一輪不應改什麼

不要改：

1. `scripts/screening/runtime_prompts/runtime_prompts.json`
2. `SeniorLead` wording
3. Stage 1 aggregation
4. pipeline code
5. marker heuristic
6. `2511.13936.json`
7. `2307` / `2601` 的現行穩定設定

### 13.4 成功標準

我建議把成功標準明確寫成：

1. `2409` combined precision `>= 0.70`
2. `2409` combined recall 維持 `1.0000`
3. combined FP `<= 9`
4. 下列 hard FP family 應至少大幅改善：  
   1. `kourani_process_modelling_with_llm`  
   2. `grohs2023large`  
   3. `bellan2020qualitative`  
   4. `bellan2021process`  
   5. `lopez2021challenges`
5. 下列 gold=true sentinel 不得掉出來：  
   1. `etikala2021extracting`  
   2. `honkisz2018concept`  
   3. `goncalves2011let`

### 13.5 失敗後的解讀方式

若這一輪做完後：

1. same-family hard FP 仍大量存活，或
2. precision 提升很小，但 gold cases 開始掉

那我會建議：

1. **停止再做 `2409` 微調 wording**
2. 改做一份 **hard-FP audit memo**
3. 明確標記哪些殘差屬於：
   1. gold boundary tension
   2. title/abstract observability limit
   3. review policy 本身未完全顯式化

而不是回頭去追 global senior tuning。

---

## 14. `2511`、`2307`、`2601` 的建議處置

### 14.1 `2511`：可以先停止大改

我的判斷是：  
**可以，現在就先停大改。**

理由：

1. 只改 criteria 就同時提升 precision 與 recall
2. combined F1 已到 `0.9206`
3. 報告已把剩餘問題界定為少數高爭議 boundary case
4. 它已經不再像是廣泛 criteria 模糊

除非你現在的研究目標是專門追最後那個殘餘 FN，否則它不應該佔用主要實驗資源。

### 14.2 `2307`：維持現狀

`2307` 現在不是瓶頸，且已經非常高分。  
若再引入全域策略調整，風險大於潛在收益。

### 14.3 `2601`：更應維持現狀

`2601` 是最不應該被全域策略波及的一篇。  
frozen replay 已經說得很清楚：strict senior 對它的 recall 傷害是真實的。  
因此後續若有任何 senior prompt 改動，都必須先過 frozen replay guardrail；但就目前階段而言，最好的策略仍是：**不要動它。**

---

## 15. 最後結論

### 15.1 我同意的總結

我同意目前的大方向：

1. 系統層大方向已收斂
2. 不應再追 global senior
3. `2511` 已大致修好
4. `2307` / `2601` 應維持現狀
5. `2409` 是主戰場

### 15.2 我補充後的更精確診斷

但我會把 `2409` 的剩餘問題更精確地改寫成：

> **`2409` 現在剩下的不是單一 target-object boundary，而是以 target-object 為核心、再疊加 primary-objective、paper-type、source-direction 三層邊界不足的 criteria boundary 問題。**

### 15.3 明確的 next-step proposal

我建議的 next step 只有一個：

> **開一輪 `criteria_2409_boundary_v3`，只改 `criteria_jsons/2409.13738.json`，把 `2409` 改成像 `2511` 那樣的 ALL-gates decision table，並明確加入 paper-level primary contribution negatives、meta/benchmark/challenge negatives、source-text gate、target-object gate、以及更窄的 maybe 規則。**

如果這一輪達標，就可以把 `2409` 也拉進「基本收斂」狀態。  
如果這一輪後同一批 sentinel hard FP 仍然存活，就不要再回頭追 global senior，也不要再無止境磨 wording；那時候最正確的做法會是把殘差升格為 **review policy / gold tension / observability** 問題來單獨處理。

---

## 附錄 A：建議直接複製使用的 `2409` negative overrides

```text
Negative override: topic relevance to BPM, process modeling, process mining, formalization, workflow support, or LLM-based BPM assistance is insufficient unless the paper's primary research contribution is explicit automatic conversion from natural-language process text to a structured process/decision representation.

Negative override: modeling assistance, interactive authoring, iterative refinement, or prompt-based generation frameworks are excluded when they facilitate human process modeling rather than evaluate a text-to-process extraction method as the paper's core contribution.

Negative override: multi-task BPM capability papers, general LLM-for-BPM papers, and prompt-based process modeling support papers are excluded when text-to-process extraction appears only as one demonstrated use case rather than the paper's central method contribution.

Negative override: qualitative analyses, benchmarking papers, evaluation pipelines, challenge papers, agenda papers, and state-of-the-art reviews about process extraction are excluded unless they themselves introduce and evaluate a novel extraction method as the primary contribution.

Negative override: extracting only activities, roles, entities, relations, constraints, process fragments, or other intermediate artifacts does not satisfy inclusion unless the paper explicitly constructs a final process/decision representation/model as the primary output.

Negative override: papers whose primary input is event logs, transactional records, structured tables, existing process models, or other non-textual/structured artifacts are out-of-scope.

Negative override: reverse or non-target directions are excluded, including process-model-to-text generation, process redesign, compliance monitoring, prediction, matching, recommendation, simulation, and general BPM decision support without text-to-model extraction as the core task.

Negative override: if title/abstract does not make both the textual source object and the process/decision-model target object explicit, topical similarity alone is insufficient; exclude rather than maybe.
```

## 附錄 B：這份報告實際依據到的關鍵結論摘要

### B.1 handoff
1. Stage 1 流程原則已固定
2. `SeniorLead` 必須保留
3. marker heuristic 已刪除
4. 不值得再追 global senior prompt
5. `2409` 是目前主戰場
6. `2511` 已大致修好
7. `2307` / `2601` 不宜亂動

### B.2 diagnosis
1. 真正 bottleneck 是 review-specific criteria observability
2. global SeniorLead non-portability 已被證實
3. 最佳 combined 版本已經分裂成不同 review 最適設定

### B.3 frozen replay
1. senior prompt effect 為真
2. `2409` / `2511` 可受 strict senior 幫助
3. `2601` 會被 strict senior 傷 recall

### B.4 `2511` criteria opv2
1. 只改 criteria 即可同時提升 precision 與 recall
2. 成功關鍵是 ALL-gates + negative overrides

### B.5 `2409` stage split
1. precision 已改善
2. recall 無損
3. 仍有 hard FP
4. stage_projection 不是唯一可靠承載點
5. 剩餘問題更像 semantic boundary，而非 senior calibration
