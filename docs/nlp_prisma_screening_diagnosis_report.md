---
title: "NLP_PRISMA_Reviews Screening Pipeline 再分析報告"
subtitle: "以 report JSON、criteria、prompt 與 runtime 設計交叉核實的研究判斷與下一步方案"
date: "2026-03-12"
lang: zh-TW
fontsize: 11pt
geometry: margin=0.8in
header-includes:
  - |
    \usepackage{xeCJK}
    \setCJKmainfont{Noto Sans CJK TC}
    \usepackage{longtable,booktabs,array}
    \usepackage[table]{xcolor}
    \usepackage{caption}
    \captionsetup[table]{skip=6pt}
    \renewcommand{\arraystretch}{1.15}
    \setlength{\parskip}{0.45em}
    \setlength{\emergencystretch}{3em}
    \definecolor{TableStripe}{HTML}{F7F9FC}
---

# 1. 執行摘要

這次我重新以可打開的 `screening/results/<paper>_full/...report.json` 為主，並交叉比對 `criteria_jsons`、prompt 模板、runtime reviewer prompt、分析文件與工作區設定。結論比上一輪更明確。

第一，現在最主要的瓶頸仍然是 Stage 1，但不是單一成因。它由兩層問題疊在一起：其一是 **review-specific criteria 在 title/abstract 階段的可觀測性不一致**；其二是 **全域版 SeniorLead prompt 無法同時適配不同 review**。前者優先級更高，尤其集中在 `2409.13738` 與 `2511.13936`；後者在 `2601.19926` 上表現得最明顯。

第二，Stage 2 並不是整體第一瓶頸，但也不能簡單說它完全沒問題。`2409` 與 `2511` 的 raw JSON 顯示，Stage 2 確實能清掉不少 Stage 1 帶進來的容易型 false positives；可是它對較難的 topic-adjacent 或邊界型 false positives 清除力不足。`2601` 則顯示 Stage 2 / full-text retrieval state 仍會干擾 final combined 指標，但這不是造成 tuned SeniorLead 大崩盤的主因。

第三，這四篇 paper 的最佳 combined 版本並不一致：`2307` 與 `2601` 的最佳 combined 版本是 `senior_no_marker`；`2409` 與 `2511` 的最佳 combined 版本則是 `prompt_only_v1`。這個結果本身就足以說明，**不存在一個簡單的全域 SeniorLead prompt 可以同時把四篇都推到最好**。

第四，從 raw JSON 反推，使用者先前確立的幾個流程原則是對的，尤其是「拿掉 marker heuristic」這件事。`senior_no_marker` 對四篇 paper 的 combined 結果都優於或不劣於 `senior_adjudication_v1`，表示那條路線確實應該停止再追。

第五，如果只做一件最值得做的事，我不建議再直接跑一輪新的 end-to-end 大實驗。我最建議的是先做 **frozen-input SeniorLead replay**：固定 junior 輸出，只重放 SeniorLead 決策，先把 rerun noise 從主要問題中拆掉。接著只做 **`2511` criteria operationalization v2**。這兩個實驗的資訊增益最高，而且混淆變因最少。

# 2. 本次核實範圍與資料可靠度說明

## 2.1 我實際核過的來源

本次分析實際打開並交叉核對了以下類型的檔案：

1. `docs/NLP_PRISMA_false_negative_report.txt`
2. `docs/reviewer_error_analysis.md`
3. `docs/detailed_reviewer_fn_analysis.md`
4. `docs/taxonomy_root_cause_qa.md`
5. `docs/prompt_only_runtime_realignment_report.md`
6. `docs/stage1_recall_redesign_report.md`
7. `docs/stage1_senior_adjudication_redesign_report.md`
8. `docs/stage1_senior_no_marker_report.md`
9. `docs/stage1_senior_prompt_tuning_report.md`
10. `criteria_jsons/2307.05527.json`
11. `criteria_jsons/2409.13738.json`
12. `criteria_jsons/2511.13936.json`
13. `criteria_jsons/2601.19926.json`
14. `sr_screening_prompts_3stage/sr_specific/03_stage1_2_criteria_review.md`
15. `sr_screening_prompts/sr_specific/05_stage2_criteria_review.md`
16. runtime reviewer prompt 與 workflow 相關程式片段
17. `screening/results/<paper>_full/` 底下可直接打開的多個 raw report JSON
18. `screening/workspaces/<paper>_full/.../config.json` 用來確認各 run 不是同一個時間點的乾淨 A/B

## 2.2 本次能直接打開的 raw report JSON

本次成功直接打開並讀取的 raw JSON 包含下列版本。

表 1. 本次直接核實的 raw JSON

| Paper | Stage 1 | Combined |
| --- | --- | --- |
| 2307.05527 | `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` | `prompt_only_v1`, `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` |
| 2409.13738 | `prompt_only_v1`, `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` | `prompt_only_v1`, `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` |
| 2511.13936 | `prompt_only_v1`, `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` | `prompt_only_v1`, `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` |
| 2601.19926 | `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` | `prompt_only_v1`, `senior_adjudication_v1`, `senior_no_marker`, `senior_prompt_tuned` |

說明：少數預期路徑在目前 snapshot 中無法打開，例如部分 `prompt_only_v1` Stage 1 JSON 與至少一部分 `recall_redesign` JSON。因此，對這些缺檔位置，我只把同輪報告中的彙總表當成輔助證據，並明確標註，不把它們假裝成已直接驗證的 raw JSON。

## 2.3 為什麼這次結論比上一輪更強

上一輪主要是根據 docs、criteria、prompt 與可見程式行為做診斷；這一輪則額外讀到了多個 paper 的 raw report JSON，因此很多先前只是方向性判斷的觀察，現在可以直接用 Stage 1 / Combined 的 TP、FP、FN 變化量來驗證。例如：`2409` 的 tuned SeniorLead 確實把 Stage 1 FP 從 24 降到 13，但 full-text 後仍輸給 `prompt_only_v1`；`2601` 的 tuned SeniorLead 在 Stage 1 就已經把 FN 從 5 拉到 61；`2511` 的 tuned SeniorLead 幾乎只是用 recall 換掉部分 Stage 1 FP，combined 並沒有超過 `prompt_only_v1`。

# 3. 先看最重要的橫向結論

## 3.1 四篇 paper 的最佳 combined 版本不一致

表格中的版本縮寫如下：PO = `prompt_only_v1`，SA = `senior_adjudication_v1`，SN = `senior_no_marker`，ST = `senior_prompt_tuned`。為避免 PDF 表格欄寬擁擠，後續主表與附錄表一律使用這四個縮寫。

表 2. 各 paper 的最佳 combined 版本

| Paper | 最佳版本 | Precision | Recall | F1 | 判讀 |
| --- | --- | ---: | ---: | ---: | --- |
| 2307.05527 | SN | 0.9816 | 0.9357 | 0.9581 | 適度 senior 有幫助；過嚴會掉 recall |
| 2409.13738 | PO | 0.7000 | 1.0000 | 0.8235 | precision 問題仍在，但 global senior 不是解方 |
| 2511.13936 | PO | 0.8438 | 0.9000 | 0.8710 | 主要是 criteria boundary，不是純 senior calibration |
| 2601.19926 | SN | 0.9676 | 0.9791 | 0.9733 | 允許弱訊號保留的 senior 有利；過嚴會大崩 |

表 2 的意義很重要。若存在一個真正有效的全域 SeniorLead prompt，理想上至少應該在四篇 paper 中大多數都贏；但現在事實是 2307/2601 與 2409/2511 的最佳版本分裂成兩組，這直接支持「單一全域 SeniorLead prompt 不可移植」的判斷。

## 3.2 marker heuristic 已被 raw JSON 否定

表 3. `senior_adjudication_v1` 與 `senior_no_marker` 的 combined 對照

| Paper | Adjudication (FP/FN/F1) | No marker (FP/FN/F1) | 結論 |
| --- | --- | --- | --- |
| 2307.05527 | SA: 4 / 15 / 0.9426 | SN: 3 / 11 / 0.9581 | no-marker 更好 |
| 2409.13738 | SA: 22 / 0 / 0.6563 | SN: 19 / 0 / 0.6885 | no-marker 更好 |
| 2511.13936 | SA: 20 / 2 / 0.7180 | SN: 11 / 3 / 0.7941 | no-marker 更好 |
| 2601.19926 | SA: 11 / 10 / 0.9687 | SN: 11 / 7 / 0.9733 | no-marker 更好 |

這個比較非常乾脆。四篇 paper 沒有一篇是 `senior_adjudication_v1` 優於 `senior_no_marker`。因此，「根據 junior reasoning 關鍵字決定是否送 senior」這條路線不只是不優雅，而是實證上已經沒有必要再保留。

## 3.3 Stage 2 不是整體第一瓶頸，但有局部不足

表 4. 以 raw JSON 觀察 Stage 1 到 Combined 的主要變化

| Paper / 版本 | Stage 1 FP | Combined FP | Stage 1 FN | Combined FN | 主要訊號 |
| --- | ---: | ---: | ---: | ---: | --- |
| 2409 / prompt_only | 24 | 9 | 0 | 0 | Stage 2 可清除大量容易型 FP |
| 2409 / senior_tuned | 13 | 12 | 0 | 0 | Stage 2 幾乎清不掉剩餘 hard FP |
| 2511 / prompt_only | 16 | 5 | 0 | 3 | Stage 2 可清很多 FP，但會犧牲部分 TP |
| 2511 / senior_tuned | 6 | 5 | 4 | 4 | Stage 2 已無法補回 Stage 1 recall 損失 |
| 2601 / senior_tuned | 7 | 7 | 61 | 63 | 崩盤已在 Stage 1 發生，非 Stage 2 主因 |
| 2307 / senior_tuned | 4 | 3 | 13 | 18 | 過嚴 senior 先傷 recall，Stage 2 再放大損失 |

表 4 告訴我們，Stage 2 的角色是「局部清理器」，不是主要 recall engine。對 `2409` 與 `2511`，它能清掉一批容易型 false positives；但對剩餘較難的邊界錯誤，清理能力不足。對 `2601`，tuned 版本的大崩盤在進 full text 前就已經發生，因此不能把鍋甩給 Stage 2。

# 4. 分 paper 詳細診斷

# 4.1 `2307.05527`

表 5. `2307.05527` 各版本摘要

| 版本 | Stage 1 FP/FN | Combined FP/FN | Combined P/R/F1 |
| --- | --- | --- | --- |
| PO | 8 / 6 | 5 / 14 | 0.9691 / 0.9181 / 0.9429 |
| SA | 8 / 7 | 4 / 15 | 0.9750 / 0.9123 / 0.9426 |
| SN | 7 / 6 | 3 / 11 | 0.9816 / 0.9357 / 0.9581 |
| ST | 4 / 13 | 3 / 18 | 0.9808 / 0.8947 / 0.9358 |

這篇的訊號非常穩定：過嚴的 SeniorLead 只帶來極小的 precision 收益，卻造成顯著 recall 損失。以 `senior_no_marker` 對 `senior_prompt_tuned` 為例，combined precision 幾乎相同，但 recall 從 0.9357 降到 0.8947，F1 反而變差。這與先前「`topic_definition` 不應再被當硬 inclusion criterion」的修正方向一致：一旦把 senior wording 再收緊，等於把已經清乾淨的大問題重新以另一種形式帶回來。

因此，`2307` 的下一步不是再調 stricter SeniorLead，而是維持現在的寬鬆保留原則，並只在 full-text 或 retrieval handling 上做非常局部的查漏。若未來要動 `2307`，我只建議做 error bucket audit，不建議再改 global policy。

# 4.2 `2409.13738`

表 6. `2409.13738` 各版本摘要

| 版本 | Stage 1 FP/FN | Combined FP/FN | Combined P/R/F1 |
| --- | --- | --- | --- |
| PO | 24 / 0 | 9 / 0 | 0.7000 / 1.0000 / 0.8235 |
| SA | 27 / 0 | 22 / 0 | 0.4884 / 1.0000 / 0.6563 |
| SN | 26 / 0 | 19 / 0 | 0.5250 / 1.0000 / 0.6885 |
| ST | 13 / 0 | 12 / 0 | 0.6364 / 1.0000 / 0.7778 |

這篇最值得注意的不是 recall，而是精準度的結構。所有版本 combined recall 都是 1.0，表示在目前 gold overlap 上，問題不是漏掉正例，而是保留了太多不該留的文章。

但更重要的細節在於：`senior_prompt_tuned` 雖然把 Stage 1 FP 從 24 壓到 13，Stage 1 precision 明顯進步，卻沒有在 combined 階段超過 `prompt_only_v1`。原因可以直接從 raw JSON 看出來：

1. `prompt_only_v1` 的 Stage 2 很會清理「容易型」FP，24 個 Stage 1 FP 中有 15 個在 combined 階段被清掉。
2. `senior_prompt_tuned` 留下來的 13 個 Stage 1 FP 中，Stage 2 只再清掉 1 個，最後還剩 12 個。

這代表什麼？代表 `senior_prompt_tuned` 並不是把真正的 hard false positives 判對，而更像是先把一批其實 Stage 2 也會自己清掉的 easy FP 提前殺掉；而真正困難、會一路存活到 full-text 的 topic-adjacent FP，反而仍然留著。因此它在 combined 指標上還是輸給 `prompt_only_v1`。

所以，`2409` 的主要問題不是單純的 SeniorLead calibration。真正更像根因的是 **Stage 1 criteria projection 不夠可操作**。`2409` 的 criteria 同時要求「specifically NLP for process extraction」、「concrete method」、「empirical validation」，還混有 full-text availability 與 superficial method 等條件。這些條件裡，有些在 title/abstract 階段根本觀測不穩。當它們被同一套 senior 判準壓在 abstract review 階段時，就很容易留下 process-adjacent 的 hard FP。

對 `2409`，最該改的是：把 Stage 1 與 Stage 2 的 criterion boundary 拆乾淨。Stage 1 只判「是不是 NLP process extraction 核心語義上在題目中」，不要把 validation 充分性與 full-text availability 的判準硬塞在 Stage 1 exclusion；Stage 2 再去判 method concreteness 與 empirical validation 是否真的成立。

# 4.3 `2511.13936`

表 7. `2511.13936` 各版本摘要

| 版本 | Stage 1 FP/FN | Combined FP/FN | Combined P/R/F1 |
| --- | --- | --- | --- |
| PO | 16 / 0 | 5 / 3 | 0.8438 / 0.9000 / 0.8710 |
| SA | 23 / 0 | 20 / 2 | 0.5833 / 0.9333 / 0.7180 |
| SN | 22 / 1 | 11 / 3 | 0.7105 / 0.9000 / 0.7941 |
| ST | 6 / 4 | 5 / 4 | 0.8387 / 0.8667 / 0.8525 |

這篇最清楚地告訴我們：問題不是「SeniorLead prompt 再修一下就好」。

`senior_prompt_tuned` 的確能把 Stage 1 FP 從 16 降到 6，但代價是 FN 從 0 變成 4。到了 combined 階段，`prompt_only_v1` 與 `senior_prompt_tuned` 最後都只剩 5 個 FP，可是 tuned 的 FN 還是多 1，因此整體仍輸給 `prompt_only_v1`。換句話說，tuned senior 做的事情，幾乎只是「用 recall 去交換一部分其實 Stage 2 也有機會清掉的 FP」。

這篇真正的核心問題，是 criteria 的 operational boundary 本身太難靠 abstract 穩定觀察。`2511` 的 eligibility 牽涉到以下幾組容易混淆的邊界：

1. audio / speech / emotion 之間的關係。很多 paper 寫的是 speech emotion recognition、spoken interaction、relative labels、ordinal annotations，但不會明說自己是 audio preference learning。
2. preference / ranking / ordinal 之間的關係。pairwise comparison、relative label、rank supervision、ordinal target，有些其實就是 preference signal；有些只是 measurement format，並沒有進入 learning objective。
3. preference-for-learning 與 preference-only-for-evaluation 的界線。這一條如果沒有明確 operational examples，reviewer 很容易高波動。

因此，`2511` 最該改的是 criteria wording，不是 senior prompt。具體說，應該把現有語意規則改寫成 reviewer 可以直接執行的 decision table：哪些情況算 positive lexical evidence，哪些只算 weak evidence，哪些是明確 negative evidence。若不先把這一層釐清，不論 junior 還是 senior，都會繼續在 abstract 階段對同一類文章做不穩定判斷。

# 4.4 `2601.19926`

表 8. `2601.19926` 各版本摘要

| 版本 | Stage 1 FP/FN | Combined FP/FN | Combined P/R/F1 |
| --- | --- | --- | --- |
| PO | 14 / 7 | 0 / 29 | 1.0000 / 0.9134 / 0.9548 |
| SA | 11 / 2 | 11 / 10 | 0.9673 / 0.9701 / 0.9687 |
| SN | 9 / 5 | 11 / 7 | 0.9676 / 0.9791 / 0.9733 |
| ST | 7 / 61 | 7 / 63 | 0.9749 / 0.8119 / 0.8860 |

這篇對更嚴格 SeniorLead 的脆弱性在 raw JSON 上非常直接。`senior_prompt_tuned` 與 `senior_no_marker` 相比，Stage 1 FN 從 5 暴增到 61，combined FN 從 7 暴增到 63。也就是說，幾乎整個崩盤都已經在 Stage 1 發生，Stage 2 只是把這個損失延續下去而已。

這個現象最合理的解釋不是 criteria wording，而是 **metadata observability**。`2601` 的 criteria 本身相對簡潔，但資料集中有不少 abstract 非常稀疏，甚至接近 citation-like metadata。對這種資料，合理策略本來就應該是「弱訊號保留為 maybe，讓後段再確認」；如果 SeniorLead 被要求在沒有 traceable core signal 時 lean exclude，就會把一批原本應保留的 sparse-but-plausible 文章直接打掉。

還要注意一件事：`2601` 的 combined JSON 中仍可見 `missing_fulltext` 與 `review_state:retrieval_failed` 這類 verdict 訊號。這表示 final combined 指標仍然摻雜了 full-text retrieval state 的影響。因此，對 `2601` 的解讀要分兩層：

1. tuned SeniorLead 崩盤的主因在 Stage 1 strictness，不在 Stage 2。
2. 但 combined 指標仍會被 retrieval / manual-review state 進一步扭曲，所以後續報表應把 semantic exclude 與 retrieval-state outcome 分開呈現。

# 5. 對五個核心問題的直接回答

# 5.1 問題 1：現在的主要瓶頸怎麼排序？

我的排序如下。

第一名：**review-specific criteria wording / operationalization / observability 問題**。這是現在最核心的瓶頸，尤其對 `2409` 與 `2511`。

第二名：**全域 SeniorLead prompt 的不可移植性**。從四篇 paper 的最佳版本分裂，以及 `2601` tuned 崩盤，可以確定這是實際存在的問題。但它更像是第一名問題的放大器，而不是唯一根因。

第三名：**Stage 2 對 hard boundary case 的回收不足**。它不是整體第一瓶頸，但 `2409` 的 residual hard FP 與 `2511` 的部分 combined 損失都顯示 Stage 2 仍有局部不足。

第四名：**實驗方法 noise / confound**。這很重要，因為它決定我們能不能乾淨地相信某一輪微小差異；但它不是實際 screening 行為差的第一原因。

# 5.2 問題 2：`2409` 與 `2511` precision 掉的根本原因有何不同？

`2409` 的 precision 掉，主因是 **process-adjacent 但非核心 eligibility 的文章在 Stage 1 沒被穩定排除**。更精確地說，是 Stage 1 criteria projection 把一部分需要 full text 才穩定判斷的條件，過早壓到 abstract review，造成 reviewer 對「核心 process extraction」與「相關但不核心」的界線抓得不一致。

`2511` 的 precision 掉，主因則是 **criteria boundary 本身在 abstract 層面就很難操作化**。它不是單純 topic-adjacent，而是 preference signal、ranking、ordinal supervision、speech/emotion/audio-domain 是否算入 learning objective 的邊界不清，導致 reviewer 對同一類 paper 的 positive / negative interpretation 高度波動。

因此，`2409` 最該改的是 Stage 1 / Stage 2 criterion split；`2511` 最該改的是 criteria operational definition 本體。

# 5.3 問題 3：`2601` 為什麼對更嚴格 SeniorLead 這麼脆弱？

核心原因是 **metadata observability 問題下，Stage 1 本來就不該太嚴**。這不是單純評估指標假象，也不是主要由 Stage 2 造成。raw JSON 已經顯示 tuned 版本在 Stage 1 就把 FN 拉到 61。`include_or_maybe` 會放大這個現象，但不是憑空製造它。

所以對 `2601`，最合理的原則是：在 abstract 弱訊號且與 syntax / transformer LM 相關時，SeniorLead 應優先保留 maybe，而不是要求過高的 explicit signal。

# 5.4 問題 4：下一步最值得做的實驗是什麼？

若按資訊增益與混淆變因一起排序，我的排序如下。

第一名：**重新設計更嚴格的實驗方法，先做 frozen-input replay，降低 rerun noise**。

第二名：**只改 `2409` / `2511` criteria wording**，但我會先從 `2511` 開始，因為證據最強。

第三名：**只做 review-specific SeniorLead prompt**，但一定要在 frozen-input replay bench 上做，不要再用全流程 rerun 來比較。

第四名：**只改 Stage 2 fulltext reviewer prompt / policy**。這一步不是沒價值，但應放在前面三步之後。

第五名：**先做 code refactor / modularization**。這件事有工程價值，但不是現在最高資訊增益的研究步。

# 5.5 問題 5：如果只能做兩個實驗，會是哪兩個？

## 實驗 A：frozen-input SeniorLead replay

固定 `2409`、`2511`、`2601` 的 junior outputs 與送 senior 的 case 集合，只改 SeniorLead prompt，不重跑 juniors，不動 Stage 2。這個實驗能直接回答「全域 senior prompt 是否真的無法同時適配所有 review」；也能把 rerun noise 從主要判斷中拆掉。

成功時代表：review-specific senior 確實有必要，而且其效果不是 rerun noise 造成的。

失敗時代表：先前觀察到的 senior 效果有相當部分可能是 rerun drift；那就不應再花大力氣在 SeniorLead wording 上。

## 實驗 B：`2511` criteria operationalization v2

只改 `2511.13936.json` 的 wording 與 operational examples，不動 routing policy、不動 SeniorLead policy、不動 Stage 2。目標是把 pairwise / ranking / ordinal / relative label / speech emotion / audio-core modality 的邊界寫成 reviewer 可直接執行的 decision table。

成功時代表：`2511` 的主問題確實是 criteria 邊界，而不是 senior prompt。

失敗時代表：還需要進一步懷疑 gold 標註、資料觀測性，或 reviewer prompt 本身存在更深層的解讀偏差。

# 6. 具體解決方案

# 6.1 不是大重構，而是三個小而準的修正面

## 6.1.1 解法一：先建立 frozen-input adjudication bench

這不是工程美化，而是研究方法修正。具體要求如下：

1. 以一個固定 baseline run 匯出每筆 paper 的 junior scores、junior rationales、是否送 senior、當下 metadata。
2. 後續所有 SeniorLead prompt 版本都在這同一份 frozen input 上 replay。
3. 報表至少分成 two views：`senior-decided subset` 與 `overall after-stage1`。
4. 每次實驗只允許一個變因：SeniorLead prompt 或 criteria wording，不能兩者同時改。

做完這件事後，你才有能力乾淨地回答「究竟是 senior 在變，還是 juniors 又漂了」。

## 6.1.2 解法二：`2511` criteria 改成 decision-table 規格

建議把現有 `2511` eligibility 重寫成四個 reviewer 直接能執行的欄位。

第一欄，`audio-domain evidence`：speech, spoken dialogue, speech emotion, paralinguistic audio, acoustic preference 全列為可接受證據；若是 multimodal，需明寫 audio 為核心訊號或核心輸入之一。

第二欄，`preference-signal evidence`：pairwise comparison, relative label, rank supervision, preference optimization, reward preference from audio response 全列為正向訊號；單純 scalar rating 只有在明確被轉成 ranking / pairwise / preference objective 時才算。

第三欄，`learning-role`：若 preference signal 只用於 evaluation、benchmarking、human study，不算；若 preference signal 直接影響 training objective、label construction、reward learning、model selection，才算。

第四欄，`negative overrides`：純 SER classification、純 ordinal intensity prediction、純 rating prediction、純 evaluation-only preference，若沒有 preference-learning component，一律排除。

這樣做的目的不是把 criteria 放寬，而是把 reviewer 心中的隱性判斷外顯化，讓 junior 與 senior 不要再對同一種 abstract 做不同映射。

## 6.1.3 解法三：`2409` 做 Stage 1 / Stage 2 criterion split

建議不要直接重寫整份 criteria，而是先做一個「Stage 1 可觀測投影版」。

Stage 1 只回答三件事：

1. 題目是否明確在 process extraction / process discovery / event-log-to-process representation 的核心任務上。
2. 是否真的在用 NLP 或 text-processing 作為核心方法，而不是只把文本當背景資料。
3. 若 abstract 無法判斷 validation 充分性，預設保留為 maybe，而不是直接 exclude。

Stage 2 再回答剩下兩件事：

1. method 是否真的 concrete，而不是泛泛提到 NLP。
2. empirical validation 是否真的支撐 eligibility。

這樣做的好處是，把 `2409` 現在混在一起的「語義核心 fit」與「證據充分度」拆開。如此一來，SeniorLead 就不用在 abstract 階段同時背兩層責任。

# 6.2 對 Stage 2 的建議：不是先全面改，而是做 targeted audit

我不建議現在就大改 Stage 2 policy，因為 evidence 還不支持它是第一瓶頸。不過我會建議針對兩篇 paper 各做一個小 audit。

對 `2409`，抽樣檢查 combined 最終留下的 hard FP，確認它們是因為 full-text reviewer 沒有抓到 `specifically NLP for process extraction`，還是因為 criteria 本身就把它們算進去了。

對 `2601`，把 final verdict 中的 `missing_fulltext` 與 `review_state:retrieval_failed` 另做一欄，不與 semantic exclude 混在同一個 precision / recall 表格裡。這一步是為了讓 combined 指標更可解釋，而不是為了立刻改 policy。

# 7. 哪些結論可以信，哪些不能信

## 7.1 可以高度相信的

1. marker heuristic 應維持刪除，因為 raw JSON 顯示 `senior_no_marker` 全面優於 `senior_adjudication_v1`。
2. stricter global SeniorLead 不可移植，因為它對 `2409` 的 Stage 1 precision 有幫助，卻無法在 combined 階段超過 `prompt_only_v1`，並且會嚴重傷害 `2307` 與 `2601`。
3. `2511` 不是純 senior calibration 問題，因為 tuned 版本幾乎只是用 recall 換部分 FP，最後 combined 仍不如 `prompt_only_v1`。
4. `2601` 的 tuned 崩盤主要發生在 Stage 1，不是 Stage 2 製造的假象。

## 7.2 不能講太滿的

1. 目前不能把所有小幅差異都當成乾淨 A/B，因為工作區時間戳與 rerun 設計顯示各 run 並非同一批固定 junior 輸出。
2. 對 `recall_redesign_v1` 的判讀，在目前 snapshot 中部分仍只能依賴報告文字或彙總表，因為對應 raw JSON 並非全部都能直接打開。
3. Stage 2 的真實上限還沒有被隔離測量，因為目前 combined 指標同時夾帶了 Stage 1 admission 結果與部分 retrieval-state outcome。

# 8. 最後的研究判斷

若把現在所有證據壓成一句話，我的結論是：

**現在最該做的不是再找一個全域更聰明的 SeniorLead prompt，而是先承認不同 review 的 eligibility 在 abstract 階段並不等觀測，再用 frozen-input replay 與 review-specific criteria operationalization，把 senior 問題與 criteria 問題拆開。**

在這四篇 paper 中，`2511` 最值得先修 criteria，`2409` 最值得先拆 Stage 1 / Stage 2 criterion boundary，`2601` 最需要避免任何要求強顯式訊號的 strict senior，`2307` 則應保持既有修正成果，不要再被 global tightening 拖回去。

# 9. 建議你下一個對話串如何限定任務範圍

## 任務 A：只做 frozen SeniorLead replay 規格

交付物應包含：固定輸入格式、SeniorLead replay driver 規格、輸出報表欄位、三篇 paper 的比較矩陣。這個任務不改任何 policy，只建立研究基礎設施。

## 任務 B：只做 `2511` criteria v2 設計稿

交付物應包含：修訂後 criteria JSON 草案、decision table、正反例列表、reviewer lexical cue 清單。這個任務不改 runtime code，只交付可審查的 spec。

## 任務 C：只做 `2409` Stage 1 可觀測投影稿

交付物應包含：把現行 `2409` criteria 拆成 Stage 1 observable criteria 與 Stage 2 confirmatory criteria，並附 10 個邊界案例的標註規則。這個任務同樣不直接改 code。

# 附錄 A. 本次分析用到的關鍵數字

表 A1. Stage 1 關鍵數字總表

| Paper | 版本 | TP | FP | TN | FN | P | R | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2307 | PO* | 165 | 8 | 39 | 6 | 0.9538 | 0.9649 | 0.9593 |
| 2307 | SA | 164 | 8 | 39 | 7 | 0.9535 | 0.9591 | 0.9563 |
| 2307 | SN | 165 | 7 | 40 | 6 | 0.9593 | 0.9649 | 0.9621 |
| 2307 | ST | 158 | 4 | 43 | 13 | 0.9753 | 0.9240 | 0.9490 |
| 2409 | PO | 21 | 24 | 33 | 0 | 0.4667 | 1.0000 | 0.6364 |
| 2409 | SA | 21 | 27 | 30 | 0 | 0.4375 | 1.0000 | 0.6087 |
| 2409 | SN | 21 | 26 | 31 | 0 | 0.4468 | 1.0000 | 0.6176 |
| 2409 | ST | 21 | 13 | 44 | 0 | 0.6176 | 1.0000 | 0.7636 |
| 2511 | PO | 30 | 16 | 38 | 0 | 0.6522 | 1.0000 | 0.7895 |
| 2511 | SA | 30 | 23 | 31 | 0 | 0.5660 | 1.0000 | 0.7229 |
| 2511 | SN | 29 | 22 | 32 | 1 | 0.5686 | 0.9667 | 0.7160 |
| 2511 | ST | 26 | 6 | 48 | 4 | 0.8125 | 0.8667 | 0.8387 |
| 2601 | PO* | 328 | 14 | 9 | 7 | 0.9591 | 0.9791 | 0.9690 |
| 2601 | SA | 333 | 11 | 12 | 2 | 0.9680 | 0.9940 | 0.9809 |
| 2601 | SN | 330 | 9 | 14 | 5 | 0.9735 | 0.9851 | 0.9792 |
| 2601 | ST | 274 | 7 | 16 | 61 | 0.9751 | 0.8179 | 0.8896 |

說明：帶星號者來自 `stage1_senior_prompt_tuning_report.md` 的彙總表，因同名 raw JSON 在本次 snapshot 的預期路徑未成功打開；其餘數值來自 raw report JSON。

表 A2. Combined 關鍵數字總表

| Paper | 版本 | TP | FP | TN | FN | P | R | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2307 | PO | 157 | 5 | 42 | 14 | 0.9691 | 0.9181 | 0.9429 |
| 2307 | SA | 156 | 4 | 43 | 15 | 0.9750 | 0.9123 | 0.9426 |
| 2307 | SN | 160 | 3 | 44 | 11 | 0.9816 | 0.9357 | 0.9581 |
| 2307 | ST | 153 | 3 | 44 | 18 | 0.9808 | 0.8947 | 0.9358 |
| 2409 | PO | 21 | 9 | 48 | 0 | 0.7000 | 1.0000 | 0.8235 |
| 2409 | SA | 21 | 22 | 35 | 0 | 0.4884 | 1.0000 | 0.6563 |
| 2409 | SN | 21 | 19 | 38 | 0 | 0.5250 | 1.0000 | 0.6885 |
| 2409 | ST | 21 | 12 | 45 | 0 | 0.6364 | 1.0000 | 0.7778 |
| 2511 | PO | 27 | 5 | 49 | 3 | 0.8438 | 0.9000 | 0.8710 |
| 2511 | SA | 28 | 20 | 34 | 2 | 0.5833 | 0.9333 | 0.7180 |
| 2511 | SN | 27 | 11 | 43 | 3 | 0.7105 | 0.9000 | 0.7941 |
| 2511 | ST | 26 | 5 | 49 | 4 | 0.8387 | 0.8667 | 0.8525 |
| 2601 | PO | 306 | 0 | 23 | 29 | 1.0000 | 0.9134 | 0.9548 |
| 2601 | SA | 325 | 11 | 12 | 10 | 0.9673 | 0.9701 | 0.9687 |
| 2601 | SN | 328 | 11 | 12 | 7 | 0.9676 | 0.9791 | 0.9733 |
| 2601 | ST | 272 | 7 | 16 | 63 | 0.9749 | 0.8119 | 0.8860 |

這張表是整份報告最值得反覆看的主表。它直接顯示：`senior_no_marker` 不是 universally best；`senior_prompt_tuned` 也不是 universally better；而 `2409` 與 `2511` 的最佳 combined 版本仍是 `prompt_only_v1`。
