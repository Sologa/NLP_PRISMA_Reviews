# QA-first experiment v0 修正版診斷報告（整合本地 Codex 意見）

## 0. 報告定位

這份報告是對上一版 ChatGPT 分析的修正版。  
目標是：保留原先高層方向中正確的部分，修掉被 Codex 指出的 case-level 錯誤，並把「已驗證事實」與「合理推論」切開。

這份報告**不**重寫 formal criteria。  
這份報告聚焦的是：

- QA coverage
- synthesis compression / distortion
- evaluator behavior
- SeniorLead routing
- Stage 1 vs Stage 2 handoff
- paper-specific failure modes

## 1. Evidence base

這次綜合的證據來源包括：

- current-state:
  - `AGENTS.md`
  - `docs/chatgpt_current_status_handoff.md`
  - `scripts/screening/runtime_prompts/runtime_prompts.json`
  - `criteria_stage1/2409.13738.json`
  - `criteria_stage2/2409.13738.json`
  - `criteria_stage1/2511.13936.json`
  - `criteria_stage2/2511.13936.json`
- experiment framing:
  - `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/EXPERIMENT_FRAMING.md`
  - `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/patches/seed_qa_patch_notes.yaml`
- result authority:
  - `screening/results/qa_first_v0_2409_2511_2026-03-18/run_manifest.json`
  - `screening/results/2409.13738_full/latte_review_results.json`
  - `screening/results/2409.13738_full/latte_fulltext_review_results.json`
  - `screening/results/2511.13936_full/latte_review_results.json`
  - `screening/results/2511.13936_full/latte_fulltext_review_results.json`
  - 4 個 experiment arm 的 stage1/fulltext raw JSON
- 本地 Codex feedback:
  - 你提供的回饋文字
  - 其中包含 local gold 驗證過的 case-level 糾正

## 2. Confidence notation

- **[M]** = metrics / raw results 直接支持
- **[C]** = 來自本地 Codex 的 local-gold 或 local-repo 驗證
- **[I]** = 合理推論，但此環境沒有重新做 gold join，不當作已驗證事實

## 3. 先講總結

### 3.1 可以保留的高層結論

1. **`2409.13738` 的 gain 主要來自 Stage 2，不是 Stage 1 變聰明。** [M]  
2. **`2511.13936` 的 regression 主要來自 Stage 1 recall collapse，不是 FP 爆炸。** [M]  
3. **`2511 qa+synthesis` 確實有 candidate-level contamination，而且規模不能忽略。** [M][C]  
4. **這輪要修的是 workflow layer，不是 formal criteria layer。** [M]

### 3.2 必須修掉的上一版說法

1. **`honkisz2018concept` 不能再被拿來當 precision gain 代表。** [C]  
   本地 Codex 已指出：它是正例，而且在 `2409 qa+synthesis stage2 raw` 裡最終也是 `include (junior:5,5)`。  
   換句話說，上一版把它寫成「被 target-object boundary 排掉」是錯的。

2. **`elallaoui2018automatic` 才是 `2409 qa+synthesis` 裡較乾淨的 target-object boundary 代表 case。** [M][C]  
   在 `2409 qa+synthesis stage2 raw`，它被 `SeniorLead` 排掉，理由是 user stories -> UML use case diagrams 不等於 review 所要求的 process models。

3. **`goossens2023extracting`` 應降級成 hygiene warning，不應當成主要結果證據。** [M][C]  
   這筆最終仍是 include；問題在於 handoff metadata 混入了 `stage1 / qa-only` 的髒欄位。

4. **`2511` 的 contamination 需要量化，不應只寫成抽象警告。** [M][C]  
   我這邊用 raw JSON 做字串檢索，抓到：
   - Stage 1 可疑污染：**10** 筆
   - Fulltext 可疑污染：**1** 筆  
   Codex 的本地檢查口徑是至少 **9 + 1**。  
   因此最穩妥的寫法是：**`>=9` 筆 Stage 1 可疑污染，另有 `1` 筆 fulltext 污染。**

## 4. Metric sanity check

### 4.1 `2409.13738`

| Arm          |   Stage1 F1 |   Combined F1 |   Stage1 Precision |   Stage1 Recall |   Combined Precision |   Combined Recall |   Stage2 selected |
|:-------------|------------:|--------------:|-------------------:|----------------:|---------------------:|------------------:|------------------:|
| baseline     |      0.7500 |        0.7843 |             0.6000 |          1.0000 |               0.6667 |            0.9524 |                35 |
| qa-only      |      0.7368 |        0.8085 |             0.5833 |          1.0000 |               0.7308 |            0.9048 |                36 |
| qa+synthesis |      0.7119 |        0.8333 |             0.5526 |          1.0000 |               0.7407 |            0.9524 |                38 |

解讀：  
- Stage 1 F1 其實下降：`0.7500 -> 0.7368 -> 0.7119` [M]
- Combined F1 卻上升：`0.7843 -> 0.8085 -> 0.8333` [M]
- 所以 `2409` 的 gain 幾乎不可能解釋成「Stage 1 判得更準」，而是 **Stage 2 closure 變好**。 [M]

### 4.2 `2511.13936`

| Arm          |   Stage1 F1 |   Combined F1 |   Stage1 Precision |   Stage1 Recall |   Combined Precision |   Combined Recall |   Stage2 selected |
|:-------------|------------:|--------------:|-------------------:|----------------:|---------------------:|------------------:|------------------:|
| baseline     |      0.8657 |        0.8814 |             0.7838 |          0.9667 |               0.8966 |            0.8667 |                37 |
| qa-only      |      0.8519 |        0.8302 |             0.9583 |          0.7667 |               0.9565 |            0.7333 |                24 |
| qa+synthesis |      0.8727 |        0.8519 |             0.9600 |          0.8000 |               0.9583 |            0.7667 |                25 |

解讀：  
- `2511` 兩個 arm 的 precision 都很高，但 recall 明顯崩掉。 [M]
- baseline Stage 1 recall `0.9667`，`qa-only` 掉到 `0.7667`，`qa+synthesis` 也只有 `0.8000`。 [M]
- baseline Stage 2 selected `37`，`qa-only` 剩 `24`，`qa+synthesis` 也只有 `25`。 [M]
- 這是**過早排掉 TP**，不是 FP 太多。 [M]

## 5. Updated diagnosis for `2409.13738`

### 5.1 現在能確定的主結論

`2409` 的改善點仍然是：**Stage 2 對 evidence 的 closure 比 baseline 更好。** [M]

更精確地說，`qa+synthesis` 看起來在某些 case 上，能把長篇 QA 壓成比較穩定的 canonical field judgment，讓 `SeniorLead` 更容易做 object-boundary 或 confirmatory closure。 [M][I]

但這裡一定要加一個修正：  
上一版把 `honkisz2018concept` 當作代表，是錯的。 [C]

### 5.2 代表 case 要改成 `elallaoui2018automatic`

`elallaoui2018automatic` 的 verdict 變化如下： [M]

- baseline Stage 2: `include (junior:5,5)`
- `qa-only` Stage 2: `include (junior:5,5)`
- `qa+synthesis` Stage 2: `exclude (senior:1)`

`qa+synthesis` 的 senior 理由是：

> The Stage 2 full-text evidence clarifies that the paper's NLP application transforms user stories into UML use case diagrams, which are not process models such as control-flow or declarative models as required by the inclusion criteria. Although the paper is a peer-reviewed primary research article with a concrete method and empirical validation, it does not meet the core thematic criterion of NLP for process extrac...

這個 case 應該怎麼用？  
最保守、最不會說過頭的寫法是：

- 它是 **target-object boundary 真正 firing 的代表 case**。 [M][C]
- 它顯示 `qa+synthesis` 的 Stage 2 確實在做 canonicalization，不只是把 QA 壓短。 [M]
- 但「它是否就是 precision gain 的那 3 個 FP-correction 之一」，若沒有重新 join local gold，就不要寫成已驗證事實。 [I]

### 5.3 `honkisz2018concept` 的正確用法

`honkisz2018concept` 的變化如下： [M][C]

- baseline Stage 2: `include (junior:5,5)`
- `qa-only` Stage 2: `exclude (senior:2)`
- `qa+synthesis` Stage 2: `include (junior:5,5)`

`qa-only` 當時排掉它的 senior 理由是：

> The paper meets most inclusion criteria, being a full peer-reviewed research article with original methodology focused on NLP-enabled process extraction. However, it lacks necessary empirical validation in the form of experiments, quantitative evaluation, or comparative analysis, which is an essential Stage 2 inclusion criterion. The descriptive case study provided is insufficient to satisfy the empirical validation...

Codex 已經用本地 gold 指出：  
**`honkisz2018concept` 是正例。** [C]

所以它應該被拿來說明的是：

- `qa+synthesis` **不只是會變嚴格**，它也會把 `qa-only` 錯失的正例拉回來。 [M][C]
- 換句話說，`2409 qa+synthesis > qa-only` 的原因，不是單純「更保守」，而是**closure 重分配**。 [M]

### 5.4 `goossens2023extracting` 應降級成 hygiene warning

這筆在 `qa+synthesis` fulltext raw 裡，確實能看到髒 metadata： [M]

```json
"stage": "stage1",
      "workflow_arm": "qa-only"
```

但它最終 verdict 仍是 `include (junior:5,5)`。 [M]

因此對這筆最正確的寫法是：

- 它證明 **handoff hygiene 有 bug**。 [M]
- 但它不適合再被當成 `2409` regression 或 gain 的主要 case-level 證據。 [C]

### 5.5 `qa-only` 和 `qa+synthesis` 在 `2409` 的差異，不是單純「一個寬、一個嚴」

`2409` 的 Stage 2，`qa+synthesis` 相對 `qa-only` 改變正負向 closure 的 key 至少有 9 個： [M]

| key                                 | qa-only              | qa+synthesis         |
|:------------------------------------|:---------------------|:---------------------|
| berti2023abstractions               | exclude (senior:2)   | include (senior:5)   |
| elallaoui2018automatic              | include (junior:5,5) | exclude (senior:1)   |
| grohs2023large                      | exclude (senior:2)   | include (junior:5,5) |
| halioui2018bioinformatic            | exclude (junior:2,2) | include (senior:5)   |
| honkisz2018concept                  | exclude (senior:2)   | include (junior:5,5) |
| kourani_process_modelling_with_llm  | exclude (senior:2)   | include (senior:4)   |
| lopez_declarative_process_discovery | include (junior:5,5) | exclude (senior:1)   |
| neuberger_data_augment              | include (senior:4)   | exclude (senior:2)   |
| robeer2016                          | include (junior:5,5) | exclude (senior:2)   |

這份差異名單很重要，因為它說明：

1. `qa+synthesis` **不是單純更嚴格**。 [M]  
   它同時：
   - 把 `honkisz2018concept`、`grohs2023large`、`halioui2018bioinformatic`、`kourani_process_modelling_with_llm`、`berti2023abstractions` 往正向拉。 [M]
   - 又把 `elallaoui2018automatic`、`lopez_declarative_process_discovery`、`neuberger_data_augment`、`robeer2016` 往負向拉。 [M]

2. 它的優勢更像是：  
   **把不同類型 ambiguity 重新分配到不同 closure**，而不是單調地提升 strictness。 [I]

3. 因為沒有在這個環境重新做 per-case gold join，  
   所以這 9 個 case 裡哪幾個是「真的改善」、哪幾個只是「高方差 flip」，要分開說。 [I]

### 5.6 `2409` 哪些變化比較像真改善，哪些比較像 accidental

#### 比較像真改善的

1. **target-object / scope boundary 被明確化**，代表 case 是 `elallaoui2018automatic`。 [M][C]  
2. **`qa-only` 對 empirical validation 的誤殺，有時會被 synthesis 拉回來**，代表 case 是 `honkisz2018concept`。 [M][C]  
3. **Stage 2 canonical closure 比 Stage 1 更重要**，這是 metrics 直接支持的。 [M]

#### 比較像 accidental / high-variance 的

1. **publication-form closure 在 `2409` 仍然很飄。** [M]  
   例如：
   - `grohs2023large`：`qa-only` 因 arXiv/preprint 排掉，`qa+synthesis` 又收回。  
   - `halioui2018bioinformatic`：`qa-only` 排掉，`qa+synthesis` senior 又收回。  
   - `lopez_declarative_process_discovery`：`qa-only` include，`qa+synthesis` 因 book chapter 排掉。  
   這些比較像 workflow-layer high variance，不像穩定 improvement。

2. **Stage 1 對 secondary-study / comparison paper 的判讀還是不穩。** [M][I]  
   例如 `bellan2021process`、`bellan2020qualitative` 在 `qa+synthesis` Stage 1 被更早排掉。  
   這說明 `2409` 不能被解讀成「QA-first Stage 1 已經成熟」。

## 6. Updated diagnosis for `2511.13936`

### 6.1 現在能確定的主結論

`2511` 的主病灶沒有變：  
**Stage 1 把太多本來應該進入 Stage 2 的 case，過早壓成 exclude。** [M]

最直接的 routing 證據： [M]

| 指標 | 數值 |
|:--|--:|
| baseline maybe(3) | 15 |
| qa-only maybe(3) | 1 |
| qa+synthesis maybe(3) | 1 |
| baseline junior(1,1) | 1 |
| qa-only junior(1,1) | 37 |
| qa+synthesis junior(1,1) | 24 |

這個 routing profile 幾乎可以直接翻成一句話：  
**baseline 願意承認 ambiguous，QA-first v0 卻把 ambiguous 壓成 early exclusion。** [M]

### 6.2 `2511 qa+synthesis` 的 contamination 要明確量化

我這邊用 raw JSON 做 conservative string scan，結果如下： [M]

- Stage 1 可疑污染：**10** 筆
- Fulltext 可疑污染：**1** 筆

Codex 的本地檢查口徑是：**至少 9 + 1**。 [C]

因此報告裡最穩妥的寫法是：

> `2511 qa+synthesis` 至少有 `>=9` 筆 Stage 1 candidate-level contamination，另有 `1` 筆 fulltext contamination。 [M][C]

### 6.3 Stage 1 contamination 名單（我這邊的 raw scan）

| key                   | flags                                                                    | verdict              |
|:----------------------|:-------------------------------------------------------------------------|:---------------------|
| google_scholar_hindex | full_review_title, preference_based_learning_phrase, systematic_analysis | exclude (senior:1)   |
| cideron2024musicrl    | full_review_title, preference_based_learning_phrase, systematic_analysis | include (junior:4,5) |
| anastassiou2024seed   | preference_based_learning_phrase, systematic_analysis                    | exclude (senior:1)   |
| wu2025adaptive        | full_review_title, preference_based_learning_phrase, systematic_analysis | include (senior:5)   |
| mckeown2011semaine    | preference_based_learning_phrase, systematic_analysis                    | exclude (junior:2,2) |
| lin2004rouge          | full_review_title, preference_based_learning_phrase, systematic_analysis | exclude (junior:2,1) |
| stiennon2020learning  | systematic_analysis                                                      | exclude (senior:1)   |
| shao2024deepseekmath  | systematic_analysis                                                      | exclude (senior:1)   |
| gao2023scaling        | preference_based_learning_phrase, systematic_analysis                    | exclude (senior:2)   |
| singhal2023long       | full_review_title, preference_based_learning_phrase, systematic_analysis | exclude (senior:1)   |

### 6.4 Fulltext contamination 名單

| key            | flags                                                                    | verdict              |
|:---------------|:-------------------------------------------------------------------------|:---------------------|
| wu2025adaptive | full_review_title, preference_based_learning_phrase, systematic_analysis | include (junior:5,5) |

### 6.5 三個最具代表性的污染例子

#### 例 1: `anastassiou2024seed`

變化： [M][C]

- baseline Stage 1: `maybe (senior:3)`
- `qa-only` Stage 1: `include (junior:4,4)`
- `qa+synthesis` Stage 1: `exclude (senior:1)`
- baseline Combined: `include (junior:5,5)`
- `qa-only` Combined: `include (junior:5,5)`
- `qa+synthesis` Combined: 沒進 Stage 2

`qa+synthesis` 的 junior/senior 說法都明確提到：

> While the title indicates preference-based learning within the audio domain, there is a strong signal that this paper is a survey or review article due to the phrase 'Systematic Analysis' in the title. Stage 1 exclusion criteria explicitly exclude survey or review articles. Key preference-related criteria related to comparison type, ratings conversion, and ...

> Despite mixed signals on preference learning due to unclear preference comparison or RL loop evidence in the abstract, the title contains a strong indicator that this paper is a survey or review article ('Systematic Analysis'). This is a clear Stage 1 exclusion criterion that overrides other uncertain or positive evidence. Therefore, the paper does not meet...

而 Codex 已明確指出：  
這是錯把 SR title 的 `Systematic Analysis` 洩漏到 candidate-level 判讀。 [C]

所以這筆是 **最乾淨的 recall-collapse + contamination 雙重例子**。 [M][C]

#### 例 2: `lin2004rouge`

candidate title 是：`Rouge: A package for automatic evaluation of summaries`。  
但 `qa+synthesis` Stage 1 reasoning 卻寫成：

> Although preference learning and audio domain applicability are indicated, the presence of a survey/review article signal (from title indicating systematic analysis) is a clear exclusion signal. Critical fields regarding conversion of ratings and RL loop are deferred to Stage 2, but the survey status creates a strong exclusion lean. Given core exclusion sig...

這種 case 的價值在於它幾乎是 **smoking gun**：  
candidate 題名和 audio preference learning 完全不相干，卻被灌進 review-title 級的 survey/review signal。 [M]

#### 例 3: `google_scholar_hindex`

candidate title 是：`Top Publications - Computer Science`。  
但 `qa+synthesis` Stage 1 reasoning 寫成：

> The paper's title indicates preference-based learning in the audio domain, satisfying core inclusion criteria. However, the presence of 'Systematic Analysis' in the title strongly signals it is a survey or review article, which conflicts with explicit exclusion criteria. Several preference learning specifics (comparison type, ratings conversion, RL loop) re...

這比 `lin2004rouge` 更極端，因為它幾乎說明：
**candidate binding 不是只「有點偏」，而是整個 evidence object 可能串錯了。** [M]

### 6.6 fulltext contamination 也不是零

`wu2025adaptive` 在 fulltext raw 仍殘留了 review title 片段： [M]

```text
al",           "state": "present",           "normalized_value": "preference-based learning",           "supporting_quotes": [             "Preference-Based Learning in Audio Applications: A Systematic Analysis",             "Preference-Based Learning"           ],           "locations": [             "title",             "abstract"           ],
```

這筆最後雖然仍是 include，  
但它足以證明：**binding 問題不只存在於 Stage 1。** [M][C]

### 6.7 `2511` 不只 contamination，還有 evaluator mapping 太保守

如果只講 contamination，會漏掉另一半問題。  
`2511` 還有大量 case 顯示：只要 title/abstract 沒把 preference signal 一次講清楚，  
v0 evaluator 就很容易把它壓成 `1` / `2`，而不是 `3 -> SeniorLead -> Stage 2`。 [M][I]

代表例子：

| key | baseline Stage1 | qa-only Stage1 | qa+synthesis Stage1 | 觀察 |
|:--|:--|:--|:--|:--|
| `huang2025step` | `maybe (senior:3)` | `exclude (senior:2)` | `exclude (senior:1)` | baseline fulltext 最終 include；v0 太早關門 |
| `xu2025qwen2` | `maybe (senior:3)` | `exclude (junior:1,1)` | `exclude (senior:1)` | multimodal+audio / deferred preference evidence 被壓成 exclude |
| `jayawardena2020ordinal` | `include (junior:5,5)` | `exclude (junior:2,1)` | `exclude (senior:2)` | ordinal / ranking boundary 讀得過窄 |
| `wu2023interval` | `include (senior:5)` | `exclude (junior:2,1)` | `exclude (senior:1)` | evaluator 對 “preference vs evaluation-only” 傾向過早負判 |

上表裡，個別 case 是否都是 gold TP，這個環境沒有逐筆重 join。  
但它們至少清楚展示了：  
**QA-first v0 的 Stage 1 mapping 把 baseline 原本願意 defer 的 ambiguity，改成 early exclusion。** [M]

### 6.8 為什麼 `qa+synthesis` 比 `qa-only` 稍微好一點，但還是輸 baseline

這一段現在可以講得更精確：

1. `qa+synthesis` 相對 `qa-only` 的確有一些 recovery。 [M]  
   最明顯的是：
   - `chu2024qwen2`: `qa-only` Stage 1 exclude，`qa+synthesis` 至少改成 `maybe`，最後 fulltext include。
   - `parthasarathy2018preference`: `qa-only` Stage 1 exclude，`qa+synthesis` 直接拉成 include。

2. 但 `qa+synthesis` 又因 contamination 損失掉 `anastassiou2024seed`。 [M][C]

3. 所以 `qa+synthesis` 的淨效果是：
   - 比 `qa-only` **少一點過度保守**
   - 但又被 binding bug 拉回去  
   最終只做到 `0.8302 -> 0.8519`，仍低於 baseline `0.8814`。 [M]

## 7. QA-only vs QA+synthesis：修正版判斷

### 7.1 `qa-only` 的優點

1. candidate-level evidence integrity 比較好。 [M]  
2. 比較不會把 review title / SR-level wording 灌進 candidate-level object。 [M]  
3. 在 `2511`，它至少沒有把 `anastassiou2024seed` 這種 case 因 `Systematic Analysis` 洩漏而錯砍。 [M][C]

### 7.2 `qa-only` 的缺點

1. raw QA 太長，evaluator 要自己做 compression。 [M][I]  
2. 在 `2409`，它容易因 publication-form / empirical-validation closure 太保守，把某些正例誤砍。 [M]  
3. 在 `2511`，它對 deferred preference evidence 太 literal，常把應該進 Stage 2 的 case 提前關掉。 [M]

### 7.3 `qa+synthesis` 的優點

1. 在 `2409`，它對 Stage 2 canonical closure **有真價值**。 [M]  
2. 它不是單純變嚴，而是會重新分配 ambiguity。 [M]  
3. 在 `2511`，它也不是完全沒用；像 `chu2024qwen2`、`parthasarathy2018preference` 就有 recovery。 [M]

### 7.4 `qa+synthesis` 的缺點

1. 在 `2511`，目前最大的問題不是 prompt wording，而是 **binding / contamination bug**。 [M]  
2. 一旦 synthesis object 串錯，`SeniorLead` 會把假 survey signal 當 hard exclusion。 [M]  
3. 所以在 decontamination 完成前，不能把 `qa+synthesis` 在 `2511` 的結果拿來評估 synthesis 本身是否有價值。 [M][C]

## 8. 哪些是 workflow-layer 真改善，哪些只是 accidental

### 8.1 比較像真的改善

1. **`2409` 的 Stage 2 evidence normalization / canonical closure** [M]  
2. **`2511` seed patch 把 `M1` 改成 reviewer guardrail，而不是假裝 answerable QA** [M]  
3. **structured QA 對 `2511` 的 precision suppression 是有效的**，只是現在 over-correct。 [M]

### 8.2 比較像 accidental 或 implementation noise

1. **`2511 qa+synthesis` review-title contamination** [M][C]  
2. **`2409` publication-form closure 的高方差 flip** [M]  
3. **`goossens2023extracting` 類型的 handoff hygiene 髒欄位** [M][C]  
4. **`2409` Stage 1 對 comparison / qualitative papers 的過早 secondary-study closure** [M][I]

## 9. 下一輪應該保留什麼、修什麼、不要動什麼

### 9.1 保留

1. 保留 current production criteria：
   - `criteria_stage1/<paper_id>.json`
   - `criteria_stage2/<paper_id>.json`
2. 保留 `SeniorLead`
3. 保留 `2511` 把 metadata/guardrail 類訊息留在 reviewer layer 的 patch
4. 保留 `2409` 用 structured evidence 幫助 Stage 2 closure 的方向

### 9.2 修

1. **先修 synthesis binding / decontamination，再談 synthesis value。**
2. `2511` Stage 1 的 evaluator mapping 要改：  
   若 preference signal 只是 unresolved，而不是明確 negative，預設應往 `3 -> SeniorLead`，不是 `1/2 -> exclude`。
3. handoff payload 要保留 raw quotes / field states，避免只剩被壓縮過的 judgment sentence。
4. rerun 前先做 contamination audit：
   - stage1 raw scan
   - fulltext raw scan
   - stage / arm / paper_id consistency assertions

### 9.3 不要動

1. 不要重寫 formal criteria
2. 不要把 workflow-layer hardening 偽裝成 criteria rewrite
3. 不要移除 `SeniorLead`
4. 不要把 `qa+synthesis` 直接當 production workflow
5. 不要把 `Hybrid-2409` 寫成已被證明；它只是值得測的假設

## 10. Recommended next experiment

### 10.1 `2409`

最值得測的是：

**`Hybrid-2409 = QA-only Stage 1 + QA+synthesis Stage 2`** [I]

理由不是它已被結果直接證明，  
而是目前 evidence 顯示：

- `2409` 的 gain 主要在 Stage 2
- `qa+synthesis` 的價值也主要出現在 Stage 2 closure
- 但 Stage 1 本身沒有因此更穩

所以這是**值得測的下一輪假設**，不是已驗證結論。

### 10.2 `2511`

最優先的下一輪不是改 criteria，而是：

**`Decontaminated-2511 Stage1`** [M]

具體做法：

1. 先加 binding assertions  
   - candidate title
   - candidate key
   - paper_id
   - stage
   - arm  
   任一不一致就 fail fast

2. Stage 1 對 unresolved preference evidence 預設走 `3 -> SeniorLead`

3. 在 decontamination 完成前：
   - 不讓 synthesis object 的 survey/review signal 單獨主導 hard exclusion
   - 先觀察 qa-only 與 cleaned-synthesis 的差異

## 11. Final one-paragraph conclusion

這輪修正版最重要的更新有四個。  
第一，原先的高層方向大致是對的：`2409` 的 gain 主要來自 Stage 2，`2511` 的 regression 主要來自 Stage 1 recall collapse。  
第二，`honkisz2018concept` 必須移除出 precision-gain 敘事，`elallaoui2018automatic` 才是更合適的 boundary-fire 代表。  
第三，`2511 qa+synthesis` 的 contamination 不能只抽象描述，應保守寫成 **`>=9` 筆 Stage 1 + `1` 筆 fulltext**。  
第四，下一輪真正該修的是 workflow layer：`2511` 先 decontaminate + 放寬 unresolved-to-senior routing；`2409` 再測 Stage 2-oriented hybrid，而不是去重寫 formal criteria。
