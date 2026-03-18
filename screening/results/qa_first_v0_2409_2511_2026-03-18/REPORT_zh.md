# QA-first experiment v0 實驗結果報告

## Current-State Recap

- current runtime prompt authority：`scripts/screening/runtime_prompts/runtime_prompts.json`。
- current production criteria authority：`criteria_stage1/<paper_id>.json` 與 `criteria_stage2/<paper_id>.json`。
- 本次 `seed QA` 只用於 experiment workflow，不是 production criteria。
- current metrics authority 仍維持 production baseline：`2409` Stage 1 `0.7500` / Combined `0.7843`；`2511` Stage 1 `0.8657` / Combined `0.8814`。

## Run Setup

- 執行日期：`2026-03-18 15:23:06`
- junior models：`gpt-5-nano` + `gpt-4.1-mini`
- synthesis / evaluator model：`gpt-4.1-mini`
- senior model：`gpt-4.1-mini`
- 所有 experiment prompts 皆由外部 `.md` 模板渲染，未寫死在 `.py`。

## Metrics Summary

| Paper | Arm | Stage 1 F1 | Delta vs current | Combined F1 | Delta vs current | Stage 2 reviewed |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2409.13738` | `qa-only` | 0.7368 | -0.0132 | 0.8085 | +0.0242 | 36 |
| `2409.13738` | `qa+synthesis` | 0.7119 | -0.0381 | 0.8333 | +0.0490 | 38 |
| `2511.13936` | `qa-only` | 0.8519 | -0.0138 | 0.8302 | -0.0512 | 24 |
| `2511.13936` | `qa+synthesis` | 0.8727 | +0.0071 | 0.8519 | -0.0295 | 25 |

## Per-Paper Notes

### `2409.13738`

- current reference baseline：Stage 1 `0.7500`，Combined `0.7843`。
- `qa-only`：Stage 1 `0.7368`，Combined `0.8085`，Stage 2 reviewed `36` 筆。
- `qa+synthesis`：Stage 1 `0.7119`，Combined `0.8333`，Stage 2 reviewed `38` 筆。

### `2511.13936`

- current reference baseline：Stage 1 `0.8657`，Combined `0.8814`。
- `qa-only`：Stage 1 `0.8519`，Combined `0.8302`，Stage 2 reviewed `24` 筆。
- `qa+synthesis`：Stage 1 `0.8727`，Combined `0.8519`，Stage 2 reviewed `25` 筆。

## Result Files

- `2409.13738 + qa-only`
  stage1 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa-only/latte_review_results.json`
  stage2 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa-only/latte_fulltext_review_results.json`
  stage1 metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa-only/stage1_f1.json`
  combined metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa-only/combined_f1.json`
- `2409.13738 + qa+synthesis`
  stage1 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_review_results.json`
  stage2 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
  stage1 metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/stage1_f1.json`
  combined metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2409.13738__qa+synthesis/combined_f1.json`
- `2511.13936 + qa-only`
  stage1 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa-only/latte_review_results.json`
  stage2 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa-only/latte_fulltext_review_results.json`
  stage1 metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa-only/stage1_f1.json`
  combined metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa-only/combined_f1.json`
- `2511.13936 + qa+synthesis`
  stage1 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/latte_review_results.json`
  stage2 results: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/latte_fulltext_review_results.json`
  stage1 metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/stage1_f1.json`
  combined metrics: `/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/qa_first_v0_2409_2511_2026-03-18/2511.13936__qa+synthesis/combined_f1.json`

## Notes

- 這些結果是 experiment-only outputs，不覆寫 current production score authority。
- 若後續同時展開多條實驗線，建議改用 `www.k-dense.ai` 管理 workflow。
