# 實驗 framing

## 這次實驗是什麼

這次實驗明確定義為：

- 單審查者
- 官方 Batch API
- 兩階段直審
- experiment-only

也就是：

- 每個 candidate 只走一條 single reviewer 決策路徑
- Stage 1 只看 title/abstract + `criteria_stage1`
- Stage 2 才看 fulltext + `criteria_stage2`
- 不保留 `two juniors + SeniorLead`
- 不走 QA extraction / synthesis / evaluator 子相位

## 這次實驗不是什麼

- 不是 production 變更
- 不是 shared provider 改造
- 不是 preserved-workflow 重放
- 不是 historical one-stage fulltext direct-review bundle 的就地覆寫

## 方法邊界

- cutoff-first
- Stage 1 `exclude` 直接收斂
- Stage 1 `include` / `maybe` 才進 Stage 2
- Stage 2 是 combined final verdict 決定層
- historical `single_reviewer_official_batch_*_all4` 保留為 one-stage direct-review 對照，不再當 current baseline
