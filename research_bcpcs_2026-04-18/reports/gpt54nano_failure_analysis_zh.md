# GPT-5.4-nano Failure Analysis

這份報告針對 `bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1` 做失敗診斷。它是 failure-slice diagnostic，不是 full benchmark，也不是 production workflow replacement。

## 1. Run status

- run_id：`bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1`
- 模型：`gpt-5.4-nano`
- reasoning effort：requested `xhigh`，effective `xhigh`
- workflow：single-reviewer / two-stage / Batch async
- 成本：`$2.6535005`（dedup 後 audited total）
- 重要狀態：Stage 2 初次批次有 14 筆失敗；經一次 identical retry 後救回 8 筆，仍殘留 6 筆 unresolved failures
- 依 charter，這表示這次 run 不能視為 clean terminal success；下列結果應解讀為「merged provisional diagnostic under unresolved retry failures」

主要 artifacts：

- `runs/bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1/evaluation_summary.json`
- `runs/bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1/validation_summary.json`
- `runs/bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1/cost/cost_audit.json`
- `runs/bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1/comparison_vs_gpt5nano.json`
- `runs/bcpcs_failure_slice_gpt54nano_xhigh_2stage_async_2026-04-19_full127_v1/comparison_vs_gpt54mini.json`

## 2. Merged result summary

### Primary 22

- precision `0.9333`
- recall `0.6667`
- F1 `0.7778`
- TP / FP / TN / FN = `14 / 1 / 0 / 7`
- unknown mapped negative = `1`

### Secondary 105

- precision `0.8000`
- recall `0.3871`
- F1 `0.5217`
- TP / FP / TN / FN = `36 / 9 / 3 / 57`
- unknown mapped negative = `7`

### All 127

- precision `0.8333`
- recall `0.4386`
- F1 `0.5747`
- TP / FP / TN / FN = `50 / 10 / 3 / 64`
- prior FP recovered = `0`
- prior FN recovered = `50`
- still wrong = `69`
- newly unknown / routed = `8`

## 3. Relative position vs prior runs

### vs `gpt-5-nano`

- `gpt-5-nano` all127 F1 = `0.6378`
- `gpt-5.4-nano` all127 F1 = `0.5747`
- 差異：`gpt-5.4-nano` 在 primary22 反而更好（`0.7778` vs `0.6667`），但 secondary105 明顯更差（`0.5217` vs `0.6316`），因此 aggregate 仍輸
- row transition summary：
  - `improved_to_recovered` = `11`
  - `regressed_from_recovered` = `21`
  - `deferred_unknown` = `5`
- 主要 regression 集中在 `2601.19926`，其次是 `2307.05527`

### vs `gpt-5.4-mini xhigh`

- `gpt-5.4-mini xhigh` all127 F1 = `0.4699`
- `gpt-5.4-nano` all127 F1 = `0.5747`
- 也就是說，`gpt-5.4-nano` 明顯優於 `gpt-5.4-mini xhigh`，但仍不如 `gpt-5-nano`
- row transition summary：
  - `improved_to_recovered` = `23`
  - `regressed_from_recovered` = `12`
  - `deferred_unknown` = `6`

## 4. Root cause 1: Stage 1 gate recall regression

和 `gpt-5-nano` 相比，`gpt-5.4-nano` 的 Stage 1 gate 問題不是「更保守但更準」，而是「更早丟掉應該進 Stage 2 的正例」。

- `gpt-5-nano`：gold positive 放行 `86/114`；gold negative 放行 `12/13`
- `gpt-5.4-nano`：gold positive 放行 `74/114`；gold negative 放行 `13/13`

也就是說：

- 少放行 `12` 個 gold positive
- 沒有多攔下任何 gold negative
- 還多放行了 `1` 個 gold negative

最關鍵的 transition：

- `route_to_stage2 -> exclude`：`20` 個，全部都是 gold positive
- `include -> exclude`：`2` 個，全部都是 gold positive

這個 regression 幾乎全部發生在 secondary tension inventory，而不是 primary22：

- primary 正例放行：兩者都為 `17/21`
- secondary 正例放行：`69/93 -> 57/93`

每篇 paper 中，`2601.19926` 是最主要的 recall 損失來源：

- `gpt-5-nano` 正例放行 `60/72`
- `gpt-5.4-nano` 正例放行 `49/72`

具體上，它更傾向把 abstract 中沒有明講 syntax / structure 的 LM analysis、benchmark、probing、psycholinguistics 類工作提早排除。

## 5. Root cause 2: Stage 2 length exhaustion persisted after retry

初次 Stage 2 有 14 筆 `JSONDecodeError`。深入看原始 Batch output，不是 schema mismatch，而是 assistant 最後完全沒有輸出 JSON：

- `completion_tokens = 32768`
- `reasoning_tokens = 32768`
- `output_len = 0`

一次 identical retry 之後：

- 14 筆中救回 8 筆
- 仍有 6 筆重現完全相同的 failure signature

殘留 6 筆如下：

- `2307.05527 / louie_expressive_2021`（primary, prior FN）
- `2601.19926 / alt_probing_2020`（secondary, prior FN）
- `2601.19926 / chang_when_2024`（secondary, prior FN）
- `2601.19926 / mueller_cross-linguistic_2020`（secondary, prior FN）
- `2601.19926 / song:etal:2022`（secondary, prior FP）
- `2601.19926 / xiang:etal:2021`（secondary, prior FP）

這說明兩件事：

1. 這不是單純 parser bug，因為模型根本沒有吐出任何 JSON。
2. 問題也不是完全 deterministic，因為 14 筆裡有 8 筆在 identical retry 後成功；但仍有一批 case 對 `gpt-5.4-nano xhigh + full-text + strict JSON output` 極度脆弱。

## 6. Unresolved failures are not the whole story

目前 all127 F1 是 `0.5747`。如果對 unresolved 6 筆做最樂觀假設：

- 4 個 prior FN 全部修成 TP
- 2 個 prior FP 全部修成 TN

那麼 optimistic upper bound 也只有：

- precision `0.8710`
- recall `0.4737`
- F1 `0.6136`

這仍然低於 `gpt-5-nano` 的 `0.6378`。所以即使把 unresolved Stage 2 failures 全部視為可補救，這次 run 的主要落後原因仍然是 Stage 1 gate regression，而不是只差這 6 筆。

## 7. Unknown / routed rows

merged evaluation 裡共有 `8` 個 unknown/routed：

- `6` 個來自 retry 後仍 unresolved 的 Stage 2 failures
- `2` 個是 `2307.05527` 的非 terminal `route_to_stage2`

這些 row 都被明確保留成 unknown/routed，而不是偷偷轉成 semantic exclude。這一點符合 charter 的 anti-leakage / anti-overfit 規則。

## 8. Evidence ledger and validation

- stage outputs = `208`
- outputs with ledger = `208`
- ledger rows = `629`
- span validated rate = `0.9650`
- span completeness rate = `1.0000`

validation summary：

- source inventory counts OK：`127 / 22 / 105`
- forbidden prompt hit count：`0`
- schema failure count：`0`
- output path audit OK：`true`
- cost ledger OK：`true`

## 9. Cost audit

原始 `cost_ledger.jsonl` 有一整批 `stage2_review` 被重覆入帳一次，因此早先的 top-level `cost_summary.json` 總額是錯的。經 dedup 稽核後：

- corrected total after main stage1+stage2 = `$2.394417675`
- 加上 retry1 = `$2.6535005`

OpenAI 官方價格頁目前列出的 `gpt-5.4-nano` standard text token 價格為 input `$0.20 / 1M`、output `$1.25 / 1M`，Batch 為 50% off。來源：

- <https://openai.com/api/pricing/>
- <https://developers.openai.com/api/docs/models/gpt-5.4-nano>

## 10. Bottom line

如果問題是「`gpt-5.4-nano` 在這個 BCPCS failure slice 上是否仍然表現差」，答案是：**是，仍然差，且原因已經足夠清楚**。

最主要的問題排序如下：

1. Stage 1 gate 對 secondary tension inventory 的 recall regression
2. Stage 2 在部分 full-text case 上持續發生 reasoning-token exhaustion，導致 strict JSON 完全產不出來
3. unresolved 6 筆會進一步拉低 final merged metrics，但不是唯一主因

因此，這次 run 最合理的解讀不是「`gpt-5.4-nano` 差一點就贏」，而是：

- 它比 `gpt-5.4-mini xhigh` 好
- 但在這個 failure-slice diagnostic 上仍不如 `gpt-5-nano`
- 而且失敗模式主要集中在 secondary tension inventory 的 Stage 1 gate 與 Stage 2 full-text reasoning budget
