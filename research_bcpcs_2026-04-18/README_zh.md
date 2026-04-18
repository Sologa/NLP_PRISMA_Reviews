# Boundary-Calibrated Proof-Carrying Screening 中文總覽

這個資料夾是 BCPCS 研究計畫的 isolated workspace。所有新文檔、schema、prototype code、run outputs、reports 都在這裡，不污染既有 production pipeline。

## 目前有什麼

不是只有文檔。目前已經有：

- 中文導讀：`GUIDE_zh.md`
- 中文實作導讀：`IMPLEMENTATION_zh.md`
- 中文流程圖：`FLOWCHARTS_zh.md`
- 中文術語表：`GLOSSARY_zh.md`
- 英文研究文檔：`README.md`, `literature_review.md`, `method_spec.md`, `novelty_claims.md`, `reviewer_critique.md`
- Protocols：`protocol/`
- Schemas：`schemas/`
- Prototype scripts：`src/`
- Run outputs：`runs/`
- Reports：`reports/`
- 概念圖：`figures/bcpcs_conceptual_framework.svg`

## 目前實作到哪裡

已完成：

- Schema 定義。
- Schema validation。
- Current criteria / metadata dry-run loader。
- Stub eligibility graph compiler。
- Evidence ledger JSONL sample generation。
- Current baseline metric recheck。
- Structural smoke experiment。

尚未完成：

- 真正的 claim compiler。
- 真正的 support/refute retriever。
- 真正的 verifier。
- Boundary atlas builder。
- Full diagnostic benchmark。
- Ablation experiments。
- External public benchmark。

## 目前最重要的結論

1. 目前 repo 已經有 stage-specific criteria 和 topic definitions。
2. 問題不是「沒有 definition」。
3. 問題是沒有穩定的 criterion-level evidence object。
4. 只有 title/abstract + criteria + definitions 不足以穩定達到 near-perfect F1。
5. 可投 conference 的 novelty 應該是 proof-carrying screening decision calculus，而不是更長的 prompt。

## 建議閱讀順序

快速理解：

1. `GUIDE_zh.md`
2. `FLOWCHARTS_zh.md`
3. `GLOSSARY_zh.md`
4. `IMPLEMENTATION_zh.md`
5. `reports/results.md`

準備做實驗：

1. `protocol/leakage_control.md`
2. `protocol/evaluation_protocol.md`
3. `schemas/*.schema.json`
4. `configs/experiment_matrix.yaml`
5. `src/*.py`

準備寫 paper：

1. `literature_review.md`
2. `reviewer_critique.md`
3. `method_spec.md`
4. `novelty_claims.md`
5. `reports/baseline_recheck.md`

## 不能做的事

- 不宣稱 universal 100% F1。
- 不修改 production criteria。
- 不修改 runtime prompts。
- 不修改 results manifest。
- 不把 operational hardening 寫進 formal criteria。
- 不用 held-out errors 建 boundary atlas 後再報 improvement。
- 不把 routed/human-assisted F1 說成 fully automated F1。
