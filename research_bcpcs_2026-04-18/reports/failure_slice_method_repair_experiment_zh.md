# BCPCS Failure-Slice Method Repair Experiment

本報告記錄 `2026-04-19` 的 BCPCS failure-slice method fix 與 re-experiment。這是 failure-slice diagnostic，不是 full-corpus benchmark，不是 production workflow replacement，也不代表正式 SR workflow 的整體提升。

## 1. 問題與修正

前一輪結果把多種狀態混成單一 headline F1，容易把兩類問題混在一起：

- 模型真的做出 `include` / `exclude` / `maybe` 判斷後的 decision quality
- `unknown`、`route`、JSON empty、parse/schema failure、full text unresolved 等 coverage/runtime 問題

本輪新增 v2 evaluator，固定輸出三組指標：

- `auto_decidable_f1`：只統計有明確 final decision 的 rows。
- `coverage`：統計 definite decision、unknown/routed、runtime failure 的比例。
- `conservative_f1`：保留舊式 worst-case 對照，把 unknown/routed/runtime 視為 negative。

同時新增 runtime failure taxonomy，把下列狀態從 semantic decision 中分離：

- `runtime_failed_json_empty`
- `runtime_failed_parse`
- `runtime_failed_schema`
- `stage2_not_available`
- `fulltext_unresolved`

## 2. 實作範圍

所有新增或修改都隔離在 `research_bcpcs_2026-04-18/` 下，沒有修改 production/historical artifacts。

新增的 methodfix code：

- `src/failure_slice_eval_v2.py`
- `src/failure_slice_runtime_taxonomy.py`
- `src/failure_slice_methodfix_runner.py`

復用既有 isolated runner / inventory / validation code：

- `src/failure_slice_runner.py`
- `src/failure_slice_inventory.py`
- `src/failure_slice_validate.py`
- `src/failure_slice_cost_audit.py`

Reviewer prompt 仍只允許看到正常 screening 可見資訊：criteria、candidate title/abstract/metadata、Stage 2 full text excerpt、Stage 1 BCPCS handoff、BCPCS output schema。prompt scan 結果顯示 forbidden-field hit count 為 `0`。

## 3. Run Set

本輪必跑模型：

- `gpt-5-nano`
- `gpt-5.4-nano`

主要 full127 runs：

| run_id | model | Stage 1 effort | Stage 2 effort/profile | scope | status |
| --- | --- | --- | --- | --- | --- |
| `bcpcs_methodfix_gpt5nano_2stage_async_2026-04-19_full127_v1` | `gpt-5-nano` | `high` | `high`, original full-text prompt | full127 | completed clean |
| `bcpcs_methodfix_gpt54nano_2stage_async_2026-04-19_full127_v1` | `gpt-5.4-nano` | `high` | `high`, original full-text prompt | full127 | completed clean |

Smoke runs：

| run_id | model | profile | purpose | outcome |
| --- | --- | --- | --- | --- |
| `bcpcs_methodfix_gpt5nano_2stage_async_2026-04-19_primary22_smoke_v1` | `gpt-5-nano` | original high | primary22 smoke | clean; primary F1 `0.6667` |
| `bcpcs_methodfix_gpt54nano_2stage_async_2026-04-19_primary22_smoke_v1` | `gpt-5.4-nano` | compact ledger | parser stress test | JSON-empty resolved, but decision quality poor |
| `bcpcs_methodfix_gpt54nano_2stage_async_2026-04-19_primary22_smoke_original_v1` | `gpt-5.4-nano` | original high | safer effort profile | JSON-empty resolved, but decision quality still poor |

## 4. Full127 Results

### Primary 22

| model/run | auto F1 | conservative F1 | coverage | runtime failures | TP/FP/TN/FN | Stage 1 gate recall |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `gpt-5-nano` methodfix | `0.6667` | `0.6667` | `100.00%` | `0` | `11/1/0/10` | `0.9048` |
| `gpt-5.4-nano` methodfix | `0.4828` | `0.4828` | `100.00%` | `0` | `7/1/0/14` | `0.7619` |

### Secondary 105

| model/run | auto F1 | conservative F1 | coverage | runtime failures | TP/FP/TN/FN | Stage 1 gate recall |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `gpt-5-nano` methodfix | `0.5972` | `0.5931` | `98.10%` | `0` | `43/9/2/49` auto | `0.7849` |
| `gpt-5.4-nano` methodfix | `0.4219` | `0.4219` | `99.05%` | `0` | `27/8/3/66` auto | `0.6129` |

Secondary105 是 criteria/gold tension secondary inventory，只能作分層診斷與 reporting，不能當成 primary unbiased improvement evidence。

### All 127 Diagnostic Inventory

| model/run | auto F1 | conservative F1 | coverage | runtime failures | TP/FP/TN/FN | Stage 1 gate recall |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `gpt-5-nano` methodfix | `0.6102` | `0.6067` | `98.43%` | `0` | `54/10/2/59` auto | `0.8070` |
| `gpt-5.4-nano` methodfix | `0.4331` | `0.4331` | `99.21%` | `0` | `34/9/3/80` auto | `0.6404` |

這張 all127 表只能解讀為 diagnostic inventory 上的表現，不能當作 full benchmark headline。

## 5. 與前一輪 `gpt-5.4-nano xhigh` 比較

前一輪 run：

- `bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1`

用同一個 v2 evaluator 重新計算後：

| run | all127 auto F1 | all127 conservative F1 | coverage | runtime failures |
| --- | ---: | ---: | ---: | ---: |
| `gpt-5.4-nano xhigh` previous | `0.5917` | `0.5747` | `93.70%` | `6` |
| `gpt-5.4-nano high` methodfix | `0.4331` | `0.4331` | `99.21%` | `0` |

因此，methodfix 對 `gpt-5.4-nano` 的影響是：

- 解決了 JSON-empty/runtime failure 問題：`6 -> 0`
- 但 decision quality 明顯下降：auto F1 `0.5917 -> 0.4331`

這表示前一輪「分數爛」不只是 parser 或 JSON-empty 問題。`xhigh + long full text` 的 runtime stability 差，但較能恢復部分 positives；`high` profile 穩定輸出 JSON，卻更保守，recall 下降。

## 6. 為什麼 `gpt-5-nano` 仍然最好

本輪修正後，`gpt-5-nano` 不是因為 runtime failure 被少算才贏。它在 methodfix full127 中：

- runtime failure = `0`
- coverage = `98.43%`
- auto F1 = `0.6102`
- conservative F1 = `0.6067`

`gpt-5.4-nano high` 甚至有更高 coverage (`99.21%`) 且 runtime failure = `0`，但 auto F1 只有 `0.4331`。主要差距在 recall：

- `gpt-5-nano` all127 auto recall = `0.4779`
- `gpt-5.4-nano` all127 auto recall = `0.2982`

Stage 1 gate 也呈現同方向差距：

- `gpt-5-nano` all127 gate recall = `0.8070`
- `gpt-5.4-nano` all127 gate recall = `0.6404`

所以目前較合理的解釋是：`gpt-5.4-nano high` 在這個 failure-slice workflow 裡更保守，尤其會在 Stage 1 或 Stage 2 把 prior FN 類 candidate 繼續判成 negative。這是 decision behavior 問題，不是單純評估程式把分數壓低。

## 7. Evidence Ledger Validity

| model/run | stage outputs | outputs with ledger | ledger rows | span validated rate | span completeness |
| --- | ---: | ---: | ---: | ---: | ---: |
| `gpt-5-nano` methodfix | `231` | `231` | `378` | `85.19%` | `100.00%` |
| `gpt-5.4-nano` methodfix | `213` | `213` | `542` | `92.44%` | `100.00%` |

兩個 methodfix run 都有完整 ledger schema output；`gpt-5.4-nano` 的 ledger span validation rate 反而較高，但這沒有轉化成更好的 decision recall。

## 8. Cost

Methodfix runs 的 Batch usage cost：

| run | input tokens | output tokens | cost |
| --- | ---: | ---: | ---: |
| `gpt-5-nano` full127 methodfix | `1,485,222` | `3,269,794` | `$0.69108935` |
| `gpt-5.4-nano` full127 methodfix | `1,318,591` | `634,649` | `$0.528514725` |
| `gpt-5-nano` primary22 smoke | n/a | n/a | `$0.12354065` |
| `gpt-5.4-nano` primary22 compact smoke | n/a | n/a | `$0.077777025` |
| `gpt-5.4-nano` primary22 original smoke | n/a | n/a | `$0.106900725` |

Methodfix total recorded cost：`$1.527822475`，低於本輪 `$10` safety cap。

注意：若把本工作串先前已執行的所有 diagnostic/sanity runs 都算入，`research_bcpcs_2026-04-18/runs/*/cost/cost_summary.json` 目前合計約 `$20.71186105`。本報告的 `$10` cap 判定只針對 methodfix re-experiment run set。

## 9. Validation

兩個 full127 methodfix runs 均通過：

- source inventory count：`127 / 22 / 105`
- forbidden prompt-field scan：`0`
- schema validation failure count：`0`
- Batch terminal status：stage1/stage2 均 completed
- output path audit：no writes outside `research_bcpcs_2026-04-18/`
- cost ledger validation：OK

Batch terminal counts：

| run | stage1 completed/failed/total | stage2 completed/failed/total |
| --- | --- | --- |
| `gpt-5-nano` methodfix | `127/0/127` | `104/0/104` |
| `gpt-5.4-nano` methodfix | `127/0/127` | `86/0/86` |

## 10. Bottom Line

本輪修正了方法層面的兩個問題：

1. 不再把 `unknown` / `route` / runtime failure 混成普通 semantic exclude。
2. 可以分開呈現 auto-decidable F1、coverage、conservative F1、Stage 1 gate recall 與 runtime failure taxonomy。

但這沒有讓 `gpt-5.4-nano` 在這個 failure slice 上變好。相反地：

- `gpt-5.4-nano high` 的 JSON output 穩定了。
- 但它的 recall 和 final F1 比 `xhigh` 更差，也明顯低於 `gpt-5-nano`。
- `gpt-5-nano` 仍是目前兩個必跑模型中較好的 failure-slice diagnostic 對照。

因此，目前不能宣稱 BCPCS-style ledger workflow 已改善這批錯例。更保守的結論是：

- evaluation/reporting 方法已修正，現在能區分 runtime stability 與 decision quality。
- `gpt-5.4-nano` 的主要問題已從「JSON-empty / parser failure」定位到「Stage 1/Stage 2 conservative recall loss」。
- 下一步如果要改善，不應調 formal criteria，也不應用 gold/forensic rationale 調 prompt；應先在 synthetic/minimal fixtures 或獨立 dev slice 上研究 gate policy、Stage 1 handoff、以及 retrieval/semantic_non_fit 的 decision boundary。
