# 2409 Criteria 變更後 Low 重跑

這個 bundle 是隔離的 experiment-only 實作。

## 核心定義

- 單一審查者全文直審
- 綁定 OpenAI 官方 Batch API
- 僅針對 `2409.13738`
- 一律先套用 `cutoff_jsons/2409.13738.json`
- 使用 `--model-override` 重跑多個模型
- 預設搭配 `--reasoning-effort low`

## 輸入來源

- metadata：`refs/2409.13738/metadata/title_abstracts_metadata.jsonl`
- gold：`refs/2409.13738/metadata/title_abstracts_metadata-annotated.jsonl`
- fulltext：`refs/2409.13738/mds/*.md`
- criteria：`criteria_stage2/2409.13738.json`

## 指令

驗證 bundle：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/tools/validate_bundle.py
```

驗證指定模型與 request serialization：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/tools/validate_bundle.py \
  --check-model \
  --check-serialization \
  --model-override gpt-5-mini
```

直接重跑單一模型：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --model-override gpt-5-mini \
  --reasoning-effort low
```

只收集指定 run：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_2409_low_rerun_after_criteria_change_2026-03-24/tools/run_experiment.py \
  --mode collect \
  --run-id <run_id>
```
