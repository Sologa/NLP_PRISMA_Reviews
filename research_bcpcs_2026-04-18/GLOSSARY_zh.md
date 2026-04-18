# BCPCS 術語表

這份術語表用中文解釋 BCPCS 相關名詞。每個術語都包含「是什麼」、「為什麼重要」、「常見誤解」。

## BCPCS

英文：Boundary-Calibrated Proof-Carrying Screening

中文：邊界校準的證據承載式篩選

是什麼：

- 一個 systematic-review screening 方法框架。
- 它要求每個 verdict 都能回溯到 criteria claim 和 evidence ledger。

為什麼重要：

- 讓 screening 不只是 LLM 的自由文字判斷。
- 可以檢查某個 include / exclude 是基於哪條 criteria、哪段 evidence、哪個 missingness state。

常見誤解：

- 它不是保證所有任務 100% F1 的魔法 prompt。
- 它也不是 TRACE-SR artifact。

## Screening

中文：文獻篩選

是什麼：

- 在 systematic review 中判斷候選 paper 是否符合納入條件。

為什麼重要：

- Screening 錯誤會直接影響 systematic review 的 evidence base。

常見誤解：

- 高 accuracy 不等於好 screening；如果漏掉應納入文獻，recall 低會很嚴重。

## Systematic Review

中文：系統性文獻回顧

是什麼：

- 用明確 protocol、search strategy、eligibility criteria 和 selection workflow 來整理一個研究問題的文獻。

為什麼重要：

- 它要求可重現、可稽核，不適合黑箱判斷。

常見誤解：

- 不是一般 narrative review。

## PRISMA

英文：Preferred Reporting Items for Systematic Reviews and Meta-Analyses

中文：系統性文獻回顧與統合分析報告規範

是什麼：

- Systematic review 常用的報告規範。

為什麼重要：

- 它要求透明說明 study selection、reviewer process 和 automation tool 的使用方式。

常見誤解：

- PRISMA 不是篩選模型；它是 reporting guideline。

## Criteria

中文：資格條件 / 納入排除標準

是什麼：

- 原始 review paper 定義的 inclusion / exclusion rules。

為什麼重要：

- Screening verdict 必須 source-faithful，也就是忠於原始 criteria。

常見誤解：

- 不能為了提高 F1，把 operational hardening 寫回 formal criteria。

## Source-Faithful

中文：忠於來源

是什麼：

- Criteria、claim、decision 不應加入原始 review 沒支持的新硬規則。

為什麼重要：

- 避免把 benchmark-specific error repair 偽裝成正式 eligibility criteria。

常見誤解：

- Source-faithful 不代表什麼都不能澄清；可以做 observable projection，但不能新增不被來源支持的 hard exclusion。

## Stage-Specific Criteria

中文：分階段 criteria

是什麼：

- Stage 1 用 `criteria_stage1/<paper_id>.json`。
- Stage 2 用 `criteria_stage2/<paper_id>.json`。

為什麼重要：

- Stage 1 只能看 title/abstract observable evidence。
- Stage 2 才能確認 full-text-only conditions。

常見誤解：

- Stage 1 criteria 不是第三套 eligibility regime；它只是 Stage 2 criteria 的 title/abstract observable projection。

## Eligibility Claim

中文：資格 claim / 資格判斷原子命題

是什麼：

- 從 criteria 拆出的最小可檢查命題。
- 例：`paper is primary research`、`task targets process extraction`、`preference signal is used for learning`。

為什麼重要：

- Final verdict 可以拆解成多個可檢查的 claim，而不是一個模糊印象。

常見誤解：

- Claim 不是新增 criteria；它應該只是把既有 criteria 結構化。

## Typed Eligibility Graph

中文：型別化資格圖

是什麼：

- 把 eligibility claims 以及它們的決策關係整理成 graph。

為什麼重要：

- Final verdict 可由 graph/lattice 推導，降低 free-form reasoning 的不穩定。

常見誤解：

- 它不是 hidden guidance layer。
- 它不能偷偷加入 source criteria 沒有的排除條件。

## Evidence Ledger

中文：證據帳本

是什麼：

- 每個 candidate paper 對每個 claim 的 evidence record。
- 包含 support/refute/unknown、quote、location、source path、confidence、missingness reason。

為什麼重要：

- 讓 verdict 可稽核。
- 可以做 evidence-span validation，而不是只看 F1。

常見誤解：

- 有 quote 不代表 quote 真的支持 verdict；還要驗 quote 是否 relevant / sufficient。

## Support Evidence

中文：支持證據

是什麼：

- 支持某個 eligibility claim 的文字片段或 metadata。

為什麼重要：

- Inclusion claim 應該有明確支持，而不是靠整體感覺。

常見誤解：

- Topic keyword 出現不等於 support。必須支持該 claim 的語義。

## Refute Evidence

中文：反駁證據 / 排除證據

是什麼：

- 顯示某個 claim 不成立，或顯示符合 exclusion criterion 的證據。

為什麼重要：

- 很多 FP 不是因為缺 support，而是因為模型沒有主動找 disqualifying evidence。

常見誤解：

- Refute retrieval 不是把模型變嚴格；它是要求先檢查最強反例。

## Refutation-First Retrieval

中文：反駁優先檢索

是什麼：

- 對每個 inclusion claim 同時找支持證據和反駁證據。
- 在 include 前先找可能排除該 paper 的 evidence。

為什麼重要：

- 對 `2409.13738` 這種 FP-heavy paper 特別重要。

常見誤解：

- 不是只找 exclusion keywords；是找與 claim 直接衝突的 evidence。

## Missingness

中文：缺證據狀態

是什麼：

- 沒有找到足夠 evidence 時的狀態。

常見類型：

- `not_observed_stage1`
- `deferred_to_stage2`
- `semantic_non_fit`
- `retrieval_failure`
- `metadata_ambiguity`
- `source_gold_tension`
- `evidence_incomplete`

為什麼重要：

- Stage 1 看不到不代表不符合。
- Stage 2 找不到也不一定代表 semantic exclude。

常見誤解：

- 把 unknown 直接當 exclude 或 include 都是不安全的。

## Stage-Aware Missingness

中文：階段感知缺證據

是什麼：

- 根據 Stage 1 / Stage 2 的可觀測性來解讀 missing evidence。

為什麼重要：

- Stage 1 只能看 title/abstract，所以很多 full-text-only 條件應 defer。

常見誤解：

- Stage 1 沒看到 full-text validation，不等於 paper 沒有 validation。

## Boundary Atlas

中文：邊界圖譜 / 邊界案例庫

是什麼：

- 一組 leakage-controlled 的 positive archetypes、hard-negative archetypes、contrast pairs。

為什麼重要：

- 幫助模型理解 near-miss cases，例如「看起來像 process extraction，但其實只是 UML / dataset / survey」。

常見誤解：

- 不能從 held-out FP/FN 建 atlas，否則就是 test leakage。

## Archetype

中文：原型案例

是什麼：

- 代表某類 included 或 excluded case 的典型樣態。

為什麼重要：

- 可以幫助 boundary calibration。

常見誤解：

- Archetype 不是 few-shot answer key；它必須有 provenance 和 allowed-use restrictions。

## Contrast Pair

中文：對照案例

是什麼：

- 一組很相似但 eligibility 不同的案例。

為什麼重要：

- 用來校準邊界，而不是只學 topic similarity。

常見誤解：

- Contrast pair 不能取自 final held-out evaluation errors 後再拿來報 improvement。

## Leakage Control

中文：資料洩漏控制

是什麼：

- 規定哪些資料可以用於設計、哪些必須 hold out。

為什麼重要：

- 避免把 test errors 變成 prompt/atlas，再宣稱模型改善。

常見誤解：

- 只要沒有直接改 gold labels 就沒有 leakage。其實看過 held-out FP/FN 後調 atlas 也可能 leakage。

## Leave-One-Review-Out

中文：留一 review 外部測試

是什麼：

- 每次留一篇 systematic review 當 held-out evaluation，其餘用於 development。

為什麼重要：

- 比在同一 review 裡切 candidates 更能測 cross-review generalization。

常見誤解：

- Candidate-level split 不一定能防止 criteria-level overfitting。

## Selective Routing

中文：選擇性轉交

是什麼：

- 高信心且 evidence 完整的 case 自動決策。
- 低信心、缺 evidence、邊界衝突 case 送 SeniorLead 或 human。

為什麼重要：

- 真實 screening 更需要 bounded risk，而不是假裝所有 case 都能自動解。

常見誤解：

- 不能只報 routed 後的 final F1；必須分開報 auto-only F1 和 assisted F1。

## Abstention

中文：棄權 / 不自動判定

是什麼：

- 系統承認不確定，不輸出自動 include/exclude。

為什麼重要：

- 對 medical / systematic-review screening 來說，不確定時 routing 通常比硬判安全。

常見誤解：

- Abstention 不是 failure；它是 risk-control mechanism。

## Auto-Only F1

中文：純自動決策 F1

是什麼：

- 只看系統自動判定的 case 的 F1。

為什麼重要：

- 評估模型本身能自動處理多少。

常見誤解：

- 如果 coverage 很低，auto-only F1 很高也不代表整體好。

## Selective Final F1

中文：選擇性流程最終 F1

是什麼：

- 自動決策加 routed adjudication 後的 final F1。

為什麼重要：

- 反映整個 workflow 的結果。

常見誤解：

- 它不能被說成 fully automated F1。

## SeniorLead

中文：資深裁決 reviewer

是什麼：

- 現有 production workflow 中處理 junior disagreement / uncertain cases 的角色。

為什麼重要：

- BCPCS 不移除 SeniorLead，而是讓 SeniorLead 接收更結構化的 evidence handoff。

常見誤解：

- SeniorLead 不是補丁；它是 selective routing 的正式 adjudication layer。

## Adjudication

中文：裁決 / 複核決策

是什麼：

- 對衝突、不確定或高風險 case 做最終判定。

為什麼重要：

- 可以處理模型無法可靠自動決策的 boundary cases。

常見誤解：

- Adjudication 不是讓另一個 LLM 自由投票；BCPCS 要求 evidence-grounded adjudication。

## Graph-Derived Verdict

中文：由圖推導的判決

是什麼：

- Final verdict 由 eligibility graph 和 evidence ledger 的狀態推導，而不是由 LLM 直接說 include/exclude。

為什麼重要：

- 更可審計、更容易 ablate、更容易定位錯誤。

常見誤解：

- Graph-derived 不代表完全 deterministic enough；上游 evidence extraction 仍可能錯，所以還要 evidence validation。

## Unsupported Verdict Rate

中文：無支持判決率

是什麼：

- Final verdict 缺乏足夠 evidence support 的比例。

為什麼重要：

- F1 高但 unsupported verdict 多，表示方法不可稽核。

常見誤解：

- 只要 verdict 對就夠。對 systematic review 來說，理由與證據也要可檢查。

## Hallucinated Citation Rate

中文：幻覺引用率

是什麼：

- Quote、citation、location 不存在或不對應原文的比例。

為什麼重要：

- Evidence-grounded 方法最怕假 citation。

常見誤解：

- LLM 產生看起來合理的 quote 不代表 quote 存在。

## Criteria-Gold Tension

中文：criteria 與 gold label 張力

是什麼：

- Gold label 和 source-faithful criteria 的合理解讀不一致或有爭議。

為什麼重要：

- 不能為了 fit gold label 而偷偷改 criteria。

常見誤解：

- Gold label 永遠是無噪音真值。實際上 systematic-review labels 也可能有 ambiguity。

## External Generalization

中文：外部泛化

是什麼：

- 在 repo 四篇以外的 public benchmark 上測試。

為什麼重要：

- 四篇 repo papers 只能當 internal diagnostic，不足以支撐 conference-level general claim。

常見誤解：

- Internal F1 很高就能投。若沒有 external data 或清楚 blocker，會被質疑 overfit。

## Ablation

中文：消融實驗

是什麼：

- 移除方法中的某個 component，看 performance 或 evidence quality 如何變化。

為什麼重要：

- 證明 novelty component 真的有用。

BCPCS 必跑 ablations：

- No typed eligibility graph
- No refute retrieval
- No boundary atlas
- No selective abstention
- No stage-aware missingness
- No SeniorLead evidence handoff
- Free-form LLM verdict instead of graph-derived verdict
