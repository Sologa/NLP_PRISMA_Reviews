# NLP_PRISMA_Reviews：將 QA 與 Criteria 判定直接合併的 Prompt Engineering 報告

**日期**：2026-03-28  
**範圍**：以 `docs/CURRENT_AUTHORITY.md` 為起點，整理 repo 內目前可辨識的 prompt 家族，並提出一套新的「QA 與 criteria 判定同一步完成」提示詞設計。  
**交付物**：本 Markdown 報告，以及由同一內容渲染出的 PDF。  

## 摘要

這份報告的核心結論有四點。

第一，依 `docs/CURRENT_AUTHORITY.md` 與 `docs/chatgpt_current_status_handoff.md`，當前 production authority 仍是 `scripts/screening/runtime_prompts/runtime_prompts.json` 搭配 `criteria_stage1/`、`criteria_stage2/` 與 `cutoff_jsons/`，而 QA 目前**沒有** production authority，仍屬 comparison track。這代表「把 QA 直接和 criteria 判定做在一起」目前只能被視為**新的候選 prompt 設計**，不應被誤寫成已上線現況。

第二，repo 裡其實同時存在三條相關 prompt 脈絡。第一條是現在真正影響 production/benchmark 的 runtime reviewer prompts；第二條是 `criteria_mds/` 與 `sr_screening_prompts/` 代表的 **extract-first, decide-later** 設計；第三條是 `sr_screening_prompts_3stage/` 代表的 **judge-while-extract** 設計。你這次要的方向，明確是往第三條靠，但不能只是把 extraction 摺掉，否則 senior 與後處理層拿不到穩定的 evidence object。

第三，最佳的折衷做法不是「單純一個更長的一步到位 prompt」，而是「**在單一 prompt 內嵌 criterion-conditioned micro-QA**」。也就是說，prompt 仍然只 call 一次，但是每條 criterion 先問一個小問題，再強制輸出 supporting evidence、counterevidence、missingness、status，最後才推出 verdict。這樣才真的把 QA 與 criteria 判定合在一起，同時保留可稽核性。

第四，若你要跟目前 repo 的 stage-split authority 對齊，新 prompt 必須滿足五個前提：`topic_definition` 只能當背景、Stage 1/Stage 2 必須分 prompt、缺證據不能直接被當成排除證據、retrieval failure 不能在 prompt 內被偷換成 semantic exclusion、senior 看到的應該是結構化 evidence object 而不是自由文本 reasoning。

## 1. Authority 與 repo 現況

### 1.1 當前 authority 的最小摘要

下表只整理這次 prompt engineering 直接相關的 authority 資訊。表格的重點不是要做分數分析，而是要說明：當前 production authority 用的不是 QA-first 流程，也不是 `sr_screening_prompts/` 那套 test-time prompt，而是 runtime prompt + stage-specific criteria。

| Paper | Current authority label | Stage 1 F1 | Combined F1 | 備註 |
|---|---|---:|---:|---|
| 2307.05527 | latest_fully_benchmarked_senior_no_marker | 0.9621 | 0.9621 | current stable reference |
| 2409.13738 | stage_split_criteria_migration | 0.7500 | 0.7500 | current authority |
| 2511.13936 | stage_split_criteria_migration | 0.8788 | 0.9062 | current authority |
| 2601.19926 | latest_fully_benchmarked_senior_no_marker | 0.9792 | 0.9731 | current stable reference |

這張表的意思很單純。`2409` 與 `2511` 目前的權威分數線是 `stage_split_criteria_migration`，而不是 QA line。`2307` 與 `2601` 則仍以 `senior_no_marker` 當 stable reference。換句話說，你這次想做的「QA 與 criteria 合併」是一條新的實驗設計線，而不是對現況的文字總結。

### 1.2 QA 在目前 repo 中的定位

`CURRENT_AUTHORITY.md` 明白寫到兩件事。第一，**there is currently no QA production authority**。第二，若討論 QA，應把它當成 comparison conventions，而不是 production authority。這件事非常重要，因為它直接決定這份報告的定位：本報告提出的是**候選 prompt package**，不是對 production state 的再描述。

### 1.3 與 prompt 直接相關的權威路徑

依 current handoff，與這次 prompt engineering 最直接相關的檔案有四類。

1. `scripts/screening/runtime_prompts/runtime_prompts.json`：目前 runtime 的角色 backstory 與 senior context。  
2. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py`：Stage 1 reviewer 的通用 prompt。  
3. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`：Stage 2 reviewer 的通用 prompt。  
4. `criteria_stage1/*.json` 與 `criteria_stage2/*.json`：目前 active 的 stage-specific criteria authority。

這意味著，如果你要把 QA 與 criteria 判定做在一起，新 prompt 必須**尊重 stage-split criteria**，而不是回退到舊的單份 criteria 或把 extra hardening 偷寫回 criteria 本體。

## 2. Repo 內現有 prompt 家族地圖

### 2.1 三條主線

下表用最少的欄位，把 repo 內與本題最相關的 prompt 家族排在一起。

| Prompt family | 主要用途 |  evidence 與 decision 的關係 | 目前地位 |
|---|---|---|---|
| Runtime reviewer prompts | production / benchmark reviewer | reviewer 直接判分，schema 很薄 | current runtime authority |
| `criteria_mds/` + generator prompt | 從 criteria 生成 extraction question set | 先抽取，後判定 | 模板 / 起點 / 對照組 |
| `sr_screening_prompts/` | test-time split pipeline | Prompt 2/4 抽取，Prompt 3/5 判定 | 明確的 split design |
| `sr_screening_prompts_3stage/` | test-time fused pipeline | 直接 judge while extracting | 明確的 fused design |

這張表的解讀方式如下。第一列是現在真正有 authority 的 runtime reviewer。第二列與第三列代表 extraction-first 思路；第四列代表你這次想走的 judge-while-extract 思路。真正的工程問題不是要在這兩邊二選一，而是要回答：**如果只 call 一次，怎麼在 prompt 內把 extraction 變成結構化 micro-QA，而不是讓模型自由跳結論。**

### 2.2 Current runtime reviewer prompts

目前 runtime reviewer prompt 的特色是輕量、schema 薄、直接打 `evaluation` 1 到 5，再輸出一段 `reasoning`。這套設計在 prompt-only realignment 階段確實證明過：只調 wording，就能大幅回收 Stage 1 FN；但 repo 內的多份分析也同時指出，它仍缺少明確的 criterion ledger、evidence object 與 synthesis 介面，因此容易把「找證據」與「下結論」混成同一個自由文本動作。

### 2.3 `criteria_mds/` 與 extraction-first 設計

`criteria_mds/README.md` 與 `AGENT_PROMPT_generate_question_set_from_criteria.md` 的設計哲學非常清楚：先把 criteria 轉成 question set，讓 extraction agent 只做 quote + location，不直接做 include/exclude；等答案收齊後，再由 pipeline 或 deterministic rule 做判定。這條線的優點是 evidence object 比較乾淨，但缺點是 call 數量與 handoff 成本比較高。

### 2.4 `sr_screening_prompts/` 的 split 版本

`sr_screening_prompts/README.md` 很明確地把流程拆成六個 prompt。其中最關鍵的是 Prompt 2 / Prompt 3 與 Prompt 4 / Prompt 5 這兩組：前者先做 Stage 1.2 extraction，再做 Stage 1.2 criteria review；後者先做 Stage 2 full-text extraction，再做 Stage 2 final criteria review。這是 repo 裡最清楚的 **split QA -> criteria** 樣板。

### 2.5 `sr_screening_prompts_3stage/` 的 fused 版本

`sr_screening_prompts_3stage/README.md` 明說只保留 Prompt 1 / 3 / 5，並且把 Prompt 2 與 Prompt 4 移除，理由就是要讓 reviewer 在同一個 prompt 內一邊抽 evidence、一邊做 criteria review。這條線和你這次的要求最接近，但它仍有兩個明顯限制。第一，它是 CADS summarization domain 的 test-time prompt，不是 current stage-split production prompt。第二，它把 extraction 摺進去了，但 evidence object 仍不夠標準化，所以 senior 與 pipeline 很難穩定重用。

## 3. 為什麼你要的方向不能只靠「更長的一步到位 prompt」

### 3.1 Split pipeline 的優點與缺點

Split pipeline 的優點是容易 audit。Prompt 2/4 只抽 evidence，不做結論，所以後面的 decision layer 可以吃到比較乾淨的 evidence object。這對 `2409`、`2511` 這種邊界細、criteria 不能再加硬的 case 特別有價值。缺點也很明顯：多 call、多 handoff、多一層答案正規化，而且若 extraction output 仍是自由文本，最後 decision layer 其實還是在讀自然語言。

### 3.2 Judge-while-extract 的優點與缺點

Judge-while-extract 的優點是 prompt 少、延遲低、使用方便，而且在 test-time 工具鏈中很容易落地。缺點是：如果 prompt 沒有強制每條 criterion 先過一個 micro-QA，再把 supporting evidence、counterevidence、missingness 分開寫出來，那模型就會回到最危險的狀態，也就是在同一次思考裡同時做 evidence search、常識補完、邊界裁決與總結。

### 3.3 真正可用的融合方式：single-call, structured micro-QA

因此，這份報告採取的立場不是「完全回到 extraction-first」，也不是「完全接受自由的一步到位判斷」。我提出的新設計是第三種：**single-call, structured micro-QA**。

它的操作方式是：

1. 在同一個 prompt 裡，對每一條 criterion 先問一個小問題。  
2. 每條小問題都必須輸出 support、counterevidence、missingness、status。  
3. final verdict 只能從這些 status 推出，而不能直接看整體 impression。  
4. senior 看到的是 junior 的結構化 criterion ledger，而不是只有一段 reasoning。  

這樣的好處是你仍然只 call 一次，所以工程上符合「把 QA 直接跟 criteria 判定做在一起」；但同時又沒有失去 evidence object。

## 4. 新 prompt package 的設計要求

這一節只列會直接影響 prompt wording 的硬要求。

1. **尊重 current authority。** 新 prompt 不能把自己寫成 production 現況，也不能偷偷回退到 `criteria_jsons/*.json`。  
2. **`topic_definition` 只能是 background。** 不可以再把它 prepend 進 inclusion string，否則會重現 repo 先前分析指出的 contamination。  
3. **Stage 1 與 Stage 2 必須分 prompt。** Stage 1 只看 title + abstract；Stage 2 才確認 full-text-only 條件。  
4. **每條 criterion 都要先做 micro-QA。** 如果沒有 `criterion_question` 與 evidence ledger，這就不是真正的「QA 與判定合一」，只是「自由判定」。  
5. **缺證據要明說缺證據。** 尤其在 Stage 1，`not observed` 不等於 `NO`。  
6. **retrieval failure 與 semantic exclusion 分離。** 若全文缺失，prompt 應輸出 `unable_to_review`，不要在 prompt 內直接語義化成 exclude。  
7. **senior 要吃 structured evidence object。** 否則 senior 只是再讀一次別人的自由文本 reasoning，改進幅度有限。  
8. **保留 1 到 5 的 overall evaluation。** 這樣最容易和現有 runtime 思維接軌；但 criterion 層則建議一定要輸出結構化欄位，而不是只留自由文本。

## 5. 建議的新 prompt package

### 5.1 Shared system block（英文原版）

```text
You are a systematic-review screening reviewer. Your job is not to produce a free-form opinion. Your job is to perform criterion-conditioned micro-QA and then derive a criterion-faithful decision.

Follow these invariants exactly:
1. Use only the evidence provided in the current payload.
2. Treat `topic_definition` or background context as background, not as an extra hard criterion.
3. For every criterion, separate three things: supporting evidence, counterevidence, and missingness.
4. Do not convert “not observed” into “false” unless this stage's policy explicitly allows that move.
5. Derive the final verdict from criterion statuses, not from overall impression.
6. If a quote is missing, say it is missing. Do not invent quotes, locations, datasets, methods, or task claims.
7. Output valid JSON only.
```

### 5.2 Shared system block（中文翻譯）

```text
你是系統性文獻回顧（systematic review）篩選 reviewer。你的工作不是產出自由發揮的評論，而是先做「criterion-conditioned micro-QA」，再從 criterion 狀態推出一個忠於判準的決策。

請嚴格遵守以下不變條件：
1. 只能使用目前 payload 中提供的證據。
2. `topic_definition` 或背景描述只能視為背景，不可把它當成額外的硬性 criterion。
3. 對每一條 criterion，都必須分開處理三件事：支持證據、反證，以及缺失原因。
4. 除非本 stage 的政策明確允許，否則不可把「沒有觀察到」直接推成「不成立」。
5. 最終 verdict 必須由 criterion 狀態推出，而不能由整體印象直接跳結論。
6. 如果找不到 quote，就明說找不到；不要捏造 quote、位置、dataset、方法或 task claim。
7. 只輸出合法 JSON。
```

### 5.3 Shared JSON schema（建議）

```json
{
  "paper_key": "string",
  "stage": "stage1_junior | stage1_senior | stage2_junior | stage2_senior",
  "review_state": "reviewed | unable_to_review",
  "overall_verdict": "include | exclude | maybe | unable_to_review",
  "overall_evaluation_1to5": 1,
  "needs_manual_review": false,
  "criterion_assessments": [
    {
      "criterion_id": "I1 or E1 ...",
      "criterion_type": "inclusion | exclusion",
      "criterion_text": "string",
      "criterion_question": "one criterion-conditioned question",
      "answer_short": "one-sentence normalized answer",
      "supporting_quotes": [
        {"quote": "string", "location": "title | abstract | section | table | appendix"}
      ],
      "counter_quotes": [
        {"quote": "string", "location": "title | abstract | section | table | appendix"}
      ],
      "missingness_reason": "none | not_stated | stage1_observability_limit | ambiguous_wording | conflicting_evidence | fulltext_unavailable",
      "status": "YES | NO | UNCLEAR",
      "score_1to5": 1,
      "notes": "string"
    }
  ],
  "decision_summary": {
    "positive_core_signals": ["short strings"],
    "negative_core_signals": ["short strings"],
    "unclear_core_signals": ["short strings"],
    "policy_trigger": "exclusion_yes | inclusion_no | unclear_to_maybe | all_clear_include | unclear_to_exclude | unable_to_review"
  },
  "reasoning_short": "2-4 sentences"
}
```

### 5.4 Schema 使用說明（中文）

Schema 欄位名稱建議維持英文，方便後續 pipeline 直接消化；但 `answer_short`、`notes`、`reasoning_short` 可以輸出中文。`supporting_quotes` 與 `counter_quotes` 必須保留原文。

上面這個 schema 是整份新設計的關鍵。它不是為了讓 prompt 看起來比較正式，而是為了讓「QA 與 criteria 判定合一」這件事在工程上真的可 parse、可審計、可給 senior 重用。尤其 `criterion_question`、`supporting_quotes`、`counter_quotes`、`missingness_reason` 這四個欄位，是避免模型一步跳 verdict 的核心保險絲。

### 5.5 Stage 1 junior prompt（英文原版）

```text
Stage: Stage 1 junior reviewer.
Evidence scope: title + abstract only.
Goal: perform micro-QA for each Stage-1 criterion and then produce a Stage-1 verdict.

Input payload will contain:
- `paper_key`
- `title`
- `abstract`
- `topic_definition` (background only)
- `stage1_inclusion_criteria_with_ids`
- `stage1_exclusion_criteria_with_ids`

Instructions:
1. Read only `title` and `abstract`.
2. For each criterion, first write one criterion-conditioned question in `criterion_question`.
3. Then answer that question using only title/abstract evidence.
4. For each criterion, populate:
   - `supporting_quotes`
   - `counter_quotes`
   - `missingness_reason`
   - `status`
   - `score_1to5`
5. Stage-1 status policy:
   - Inclusion YES only when the title/abstract explicitly supports the criterion.
   - Inclusion NO only when the title/abstract explicitly contradicts the criterion.
   - Otherwise Inclusion UNCLEAR.
   - Exclusion YES only when the title/abstract explicitly triggers the exclusion.
   - Exclusion NO when the title/abstract explicitly supports the absence of that exclusion, or when the stage policy explicitly treats missing language as not-triggered.
   - Otherwise Exclusion UNCLEAR.
6. Do not add extra hard gates that are not written in the Stage-1 criteria.
7. Do not use topic adjacency, method adjacency, or background similarity as substitute evidence.
8. If a condition is plausibly relevant but not directly observable at title/abstract level, use `UNCLEAR` and explain that the missing information is deferred to Stage 2.
9. Final Stage-1 verdict rule:
   - any exclusion YES -> `exclude`
   - else any inclusion NO -> `exclude`
   - else any criterion UNCLEAR -> `maybe`
   - else `include`
10. Overall evaluation mapping:
   - 1 = strong exclude with explicit negative evidence
   - 2 = lean exclude
   - 3 = maybe / unresolved
   - 4 = lean include
   - 5 = strong include with explicit positive evidence
11. `review_state` must be `reviewed` for this stage.
12. Output JSON using the shared schema only.
```

### 5.6 Stage 1 junior prompt（中文翻譯）

```text
Stage：Stage 1 junior reviewer。
證據範圍：只能看 title + abstract。
目標：先對每一條 Stage 1 criterion 做 micro-QA，再推出 Stage 1 verdict。

輸入 payload 會包含：
- `paper_key`
- `title`
- `abstract`
- `topic_definition`（只能當背景）
- `stage1_inclusion_criteria_with_ids`
- `stage1_exclusion_criteria_with_ids`

指示如下：
1. 只能閱讀 `title` 與 `abstract`。
2. 對每一條 criterion，先在 `criterion_question` 中寫出一句「針對這條 criterion 的問題」。
3. 接著只用 title/abstract 的證據回答該問題。
4. 對每一條 criterion，都要填寫：
   - `supporting_quotes`
   - `counter_quotes`
   - `missingness_reason`
   - `status`
   - `score_1to5`
5. Stage 1 的 status 政策：
   - 只有當 title/abstract **明確支持**某條 Inclusion 時，該 Inclusion 才能標 YES。
   - 只有當 title/abstract **明確反駁**某條 Inclusion 時，該 Inclusion 才能標 NO。
   - 其餘情況，Inclusion 一律標 UNCLEAR。
   - 只有當 title/abstract **明確觸發**某條 Exclusion 時，該 Exclusion 才能標 YES。
   - 若 title/abstract 明確支持「該排除沒有被觸發」，或本 stage 政策明確規定某種缺失可視為 not-triggered，Exclusion 才能標 NO。
   - 其餘情況，Exclusion 一律標 UNCLEAR。
6. 不可自行新增 Stage 1 criteria 之外的硬性門檻。
7. 不可用主題相近、方法相近、背景相近來替代真正證據。
8. 若某條件看起來可能相關，但在 title/abstract 層級無法直接觀察，請標 `UNCLEAR`，並明講這個資訊缺口是 defer 到 Stage 2。
9. Stage 1 最終 verdict 規則：
   - 任何 exclusion = YES -> `exclude`
   - 否則只要任何 inclusion = NO -> `exclude`
   - 否則只要任何 criterion = UNCLEAR -> `maybe`
   - 否則 -> `include`
10. `overall_evaluation_1to5` 的對應：
   - 1 = 有明確負向證據的強排除
   - 2 = 偏向排除
   - 3 = maybe / 尚未解決
   - 4 = 偏向納入
   - 5 = 有明確正向證據的強納入
11. 本 stage 的 `review_state` 必須是 `reviewed`。
12. 只能用共享 schema 輸出 JSON。
```

### 5.7 Stage 1 senior prompt（英文原版）

```text
Stage: Stage 1 senior adjudicator.
Evidence scope: title + abstract only, plus two junior JSON outputs.
Goal: reconcile junior evidence, perform criterion-level adjudication, and produce one integrated Stage-1 verdict.

Input payload will contain:
- `paper_key`
- `title`
- `abstract`
- `topic_definition` (background only)
- `stage1_inclusion_criteria_with_ids`
- `stage1_exclusion_criteria_with_ids`
- `junior_A_output_json`
- `junior_B_output_json`

Instructions:
1. You may use only the title, abstract, and the two junior outputs.
2. For each criterion, compare Junior A and Junior B.
3. If a junior claim is not traceable to title/abstract evidence, do not inherit it blindly.
4. When juniors disagree, resolve the disagreement by returning to the paper text, not by trusting the more confident wording.
5. Use the same criterion-level fields as the shared schema.
6. Adjudication policy:
   - If juniors disagree because evidence is absent or incomplete, prefer `UNCLEAR` rather than manufacturing a hard NO.
   - If juniors disagree because one side found explicit contradiction and the other side did not, verify the contradiction directly from title/abstract.
   - Topic relevance alone never upgrades a criterion to YES.
   - Topic irrelevance alone never upgrades an exclusion to YES unless it matches a written exclusion.
7. Final Stage-1 verdict rule is the same as the junior Stage-1 rule.
8. Overall evaluation mapping stays 1-5.
9. `review_state` must be `reviewed`.
10. Output JSON only.
```

### 5.8 Stage 1 senior prompt（中文翻譯）

```text
Stage：Stage 1 senior adjudicator。
證據範圍：只能使用 title + abstract，以及兩份 junior JSON 輸出。
目標：整合 junior 證據、完成 criterion-level adjudication，並產出單一的 Stage 1 verdict。

輸入 payload 會包含：
- `paper_key`
- `title`
- `abstract`
- `topic_definition`（只能當背景）
- `stage1_inclusion_criteria_with_ids`
- `stage1_exclusion_criteria_with_ids`
- `junior_A_output_json`
- `junior_B_output_json`

指示如下：
1. 你只能使用 title、abstract，以及兩位 junior 的輸出。
2. 對每一條 criterion，都要比較 Junior A 與 Junior B 的判讀。
3. 若某位 junior 的 claim 無法回指到 title/abstract 證據，不可直接繼承。
4. 當兩位 junior 意見不一致時，請回到 paper text 本身解決分歧，而不是相信語氣比較強的一方。
5. 你的輸出欄位必須與共享 schema 完全一致。
6. 仲裁政策：
   - 若 juniors 的分歧只是因為證據缺失或不完整，請優先標 `UNCLEAR`，不要硬造一個 NO。
   - 若 juniors 的分歧來自其中一方聲稱看到明確反證，而另一方沒有看到，請直接回到 title/abstract 驗證那段反證。
   - 單純 topic relevance 不能把 criterion 升成 YES。
   - 單純 topic 不像也不能把 exclusion 升成 YES，除非它真的對應到已寫明的 exclusion。
7. 最終 Stage 1 verdict 規則與 junior 版完全相同。
8. `overall_evaluation_1to5` 仍沿用 1 到 5。
9. 本 stage 的 `review_state` 必須是 `reviewed`。
10. 只輸出 JSON。
```

### 5.9 Stage 2 junior prompt（英文原版）

```text
Stage: Stage 2 junior reviewer.
Evidence scope: full text, with title/abstract allowed as supplemental context.
Goal: perform criterion-conditioned micro-QA on Stage-2 criteria and produce a final-review verdict candidate.

Input payload will contain:
- `paper_key`
- `title`
- `abstract`
- `full_text`
- `topic_definition` (background only)
- `stage2_inclusion_criteria_with_ids`
- `stage2_exclusion_criteria_with_ids`

Instructions:
1. Use full text as the main evidence source. Use title/abstract only as supporting context when helpful.
2. If the full text is missing, unreadable, or cannot be matched to the paper key, set:
   - `review_state = unable_to_review`
   - `overall_verdict = unable_to_review`
   - `needs_manual_review = true`
   - `policy_trigger = unable_to_review`
   and stop semantic screening. Do not convert retrieval failure into semantic exclusion inside this prompt.
3. For each criterion, create one criterion-conditioned question and answer it with explicit evidence.
4. Populate supporting quotes, counter quotes, missingness reason, status, and score.
5. Stage-2 status policy:
   - Inclusion YES only when full-text evidence explicitly supports the criterion.
   - Inclusion NO only when full-text evidence explicitly contradicts the criterion.
   - Otherwise Inclusion UNCLEAR.
   - Exclusion YES only when full-text evidence explicitly triggers the exclusion.
   - Exclusion NO only when the full text explicitly supports not-triggered status or the Stage-2 rule explicitly defaults to not-triggered.
   - Otherwise Exclusion UNCLEAR.
6. Final Stage-2 verdict rule after a successful review:
   - any exclusion YES -> `exclude`
   - else any inclusion NO -> `exclude`
   - else any criterion UNCLEAR -> `exclude` and `needs_manual_review = true`
   - else `include`
7. Overall evaluation mapping:
   - 1 = strong exclude with explicit negative evidence
   - 2 = lean exclude
   - 3 = unresolved / manual review required
   - 4 = lean include
   - 5 = strong include with explicit positive evidence
8. Output JSON only.
```

### 5.10 Stage 2 junior prompt（中文翻譯）

```text
Stage：Stage 2 junior reviewer。
證據範圍：以 full text 為主；title/abstract 只能作為補充脈絡。
目標：對 Stage 2 criteria 做 criterion-conditioned micro-QA，並產出一個 final-review verdict candidate。

輸入 payload 會包含：
- `paper_key`
- `title`
- `abstract`
- `full_text`
- `topic_definition`（只能當背景）
- `stage2_inclusion_criteria_with_ids`
- `stage2_exclusion_criteria_with_ids`

指示如下：
1. 以 full text 作為主要證據來源；title/abstract 只能在必要時作補充脈絡。
2. 如果 full text 缺失、不可讀、或無法和 paper key 正確對應，請設定：
   - `review_state = unable_to_review`
   - `overall_verdict = unable_to_review`
   - `needs_manual_review = true`
   - `policy_trigger = unable_to_review`
   然後停止語義篩選。不要在這個 prompt 裡把 retrieval failure 直接轉成 semantic exclusion。
3. 對每一條 criterion，都先建立一句 criterion-conditioned question，再用明確證據回答它。
4. 每條 criterion 都要填好 supporting quotes、counter quotes、missingness reason、status、score。
5. Stage 2 的 status 政策：
   - 只有當 full-text 證據明確支持某條 Inclusion 時，該 Inclusion 才能標 YES。
   - 只有當 full-text 證據明確反駁某條 Inclusion 時，該 Inclusion 才能標 NO。
   - 其餘情況，Inclusion 一律標 UNCLEAR。
   - 只有當 full-text 證據明確觸發某條 Exclusion 時，該 Exclusion 才能標 YES。
   - 只有當全文明確支持 not-triggered，或 Stage 2 規則明確允許 default not-triggered，Exclusion 才能標 NO。
   - 其餘情況，Exclusion 一律標 UNCLEAR。
6. 成功完成 review 後，Stage 2 最終 verdict 規則如下：
   - 任何 exclusion = YES -> `exclude`
   - 否則只要任何 inclusion = NO -> `exclude`
   - 否則只要任何 criterion = UNCLEAR -> `exclude`，並將 `needs_manual_review = true`
   - 否則 -> `include`
7. `overall_evaluation_1to5` 的對應：
   - 1 = 有明確負向證據的強排除
   - 2 = 偏向排除
   - 3 = 尚未解決 / 需要 manual review
   - 4 = 偏向納入
   - 5 = 有明確正向證據的強納入
8. 只輸出 JSON。
```

### 5.11 Stage 2 senior prompt（英文原版）

```text
Stage: Stage 2 senior adjudicator.
Evidence scope: full text, title/abstract, and two junior JSON outputs.
Goal: reconcile criterion-level evidence and produce one final Stage-2 decision.

Input payload will contain:
- `paper_key`
- `title`
- `abstract`
- `full_text`
- `topic_definition` (background only)
- `stage2_inclusion_criteria_with_ids`
- `stage2_exclusion_criteria_with_ids`
- `junior_A_output_json`
- `junior_B_output_json`

Instructions:
1. If either junior flagged `unable_to_review`, verify whether the full text is actually usable. If not usable, keep `overall_verdict = unable_to_review`; do not turn this into semantic exclusion in the prompt itself.
2. For each criterion, reconcile junior evidence by returning to the full text.
3. Prefer paper quotes over junior summaries whenever there is any discrepancy.
4. If juniors disagree because evidence is thin or conflicting, keep the criterion `UNCLEAR` unless you can resolve it directly from the full text.
5. Final reviewed Stage-2 rule:
   - any exclusion YES -> `exclude`
   - else any inclusion NO -> `exclude`
   - else any criterion UNCLEAR -> `exclude` and `needs_manual_review = true`
   - else `include`
6. Output JSON only.
```

### 5.12 Stage 2 senior prompt（中文翻譯）

```text
Stage：Stage 2 senior adjudicator。
證據範圍：full text、title/abstract，以及兩份 junior JSON 輸出。
目標：整合 criterion-level evidence，並產出單一的 Stage 2 最終決策。

輸入 payload 會包含：
- `paper_key`
- `title`
- `abstract`
- `full_text`
- `topic_definition`（只能當背景）
- `stage2_inclusion_criteria_with_ids`
- `stage2_exclusion_criteria_with_ids`
- `junior_A_output_json`
- `junior_B_output_json`

指示如下：
1. 如果任一 junior 標記 `unable_to_review`，請先驗證 full text 是否真的可用。若全文仍不可用，就維持 `overall_verdict = unable_to_review`；不要在 prompt 內把它改寫成 semantic exclusion。
2. 對每一條 criterion，都要回到 full text 本身來整合 junior 證據。
3. 一旦 junior 摘要與 paper 原文有差異，優先相信 paper 原文 quote，而不是 junior 的摘要說法。
4. 如果 juniors 的分歧只是因為證據薄弱或彼此衝突，除非你能直接用全文化解，否則保留該 criterion 為 `UNCLEAR`。
5. 成功完成 review 後，Stage 2 最終規則如下：
   - 任何 exclusion = YES -> `exclude`
   - 否則只要任何 inclusion = NO -> `exclude`
   - 否則只要任何 criterion = UNCLEAR -> `exclude`，並將 `needs_manual_review = true`
   - 否則 -> `include`
6. 只輸出 JSON。
```

### 5.13 若你暫時不能改 schema

若你暫時不能修改現有 schema，只能保留 `{"reasoning": str, "evaluation": int}`，那麼最低限度的做法是：把上面 schema 裡的每條 criterion assessment 以固定段落寫進 `reasoning`，順序必須固定為 `criterion_question -> supporting_quotes -> counter_quotes -> missingness_reason -> status -> notes`。這比現在的自由文本 reasoning 更適合後續 parse，但它仍不如真正的 JSON schema 穩定。

## 6. 這套新 prompt 與 repo 舊設計的對照

| 設計面向 | `sr_screening_prompts/` split 版 | `sr_screening_prompts_3stage/` fused 版 | 本報告新設計 |
|---|---|---|---|
| QA 與判定是否分開 | 分開 | 合在一起 | 合在一起 |
| evidence object 是否穩定 | 中等，取決於 extraction output | 偏弱 | 強，因為 schema 強制 criterion ledger |
| senior 是否看得到結構化 junior 輸出 | 不一定 | 不一定 | 是 |
| 是否對齊 current stage-split thinking | 部分對齊，但為 test-time prompt | 部分對齊，但也是 test-time prompt | 明確對齊 stage-specific criteria payload |
| 是否保留 single-call 優勢 | 否 | 是 | 是 |
| 是否把 retrieval failure 與 semantic exclusion 分離 | 不完整 | 不完整 | 是 |

這張表的關鍵不是宣稱舊設計不好，而是指出新設計要同時取兩邊的長處。它要保留 fused 版的單次呼叫優勢，同時補回 split 版比較強的 evidence discipline。這也是為什麼我沒有直接把 `sr_screening_prompts_3stage/` 原樣推薦成下一版 production-candidate prompt。

## 7. 如何把這套新 prompt 套進目前 repo 的 stage-split criteria

### 7.1 先做 serializer 修正，再餵 prompt

若你之後真的要實作，最重要的輸入前處理規則只有兩條。

1. 把 `criteria_stage1/*.json` 或 `criteria_stage2/*.json` 先 enumerate 成有 ID 的列表，例如 `I1`, `I2`, `E1`, `E2`。  
2. `topic_definition` 必須獨立放到 `background_context`，絕對不能再當成 inclusion criteria 的第一條字串。

### 7.2 針對 `2409` 的 micro-QA 例子

| Paper | Stage | Criterion | 建議的 criterion-question |
|---|---|---|---|
| 2409.13738 | Stage 1 | Inclusion: process extraction fit | Does the title/abstract explicitly link natural-language text to process-model or process-representation extraction, rather than prediction, matching, redesign, or text generation from processes? |
| 2409.13738 | Stage 2 | Inclusion: concrete method + empirical validation | Does the full text present a concrete NLP-based process-extraction method and explicit empirical validation, with experiments or evaluation rather than conceptual discussion only? |

這兩個例子刻意不是一般化的 yes/no 問法，而是直接把 `2409` 最危險的 object boundary 寫進 question wording。這樣做的目的，是讓 reviewer 在回答問題時就先處理「是不是 process extraction，而不是 process-related NLP」這件事，而不是等到最後 verdict 才想起來。

### 7.3 針對 `2511` 的 micro-QA 例子

| Paper | Stage | Criterion | 建議的 criterion-question |
|---|---|---|---|
| 2511.13936 | Stage 1 | Inclusion: preference-learning signal | Does the title/abstract explicitly show a learning signal based on pairwise preference, ranking, A/B comparison, converted ratings, or an RL loop for an audio model, rather than preference used only for evaluation? |
| 2511.13936 | Stage 2 | Inclusion: audio-domain application | Does the full text show that the learning setup is applied within the audio domain, including multimodal settings that contain audio, rather than merely citing audio as a side example? |

這兩個問題對 `2511` 特別重要，因為 repo 內多份分析都指出：`2511` 的真瓶頸不是單純 prompt 太短，而是 rating vs ranking、learning vs evaluation、audio-adjacent vs audio-in-domain 這幾條邊界很容易在自由文本 reasoning 中漂移。把這些 boundary 直接前置進 `criterion_question`，比最後再補一條嚴格 senior instruction 更乾淨。

## 8. 建議的落地順序

若你下一步真的要做實驗，我建議以下順序。

1. 先把這套新 prompt 當成 **non-production experimental line**。  
2. 第一輪只在 `2409` 與 `2511` 上做，因為它們最能檢查 evidence interface 是否真的變穩。  
3. 優先比較三組：current baseline、existing 3stage fused prompt、本報告新 prompt。  
4. 第一輪就把 junior output 存成結構化 JSON，不要等第二輪再補。  
5. senior 一定要吃 junior 的 JSON ledger，不要退回只看一段 reasoning。  
6. 指標上至少同看 Stage 1 F1、Combined F1、criterion-level disagreement rate、`UNCLEAR` 分布，以及 `unable_to_review` 比例。  

這個順序的理由很務實。因為 `CURRENT_AUTHORITY.md` 已經明講 QA 不是 production authority，所以最合理的姿勢不是直接替換，而是先讓新 prompt 自己證明：它是否真的比現有 3stage fused 版更能穩定保存 evidence object，並且在 `2409/2511` 這種邊界案例上帶來可量測的好處。

## 9. 舊 prompt 全文附錄

### 9.1 說明

為了讓附錄聚焦，這裡採一個一致原則。若原 prompt 本來就是中文，就直接保留原文；這同時也滿足「中文翻譯版」的要求。只有原文主要是英文的 prompt，我才額外附上中文翻譯版。

### 附錄 A：目前 runtime reviewer prompts

#### A1. `title_abstract_reviewer.py` 的 Stage 1 generic prompt（英文原版）

```text
**Stage 1 Review (Title + Abstract only, high-recall gate)**
You are screening only `title` and `abstract` to decide whether a paper should move to full review. Do not use or assume any full-text content.
This stage is recall-oriented: keep papers in flow when evidence is weak, and avoid hard exclusion without explicit evidence.
---
**Input item:**
<<${item}$>>
---
**Inclusion criteria:**
${inclusion_criteria}$

**Exclusion criteria:**
${exclusion_criteria}$
---
**Instructions**
1. Output your evaluation as an integer between 1 and 5:
- 1 強烈排除
- 2 可能排除
- 3 不確定 / 需要更多證據
- 4 可能納入
- 5 強烈納入
2. Stage 1 constraints:
- 只看 `title` + `abstract`，不得依賴 full text。
- 未出現否定性證據時，不應直接用 1 或 2 排除。
- 對 topic relevance 有一定疑似但不足以證成的，請偏向 3。
3. Sparse metadata 規則（citation-like/keyword-only/metadata 片段）：
- 不夠明確時不應直接視為 exclusion。
- 若只有摘要片段且缺關鍵 evidence，請保守為 3 並說明缺什麼。
4. 理由要簡潔：
- 指出你採用該分數的關鍵證據；若不確定，請明確列出缺少哪一條 criteria 證據。
5. 不要憑空捏造任何事實，不要推測 full text。
---
${reasoning}$
${additional_context}$
${examples}$
```

#### A2. `title_abstract_reviewer.py` 的 Stage 1 generic prompt（中文翻譯）

```text
**Stage 1 審查（只看標題與摘要，高召回閘門）**
你只根據 `title` 與 `abstract` 進行篩選，以決定一篇論文是否應該進入全文審查。不可使用或假設任何全文內容。
本階段以召回為優先：當證據偏弱時，應讓論文留在流程內；若沒有明確的否定性證據，不要做強硬排除。
---
**輸入項目：**
<<${item}$>>
---
**納入條件：**
${inclusion_criteria}$

**排除條件：**
${exclusion_criteria}$
---
**指示**
1. 以 1 到 5 的整數輸出你的評估：
- 1 = 強烈排除
- 2 = 可能排除
- 3 = 不確定 / 需要更多證據
- 4 = 可能納入
- 5 = 強烈納入
2. Stage 1 限制：
- 只能看 `title` + `abstract`，不得依賴 full text。
- 在沒有出現明確否定性證據時，不應直接用 1 或 2 排除。
- 若只是主題上似乎相關，但證據仍不足以支持納入，請偏向 3。
3. Sparse metadata 規則（像 citation-like、keyword-only、metadata 片段這類稀疏資料）：
- 資訊不夠明確時，不應直接當成排除證據。
- 若只有摘要片段且缺少關鍵 evidence，請保守給 3，並說明到底缺了什麼。
4. 理由要簡潔：
- 指出支撐你分數的關鍵證據；若不確定，請清楚列出是哪一條 criteria 的證據不足。
5. 不要捏造任何事實，也不要自行推測全文會補上什麼內容。
---
${reasoning}$
${additional_context}$
${examples}$
```

#### A3. `fulltext_reviewer.py` 的 Stage 2 generic prompt（英文原版）

```text
**Stage 2 Review (Full Text, criteria-level)**
You are doing final full-text screening for this paper. Decide based on explicit criteria evidence in the text, not on overall impression.
---
**Input item:**
<<${item}$>>
---
**Inclusion criteria:**
${inclusion_criteria}$

**Exclusion criteria:**
${exclusion_criteria}$
---
**Instructions**
1. Output your evaluation as an integer between 1 and 5:
- 1 強烈不納入
- 2 可能不納入
- 3 不確定 / 需要更多證據
- 4 可能納入
- 5 強烈納入
2. 評估必須逐條對齊 criteria：
- 只用 full text 文字片段（title/abstract + provided full text）支持每個判斷。
- 未明確提到的主張不算作證據；避免把隱含訊息硬推斷為事實。
3. 請列出關鍵證據：哪個 criteria 因何被支持、哪個無法支持、哪個有缺口。
4. 若證據缺失，不要猜測，保守給 `3`，並在 reasoning 中標明「缺少何種可追溯依據」。
5. reasoning 必須可追溯、可驗證，聚焦證據與 criteria，而非模型印象或作者聲望。
---
${reasoning}$
${additional_context}$
${examples}$
```

#### A4. `fulltext_reviewer.py` 的 Stage 2 generic prompt（中文翻譯）

```text
**Stage 2 審查（全文、criteria 級別）**
你正在對這篇論文進行最終的全文篩選。判定必須建立在文中可明確追溯的 criteria 證據上，而不是整體印象。
---
**輸入項目：**
<<${item}$>>
---
**納入條件：**
${inclusion_criteria}$

**排除條件：**
${exclusion_criteria}$
---
**指示**
1. 以 1 到 5 的整數輸出你的評估：
- 1 = 強烈不納入
- 2 = 可能不納入
- 3 = 不確定 / 需要更多證據
- 4 = 可能納入
- 5 = 強烈納入
2. 你的評估必須逐條對齊 criteria：
- 每個判斷都只能由 full text 的文字片段來支持（可含 title/abstract 與提供的全文內容）。
- 沒有被明確寫出的主張，不可以視為證據；不要把隱含訊息硬推論成事實。
3. 請列出關鍵證據：哪一條 criteria 被支持、哪一條不被支持、哪一條仍存在缺口。
4. 若證據缺失，不要猜測，保守給 `3`，並在 reasoning 裡標清楚「缺少哪一種可追溯依據」。
5. reasoning 必須可追溯、可驗證，聚焦在 evidence 與 criteria，而不是模型印象或作者名氣。
---
${reasoning}$
${additional_context}$
${examples}$
```

#### A5. `runtime_prompts.json` 角色設定（英文原版）

```json
{
  "stage1_junior": {
    "junior_nano": {
      "backstory": "A research assistant responsible for preliminary literature screening."
    },
    "junior_mini": {
      "backstory": "A research assistant familiar with the target domain."
    }
  },
  "stage1_senior_no_marker": {
    "backstory": "A senior reviewer responsible for synthesizing junior feedback and making final decisions.",
    "additional_context": "Two junior reviewers have provided initial assessments.\nReview their feedback before making your integrated judgment."
  },
  "stage1_senior_prompt_tuned": {
    "backstory": "You are the Stage 1 senior adjudicator. Your goal is to resolve key boundary cases using only title + abstract evidence with traceable decisions. You may only use the title, abstract, and both juniors' outputs/evaluations.\nDo not assume full text will fill missing evidence.",
    "additional_context": "Adjudication rules (strict mode):\n1) Only use information explicitly present in this input: title, abstract, and round-A_JuniorNano/JuniorMini outputs/evaluations; do not rely on unseen full text.\n2) Do not treat topic relevance, conceptual similarity, method similarity, or domain adjacency as sufficient inclusion evidence.\n3) You may assign 3 (maybe) only when all conditions are met:\n a. At least one traceable core positive inclusion signal is present (not just concept-related wording).\n b. Exactly one key eligibility condition is missing.\n c. That missing condition cannot be directly determined from the current title/abstract, yet deferral remains justified under this round's rules.\n4) If the case is topic-adjacent, method-related, metadata-like, or only mentions related keywords without core positive inclusion evidence, prefer 1 or 2 (exclude).\n5) High topic relevance does not imply inclusion: unless core eligibility is explicitly supported, do not retain the paper simply because it seems possibly related.\n6) In reasoning, explicitly state: what positive evidence is present, what key condition is missing, and why that does or does not warrant exclusion."
  },
  "stage2_fulltext": {
    "junior_nano": {
      "backstory": "A research assistant responsible for preliminary full-text screening."
    },
    "junior_mini": {
      "backstory": "A research assistant familiar with the target domain and able to review full text."
    },
    "senior": {
      "backstory": "A senior reviewer responsible for synthesizing full-text reviews and making final decisions.",
      "additional_context": "Two junior reviewers have provided initial assessments.\nReview their feedback before making your integrated judgment."
    }
  }
}
```

#### A6. `runtime_prompts.json` 角色設定（中文翻譯）

```json
{
  "stage1_junior": {
    "junior_nano": {
      "backstory": "負責初步文獻篩選的研究助理。"
    },
    "junior_mini": {
      "backstory": "熟悉目標領域的研究助理。"
    }
  },
  "stage1_senior_no_marker": {
    "backstory": "負責整合 junior 回饋並做出最終決定的資深 reviewer。",
    "additional_context": "兩位 junior reviewer 已經給出初步評估。\n請先閱讀他們的回饋，再做出你的整合判斷。"
  },
  "stage1_senior_prompt_tuned": {
    "backstory": "你是 Stage 1 的 senior adjudicator。你的任務是只用 title + abstract 的可追溯證據來處理關鍵邊界案例。你只能使用 title、abstract，以及兩位 junior 的 outputs/evaluations。\n不要假設 full text 會補上缺失證據。",
    "additional_context": "仲裁規則（strict mode）：\n1) 只能使用這份輸入中明確出現的資訊：title、abstract，以及 round-A_JuniorNano/JuniorMini 的 outputs/evaluations；不可依賴未見的全文。\n2) 不可把 topic relevance、概念相似、方法相似、領域鄰接性當成足夠的納入證據。\n3) 只有在以下條件同時成立時，才可以給 3（maybe）：\n a. 至少存在一條可追溯的核心正向納入訊號（不能只是概念相關字眼）。\n b. 剛好只缺一個關鍵 eligibility 條件。\n c. 這個缺口在目前 title/abstract 中無法直接判定，但依本輪規則，仍然值得 defer。\n4) 若案例只是 topic-adjacent、method-related、metadata-like，或只提到相關關鍵詞但沒有核心正向納入訊號，請優先給 1 或 2（exclude）。\n5) 高 topic relevance 不等於納入：除非核心 eligibility 已被明確支持，否則不要只因為看起來可能相關就保留。\n6) 在 reasoning 中，必須明確交代：有哪些正向證據、缺了哪一個關鍵條件、以及為什麼這個缺口是否足以導向排除。"
  },
  "stage2_fulltext": {
    "junior_nano": {
      "backstory": "負責初步全文篩選的研究助理。"
    },
    "junior_mini": {
      "backstory": "熟悉目標領域且能夠閱讀全文的研究助理。"
    },
    "senior": {
      "backstory": "負責整合全文審查結果並做出最終決定的資深 reviewer。",
      "additional_context": "兩位 junior reviewer 已經給出初步評估。\n請先閱讀他們的回饋，再做出你的整合判斷。"
    }
  }
}
```

### 附錄 B：`criteria_mds/` 的 upstream prompt

#### B1. `AGENT_PROMPT_generate_question_set_from_criteria.md`

```text
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
```

### 附錄 C：split QA -> criteria 版（`sr_screening_prompts/`）

#### C1. Prompt 2：Stage 1.2 title+abstract extraction

# Prompt 2 — Stage 1.2（只讀 Title + Abstract 的資訊抽取；**禁止**做 include/exclude 判定）
> **Stage 1.2 = title/abstract 抽取（不判定）**
> 你只能讀：title + abstract（來自 Stage 1.1 輸出）。
> 你要做的是：把後續 criteria 需要的資訊「抽取出來」，**不要**判定 include/exclude。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl （Stage 1.1 的輸出，含 key/title/abstract 與 eligible_for_stage1_2）
（可選）2) title_abstracts_metadata.jsonl（原始 metadata；若你需要確認欄位存在與否，但 join 仍只能用 key）

你的任務：針對 eligible_for_stage1_2=true 的 papers，**只用 title+abstract** 做資訊抽取。
嚴格禁止做任何 include/exclude/pass/fail 的最終判定；你只能抽取、定位、摘錄原文。答案允許「未提及/無法從 title+abstract 判斷」。

〖硬性要求〗
A) 只能以 key（bibkey）索引與輸出。禁止用 title 做 join。
B) 只能讀 title + abstract；禁止讀 full text；禁止上網。
C) 不可推論：沒有寫就回答「未提及」或「無法從 title/abstract 判斷」。
D) 但你可以做純格式化：列出出現的關鍵字、摘錄一句話、標記出處是 title 或 abstract。

================================================
Q0. Secondary research signals（只抽取，不下結論）
================================================
背景（操作性定義）：secondary research 指主要貢獻在於「綜整既有研究」而不是提出新的 primary study 實證結果。
常見兩群訊號：
A) evidence synthesis/review 方法學類：systematic review / systematic literature review / mapping study / scoping review / rapid review / realist review/synthesis / integrative review / mixed methods review / meta-analysis / qualitative evidence synthesis（meta-synthesis, meta-ethnography, meta-narrative…）/ concept analysis / critical interpretive synthesis / best evidence synthesis / meta-study / meta-summary…
B) CS/NLP 常見綜整型文章命名：survey / overview / tutorial / primer / taxonomy / conceptual framework / SoK (Systematization of Knowledge) / roadmap / research agenda / future directions / perspective / position paper / vision paper / opinion / commentary

你要做的事（僅從 title+abstract）：
- Q0.1 列出 title/abstract 中出現的 secondary research 關鍵詞（逐個列出，並附上原文片段與出處：title/abstract）。
- Q0.2 若 abstract 有明示 “this survey/review/overview…”、“we review/summarize/systematize existing…”、“we provide a taxonomy of existing approaches…”、“open challenges/future directions …” 等綜整語氣：摘錄 1–3 段原文。
- Q0.3 若 abstract 提到 systematic 流程線索（例如 database search / inclusion criteria / exclusion criteria / PRISMA / screening / study selection / mapping protocol）：摘錄原文；未提及則寫 "未提及"。

--------------------------------
Q1 任務定義（僅 title/abstract）
--------------------------------
- Q1.1 摘錄 abstract 中最能代表「任務/問題設定」的一句原文。
- Q1.2 Input 的描述（若 abstract 有寫）：摘錄原文；否則 "未提及"。
- Q1.3 Output 的描述（若 abstract 有寫）：摘錄原文；否則 "未提及"。
- Q1.4 是否明示 dialogue/conversation/meeting summarization 相關字樣？
  - 請列出關鍵字（從 title+abstract 直接擷取）
  - 記錄出處：title 或 abstract

--------------------------------
Q2 作者自述貢獻（僅 abstract；只摘錄不分類）
--------------------------------
- Q2.1 摘錄 abstract 中描述 contribution 的一句（we propose/introduce/present...）。
- Q2.2 若 abstract 出現 dataset/benchmark/metric/evaluation/survey/analysis/model/framework 等詞：
  - 逐一列出包含該詞的原文片段（可多段）+ 出處（title/abstract）
  - 若未出現，回答 "未提及"

--------------------------------
Q3 datasets（僅 title/abstract 中被明示者）
--------------------------------
- Q3.1 列出 title/abstract 中明確出現的 dataset 名稱（含縮寫/全名）。
- Q3.2 若 abstract 有說 dataset 用途（evaluate on / trained on / tested on...）：摘錄原文；否則 "未提及"。
- Q3.3 本階段不要求表格統計（因為只有 title/abstract）。

--------------------------------
Q4 dataset 語言（規則強化：未明說 → 直接視為英文）
--------------------------------
只對 Q3 列出的 datasets 做語言抽取：
- 若 abstract 明確寫 English/Chinese/multilingual/... → 摘錄原文
- 若沒有明確語言 → 直接輸出 **"英文"**（不要加不確定語氣）
另外，即使默認英文，仍要列出 title/abstract 中所有「可能暗示多語/非英文」的字眼（multilingual/cross-lingual/translation/Chinese/...），只摘錄不解釋。
（注意：這些暗示字眼只是保留線索，不代表你要下結論。）

--------------------------------
Q5 primary dataset 信號（title/abstract 可觀測部分；不做 primary 判定）
--------------------------------
- Q5.1 若 abstract 有 main/primary/we mainly evaluate on...：摘錄；否則 "未提及"
- Q5.2 若 abstract 提到 evaluation datasets：摘錄並列 dataset 名稱；否則 "未提及"

--------------------------------
Q6 多模態（title/abstract 可觀測部分；只抽取）
--------------------------------
- 列出 abstract 中明確提到的輸入模態關鍵字：text/audio/image/video/multimodal/ASR/transcript 等
- 若未提及：回答 "未提及"

--------------------------------
Q7 摘要型態（title/abstract 可觀測部分；只抽取）
--------------------------------
- 是否明示 extractive/abstractive/hybrid/generative？有則摘錄；無則 "未明說"
- 若 abstract 描述輸出形式（extract utterances / generate summary / free-form ...）：摘錄；無則 "未提及"

--------------------------------
Q8 Backbone/架構（title/abstract 可觀測部分；只抽取）
--------------------------------
- 列出 abstract/title 中出現的模型/架構名（BART/T5/PEGASUS/Transformer/GPT...），逐項附上原文片段。
- 若未提及 Transformer 字樣：回答 "未明說"

--------------------------------
Q9 multilingual/translation（title/abstract 只抽取）
--------------------------------
- 若提到 multilingual/cross-lingual/translation/non-English/other languages：摘錄；否則 "未提及"

--------------------------------
Q10 評估指標（title/abstract 可觀測部分；只抽取）
--------------------------------
- 列出 title/abstract 中出現的 metrics 名稱（ROUGE/BERTScore/...）及原文片段
- human evaluation 若在 abstract 提到也摘錄；否則 "未提及"

================================================
〖輸出格式（請提供下載）〗
================================================
A) JSONL：`stage1_2_title_abstract_extraction.jsonl`
- 一行一筆，僅包含 eligible_for_stage1_2=true 的 keys（其餘可不輸出，或輸出但標記 skipped）
- 建議結構（每個 Q 都要含 evidence_quotes/location；沒提及就用空陣列 + "未提及"）：
  {
    "key": "...",
    "source": {"used_fields": ["title","abstract"], "notes": "..."},
    "Q0_secondary_signals": {...},
    "Q1_task_definition": {...},
    ...,
    "Q10_evaluation": {...},
    "extraction_confidence": "high|medium|low",
    "missing_info_notes": "..."
  }
B) CSV：`stage1_2_title_abstract_extraction.csv`
- 只做索引（不要塞大量 quote）：
  - key
  - task_sentence（Q1.1）
  - datasets_mentioned（Q3.1）
  - backbone_terms_mentioned（Q8）
  - modality_terms_mentioned（Q6）
  - secondary_terms_mentioned（Q0.1）
  - multilingual_terms（Q9 + Q4 hints）
  - extraction_confidence
C) Key 清單：
- `stage1_2_processed_keys.txt`

〖回覆中請給 summary〗
- eligible_for_stage1_2=true 的數量
- abstract 缺失或空白的數量
- title/abstract 明確提到 summarization 的數量
- title/abstract 明確提到 Transformer 或具體 backbone 的數量
- title/abstract 出現 secondary research 強訊號（survey/review/SoK/systematic...）的數量
並提供所有輸出檔案下載連結。
```

#### C2. Prompt 3：Stage 1.2 criteria review

# Prompt 3 — Stage 1.2（用 criteria 對 Title + Abstract 抽取結果做初判：include / exclude / maybe）
> **Stage 1.2 = criteria review（允許 maybe）**
> 輸入：Stage 1.1（metadata prefilter）+ Stage 1.2（title/abstract 抽取）。
> 輸出：include / exclude / maybe（三分類）+ 每條 criterion 的 YES/NO/UNCLEAR + 可稽核理由。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl
2) stage1_2_title_abstract_extraction.jsonl

你的任務：依下列 criteria，對每篇 eligible_for_stage1_2=true 的 paper 做 Stage 1.2 初判：
- 輸出 include / exclude / maybe
- 對每條 criterion 輸出 status：YES / NO / UNCLEAR
- 並寫可稽核理由（必須引用 Stage1.1 欄位值或 Stage1.2 的 evidence_quotes）

================================================
〖Stage 1.2 的硬規則（務必逐字遵守）〗
================================================
(1) 只要任一條 Exclusion == YES → verdict = EXCLUDE
(2) 只要任一條 Inclusion == NO → verdict = EXCLUDE
(3) 若沒有觸發 EXCLUDE，但任一條 criterion == UNCLEAR → verdict = MAYBE
(4) 只有在「所有 Inclusion == YES」且「所有 Exclusion == NO」時 → verdict = INCLUDE

================================================
〖本 SR 的 criteria（CADS 類型 + 新增 secondary 排除）〗
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later. （用 Stage1.1 的 pub_ge_2019）
I2. Transformer-based methods. （看 title/abstract 的 backbone/Transformer 字樣）
I3. In the context of summarization. （任務與 output=summary/minutes/highlights 等）

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset. （只在 title/abstract 有明確 non-English/multilingual 證據才 YES）
E2. Multi-modal (visual/audio) as input. （title/abstract 明確提到用 audio/image/video features 才 YES）
E3. Focus on extractive summarization. （title/abstract 明確自稱 extractive 或輸出=extracted spans 才 YES）
E4. Non-Transformer-based methods. （title/abstract 明確說主要方法非 Transformer 才 YES）
E5. Secondary research. （survey/review/SoK/taxonomy/tutorial/roadmap/... 的強訊號才 YES）

注意：E5 是 evidence base=primary studies 的常見排除政策，即使原 SR 沒明寫，也常用於避免把 review/survey 當 primary study。

================================================
〖如何用 Stage1.1 + Stage1.2 抽取結果判定每條 criterion〗
================================================
I1（>=2019）
- 用 Stage1.1 的 pub_ge_2019：
  - true → YES
  - false → NO
  - null → UNCLEAR
- evidence：publication_year + pub_ge_2019_reason

I2（Transformer-based）
- 用 Stage1.2 的 Q8：
  - 若 title/abstract 明確寫 Transformer / Transformer-based / 或列出明確 Transformer backbone（BART/T5/PEGASUS/LED/Longformer/GPT...）→ YES
  - 若 title/abstract 明確表述主要方法是 RNN/LSTM/GRU/CNN 等非 Transformer → NO
  - 否則 → UNCLEAR
- evidence：Q8 的 quotes

I3（Summarization context）
- 用 Stage1.2 的 Q1（task/input/output）：
  - 若 output 明確是 summary/minutes/highlights 或明示 summarization → YES
  - 若 task/output 明確不是 summarization（例如 classification/retrieval/metric/dataset paper…）→ NO
  - 否則 → UNCLEAR
- evidence：Q1.1/Q1.3/Q1.4 + Q2.1（如有）

E4（Non-Transformer methods）
- 與 I2 互補，但仍要明確輸出：
  - 若 I2==NO → E4=YES
  - 若 I2==YES → E4=NO
  - 若 I2==UNCLEAR → E4=UNCLEAR

E3（Extractive focus）
- 用 Stage1.2 的 Q7：
  - 明確自稱 extractive 或輸出定義為 extracted utterances/sentences/spans → YES
  - 明確自稱 abstractive/generative/free-form summary → NO
  - 否則 → UNCLEAR
- evidence：Q7 quotes

E2（Multi-modal as input）
- 用 Stage1.2 的 Q6：
  - 只有在 title/abstract 明確說模型輸入包含 audio/image/video（例如 audio features / visual features / multimodal encoder 等）→ YES
  - 若只提到 transcript / text / dialogue logs，且未提 audio/image/video 特徵 → NO（title/abstract 階段通常只到 NO/UNCLEAR；這裡採保守但不亂排除）
  - 若有模糊字眼（例如只寫 multimodal 但不清楚是否作為模型輸入）→ UNCLEAR
- evidence：Q6 quotes

E1（Non-English primary dataset）
- Stage 1.2 只能用 title/abstract，通常難以判 primary dataset；本階段規則如下：
  - 若 title/abstract 明確寫 non-English / Chinese / Arabic / multilingual / cross-lingual / translation 且語境是 dataset/語料/評估語言 → YES
  - 若完全未提語言（依 Q4 規則：未明說→視為英文）→ NO（高確定度 not-triggered）
  - 若只有“可能暗示”字眼（如 dataset 名稱看起來像非英文，但 abstract 沒明說）→ NO（不要用名稱硬推論）；但可在 notes 記錄 hints
  - 若 abstract 同時提到 multilingual/translation 但不清楚是否 primary dataset → UNCLEAR
- evidence：Q4（language quotes or default English）+ Q9（multilingual terms）+ Q3（dataset mentions）

E5（Secondary research）
- 用 Stage1.2 的 Q0 + Q2：
  - 若 title 或 abstract **明確自述**：survey / review / systematic review / mapping / scoping / meta-analysis / SoK / tutorial / overview / roadmap / position/vision/perspective/opinion/commentary → YES
  - 若只有 “taxonomy” 字樣：
    - 若 abstract 同時出現綜整語氣（we review/systematize existing work / comprehensive overview / future directions）→ YES
    - 否則 → UNCLEAR（不要僅憑 taxonomy 一詞就 YES）
  - 若完全沒有 secondary 訊號 → NO
- evidence：Q0.1/Q0.2/Q0.3 quotes（必要時也可引用 Q2 中出現 survey/overview 等詞的片段）

================================================
〖輸出檔案（請提供下載）〗
================================================
A) JSONL：`stage1_2_screening_decisions.jsonl`
- 一行一筆（只需包含 eligible_for_stage1_2=true 的 keys）
- 每筆至少包含：
  - key
  - stage1_1_decision（帶過來）
  - criteria_status：
    * I1/I2/I3/E1/E2/E3/E4/E5：{status:"YES|NO|UNCLEAR", evidence:[...], notes:"..."}
  - stage1_2_decision：include/exclude/maybe
  - exclude_reasons：若 exclude，列出觸發的條件（例如 ["E5","I2"]）
  - maybe_reasons：若 maybe，列出 UNCLEAR 的條件 key
  - decision_confidence_1to5：1–5（可選；**是對整體判定把握**，不是對單條 criterion）
  - decision_reason：中文，必須引用 evidence（Stage1.1 欄位值或 Stage1.2 quotes）
B) CSV：`stage1_2_screening_decisions.csv`
- 至少包含：key, stage1_2_decision, I1,I2,I3,E1,E2,E3,E4,E5, exclude_reasons, maybe_reasons, decision_confidence_1to5, decision_reason（可略縮）
C) Key 清單（供 Stage 2 用）
- `stage1_2_include_keys.txt`
- `stage1_2_maybe_keys.txt`
- `stage1_2_exclude_keys.txt`

〖回覆中請給 summary〗
- include/maybe/exclude 各多少
- 最常見的 exclude 原因（列前 5）
- maybe 最常見來自哪些 UNCLEAR criterion
並提供所有輸出檔案下載連結。
```

#### C3. Prompt 4：Stage 2 full-text extraction

# Prompt 4 — Stage 2（讀 Full Text 的資訊抽取；**禁止**做 include/exclude 判定）
> **Stage 2 = full-text 抽取（不判定）**
> 你只對 Stage 1.2 判定為 include/maybe 的 papers 讀 full text。
> 這一步仍然 **只做資訊抽取**（Q0–Q10），不做 include/exclude 最終判定。

```text
我會提供你：
1) stage1_2_screening_decisions.jsonl （Stage 1.2 的 include/maybe/exclude 結果）
2) fulltexts_text_only.zip （254 篇 paper 的全文 md）
（可選）3) stage1_1_metadata_screening.jsonl（若你想保留 metadata 欄位，但 join 仍只能用 key）

你的任務：只針對 Stage 1.2 決策為 include 或 maybe 的 keys，讀取 fulltexts_text_only.zip 中對應的 md 全文，並完成 Q0–Q10 的「全文級資訊抽取」。
嚴格禁止做 include/exclude/pass/fail 的最終判定；你只能抽取、定位、摘錄原文。答案允許不確定，但必須說明是因為 paper 沒寫或你找不到明示句。

〖硬性要求〗
A) 以 key（bibkey）做唯一索引；檔名若不等於 key，必須記錄 mapping 規則與是否 ambiguous。
B) 可用程式做：解壓縮、列檔、搜尋 Table/Figure/Section 位置、輸出 JSONL/CSV、統計 table 數量。
C) 不可用程式做：自動關鍵詞分類後直接下結論。你必須閱讀並摘錄原文作證。
D) 每個 Q 的輸出都要包含：
- answer（結構化）
- evidence_quotes（至少 1 段原文；若未提及則空陣列）
- evidence_location（例如 Abstract / Introduction / Section 2 / Experiments / Table 1 / Appendix ...）

================================================
Q0. Secondary research signals（全文版；只抽取不判定）
================================================
你要從全文抽取能判斷 paper 是否屬於 secondary research 的“可觀測證據”，但你不能下 verdict。
Q0.1 Self-identification（作者是否自稱綜整研究？）
- 摘錄 paper 自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/taxonomy/roadmap/position/vision/perspective/opinion/commentary 的句子（若有）。
- 若未提及，回答 "未提及"。
Q0.2 Evidence synthesis methodology signals（若有，通常很強）
- 是否出現：PRISMA、database search、search strings/queries、screening、study selection、inclusion criteria、exclusion criteria、quality assessment、flow diagram、systematic mapping protocol…？
- 有則逐項摘錄原文 + 位置（通常在 Method/Appendix）；無則 "未提及"。
Q0.3 “Taxonomy/SoK” 類綜整語氣
- 若 paper 有 taxonomy / systematization / categorize existing approaches / comprehensive overview / future directions/open challenges 等敘述：
- 摘錄 1–3 段原文，並標位置（Intro/Related Work/Conclusion 等）
Q0.4 兼具資源釋出（仍然只抽取）
- 若 paper 同時提出 dataset/benchmark/metric/evaluation protocol：摘錄作者自述 “we release/provide a dataset/benchmark/metric…” 的句子（這不代表不是 secondary；你只負責抽取）

================================================
Q1–Q10（依你先前定義；全文抽取）
================================================
Q1 任務定義
- (1) 任務/問題設定一句原文（Abstract/Introduction/Task Definition）
- (2) Input 描述原文（dialogue transcript / multi-party conversation / meeting / chat ...）
- (3) Output 描述原文（summary/minutes/highlights ...）
- (4) 是否明示 dialogue/conversation/meeting summarization 字樣？列出關鍵字 + 段落/小節名

Q2 作者自述主要貢獻（只摘錄，不分類、不下結論）
- (1) Abstract 中 contribution 句（we propose/introduce/present...）
- (2) 若明示 dataset/benchmark/metric/evaluation/survey/analysis/model/framework 等詞：逐一列出原文片段（可多段）+ 位置

Q3 datasets（只列舉與定位，不判定 primary）
- (1) 列出所有 dataset 名稱（含縮寫/全名）+ 出現位置（Abstract/Experiments/Table/Figure/Appendix）
- (2) 每個 dataset 的用途：training/validation/test/evaluation/case study/human eval data（用原文支持）
- (3) 若有主要結果表：列出每張主要表用到哪些 dataset（表號 + dataset）

Q4 dataset 語言（規則強化：未明說 → 直接視為英文）
- (1) 對每個 dataset：若 paper 明確寫語言，摘錄原文
- (2) 若沒寫語言：直接回答「英文」（不要加不確定語氣），並標記是 default rule
- (3) 仍要額外摘錄所有可能暗示非英文/多語的字眼（dataset 名稱含 Chinese/... 或 multilingual/cross-lingual/translation 段落），只摘錄不推論

Q5 primary dataset 可觀測信號（只提供信號，後續 prompt 才決策）
- (1) 是否出現 primary/main/we mainly evaluate on...？摘錄
- (2) Abstract 是否提到特定 dataset 用於 evaluation？摘錄 + dataset 名稱
- (3) 統計：每個 dataset 出現在多少張「主要結果表」中（只要數字）
- (4) 若 paper 是 metric/evaluation 類：列出 metric/eval → datasets 的對應（原文支持）

Q6 多模態（只抽取 input modality，不下 multi-modal 結論）
- (1) 列出輸入模態 text/audio/image/video/other（逐項附原文）
- (2) audio：是否用音訊特徵作輸入？摘錄；若只用 transcript，摘錄並明確寫「僅使用文字轉錄」
- (3) image/video：是否用視覺特徵作輸入？摘錄；若輸入仍是文字，摘錄並明確寫「輸入仍為文字」
- (4) dataset 含影音但只用文字部分：摘錄支持句

Q7 摘要型態（extractive/abstractive/hybrid：只取作者自述與輸出定義）
- (1) 是否明確自稱 extractive/abstractive/hybrid/generative？摘錄；無則「未明說」
- (2) 系統輸出形式原文：free-form summary / extracted utterances / hybrid two-stage ...
- (3) 若有 output example：指出位置並摘錄代表性片段（不解釋）

Q8 Backbone（Transformer 與否：只列模型與作者用詞）
- (1) 列出 backbone/model 名稱（BART/T5/PEGASUS/LED/Longformer/GPT/...），每個附原文片段
- (2) 是否明寫 Transformer-based/Transformer architecture/encoder-decoder/decoder-only？摘錄；無則「未明說」
- (3) 若比較非 Transformer baseline：列出名稱與原文片段

Q9 multilingual/translation（只摘錄）
- (1) 是否提到 multilingual/cross-lingual/translation/non-English/...？有則摘錄；無則「未提及」
- (2) 若提到：逐項摘錄“哪些部分是多語”（dataset/model/training/eval/application）

Q10 評估方式與指標（只抽取）
- (1) 列出 automatic metrics（ROUGE/BERTScore/...）+ 原文片段
- (2) human eval 若有：摘錄（面向 + 設定）
- (3) 若提出新 metric / 新 evaluation protocol：摘錄命名與定義句

================================================
〖輸出檔案（請提供下載）〗
================================================
A) JSONL：`stage2_fulltext_extraction.jsonl`
- 一行一筆，只包含 Stage 1.2 include/maybe 的 keys
- 建議結構：
  {
    "key": "...",
    "mapping": {...},
    "Q0_secondary_signals": {...},
    "Q1_task_definition": {...},
    ...,
    "Q10_evaluation": {...},
    "extraction_confidence": "high|medium|low",
    "notes": "..."
  }
B) CSV：`stage2_fulltext_extraction.csv`
- 作為索引用：key +（任務一句話、output、backbone terms、datasets list、modality terms、extractive/abstractive terms、secondary terms、multilingual terms、confidence）
C) `dataset_table_index_stage2.csv`
- 每篇 paper 的主要表格索引：key, table_id, table_context, datasets_mentioned

〖回覆中請給 summary〗
- Stage 1.2 include/maybe 的總數，以及實際成功讀到 full text 的數量
- 找不到對應 md 的 key 清單（若有）
- extraction_confidence=low 的 key 清單（若有）
並提供所有輸出檔案下載連結。
```

#### C4. Prompt 5：Stage 2 final criteria review

# Prompt 5 — Stage 2（用 criteria 對 Full Text 抽取結果做最終判定：include / exclude）
> **Stage 2 = final decision（不允許 maybe）**
> 輸入：Stage 1.1 + Stage 1.2（decision）+ Stage 2（full text 抽取）。
> 輸出：include / exclude（二分類）+ 每條 criterion 的 YES/NO/UNCLEAR + 可稽核理由。
> 若仍 UNCLEAR：採保守策略 → EXCLUDE，並標 `needs_manual_review=true`。

```text
我會提供你：
1) stage1_1_metadata_screening.jsonl
2) stage1_2_screening_decisions.jsonl
3) stage2_fulltext_extraction.jsonl

你的任務：只針對 Stage 1.2 決策為 include 或 maybe 的 keys，依下列 criteria 做 Stage 2 最終判定（include/exclude）：

================================================
〖Stage 2 的硬規則（務必逐字遵守）〗
================================================
(1) 只要任一條 Exclusion == YES → verdict = EXCLUDE
(2) 只要任一條 Inclusion == NO → verdict = EXCLUDE
(3) Stage 2 不允許 MAYBE：
- 若沒有觸發 (1)(2)，但任一條 criterion == UNCLEAR → verdict = EXCLUDE，並 `needs_manual_review=true`
(4) 只有在「所有 Inclusion == YES」且「所有 Exclusion == NO」時 → verdict = INCLUDE

================================================
〖本 SR 的 criteria（CADS 類型 + Secondary 排除）〗
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later.
I2. Transformer-based methods.
I3. In the context of summarization（主要任務/輸出是 summarization）。

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset.
E2. Multi-modal studies incorporating visual or audio elements as model input.
E3. Focus on extractive rather than abstractive summarization.
E4. Non-Transformer-based methods.
E5. Secondary research（survey/review/systematic mapping/scoping/meta-analysis/SoK/taxonomy/tutorial/roadmap/position/vision/...）

================================================
〖如何用 Stage1.1/Stage1.2/Stage2 抽取結果判定 criteria〗
================================================
先做“繼承規則”：
- 若 stage1_1_decision=="exclude" 或 stage1_2_decision=="exclude"：本階段直接 final_decision="exclude"（並寫明是前序已排除）。
（不需要再算所有 criterion，但仍可填 criteria_status 為 null 並寫 reason。）

I1（>=2019）
- 用 Stage1.1 pub_ge_2019：
  - true → YES
  - false → NO
  - null → UNCLEAR

I2（Transformer-based）
- 用 Stage2-Q8：
  - 若 paper 明確寫 Transformer-based / Transformer architecture / encoder-decoder Transformer / decoder-only，或主要 backbone 明確為 Transformer 家族（BART/T5/PEGASUS/LED/Longformer/GPT...）→ YES
  - 若 paper 明確以非 Transformer 作為主要方法（RNN/LSTM/GRU/CNN/graph model… 且非只是 baseline）→ NO
  - 否則 → UNCLEAR
- 同時更新 E4（互補）：
  - I2==NO → E4=YES
  - I2==YES → E4=NO
  - I2==UNCLEAR → E4=UNCLEAR

I3（Summarization）
- 用 Stage2-Q1（任務/輸出定義）：
  - output 明確是 summary/minutes/highlights 或明示 summarization → YES
  - 明確不是 summarization → NO
  - 否則 → UNCLEAR

E3（Extractive focus）
- 只在 I3==YES 時評估：
  - 若 Stage2-Q7 明確自稱 extractive，或輸出定義為 extracted utterances/sentences/spans → YES
  - 若明確自稱 abstractive/generative/free-form summary → NO
  - 若未明說但 output example/輸出格式可判定 → 依原文決定 YES/NO
  - 仍無法判定 → UNCLEAR

E2（Multi-modal as model input）
- 用 Stage2-Q6（以“模型輸入模態”為準）：
  - 若模型輸入包含 audio features / spectrogram / MFCC / prosody，或包含 image/video features / vision encoder outputs → YES
  - 若只用 ASR transcript / text transcript，且有原文支持 “transcripts only” → NO
  - 若 dataset 含影音但 paper 明確只用文字部分 → NO
  - 否則 → UNCLEAR

E1（Non-English primary dataset）
- 用 Stage2-Q3/Q4/Q5（注意：規則強化：未明說語言 → 直接視為英文）：
  1) 先用 Q5 的 signals 選出 `primary_dataset_candidate`（可多個並列，但必須引用信號：main/primary 語句、abstract 指名、主要結果表出現次數等）
  2) 再用 Q4 的語言資訊判定：
     - 若 primary_dataset_candidate 的語言明確非英文（Chinese/Arabic/...）或明確寫 multilingual/cross-lingual/non-English 且語境是 primary dataset → E1=YES
     - 若 paper 沒有明確寫語言（依 Q4 規則默認英文），且全文也未明示 non-English/multilingual/cross-lingual 作為 dataset 語言 → E1=NO（高確定度）
     - 若 paper 明確談 multilingual/cross-lingual/translation，但無法釐清 primary dataset 語言 → E1=UNCLEAR
  3) 若完全選不出 primary_dataset_candidate：
     - 不要因為“選不出 primary”就把 E1 當 YES
     - 只有在明確證據指向 non-English dataset 時才 YES；否則 NO 或 UNCLEAR（依是否提到 multilingual/translation）

E5（Secondary research）
- 用 Stage2-Q0 + Q2（作者自述）：
  - 若 paper 自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/roadmap/position/vision/perspective/opinion/commentary → YES
  - 若 paper 出現 evidence synthesis 方法學線索（PRISMA、database search、screening、inclusion/exclusion criteria、flow diagram…）→ YES
  - 若 paper 只有 taxonomy 字眼，但全文大量是整理既有方法、提出 taxonomy、future directions（非提出 primary empirical study）→ YES
  - 若完全無此類訊號 → NO
  - 若訊號矛盾或不足（少見）→ UNCLEAR
  （注意：就算 paper 同時釋出 dataset/benchmark/metric，若整體仍是綜整型 secondary research，E5 仍可為 YES；但你只依 paper 自述與方法描述下結論。）

================================================
〖輸出檔案（請提供下載）〗
================================================
A) JSONL：`stage2_final_decisions.jsonl`
- 一行一筆（只包含 Stage1.2 include/maybe 的 keys）
- 每筆至少包含：
  - key
  - final_decision: "include" / "exclude"
  - needs_manual_review: true/false（若任何 criterion==UNCLEAR 且因此被保守排除 → true）
  - criteria_status：
    * I1/I2/I3/E1/E2/E3/E4/E5：{status:"YES|NO|UNCLEAR", evidence:[...], notes:"..."}
  - primary_dataset_candidate：[...]
  - exclude_reasons：若 exclude，列出觸發的條件（E 或 I）
  - decision_confidence_1to5：1–5（可選；整體把握，不是逐條打分）
  - decision_reason：中文，逐條交代 I 與 E 的狀態與最關鍵 evidence quote
B) CSV：`stage2_final_decisions.csv`
- 至少包含：key, final_decision, needs_manual_review, I1,I2,I3,E1,E2,E3,E4,E5, primary_dataset_candidate, exclude_reasons, decision_reason（可略縮）
C) Key 清單：
- `stage2_include_keys.txt`
- `stage2_exclude_keys.txt`

〖回覆中請給 summary〗
- include / exclude 各多少
- needs_manual_review=true 的數量與 key 清單
- 最常見的 exclude 觸發原因（I 不滿足 or 哪個 E==YES / UNCLEAR）
並提供所有輸出檔案下載連結。
```

### 附錄 D：既有 fused 版（`sr_screening_prompts_3stage/`）

#### D1. Prompt 3：Stage 1.2 直接 criteria review

# Prompt 3 — Stage 1.2（Title+Abstract 直接 Criteria Review：逐條 1～5 分 + verdict=include/exclude/maybe）
> **Stage 1.2 = 只看 Title + Abstract，直接做 criteria review（允許 maybe）**
> 注意：本版本沒有 Prompt 2（不做獨立 evidence extraction）。你必須在打分時同步把證據（quotes）抽出來。

```text
- 角色：SR Screening Reviewer（Stage 1.2 criteria review；title+abstract）單 agent
- 你會收到：
  1) `stage1_1_metadata_screening.jsonl`（Stage 1.1 輸出；含 key/title/abstract/eligible_for_stage1_2）
  （可選）2) `title_abstracts_metadata.jsonl`（原始 metadata；若 Stage1.1 內文缺 title/abstract 可用 key 回填）
- 你的任務：對每篇 `eligible_for_stage1_2=true` 的 paper，只用 title+abstract：
  1) 針對每條 criterion 打 1～5 分（並轉成 YES/NO/UNCLEAR）
  2) 套用硬規則輸出 Stage 1.2 verdict：include / exclude / maybe
  3) 產出可下載的 decision 檔（JSONL + CSV + key 清單）
- 限制（硬性）：
  1) 禁止上網；只能用提供的檔案內容。
  2) 只能用 `key` 做 join；禁止用 title 來 join。
  3) Stage 1.2 僅允許閱讀 **title + abstract**；不得讀 full text（fulltexts_text_only.zip 在 Stage 2 才能用）。
  4) 所有分數必須能回指到 evidence_quotes（title/abstract 的原文片段）或 Stage1.1 的欄位值；沒有證據就給 3（UNCLEAR），禁止臆測。
  5) 不要先假設「最後會有幾篇 include」；test-time 只能依現有資料判斷。

================================================
本 SR criteria（CADS 類型 + Secondary 排除）
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later. （來自 Stage1.1: pub_ge_2019）
I2. Transformer-based methods.
I3. In the context of summarization.

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset.
E2. Multi-modal input (visual/audio as model input).
E3. Focus on extractive rather than abstractive summarization.
E4. Non-Transformer-based methods.
E5. Secondary research.

------------------------------------------------
重要預設/規則（用來降低“不確定”）
------------------------------------------------
(1) Dataset 語言預設（對應 E1）：
- 若 title/abstract 沒有明確寫 dataset/語言（English/Chinese/…），依 CADS 規則 **直接視為 English**。
- 只有在 title/abstract 明確指向非英文（例如 Chinese/Arabic/…、non-English、multilingual、cross-lingual、translation… 且語境是 dataset/corpus）時，才提高 E1 分數。
(2) Multi-modal（對應 E2）：
- 只有當 title/abstract 明確提到 audio/video/image/multimodal 且語境是「模型輸入」時，才提高 E2 分數。
- 若只看到 “speech transcript / ASR transcript” 等，且未提音訊特徵 → 不可直接判 multi-modal；通常給 3（UNCLEAR）或 1（NO）需看文字是否清楚。
(3) Secondary research（對應 E5）：
- 若 title/abstract 明確自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/roadmap/taxonomy/future directions 等「綜整既有工作」型態 → E5 高分。
- 若只有 “taxonomy” 但 abstract 沒有綜整語氣 → 不可直接當成 secondary；可給 3（UNCLEAR）。

================================================
分數 → 狀態（必須一致）
================================================
- Inclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR
- Exclusion：4–5 => YES（觸發排除）；1–2 => NO；3 => UNCLEAR

================================================
Stage 1.2 硬規則（務必逐字遵守）
================================================
(1) 只要任一條 Exclusion.status == YES → verdict = EXCLUDE
(2) 只要任一條 Inclusion.status == NO → verdict = EXCLUDE
(3) 若未觸發 EXCLUDE，但任一條 criterion.status == UNCLEAR → verdict = MAYBE
(4) 只有在「所有 Inclusion.status == YES」且「所有 Exclusion.status == NO」時 → verdict = INCLUDE

================================================
你需要做的事（流程）
================================================
Step 0) 讀入 Stage 1.1 檔，取得 eligible keys
- 以 key 為主鍵
- 只處理 eligible_for_stage1_2=true 的 records

Step 1) 對每篇 paper，建立 Stage 1.2 的 evidence pack（只限 title+abstract）
- 你必須把每條 criterion 的 evidence_quotes 抽出來（1–3 段短 quote）
- quote 來源只能是 title 或 abstract；並記錄來源：title / abstract

Step 2) 逐條 criterion 打分（1–5）並給出 status
- I1：直接用 Stage1.1 的 pub_ge_2019（不用 quote）
- I2/I3/E2/E3/E4/E5：用 title/abstract 的 evidence_quotes
- E1：若未明說語言 → 依規則視為 English → E1_score=1（NO）並在 notes 註明「未明說→預設 English」；若明確提 non-English/multilingual/translation 且語境是 dataset/corpus → 提高分數

Step 3) 套用硬規則輸出 verdict（include/exclude/maybe）
- 同時輸出 `exclude_reason_primary`：
  - 若因 Exclusion=YES 排除：列出觸發的 exclusion id（可多個）
  - 若因 Inclusion=NO 排除：列出不符合的 inclusion id

================================================
輸出（必須提供下載）
================================================
A) JSONL：`stage1_2_screening_decisions.jsonl`
- 一行一筆（只包含 eligible_for_stage1_2=true 的 papers）
- 每筆至少包含：
  - key
  - stage1_2_verdict: "include"|"exclude"|"maybe"
  - exclude_reason_primary: ["E2", ...] 或 ["I2", ...]
  - criteria_scores:
    {
      "I1": {"score_1to5": int, "status": "YES|NO|UNCLEAR", "evidence_quotes": [], "evidence_source": "stage1_1"},
      "I2": {"score_1to5": int, "status": "YES|NO|UNCLEAR", "evidence_quotes": [], "evidence_source": "title|abstract"},
      ...,
      "E5": {...}
    }
  - decision_confidence_1to5（整體把握；不是逐條）
  - notes（可空）
B) CSV：`stage1_2_screening_decisions.csv`
- 至少包含：key, stage1_2_verdict, I1_score,I2_score,I3_score,E1_score,E2_score,E3_score,E4_score,E5_score, decision_confidence_1to5
C) key 清單：
- `stage1_2_include_keys.txt`
- `stage1_2_maybe_keys.txt`
- `stage1_2_exclude_keys.txt`

================================================
回覆文字（summary）
================================================
請在回覆中提供：
- eligible_for_stage1_2 的篇數
- stage1_2 include/exclude/maybe 各自數量
- 最常見的排除原因（E? 或 I?）前 5 名（按次數）
- 以及 `mapping_ambiguous=true`（若你需要用 title 做 debug） 的 key 清單
最後提供所有輸出檔案下載連結。
```

#### D2. Prompt 5：Stage 2 直接 final criteria review

# Prompt 5 — Stage 2（Final Criteria Review on Full Text：逐條 1～5 分 + final verdict=include/exclude）
> **Stage 2 = 讀 Full text，直接做最終 criteria review（不允許 maybe）**
> 注意：本版本沒有 Prompt 4（不做獨立 evidence extraction）。你必須在打分時同步把證據（quotes）抽出來。

```text
- 角色：SR Screening Reviewer（Stage 2 final criteria review；full text）單 agent
- 你會收到：
  1) `stage1_1_metadata_screening.jsonl`
  2) `stage1_2_screening_decisions.jsonl`
  3) `fulltexts_text_only.zip`（多篇 paper 的全文 md）
- 你的任務：只針對 Stage 1.2 verdict 為 include 或 maybe 的 keys：
  1) 讀取 full text（md）
  2) 依 SR criteria 逐條打 1～5 分（並轉 YES/NO/UNCLEAR）
  3) 套用硬規則輸出最終 verdict：include / exclude（Stage 2 不允許 maybe）
  4) 產出可下載的最終 decision 檔（JSONL + CSV + key 清單）
- 限制（硬性）：
  1) 禁止上網；只能用提供檔案。
  2) 只能用 key 做 join。
  3) 每條 criterion 的分數都必須引用 evidence_quotes（full text 原文片段；必要時可補引用 title/abstract）。
  4) Stage 2 不允許 maybe：若任何 criterion = UNCLEAR（score=3）→ 必須保守排除並標 needs_manual_review=true。
  5) 不要先假設最後 include 幾篇；test-time 只能依提供資料判斷。

================================================
本 SR criteria（CADS 類型 + Secondary 排除）
================================================
Inclusion（全部必須 YES）
I1. Published in 2019 or later. （Stage1.1: pub_ge_2019）
I2. Transformer-based methods.
I3. In the context of summarization.

Exclusion（任一 YES 就排除）
E1. Non-English primary dataset.
E2. Multi-modal input (visual/audio as model input).
E3. Focus on extractive rather than abstractive summarization.
E4. Non-Transformer-based methods.
E5. Secondary research.

------------------------------------------------
Dataset 語言預設（對應 E1；在 Stage 2 也要遵守）
------------------------------------------------
- 若全文沒有明確寫 dataset/corpus 語言：依規則 **直接視為 English**（E1_score=1，NO）
- 只有在全文明確寫 non-English / Chinese / Arabic / multilingual / cross-lingual / translation，且語境是 dataset/corpus 或主要評估資料，才提高 E1 分數。

================================================
分數 → 狀態（必須一致）
================================================
- Inclusion：4–5 => YES；1–2 => NO；3 => UNCLEAR
- Exclusion：4–5 => YES（觸發排除）；1–2 => NO；3 => UNCLEAR

================================================
Stage 2 硬規則（務必逐字遵守）
================================================
(1) 只要任一條 Exclusion.status == YES → final_verdict = EXCLUDE
(2) 只要任一條 Inclusion.status == NO → final_verdict = EXCLUDE
(3) Stage 2 不允許 MAYBE：
- 若未觸發 EXCLUDE，但任一條 criterion.status == UNCLEAR → final_verdict = EXCLUDE 且 needs_manual_review=true
(4) 只有在「所有 Inclusion.status == YES」且「所有 Exclusion.status == NO」時 → final_verdict = INCLUDE

================================================
你需要做的事（流程）
================================================
Step 0) 取得 Stage 2 待審 keys
- 從 `stage1_2_screening_decisions.jsonl` 選出 stage1_2_verdict in {include, maybe}

Step 1) 在 fulltexts_text_only.zip 中找到對應 md
- 最優先：檔名（去掉副檔名）== key
- 若找不到：在 md 內文開頭尋找可定位資訊（如 Bibkey/ID/Title）
- 若仍無法對應：標記 `fulltext_missing_or_unmatched=true`，並直接輸出 final_verdict=EXCLUDE + needs_manual_review=true（因為無法完成 Stage 2）

Step 2) 逐條 criterion 打分（1～5）+ evidence_quotes
- I1：直接引用 Stage1.1 的 pub_ge_2019（不用 quote）
- I2（Transformer-based）：
  - 找模型/架構描述（如 Transformer/BART/T5/PEGASUS/Longformer/LED/GPT/encoder-decoder）
  - 若主要方法明確是 RNN/LSTM/非 Transformer → I2 低分，且 E4 高分
- I3（Summarization）：
  - 找 task/goal/output 定義（summary/minutes/highlights/summarization）
- E3（Extractive focus）：
  - 找 “extractive/abstractive/hybrid/generative” 自述或輸出定義/例子
- E2（Multi-modal input）：
  - 只看「模型輸入」是否包含 audio/image/video features；若只用 transcript 文字需引用原文支持
- E1（Non-English primary dataset）：
  - 若全文明確指出主要 dataset/corpus 語言為非英文 → E1 高分
  - 若未明說 → 依規則視為 English → E1=1（NO），並在 notes 註明
- E5（Secondary research）：
  - 看是否自稱 survey/review/systematic review/scoping/mapping/meta-analysis/SoK/tutorial/overview/roadmap 等
  - 或是否描述文獻檢索/篩選/inclusion-exclusion/PRISMA flow（secondary 的強訊號）

Step 3) 套用 Stage 2 硬規則輸出 final verdict（include/exclude）
- 並輸出：
  - `exclude_reason_primary`：觸發的 exclusion id 或不符合的 inclusion id
  - `needs_manual_review`：若任何 criterion=UNCLEAR 或 fulltext 缺失/對不上 key，則 true

================================================
輸出（必須提供下載）
================================================
A) JSONL：`stage2_final_decisions.jsonl`
- 一行一筆（只包含 stage1_2_verdict in {include, maybe} 的 keys）
- 每筆至少包含：
  - key
  - stage1_2_verdict
  - final_verdict: "include"|"exclude"
  - needs_manual_review: true/false
  - exclude_reason_primary: ["E2", ...] 或 ["I2", ...]
  - criteria_scores（同 Prompt 3 的格式；但 evidence_quotes 主要來自 fulltext）
  - decision_confidence_1to5（整體把握；不是逐條）
  - fulltext_file（對應到哪個 md 檔）
  - fulltext_missing_or_unmatched（true/false）
  - notes
B) CSV：`stage2_final_decisions.csv`
- 至少包含：key, final_verdict, needs_manual_review, I1_score,I2_score,I3_score,E1_score,E2_score,E3_score,E4_score,E5_score, decision_confidence_1to5
C) key 清單：
- `final_include_keys.txt`
- `final_exclude_keys.txt`

================================================
回覆文字（summary）
================================================
請在回覆中提供：
- Stage 2 審查篇數（從 Stage1.2 include/maybe 來的）
- final include/exclude 各自數量
- needs_manual_review 的數量與 key 清單（若太多，只列前 50；完整另存檔）
- 最常見的排除原因前 5 名（按次數）
並提供所有輸出檔案下載連結。
```

## 10. 來源清單

本報告直接依賴以下 repo 檔案；若之後 repo 更新，應以新版檔案重新生成本報告，而不是手動 patch 舊版摘要。

1. `docs/CURRENT_AUTHORITY.md`  
2. `docs/chatgpt_current_status_handoff.md`  
3. `scripts/screening/runtime_prompts/runtime_prompts.json`  
4. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/title_abstract_reviewer.py`  
5. `scripts/screening/vendor/resources/LatteReview/lattereview/agents/fulltext_reviewer.py`  
6. `docs/taxonomy_root_cause_qa.md`  
7. `docs/prompt_only_runtime_realignment_report.md`  
8. `docs/stage1_senior_prompt_tuning_report.md`  
9. `sr_screening_prompts/README.md`  
10. `sr_screening_prompts/sr_specific/02_stage1_2_title_abstract_questions.md`  
11. `sr_screening_prompts/sr_specific/03_stage1_2_criteria_review.md`  
12. `sr_screening_prompts/sr_specific/04_stage2_fulltext_questions.md`  
13. `sr_screening_prompts/sr_specific/05_stage2_criteria_review.md`  
14. `sr_screening_prompts_3stage/README.md`  
15. `sr_screening_prompts_3stage/sr_specific/03_stage1_2_criteria_review.md`  
16. `sr_screening_prompts_3stage/sr_specific/05_stage2_criteria_review.md`  
17. `criteria_mds/README.md`  
18. `criteria_mds/AGENT_PROMPT_generate_question_set_from_criteria.md`  
19. `criteria_stage1/2409.13738.json`  
20. `criteria_stage2/2409.13738.json`  
21. `criteria_stage1/2511.13936.json`  
22. `criteria_stage2/2511.13936.json`  
23. `docs/ChatGPT/evidence_qa_feasibility_analysis_2409_2511.md`  
24. `docs/ChatGPT/next_experiments_criteria_mds_qa_report_2409_2511_zh.md`
