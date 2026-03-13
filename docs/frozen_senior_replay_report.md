# Frozen-input SeniorLead Replay Report

## 1) 本輪完成的兩件事
1. **任務 A：Runtime prompt externalization（zero-behavior-change）**
   - 把 runtime 真正使用的 Stage 1 / Stage 2 prompt 從 `topic_pipeline.py` 移到外部檔案。
2. **任務 B：Frozen-input SeniorLead replay（雙 prompt 對照）**
   - 固定 junior 輸出與 sent-to-senior case 集合，只重跑 SeniorLead，比較 `stage1_senior_no_marker` 與 `stage1_senior_prompt_tuned`。

## 2) Runtime prompt externalization 怎麼做
- 新增 runtime prompt 檔：
  - `scripts/screening/runtime_prompts/runtime_prompts.json`
- 新增 loader：
  - `scripts/screening/vendor/src/pipelines/runtime_prompt_loader.py`
- 修改 production path：
  - `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
  - Stage 1 Junior / Senior 與 Stage 2 Fulltext Junior / Senior 改由 loader 讀 `backstory` / `additional_context`。
- Stage 1 senior 在 production path 仍使用 `stage1_senior_prompt_tuned`（維持現況）。

### Zero-behavior-change 證據
- 生成等價檢查：
  - `screening/results/runtime_prompt_externalization/prompt_equivalence_check.json`
- 檢查結果：
  - `all_match = true`
  - `mismatch_count = 0`
- 並保留基準快照：
  - `screening/results/runtime_prompt_externalization/original_runtime_prompts.from_topic_pipeline.json`
  - `screening/results/runtime_prompt_externalization/historical_stage1_senior_no_marker.from_git_229e5e1.json`

## 3) 被刪除的舊 template
- `sr_screening_prompts_3stage/sr_specific/03_stage1_2_criteria_review.md`
- `sr_screening_prompts/sr_specific/05_stage2_criteria_review.md`

## 4) Frozen baseline 定義
固定來源（四篇 baseline no-marker 結果）：
- `screening/results/2307.05527_full/latte_review_results.senior_no_marker.json`
- `screening/results/2409.13738_full/latte_review_results.senior_no_marker.json`
- `screening/results/2511.13936_full/latte_review_results.senior_no_marker.json`
- `screening/results/2601.19926_full/latte_review_results.senior_no_marker.json`

固定欄位（每筆 sent-to-senior case）：
- `key`
- `title`
- `abstract`
- `round-A_JuniorNano_output`
- `round-A_JuniorNano_evaluation`
- `round-A_JuniorMini_output`
- `round-A_JuniorMini_evaluation`
- baseline 原本是否 sent-to-senior 的集合

Frozen 輸入輸出位置（每篇）：
- `screening/results/<paper_id>_full/frozen_senior_replay/frozen_stage1_senior_inputs.json`

## 5) 本輪只比較的兩個 SeniorLead prompt
1. `stage1_senior_no_marker`
2. `stage1_senior_prompt_tuned`

沒有引入第三種 prompt。

## 6) View 1：senior-decided subset（只看 baseline 原 sent-to-senior）
來源：`screening/results/frozen_senior_replay_summary.json`

### 各篇分布（`1/2`, `3`, `4/5`）
- **2307.05527**（n=43）
  - baseline no-marker: `24, 5, 14`
  - replay no-marker: `20, 12, 11`
  - replay tuned: `29, 11, 3`
- **2409.13738**（n=55）
  - baseline no-marker: `27, 21, 7`
  - replay no-marker: `27, 20, 8`
  - replay tuned: `42, 8, 5`
- **2511.13936**（n=53）
  - baseline no-marker: `21, 28, 4`
  - replay no-marker: `20, 29, 4`
  - replay tuned: `36, 14, 3`
- **2601.19926**（n=215）
  - baseline no-marker: `16, 165, 34`
  - replay no-marker: `10, 175, 30`
  - replay tuned: `85, 121, 9`

### 合計分布（n=366）
- baseline no-marker: `1/2=88, 3=219, 4/5=59`
- replay no-marker: `1/2=77, 3=236, 4/5=53`
- replay tuned: `1/2=192, 3=154, 4/5=20`

## 7) View 2：整體 Stage 1 reconstructed
來源：`screening/results/frozen_senior_replay_summary.json`

## Aggregate（四篇合併）
- baseline no-marker：
  - `TP=545, FP=64, TN=117, FN=12`
  - `precision=0.8949, recall=0.9785, f1=0.9348`
- replay no-marker：
  - `TP=550, FP=70, TN=111, FN=7`
  - `precision=0.8871, recall=0.9874, f1=0.9346`
- replay tuned：
  - `TP=475, FP=30, TN=151, FN=82`
  - `precision=0.9406, recall=0.8528, f1=0.8945`

## Per-paper（重點三篇）
- **2409.13738**
  - baseline: `P=0.4468, R=1.0000, F1=0.6176`
  - replay no-marker: `P=0.4468, R=1.0000, F1=0.6176`
  - replay tuned: `P=0.6563, R=1.0000, F1=0.7925`
- **2511.13936**
  - baseline: `P=0.5686, R=0.9667, F1=0.7160`
  - replay no-marker: `P=0.5577, R=0.9667, F1=0.7073`
  - replay tuned: `P=0.7500, R=0.9000, F1=0.8182`
- **2601.19926**
  - baseline: `P=0.9735, R=0.9851, F1=0.9792`
  - replay no-marker: `P=0.9623, R=0.9910, F1=0.9765`
  - replay tuned: `P=0.9778, R=0.7881, F1=0.8727`

## 8) 可歸因於 Senior prompt 的差異
用 `replay tuned` 對 `replay no-marker`（同 frozen inputs）做比較：
- **2409.13738**：`ΔP +0.2094, ΔR +0.0000, ΔF1 +0.1748`
- **2511.13936**：`ΔP +0.1923, ΔR -0.0667, ΔF1 +0.1109`
- **2601.19926**：`ΔP +0.0155, ΔR -0.2030, ΔF1 -0.1037`

結論：在 frozen-input 下，tuned prompt 的高槓桿效果仍明顯存在（尤其壓低 FP、同時在 2601 明顯增加 FN）。

## 9) 可能屬於 rerun noise 的差異
用 `replay no-marker` 對 `baseline no-marker`（同 prompt，不同 run）做比較：
- **2409.13738**：`ΔP 0.0000, ΔR 0.0000, ΔF1 0.0000`
- **2511.13936**：`ΔP -0.0109, ΔR 0.0000, ΔF1 -0.0087`
- **2601.19926**：`ΔP -0.0111, ΔR +0.0060, ΔF1 -0.0028`

結論：rerun noise 存在但幅度小；先前觀察到的大差異主要不是 noise，而是 senior prompt 本身。

## 10) Spot check（指定案例）
來源：`screening/results/frozen_senior_replay_summary.json` 的 `aggregate.spot_checks`

1. **2409.13738 / etikala2021extracting**
   - baseline junior: `(Nano=3, Mini=4)`
   - baseline senior: `3`
   - replay no-marker senior: `4`
   - replay tuned senior: `3`
   - 判讀：在邊界案上 tuned 保守於 no-marker，符合「壓縮過度樂觀 include」方向。

2. **2511.13936 / lotfian2016retrieving**
   - baseline junior: `(3, 3)`
   - baseline senior: `3`
   - replay no-marker senior: `3`
   - replay tuned senior: `3`
   - 判讀：穩定不變，符合預期（純邊界、資訊不足）。

3. **2511.13936 / han2020ordinal**
   - baseline junior: `(5, 3)`
   - baseline senior: `4`
   - replay no-marker senior: `3`
   - replay tuned senior: `3`
   - 判讀：兩版 replay 都比 baseline 更保守；此案顯示單次 baseline senior 可能偏樂觀。

4. **2601.19926 / mccoy_right_2019**
   - baseline junior: `(3, 3)`
   - baseline senior: `3`
   - replay no-marker senior: `3`
   - replay tuned senior: `2`
   - 判讀：tuned 將邊界案推向排除，符合 2601 recall 下降主因。

5. **2307.05527 / Suh2021AI**
   - baseline junior: `(5, 3)`
   - baseline senior: `5`
   - replay no-marker senior: `5`
   - replay tuned senior: `5`
   - 判讀：強陽性案三者一致，符合預期。

## 11) 直接回答（你要求的 5 個問題）
1. 在 frozen-input 條件下，`senior_prompt_tuned` 對 `2409` 的 precision 改善是否仍存在？
   - **是，仍存在且幅度大**（`0.4468 -> 0.6563`，`+0.2094`）。
2. 在 frozen-input 條件下，`senior_prompt_tuned` 對 `2511` 的 precision 改善是否仍存在？
   - **是，仍存在且幅度大**（相對 replay no-marker：`0.5577 -> 0.7500`，`+0.1923`）。
3. 在 frozen-input 條件下，`senior_prompt_tuned` 是否仍會明顯傷到 `2601` recall？
   - **是，仍明顯受傷**（相對 replay no-marker：`0.9910 -> 0.7881`，`-0.2030`）。
4. 如果差異仍然存在，是否可說明 SeniorLead prompt 是高槓桿變因？
   - **可以**。因為 frozen-input 已鎖住 juniors 與 sent-to-senior 集合，差異仍大，主因可歸因 senior prompt。
5. 如果差異縮小很多，是否代表先前混有 rerun noise？
   - **原則上是**；但本輪結果顯示差異未縮小到可忽略，noise 只占小部分。

## 12) 產物清單
### 程式與模板
- `scripts/screening/runtime_prompts/runtime_prompts.json`
- `scripts/screening/vendor/src/pipelines/runtime_prompt_loader.py`
- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
- `scripts/screening/replay_stage1_senior.py`
- `scripts/screening/verify_runtime_prompt_externalization.py`

### 驗證與彙總
- `screening/results/runtime_prompt_externalization/prompt_equivalence_check.json`
- `screening/results/frozen_senior_replay_summary.json`

### 各篇 replay 目錄
- `screening/results/2307.05527_full/frozen_senior_replay/`
- `screening/results/2409.13738_full/frozen_senior_replay/`
- `screening/results/2511.13936_full/frozen_senior_replay/`
- `screening/results/2601.19926_full/frozen_senior_replay/`

## 13) 下一步建議
1. 以 `2601` 高風險 FN case 建立「tuned prompt 失誤子集」做 targeted wording 修補，而非全域再調。
2. 保留 frozen-input replay bench，後續任何 Senior prompt 改動都先跑 replay 再跑 end-to-end。
3. 若要最終上線新 prompt，先以 paper-level guardrail 設定最低 recall 門檻（特別是 2601 類型）。
