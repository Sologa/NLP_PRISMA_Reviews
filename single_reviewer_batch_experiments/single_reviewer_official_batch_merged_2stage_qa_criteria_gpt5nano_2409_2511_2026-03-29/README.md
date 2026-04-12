# 單審查者官方 Batch Merged 2-Stage QA+Criteria（`gpt-5-nano`）

這個 bundle 是隔離的 experiment-only 實作。
目前 contract 為 score-authoritative：模型只回 `stage_score`，stage recommendation 由 runner deterministic 派生。

`--phase all` 僅支援 `--mode run`。因為 `stage2_review` 依賴 `stage1_review` collect 後的 gating 結果；若要分段執行，請明確指定 `stage1_review` 或 `stage2_review`。

## 核心定義

- current-state-aligned `Stage 1 merged review -> Stage 2 merged review`
- 每個 stage 只呼叫一次模型，於同一 prompt 內完成 micro-QA 與 criteria 判定
- decision authority 對齊 production score-driven flow
- 單一 reviewer lane
- cutoff-first
- 不修改 production criteria、runtime prompts、shared batch helper
- 測試 paper 固定為 `2409.13738` 與 `2511.13936`

## 輸入來源

- metadata：`refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- gold：`refs/<paper_id>/metadata/title_abstracts_metadata-annotated.jsonl`
- fulltext：`refs/<paper_id>/mds/*.md`
- Stage 1 criteria：`criteria_stage1/<paper_id>.json`
- Stage 2 criteria：`criteria_stage2/<paper_id>.json`
- cutoff：`cutoff_jsons/<paper_id>.json`

## 驗證

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_merged_2stage_qa_criteria_gpt5nano_2409_2511_2026-03-29/tools/validate_bundle.py \
  --check-serialization
```

## Smoke

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_merged_2stage_qa_criteria_gpt5nano_2409_2511_2026-03-29/tools/run_experiment.py \
  --mode run \
  --phase all \
  --run-id 20260329_smoke_gpt5nano_low_merged2stage_scoreauth_2409_2511 \
  --papers 2409.13738 2511.13936 \
  --candidate-keys-file single_reviewer_batch_experiments/single_reviewer_official_batch_merged_2stage_qa_criteria_gpt5nano_2409_2511_2026-03-29/smoke/smoke_candidates.json \
  --reasoning-effort low
```

## Full

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_merged_2stage_qa_criteria_gpt5nano_2409_2511_2026-03-29/tools/run_experiment.py \
  --mode run \
  --phase all \
  --run-id 20260329_full_gpt5nano_low_merged2stage_scoreauth_2409_2511 \
  --papers 2409.13738 2511.13936 \
  --reasoning-effort low
```

## 單一 phase

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_merged_2stage_qa_criteria_gpt5nano_2409_2511_2026-03-29/tools/run_experiment.py \
  --mode submit \
  --phase stage1_review \
  --run-id <run_id> \
  --papers 2409.13738 \
  --reasoning-effort low
```

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_merged_2stage_qa_criteria_gpt5nano_2409_2511_2026-03-29/tools/run_experiment.py \
  --mode collect \
  --phase stage1_review \
  --run-id <run_id> \
  --papers 2409.13738
```
