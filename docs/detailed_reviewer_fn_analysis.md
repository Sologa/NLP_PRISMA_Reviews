# Detailed FN Analysis: Reviewer Effects, Taxonomy, Stage-1 Recall Policy, and 2307.05527 Deep Dive

## 0. 目的與資料來源

這份報告是前一份 reviewer-oriented 報告的擴充版，目標有四個：

1. 先確認 false negative 到底是不是某個 reviewer 特別差。
2. 如果不是單一 reviewer 問題，則依照先前約定的 `1 -> 3` 路線繼續分析：
   - `1`：建立跨 review 的 FN taxonomy
   - `2`：提出更偏 recall 的 Stage 1 decision rule
   - `3`：深入拆解 `2307.05527`
3. 把 reviewer 問題和 pipeline aggregation 問題分開。
4. 給出後續最值得先改的地方。

分析使用的資料：

- `screening/results/<paper>_full/run01/latte_review_results.run01.json`
- `screening/results/<paper>_full/latte_fulltext_review_from_run01.json`
- `refs/<paper>/metadata/title_abstracts_metadata-annotated.jsonl`
- `criteria_jsons/<paper>.json`
- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

分析對象：

- `2307.05527`
- `2409.13738`
- `2511.13936`
- `2601.19926`

## 1. 先講最重要的結論

整體來看，確實有 reviewer-specific 差異，但真正放大 FN 的不是單一 reviewer，而是：

- Stage 1 本身偏保守
- senior arbitration 規則會把 disagreement case 壓成 `exclude`
- 某些 review 的 criteria / topic grounding 有系統性偏差

一句話總結：

- `JuniorMini` 是比較好的 Stage 1 reviewer。
- `JuniorNano` 較保守，確實比較容易造成 FN。
- 但如果只怪 `JuniorNano`，會低估 `SeniorLead + aggregation` 的影響。

更具體地說：

- 四篇合計 Stage 1 FN = `117`
- 其中 `59` 個是兩個 junior 都判成 negative
- 其中 `58` 個是至少一個 junior 已經 positive 或 unclear，但 final Stage 1 還是 `exclude`

這個比例幾乎一半一半，所以問題不能只歸因在單一 reviewer。

## 2. Pipeline 行為：FN 是怎麼被放大的

這一段很重要，因為很多 error 並不是 reviewer 單獨犯的，而是 aggregation 規則把它放大。

### 2.1 `SeniorLead` 什麼時候會出手

在 [topic_pipeline.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/src/pipelines/topic_pipeline.py:4957) 附近，`_senior_filter` 的邏輯大致是：

- 若兩位 junior 分數不同，而且至少一人分數 `>= 3`，就送 senior
- 若兩人都給 `3`，也送 senior
- 若兩人都高分，則不送 senior

意思是：

- `5 vs 1`
- `4 vs 2`
- `5 vs 3`
- `3 vs 3`

這些都可能被 senior 接手。

### 2.2 final verdict 怎麼來

在 [topic_pipeline.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/src/pipelines/topic_pipeline.py:4699) 附近，`_derive_final_verdict_from_row` 的邏輯是：

- 若 senior 有分數，直接用 senior 分數
- 若 senior 沒分數，才用兩個 junior 分數平均後四捨五入

這個規則的副作用非常明顯：

- 只要 senior 出手，實際上就是 senior 覆蓋兩個 junior
- 而 senior 在這批 run 裡明顯比 juniors 更保守

因此很多 case 的路徑是：

- `Junior A = include`
- `Junior B = exclude`
- `Senior = 2`
- final = `exclude`

這就是為什麼我們看到很多 FN 不是「兩個 junior 都失敗」，而是「有一個 junior 已經看對了，但被 senior 壓掉」。

## 3. Reviewer 層次的定量分析

### 3.1 Stage 1: title + abstract

將 reviewer 分數視為單獨 classifier，採用：

- `4-5` -> positive
- `1-2` -> negative
- `3` -> unclear

結果如下：

| Reviewer | TP | FP | TN | FN | Unclear | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `JuniorNano` | 386 | 16 | 161 | 121 | 54 | 0.960 | 0.761 |
| `JuniorMini` | 384 | 13 | 160 | 80 | 101 | 0.967 | 0.828 |
| `SeniorLead` | 60 | 1 | 6 | 58 | 613 | 0.984 | 0.508 |

解讀：

- `JuniorMini` 的 Stage 1 recall 明顯最好。
- `JuniorNano` 較容易過早排除。
- `SeniorLead` precision 很高，但 coverage 很低，而且行為明顯偏 conservative。

### 3.2 Stage 2: full text

| Reviewer | TP | FP | TN | FN | Unclear | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `JuniorNano` | 411 | 11 | 1 | 24 | 10 | 0.974 | 0.945 |
| `JuniorMini` | 403 | 11 | 1 | 26 | 16 | 0.973 | 0.939 |
| `SeniorLead` | 17 | 0 | 0 | 25 | 415 | 1.000 | 0.405 |

這個結果更支持一件事：

- 只要 paper 進得了 full text，兩個 junior 其實都做得不差。
- 真正的 recall 瓶頸主要在 Stage 1。

### 3.3 單看 reviewer，誰問題最大

如果只比較兩個 junior：

- `JuniorMini` 明顯優於 `JuniorNano`
- 因此若一定要指出一個 reviewer 問題比較大，答案是 `JuniorNano`

但若從最終 FN 的系統來源來看：

- `JuniorNano` 不是唯一主因
- `SeniorLead` 的 override 與 aggregation 設計，同樣是主因

因此比較精確的結論是：

- reviewer 層次：`JuniorNano` 較弱
- system 層次：`SeniorLead + aggregation` 更容易把可挽回的 case 壓成 FN

## 4. Review-by-Review：reviewer 與 aggregation 各自影響多大

### 4.1 `2307.05527`

Stage 1 standalone recall：

- `JuniorNano`: `0.782`
- `JuniorMini`: `0.916`

Stage 1 final FN：`33`

Stage 1 FN pattern：

- `17` 個是 `JuniorNano=neg`, `JuniorMini=pos`, final 仍 `exclude`
- `6` 個是 `JuniorNano=pos`, `JuniorMini=neg`, final 仍 `exclude`
- 只有 `6` 個是兩個 junior 都 negative

解讀：

- 這篇最嚴重的不是 junior 共同失敗
- 而是 disagreement case 被 senior/aggregation 壓掉

`SeniorLead` 對 `2307.05527` 的 recall 傷害非常大。

### 4.2 `2409.13738`

Stage 1 standalone recall：

- `JuniorNano`: `0.850`
- `JuniorMini`: `0.889`

Stage 1 final FN：`4`

pattern：

- `2` 個是兩個 junior 都 negative
- `2` 個是至少一個 junior positive/unclear，但 final 還是 `exclude`

解讀：

- 沒有特別壞的 reviewer
- 真正的問題是 abstract 裡沒有明說 validation 時，policy 太容易直接排除

### 4.3 `2511.13936`

Stage 1 standalone recall：

- `JuniorNano`: `0.700`
- `JuniorMini`: `0.655`

Stage 1 final FN：`10`

pattern：

- `8` 個是兩個 junior 都 negative
- `2` 個才是 disagreement 後被壓掉

解讀：

- 這篇比較不像 arbitration 問題
- 比較像兩個 junior 對 criteria 的 operational definition 都理解得太窄

### 4.4 `2601.19926`

Stage 1 standalone recall：

- `JuniorNano`: `0.749`
- `JuniorMini`: `0.785`

Stage 1 final FN：`70`

pattern：

- `43` 個是兩個 junior 都 negative
- `27` 個是至少一個 junior positive/unclear，但 final 仍 `exclude`

解讀：

- 這篇是混合型問題
- 一半像 reviewer 在 sparse metadata 上過度保守
- 一半像 arbitration/aggregation 放大了保守傾向

## 5. Part 1: FN Taxonomy

這一節是 `1 -> 3` 裡的第 `1` 部分。

### 5.1 方法說明

我把 FN 分成 review-specific taxonomy。這些 taxonomy 是為了找到「穩定的錯誤型態」，不是為了做完美互斥分類。

因此要注意：

- 同一篇 paper 可以同時落入多個 tag
- 所以下面的 count 不是 mutually exclusive

### 5.2 `2307.05527` 的 taxonomy

主要 tag 與數量：

- `topic_narrowed_to_explicit_ethics`: `42`
- `broad_or_symbolic_music_gen_flagged`: `43`
- `stage2_scope_reversal`: `19`
- `technical_generative_audio_misaligned_with_gold_scope`: `13`

代表性例子：

- `huang2020ai`:
  - `AI Song Contest: Human-AI Co-Creation in Songwriting`
  - 被排除的核心理由是「沒有直接談 ethical implications」
- `Suh2021AI`:
  - Stage 1 進了，Stage 2 又因為「social dynamics 不是 ethics」被翻掉
- `zhou2018voice`:
  - `Voice Conversion with Conditional SampleRNN`
  - 明顯是 generative audio paper，但仍被排除，理由仍是沒有 ethics

這一組 taxonomy 指向同一個核心問題：

- reviewer 把 `topic_definition` 裡的 ethical framing，錯當成嚴格 inclusion criterion

### 5.3 `2409.13738` 的 taxonomy

主要 tag 與數量：

- `validation_not_explicit_in_abstract`: `4`
- `process_extraction_boundary_case`: `4`
- `decision_model_vs_process_model_boundary`: `1`

代表性例子：

- `etikala2021extracting`
- `goncalves2011let`
- `honkisz2018concept`

共通點：

- 都很像 NLP-to-process / model extraction
- 但 abstract 沒明寫驗證實驗時，就被直接排除

這組 taxonomy 的中心問題是：

- `lack of explicit validation` 被直接映射成 `exclude`
- 而不是 `unclear -> maybe`

### 5.4 `2511.13936` 的 taxonomy

主要 tag 與數量：

- `preference_definition_too_strict`: `10`

如果看這 `10` 個 Stage 1 FN 的 title/abstract 關鍵詞：

- 含 `speech` 的有 `6`
- 含 `call` 的有 `6`
- 含 `emotion` 的有 `7`
- 直接含 `audio` 的只有 `1`

這組 taxonomy 非常集中，幾乎都在同一個問題上：

- reviewer 太要求 abstract 明講 `audio`
- reviewer 對 preference learning 的定義太偏向顯式 pairwise / A-B comparison

代表性例子：

- `lotfian2016retrieving`
- `parthasarathy2016using`
- `parthasarathy2018preference`
- `han2020ordinal`

這一組其實是在告訴我們：

- gold label 的 operational definition 比 reviewer 當下採用的定義更寬

### 5.5 `2601.19926` 的 taxonomy

主要 tag 與數量：

- `explicit_tlm_or_syntax_signal_still_missed`: `62`
- `insufficient_ta_evidence_defaults_to_exclude`: `47`
- `sparse_or_citation_like_abstract`: `19`
- `fulltext_retrieval_failure`: `5`
- `mt_or_encoder_decoder_boundary`: `5`

代表性例子：

- `mccoy_right_2019`
- `Tenney:etal:2019b`
- `Warstadt:etal:2020`
- `marecek_balustrades_2019`

這組 taxonomy 告訴我們有三層問題：

1. metadata 品質差
2. reviewer 對 sparse metadata 過度保守
3. 有些 Stage 2 FN 根本不是語義判斷，而是 `missing_fulltext`

### 5.6 跨四篇總結：taxonomy 對應到哪幾種大錯誤

如果把四篇合起來，高階上可濃縮成五類：

1. `Topic framing 被誤當硬 criteria`
   - 典型：`2307`

2. `缺少正面證據` 被誤當 `排除證據`
   - 典型：`2409`, `2601`

3. `operational definition 太窄`
   - 典型：`2511`

4. `disagreement arbitration 過於保守`
   - 典型：`2307`, `2601`

5. `pipeline / retrieval 問題`
   - 典型：`2601` 的 `missing_fulltext`

## 6. Part 2: Stage 1 Recall-First Decision Rule

這一節是 `1 -> 3` 裡的第 `2` 部分。

### 6.1 為什麼要改 Stage 1 規則

你的流程是：

- Stage 1: title + abstract
- 若 Stage 1 = `exclude`，就永遠不進 Stage 2

因此 Stage 1 的 false negative 成本非常高。

換句話說：

- Stage 1 不應該像 final decision
- Stage 1 應該像 `high-recall gate`

### 6.2 建議的新決策原則

最核心的一句話：

- 在 Stage 1，`缺少足夠證據支持 include` 不等於 `有足夠證據支持 exclude`

建議規則如下：

#### Rule A: 只有在「明確排除證據」存在時，才允許 Stage 1 `exclude`

例如：

- 明確是 survey / review / meta-analysis
- 明確不是該 domain
- 明確是非 transformer / 非 audio / 非 process extraction
- 明確是 evaluation-only，不是 learning

#### Rule B: 任何 disagreement case 預設走 `maybe`

具體化：

- `pos + neg` -> `maybe`
- `pos + unclear` -> `maybe`
- `unclear + neg` -> `maybe`
- `unclear + unclear` -> `maybe`

#### Rule C: 只有 `neg + neg` 才允許進入 `exclude`

但這裡還要再加一層保護：

- 若 title/abstract 很 sparse
- 或 abstract 幾乎只是 citation text
- 或 metadata 不足

則 `neg + neg` 也應優先改成 `maybe`

#### Rule D: Stage 1 的 `include` 條件應該比現在保守一些，但 `maybe` 應更寬

也就是：

- `pos + pos` -> `include`
- 其他非雙負情況 -> `maybe`

這會讓 Stage 2 工作量增加，但能顯著改善 recall。

### 6.3 Counterfactual：如果只用「雙負才排除」

我用現有 run01 的 reviewer 分數做了一個簡單 counterfactual：

- 只要兩個 junior 不同意都 negative，就不要 Stage 1 `exclude`
- 換句話說：`only both negative => exclude`

四篇合計 Stage 1 的變化如下：

| Policy | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 現況 | 440 | 17 | 164 | 117 | 0.9628 | 0.7899 | 0.8679 |
| `only both neg => exclude` | 498 | 23 | 158 | 59 | 0.9559 | 0.8941 | 0.9239 |

這個結果很強：

- precision 只從 `0.9628` 小降到 `0.9559`
- recall 從 `0.7899` 大幅升到 `0.8941`

這代表目前系統真的太保守。

### 6.4 Counterfactual：各 review 的 Stage 1 改善幅度

| Review | Actual Recall | CF Recall | FN Recover | Actual Precision | CF Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| `2307.05527` | 0.807 | 0.965 | 27 | 0.979 | 0.976 |
| `2409.13738` | 0.810 | 0.905 | 2 | 0.680 | 0.633 |
| `2511.13936` | 0.667 | 0.733 | 2 | 0.952 | 0.957 |
| `2601.19926` | 0.791 | 0.872 | 27 | 0.981 | 0.977 |

解讀：

- `2307` 和 `2601` 的收益最大
- `2409` 也有改善，但 precision 下降相對明顯
- `2511` 改善有限，表示它更多是 criteria-definition 問題，不只是 arbitration 問題

### 6.5 若要更保守一點，可用 `JuniorMini anchor`

另一個比較穩妥的政策是：

- 先以 `JuniorMini` 作為 Stage 1 anchor
- `JuniorMini >= 3` 視為保留
- 再用另一位 reviewer 做附加參考

這個政策對 Stage 1 的影響：

- `2307`: recall `0.807 -> 0.918`
- `2601`: recall `0.791 -> 0.839`
- `2511`: 幾乎沒變

這說明：

- `JuniorMini` 適合做 recall-sensitive gate
- 但它不能單獨修好 `2511`

### 6.6 對 prompt 的直接修改建議

Stage 1 prompt 應明寫以下原則：

1. `缺少支持 include 的證據` 不等於 `支持 exclude 的證據`
2. 若 abstract 不能確證，但 title/abstract 沒有明確排除訊號，給 `maybe`
3. reviewer 不得用 `topic_definition` 去縮窄 `inclusion_criteria`
4. sparse metadata / citation-like abstract 一律偏向 `maybe`
5. 若兩位 reviewer 分歧，final Stage 1 不得直接因 senior 單人意見變成 `exclude`，除非 senior 能指出明確 exclusion evidence

## 7. Part 3: `2307.05527` 深入拆解

這一節是 `1 -> 3` 裡的第 `3` 部分。

也是四篇裡最值得優先修的那一篇。

### 7.1 這篇最核心的問題：criteria grounding 有內部不一致

看 [2307.05527.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/criteria_jsons/2307.05527.json) 可以看到：

- `topic_definition` 談的是 ethical implications
- 但 `inclusion_criteria.required` 真正列出的條件是：
  - full research paper
  - topic is generative audio models / application as primary focus
  - output domain entirely audio
  - evidence scope in main text + appendices

關鍵點是：

- `inclusion_criteria.required` 本身沒有要求 paper 必須直接討論 ethics

但 reviewer 的理由卻大量變成：

- 「這篇沒有討論 ethical/legal/social implications，所以 exclude」

這表示目前系統很可能把：

- `topic_definition`

誤讀成：

- `hard inclusion criterion`

### 7.2 數據上這件事有多嚴重

`2307.05527` 的 final FN = `55`

其中：

- Stage 1 FN = `33`
- Stage 2 FN = `22`

如果看理由文字：

- Stage 1 FN 中，`22/33` 的主要理由明確提到 ethics / legal / social implications
- Stage 2 FN 中，`19/22` 的主要理由也明確提到 ethics / legal / social implications

這不是偶發，而是系統性偏差。

### 7.3 Reviewer 與 aggregation 在 `2307` 的具體傷害

Stage 1 final FN = `33`

其中：

- 只有 `6` 個是兩個 junior 都 negative
- `27` 個其實至少一個 junior 已經 positive 或 unclear

這幾乎直接說明：

- 這篇的 recall 不是被 junior 本身吃掉的
- 而是被 senior override 吃掉的

### 7.4 Counterfactual：如果只是改 arbitration，`2307` 會好多少

`2307` 的 Stage 1：

| Policy | TP | FP | TN | FN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 現況 | 138 | 3 | 44 | 33 | 0.979 | 0.807 |
| `only both neg => exclude` | 165 | 4 | 43 | 6 | 0.976 | 0.965 |

這是一個非常大的差距。

重點是：

- precision 幾乎沒掉
- recall 大幅提高

表示 `2307` 現在的問題不是必要的 precision-recall tradeoff。

### 7.5 這些被錯殺的 paper 類型

`2307` 的 FN 大致可分為四群：

1. `generative music / co-creation / HCI`
   - `huang2020ai`
   - `Suh2021AI`

2. `technical generative audio or speech papers`
   - `zhou2018voice`
   - `marafioti_context_2019`
   - `xiang_parallel-data-free_2020`

3. `AI-generated audio detection / misuse-related papers`
   - `Wang2020DeepSonar`
   - `Li2021Robust`

4. `broad survey / symbolic or mixed music generation papers`
   - `zhao_review_2022`
   - `purwins2019deep`

前 1 到 3 類其實最關鍵，因為它們很可能是 gold 標注認為應保留的 evidence base，但被 reviewer 以「沒有直接談 ethics」為由排掉。

### 7.6 為什麼 `2307` 特別危險

因為它呈現出一種很難靠小修補修好的錯誤：

- 不是單篇 abstract 難
- 不是某個 reviewer 隨機失手
- 而是 criteria representation 本身把 reviewer 帶到錯方向

只要這個 grounding 不改：

- 換模型也可能重複犯同樣的錯
- 換 prompt wording 也可能只得到局部改善

### 7.7 `2307` 最值得優先做的修正

我會把 `2307` 的修正排在最高優先級：

1. 在 criteria prompt 中明確分離：
   - `topic background`
   - `eligibility rule`

2. 直接加一條硬性 instruction：
   - `不得因 paper 未直接討論 ethics 而排除，除非 inclusion_criteria 明文要求 ethics discussion`

3. disagreement case 不得由 senior 單獨用 topic paraphrase 做 narrowing

4. 對 `2307` 做一次 criteria serialization 重整
   - 讓 prompt 僅看到可執行 eligibility criteria
   - 不讓 `topic_definition` 在 decision step 參與判斷

## 8. 綜合判斷：先改哪裡最有價值

若要按 ROI 排序，我會建議：

### Priority 1: 改 Stage 1 arbitration

原因：

- 成本低
- 對 `2307`、`2601` 立刻有效
- 可直接救回大量 FN

### Priority 2: 改 `2307` criteria grounding

原因：

- 這是最明顯的系統性 misalignment
- 不修它，senior 會持續把 paper 依 ethics narrow 掉

### Priority 3: 對 `2511` 重寫 operational definition

原因：

- 這篇的問題更多在 criteria interpretation
- 單靠 arbitration 規則，改善有限

### Priority 4: 對 `2601` 增加 sparse metadata fallback

原因：

- citation-like abstract 太多
- 缺資訊時不應直接排除

### Priority 5: 將 `missing_fulltext` 從 reviewer error 中分開

原因：

- 這屬於 retrieval / pipeline failure
- 不應和 semantic screening error 混在一起

## 9. 最後的結論

如果只問「是不是某個 reviewer 問題比較大」：

- 是，`JuniorNano` 在 Stage 1 比 `JuniorMini` 差。

如果問「真正最需要修的是哪裡」：

- 不是單一 reviewer，而是 `Stage 1 aggregation policy`
- 再加上 `2307` 的 criteria grounding 問題

如果問「依照 1 -> 3 的順序分析後，哪個發現最有行動價值」：

- 最有價值的是第 `2` 點，也就是 Stage 1 recall-first decision rule
- 因為它能在不大幅犧牲 precision 的前提下，直接大幅減少 FN

最值得立刻做的最小修正版本是：

1. Stage 1 只有在 `兩個 junior 都 negative` 時才允許 `exclude`
2. sparse / citation-like metadata 一律偏向 `maybe`
3. senior 不可單獨用 `topic_definition` 收窄 criteria
4. `2307` 的 decision prompt 只暴露真正的 inclusion / exclusion rules

如果你要往下走，下一份最有價值的報告應該是：

- 直接把新的 Stage 1 policy 寫成可落地規格
- 或者直接改 prompt / aggregation code，然後跑一次 counterfactual re-eval
