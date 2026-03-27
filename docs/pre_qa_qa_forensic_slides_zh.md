---
marp: true
paginate: true
theme: default
size: 16:9
style: |
  section {
    font-family: "Noto Sans CJK TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
    font-size: 26px;
    line-height: 1.35;
    padding: 36px 48px;
  }
  h1 { font-size: 1.45em; }
  h2 { font-size: 1.15em; }
  h3 { font-size: 1em; }
  table { font-size: 0.68em; }
  code, pre { font-size: 0.7em; }
  blockquote {
    font-size: 0.72em;
    border-left: 6px solid #c7c7c7;
    background: #f5f5f5;
    padding: 0.6em 0.9em;
  }
---

# QA 前實驗到 QA Forensic 的重點整理

副標：四篇 SR、criteria、流程圖、結果、confusion matrix、case dossiers  
日期：2026-03-19  
範圍：

- `docs/pre_qa_experiment_summary_zh-報告用.md`
- `docs/qa_forensic_error_analysis-報告用.md`
- QA results reports on `2026-03-18` to `2026-03-19`

---

## 這份投影片要回答什麼

| 問題 | 這份 deck 怎麼回答 |
| --- | --- |
| 四篇 SR 各自在看什麼？ | 先用中文白話講四篇 SR 主題、criteria 邊界與例子。 |
| QA 前系統怎麼演進？ | 用兩張概念流程圖把 pre-QA 主線講清楚。 |
| 為什麼最後會走到 QA？ | 用 `2409/2511` 的殘留問題與 confusion matrix 說明。 |
| QA-first 到底改了什麼？ | 用口語解釋 v0、v1 first-pass、second-pass、`2409` follow-up。 |
| QA 的效果怎麼看？ | 放 F1、confusion matrix、hygiene、誤差型態。 |
| 哪些個案最重要？ | 保留 `2409` 與 `2511` 全部 case dossiers。 |

---

## 四篇 SR 是在做什麼

| Paper | SR 正式 title | 白話主題 | 白話說明 | 直覺例子 |
| --- | --- | --- | --- | --- |
| `2307.05527` | *The Ethical Implications of Generative Audio Models* | 生成式音訊模型的倫理問題 | 看生成式音訊模型會帶來哪些道德、法律、社會風險。 | deepfake 聲音、聲音版權、模仿他人聲音的同意權。 |
| `2409.13738` | *NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods* | 用 NLP 從文字抽流程模型 | 看論文是否真的把自然語言流程描述轉成 process model。 | 把 SOP 或醫療流程文件轉成流程圖。 |
| `2511.13936` | *Preference-Based Learning in Audio Applications: A Systematic Analysis* | 音訊領域的偏好式學習 | 看研究是否真的用偏好訊號來訓練音訊模型。 | 讓人比兩段音訊哪個較好，再用這個偏好更新模型。 |
| `2601.19926` | *The Grammar of Transformers* | Transformer 的句法知識與可解釋性 | 看 Transformer LM 是否學到 syntax，以及怎麼證明。 | 分析 BERT/GPT 是否知道依存關係、句法樹、主詞動詞一致。 |

---

## Criteria 是什麼

| 名詞 | 白話說明 | 例子 |
| --- | --- | --- |
| `criteria` | 這篇 SR 用來決定「要收還是不收」的正式規則。 | 一篇 paper 雖然跟流程有關，但如果不是「從文字抽流程模型」，就不收進 `2409`。 |
| `Stage 1 criteria` | 只給標題與摘要用的版本。只保留摘要看得到的條件。 | 摘要只寫有 NLP 處理流程文字，但沒說有沒有真的抽出 process model，就先保留給下一階段。 |
| `Stage 2 criteria` | 給全文審查的完整版本。 | 全文再確認它是不是 original research、是不是 peer-reviewed、是不是 canonical target。 |
| `source-faithful` | 忠於原 SR paper 的本意，不偷加方便模型判斷的硬規則。 | 不能因為某類 paper 常常是假陽性，就把它硬寫成 formal exclusion。 |
| `operational hardening` | 為了拿分而加上的操作型硬規則。 | 看到某種方法名就直接排除，這種做法分數可能變高，但不一定忠於原 paper。 |

---

## 四篇 SR 的 criteria 邊界

| Paper | 會收什麼 | 不收什麼 | 白話邊界 |
| --- | --- | --- | --- |
| `2307` | 生成式音訊模型與其倫理、法律、社會風險 | 純 ASR、純文字生成、非音訊輸出 | 不是看模型準不準，是看這類技術的風險。 |
| `2409` | 從文字抽流程模型、決策模型的 original research | 只做 IE/分類/比對、但沒有真正抽出 model | 不是「碰到流程文字」就算，要真的抽 model。 |
| `2511` | 用偏好、排序、A/B、RLHF 等信號來訓練音訊模型 | 只有 evaluation 用偏好、沒有 learning component | 關鍵不是有沒有問人喜不喜歡，而是偏好有沒有拿來學習。 |
| `2601` | 研究 Transformer LM 的 syntax knowledge 與 interpretability | 非 Transformer、沒碰 syntax、純 survey | 不是所有 interpretability paper 都算，要明確碰 syntax。 |

---

## QA 前 production workflow

```text
候選論文
  |
  v
看 title + abstract
（Stage 1 初篩）
  |
  +--> 兩位 junior 都高分
  |      -> 直接 include
  |
  +--> 兩位 junior 都低分
  |      -> 直接 exclude
  |
  +--> 意見不一致
         -> 送 SeniorLead 仲裁
  |
  v
需要全文確認的論文
  |
  v
看 full text
（Stage 2 用完整 criteria）
  |
  v
最終 include / exclude
```

白話：

- QA 前系統不是先問一串固定問題，而是 reviewer 直接讀內容後做判斷。
- 真正正式採用的是 `criteria_stage1/` + `criteria_stage2/` + `SeniorLead`。

---

## QA 前實驗主線怎麼演進

```text
原始 baseline
  |
  v
prompt 對齊
  |
  v
recall-first redesign
  |
  v
SeniorLead 仲裁重整
  |
  v
拿掉 marker heuristic
  |
  v
驗證 strict senior 到底是不是真有效
（frozen replay）
  |
  v
把 2409 / 2511 問題拆到 criteria 線
  |
  v
正式遷移到 stage-split criteria
  |
  v
開始思考 QA-first
```

白話：

- 前半段主要在調 prompt、routing、senior。
- 後半段才發現：`2409/2511` 的核心問題不只在 senior，而是在 criteria 的可觀測性與 evidence interpretation。

---

## QA 前 current authority 與最佳表現

| Paper | QA 前 current authority | Stage 1 F1 | Combined F1 | 同線最佳歷史版本 | 最佳 Combined F1 |
| --- | --- | ---: | ---: | --- | ---: |
| `2307` | `senior_no_marker` | `0.9113` | `0.9057` | `senior_no_marker` | `0.9057` |
| `2409` | `stage_split_criteria_migration` | `0.7500` | `0.8235` | `prompt_only_v1` | `0.8235` |
| `2511` | `stage_split_criteria_migration` | `0.8788` | `0.9062` | `criteria_2511_opv2` | `0.9062` |
| `2601` | `senior_no_marker` | `0.9792` | `0.9731` | `senior_no_marker` | `0.9731` |

白話：

- `2307/2601` 已經很穩。
- `2409/2511` 雖然 current state 比早期乾淨，但還沒有過 `0.9`。
- `2511` 的歷史高分有一部分來自 operational hardening，所以沒有直接採用。

---

## QA 前重要結果：全域流程線

| 實驗版本 | `2307` Combined | `2409` Combined | `2511` Combined | `2601` Combined | 四篇平均 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `before` | 0.8000 | 0.7556 | 0.8235 | 0.8567 | 0.7991 |
| `prompt_only_v1` | 0.9429 | **0.8235** | 0.8710 | 0.9548 | **0.8980** |
| `recall_redesign` | 0.9521 | 0.6269 | 0.8406 | 0.9545 | 0.8435 |
| `senior_adjudication_v1` | 0.9426 | 0.6562 | 0.7179 | 0.9687 | 0.8214 |
| `senior_no_marker` | **0.9057** | 0.6885 | 0.7941 | **0.9731** | 0.8553 |
| `senior_prompt_tuned` | 0.9358 | 0.7778 | 0.8525 | 0.8860 | 0.8630 |

白話：

- `prompt_only_v1` 是早期非常強的跳升。
- `strict senior` 對 `2409/2511` 有幫助，但會傷到 `2601`。
- 所以系統後來不能只靠「把 senior 變更嚴」。

---

## QA 前 confusion matrix：穩的兩篇

表 A `2307` 最佳 setting = `senior_no_marker`

| 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | ---: | ---: | ---: | ---: | --- |
| Stage 1 | 165 | 7 | 40 | 6 | 已很平衡，只有少量 FP / FN。 |
| Combined | 160 | 3 | 44 | 11 | 全文後 FP 更少，但 FN 稍增。 |

表 B `2601` 最佳 setting = `senior_no_marker`

| 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | ---: | ---: | ---: | ---: | --- |
| Stage 1 | 330 | 9 | 14 | 5 | 高 TP、低 FP、低 FN。 |
| Combined | 328 | 11 | 12 | 7 | 全文後略變差，但整體仍很穩。 |

---

## 為什麼 `2409 / 2511` 還不到 `0.9`

| Paper | current state | Stage 1 confusion matrix | Combined confusion matrix | 主要問題 |
| --- | --- | --- | --- | --- |
| `2409` | `stage_split_criteria_migration` | `TP 21 / FP 14 / TN 45 / FN 0` | `TP 21 / FP 9 / TN 50 / FN 0` | 明顯是 FP-heavy。 |
| `2511` | `stage_split_criteria_migration` | `TP 29 / FP 7 / TN 50 / FN 1` | `TP 29 / FP 5 / TN 52 / FN 1` | cutoff 修正後，current state 已回到高位，只剩少量 residual edge cases。 |

白話：

- `2409` 的問題像是：很多 paper 看起來很像正例，但其實不是 canonical target。
- `2511` 的問題像是：摘要常有偏好或 ranking 訊號，但不容易立刻看出它到底是 learning 還是 evaluation。

---

## `stage_split_criteria_migration` 到底改了什麼

| 面向 | 以前 | 遷移後 | 白話說明 |
| --- | --- | --- | --- |
| criteria 結構 | 同一套條件常被硬套在兩個 stage | 正式拆成 `criteria_stage1/` 與 `criteria_stage2/` | 初篩與全文確認不再共用同一份規則。 |
| Stage 1 角色 | 常被迫判太細 | 只保留 title/abstract 可觀測條件 | 初篩只做它看得到的事。 |
| Stage 2 角色 | 和 Stage 1 混在一起 | 固定處理完整 canonical eligibility | 全文階段才做完整確認。 |
| 方法學定位 | 容易把拿分規則寫回 criteria | 強調 `source-faithful` | 不再把 performance hardening 偽裝成 paper 原規則。 |

---

## `2409` 與 `2511` 的 stage-split 差異

| Paper | Stage 1 在看什麼 | Stage 2 在看什麼 | 白話結論 |
| --- | --- | --- | --- |
| `2409` | 摘要裡是否真的有 text -> process/decision model 的可觀測訊號 | paper type、publication form、method、experiment、canonical target fit | 把很多摘要看不穩的條件往後移。 |
| `2511` | 摘要裡是否真的有 preference / ranking / RL training signal，且與 audio 有關 | 確認 preference signal 是不是進 learning，而不只是 evaluation | 把「有偏好字眼」和「真的用偏好學習」分開。 |

---

## 為什麼最後會走到 QA

| QA 前觀察 | 白話解讀 |
| --- | --- |
| `2409` current Combined F1 只有 `0.8235` | rules 拆乾淨了，但 residual FP 還很多。 |
| `2511` current Combined F1 已回到 `0.9062` | cutoff 修正後，current baseline 已不再是主要瓶頸。 |
| `strict senior` 不能全域套用 | `2601` 對過嚴 senior 很敏感。 |
| stage-split 已把 criteria 整理乾淨 | 下一步比較像是證據怎麼被抽出、怎麼被整理。 |

一句話：

> QA-first 的出發點是：不要再讓 reviewer 直接憑自由文本整體印象下 verdict，而是先把證據拆成固定問題，再根據答案做判斷。

---

## QA-first 概念流程圖

```text
候選論文
  |
  v
先看 title + abstract
  |
  v
先回答一組固定 QA 問題
（不是先直接下 verdict）
  |
  v
把 QA 答案整理成 evidence synthesis
  |
  v
criteria evaluator 根據 evidence 打分
  |
  v
Stage 1 senior 收尾
  |
  v
需要全文的 case 才進 Stage 2
  |
  v
全文再跑一次 QA + synthesis + evaluator + senior
  |
  v
最終 include / exclude
```

---

## QA 部分的設定，用口語講明白

| 版本 | 口語說明 | 有沒有改 production criteria / prompt |
| --- | --- | --- |
| current production | 還是 pre-QA 正式系統，沒有先做 QA。 | 否 |
| QA v0 `qa+synthesis` | 第一版 QA-first。先問問題，再做 synthesis，最後才決定。 | 只是實驗，不改 production |
| QA v1 first-pass | 想把整體 workflow 修得更完整，但 Stage 1 defer 太寬，很多 case 被送成 `maybe`。 | 不改 production |
| QA v1 second-pass | 修兩件事：漏掉 review topic 的 hygiene bug，以及 Stage 1 `maybe` 條件太寬。 | 不改 production |
| `2409` Stage 2 follow-up | 只針對 `2409` Stage 2 再補一條更窄的 closure policy，想壓 FP。 | 不改 production |

重點：

- 這些 QA runs 都是 experiment workflow。
- `2026-03-19` second-pass 明確沒有改 `runtime_prompts.json`，也沒有改 `criteria_stage1/` / `criteria_stage2/`。

---

## QA 重要流程圖：first-pass 到 second-pass

```text
QA v1 first-pass
  |
  +--> 問題 1：review topic literal 會漏進 final outputs
  |
  +--> 問題 2：只要沒有明確負證據，就很容易變成 score 3 / maybe
  |
  v
QA v1 second-pass
  |
  +--> 修 leak detector coverage 與 allowlist
  |
  +--> 收緊 defer 規則：
         必須先有正向 fit
         且不能同時帶 direct negative
  |
  v
結果
  |
  +--> hygiene 乾淨很多
  +--> 2511 明顯改善
  +--> 2409 的 Combined F1 反而掉太多
```

---

## QA 重要結果總表

| Source | `2409` Stage 1 | `2409` Combined | `2511` Stage 1 | `2511` Combined | 白話結論 |
| --- | ---: | ---: | ---: | ---: | --- |
| current production | `0.7500` | `0.8235` | `0.8788` | `0.9062` | pre-QA 正式基準；`2511` cutoff 修正後已回到 >0.9。 |
| QA v0 | `0.7119` | `0.8333` | `0.8727` | `0.8519` | `2409` Combined 曾短暫更高；`2511` 沒贏 current。 |
| QA v1 first-pass | `0.5753` | `0.8333` | `0.6383` | `0.8571` | first-pass 的 Stage 1 幾乎被 `maybe flood` 拖垮。 |
| QA v1 second-pass | `0.6774` | `0.7500` | `0.8772` | `0.8727` | `2511` 明顯救回，`2409` hygiene 修好但 Combined 變差。 |
| `2409` follow-up | `0.6897` | `0.7692` | n/a | n/a | precision 拉高，但 recall 掉太多。 |

---

## 新增 baseline：`stage2-only / fulltext-direct` 是什麼

| 面向 | 設定 | 白話說明 |
| --- | --- | --- |
| 名稱 | `fulltext-direct` / `stage2-only` | 不做 Stage 1 初篩，直接對所有 candidate 跑 full-text review。 |
| positive mode | `include_or_maybe` | 只要 final verdict 是 `include` 或 `maybe`，都算 positive。 |
| 範圍 | 四篇全跑 | `2307`、`2409`、`2511`、`2601` 都有結果。 |
| 性質 | experiment-only baseline | 只是比較用，不覆寫 production。 |
| 為什麼重要 | 它回答「如果乾脆直接讀全文，會不會比較好」 | 可以看出問題到底比較像 Stage 1 gating，還是全文判讀本身。 |

---

## `stage2-only / fulltext-direct` 結果

| Paper | F1 | TP | FP | TN | FN | Delta vs current combined | 白話判讀 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2307.05527` | `0.8924` | 141 | 4 | 47 | 30 | `-0.0657` | 直接讀全文反而比 current 差，代表它不需要這種重做法。 |
| `2409.13738` | `0.7692` | 20 | 11 | 52 | 1 | `-0.0151` | 幾乎沒比 current 好，表示 `2409` 問題不只是 Stage 1。 |
| `2511.13936` | `0.9062` | 29 | 5 | 53 | 1 | `+0.0000` | 直接讀全文與 current 打平，表示 cutoff 修正後的 current baseline 已吸收這條收益。 |
| `2601.19926` | `0.9691` | 329 | 14 | 10 | 7 | `-0.0042` | 幾乎和 current 差不多，沒有顯著收益。 |

四篇 pooled：

| 指標 | 數值 |
| --- | --- |
| pooled F1 | `0.9343` |
| pooled confusion matrix | `TP=519, FP=34, TN=162, FN=39` |

一句話：

> `stage2-only` 最有訊號的是 `2511`，但對 `2409` 沒有形成決定性改善，所以它不能單獨取代 QA 線或 current production。

---

## QA confusion matrix：`2409`

| 版本 | 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| current production | Stage 1 | 21 | 14 | 43 | 0 | pre-QA 基準是 FP-heavy。 |
| current production | Combined | 20 | 10 | 47 | 1 | 仍以 FP 為主。 |
| QA v0 | Stage 1 | 21 | 17 | 40 | 0 | 比 current 多 3 個 FP。 |
| QA v0 | Combined | 20 | 7 | 50 | 1 | Combined 一度拉到 `0.8333`。 |
| QA v1 first-pass | Stage 1 | 21 | 31 | 26 | 0 | 問題很明顯：`maybe` flood 造成 FP 爆量。 |
| QA v1 first-pass | Combined | 20 | 7 | 50 | 1 | Stage 2 還是把很多 FP 洗掉了。 |
| QA v1 second-pass | Stage 1 | 21 | 20 | 37 | 0 | hygiene 修好，FP 有降，但還是偏高。 |
| QA v1 second-pass | Combined | 18 | 9 | 48 | 3 | 為了收 FP，開始傷到 recall。 |
| `2409` follow-up | Stage 1 | 20 | 17 | 40 | 1 | Stage 1 沒有真正根治。 |
| `2409` follow-up | Combined | 15 | 3 | 54 | 6 | FP 壓很低，但 FN 增太多。 |

---

## QA confusion matrix：`2511`

| 版本 | 階段 | TP | FP | TN | FN | 白話判讀 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| current production | Stage 1 | 29 | 7 | 50 | 1 | cutoff 修正後，baseline 幾乎已穩。 |
| current production | Combined | 29 | 5 | 52 | 1 | current baseline 已到 `0.9062`，不再是明顯 recall-collapse。 |
| QA v0 | Stage 1 | 24 | 1 | 53 | 6 | 超高 precision，但漏收較多。 |
| QA v0 | Combined | 23 | 1 | 53 | 7 | Combined 被 FN 拖住。 |
| QA v1 first-pass | Stage 1 | 30 | 34 | 20 | 0 | `maybe flood` 導致 FP 失控。 |
| QA v1 first-pass | Combined | 24 | 2 | 52 | 6 | Stage 2 洗掉不少 FP。 |
| QA v1 second-pass | Stage 1 | 25 | 2 | 52 | 5 | second-pass 明顯成功救回 precision。 |
| QA v1 second-pass | Combined | 24 | 1 | 53 | 6 | Combined 到 `0.8727`，高於 v0 / first-pass。 |

---

## QA misclassification inventory

| Paper | Stage 1 FP / FN 重點 | Combined FP / FN 重點 |
| --- | --- | --- |
| `2409` | FP 很多，如 `bellan2022extracting`, `robeer2016`；FN 有 `azevedo2018bpmn` | FP 有 `bellan2022extracting`, `bellan_gpt3_2022`, `robeer2016`；FN 有 `goossens2023extracting`, `qian2020approach`, `vda_extracting_declarative_process` 等 |
| `2511` | current baseline 只剩少量 FP 與單一 unmatched gold case；QA 線則仍有 `chumbalov2020scalable`, `huang2025step`, `parthasarathy2018preference` 等 FN | QA 線的失誤現在比 current baseline 更值得分析 |

白話：

- `2409` 的錯很像「邊界抓太寬」與「publication-form 收錯方向」。
- `2511` 的錯更像「沒讀出 preference signal / speech-audio domain / RLHF learning role」。

---

## QA error taxonomy

| Family | 代表 paper | 白話說明 |
| --- | --- | --- |
| `publication-form overreach` | `goossens2023extracting`, `vda_extracting_declarative_process` | 把 accepted pre-proof、LNCS proceedings、metadata 缺口，直接當成不可納入。 |
| `target-boundary confusion` | `bellan2022extracting`, `robeer2016` | 把 process-adjacent、conceptual modeling 當成真正 target。 |
| `source-target inversion` | `azevedo2018bpmn` | 先看到 model->text，就漏掉 paper 其實也有 text->model。 |
| `preference-vs-evaluation confusion` | `manocha2020differentiable`, `huang2025step` | 一篇把 evaluation 誤認成 preference learning，另一篇把真的 reward learning 誤看成 evaluation。 |
| `pairwise / ranking / ordinal under-detection` | `wu2023interval`, `jayawardena2020ordinal` | paper 明明用了相對排序訊號，模型卻沒讀出來。 |
| `speech/audio domain miss` | `chumbalov2020scalable`, `parthasarathy2018preference` | 這類 case 在 QA 歷史線仍會漏掉，但 current production 已不再把 `parthasarathy2018preference` 當 cutoff case。 |

---

## 2409 Case Dossier 1

### `azevedo2018bpmn`

| 欄位 | 內容 |
| --- | --- |
| title | *BPMN Model and Text Instructions Automatic Synchronization* |
| gold label | `True` |
| predicted final verdict | Stage 1 `exclude (senior:2)`；combined 沒進 Stage 2 |
| 出錯層級 | `Stage 1 early exclude` + `source-target inversion` |
| 模型當時的主要理由 | senior 把它讀成「從 model 生成 text」，沒抓到 paper 也有 `text -> model` 半邊。 |
| 摘要白話 | 這篇做的是 BPMN 與文字工作說明的雙向同步：不只從 model 產文字，也會在文字被修改後回頭更新 model。 |
| 全文 evidence | 文內不只寫 `generate textual work instructions from the model`，也明寫 `updates the original model if the textual instructions are edited`，並把 `Text to Model` branch 獨立成 NLP component。 |
| FP / FN | `FN` |
| ambiguity | `borderline ambiguity` |
| 最核心一句 | 這篇不是只有 process-to-text；全文明確包含從自然語言文字回推 BPMN model。 |

---

## 2409 Case Dossier 2

### `bellan2022extracting`

| 欄位 | 內容 |
| --- | --- |
| title | *Extracting business process entities and relations from text using pre-trained language models and in-context learning* |
| gold label | `False` |
| predicted final verdict | Stage 2 `maybe (senior:3)`，combined 保持 positive |
| 出錯層級 | `Stage 2 closure` + `target-boundary confusion` |
| 模型當時的主要理由 | 模型認為它有具體方法與驗證，但 target fit 沒完全關閉，所以保留 `maybe`。 |
| 摘要白話 | 這篇是在抽 process entities 與 relations，想改善 process description documents 的資訊抽取。 |
| 全文 evidence | paper 自己把這件事定義成 two-step pipeline 的第一步：先抽 building blocks，再由下一步建 process model。它做的是 entities / relations，不是最終 formal model extraction。 |
| FP / FN | `FP` |
| ambiguity | `clean model error` |
| 最核心一句 | 這篇是在抽 process elements，不是在抽最終 formal process model。 |

---

## 2409 Case Dossier 3

### `robeer2016`

| 欄位 | 內容 |
| --- | --- |
| title | *Automated Extraction of Conceptual Models from User Stories via NLP* |
| gold label | `False` |
| predicted final verdict | Stage 2 `maybe (senior:3)`，combined 保持 positive |
| 出錯層級 | `Stage 2 closure` + `target-boundary confusion` |
| 模型當時的主要理由 | 模型承認它有 method 與 evaluation，但把「conceptual model from user stories」留成 plausibly-related。 |
| 摘要白話 | 這篇要從 agile requirements 的 user stories 自動生成 conceptual model。 |
| 全文 evidence | 文中多次限定 target object 是 `graphical conceptual models`、`OWL ontologies`、`conceptual model from user stories`，不是 business-process / decision-model extraction。 |
| FP / FN | `FP` |
| ambiguity | `clean model error` |
| 最核心一句 | 這篇是 user-story conceptual modeling，不是 process-model extraction。 |

---

## 2409 Case Dossier 4

### `goossens2023extracting`

| 欄位 | 內容 |
| --- | --- |
| title | *Extracting Decision Model and Notation models from text using deep learning techniques* |
| gold label | `True` |
| predicted final verdict | Stage 2 `exclude (senior:2)`；Stage 1 原本是 `maybe` |
| 出錯層級 | `Stage 2 closure` + `senior adjudication` + `publication-form overreach` |
| 模型當時的主要理由 | Stage 2 evaluator 其實已到 `clear_include`，但 senior 把 `Journal Pre-proof` 當成 publication-form negative。 |
| 摘要白話 | 這篇直接在做「從文字抽 DMN decision models」，而且用了 BERT / Bi-LSTM-CRF 與真實資料集驗證。 |
| 全文 evidence | 文內明寫 `To appear in: Expert Systems With Applications` 與 accepted date，且內容面上有完整 pipeline、dataset、experiments。 |
| FP / FN | `FN` |
| ambiguity | `clean model error` |
| 最核心一句 | accepted journal pre-proof 不是未審稿 preprint，不能直接當 negative。 |

---

## 2409 Case Dossier 5

### `qian2020approach`

| 欄位 | 內容 |
| --- | --- |
| title | *An Approach for Process Model Extraction by Multi-grained Text Classification* |
| gold label | `True` |
| predicted final verdict | Stage 2 `exclude (senior:2)`；Stage 1 原本是 `maybe` |
| 出錯層級 | `Stage 2 closure` |
| 模型當時的主要理由 | senior 認為 task fit、method、evaluation 都正向，但 local fulltext 的 `arXiv` header 讓 publication form 看起來不夠穩。 |
| 摘要白話 | 這篇就是 process model extraction from text，提出 hierarchical neural network 與 multi-grained learning，並做 extensive experiments。 |
| 全文 evidence | 內容 fit 幾乎完全沒問題；真正衝突的是 local markdown 只直接露出 `arXiv:1906.02127v3` 這種 metadata。 |
| FP / FN | `FN` |
| ambiguity | `borderline ambiguity` |
| 最核心一句 | 主衝突不在 task fit，而在 local fulltext 只露出 arXiv metadata。 |

---

## 2409 Case Dossier 6

### `vda_extracting_declarative_process`

| 欄位 | 內容 |
| --- | --- |
| title | *Extracting Declarative Process Models from Natural Language* |
| gold label | `True` |
| predicted final verdict | Stage 2 `exclude (senior:2)`；Stage 1 原本是 `maybe` |
| 出錯層級 | `Stage 2 closure` + `senior adjudication` + `publication-form overreach` |
| 模型當時的主要理由 | 模型承認它是 original NLP method with evaluation，但把它讀成 disqualifying book chapter。 |
| 摘要白話 | 這篇提出第一個從自然語言抽 declarative process model 的自動方法，並做 quantitative evaluation。 |
| 全文 evidence | 文中明寫 `CAiSE 2019, LNCS 11483`，且結果是拿自動抽取結果對 manually created gold standard 做 quantitative evaluation。 |
| FP / FN | `FN` |
| ambiguity | `clean model error` |
| 最核心一句 | `CAiSE 2019, LNCS` 被誤讀成 disqualifying book chapter。 |

---

## 2511 Case Dossier 1

### `manocha2020differentiable`

| 欄位 | 內容 |
| --- | --- |
| title | *A differentiable perceptual audio metric learned from just noticeable differences* |
| gold label | `False` |
| predicted final verdict | Stage 2 `include (junior:5,4)` |
| 出錯層級 | `Stage 2 closure` + `preference-signal overread` |
| 模型當時的主要理由 | 模型把 binary `same or different` judgments 視為 pairwise preference signal。 |
| 摘要白話 | 這篇做的是音訊 perceptual discriminability / JND metric，用人類判斷「是否相同」來訓練可微分的評估模型。 |
| 全文 evidence | 受試者回答的是兩段音訊是否 `same or different`；真正的 A/B preference test 只是 downstream denoising evaluation，不是 core training signal。 |
| FP / FN | `FP` |
| ambiguity | `clean model error` |
| 最核心一句 | `same or different` 的 JND 標註不是 ranking / preference learning。 |

---

## 2511 Case Dossier 2

### `wu2023interval`

| 欄位 | 內容 |
| --- | --- |
| title | *From Interval to Ordinal: A HMM based Approach for Emotion Label Conversion* |
| gold label | `True` |
| predicted final verdict | Stage 2 `exclude (senior:2)`；Stage 1 原本是 `maybe` |
| 出錯層級 | `Stage 2 closure` + `preference-signal under-detection` |
| 模型當時的主要理由 | 模型以為它只是 label conversion，沒有 ranking / comparative preference / RL loop。 |
| 摘要白話 | 這篇把 affective speech 的 interval labels 轉成 ordinal labels，同時用到 relative ordinal labels，也就是 pairwise comparisons。 |
| 全文 evidence | 文中直接說 `ROLs encode pairwise comparisons`，HMM transition probabilities 也整合了 relative ordinal information。 |
| FP / FN | `FN` |
| ambiguity | `borderline ambiguity` |
| 最核心一句 | 這篇不是沒有 preference signal，而是把 pairwise ordinal signal 用在 speech label conversion。 |

---

## 2511 Case Dossier 3

### `chumbalov2020scalable`

| 欄位 | 內容 |
| --- | --- |
| title | *Scalable and efficient comparison-based search without features* |
| gold label | `True` |
| predicted final verdict | Stage 1 `exclude (junior:2,2)`，combined 沒進 Stage 2 |
| 出錯層級 | `Stage 1 early exclude` + `audio-domain miss` |
| 模型當時的主要理由 | Stage 1 直接把它當成 generic comparison-based search，不是 audio。 |
| 摘要白話 | 這篇核心是 comparison-based search 與 triplet embedding；audio 不是唯一主軸，但 blind-setting evaluation 真的用到 music artists comparisons。 |
| 全文 evidence | 文中後段有 `music dataset` / `Music artists` triplet comparisons，但另一個重點實驗也在 movie actors。 |
| FP / FN | `FN` |
| ambiguity | `borderline ambiguity` |
| 最核心一句 | 這篇不是完全非-audio，但 audio 只佔一個側面，所以邊界最模糊。 |

---

## 2511 Case Dossier 4

### `jayawardena2020ordinal`

| 欄位 | 內容 |
| --- | --- |
| title | *How Ordinal Are Your Data?* |
| gold label | `True` |
| predicted final verdict | Stage 1 `exclude (senior:2)`，combined 沒進 Stage 2 |
| 出錯層級 | `Stage 1 early exclude` + `pairwise/ranking/ordinal under-detection` |
| 模型當時的主要理由 | title/abstract 很 generic，模型把它當成一般 ordinal-data methodology paper。 |
| 摘要白話 | 這篇研究在 affective computing 裡，什麼時候該做 classification、ordinal regression、regression，並提出含 pairwise preference loss 的框架。 |
| 全文 evidence | 文中明寫語境是 `speech processing` / `speech-based affective computing`，也直接引入 `PrefNet` 與 `pairwise preference loss`。 |
| FP / FN | `FN` |
| ambiguity | `borderline ambiguity` |
| 最核心一句 | title 很 generic，但正文其實明確站在 speech affective computing，且用 pairwise preference loss。 |

---

## 2511 Case Dossier 5

### `parthasarathy2018preference`

| 欄位 | 內容 |
| --- | --- |
| title | *Preference-Learning with Qualitative Agreement for Sentence Level Emotional Annotations* |
| gold label | `True` |
| predicted final verdict | Stage 1 `exclude (junior:2,2)`，combined 沒進 Stage 2 |
| 出錯層級 | `Stage 1 early exclude` + `speech/audio domain miss` |
| 模型當時的主要理由 | 模型承認它有 preference-learning，但沒把 title/abstract 讀成 audio / speech。 |
| 摘要白話 | 這篇直接做 sentence-level emotional annotations 的 QA-based labels，並用 preference-learning 來 rank-order emotional attributes。 |
| 全文 evidence | abstract 結尾的 index terms 就有 `speech emotion recognition, preference-learning`；全文前幾行也直接寫 speech。 |
| FP / FN | `FN` |
| ambiguity | `clean model error` |
| 最核心一句 | 這篇連 index terms 都寫了 `speech emotion recognition, preference-learning`，卻仍被 Stage 1 當成非-audio。 |

---

## 2511 Case Dossier 6

### `huang2025step`

| 欄位 | 內容 |
| --- | --- |
| title | *Step-Audio: Unified Understanding and Generation in Intelligent Speech Interaction* |
| gold label | `True` |
| predicted final verdict | Stage 1 `exclude (senior:2)`，combined 沒進 Stage 2 |
| 出錯層級 | `Stage 1 early exclude` + `preference-vs-evaluation confusion` |
| 模型當時的主要理由 | 模型把它看成 audio model with human evaluation，但沒有 preference-learning core。 |
| 摘要白話 | 這篇是 production-ready speech-text multimodal model，但全文其實還有 AQTA preference data、reward model、PPO、RLHF。 |
| 全文 evidence | 文中明寫 `Reinforcement Learning from Human Feedback`、`AQTA Preference Data Construction`、Bradley-Terry loss、reward model、PPO training。 |
| FP / FN | `FN` |
| ambiguity | `clean model error` |
| 最核心一句 | 這篇把 audio preference pairs 用在 reward model 和 PPO，不是只做 human eval。 |

---

## 最後整理：pre-QA 到 QA 的主結論

| 問題 | 最後結論 |
| --- | --- |
| pre-QA 系統最後長什麼樣？ | `runtime_prompts.json` + stage-split criteria + Stage 1 routing + `SeniorLead`。 |
| 哪兩篇最難？ | `2409` 與 `2511`。 |
| 為什麼 `2409` 還低？ | 核心是 FP-heavy，process-adjacent 與 publication-form closure 容易出錯。 |
| 為什麼 `2511` 曾經難？ | preference signal、audio domain、learning vs evaluation 的邊界常被讀錯；但 cutoff 修正後 current baseline 已回到 `0.9062`。 |
| QA-first 想解什麼？ | 不是再改 formal criteria，而是把 evidence 先拆成固定 QA，再根據答案做判斷。 |
| QA second-pass 成功了嗎？ | `2511` 成功很多；`2409` hygiene 修好了，但 Combined F1 掉到 `0.7500`。 |
| `2409` follow-up 成功了嗎？ | 沒有。FP 壓低了，但 recall 掉太多，Combined 只有 `0.7692`。 |
| 新增的 `stage2-only` baseline 告訴我們什麼？ | `2511` 直接全文與 current 打平在 `0.9062`，表示 cutoff 修正後 baseline 已吸收主要收益；`2409` 仍只有 `0.7692`，所以它依然更像全文判讀本身也難。 |

---

## 可直接拿來講的一句話版本

> QA 前，系統已把 prompt、routing、criteria 結構整理到相對乾淨；但 `2409` 仍卡 hard FP，`2511` 仍卡 preference-signal 邊界。  
> QA-first 的目的不是再偷加新 criteria，而是先把證據問清楚，再做判斷。  
> 到 `2026-03-19` 為止，`2511` second-pass 已有進展，但 `2409` 還沒被救回到可放行的水位。

---

## 來源

- `docs/pre_qa_experiment_summary_zh-報告用.md`
- `docs/qa_forensic_error_analysis-報告用.md`
- `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/REPORT_zh.md`
- `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/REPORT_zh.md`
- `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/REPORT_zh.md`
- `AGENTS.md`
