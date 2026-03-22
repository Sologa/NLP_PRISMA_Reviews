# 單審查者官方批次基線（`gpt-5-nano`）

這個 bundle 是隔離的 experiment-only 實作。

## 核心定義

- 單一審查者全文直審
- 綁定 OpenAI 官方 Batch API
- 不修改 production prompt source
- 不修改 production shared API call semantics
- 四篇 paper 全部納入同一條實驗線

## 輸入來源

- metadata：`refs/<paper_id>/metadata/title_abstracts_metadata.jsonl`
- gold：`refs/<paper_id>/metadata/title_abstracts_metadata-annotated.jsonl`
- fulltext：`refs/<paper_id>/mds/*.md`
- criteria：`criteria_stage2/<paper_id>.json`

## 指令

驗證 bundle：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/tools/validate_bundle.py
```

驗證 bundle、model 與 request serialization：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/tools/validate_bundle.py \
  --check-model \
  --check-serialization
```

提交最小官方批次冒煙：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/tools/run_experiment.py \
  --mode submit \
  --papers 2409.13738 \
  --max-records 2
```

收集指定 run 的結果：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/tools/run_experiment.py \
  --mode collect \
  --run-id <run_id>
```

小型一鍵冒煙：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/tools/run_experiment.py \
  --mode run \
  --papers 2409.13738 \
  --max-records 2 \
  --batch-max-wait-minutes 30
```

完整四篇：

```bash
./.venv/bin/python single_reviewer_batch_experiments/single_reviewer_official_batch_gpt5nano_all4_2026-03-22/tools/run_experiment.py \
  --mode run \
  --papers 2307.05527 2409.13738 2511.13936 2601.19926
```
