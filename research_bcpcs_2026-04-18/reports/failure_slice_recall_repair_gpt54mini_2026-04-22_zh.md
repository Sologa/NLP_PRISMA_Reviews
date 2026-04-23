# BCPCS Recall Repair V3: gpt-5.4-mini Full127

這是 failure-slice diagnostic，不是 full benchmark，也不是 production workflow replacement。

## Run

- run_id: `bcpcs_recall_v3_full127_gpt-54-mini_recall_boundary_maybe_v1_2026-04-22_v1`
- model: `gpt-5.4-mini`
- reasoning_effort: `low`
- scope: `full127`

## Full127

- auto F1: `0.9461`
- precision / recall: `0.8976` / `1.0000`
- TP / FP / TN / FN: `114/13/0/0`
- coverage: `100.00%`
- runtime failures: `0`
- decisions: `{"include": 19, "maybe": 108}`

## Slice Breakdown

- primary22 auto F1: `0.9767` (`21/1/0/0`)
- secondary105 auto F1: `0.9394` (`93/12/0/0`)

## Recovery

- prior FN recovered: `114/114`
- prior FP recovered: `0/13`
- still wrong: `13`
- paired net recovered change vs locked baseline: `54`

## Validation

- forbidden prompt hits: `0`
- direct output path audit ok: `true`
- source inventory counts ok: `true`
- schema failure count: `0`
- cost ledger ok: `true`

## Cost

- total cost: `$0.624703`
- input tokens: `627786`
- output tokens: `34192`

## Interpretation

- 這輪在 current V3 recall-repair architecture 上達到 >0.8，而且 runtime/schema 全乾淨。
- 但它本質上仍是 recall-biased maybe policy：127 筆裡沒有任何 `exclude`，因此 `TN=0`，不能把這個結果直接外推成正常 corpus 表現。
- 這比較像 failure-slice 上限測試，而不是 production-ready decision boundary。
