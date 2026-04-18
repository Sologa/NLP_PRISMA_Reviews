# BCPCS 中文導讀

這份導讀是給第一次打開 `research_bcpcs_2026-04-18/` 的閱讀路線。它不是新的方法定義；正式方法仍以 `method_spec.md`、protocol、schemas 為準。

## 一句話結論

目前 pipeline 已經不是「只有 title/abstract + criteria」。Stage-specific criteria 已有 topic definitions，runtime prompt 也會用 criteria。但這仍不夠穩，因為目前缺的是可驗證的 criterion-level evidence object。

BCPCS 的核心主張是：

> 把 systematic-review screening 從 free-form LLM verdict 轉成 proof-carrying decision problem：source-faithful criteria -> typed eligibility claims -> support/refute evidence ledger -> stage-aware missingness -> calibrated routing -> graph-derived verdict。

## 先讀哪幾份

如果你只有 10 分鐘：

1. `README_zh.md`
2. `FLOWCHARTS_zh.md`
3. `GLOSSARY_zh.md`
4. `IMPLEMENTATION_zh.md`
5. `reports/results.md`

如果你要判斷這能不能投 conference：

1. `literature_review.md`
2. `reviewer_critique.md`
3. `novelty_claims.md`
4. `protocol/evaluation_protocol.md`
5. `protocol/leakage_control.md`

如果你要開始做實驗：

1. `protocol/leakage_control.md`
2. `protocol/evaluation_protocol.md`
3. `schemas/eligibility_graph.schema.json`
4. `schemas/evidence_ledger.schema.json`
5. `configs/experiment_matrix.yaml`
6. `src/dry_run_loader.py`
7. `src/smoke_experiment.py`

如果你想知道「目前到底有沒有實作」：

1. `IMPLEMENTATION_zh.md`
2. `src/bcpcs_utils.py`
3. `src/dry_run_loader.py`
4. `src/baseline_recheck.py`
5. `src/smoke_experiment.py`

如果你想看流程圖：

1. `FLOWCHARTS_zh.md`
2. `figures/bcpcs_conceptual_framework.svg`

如果你想查術語：

1. `GLOSSARY_zh.md`

## 各文件在回答什麼問題

`README.md`

- 這個資料夾的 scope 是什麼。
- 哪些 production files 禁止碰。
- 為什麼這不是 TRACE-SR artifact。
- 目前 repo state 的前提是什麼。

`literature_review.md`

- 這個方向站在哪些 literature 上。
- LLM screening、QA screening、TAR、RAG/evidence grounding、calibration、adjudication 分別已經做到哪裡。
- 為什麼「再加 definition」不是最有 novelty 的路線。

`reviewer_critique.md`

- reviewer 會怎麼打。
- 哪些 claim 會被認為 overfit 或 benchmark gaming。
- 怎樣才有機會從 reject 變成 borderline/accept。

`method_spec.md`

- BCPCS 的正式方法定義。
- Criteria 如何被 compile 成 typed claims。
- Evidence ledger 需要哪些欄位。
- Final verdict 為什麼要由 graph/lattice 推導，而不是 LLM 自由判斷。

`novelty_claims.md`

- 可以 claim 什麼。
- 不能 claim 什麼。
- 如何避免把既有 QA / RAG / active learning / multi-agent work 包裝成假 novelty。

`protocol/leakage_control.md`

- 什麼資料可以在設計時看。
- 什麼資料不能用來建 boundary atlas。
- 什麼情況會讓結果失效。
- 這份是後續正式 benchmark 前最重要的防爆文件。

`protocol/evaluation_protocol.md`

- 內部四篇 paper 怎麼當 diagnostic benchmark。
- 哪些 baselines 和 ablations 必須跑。
- 要分開報 auto-only F1、selective final F1、senior/human-assisted F1。

`protocol/annotation_guidelines.md`

- 人工驗證 evidence span 時該怎麼判。
- 什麼叫 support、refute、unknown。
- 怎麼標 missingness 和 error taxonomy。

`schemas/*.schema.json`

- 方法的 machine-readable contract。
- 後續所有真實 run 都應該先符合這些 schema，再談 performance。

`configs/experiment_matrix.yaml`

- 實驗矩陣草案。
- 包含 internal papers、baselines、ablations、metrics、external benchmark candidates。

`reports/baseline_recheck.md`

- 重算 current authority metrics。
- 重要狀態：`2409.13738` current combined F1 是 `0.7500`，不是舊 handoff 裡的 `0.8235`。

`reports/schema_validation.md`

- JSON schemas 和目前 generated stub artifacts 的 validation 結果。

`reports/smoke_report.md`

- 小型 structural smoke run。
- 它只證明 graph/ledger interface 可以跑通，不代表 performance improvement。

`reports/results.md`

- 目前總結。
- 明確寫著 full BCPCS benchmark 還沒跑，不能宣稱 F1 improvement。

`reports/subagent_synthesis.md`

- 整合 literature review、repo forensic、brainstorming、reviewer critique subagents 的結論。

## 這個方法真正想解決的錯誤

`2409.13738`

- 主要是 FP-heavy。
- 模型會把 topic-adjacent 的 NLP / conceptual model / UML / user-story / survey / dataset 類 paper 泛化成 process extraction。
- BCPCS 對應策略：refutation-first retrieval + target-object claim + boundary atlas。

`2511.13936`

- 主要是 preference-learning vs evaluation-only 的 boundary。
- Audio-domain signal 不夠，還要證明 preference signal 被用在 learning/training/optimization，而不是只做 MOS 或 quality evaluation。
- BCPCS 對應策略：typed claim 區分 audio fit、preference signal、learning role、evaluation-only refute evidence。

`2307.05527`

- 目前已經很強。
- 不能用 global strictness 亂打，否則可能 destabilize。
- BCPCS 對應策略：選擇性 routing 和 abstention，避免用同一套 strict rule 打所有 paper。

`2601.19926`

- 需要分清 semantic non-fit、retrieval failure、metadata ambiguity。
- Over-strict senior behavior 會傷 recall。
- BCPCS 對應策略：stage-aware missingness + retrieval/failure-aware decision state。

## 最重要的非目標

- 不保證 universal 100% F1。
- 不把 operational hardening 寫回 formal criteria。
- 不新增 hidden third-layer guidance。
- 不把 human-assisted final F1 偽裝成 fully automated F1。
- 不用 held-out FP/FN 來建 boundary atlas 後再回報改善。
- 不把四個 repo papers 當成唯一 conference evidence。

## 下一步應該怎麼做

正確順序是：

1. Freeze `protocol/leakage_control.md`。
2. 選定 leave-one-review-out 或 frozen dev/eval split。
3. 建立真實 claim compiler，不改 formal criteria。
4. 實作 support/refute retrieval 和 evidence verifier。
5. 跑 internal diagnostic。
6. 跑 ablations。
7. 人工驗 evidence spans。
8. 找外部 public benchmark，或明確記錄不可行 blocker。
9. 才開始寫 conference paper 的 results section。

目前 `reports/results.md` 的狀態是 scaffold validation complete，不是 method validated。
