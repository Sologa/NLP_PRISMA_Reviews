# NLP PRISMA Screening Current Status Handoff

Date: 2026-03-13

## 1. 這份 handoff 的目的

這份文件是給外部 ChatGPT / GPT-5.4-pro 之類模型閱讀的最新狀態交接。

重點不是重述整個專案背景，而是把目前已經驗證過的結論、各輪實驗的作用、最新可用分數、以及真正還值得做的下一步，整理成一份可直接承接的工作備忘錄。

---

## 2. 專案目前已經大致確定的事情

### 2.1 runtime prompt 與原始 template 的關係

一開始 repo 內有 markdown prompt templates，但 runtime 並沒有真正直接用它們。

後來已經做了 runtime prompt externalization，現在 runtime prompt 已外移為：

- `scripts/screening/runtime_prompts/runtime_prompts.json`

而且已做過 equivalence check，確認 externalization 本身不是主要 confound。

### 2.2 Stage 1 流程原則目前固定

目前已經收斂的 Stage 1 原則是：

- 兩位 junior 都 `>= 4`：直接 `include`
- 兩位 junior 都 `<= 2`：直接 `exclude`
- 其他情況：送 `SeniorLead`

並且：

- `SeniorLead` 必須保留
- `SeniorLead` 一旦介入，可單點裁決
- marker heuristic 已刪除，不再回頭使用

### 2.3 已知不值得再追的方向

下列方向已經基本驗證過，不值得再花主力：

1. 追求一個全域更好的 `SeniorLead` strict prompt
2. 重新引入 marker heuristic
3. 再做一輪純 global prompt tuning 想一次解四篇

原因是：

- `senior_prompt_tuned` 確實能改善 `2409`、部分改善 `2511`
- 但會明顯傷到 `2601`
- `frozen-input SeniorLead replay` 已證明這不是主要由 junior rerun noise 造成

也就是說：

- `SeniorLead` prompt effect 是真的
- 但這個 effect 明顯是 review-specific，不能用單一全域 prompt 解掉

---

## 3. 已完成的重要實驗與結論

### 3.1 prompt-only runtime realignment

目的：

- 驗證 runtime reviewer prompt 往 template 精神靠攏後，是否能改善結果

結論：

- 有改善，但不是根治
- 主要只是證明 prompt drift 的確是問題之一

對應文件：

- `docs/prompt_only_runtime_realignment_report.md`

### 3.2 stage1 recall redesign / senior adjudication / no-marker

目的：

- 測試 Stage 1 recall-first 改法
- 保留 `SeniorLead`
- 移除 marker heuristic
- 找出更像人工流程的 Stage 1 aggregation

結論：

- `SeniorLead` 必須保留
- `double-high include / double-low exclude / else senior` 是可 defend 的流程版本
- marker heuristic 應刪除

對應文件：

- `docs/stage1_recall_redesign_report.md`
- `docs/stage1_senior_adjudication_redesign_report.md`
- `docs/stage1_senior_no_marker_report.md`

### 3.3 strict `SeniorLead` prompt tuning

目的：

- 壓縮 `maybe`
- 對 topic-adjacent paper 更嚴格

結論：

- 幫到 `2409`
- 部分幫到 `2511`
- 但嚴重傷到 `2601`

對應文件：

- `docs/stage1_senior_prompt_tuning_report.md`

### 3.4 frozen-input SeniorLead replay

目的：

- 固定 junior outputs 與 sent-to-senior case 集合
- 只比較不同 `SeniorLead` prompt 的 effect

結論：

- `SeniorLead` prompt effect 是真的，不主要是 rerun noise
- `senior_prompt_tuned` 對 `2409` / `2511` 的 precision 幫助在 frozen-input 下仍存在
- `senior_prompt_tuned` 對 `2601` recall 的傷害在 frozen-input 下也仍存在

這份實驗的研究意義非常高，因為它把「SeniorLead prompt 是真效果還是噪音」這件事講清楚了。

對應文件：

- `docs/frozen_senior_replay_report.md`

### 3.5 `2511` criteria operationalization v2

目的：

- 驗證 `2511` 的主問題是不是 criteria boundary / operationalization

做法：

- 只改 `criteria_jsons/2511.13936.json`
- 不改 pipeline / prompt / senior / aggregation

結論：

- 這一輪非常成功
- 只改 criteria，就能同時提升 precision 與 recall
- 因此 `2511` 的主問題確實是 criteria operationalization，而不是 senior prompt

對應文件：

- `docs/criteria_2511_operationalization_v2_report.md`

### 3.6 `2409` criteria stage split

目的：

- 驗證 `2409` 是否存在 Stage 1 / Stage 2 criteria 混層

做法：

- 只改 `criteria_jsons/2409.13738.json`
- 把 criteria wording 明確區分為：
  - Stage 1 observable
  - Stage 2 confirmatory

結論：

- 這一輪有效
- precision 明顯改善
- recall 無損
- 但仍有殘餘 hard FP

重要 caveat：

- 這不是 pipeline-level 的真正 stage split
- 而是 criteria wording 上的 stage-aware projection
- pipeline 目前並不真正 hard-consume `stage_projection` 欄位

對應文件：

- `docs/criteria_2409_stage_split_report.md`

---

## 4. 目前四篇 SR 最新可視為「現行狀態」的分數

口徑：

- `2409`、`2511` 使用各自最新 criteria surgery 結果
- `2307`、`2601` 目前仍以 `senior_no_marker` 代表現行穩定版本

### 4.1 `2307.05527`

Stage 1:

- precision `0.9593`
- recall `0.9649`
- f1 `0.9621`
- `tp=165 fp=7 tn=40 fn=6`

Combined:

- precision `0.9816`
- recall `0.9357`
- f1 `0.9581`
- `tp=160 fp=3 tn=44 fn=11`

### 4.2 `2409.13738`

使用：`criteria_2409_stage_split`

Stage 1:

- precision `0.5250`
- recall `1.0000`
- f1 `0.6885`
- `tp=21 fp=19 tn=38 fn=0`

Combined:

- precision `0.6364`
- recall `1.0000`
- f1 `0.7778`
- `tp=21 fp=12 tn=45 fn=0`

### 4.3 `2511.13936`

使用：`criteria_2511_opv2`

Stage 1:

- precision `0.8056`
- recall `0.9667`
- f1 `0.8788`
- `tp=29 fp=7 tn=47 fn=1`

Combined:

- precision `0.8788`
- recall `0.9667`
- f1 `0.9206`
- `tp=29 fp=4 tn=50 fn=1`

### 4.4 `2601.19926`

Stage 1:

- precision `0.9735`
- recall `0.9851`
- f1 `0.9792`
- `tp=330 fp=9 tn=14 fn=5`

Combined:

- precision `0.9676`
- recall `0.9791`
- f1 `0.9733`
- `tp=328 fp=11 tn=12 fn=7`

---

## 5. 用白話講，目前系統還剩什麼要修

### 5.1 `2307`

大致已經不是主戰場。

白話講：

- 整體已經很強
- 還有少數 final FN
- 但目前不值得優先大動

### 5.2 `2409`

這是目前最明顯的瓶頸。

白話講：

- 它還是會把很多「看起來跟流程 / BPM / LLM / NLP 很有關」的 paper 收進來
- 但那些 paper 不一定真的是 review 要的 `text -> process representation extraction`

也就是：

- 它還是太容易把「沾邊」當成「核心符合」

目前已經修掉的是：

- Stage 1 / Stage 2 混層的一部分

目前還沒完全修掉的是：

- core target object boundary
- process-adjacent 與 true text-to-process extraction 的語義邊界

### 5.3 `2511`

這篇現在已經大致修好了。

白話講：

- 原本最大問題是 criteria 沒把邊界講清楚
- 現在把 audio-domain、preference-signal、learning-role、negative overrides 寫清楚後，結果就明顯變好

剩下的是：

- 少數高爭議 boundary case
- 不再是廣泛的 criteria 模糊

### 5.4 `2601`

這篇現在很強，不應亂動。

白話講：

- 很多真陽性本來就摘要弱、metadata 薄
- 只要把 senior prompt 調太嚴，它就會壞

所以這篇的策略不是再變嚴，而是：

- 不要讓全域 strict senior 再傷到它

---

## 6. 現在最值得做的事

### 6.1 第一優先：`2409` 再做一輪 criteria boundary cleanup

方向不是再改 senior，也不是再改 global prompt，而是：

- 只針對 `2409` 剩下的 hard FP
- 再補一輪更硬的 target-object boundary

重點是把以下邊界寫得更可操作：

- 談 process / BPM 不等於 text-to-process extraction
- generic LLM for BPM 不等於 process representation extraction
- process-adjacent task 不等於 core extraction object

### 6.2 `2511` 可以暫時停止大改

除非要專門追那 1 個殘餘 FN，否則目前不值得再大動。

### 6.3 `2307`、`2601` 暫時不要動

這兩篇現在不是瓶頸，尤其 `2601` 很容易被修壞。

---

## 7. 建議 ChatGPT 接下來優先回答的問題

如果你是外部模型，最值得先回答的是：

1. 針對 `2409` 剩餘 hard FP，應該如何進一步 sharpen target-object boundary？
2. 目前 `2409` criteria wording 中，哪些句子仍太容易讓 reviewer把 topic-adjacent paper 納入？
3. 如果不改 pipeline，只改 `2409` criteria，下一輪最有希望補的 negative overrides 是哪些？
4. 目前 `2511` 是否已經可以視為「主要問題已解決」，只剩少數 boundary policy issue？
5. `2307` 與 `2601` 是否應保持現狀，避免 global prompt / policy 調整造成退步？

---

## 8. 建議外部模型優先閱讀的檔案順序

1. `docs/nlp_prisma_screening_diagnosis_report.md`
2. `docs/frozen_senior_replay_report.md`
3. `docs/criteria_2511_operationalization_v2_report.md`
4. `docs/criteria_2409_stage_split_report.md`
5. `criteria_jsons/2511.13936.json`
6. `criteria_jsons/2409.13738.json`
7. `scripts/screening/runtime_prompts/runtime_prompts.json`
8. `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

---

## 9. 最後一句話版結論

目前系統層面的主要問題已經大致釐清：

- 不要再追 global SeniorLead tuning
- `2511` 主要靠 criteria surgery 已大致修好
- `2409` 仍是目前最值得處理的 paper，而且剩餘問題主要是 target-object boundary，不是再改全域流程

