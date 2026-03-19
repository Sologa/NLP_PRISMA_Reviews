# QA-first v1 Phase 1 Second-Pass 中文交接報告

這份報告的目的，是讓另一個對話串或 ChatGPT 可以直接接手目前的 second-pass 狀態，而不用重新追整個 repo 與 first-pass 脈絡。

本次 second pass 只針對 `qa+synthesis` 路線，且只跑兩個 arms：

- `2409.13738__qa+synthesis`
- `2511.13936__qa+synthesis`

沒有做的事：

- 沒有改 production runtime prompt authority：`scripts/screening/runtime_prompts/runtime_prompts.json`
- 沒有改 formal criteria：`criteria_stage1/<paper_id>.json`、`criteria_stage2/<paper_id>.json`
- 沒有跑 `qa-only`
- 沒有跑 `2307` / `2601`
- 沒有覆蓋 v0 或 v1 first-pass results root

## Root-Cause Short Diagnosis

### 1. `2409` topic leak root cause

`2409` first-pass 的 review title literal 已清掉，但 review topic literal `NLP for process extraction from natural-language text` 仍會進 final outputs。實際 root cause 不是 formal criteria，也不是某篇 paper 的 semantics，而是 workflow hygiene：

- `qa_first_experiments/qa_first_experiment_v1_global_repair_2409_2511_2026-03-18/tools/run_experiment.py` 的 `_protected_review_phrases()` 只保護 `review.title`，沒有保護 `review.topic`
- 同一支 runner 的 `_build_allowed_candidate_text()` 把 QA question text 納進 leak allowlist，等於把 review topic literal 白名單化
- reviewer 一旦把這個 literal 寫進 QA output，後面的 synthesis / evaluator / senior 只是沿用 upstream output 繼續 echo

結論：`2409` 的 leak 是 runner leak detector coverage + allowlist 邏輯造成的 hygiene bug，不是 criteria 問題。

### 2. global Stage 1 defer-overfire root cause

first-pass 的 global defer 規則太寬，接近：

- 只要 `unresolved_core_evidence_ids` 非空
- 且 `direct_negative_evidence_ids` 為空
- 就容易直接映成 `stage_score = 3`

這在指標上直接表現成：

- `2409` Stage 1 maybe flood：`51`
- `2409` Stage 1 senior-finalized：`66`
- `2409` Stage 1 precision：`0.4038`
- `2511` Stage 1 maybe flood：`64`
- `2511` Stage 1 senior-finalized：`77`
- `2511` Stage 1 precision：`0.4688`

更具體地說，first-pass 沒有要求 `3 / maybe / SeniorLead` 必須先有正向 thematic fit / plausible core-fit。結果變成：

- 只要沒有直接負證據，就容易被送去 `3`
- generic lexical overlap 也會被誤當成 positive fit

second-pass 的核心收斂方向就是：

- 不是「資訊少就 defer」
- 而是「有正向 fit，但 closure 不足，且沒有直接負證據時才 defer」

## Minimal Patch Plan

### Repair 1: `2409` topic leak 清零

修補方向：

- 把 `review.topic` 納入 protected literals
- 把 protected review phrases 改成 always-forbidden exact literal
- 不再因為 QA question wording 含同一 literal，就把它放進 allowlist
- 明寫上游 QA / synthesis outputs 裡若有 protected literal，也不可直接抄回

實際落點：

- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/policies/global_identity_hygiene_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/03_stage1_qa_synthesis_reviewer_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/04_stage2_qa_synthesis_reviewer_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/05_synthesis_builder_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/09_stage1_senior_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/11_stage2_senior_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/tools/run_experiment.py`

### Repair 2: global Stage 1 defer policy 收斂

修補方向：

- `3 / maybe / SeniorLead` 只能用在：
  - `positive_fit_evidence_ids` 非空
  - `direct_negative_evidence_ids` 為空
  - `unresolved_core_evidence_ids` 或 `deferred_core_evidence_ids` 非空
- generic lexical overlap 不得直接當成 positive fit
- `direct_negative_evidence_ids` 非空時，不可再輸出 `3`

實際落點：

- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/policies/global_stage1_defer_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/03_stage1_qa_synthesis_reviewer_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/09_stage1_senior_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/schemas/criteria_evaluation_output_contract.yaml`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/schemas/senior_output_contract.yaml`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/samples/sample_criteria_evaluation_output.json`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/samples/sample_senior_output.json`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/tools/run_experiment.py`

### Additional retry repair added during execution

在實際 rerun 時，`2511` Stage 1 evaluator 有少數 cases 會在 5 次 retries 內重複輸出同一種 invalid pattern：

- `Stage 1 score 3 cannot keep direct negative evidence ids`

因此又補了一個很小的、仍然 externalized 的 retry repair policy，只在 validator failure 後追加到下一次 retry prompt，不改 production、不改 formal criteria：

- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/policies/validation_retry_repair_policy.md`

並在 `tools/run_experiment.py` 中載入這個外部 `.md`，只對 ValueError retry 生效。

## Exact Patch Scope

### 本次實際有改的檔案

- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/manifest.json`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/EXPERIMENT_FRAMING.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/policies/global_identity_hygiene_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/policies/global_stage1_defer_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/policies/validation_retry_repair_policy.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/03_stage1_qa_synthesis_reviewer_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/04_stage2_qa_synthesis_reviewer_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/05_synthesis_builder_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/07_criteria_evaluator_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/09_stage1_senior_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/11_stage2_senior_from_synthesis_TEMPLATE.md`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/schemas/criteria_evaluation_output_contract.yaml`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/schemas/senior_output_contract.yaml`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/samples/sample_criteria_evaluation_output.json`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/samples/sample_senior_output.json`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/tools/run_experiment.py`

### 本次明確沒改的檔案

- production runtime prompt：
  - `scripts/screening/runtime_prompts/runtime_prompts.json`
- production criteria：
  - `criteria_stage1/2409.13738.json`
  - `criteria_stage2/2409.13738.json`
  - `criteria_stage1/2511.13936.json`
  - `criteria_stage2/2511.13936.json`
- v0 bundle / v0 results
- v1 first-pass bundle / v1 first-pass results root
- `qa-only` arms
- `2307` / `2601`
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/tools/validate_bundle.py`
  - 這次不用改 code，因為 sample/schema required-key 檢查是 contract-driven，manifest policy file 也會自動被檢查
- `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/templates/policies/stage_specific_policy_manifest.yaml`
  - 本次沒有新增任何 paper-specific policy

## Execution Summary

### 1. New bundle / results roots

- second-pass bundle root：
  - `qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19`
- second-pass results root：
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19`

### 2. 實際執行的主要 commands

1. 複製 first-pass bundle 成 second-pass bundle
   - `cp -R qa_first_experiments/qa_first_experiment_v1_global_repair_2409_2511_2026-03-18 qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19`
2. 驗證 second-pass bundle
   - `./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/tools/validate_bundle.py`
3. 第一次 second-pass rerun
   - `./.venv/bin/python qa_first_experiments/qa_first_experiment_v1_global_repair_second_pass_2409_2511_2026-03-19/tools/run_experiment.py --papers 2409.13738 2511.13936 --arms qa+synthesis --concurrency 6 --record-batch-size 6`
4. 中途檢查 `2511` 的 `validation_failures.jsonl`
5. 補更窄的 evaluator wording
6. 第二次 validate
7. 第二次 rerun resume
8. 補 `validation_retry_repair_policy.md`
9. 第三次 validate
10. 只清掉 second-pass 的 `2511` arm output dir，保持 `2409` 不動
11. 第三次 rerun，讓 `2409` pending=0、`2511` fresh rerun

### 3. 最終輸出 inventory

root：

- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/run_manifest.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/REPORT_zh.md`

`2409.13738__qa+synthesis`：

- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/latte_review_results.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/hygiene_summary.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/validation_failures.jsonl`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/selected_for_stage2.keys.txt`

`2511.13936__qa+synthesis`：

- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/stage1_f1.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/combined_f1.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/latte_review_results.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/latte_fulltext_review_results.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/hygiene_summary.json`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/validation_failures.jsonl`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/selected_for_stage2.keys.txt`

### 4. Hygiene Verification

#### `2409.13738__qa+synthesis`

- `validation_failures.jsonl`：存在
- `validation_failures.jsonl` 行數：`57`
- `hygiene_summary.json` 原始內容：
  - `{"paper_id":"2409.13738","arm":"qa+synthesis","validation_failure_count":0,...}`
- 注意：
  - 這個 `0` 不是第二次 pass 真正的 failure log count
  - 原因是後續 no-pending rerun 重新寫了 summary，覆蓋成 `0`
  - 實際 authoritative hygiene count 應以 `validation_failures.jsonl` 為準
- log error breakdown：
  - `review-level phrase leaked into output: NLP for process extraction from natural-language text`：`50`
  - `Stage 1 score 3 cannot keep direct negative evidence ids`：`6`
  - `qa_source_path mismatch`：`1`
- final outputs exact-literal leak check：
  - `NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods`
    - review hits `0`
    - fulltext hits `0`
  - `NLP for process extraction from natural-language text`
    - review hits `0`
    - fulltext hits `0`
- final outputs identity mismatch：
  - final saved outputs 無 identity mismatch
  - 只有一次 transient `qa_source_path mismatch` retry，未進 final outputs

#### `2511.13936__qa+synthesis`

- `validation_failures.jsonl`：存在
- `validation_failures.jsonl` 行數：`13`
- `hygiene_summary.json` 原始內容：
  - `{"paper_id":"2511.13936","arm":"qa+synthesis","validation_failure_count":13,...}`
- log error breakdown：
  - `Stage 1 score 3 requires positive fit evidence`：`4`
  - `Stage 1 score 3 cannot keep direct negative evidence ids`：`3`
  - `review-level phrase leaked into output: Preference learning in audio applications`：`3`
  - `Stage 1 score 3 requires unresolved or deferred core evidence`：`1`
  - `paper_id identity mismatch`：`1`
  - OpenAI `BadRequest` JSON parse error：`1`
- final outputs exact-literal leak check：
  - `Preference-Based Learning in Audio Applications: A Systematic Analysis`
    - review hits `0`
    - fulltext hits `0`
  - `Preference learning in audio applications`
    - review hits `0`
    - fulltext hits `0`
- final outputs identity mismatch：
  - final saved outputs 無 identity mismatch
  - 一次 transient retry mismatch 已被消化

## Result Comparison

### 1. Metrics table: `2409.13738`

sources：

- current Stage 1：
  - `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
- current Combined：
  - `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
- current routing snapshot：
  - `screening/results/2409.13738_full/latte_review_results.json`
  - `screening/results/2409.13738_full/latte_fulltext_review_results.json`
- v0：
  - `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/*`
- v1 first-pass：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/*`
- v1 second-pass：
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/*`

| Source | Stage 1 P / R / F1 | Combined P / R / F1 | Stage 2 Selected | Stage 1 Maybe | Stage 1 Senior-Finalized | Hygiene |
| --- | --- | --- | ---: | ---: | ---: | --- |
| current production | `0.6000 / 1.0000 / 0.7500` | `0.6667 / 0.9524 / 0.7843` | `40` | `3` | `32` | n/a |
| v0 `qa+synthesis` | `0.5526 / 1.0000 / 0.7119` | `0.7407 / 0.9524 / 0.8333` | `38` | `8` | `36` | final topic leak `81` |
| v1 first-pass | `0.4038 / 1.0000 / 0.5753` | `0.7407 / 0.9524 / 0.8333` | `52` | `51` | `66` | final topic leak `68` |
| v1 second-pass | `0.5122 / 1.0000 / 0.6774` | `0.6667 / 0.8571 / 0.7500` | `41` | `41` | `55` | final title/topic leak `0`; validation log `57` |

`2409` second-pass interpretation：

- topic leak 清零成功
- Stage 1 precision relative to first-pass 有回升：`0.4038 -> 0.5122`
- maybe / senior flood 有收斂，但仍偏高：`51 -> 41`、`66 -> 55`
- 最大失敗點是 Combined F1 從 `0.8333` 掉到 `0.7500`
- 這表示 second-pass 目前成功修掉 hygiene，但在 `2409` 上過度收縮 Stage 1 defer / selection，導致 Stage 2 無法維持 first-pass 的 closure gains

### 2. Metrics table: `2511.13936`

sources：

- current Stage 1：
  - `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
- current Combined：
  - `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`
- current routing snapshot：
  - `screening/results/2511.13936_full/latte_review_results.json`
  - `screening/results/2511.13936_full/latte_fulltext_review_results.json`
- v0：
  - `screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/*`
- v1 first-pass：
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2511.13936__qa+synthesis/*`
- v1 second-pass：
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2511.13936__qa+synthesis/*`

| Source | Stage 1 P / R / F1 | Combined P / R / F1 | Stage 2 Selected | Stage 1 Maybe | Stage 1 Senior-Finalized | Hygiene |
| --- | --- | --- | ---: | ---: | ---: | --- |
| current production | `0.7838 / 0.9667 / 0.8657` | `0.8966 / 0.8667 / 0.8814` | `36` | `12` | `45` | n/a |
| v0 `qa+synthesis` | `0.9600 / 0.8000 / 0.8727` | `0.9583 / 0.7667 / 0.8519` | `25` | `1` | `23` | final review-title leak `32` |
| v1 first-pass | `0.4688 / 1.0000 / 0.6383` | `0.9231 / 0.8000 / 0.8571` | `64` | `64` | `77` | final title/topic leak `0`; validation log `7` |
| v1 second-pass | `0.9259 / 0.8333 / 0.8772` | `0.9600 / 0.8000 / 0.8727` | `27` | `26` | `49` | final title/topic leak `0`; validation log `13` |

`2511` second-pass interpretation：

- hygiene 保持乾淨，title/topic leak final outputs 仍為 `0`
- Stage 1 precision 大幅回升：`0.4688 -> 0.9259`
- Stage 1 F1 回升到 `0.8772`，已高於 first-pass `0.6383`，也略高於 current production `0.8657`
- Combined F1 提升到 `0.8727`
  - 高於 v0 `0.8519`
  - 高於 v1 first-pass `0.8571`
  - 但仍低於 current production `0.8814`
- Stage 2 selected count 大幅收斂：`64 -> 27`
- maybe / senior flood 明顯收斂：`64 -> 26`、`77 -> 49`

結論：second-pass 的 defer 收斂在 `2511` 上是有效的。

### 3. Case-Level Inspection

#### `2409 / elallaoui2018automatic`

來源：

- v0:
  - `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_review_results.json`
  - `screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
- v1 first-pass:
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_review_results.json`
  - `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
- v1 second-pass:
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/latte_review_results.json`
  - `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/latte_fulltext_review_results.json`

verdicts：

- v0：Stage 1 `include (senior:4)`；Combined `exclude (senior:1)`
- v1 first-pass：Stage 1 `maybe (senior:3)`；Combined `exclude (senior:2)`
- v1 second-pass：Stage 1 `maybe (senior:3)`；Combined `exclude (senior:2)`

contamination：

- v1 first-pass：case JSON 中 `2409` topic literal 命中 `2`
- v1 second-pass：命中 `0`

判讀：

- verdict 沒有相對 first-pass 改變
- 這個 case 的 second-pass 變化主要是 hygiene 修正，不是 evaluator behavior reversal

#### `2409 / honkisz2018concept`

verdicts：

- v0：Stage 1 `include (senior:4)`；Combined `include (junior:5,5)`
- v1 first-pass：Stage 1 `include (junior:4,4)`；Combined `include (junior:5,5)`
- v1 second-pass：Stage 1 `maybe (senior:3)`；Combined `include (junior:4,5)`

contamination：

- v0 / v1 first-pass / v1 second-pass：都無 `2409` topic literal 污染

判讀：

- 這個變化不是 contamination 修正
- 比較像 Stage 1 defer tightening 後，對 borderline-but-ultimately-includable case 的 routing behavior 改變

#### `2511 / anastassiou2024seed`

verdicts：

- v0：Stage 1 `exclude (senior:1)`；Combined `None`
- v1 first-pass：Stage 1 `maybe (senior:3)`；Combined `maybe (senior:3)`
- v1 second-pass：Stage 1 `maybe (senior:3)`；Combined `maybe (senior:3)`

contamination：

- v0 / v1 first-pass / v1 second-pass：title/topic literal hits 都是 `0`

判讀：

- 這不是 hygiene 問題
- 這是 recall-preserving defer 行為仍保留在 second-pass 中的 case
- 目前 residual issue 比較像 Stage 2 closure 尚未完全收斂，而不是 Stage 1 collapse

#### `2511 / lin2004rouge`

verdicts：

- v0：Stage 1 `exclude (junior:2,1)`；Combined `None`
- v1 first-pass：Stage 1 `exclude (senior:1)`；Combined `None`
- v1 second-pass：Stage 1 `exclude (junior:2,2)`；Combined `None`

contamination：

- v0：review-title literal 命中 `10`
- v1 first-pass：title/topic 命中 `0`
- v1 second-pass：title/topic 命中 `0`

判讀：

- 這個 case 的主要改善是 hygiene 修正
- second-pass 也讓 exclude 更乾淨地在 junior stage 收斂，不再依賴 senior cleanup

#### `2511 / google_scholar_hindex`

verdicts：

- v0：Stage 1 `exclude (senior:1)`；Combined `None`
- v1 first-pass：Stage 1 `maybe (senior:3)`；Combined `maybe (senior:3)`
- v1 second-pass：Stage 1 `exclude (senior:2)`；Combined `None`

contamination：

- v0：review-title literal 命中 `1`
- v1 first-pass：title/topic 命中 `0`
- v1 second-pass：title/topic 命中 `0`

判讀：

- first-pass 把這類只有 lexical overlap / metadata noise 的 case 錯送到 `maybe`
- second-pass 把它壓回 exclude
- 這是 hygiene 已穩定後，evaluator behavior 修正成功的代表案

## Exit-Criteria Check

1. `2409` topic leak = `0`
   - 結果：`PASS`
   - review hits `0`，fulltext hits `0`

2. `2511` review-title/topic leak = `0`
   - 結果：`PASS`
   - title hits `0`，topic hits `0`

3. `2511 Combined F1` > v0 `0.8519`
   - 結果：`PASS`
   - second-pass `0.8727`

4. `2511 Stage 1 precision` 明顯高於 first-pass v1 `0.4688`
   - 結果：`PASS`
   - second-pass `0.9259`

5. `2409 Combined F1` 不低於 `0.8333`
   - 結果：`FAIL`
   - second-pass `0.7500`

6. `2409` Stage 1 maybe / senior flood 明顯收斂
   - 結果：`PARTIAL FAIL`
   - maybe：`51 -> 41`
   - senior-finalized：`66 -> 55`
   - 有收斂，但仍未達建議 gate（`maybe <= 25`、`senior <= 50`）

## Phase-Gate Decision

### 是否進 Phase 2

- `NO`

### 是否值得現在擴到 `qa-only`

- `NO`

### 是否值得現在擴到四篇 regression / stability pass

- `NO`

### 原因

`2511` second-pass 已經證明兩件事：

- hygiene patch 可以把 title/topic contamination 壓到 final outputs `0`
- global defer policy 收斂後，可以把 Stage 1 precision 從 first-pass collapse 中救回來

但 `2409` second-pass 同時暴露出另一件事：

- leak 雖然清零了
- defer flood 也稍微收斂了
- 可是 Combined F1 從 `0.8333` 掉到 `0.7500`

所以目前不能說「global second-pass 直接成功」，只能說：

- hygiene repair 成功
- `2511` 的 Stage 1 defer repair 成功
- 但 `2409` 還需要下一個更窄的 closure stabilization pass

## Recommended Next Move

不要進 Phase 2，不要跑 `qa-only`，也不要跑四篇 regression。

下一步最推薦的是：

1. 凍結這次 second-pass 已經證明成功的部分：
   - `2409` / `2511` final outputs title/topic leak = `0`
   - `2511` Stage 1 defer-overfire 已大幅收斂
2. 保持這兩個 global fixes 不動：
   - protected review topic always-ban
   - `positive_fit_evidence_ids` gate + retry repair policy
3. 開一個更小的 `2409 qa+synthesis` follow-up pass，只修 `2409` Stage 2 closure stabilization
   - 不動 `2511`
   - 不動 `qa-only`
   - 不動四篇 regression
4. 只有當 `2409 Combined F1` 被拉回至少 `0.8333`，再談是否進 Phase 2

一句話總結：

- `2409`：topic leak 已清零，但 Combined 掉太多，還不能放行
- `2511`：second-pass 明顯優於 first-pass，也高於 v0 Combined，但還沒強到足以單獨推進 Phase 2

如果後續 second-pass / third-pass 分支開始變多，再用 `www.k-dense.ai` 管 workflow，會比在多個對話串裡反覆搬運 handoff 更乾淨。
