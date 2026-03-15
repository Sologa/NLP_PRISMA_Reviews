# Stage-Split Criteria Migration Report

Date: 2026-03-15

## 1) 為什麼改成兩份 criteria

本次遷移的核心目標是把「方法學定義」與「可觀測性限制」分開：

- `criteria_stage2/`：canonical、source-faithful、對齊原 paper 的完整 eligibility（final fulltext decision 依此為準）。
- `criteria_stage1/`：僅保留 title/abstract 可觀測的投影，不新增原文沒有的 hard exclusion。

這樣做可以避免把 runtime 調參需求誤寫成正式 criteria。

## 2) 為什麼不再使用 guidance

本輪刻意不新增第三層（`reviewer_guidance` / `operational_policy`）：

- 第三層會讓規則來源變成三套（Stage1/Stage2/guidance），邊界更難追責。
- 本輪需求是直接把 stage 差異內建在兩份 criteria 本體，而不是再疊解釋層。
- 因此本次實作只有兩份 criteria，無 guidance 檔與 guidance 欄位。

## 3) 四篇 paper 的 stage1 / stage2 差異

### 2409.13738

- Stage 2（canonical）：回到原文 IC.1-IC.4 / EC.1-EC.4（full paper、peer-reviewed、English/fulltext、primary research、NLP for process extraction、concrete method、experiments）。
- Stage 1（projection）：只保留 title/abstract 可觀測核心：
  - 是否明確是 NLP for process extraction from natural language text。
  - 是否可觀測到 text -> process representation/model 的任務訊號。
  - 若證據不完整則保留 `maybe`，延後 Stage 2。
- faithful projection 判定句（代表）：
  - `Title/abstract explicitly indicates ... specifically covers the use of NLP for process extraction ...`
  - `Observable non-target examples from EC.3: ... process redesign/matching/prediction ...`
- 移除的超譯 hardening（不再放入正式 criteria）：
  - `Generic NLP/LLM/dataset/foundation-model paper ... exclude`
  - `Output-object mismatch: IE/NER/RE/classification/retrieval ... exclude`
  - `compliance/recommendation/simulation` 等外擴 hard negatives
  - `executable extraction pipeline` 這類加嚴措辭

### 2511.13936

- Stage 2（canonical）：回到原文 final selection 定義（audio domain + preference learning + 非 survey/review；evaluation-only preference 排除；multimodal including audio 納入）。
- Stage 1（projection）：
  - ranking / A-B / comparative preference 的可觀測訊號
  - rating 只有在可觀測為 ranking 轉換時才算
  - 無 explicit comparison 但可觀測 RL loop for audio model 仍可納入
  - audio domain（含 multimodal including audio）
- faithful projection 判定句（代表）：
  - `... ranking or A/B comparison of two or more audio clips`
  - `... still eligible when ... RL training loop for an audio model`
  - `Multimodal works including audio are treated as within the audio domain`
- 移除的超譯 hardening：
  - `audio must be core` 強制門檻
  - `training objective/loss/reward/model selection` 細粒度硬 gate
  - `IEMOCAP/SEMAINE`、`SER/ordinal` 這類額外硬化規則

### 2307.05527

- Stage 1 = Stage 2（本輪先維持一致）。

### 2601.19926

- Stage 1 = Stage 2（本輪先維持一致）。

## 4) 哪些 paper 兩份相同、哪些不同

- 不同：`2409.13738`, `2511.13936`
- 相同：`2307.05527`, `2601.19926`

檢查結果：

- `cmp criteria_stage1/2307.05527.json criteria_stage2/2307.05527.json` -> identical
- `cmp criteria_stage1/2601.19926.json criteria_stage2/2601.19926.json` -> identical

## 5) runtime 如何讀取兩份 criteria（無 fallback）

本次在 `scripts/screening/vendor/src/pipelines/topic_pipeline.py` 新增 stage-aware 解析：

- `run_latte_review`（Stage 1）只解析 `criteria_stage1/<paper_id>.json`
- `run_latte_fulltext_review`（Stage 2）只解析 `criteria_stage2/<paper_id>.json`
- 若缺檔，直接 `FileNotFoundError`（明確訊息含 `本流程不使用 fallback`）
- 不再回退到 `workspace/criteria/criteria.json` 或舊 `criteria_jsons/`

另外更新：

- `scripts/screening/run_review_smoke5.sh`
- `scripts/screening/run_review_full_and_f1.sh`
- `scripts/screening/run_review_2511_13936.sh`
- `scripts/screening/replay_stage1_senior.py`
- `scripts/screening/README.md`
- `scripts/screening/vendor/scripts/topic_pipeline.py`（CLI help 文案）

## 6) 測試結果

### A. 路徑分流驗證（必須）

`run_review_smoke5.sh` 執行輸出明確顯示：

- `stage1_criteria_path=/.../criteria_stage1/<paper>.json`
- `stage2_criteria_path=/.../criteria_stage2/<paper>.json`

且 pipeline 回傳 payload 亦分別含：

- Stage 1 回傳 `criteria_path=/.../criteria_stage1/...`
- Stage 2 回傳 `criteria_path=/.../criteria_stage2/...`

### B. 正式 benchmark（2409 / 2511，TOP_K=0 + fulltext）

#### 2409.13738

- Stage 1 (`stage1_f1.stage_split_criteria_migration.json`)
  - precision: `0.6000`
  - recall: `1.0000`
  - f1: `0.7500`
  - tp/fp/tn/fn: `21/14/43/0`
- Combined (`combined_f1.stage_split_criteria_migration.json`)
  - precision: `0.6667`
  - recall: `0.9524`
  - f1: `0.7843`
  - tp/fp/tn/fn: `20/10/47/1`

#### 2511.13936

- Stage 1 (`stage1_f1.stage_split_criteria_migration.json`)
  - precision: `0.7838`
  - recall: `0.9667`
  - f1: `0.8657`
  - tp/fp/tn/fn: `29/8/46/1`
- Combined (`combined_f1.stage_split_criteria_migration.json`)
  - precision: `0.8966`
  - recall: `0.8667`
  - f1: `0.8814`
  - tp/fp/tn/fn: `26/3/51/4`

### C. Sanity（2307 / 2601）

- `2307.05527`：TOP_K=5 Stage1-only 成功，回傳 `criteria_path=/.../criteria_stage1/2307.05527.json`。
- `2601.19926`：TOP_K=5 Stage1-only 成功，回傳 `criteria_path=/.../criteria_stage1/2601.19926.json`。

補充：`2307` 在 TOP_K=5 + fulltext 嘗試時，因該批次無 include/maybe 候選，fulltext 流程回報「無可審查條目」而停止；此為資料批次結果，不是路徑解析錯誤。

## 7) 是否真正解決「超譯 criteria」問題

在本輪目標範圍內，答案是「有實質改善」：

- Stage 2 被固定為 source-faithful canonical criteria。
- Stage 1 僅保留可觀測投影，且 `2409/2511` 已移除明確超譯 hardening。
- runtime 強制 stage-specific 讀取且無 fallback，避免舊路徑或混用造成語義漂移。

仍需注意：

- 本輪未改 aggregation/SeniorLead/prompt，因此最終指標仍受既有流程影響。
- 但 criteria 層的語義責任已明確切開，後續誤差可更乾淨地歸因。

