# QA-first v0 Repair Plan / Rerun Plan (Implementation-Ready)

## 1. Current-State Recap

1. current runtime prompt authority 仍是 `scripts/screening/runtime_prompts/runtime_prompts.json`。  
2. current production criteria authority 仍是：
   - Stage 1: `criteria_stage1/<paper_id>.json`
   - Stage 2: `criteria_stage2/<paper_id>.json`
3. current metrics authority 仍是 production baseline：
   - `2409.13738`: Stage 1 F1 `0.7500`, Combined F1 `0.8235`
   - `2511.13936`: Stage 1 F1 `0.7407`, Combined F1 `0.7692`
4. `qa_first_v0_2409_2511_2026-03-18` 是 experiment-only bundle，不是 production replacement。
5. current workflow invariants 不變：
   - Stage 1 兩位 junior reviewer
   - 兩位都 `>=4` => include
   - 兩位都 `<=2` => exclude
   - 其餘送 `SeniorLead`
   - `SeniorLead` 必須保留
6. 本文件所有修法都以 workflow layer 為主：
   - prompting
   - evidence extraction
   - synthesis
   - handoff
   - evaluator / adjudication
   不是 formal criteria rewrite。

---

## 2. Confirmed Diagnosis

下面只保留「被結果支持」或「至少被 raw case inspection 直接看到」的 diagnosis。

### 2.1 已驗證結論總表

| # | 結論 | 狀態 | 證據層級 | 依據 |
|---|---|---|---|---|
| 1 | `2409` 的 gain 主要發生在 Stage 2，不是 Stage 1 | 成立 | confirmed by metrics | `2409` baseline Stage 1 F1 `0.7500`，`qa-only` `0.7368`，`qa+synthesis` `0.7119`；但 Combined 從 baseline `0.8235` 升到 `0.8085` / `0.8333` |
| 2 | `2409 qa+synthesis` 的 Combined F1 高於 baseline 與 qa-only | 成立 | confirmed by metrics | `0.8333 > 0.8085 > 0.8235` |
| 3 | `2511` 的 regression 主要是 Stage 1 recall collapse，不是 FP 爆炸 | 成立 | confirmed by metrics | baseline Stage 1 `tp/fp/fn = 29/8/1`；`qa-only = 23/1/7`；`qa+synthesis = 24/1/6` |
| 4 | `2511 qa+synthesis` 存在 contamination / binding 問題 | 成立 | confirmed by case inspection | `anastassiou2024seed`、`lin2004rouge`、`google_scholar_hindex` 等 case 出現 review title / `Systematic Analysis` 洩漏 |
| 5 | `honkisz2018concept` 不應再被當成 `2409 qa+synthesis` 的 target-boundary exclusion 代表 case | 成立 | confirmed by case inspection | `2409 qa+synthesis` Stage 2 中 `honkisz2018concept` 最終是 `include (junior:5,5)` |
| 6 | `elallaoui2018automatic` 才是較好的 `2409` target-boundary exclusion 代表 case | 成立 | confirmed by case inspection | baseline / qa-only Stage 2 include；`qa+synthesis` Stage 2 由 senior exclude，理由是 UML use case diagrams 不屬 canonical process-model family |
| 7 | `2511` 的 repair focus 應先放在 contamination / binding、Stage 1 evaluator mapping、unresolved preference evidence defer strategy | 成立 | confirmed by metrics + case inspection | recall collapse 主要在 Stage 1；且 qasynthesis 有明顯 review-title 洩漏 |
| 8 | `2409` 的 repair focus 應放在 Stage 2 canonical closure 與 publication-form / empirical-validation closure stability | 成立 | confirmed by metrics + case inspection | `elallaoui` 顯示 target-boundary gain；`kourani` / `neuberger` / `grohs` 顯示 publication-form closure 仍不穩 |

### 2.2 額外確認

#### A. `2511` contamination 是真的，而且不是單一髒 case

- `2511 qa+synthesis` Stage 1 raw 裡，至少有 **9 筆** case 出現 `Systematic Analysis` 這種 review-title 洩漏痕跡：
  - `anastassiou2024seed`
  - `cideron2024musicrl`
  - `gao2023scaling`
  - `google_scholar_hindex`
  - `lin2004rouge`
  - `mckeown2011semaine`
  - `singhal2023long`
  - `stiennon2020learning`
  - `wu2025adaptive`
- Fulltext 端至少還有 **1 筆**：`wu2025adaptive`
- 這不是單純 wording 不夠好，而是 evidence object binding / prompt payload hygiene 出問題。

標示：**confirmed by case inspection**

#### B. `2511` Stage 1 的問題不是只有 qasynthesis contamination

就算不看 qasynthesis，`qa-only` 也已經出現 Stage 1 recall collapse：

- baseline Stage 1: `29/8/1`
- `qa-only` Stage 1: `23/1/7`

代表 `2511` 還有另一層問題：  
同一套 evaluator rubric 在 `2511` 會把「title/abstract 尚未講完整，但其實應該 defer 到 Stage 2」的 case 過早壓成 exclude。

標示：**confirmed by metrics**

#### C. `2409` 的 improvement 不能解讀成 Stage 1 變聰明

- `2409 qa-only` Stage 1 F1 低於 baseline
- `2409 qa+synthesis` Stage 1 F1 也低於 baseline
- gain 幾乎全部來自 Stage 2

標示：**confirmed by metrics**

### 2.3 仍屬推論、不能寫成已驗證事實的部分

| 主張 | 狀態 | 原因 |
|---|---|---|
| `2409_hybrid_stage1_qa_only__stage2_qa_synthesis` 一定會贏過 current best | plausible but not fully verified | 目前只是合理假設，尚未 rerun |
| 只做 `2511` decontamination 就一定足以把 Combined 拉回 baseline | plausible but not fully verified | contamination 很大，但 `qa-only` 也已經顯示 mapping 問題 |
| `2409` publication-form closure 就是目前殘存誤差的最大來源 | plausible but not fully verified | case inspection 強烈支持，但尚未逐筆對 gold 做完整 attribution |

---

## 3. Issue Taxonomy

### 3.1 Global to v0 experiment bundle

| Issue | 為什麼屬於 global | 影響 stage | 問題型別 |
|---|---|---|---|
| hardcoded sample schema hints 把 `2409/stage1/qa-only` 寫死進 prompt context | `run_experiment.py` 全域載入 `sample_reviewer_qa_output.json` / `sample_synthesis_output.json` / `sample_criteria_evaluation_output.json` / `sample_senior_output.json` | Stage 1 + Stage 2，尤其 qasynthesis | hygiene |
| full QA JSON 被 verbatim 注入 prompt，包含 `review.title` / `review.topic` | `_base_context()` 把 `QA_JSON_CONTENT` 整包送進去；`2511` review title 正好含 `Preference-Based Learning in Audio Applications: A Systematic Analysis` | Stage 1 為主，Stage 2 亦可能受污染 | hygiene |
| runner 沒有 binding assertions / fail-fast | 所有 arm 共用同一個 `run_experiment.py`，目前不檢查 `paper_id` / `stage` / `workflow_arm` / title / provenance | Stage 1 + Stage 2，尤其 qasynthesis | hygiene |
| synthesis schema 太薄，identity/provenance 欄位不足 | `minimal_synthesis_schema.yaml` 沒有 `candidate_key`、`source_record_provenance` 等欄位 | Stage 1 -> Stage 2 handoff | hygiene |
| evaluator prompt 是 shared implementation | `06` / `07` 都是共用 evaluator 模板 | Stage 1 + Stage 2 | implementation-global；行為影響 paper-specific |

### 3.2 `2409`-specific

| Issue | 為什麼屬於 `2409` | 影響 stage | 問題型別 |
|---|---|---|---|
| target-object family closure 要穩定保住 | `elallaoui2018automatic` 是 `2409` qasynthesis precision gain 的代表 case | Stage 2 | precision |
| publication-form / preprint closure 不穩 | `kourani_process_modelling_with_llm`、`neuberger_data_augment`、`grohs2023large` 在 qa-only / qasynthesis 間有晃動 | Stage 2 | precision + recall |
| empirical-validation / primary-research closure 需拆開看 | `2409` Stage 2 criteria 同時要求 thematic fit + concrete method + empirical validation + publication form | Stage 2 | closure stability |
| `goossens2023extracting` 的髒欄位屬於 hygiene warning，不應當成主效應 case | 這筆最後仍 include，不是主要 performance driver | Stage 2 | hygiene warning |

### 3.3 `2511`-specific

| Issue | 為什麼屬於 `2511` | 影響 stage | 問題型別 |
|---|---|---|---|
| Stage 1 evaluator mapping 對 unresolved preference evidence 太 exclusion-leaning | `qa-only` 已從 baseline `29/8/1` 掉到 `23/1/7`，且 maybe-count 從 15 掉到 1 | Stage 1 | recall |
| qasynthesis 容易把 review title/topic 誤灌進 candidate-level reasoning | `anastassiou2024seed`、`lin2004rouge`、`google_scholar_hindex` 等明顯中招 | Stage 1，少量波及 Stage 2 | hygiene + recall |
| defer strategy 不夠：RL loop / ratings conversion / ranking signal 在 title/abstract 常不完整 | `chu2024qwen2`、`huang2025step`、`parthasarathy2018preference` 等顯示 Stage 1 太早排掉 TP | Stage 1 | recall |
| audio / multimodal / evaluation-only 的 negative closure 太快 | 對 `2511` 來說，「沒講清楚」不等於「只做 evaluation」 | Stage 1 | recall |

---

## 4. Draft Repair Framing

先給一版刻意粗的 repair framing，之後再自我修正。

1. 先修全域 hygiene，再碰 paper-specific mapping。
2. `2511` 先做 decontamination / binding repair，不要一開始就大改 evaluator。
3. `2409` 優先修 Stage 2 closure，而不是重做 Stage 1 QA。
4. evaluator 不先做 global rewrite，先做 `2511` Stage 1 override。
5. hybrid rerun 放最後，不要一開始就跑 compound experiment。

這版 framing 的核心意圖是：  
**先把 confound 清掉，再去測行為修正。**

---

## 5. Self-Critique

上面的 Draft Repair Framing 方向是對的，但還不夠 implementation-ready，主要有四個問題：

1. 還沒有把「全域 hygiene」拆到檔案 / 欄位 / assertion contract。  
2. 還沒有清楚回答：`2511 Stage 1 evaluator mapping` 到底是 global implementation、還是 SR-specific behavior。  
3. 還沒有把 template patch 寫到可直接交給 Codex 的 wording 層。  
4. 還沒有把 rerun matrix 變成真正可執行的 ablation 設計。

所以 final plan 必須往下壓到：

- 哪些檔要改
- 哪些 placeholder 要加
- 哪些 sample/hint 要換
- 哪些 mismatch 要 fail fast
- 哪些 rerun 要先做，哪些後做

---

## 6. Revised Final Repair Plan

### 6.1 先回答關鍵問題：`2511 Stage 1 evaluator mapping` 是 global 還是 SR-specific？

#### (1) implementation layer

**實作層是 global。**

原因：

- `06_criteria_evaluator_from_qa_only_TEMPLATE.md` 是共用 evaluator prompt
- `07_criteria_evaluator_from_synthesis_TEMPLATE.md` 也是共用 evaluator prompt
- `run_experiment.py` 用同一套 runner path 去喂兩篇 SR

所以從「程式和模板是不是共用」來看，答案是：**global shared implementation**。

#### (2) behavior layer

**行為層是 SR-specific in severity。**

為什麼同一套 mapping 在 `2511` 特別容易出事、在 `2409` 沒那麼嚴重？

- `2409` 的 core-fit（text -> process model / process representation）在標題與摘要常比較直接可見；而且即使 Stage 1 沒變好，Stage 2 也有明顯 closure gain。
- `2511` 的 core-fit 不是只有「在 audio domain」，還牽涉：
  - pairwise / ranking / A/B preference
  - numeric ratings 是否轉成 relative preference
  - RL loop 是否真的作用於 audio model learning
  - learning vs evaluation-only 的界線
- 這些訊號在 title/abstract 往往只露一半。  
  如果 evaluator 把「還沒看到」直接映成 `1` 或 `2`，就會把應該 defer 的 TP 提早砍掉。

所以答案不是「mapping 只有 `2511` 有」，而是：

- **shared implementation 是 global**
- **failure pattern 的嚴重度是 `2511`-specific**

#### (3) repair strategy layer

**下一步先做 `2511-specific override`，不要先做全域 evaluator rewrite。**

理由：

1. `2409` 目前主要 gain 在 Stage 2，不是 Stage 1 mapping。  
2. `2511` 的 failure mode 很明顯是「unresolved preference evidence 被過早當成 negative」。  
3. 如果先做 global loosening，風險是把其他 paper 的 Stage 1 precision 一起鬆掉。  
4. 先做 `2511`-specific Stage 1 evaluator addendum，可以在不動 formal criteria 的情況下，把「defer vs exclude」邊界修正到比較合理的位置。  
5. 等 decontamination 完成、`2511` rerun 看過，再決定是否需要抽象成 global policy。

### 6.2 Workstream 1 - `2511 decontamination / binding repair`

**Objective**  
先把 `2511 qasynthesis` 的資料混線問題清掉，讓下一輪 rerun 至少不再把 SR title/topic 當 candidate evidence。

**Why this fix matters**  
如果連 `review.title = Preference-Based Learning in Audio Applications: A Systematic Analysis` 都會跑進 candidate-level reasoning，那後面談 evaluator mapping 幾乎都是被 confound 污染的。

**Exact files to touch**

1. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/03_stage1_qa_synthesis_reviewer_TEMPLATE.md`
2. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/05_synthesis_builder_TEMPLATE.md`
3. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
4. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/prompt_manifest.yaml`
5. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/tools/run_experiment.py`
6. 取代目前 hardcoded sample hints：
   - `.../samples/sample_reviewer_qa_output.json`
   - `.../samples/sample_synthesis_output.json`
   - `.../samples/sample_criteria_evaluation_output.json`
   - `.../samples/sample_senior_output.json`

**What to change**

- 不再把完整 `QA_JSON_CONTENT` verbatim 丟進 prompt。
- 改成由 runner 先產生 `QA_PROMPT_PAYLOAD_JSON`，只保留：
  - `paper_id`
  - `stage`
  - `question_groups`
  - `reviewer_guardrails`
  - `handoff_policy` / `conflict_handling_policy`
  - `non_goals`
- 明確禁止把：
  - `review.title`
  - `review.topic`
  - `source_basis`
  - criteria `topic`
  當成 candidate evidence。
- sample output hints 改成 **generic YAML hints**，不能再有 literal `2409.13738` / `stage1` / `qa-only`。
- runner 加 binding assertions；identity mismatch 或 review-title leakage 直接 retry，仍失敗就 fail fast。

**Global or SR-specific?**  
以 implementation 來說是 **global**；以效益優先順序來說，先救 `2511`。

**Expected metric movement**

- 首先期待 hygiene 指標改善，不是先看 F1。
- `2511 qasynthesis` Stage 1 recall 應至少不再被 review-title contamination 壓低。
- 目標不是「一次回 baseline」，而是先做到 **zero contamination / zero identity drift**。

**Main regression risk**

- 如果 sanitized payload 裁太兇，模型可能少掉必要 QA context。  
- 緩解方法：保留 question groups、guardrails、handoff policy、non_goals，不是只丟 bare questions。

### 6.3 Workstream 2 - `2511 Stage 1 evaluator mapping repair`

**Objective**  
把 `2511` Stage 1 中「尚未看清 preference mechanism，但其實不該提早 exclude」的 case 拉回 `3 / maybe / SeniorLead`。

**Why this fix matters**  
`2511` regression 的主因不是 FP 爆炸，而是 Stage 1 recall collapse。

**Exact files to touch**

1. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/06_criteria_evaluator_from_qa_only_TEMPLATE.md`
2. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
3. 新增外部 policy 檔：
   - `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/policies/2511_stage1_evaluator_policy.md`
4. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/prompt_manifest.yaml`
5. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/tools/run_experiment.py`

**What to change**

- evaluator template 保留 shared rubric，但插入一段 **paper-specific addendum placeholder**。
- 對 `2511 stage1` 注入以下政策：
  1. 若 `audio_domain` 為 present，且沒有 survey/review 明確負證據，則 preference mechanism 只有 unresolved 時，優先給 `3`，不要直接 `1/2`。
  2. abstract 若明示 RL for audio model，即使沒寫 pairwise ranking，也不能直接當 absent。
  3. numeric ratings / ordinal labels / relative judgments，只要有 plausible learning use，就應留在 unresolved-positive，不可因細節缺失直接排除。
  4. 「evaluation-only exclusion」必須要求正向負證據：  
     明確看出 preferences 只用於 evaluation/reporting，而非只是 abstract 沒講清楚 training loop。

**Global or SR-specific?**  
**SR-specific behavior fix**。  
實作上是往 shared evaluator 插外部 addendum，但先只對 `2511 stage1` 開。

**Expected metric movement**

- `2511` Stage 1 recall 上升
- maybe-count 從 `1` 回升
- direct junior excludes 減少
- Combined F1 應高於 current `qa+synthesis = 0.8519`

**Main regression risk**

- 太鬆會把 FP 拉回來。  
- 所以 stop condition 要放在「precision 不得大幅掉水」。

### 6.4 Workstream 3 - `2409 Stage 2 closure stabilization`

**Objective**  
保留 `2409 qasynthesis` 在 target-boundary 上的好處，同時減少 publication-form / empirical-validation closure 的晃動。

**Why this fix matters**  
`2409` 的 gain 主要在 Stage 2；所以修法應集中在 Stage 2 closure，而不是去重寫 Stage 1 QA。

**Exact files to touch**

1. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/05_synthesis_builder_TEMPLATE.md`
2. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
3. 視需要同步到：
   - `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/06_criteria_evaluator_from_qa_only_TEMPLATE.md`
4. 新增外部 policy 檔：
   - `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/policies/2409_stage2_closure_policy.md`
5. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/schemas/minimal_synthesis_schema.yaml`

**What to change**

- 對 `2409 stage2` 注入 closure policy：
  1. 先分開判：
     - thematic fit / target-object family
     - publication form
     - primary research
     - concrete method
     - empirical validation
  2. 如果 target object 明確落在非 canonical family（例如 UML use case diagrams），可直接 exclusion-lean。
  3. 如果 thematic fit 很強，但 publication-form 只有 unresolved，不要讓 publication-form 一條把整體直接壓到 `1/2`；優先給 `3` 讓 senior 收斂。
  4. empirical validation 與 publication form 要拆開，不可互相覆蓋。
- Stage 2 synthesis object 必須把這些 closure bucket 分欄表達，而不是只給一段混合判斷。

**Global or SR-specific?**  
**`2409`-specific**

**Expected metric movement**

- 保住 `elallaoui2018automatic` 這類 target-boundary precision gain
- 減少 `kourani` / `neuberger` / `grohs` 這類 publication-form wobble

**Main regression risk**

- 如果 publication-form 被放太鬆，可能把真 preprint-only negative 又收回來。  
- 所以這不是 criteria 改寫，而是「有主題正證據但 publication-form 尚未確認」時先走 `3`。

### 6.5 Workstream 4 - `synthesis / handoff hygiene repair`

**Objective**  
讓 qasynthesis 物件與 stage handoff 變成 identity-clean、provenance-traceable、可驗證的 workflow object。

**Why this fix matters**  
現在不是只有 `2511` contamination，`2409` 的 qasynthesis 路徑也有 metadata drift。  
只是不像 `2511` 那麼直接傷害 decision semantics。

**Exact files to touch**

1. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/05_synthesis_builder_TEMPLATE.md`
2. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/templates/prompt_manifest.yaml`
3. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/schemas/minimal_synthesis_schema.yaml`
4. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/schemas/qa_output_contract.yaml`
5. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/schemas/criteria_evaluation_output_contract.yaml`
6. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/schemas/senior_output_contract.yaml`
7. `qa_first_experiments/qa_first_experiment_v0_2409_2511_2026-03-18/tools/run_experiment.py`

**What to change**

- 所有 reviewer / synthesis / evaluator / senior output contract 都新增：
  - `candidate_key`
  - `candidate_title`
  - `source_record_provenance`
- synthesis object 再新增：
  - `prior_stage_reference`
  - `support_source_kind`
- top-level identity 欄位不應讓模型自由發揮：
  - `paper_id`
  - `candidate_key`
  - `candidate_title`
  - `stage`
  - `arm`
  - `source_record_provenance`
- runner 要把這些欄位當 contract 驗證。

**Global or SR-specific?**  
**global**

**Expected metric movement**

- 先期待 hygiene zero-defect
- 其次才期待 `2511 qasynthesis` 回正、`2409 qasynthesis` 更穩

**Main regression risk**

- schema 改動過大會讓 prompt / parser 同步成本上升。  
- 所以 identity/provenance 只加最必要欄位，不要一次擴太多。

---

## 7. Template-Level Prompt Changes

這一節只談 template-level patch，不把 prompt 本體塞回 `.py`。

### 7.1 `01_stage1_qa_only_reviewer_TEMPLATE.md`

**為什麼要改**  
這個模板雖然不是 contamination 主戰場，但它目前沒有清楚區分：

- SR id
- candidate key
- candidate title
- review-level metadata vs candidate evidence

這會讓 evaluator / reviewer 容易混淆 `paper_id` 的語義。

**建議新增的 placeholder**

- `SR_PAPER_ID`
- `CANDIDATE_KEY`
- `CANDIDATE_TITLE`
- `QA_PROMPT_PAYLOAD_JSON`
- `OUTPUT_IDENTITY_CONTRACT_JSON`

**建議 patch 位置**  
在 `## Review Target` 與 `## Hard Rules` 中各補一段。

**建議新 wording**

```md
## Review Target

- `sr_paper_id`: `{{SR_PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `stage`: `stage1`
- `workflow_arm`: `qa-only`

## Inputs

### QA Prompt Payload
Path: `{{QA_JSON_PATH}}`

```json
{{QA_PROMPT_PAYLOAD_JSON}}
```

## Hard Rules

- `sr_paper_id` is the review id, not the candidate record key.
- Candidate identity is defined only by:
  - `candidate_key`
  - `candidate_title`
- Review-level metadata in the QA asset or criteria file (for example review title, review topic, source basis, or review headings) is context about the review, not evidence about the candidate paper.
- Never copy review title/topic text into candidate evidence.
- If a phrase does not appear in the candidate title, abstract, metadata, or allowed stage input, you may not use that phrase as supporting evidence.
- Use missing evidence as `unclear`; do not convert missing detail into a new hard exclusion.
```

**Global or SR-specific?**  
**global**

---

### 7.2 `03_stage1_qa_synthesis_reviewer_TEMPLATE.md`

**為什麼要改**  
這是 `2511` contamination 的主要入口之一。  
需要同時補 identity contract、review-level contamination guard、以及 `2511` unresolved preference evidence 的 defer stance。

**建議新增的 placeholder**

- `SR_PAPER_ID`
- `CANDIDATE_KEY`
- `CANDIDATE_TITLE`
- `QA_PROMPT_PAYLOAD_JSON`
- `OUTPUT_IDENTITY_CONTRACT_JSON`
- `PAPER_SPECIFIC_STAGE1_POLICY_MD`

**建議 patch 位置**  
在 `## Inputs` 後補 identity 區塊；在 `## Hard Rules` 前後加 policy 段。

**建議新 wording**

```md
## Identity Contract

- `sr_paper_id`: `{{SR_PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `stage`: `stage1`
- `workflow_arm`: `qa+synthesis`

The review title/topic in the criteria or QA asset is not candidate evidence.

## QA Prompt Payload
Path: `{{QA_JSON_PATH}}`

```json
{{QA_PROMPT_PAYLOAD_JSON}}
```

## Paper-Specific Stage 1 Policy
{{PAPER_SPECIFIC_STAGE1_POLICY_MD}}

## Hard Rules

- Never infer survey/review status from the review title or review topic.
- `survey_review_negative = present` only when the candidate title/abstract itself contains survey/review language or equivalent direct evidence.
- If audio-domain fit is present but preference mechanism, ratings conversion, or RL-loop evidence is unresolved at Stage 1, prefer `unclear` over `absent`.
- Do not fill `candidate_synthesis_fields` from review-level metadata.
- Do not build negative certainty from short abstracts.
```

**Global or SR-specific?**  
base guard 是 **global**；`PAPER_SPECIFIC_STAGE1_POLICY_MD` 可對 `2511` 專用。

---

### 7.3 `05_synthesis_builder_TEMPLATE.md`

**為什麼要改**  
這是 handoff / synthesis hygiene 的核心模板，必須先鎖死 identity 與 provenance，再談 field normalization。

**建議新增的 placeholder**

- `SR_PAPER_ID`
- `CANDIDATE_KEY`
- `CANDIDATE_TITLE`
- `SOURCE_RECORD_PROVENANCE_JSON`
- `OUTPUT_IDENTITY_CONTRACT_JSON`

**建議 patch 位置**  
在 `## Inputs` 與 `## Hard Rules` 補 identity/provenance 合約。

**建議新 wording**

```md
## Inputs

- `sr_paper_id`: `{{SR_PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `target_stage`: `{{TARGET_STAGE}}`
- `arm`: `qa+synthesis`

### Source Record Provenance
```json
{{SOURCE_RECORD_PROVENANCE_JSON}}
```

## Identity Contract

Copy the following values exactly into the synthesis object:

- `paper_id = {{SR_PAPER_ID}}`
- `candidate_key = {{CANDIDATE_KEY}}`
- `candidate_title = {{CANDIDATE_TITLE}}`
- `stage = {{TARGET_STAGE}}`
- `arm = qa+synthesis`

## Hard Rules

- Use only candidate-level evidence from `CURRENT_QA_OUTPUT_JSON` and `PRIOR_STAGE_OUTPUT_JSON`.
- Ignore review title, review topic, source basis, criteria topic, and review headings when normalizing field values.
- If a normalized field is not supported by candidate quotes/locations or prior-stage traceable evidence, set `unclear` or `absent`; never backfill from SR-level metadata.
- Preserve provenance:
  - `source_record_provenance`
  - `derived_from_qids`
  - `stage_handoff_status`
- `candidate_title` must match the prompt header exactly.
```

**Global or SR-specific?**  
**global**

---

### 7.4 `06_criteria_evaluator_from_qa_only_TEMPLATE.md`

**為什麼要改**  
`2511 qa-only` 已證明 shared evaluator 在 Stage 1 會把 unresolved preference evidence 壓成 exclude。  
但不建議直接全域改 rubric，因此要做 shared prompt + external per-paper policy addendum。

**建議新增的 placeholder**

- `SR_PAPER_ID`
- `CANDIDATE_KEY`
- `CANDIDATE_TITLE`
- `PAPER_SPECIFIC_STAGE1_POLICY_MD`
- `PAPER_SPECIFIC_STAGE2_POLICY_MD`
- `OUTPUT_IDENTITY_CONTRACT_JSON`

**建議 patch 位置**  
在 `## Scoring Rubric` 後新增 `Stage-Specific Policy Layer`。

**建議新 wording**

```md
## Identity Contract

- `sr_paper_id`: `{{SR_PAPER_ID}}`
- `candidate_key`: `{{CANDIDATE_KEY}}`
- `candidate_title`: `{{CANDIDATE_TITLE}}`
- `stage`: `{{STAGE}}`
- `arm`: `qa-only`

## Scoring Rubric Addendum

- Distinguish missing evidence from contradictory evidence.
- A Stage 1 score of `1` or `2` requires direct exclusionary evidence or a clear absence of core fit, not merely an underspecified abstract.
- When evidence is unresolved but still plausibly compatible with the current criteria, prefer `3` and route to adjudication instead of forcing exclusion.

## Paper-Specific Policy
{{PAPER_SPECIFIC_STAGE1_POLICY_MD}}
{{PAPER_SPECIFIC_STAGE2_POLICY_MD}}
```

**`2511` Stage 1 專用 addendum 建議內容**

```md
### 2511 Stage 1 Evaluator Policy

- If the candidate is clearly within the audio domain and there is no direct survey/review exclusion signal, unresolved preference evidence should default to `3`, not `1/2`.
- An RL training loop for an audio model is sufficient to avoid Stage 1 exclusion even when pairwise comparison wording is not explicit in the abstract.
- Numeric ratings, ordinal labels, or relative judgments remain potentially eligible when they plausibly feed learning rather than evaluation only.
- "Evaluation-only" exclusion requires direct evidence that preferences are used solely for evaluation/reporting and not for model learning.
```

**`2409` Stage 2 在 `06` 不一定要放強 patch**  
若 qa-only Stage 2 也要修 publication-form closure，可在這裡放較輕量 addendum；否則主 patch 放在 `07` 即可。

**Global or SR-specific?**  
shared wording 是 **global**；addendum 是 **SR-specific**

---

### 7.5 `07_criteria_evaluator_from_synthesis_TEMPLATE.md`

**為什麼要改**  
這個模板同時牽涉：

- `2511` decontamination / invalid synthesis refusal
- `2409` Stage 2 closure policy

所以需要比 `06` 更嚴格。

**建議新增的 placeholder**

- `SR_PAPER_ID`
- `CANDIDATE_KEY`
- `CANDIDATE_TITLE`
- `PAPER_SPECIFIC_STAGE1_POLICY_MD`
- `PAPER_SPECIFIC_STAGE2_POLICY_MD`
- `OUTPUT_IDENTITY_CONTRACT_JSON`

**建議 patch 位置**  
在 `## Inputs` 與 `## Task` 之間加 identity validation rule；在 rubric 後加 addendum。

**建議新 wording**

```md
## Identity Contract

Expected identity:

- `paper_id = {{SR_PAPER_ID}}`
- `candidate_key = {{CANDIDATE_KEY}}`
- `candidate_title = {{CANDIDATE_TITLE}}`
- `stage = {{STAGE}}`
- `arm = qa+synthesis`

Do not semantically interpret an invalid synthesis object.

## Scoring Rubric Addendum

- Treat synthesis identity fields as a contract, not as soft hints.
- Ignore any field record whose support quotes/locations do not come from candidate text, metadata, or prior-stage traceable handoff.
- Never use SR title, criteria topic, or QA asset review headings as candidate evidence.
- Distinguish unresolved evidence from contradictory evidence before assigning `1` or `2`.

## Paper-Specific Policy
{{PAPER_SPECIFIC_STAGE1_POLICY_MD}}
{{PAPER_SPECIFIC_STAGE2_POLICY_MD}}
```

**`2409` Stage 2 專用 addendum 建議內容**

```md
### 2409 Stage 2 Closure Policy

- Separate thematic fit, publication form, primary research status, concrete method, and empirical validation into distinct closure checks.
- A clear non-canonical target object (for example UML use case diagrams rather than process-model/process-representation extraction) may justify exclusion even when other research-quality criteria are satisfied.
- When thematic fit is strong but publication-form evidence remains unresolved rather than contradicted, prefer `3` over `1/2`.
- Do not let publication-form uncertainty erase strong positive evidence for concrete method or empirical validation.
```

**Global or SR-specific?**  
shared guard 是 **global**；addendum 依 paper/stage 注入。

---

### 7.6 `prompt_manifest.yaml`

**為什麼要改**  
目前 required placeholders 不足以支援 identity contract / sanitized QA payload / paper-specific addenda。

**建議改動**

新增：

```yaml
required_placeholders:
  - SR_PAPER_ID
  - CANDIDATE_KEY
  - CANDIDATE_TITLE
  - QA_PROMPT_PAYLOAD_JSON
  - SOURCE_RECORD_PROVENANCE_JSON
  - OUTPUT_IDENTITY_CONTRACT_JSON
  - PAPER_SPECIFIC_STAGE1_POLICY_MD
  - PAPER_SPECIFIC_STAGE2_POLICY_MD
```

並把 `PAPER_ID` / `PAPER_TITLE` 標成 deprecated，逐步從模板本體移除。

**Global or SR-specific?**  
**global**

---

### 7.7 哪些 template 暫時不需要大改

#### `02_stage2_qa_only_reviewer_TEMPLATE.md`
#### `04_stage2_qa_synthesis_reviewer_TEMPLATE.md`

這兩個模板需要做的主要是：

- identity contract
- 不可複用 stage1 的髒 metadata
- stage2 fulltext evidence 優先於 stage1 片段

但不需要先做大的語義重寫。  
原因是這輪主要 regression 並不來自 stage2 reviewer prompt 本身，而是：

- `2511` Stage 1 recall collapse
- qasynthesis contamination
- `2409` evaluator closure stability

---

## 8. Code-Level / Runner-Level Changes

### 8.1 `run_experiment.py` 必改項目總覽

| 區塊 | 改動 |
|---|---|
| `PromptAssets.__init__()` | 停止載入 hardcoded sample JSON hints；改讀 generic YAML hints |
| `_base_context()` | 不再傳 full QA JSON；改傳 sanitized `QA_PROMPT_PAYLOAD_JSON`；新增 identity / provenance placeholders |
| model call wrapper | 加上 validation / retry / fail-fast |
| stage1 / stage2 runners | 在每一個 reviewer / synthesis / evaluator / senior call 後驗證 output contract |
| CLI | 新增 isolated rerun / hybrid rerun 所需 flags |

### 8.2 取代 hardcoded sample hints

**目前問題**  
`run_experiment.py` 在 `PromptAssets.__init__()` 載入：

- `sample_reviewer_qa_output.json`
- `sample_synthesis_output.json`
- `sample_criteria_evaluation_output.json`
- `sample_senior_output.json`

這些 sample 檔直接寫死：

- `paper_id = 2409.13738`
- `stage = stage1`
- `workflow_arm = qa-only`

這很可能就是 qasynthesis metadata drift 的來源之一。

**具體修法**

1. 新增 generic YAML hints：
   - `qa_first_experiments/.../schemas/hints/reviewer_qa_output_hint.yaml`
   - `.../schemas/hints/synthesis_output_hint.yaml`
   - `.../schemas/hints/criteria_evaluation_output_hint.yaml`
   - `.../schemas/hints/senior_output_hint.yaml`
2. hints 只能放欄位結構，不放 literal `2409/stage1/qa-only`。
3. `PromptAssets.__init__()` 改讀這四個 YAML hint 檔，而不是 sample JSON。

### 8.3 `_base_context()` 要改什麼

**目前問題**

- `PAPER_ID` 其實是 SR id，不是 candidate key
- `PAPER_TITLE` 其實是 candidate title
- `QA_JSON_CONTENT` 是整包 seed QA JSON，會把 `review.title` / `review.topic` 一起送進 prompt

**建議改法**

新增 helper：

```python
def _sanitized_qa_prompt_payload(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": asset["paper_id"],
        "stage": asset["stage"],
        "question_groups": asset.get("question_groups", []),
        "reviewer_guardrails": asset.get("reviewer_guardrails", []),
        "handoff_policy": asset.get("handoff_policy", []),
        "conflict_handling_policy": asset.get("conflict_handling_policy", []),
        "non_goals": asset.get("non_goals", []),
    }
```

然後 `_base_context()` 改成提供：

```python
{
    "SR_PAPER_ID": paper_id,
    "CANDIDATE_KEY": str(record.get("key") or ""),
    "CANDIDATE_TITLE": _safe_title(record.get("title") or record.get("query_title")),
    "QA_PROMPT_PAYLOAD_JSON": _json_text(_sanitized_qa_prompt_payload(qa_asset)),
    "SOURCE_RECORD_PROVENANCE_JSON": _json_text({
        "key": record.get("key"),
        "source": record.get("source"),
        "source_id": record.get("source_id"),
        "match_status": record.get("match_status"),
        "fulltext_candidate_path": str(_fulltext_path(...)),
    }),
    "OUTPUT_IDENTITY_CONTRACT_JSON": _json_text({
        "paper_id": paper_id,
        "candidate_key": str(record.get("key") or ""),
        "candidate_title": _safe_title(...),
        "stage": stage,
        "arm": arm,
        "qa_source_path": str(qa_asset_path.relative_to(REPO_ROOT)),
    }),
    "PAPER_SPECIFIC_STAGE1_POLICY_MD": ...,
    "PAPER_SPECIFIC_STAGE2_POLICY_MD": ...,
}
```

並逐步停用：

- `PAPER_ID`
- `PAPER_TITLE`
- `QA_JSON_CONTENT`

### 8.4 必加的 validation / fail-fast contract

這一段不能只寫「加 assertion」，要明確列 contract。

#### A. reviewer output contract

`QAReviewOutput` 必須滿足：

- `paper_id == expected_sr_paper_id`
- `candidate_key == expected_candidate_key`  **(新欄位)**
- `candidate_title == expected_candidate_title`  **(新欄位)**
- `stage == expected_stage`
- `workflow_arm == expected_arm`
- `qa_source_path == expected_relative_qa_path`
- `source_record_provenance.key == expected_candidate_key`  **(新欄位，若加入)**

#### B. synthesis output contract

`SynthesisOutput` 必須滿足：

- `paper_id == expected_sr_paper_id`
- `candidate_key == expected_candidate_key`
- `candidate_title == expected_candidate_title`
- `stage == expected_stage`
- `arm == expected_arm`
- `source_record_provenance.key == expected_candidate_key`
- `field_records` 至少覆蓋 `minimal_synthesis_schema.yaml` 對應 paper 的 required fields
- `paper_title` 這個 legacy 名稱若還保留，必須與 `candidate_title` 完全一致；否則直接廢掉 `paper_title`，改統一為 `candidate_title`

#### C. evaluator output contract

`CriteriaEvaluationOutput` 必須滿足：

- `paper_id == expected_sr_paper_id`
- `candidate_key == expected_candidate_key`
- `candidate_title == expected_candidate_title`
- `stage == expected_stage`
- `arm == expected_arm`

#### D. senior output contract

`SeniorOutput` 必須滿足：

- `paper_id == expected_sr_paper_id`
- `candidate_key == expected_candidate_key`
- `candidate_title == expected_candidate_title`
- `stage == expected_stage`
- `arm == expected_arm`

### 8.5 哪些 mismatch 要直接 fail fast

| mismatch | 處理方式 |
|---|---|
| `paper_id` mismatch | retry up to N 次；仍失敗 => fail fast |
| `candidate_key` mismatch | retry；仍失敗 => fail fast |
| `candidate_title` mismatch | retry；仍失敗 => fail fast |
| `stage` mismatch | retry；仍失敗 => fail fast |
| `workflow_arm` / `arm` mismatch | retry；仍失敗 => fail fast |
| `qa_source_path` mismatch | retry；仍失敗 => fail fast |
| synthesis/evaluator/senior 內出現 review-level phrase，但 candidate text 不含該 phrase | 標為 contamination；retry；仍失敗 => fail fast |

### 8.6 contamination 檢查不要只寫 `2511` 特例

**不要只 hard-code `Systematic Analysis`。**

建議 runner 從 QA asset / criteria 讀出 review-level strings：

- `qa_asset["review"]["title"]`
- `qa_asset["review"]["topic"]`
- `criteria["topic"]`
- `qa_asset["source_basis"]`

然後做 generic check：

1. 如果這些 review-level strings verbatim 出現在 output 的：
   - rationale
   - normalized_value
   - supporting_quotes
   - criterion_conflicts
2. 但同時不在 candidate title / abstract / fulltext / metadata 中出現

=> 視為 contamination。

### 8.7 建議新增的 helper functions

```python
def _load_paper_specific_policy(paper_id: str, stage: str) -> str: ...
def _sanitized_qa_prompt_payload(asset: dict[str, Any]) -> dict[str, Any]: ...
def _expected_identity(paper_id: str, stage: str, arm: str, record: dict[str, Any], qa_source_path: Path) -> dict[str, Any]: ...
def _validate_review_output(obj: dict[str, Any], expected: dict[str, Any]) -> list[str]: ...
def _validate_synthesis_output(obj: dict[str, Any], expected: dict[str, Any], required_fields: list[str]) -> list[str]: ...
def _validate_eval_output(obj: dict[str, Any], expected: dict[str, Any]) -> list[str]: ...
def _validate_senior_output(obj: dict[str, Any], expected: dict[str, Any]) -> list[str]: ...
def _detect_review_level_leak(obj: dict[str, Any], review_strings: list[str], candidate_strings: list[str]) -> list[str]: ...
async def _call_with_validation(...): ...
```

### 8.8 retry / invalid sidecar 寫法

建議流程：

1. call model
2. validate
3. 若 invalid：
   - retry 最多 2~3 次
4. 若仍 invalid：
   - 寫 `invalid_contract` sidecar
   - 該 record fail fast，不要默默當有效輸出繼續跑

建議 sidecar 路徑：

- `screening/results/<new_results_root>/<paper>__<arm>/invalid_contract/<stage>/<candidate_key>__<role>.json`

sidecar 內容至少要含：

- expected identity
- observed payload
- validation errors
- review-level leak hits
- retry count
- source prompt template id

### 8.9 為 rerun 支援的 CLI 改動

至少新增以下 flags：

```text
--results-suffix
--stage1-only
--stage2-only
--reuse-stage1-from-arm
--fail-on-invalid-contract
--max-validation-retries
```

推薦語義：

- `--results-suffix`: 把 rerun 寫到新結果目錄，避免覆蓋 v0
- `--stage1-only`: 只跑 Stage 1
- `--stage2-only`: 只跑 Stage 2
- `--reuse-stage1-from-arm qa-only|qa+synthesis`: Stage 2 從另一個 arm 的 stage1 結果接續
- `--fail-on-invalid-contract`: 出現 invalid contract 立即停止該 run
- `--max-validation-retries N`: validation retry 次數

這樣才有辦法乾淨地做：

- `2511_decontaminated_stage1`
- `2409_stage2_closure_fix`
- `2409_hybrid_stage1_qa_only__stage2_qa_synthesis`

---

## 9. Schema / Handoff Changes

### 9.1 `minimal_synthesis_schema.yaml`

**建議保留的欄位**

- `field_records`
- `field_name`
- `state`
- `normalized_value`
- `supporting_quotes`
- `locations`
- `missingness_reason`
- `conflict_note`
- `derived_from_qids`
- `stage_handoff_status`

**建議新增的欄位**

Top-level 新增：

- `candidate_key`
- `candidate_title`
- `source_record_provenance`
- `prior_stage_reference`

Field-level 新增：

- `support_source_kind`
  - allowed values:
    - `candidate_title_abstract`
    - `candidate_fulltext`
    - `metadata`
    - `prior_stage_handoff`

### 9.2 哪些欄位不該讓模型自由生成

以下欄位應由 runner 提供 deterministic expectation，並強驗證：

- `paper_id`
- `candidate_key`
- `candidate_title`
- `stage`
- `arm`
- `source_record_provenance`
- `prior_stage_reference`

如果模型輸出不一致，不要「幫它修正後繼續用」，而是先 retry / fail fast。  
原因是這類 mismatch 代表 prompt binding 已經不可靠。

### 9.3 reviewer / evaluator / senior contracts 也要加 identity 欄位

建議同步修改：

1. `schemas/qa_output_contract.yaml`
2. `schemas/criteria_evaluation_output_contract.yaml`
3. `schemas/senior_output_contract.yaml`

三個 contract 都加：

- `candidate_key`
- `candidate_title`
- `source_record_provenance`（至少在 reviewer / synthesis 端必須有）

### 9.4 如何避免 review-level metadata 灌進 paper-level synthesis object

**不要只靠 prompt 規勸。**  
應該三層一起做：

1. **input sanitization**  
   prompt 不再看到完整 seed QA review header
2. **prompt rule**  
   template 明確禁止把 review title/topic 當 candidate evidence
3. **runner validation**  
   output 若出現 review-level strings 且不在 candidate evidence 裡，直接判 invalid

---

## 10. Rerun Matrix

### 10.1 `2511_decontaminated_stage1`

**Exact changes included**

- sanitized QA payload
- generic YAML schema hints，移除 hardcoded sample JSON hints
- identity assertions
- contamination leak detection
- fail-fast / retry
- 暫時 **不加** `2511` evaluator mapping fix

**What is held constant**

- `criteria_stage1/2511.13936.json`
- `criteria_stage2/2511.13936.json`
- Stage 1 routing thresholds
- `SeniorLead`
- seed QA question content

**Why this ablation matters**

先回答一個最基本的問題：  
把 contamination / binding confound 清掉之後，`2511` qasynthesis Stage 1 會不會自然回穩一些？

**Success criteria**

1. reviewer / synthesis / evaluator / senior 的 identity mismatch = `0`
2. candidate-level outputs 中 review-title leakage = `0`
3. `2511 qasynthesis` Stage 1 maybe-count > `1`
4. Stage 1 recall 不低於 current qasynthesis 的 `0.8000`

**Stop condition**

- 任一 contract mismatch 仍存在
- 任一 review-title leakage 仍存在

---

### 10.2 `2511_decontaminated_plus_mapping_fix`

**Exact changes included**

- `2511_decontaminated_stage1` 的全部修法
- `2511_stage1_evaluator_policy.md`
- evaluator templates 注入 `PAPER_SPECIFIC_STAGE1_POLICY_MD`

**What is held constant**

- formal criteria
- Stage 1 routing thresholds
- `SeniorLead`
- Stage 2 semantic prompt（只保留 hygiene required patch，不做新的 semantic rewrite）
- seed QA question content

**Why this ablation matters**

這一輪才真正測：  
`2511` recall collapse 是否主要來自 Stage 1 mapping，而不是 contamination 以外的別的東西。

**Success criteria**

1. Stage 1 recall 高於 current qasynthesis `0.8000`
2. maybe-count 明顯高於 `1`，建議至少 `>= 5`
3. Combined F1 高於 current qasynthesis `0.8519`
4. precision 不得較 current qasynthesis 下滑超過 `0.05`

**Stop condition**

- precision 大幅掉水
- maybe-count 仍近似 `1`
- 直接 `exclude (junior:1,1)` 仍維持高位

---

### 10.3 `2409_stage2_closure_fix`

**Exact changes included**

- global hygiene patch（至少 runner validation 與 identity cleanup）
- `2409_stage2_closure_policy.md`
- `07_criteria_evaluator_from_synthesis_TEMPLATE.md` 注入 Stage 2 closure addendum
- 視需要補到 qa-only evaluator，但不重寫 Stage 1 QA

**What is held constant**

- `criteria_stage1/2409.13738.json`
- `criteria_stage2/2409.13738.json`
- Stage 1 routing thresholds
- Stage 1 QA content
- `SeniorLead`

**Why this ablation matters**

`2409` 的 gain 本來就主要在 Stage 2。  
所以應先 isolated test Stage 2 closure，而不是重跑整個 bundle 再一起猜。

**Success criteria**

1. `elallaoui2018automatic` 仍維持 exclusion
2. `honkisz2018concept` 仍維持 inclusion
3. 至少一個 publication-form wobble case 變穩：
   - `kourani_process_modelling_with_llm`
   - `neuberger_data_augment`
   - `grohs2023large`
4. Combined F1 不低於 current qasynthesis `0.8333` 超過 `0.01`

**Stop condition**

- `elallaoui` 被收回 include
- `honkisz` 再次被錯砍
- Combined precision 明顯下滑

---

### 10.4 `2409_hybrid_stage1_qa_only__stage2_qa_synthesis`

**Exact changes included**

- global hygiene patch
- `2409_stage2_closure_policy.md`
- runner 新增 `--reuse-stage1-from-arm qa-only`
- Stage 2 使用 qasynthesis path，但 Stage 1 pool 直接承接 qa-only 結果

**What is held constant**

- current formal criteria
- current Stage 1 routing invariant
- `SeniorLead`
- current seed QA content

**Why this ablation matters**

這個 run 是在測一個明確假設：

- `2409` 的 Stage 1 不需要 synthesis 才有價值
- 但 Stage 2 的 canonical closure 可能仍以 qasynthesis 較強

**Success criteria**

1. Combined F1 >= current qasynthesis `0.8333`
2. `elallaoui` exclusion 保住
3. `honkisz` inclusion 保住
4. publication-form wobble 不要比 `2409_stage2_closure_fix` 更差

**Stop condition**

- hybrid 同時輸給 `2409 qa-only` 與 `2409 qa+synthesis`
- target-boundary precision gain 消失

---

## 11. Recommended Run Order

### Prerequisite: 先做 patch，不先 rerun

先完成這些不帶結論的 prerequisite patch：

1. 去掉 hardcoded sample JSON hints
2. `_base_context()` 改成 sanitized QA payload
3. 加 identity contract / leak detection / fail-fast
4. prompt_manifest 加新 placeholders
5. 加外部 policy files，但先不要開 `2511` mapping fix

### 正式 rerun 順序

#### 1. `2511_decontaminated_stage1`

**原因**  
這是目前最便宜、最必要、confound 最重的清理。  
不先確認 contamination 清乾淨，後面的 `2511` mapping rerun 會繼續混在一起看不懂。

#### 2. `2409_stage2_closure_fix`

**原因**  
`2409` 問題集中在 Stage 2，blast radius 小，容易 isolated。  
在 hygiene patch 做完後，它是最適合先驗證的 paper-specific closure fix。

#### 3. `2511_decontaminated_plus_mapping_fix`

**原因**  
等 contamination 被清乾淨，再測 `2511` 的 Stage 1 mapping fix，才能知道 recall collapse 到底修了多少。

#### 4. `2409_hybrid_stage1_qa_only__stage2_qa_synthesis`

**原因**  
這是 compound hypothesis，不該先跑。  
應等 `2409_stage2_closure_fix` 先證明 stage2 closure patch 沒把 precision 搞壞，再做 hybrid。

### 一句話版排序邏輯

**先清 hygiene -> 再測 isolated fixes -> 最後才測 hybrid。**

---

## 12. What Not To Change

### 12.1 formal criteria 不要動

不要改：

- `criteria_stage1/2409.13738.json`
- `criteria_stage2/2409.13738.json`
- `criteria_stage1/2511.13936.json`
- `criteria_stage2/2511.13936.json`

這輪看到的主問題發生在：

- prompt payload hygiene
- output binding
- synthesis object construction
- evaluator mapping
- defer strategy
- stage handoff

不是 formal criteria source-faithfulness 已被證明錯掉。

### 12.2 不要把歷史 hardening 回灌

不要把：

- `criteria_jsons/*.json`
- 舊版 op hardening
- 任何 hidden guidance / pseudo-guidance

再寫回 current criteria layer。

### 12.3 不要先做 global evaluator rewrite

shared evaluator implementation 確實是 global，  
但這不代表第一步就該全局改 rubric。

正確順序是：

1. 先修 hygiene
2. 先做 `2511`-specific Stage 1 override
3. 看 rerun 結果
4. 再決定是否抽象成 global policy

### 12.4 不要移除 `SeniorLead`

`SeniorLead` 不是問題本身。  
這輪真正的問題是太多本該送 `SeniorLead` 的 `2511` case，在 Stage 1 就被壓成 `1/2` 了。

### 12.5 不要把 prompt patch 寫回 `.py`

所有 prompt / policy patch 都應維持在外部模板檔：

- `.md`
- `.yaml`
- `.yml`

Python 只負責：

- 讀模板
- 填 placeholder
- 驗證輸出
- 管理 rerun orchestration

---

## Bottom Line

這一輪最應該做的，不是重寫 criteria，也不是再寫一份 diagnosis。  
而是把 repair plan 拆成兩層：

1. **global hygiene patch**
   - sample hints 去硬編碼
   - sanitized QA payload
   - identity contract
   - review-level leak detection
   - fail-fast

2. **paper-specific fixes**
   - `2511`: Stage 1 mapping + defer strategy
   - `2409`: Stage 2 closure stabilization

然後 rerun 順序採用：

1. `2511_decontaminated_stage1`
2. `2409_stage2_closure_fix`
3. `2511_decontaminated_plus_mapping_fix`
4. `2409_hybrid_stage1_qa_only__stage2_qa_synthesis`

這樣下一輪才是可解釋、可落地、可比對的 repair cycle。
