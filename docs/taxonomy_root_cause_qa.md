# Taxonomy Root-Cause Q&A

This note answers the five follow-up questions based on taxonomy section 5.6 in the detailed FN report.

## Q1. `Topic framing 被誤當硬 criteria`：這是不是 prompt template 的問題？

短答案：

- 是，但不是只有 prompt template。
- 更精確地說，這是 `criteria serialization + runtime reviewer prompt + senior arbitration` 三者一起造成的。

### 1. 先把目前會影響行為的 prompt 分成兩層

#### A. Repo 裡的 markdown prompt templates

這一層是你手上那套較明確、規則比較完整的模板：

- [03_stage1_2_criteria_review.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/sr_screening_prompts_3stage/sr_specific/03_stage1_2_criteria_review.md)
- [05_stage2_criteria_review.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/sr_screening_prompts/sr_specific/05_stage2_criteria_review.md)

這一層的特點是：

- Stage 1 明確允許 `maybe`
- 明確寫了「沒有證據就給 3（UNCLEAR），禁止臆測」
- 明確把 Stage 1 當作 title+abstract only 的保守判斷

如果這一套被完整拿去執行，taxonomy 1 的問題理論上會小很多。

#### B. 目前 run 實際用到的 runtime reviewer prompt

真正影響這批 run 的是 vendor reviewer 類別：

- [title_abstract_reviewer.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py)
- [fulltext_reviewer.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py)
- [basic_reviewer.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/resources/LatteReview/lattereview/agents/basic_reviewer.py)

它們的核心 prompt 非常簡單：

- 把 input item 貼進去
- 把 inclusion criteria / exclusion criteria 貼進去
- 告訴 reviewer：滿足全部 inclusion 且不碰任何 exclusion 才 include
- 輸出 `1-5`

但這層 prompt 沒有幾個非常重要的 guardrail：

- 沒有明確說 `topic_definition` 只是背景，不是 eligibility rule
- 沒有明確說 `lack of evidence != evidence of exclusion`
- 沒有 evidence-quote 機制
- 沒有逐條 criteria 狀態
- 沒有說明 sparse metadata 應偏 `maybe`
- 沒有明確說 Stage 1 是 recall-first gate

### 2. 真正致命的是 criteria serialization

目前 criteria 進 reviewer 前，會先被 serialize 成字串。在 [topic_pipeline.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/src/pipelines/topic_pipeline.py:4440) 附近，程式會把：

- `topic_definition`

直接 prepend 到 inclusion text，形式是：

- `主題定義：{topic_definition}`

也就是說 reviewer 實際看到的 inclusion criteria 第一條，不只是 formal inclusion 條件，而是整段主題定義本身。

這會導致：

- reviewer 容易把 topic framing 當成一條必須滿足的 inclusion line

對 `2307.05527` 而言，這等於把：

- `The ethical implications of generative audio models...`

直接塞成 reviewer 眼中的 inclusion criterion。

### 3. 為什麼這會特別害 `2307`

因為 `2307` 的 criteria JSON 本身是：

- `topic_definition`：很強烈地談 ethics
- `inclusion_criteria.required`：其實列的是 generative audio / audio output / full paper 等條件

這兩者本來就不是同一層。

但 runtime reviewer prompt 沒有能力把它們分層，而且 serialization 又把 `topic_definition` 放進 inclusion list 最前面，於是 reviewer 很自然就會判成：

- 「這篇 paper 沒有直接談 ethics，所以不滿足 inclusion」

### 4. 這是不是純 template 問題？

不是純 template 問題。

更精確地分層：

1. `sr_screening_prompts/` 這套 markdown template：
   - 其實比 runtime prompt 更安全

2. runtime reviewer prompt：
   - 太 generic，缺乏 guardrail

3. criteria serialization：
   - 直接把 `topic_definition` 混進 inclusion string

4. senior arbitration：
   - 一旦 senior 接手，最終判斷幾乎就被 senior 單人覆蓋

所以 taxonomy 1 的根因不是「單一 template 寫壞」，而是：

- prompt 太 generic
- criteria serialization 把背景敘述變成半硬規則
- aggregation 又讓這個偏差被放大

### 5. 我對 Q1 的結論

- 是，和 prompt 有高度關係。
- 但最該修的不是單純改 wording，而是：
  - 不要把 `topic_definition` prepend 到 inclusion criteria
  - runtime prompt 要明寫 `topic_definition is background, not a hard criterion`
  - Stage 1 prompt 要明寫 `lack of explicit ethics mention is not exclusion evidence`

## Q2. `缺少正面證據` 被誤當 `排除證據`：這是 criteria 沒寫好，還是 reviewer 找不到證據就直接排？

短答案：

- 主要不是 criteria 寫壞。
- 主要是 reviewer 在 Stage 1 找不到足夠證據時，直接走向 `exclude`，而不是 `maybe`。
- 但更深一層來說，這也是 `same criteria used at final stage` 被直接套到 `title+abstract stage` 的 operational mismatch。

### 1. 先看 `2409.13738` 的特徵

這一類 FN 的典型例子是：

- `etikala2021extracting`
- `goncalves2011let`
- `honkisz2018concept`

它們的共通點是：

- 很像 process/model extraction paper
- abstract 可能沒明寫實驗驗證
- reviewer 因此判成 `exclude`

### 2. criteria 本身有沒有錯

如果你把這些 criteria 當成 final/full-text criteria，看起來不算錯：

- full research paper
- primary research
- concrete method
- experiments to empirically validate the method

這些都合理。

問題在於：

- Stage 1 只有 title+abstract
- 但 reviewer 被要求實際上像 final gate 一樣地判

於是就會出現：

- abstract 沒看到 validation
- reviewer 就把「看不到」當成「沒有」

### 3. 這個錯是 criteria 還是 reviewer？

比較準確的說法是：

- `criteria 本身`: 不一定錯
- `Stage 1 operationalization`: 有問題
- `runtime prompt`: 沒有告訴 reviewer 遇到證據不足時要偏 `maybe`

如果你用更 formal 的邏輯寫，就是：

- `not observed in abstract`
  不應推出
- `criterion is false`

但目前 reviewer 行為卻常常是這樣推。

### 4. 為什麼 markdown template 比 runtime prompt 安全

因為 Stage 1 markdown template 明寫：

- 沒有證據就給 `3 / UNCLEAR`
- 任一 unclear -> `maybe`

但 runtime prompt 只說：

- 滿足全部 inclusion 才 include
- 輸出 1 到 5 分

少了這些「缺證據時的行為規則」後，model 很容易自發採保守策略：

- 「我無法證明它符合」
- `=>` 低分

### 5. 我對 Q2 的結論

- 這一類問題主要不是 criteria 沒寫好。
- 主要是 reviewer 在 Stage 1 沒找到足夠證據，就直接排除了。
- 如果要修，優先修的是 Stage 1 prompt / policy，不是先重寫 criteria。

更具體地說：

- Stage 1 需要一條明文規則：
  - `abstract 未明示驗證 ≠ 可直接排除`
  - `若主題相符但驗證訊息不足 -> maybe`

## Q3. `operational definition 太窄`：這是 criteria 沒寫好嗎？

短答案：

- 這一項比 Q2 更像 criteria wording 問題。
- 尤其是 `2511.13936`，我認為 criteria 的 operational boundary 沒寫得足夠可執行，才讓 reviewer 用了過窄版本。

### 1. 為什麼 `2511` 特別像 criteria 問題

`2511.13936` 的核心 criteria 是：

- preference-learning component exists
- audio-domain application is present

看起來很清楚，但實際上有兩個邊界沒有寫死：

1. `audio-domain` 要多 explicit 才算？
2. `preference learning` 是否包含：
   - ordinal learning
   - rank-based formulations
   - relative labels
   - qualitative agreement derived rankings

從 gold label 看起來，答案比較寬。

但 reviewer 實際採用的答案比較窄：

- 要看見更直接的 `audio`
- 要看見更直接的 pairwise / A-B preference

### 2. 這代表什麼

這表示：

- gold operational definition
  和
- criteria 文本可直接推得出的 operational definition

之間存在落差。

一旦 reviewer 只能從文字字面判，它就很容易收窄成：

- explicit pairwise preference only
- explicit audio mention only

### 3. 為什麼我說這比 Q2 更像 criteria 問題

因為 Q2 的 case 大多是：

- criteria 沒錯，但 abstract 訊息不足

而 Q3 的 case 更像：

- criteria 本身就沒有把邊界寫清楚

例如：

- `han2020ordinal`
- `parthasarathy2016using`
- `parthasarathy2018preference`

這些 paper 的 title/abstract 明明有 ranking / emotion / speech-like task context，
但 reviewer 還是能合理地用較窄的字面解讀把它們排掉。

如果 criteria 真要納入這些 paper，就應該更明寫：

- ordinal / rank-based learning in audio tasks counts
- audio modality may be inferred from standard speech-emotion task wording or canonical datasets

### 4. 我對 Q3 的結論

- 是，這一項我傾向判為 criteria 沒寫夠清楚。
- prompt 可以幫忙，但不能根治。
- 這一類最好直接重寫 criteria 的 operational definition。

## Q4. `disagreement arbitration 過於保守`：這個是不是同上？

短答案：

- 不同。
- 這一項主要不是 criteria 問題，而是 workflow / aggregation 問題。

### 1. 這件事發生在哪裡

在 [topic_pipeline.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/src/pipelines/topic_pipeline.py:4966) 附近，`_senior_filter` 會把某些 disagreement case 送給 senior。

在 [topic_pipeline.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/src/pipelines/topic_pipeline.py:4699) 附近，`_derive_final_verdict_from_row` 的邏輯是：

- senior 有分數 -> 直接用 senior
- 否則才平均 juniors

所以只要 senior 被叫進來，實質上就是：

- `senior override`

### 2. 這為什麼會造成 taxonomy 4

因為很多 Stage 1 FN 其實不是兩個 junior 都失敗。

四篇合計：

- Stage 1 FN = `117`
- 其中至少 `58` 個 case 是「至少一位 junior 已經 positive 或 unclear」

也就是說：

- 這些 case 本來完全有機會被留在 pipeline 裡
- 但因為 senior 的單人保守判斷，最後變成 `exclude`

### 3. 所以 Q4 跟 criteria 有關嗎

只有弱關聯。

因為：

- criteria 若寫得模糊，會增加 disagreement
- 但 disagreement 被怎麼解，主要是 workflow design

taxonomy 4 的主根因不是 criteria，而是：

- senior 何時被觸發
- senior 是否覆蓋 juniors
- disagreement 是否預設 `maybe`

### 4. 我對 Q4 的結論

- 不是「同上」。
- 它不是主要的 criteria 問題。
- 它是 aggregation / arbitration policy 問題。

最直接的修法不是重寫 criteria，而是改 policy：

- `pos + neg -> maybe`
- `unclear + neg -> maybe`
- `pos + unclear -> maybe`
- 只有 `neg + neg -> exclude`

## Q5. `pipeline / retrieval 問題`：找不到的不都是本來就 exclude 嗎？還是真的有少數篇連手動也難拿但剛好是入選的？

短答案：

- 不是，`pipeline 找不到 full text` 不等於這篇本來就該 exclude。
- 在目前這批結果裡，確實有個位數篇 `gold-positive` 因為 `missing_fulltext` 被排除。
- 而且我查到的這些 `gold-positive missing_fulltext` 裡，至少多篇今天其實公開可得，表示這更像 pipeline failure，不是「人手也真的拿不到」。

### 1. 目前實際有多少 `missing_fulltext`

在這批 run 裡，`exclude (missing_fulltext)` 出現在 `2601.19926`。

共有 `10` 篇：

- 其中 `5` 篇是 gold negative
- 其中 `5` 篇是 gold positive

也就是說：

- 不是所有 `missing_fulltext` 都本來就該 exclude
- 至少有 `5` 篇是被 pipeline 錯殺

### 2. 這 5 篇 gold-positive missing_fulltext

目前對應到的 key 是：

- `agarwal:etal:2025`
- `Warstadt:etal:2020`
- `jumelet:etal:2025`
- `Tenney:etal:2019b`
- `aoyama:schneider:2022`

### 3. 這些 paper 今天是否公開可得

我在 `2026-03-11` 檢查時，至少以下幾篇明顯是公開可得的：

- `Warstadt:etal:2020`
  - BLiMP on ACL Anthology / TACL:
  - https://aclanthology.org/2020.tacl-1.25

- `agarwal:etal:2025`
  - arXiv abstract:
  - https://arxiv.org/abs/2506.16678
  - ACL Anthology PDF result also exists in search:
  - https://aclanthology.org/2025.emnlp-main.1712.pdf

- `jumelet:etal:2025`
  - arXiv:
  - https://arxiv.org/abs/2504.02768

- `aoyama:schneider:2022`
  - ACL Anthology:
  - https://aclanthology.org/2022.naacl-srw.25/

- `Tenney:etal:2019b`
  - dblp points to open electronic edition / OpenReview:
  - https://dblp.org/rec/conf/iclr/TenneyXCWPMKDBD19

### 4. 這代表什麼

這代表至少在目前查到的 gold-positive missing_fulltext cases 裡：

- 我看不到「這篇本來就應該因找不到全文而 exclude」的證據
- 反而看到的是「今天其實公開可得，但 pipeline 沒抓到」

所以 taxonomy 5 不能簡化成：

- `找不到 -> 本來就該 exclude`

更準確的說法是：

- `找不到` 這件事，混有兩種情況
  - 真正難以取得
  - pipeline matching / download / path resolution 失敗

而在這批資料裡，至少那 `5` 個 gold-positive 例子，後者是主嫌。

### 5. 有沒有「真的手動也拿不到、而且剛好 gold-positive」的個位數篇？

以我這次檢查到的 `5` 個 gold-positive missing_fulltext 來看：

- 我沒有看到明確屬於「今天手動也拿不到」的案例

也就是說，在這個已確認的子集合裡，我目前傾向判定：

- `0` 篇明確是「我手動也拿不到」
- `5` 篇更像是 pipeline failure

但我要保留一個技術上的 caveat：

- 我這裡驗證的是公開可得性，不是逐篇手動實際完成下載、清洗、轉成你 pipeline 需要的 md 格式
- 所以我能很有把握地說「不是本來就該 exclude」
- 但若要說「所有都能無摩擦地餵進現有 pipeline」，那還需要另做逐篇取檔驗證

### 6. 我對 Q5 的結論

- 不是，找不到全文不等於本來就應該 exclude
- 在你目前的結果裡，確實有個位數篇 `gold-positive` 被 `missing_fulltext` 錯殺
- 而且我查到的這幾篇大多其實今天公開可得，因此比較像：
  - URL / venue matching
  - downloader coverage
  - local fulltext resolution
  的問題

## Final Take

把 5.6 的五種 taxonomy 對應回根因，我會這樣總結：

1. `Topic framing 被誤當硬 criteria`
   - 主要是 `criteria serialization + generic runtime prompt`

2. `缺少正面證據` 被誤當 `排除證據`
   - 主要是 `Stage 1 reviewer policy` 問題，不是 criteria 主體錯

3. `operational definition 太窄`
   - 主要是 criteria 邊界沒有寫清楚

4. `disagreement arbitration 過於保守`
   - 主要是 aggregation / senior override 設計

5. `pipeline / retrieval failure`
   - 不是天然等於 exclude
   - 目前有少數 gold-positive 被這個問題錯殺
