請全程使用中文回答。

我會讓你直接讀 GitHub 上這個 repo 的內容。請你不要泛泛而談，而是先依照我指定的閱讀順序，理解目前這個 systematic review screening pipeline 的實驗進度，再回答我接下來的問題。

## 你的任務

請先閱讀以下檔案，並以這些檔案為主要依據做分析：

1. `docs/chatgpt_current_status_handoff.md`
2. `docs/nlp_prisma_screening_diagnosis_report.md`
3. `docs/frozen_senior_replay_report.md`
4. `docs/criteria_2511_operationalization_v2_report.md`
5. `docs/criteria_2409_stage_split_report.md`
6. `criteria_jsons/2511.13936.json`
7. `criteria_jsons/2409.13738.json`
8. `scripts/screening/runtime_prompts/runtime_prompts.json`
9. `scripts/screening/vendor/src/pipelines/topic_pipeline.py`

## 背景重點

你必須先理解以下已知事實：

1. 這個專案已經做過多輪 prompt / senior / replay / criteria 實驗。
2. `SeniorLead` 必須保留，而且一旦介入，可單點裁決。
3. 目前 Stage 1 流程原則已固定為：
   - 兩位 junior 都 `>=4`：直接 include
   - 兩位 junior 都 `<=2`：直接 exclude
   - 其他：送 `SeniorLead`
4. marker heuristic 已刪除，不再是候選方向。
5. `frozen-input SeniorLead replay` 已驗證：
   - `SeniorLead` prompt effect 是真的
   - 但不存在一個對四篇都好的全域 strict senior prompt
6. `2511` 已透過 criteria operationalization v2 明顯改善，說明其主問題確實是 criteria boundary。
7. `2409` 也透過 criteria stage split 得到改善，但仍有 hard FP，代表剩餘問題更像 target-object boundary，而不是單純 senior calibration。

## 你要回答的問題

請在完整閱讀後，用中文詳細回答以下問題：

1. 你是否同意目前的總判斷：系統層面的大方向已大致收斂，現在主戰場主要是 `2409` 的 criteria boundary，而不是再追 global senior prompt？
2. `2409` 目前剩下的 hard FP，最可能是哪幾類語義邊界沒有寫硬？
3. 如果堅持「不改 pipeline、不改 senior、不改 aggregation」，只再改一輪 `2409` criteria，你會怎麼改？
4. 你會如何重寫 `2409` 的 negative overrides，讓它更能擋住：
   - generic BPM / process / LLM papers
   - process-adjacent but not text-to-process extraction papers
5. 你是否同意 `2511` 現在已經大致修好，可以先停止大改？
6. `2307` 與 `2601` 是否應維持現狀，不要再因全域策略調整而冒退步風險？

## 回答要求

請不要只講抽象建議。請你：

1. 明確引用你閱讀到的檔案與實驗結論
2. 分開講：
   - 你同意的部分
   - 你不同意或要保留的部分
3. 對 `2409` 提出具體、可落地的 criteria wording 修改方向
4. 最後給我一個明確的 next-step proposal

## 額外要求

如果你認為應該再開一輪實驗，請明確說：

1. 那一輪只應改什麼
2. 不應改什麼
3. 成功標準是什麼

不要泛泛說「可以再優化」。請具體。

