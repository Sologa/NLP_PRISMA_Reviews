# Single Reviewer 引入 Current-State-Aligned 2-Stage QA 的設計藍圖

> status note:
> 這份文件描述的是新的 `single reviewer official-batch` 實驗提案，不是 current production workflow。
> production authority 仍以 [AGENTS.md](../../AGENTS.md)、[chatgpt_current_status_handoff.md](../chatgpt_current_status_handoff.md)、[results_manifest.json](../../screening/results/results_manifest.json)、`criteria_stage1/<paper_id>.json`、`criteria_stage2/<paper_id>.json`、`cutoff_jsons/<paper_id>.json` 為準。

## 1. 目的與邊界

這份文件要回答的不是「production screening 現在怎麼跑」，而是：

**如果要在目前的 `single reviewer official-batch` 線中，引進 current-state-aligned 的 2-stage QA / evidence synthesis / criteria evaluation，推薦的設計應該長什麼樣子。**

本文件的定位是：

- 新實驗設計
- 可落地實作藍圖
- 給下一位工程師直接照著建新 bundle / runner / schema 的 blueprint

本文件不是：

- current runtime 說明
- 舊 QA-first bundle 的移植手冊
- criteria rewrite 提案
- code diff 清單

本文件採用的邊界固定如下：

- 不更動 production runtime authority
- 不把 `qa_first_experiments/` 描述成 current active path
- 不把 `criteria_mds/` 描述成 current QA spec
- 不把 operational hardening 寫回 formal criteria
- 不把雙 junior / `SeniorLead` routing 直接搬進 single reviewer 實驗線

## 2. 先對齊 current state

### 2.1 current production authority

目前 repo 的 authoritative current state 是：

1. [AGENTS.md](../../AGENTS.md)
2. [docs/chatgpt_current_status_handoff.md](../chatgpt_current_status_handoff.md)
3. [screening/results/results_manifest.json](../../screening/results/results_manifest.json)
4. `screening/results/<paper>_full/CURRENT.md`

對這份設計最重要的 current-state invariant 有四個：

1. runtime prompt authority 是 `scripts/screening/runtime_prompts/runtime_prompts.json`
2. current active criteria 是 stage-split：
   - Stage 1：`criteria_stage1/<paper_id>.json`
   - Stage 2：`criteria_stage2/<paper_id>.json`
3. cutoff 必須在 reviewer routing 之前執行
4. `criteria_jsons/*.json` 不是 current production criteria

若後續用這條新實驗線做比較，score authority 也應維持 current-state 定義：

- `2409` / `2511` 以 `stage_split_criteria_migration` 為當前權威比較基準
- `2307` / `2601` 以 latest fully benchmarked `senior_no_marker` 為穩定參考

### 2.2 current single reviewer baseline 是什麼

目前 single reviewer official-batch baseline 以 [single_reviewer_official_batch_experiments_usage_zh.md](./single_reviewer_official_batch_experiments_usage_zh.md) 為主，代表性 bundle 是：

- `single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5_all4_2026-03-22/`

它的核心特徵是：

- cutoff-first
- one-stage fulltext direct review
- criteria 固定只讀 `criteria_stage2/<paper_id>.json`
- 每個 candidate 只經過一條 single reviewer 決策路徑
- 沒有 stage1 gate
- 沒有 QA extraction layer
- 沒有 evidence synthesis layer

換句話說，現在的 official-batch single reviewer 不是 2-stage workflow，而是：

```text
cutoff -> fulltext direct review -> single verdict
```

### 2.3 現有 QA-first bundle 的正確定位

目前 repo 中可以參考的 QA-first 實作主要在：

- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/`

它的價值在於提供了可重用的設計概念：

- stage-specific QA extraction
- evidence-oriented contract
- synthesis object
- criteria evaluator object
- policy hook / validation hook

但它不是 current production runtime，原因很明確：

- 它是 experiment-only branch
- 它的 orchestration 不是 official Batch API
- 它目前主要聚焦在 `2409` / `2511`
- 它同時保留 `qa-only` 與 `qa+synthesis` arm，比這份文件要推薦的 single-path MVP 更寬

### 2.4 `criteria_mds/` 的正確定位

`criteria_mds/` 可以用來參考 extraction-first 方法論，但不能直接當 current QA spec。原因是：

- 它不是 current active criteria authority
- 它不是 stage-specific runtime contract
- 它混合了 question generation 與 extraction scaffolding
- 它沒有直接對齊 current `criteria_stage1/` / `criteria_stage2/`

因此，本文件採用的路線是：

**current-state-aligned stage-specific QA / extraction -> evidence synthesis -> criteria evaluation**

而不是：

- 直接沿用舊 `criteria_mds/`
- 直接複製舊 QA-first bundle
- 把 operational hardening 寫回 criteria

## 3. 推薦的單一路線

這份設計不做多方案搖擺，推薦架構固定為：

```text
cutoff
-> stage1 QA extraction
-> stage1 evidence synthesis
-> stage1 criteria evaluation
-> stage2 selection
-> stage2 QA extraction
-> stage2 evidence synthesis
-> stage2 criteria evaluation
-> final single-reviewer verdict
```

### 3.1 這裡的「single reviewer」是什麼意思

這裡的 `single reviewer` 不是指「只有一次模型呼叫」，而是指：

- 每個 candidate 只有一條 reviewer lane
- 該 lane 最終只產出一個 final verdict
- 不走雙 junior 互評
- 不進 `SeniorLead`
- 允許在同一條 lane 內使用多個依賴式 batch phase

也就是說，本設計保留 `single reviewer` 的實驗邊界，但不保留現有 one-shot fulltext direct review 的 prompt 形狀。

### 3.2 Stage 1 的任務定義

Stage 1 固定只用：

- `refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- `criteria_stage1/<paper_id>.json`
- cutoff 通過後的 candidate metadata

Stage 1 不讀 fulltext，也不讀 `criteria_stage2/<paper_id>.json`。

Stage 1 的任務是：

1. 先對 title/abstract 做 criteria-conditioned QA extraction
2. 把 QA 答案整理成穩定 evidence object
3. 用 Stage 1 criteria 做 evaluator 判讀
4. 產生 stage1 gate

Stage 1 的 gate 規則固定為：

- 只有 `decision_recommendation = exclude` 會停止進入 Stage 2
- `include` 與 `maybe` 都進 Stage 2

這樣做的理由是保留召回，避免把 single reviewer 的 Stage 1 gate 做得過嚴。

### 3.3 Stage 2 的任務定義

Stage 2 固定只用：

- `refs/<paper_id>/mds/<candidate_key>.md`
- `criteria_stage2/<paper_id>.json`
- Stage 1 handoff object

Stage 2 的任務是：

1. 使用 fulltext 做更完整的 criteria-conditioned QA extraction
2. 與 Stage 1 evidence handoff 合併成穩定 evidence object
3. 用 canonical Stage 2 criteria 做 evaluator 判讀
4. 產生 combined final verdict

Stage 2 才是 combined screening 的決定層。

## 4. 為什麼推薦 QA -> synthesis -> evaluator，而不是直接 fulltext review

目前 single reviewer baseline 最大的結構限制，是把以下三件事塞進同一次 review prompt：

1. 找證據
2. 整理證據
3. 用 criteria 下結論

這個結構在 source-faithful stage-split criteria 之下會比較脆弱，因為模型容易：

- 在找 evidence 時混入 topic intuition
- 在 criteria 判讀時補完 paper 沒寫的條件
- 在 title/abstract 與 fulltext 可觀測資訊之間漂移

把流程拆成 `QA -> synthesis -> evaluator` 有三個好處：

1. evidence object 能被單獨稽核
2. criteria evaluator 不需要直接吃自由文本 reasoning
3. Stage 1 與 Stage 2 的 handoff 可以做成明確 contract，而不是靠 prompt 隱式傳遞

## 5. 推薦的 bundle 與 runner 形狀

### 5.1 新 bundle 不覆寫現有 baseline

新的 single reviewer 2-stage QA 實驗線應該放在新的 bundle，而不是直接改現有 baseline bundle。

建議命名模式：

```text
single_reviewer_batch_experiments/
  single_reviewer_official_batch_2stage_qa_v1_<date>/
```

這樣做的理由是：

- baseline 要保留作為對照
- 2-stage QA bundle 的 prompt / schema / artifact 結構都不同
- 後續需要平行比較 `direct-review baseline` 與 `2-stage QA reviewer`

### 5.2 推薦保留的共用元件

新的 bundle 應優先重用下列現有元件，而不是重造一套 orchestration：

- `scripts/screening/openai_batch_runner.py`
- current single reviewer baseline 的 `submit / collect / run` 模式
- QA-first 既有的 schema 語義
- current cutoff helper
- 現有 per-paper F1 產出方式

### 5.3 推薦的 bundle 內檔案

建議新 bundle 至少包含：

- `manifest.json`
- `config/experiment_config.json`
- `tools/run_experiment.py`
- `tools/render_prompt.py`
- `tools/validate_bundle.py`
- `templates/01_stage1_qa_TEMPLATE.md`
- `templates/02_stage1_eval_TEMPLATE.md`
- `templates/03_stage2_qa_TEMPLATE.md`
- `templates/04_stage2_eval_TEMPLATE.md`
- `templates/validation_retry_repair_policy.md`
- `samples/stage1_qa_output.sample.json`
- `samples/stage1_eval_output.sample.json`
- `samples/stage2_qa_output.sample.json`
- `samples/stage2_eval_output.sample.json`

本設計不建議另外加 `synthesis` prompt template。`evidence synthesis` 預設應寫成 local deterministic normalization，原因是：

- Stage 1 / Stage 2 的 phase 已經有明確依賴
- 若 synthesis 也變成模型 phase，Batch job 會再多兩段
- 目前要先驗證的是 `QA extraction object + deterministic synthesis + evaluator` 這條路是否穩定

## 6. Batch phase 的固定拆法

### 6.1 phase 一律固定為四段

新的 official-batch runner 固定拆成四個 phase：

1. `stage1_qa`
2. `stage1_eval`
3. `stage2_qa`
4. `stage2_eval`

這裡的 `synthesis` 不單獨開 Batch job，而是在 `collect` 時本地生成：

- `stage1_qa collect -> stage1_synthesis.json`
- `stage2_qa collect -> stage2_synthesis.json`

### 6.2 為什麼不能做成單一 batch job

不能做成單一 batch job 的原因不是技術限制，而是資料依賴順序：

1. `stage1_eval` 的輸入依賴 `stage1_qa`
2. `stage2_qa` 的輸入依賴 `stage1_eval`
3. `stage2_eval` 的輸入依賴 `stage2_qa`

因此，official-batch runner 應該保留 `submit / collect / run` 三種模式，但把 phase 額外顯式化，例如：

```bash
./.venv/bin/python single_reviewer_batch_experiments/<new_bundle>/tools/run_experiment.py \
  --mode run \
  --phase all \
  --papers 2409.13738 2511.13936
```

或：

```bash
./.venv/bin/python single_reviewer_batch_experiments/<new_bundle>/tools/run_experiment.py \
  --mode submit \
  --phase stage1_qa \
  --papers 2409.13738
```

`all` 的實際執行順序必須固定為：

1. cutoff
2. stage1_qa submit / collect
3. stage1 deterministic synthesis
4. stage1_eval submit / collect
5. stage2 selection
6. stage2_qa submit / collect
7. stage2 deterministic synthesis
8. stage2_eval submit / collect
9. final result assembly
10. per-paper F1 與 run summary 產生

## 7. 介面與契約

這一節是實作時最不能模糊的地方。建議新 bundle 的 schema 盡量沿用 QA-first contract 的語義，避免同一個概念在 repo 內有兩套名字。

### 7.1 `StageQAOutput`

用途：

- 讓 reviewer 只做 criteria-conditioned evidence extraction
- 不直接產出 final verdict

建議欄位：

| 欄位 | 說明 |
| --- | --- |
| `paper_id` | paper id |
| `candidate_key` | candidate key |
| `candidate_title` | candidate title |
| `stage` | `stage1` 或 `stage2` |
| `workflow_arm` | 例如 `single-reviewer-official-batch-2stage-qa` |
| `qa_source_path` | QA asset 或 rendered prompt 的來源 |
| `reviewer_guardrails_applied` | 套用的 hygiene / policy 名稱 |
| `source_record_provenance` | metadata / criteria / fulltext path 等 provenance |
| `answers` | `QAAnswer[]` |

`QAAnswer` 建議沿用 QA-first 語義：

| 欄位 | 說明 |
| --- | --- |
| `qid` | question id |
| `criterion_family` | 對應 criterion family |
| `answer_state` | `present` / `absent` / `unclear` |
| `state_basis` | `direct_support` / `direct_counterevidence` / `insufficient_signal` / `mixed_signal` |
| `answer_rationale` | 簡短說明 |
| `supporting_quotes` | 原文摘句 |
| `locations` | section / page / paragraph pointer |
| `missingness_reason` | 沒證據時原因 |
| `stage2_handoff_note` | Stage 1 對 Stage 2 的 handoff |
| `conflict_note` | 證據衝突備註 |
| `candidate_synthesis_fields` | 建議映射的 field 名稱 |

### 7.2 `StageSynthesisOutput`

用途：

- 把自由文本 QA 答案正規化成 evaluator 可穩定消化的 evidence object

建議欄位：

| 欄位 | 說明 |
| --- | --- |
| `paper_id` | paper id |
| `candidate_key` | candidate key |
| `candidate_title` | candidate title |
| `stage` | `stage1` 或 `stage2` |
| `workflow_arm` | 與 QA phase 相同 |
| `source_record_provenance` | provenance |
| `prior_stage_reference` | Stage 2 時引用 Stage 1 handoff |
| `field_records` | `FieldRecord[]` |

`FieldRecord` 建議欄位：

| 欄位 | 說明 |
| --- | --- |
| `field_name` | evidence field 名稱 |
| `state` | 正規化狀態 |
| `state_basis` | 同 QA answer basis |
| `normalized_value` | 正規化值 |
| `supporting_quotes` | 支持片段 |
| `locations` | 來源位置 |
| `missingness_reason` | 缺失原因 |
| `conflict_note` | 衝突說明 |
| `derived_from_qids` | 由哪些 QA 題得出 |
| `stage_handoff_status` | `current_stage_only` / `carried_from_stage1` / `resolved_in_stage2` 等 |
| `support_source_kind` | `current_stage_qa` / `prior_stage_output` / `current_stage_qa_and_prior_stage_output` |

### 7.3 `StageCriteriaEvaluationOutput`

用途：

- evaluator 根據 synthesized evidence object 做 criteria 判讀

建議欄位：

| 欄位 | 說明 |
| --- | --- |
| `paper_id` | paper id |
| `candidate_key` | candidate key |
| `candidate_title` | candidate title |
| `stage` | `stage1` 或 `stage2` |
| `workflow_arm` | workflow arm |
| `source_record_provenance` | provenance |
| `stage_score` | `1` 到 `5` |
| `scoring_basis` | `clear_include` / `clear_exclude_with_direct_negative` / `unresolved_without_direct_negative` / `mixed_conflict` |
| `decision_recommendation` | `include` / `exclude` / `maybe` |
| `positive_fit_evidence_ids` | 支持 include 的 field id |
| `direct_negative_evidence_ids` | 支持 exclude 的 field id |
| `unresolved_core_evidence_ids` | 尚未解決的 field id |
| `deferred_core_evidence_ids` | Stage 1 defer 到 Stage 2 的 field id |
| `criterion_mapping` | criterion 與 evidence 對應 |
| `criterion_conflicts` | criterion conflict 摘要 |
| `decision_rationale` | evaluator 簡短說明 |
| `manual_review_needed` | 是否需人工檢查 |
| `routing_note` | Stage 1 gate / Stage 2 final note |

### 7.4 `SingleReviewerFinalOutput`

用途：

- 把四段 phase 的結果收斂成 single reviewer 現有結果列風格
- 方便直接接回既有 reporting / F1 pipeline

建議欄位應兼容現有 `single_reviewer_batch_results.json` 的閱讀習慣：

| 欄位 | 說明 |
| --- | --- |
| `key` | candidate key |
| `title` | candidate title |
| `review_state` | `cutoff_filtered` / `reviewed` / `missing` / `batch_error` / `batch_missing` / `batch_unmapped` |
| `stage1_stage_score` | Stage 1 score |
| `stage1_decision_recommendation` | Stage 1 decision |
| `stage2_stage_score` | Stage 2 score |
| `stage2_decision_recommendation` | Stage 2 decision |
| `final_verdict` | final verdict string |
| `discard_reason` | `cutoff_time_window:*` / `fulltext_missing` / `batch_error` 等 |
| `stage1_eval_path` | stage1 eval artifact path |
| `stage2_eval_path` | stage2 eval artifact path |
| `stage1_synthesis_path` | stage1 synthesis artifact path |
| `stage2_synthesis_path` | stage2 synthesis artifact path |
| `source_record_provenance` | provenance 摘要 |

這裡最重要的是：`SingleReviewerFinalOutput` 不是另一套全新格式，而是 single reviewer 現有 row shape 的擴充版。

## 8. Evidence synthesis 的本地化原則

這份設計預設 `evidence synthesis` 不再交給 LLM，而是在 `collect` 階段本地 deterministic 生成。

### 8.1 為什麼這裡要 deterministic

原因是：

1. QA 已經把 evidence 抽出來了
2. synthesis 的主要工作是正規化與去重
3. 若 synthesis 也交給模型，official-batch phase 數量會翻倍
4. single reviewer 2-stage QA 的第一版，應先把變因壓在最少

### 8.2 deterministic synthesis 要做什麼

本地 synthesis 應至少做以下事：

1. 把多題 QA 答案歸併到穩定 `field_name`
2. 對 `present / absent / unclear` 做一致化
3. 保留 supporting quotes 與 locations
4. 標出 direct negative 與 unresolved core evidence
5. 在 Stage 2 合併 Stage 1 handoff 與 current-stage QA answers
6. 對互相衝突的 evidence 顯式加 `conflict_note`

這裡要強調的是：deterministic synthesis 是 workflow support，不是 criteria rewrite。

## 9. artifact layout

### 9.1 `batch_jobs/` 目錄

每個 run 建議產生：

- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_qa/<model>/input.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_qa/<model>/batch_latest.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_qa/<model>/output.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_qa/<model>/parsed_results.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_eval/<model>/input.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_eval/<model>/batch_latest.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_eval/<model>/output.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage1_eval/<model>/parsed_results.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_qa/<model>/input.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_qa/<model>/batch_latest.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_qa/<model>/output.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_qa/<model>/parsed_results.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_eval/<model>/input.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_eval/<model>/batch_latest.json`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_eval/<model>/output.jsonl`
- `screening/results/<results_root>/runs/<run_id>/batch_jobs/stage2_eval/<model>/parsed_results.json`

### 9.2 `papers/<paper_id>/` 目錄

每篇 paper 建議產生：

- `papers/<paper_id>/cutoff_audit.json`
- `papers/<paper_id>/stage1_qa.jsonl`
- `papers/<paper_id>/stage1_synthesis.json`
- `papers/<paper_id>/stage1_eval.json`
- `papers/<paper_id>/selected_for_stage2.keys.txt`
- `papers/<paper_id>/stage2_qa.jsonl`
- `papers/<paper_id>/stage2_synthesis.json`
- `papers/<paper_id>/stage2_eval.json`
- `papers/<paper_id>/single_reviewer_batch_results.json`
- `papers/<paper_id>/single_reviewer_batch_f1.json`

run 級別建議產生：

- `runs/<run_id>/run_manifest.json`
- `runs/<run_id>/REPORT_zh.md`

### 9.3 這些 artifact 要如何對接現有評分方式

推薦做法是：

1. `single_reviewer_batch_results.json` 保持現有閱讀習慣
2. 每列再附上 Stage 1 / Stage 2 evaluator 的 provenance
3. `single_reviewer_batch_f1.json` 延續現有 single reviewer per-paper summary
4. run 級別 summary 延續目前 official-batch baseline 的寫法

這樣一來，新線雖然是 2-stage QA reviewer，但最後仍能與現有 single reviewer baseline 同口徑比較。

## 10. failure modes 與 handoff 規則

### 10.1 cutoff fail

規則固定為：

- 不送 `stage1_qa`
- 不送 `stage1_eval`
- 不送 `stage2_qa`
- 不送 `stage2_eval`
- 直接寫 final row：
  - `review_state = cutoff_filtered`
  - `final_verdict = exclude (cutoff_time_window)`
  - `discard_reason = cutoff_time_window:<status>`

這裡不能做成「先送模型，再讓模型知道 cutoff」，因為 cutoff 是 authoritative pre-review hard filter。

### 10.2 Stage 1 clear exclude

規則固定為：

- `stage1_eval.decision_recommendation = exclude`
- 不進 Stage 2
- 仍寫入完整 `stage1_qa.jsonl`、`stage1_synthesis.json`、`stage1_eval.json`
- `selected_for_stage2.keys.txt` 不包含該 key
- final row 直接以 Stage 1 exclude 收斂

### 10.3 Stage 1 unresolved 或 positive

規則固定為：

- `include` 與 `maybe` 都進 Stage 2
- Stage 2 的 prompt / context 必須接收 Stage 1 handoff
- Stage 2 evaluator 才負責 combined final verdict

### 10.4 missing fulltext

這一條必須對齊 repo 內既有 single reviewer / QA-first code 的行為，不可自己發明新規則。

推薦行為固定為：

- `stage2_qa` 不送模型
- `review_state = missing`
- `fulltext_missing_or_unmatched = true`
- `discard_reason = fulltext_missing`
- `final_verdict` 沿用 Stage 1 verdict

也就是說，missing fulltext 在這條設計裡不是「偷偷補判」，而是顯式記錄為 stage2 missing，並保留 stage1 gate 結果。

### 10.5 batch parse error / batch missing / batch unmapped

沿用現有 single reviewer error-row 風格：

- `review_state = batch_error`
- `review_state = batch_missing`
- `review_state = batch_unmapped`
- `final_verdict = maybe (review_state:<status>)`

這類錯誤不能默默回填 verdict，也不能在報告裡假裝它們是正常 reviewed row。

### 10.6 criteria fidelity 的底線

這份設計的底線只有一條：

**任何 performance support 都只能放在 workflow、prompt、evidence extraction、structured output、handoff design。**

不能做的事包括：

- 把 derived hardening 寫進 `criteria_stage1/`
- 把 derived hardening 寫進 `criteria_stage2/`
- 把 evaluator heuristic 偽裝成 source criterion

## 11. 驗收場景

這裡的目標不是提供 benchmark 保證，而是提供實作後可立即執行的 smoke tests。

### 11.1 cutoff-failed candidate 應完全跳過後續 phase

可以直接用現成 baseline 中 `2511.13936` 的 cutoff-failed key 當 smoke-test seed，例如：

- `harzing2007pop`
- `yang2010ranking`
- `cao2012combining`

驗收點：

1. 這些 key 只出現在 `cutoff_audit.json` 與 final row
2. 不應出現在 `stage1_qa.jsonl`
3. 不應出現在 `stage1_eval.json`
4. 不應出現在 `selected_for_stage2.keys.txt`
5. final row 應是 `exclude (cutoff_time_window)`

### 11.2 Stage 1 clear negative 應不進 Stage 2

驗收點：

1. 該 key 在 `stage1_eval.json` 中是 `decision_recommendation = exclude`
2. 該 key 不出現在 `selected_for_stage2.keys.txt`
3. 該 key 不出現在 `stage2_qa.jsonl`
4. final row 直接由 Stage 1 收斂

這個案例的具體 key 取決於新 runner 首次實作後的 `stage1_eval.json`，不要求先用現有 baseline 代替。

### 11.3 Stage 1 `maybe` 應進 Stage 2

可以把現有 baseline 中屬於模糊邊界的 reviewed row 當 smoke-test seed。`2511.13936` 目前有例如：

- `hurst2024gpt`，現有 baseline final row 為 `maybe (single:3)`

在新 2-stage QA 線中的驗收點不是要求它一定維持 `maybe`，而是要求：

1. Stage 1 若產生 `maybe`
2. 它必須被寫入 `selected_for_stage2.keys.txt`
3. 它必須出現在 `stage2_qa.jsonl`

### 11.4 missing fulltext 應顯式標記為 missing，而不是默默補判

驗收點：

1. 找一個不存在 `refs/<paper_id>/mds/<candidate_key>.md` 的 key
2. `stage2_qa` 不送該 key
3. final row 寫 `review_state = missing`
4. `discard_reason = fulltext_missing`
5. `final_verdict` 沿用 Stage 1 verdict

這個案例可用開發時的人為缺文測試產生，不要求先在 current single reviewer 結果中存在。

### 11.5 Stage 2 明確 positive / negative 應與 evidence object 對齊

可以先用現有 `2511.13936` baseline 的兩個 reviewed row 作 smoke-test seed：

- positive seed：`han2020ordinal`，現有 baseline final row 為 `include (single:5)`
- negative seed：`page2021prisma`，現有 baseline final row 為 `exclude (single:1)`

在新設計中的驗收點是：

1. Stage 2 evaluator 的 `decision_recommendation` 與 `stage_score` 合理一致
2. `positive_fit_evidence_ids` / `direct_negative_evidence_ids` 能對回 `field_records`
3. final row 不是憑空生成，而是能追到 `stage2_eval.json`

## 12. 實作時的簡短 checklist

真正開始寫 code 前，實作者應先確認：

1. 新 bundle 不覆寫現有 baseline bundle
2. `cutoff -> stage1 -> stage2` 的 phase 依賴順序已固定
3. Stage 1 只讀 `criteria_stage1`
4. Stage 2 只讀 `criteria_stage2`
5. synthesis 是 local deterministic，不另開 batch job
6. final row shape 與現有 single reviewer artifact 相容
7. 評分報告仍能產出 per-paper F1 與 run summary

## 13. 結論

對 single reviewer 來說，推薦的 next step 不是把 prompt 再寫長一點，而是把 reviewer lane 的內部結構改成：

**stage-specific QA extraction -> deterministic evidence synthesis -> criteria evaluation**

這條路的好處是：

- 與 current stage-split criteria 對齊
- 不把 operational hardening 寫回 formal criteria
- 保留 official Batch API orchestration
- 保留 single reviewer 實驗線的可比性

如果後續這條線擴張成多個平行 bundle、模型與 ablation 組合，建議改用 `www.k-dense.ai` 管理 workflow，而不是把大量平行實驗追蹤繼續塞在同一批手工文檔裡。
