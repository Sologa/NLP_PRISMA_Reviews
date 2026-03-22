---
title: "NLP_PRISMA_Reviews cutoff_jsons 時間限制稽核"
generated_on: "2026-03-22"
paper_count: 16
source_repo: "https://github.com/Sologa/NLP_PRISMA_Reviews/"
scope: "cutoff_jsons/ 內 16 篇 SR；同時參照 source_md 與 arXiv abs 頁面"
interpretation_rule: "嚴格區分 paper-native time rule 與 repo pipeline fallback"
---

# NLP_PRISMA_Reviews cutoff_jsons 時間限制稽核

## 方法

1. 以 `cutoff_jsons/*.json` 作為時間政策的正規化主來源。
2. 以 `source_md`（`criteria_mds` / `criteria_corrected_3papers`）確認 Stage 1 / Stage 2 / notes 的原始描述。
3. 以 arXiv `abs` 頁面記錄 review paper 自身的公開時間；若 abs 顯示 later version，亦一併標示。
4. 本檔特別區分：
   - `paper-native time rule`：SR 文本自己明寫的年份/日期納入規則。
   - `repo fallback`：為了讓 pipeline 可 deterministic 執行，`cutoff_json` 額外補上的 upper bound 或正規化。

## 高層摘要

| 類型 | 數量 | 說明 |
|---|---:|---|
| 明文 bounded window（Stage 2 / final analysis） | 7 | 2303.13365, 2307.05527, 2312.05172, 2405.15604, 2503.04799, 2507.07741, 2510.01145 |
| 明文 no restriction | 1 | 2409.13738 |
| retrieval-only window | 4 | 2306.12834, 2407.17844, 2507.18910, 2601.19926 |
| 無 paper-native 時間規則，repo fallback | 3 | 2310.07264, 2401.09244, 2509.11446 |
| retrieval lower bound + repo upper bound | 1 | 2511.13936 |

## 優先人工複核的 caveats

1. 2405.15604：criteria 正規化為 2017–2023，但 arXiv 摘要寫 review comprises 244 selected papers between 2017 and 2024。
2. 2312.05172：time window 上界到 2025，需搭配 later arXiv revision（v2, 2026-01-31）理解，不能只看 v1。
3. 2310.07264 / 2401.09244 / 2509.11446 / 2511.13936：cutoff_json 有 repo-level upper bound；這不等於 paper 自己明寫的納入年份規則。
4. 2409.13738：formal criterion 明確無年份限制，但 paper 正文結果段仍寫 search executed in June 2023、實際找到的 papers span 2011–2023。

## 全表總覽

| ID | arXiv 自身時間 | 結論 | 標準化視窗/規則 | repo 註記 |
|---|---|---|---|---|
| 2303.13365 | 2023-03-18 (arXiv v1) | 有。正式納入條件在 Stage 2 I1 明定發表時間為 2012-01 至 2022-03。 | `2012-01-01 至 2022-03-31 (inclusive)` | 無額外 repo fallback；cutoff_json 直接對應 Stage 2... |
| 2306.12834 | 2023-06-22 (arXiv v1) | 只有檢索期限制。Stage 1 指定 search period 為 2016–2022；Stage 2 沒有另外明定年份納入條件。 | `2016-01-01 至 2022-12-31 (repo 以 Stage 1 fallback 正規化)` | cutoff_json 註記沒有 Stage 2 time rule，因此 fall... |
| 2307.05527 | 2023-07-07 (arXiv v1; comments 顯示 AIES '23) | 有。Stage 2 I5 明定 submitted/published 必須落在 2018-02-01 至 2023-02-01。 | `2018-02-01 至 2023-02-01 (inclusive)` | 無額外 repo fallback；cutoff_json 直接沿用 Stage 2... |
| 2310.07264 | 2023-10-11 (arXiv v1) | 沒有找到 paper-native 的發表時間限制。criteria 只規範主題與關鍵詞，不規範年份。 | `無明文視窗；repo 為可執行性手動加上 end_date = 2023-10-11` | cutoff_json 明寫這是 manual no-time mapping：把 ... |
| 2312.05172 | 2023-12-08 (arXiv v1); latest visible version 2026-01-31 (v2) | 有。Stage 2 I1 明定 publication date between 2000 and 2025。 | `2000-01-01 至 2025-12-31 (inclusive)` | 無 repo fallback；但要注意 2025 上界顯然對應較晚版本內容，不能只... |
| 2401.09244 | 2024-01-17 (arXiv v1); latest visible version 2026-02-12 (v3) | criteria 中沒有明文的 publication-year restriction。 | `無明文視窗；repo 以 2024-01-17 作為 deterministic upper bound` | cutoff_json 明確說這是 manual no-time mapping；e... |
| 2405.15604 | 2024-05-24 (arXiv v1); latest visible version 2024-08-29 (v3) | 依 cutoff_json/criteria_md，Stage 2 I1 將手動評估候選文獻限制在 2017–2023。 | `2017-01-01 至 2023-12-31 (inclusive; repo 以 Stage 2 優先)` | 存在 paper-internal discrepancy：criteria 正規化... |
| 2407.17844 | 2024-07-25 (arXiv v1); latest visible version 2024-09-24 (v4) | 只有 retrieval-stage 的年份條件。Stage 1 R5 設 year filter = 2020 onwards；Stage 2 無額外年份條件。 | `自 2020-01-01 起；無 paper-native 上界` | cutoff_json 依 Stage 1 R5 建立開區間下界；沒有 Stage ... |
| 2409.13738 | 2024-09-10 (arXiv v1) | 沒有年份限制。Stage 2 I8 明寫 do not exclude by year。 | `無時間窗；time filtering disabled` | cutoff_json 正確地把 enabled 設為 false；沒有套用 man... |
| 2503.04799 | 2025-03-03 (arXiv v1) | 有。Stage 2 I2 明定 published between 2016 and 2024。 | `2016-01-01 至 2024-12-31 (inclusive)` | 無 repo fallback。 |
| 2507.07741 | 2025-07-10 (arXiv v1) | 有兩層：Stage 1 retrieval 先抓 2014-01-01 到 2025-02-27；Stage 2/analysis set 再聚焦 2018–2024。 | `retrieval: 2014-01-01 至 2025-02-27; analysis set: 2018-01-01 至 2024-12-31` | 這篇要區分『候選集時間窗』與『最終分析集時間窗』；repo 取後者。 |
| 2507.18910 | 2025-07-25 (arXiv v1) | 只有 Stage 1 的時間 coverage：2017 到 mid-2025 結束；Stage 2 沒有獨立年份條件。 | `2017-01-01 至 2025-06-30 (repo 將 'end of mid 2025' 正規化為 2025-06-30)` | cutoff_json 只有 Stage 1 R6 可用，因此把 mid-2025 ... |
| 2509.11446 | 2025-09-14 (arXiv v1) | criteria 沒有明文的 publication-time restriction。 | `無明文視窗；repo 手動設 end_date = 2025-09-14` | cutoff_json 的 upper bound 是 pipeline-frien... |
| 2510.01145 | 2025-10-01 (arXiv v1) | 有。Stage 2 I2 明定 published between January 2020 and July 2025。 | `2020-01-01 至 2025-07-31 (inclusive)` | 無 repo fallback。 |
| 2511.13936 | 2025-11-17 (arXiv v1) | paper 文本明確把 candidate works 限定為 2020 onward；但 final selection rule 本身沒有另寫 upper bound。repo 為重現性加上 upper bound = review 發表日。 | `start_date = 2020-01-01; repo practical end_date = 2025-11-17` | cutoff_json 明說 upper bound 來自 review paper... |
| 2601.19926 | 2026-01-09 (arXiv v1) | 只有 retrieval-stage upper bound。Stage 1 R1 寫 cut-off date for inclusion: up to July 31, 2025；Stage 2 沒有額外 lower bound。 | `publication_date <= 2025-07-31` | cutoff_json 直接採 Stage 1 R1 作為 cutoff fallb... |

## A. 有明文時間限制（Stage 2 或 final analysis set）

這一組 papers 在最終納入條件或最終分析集合中直接寫出時間窗；其中 2507.07741 同時保留更寬的 retrieval window。

### 2303.13365 — Requirement Formalisation using Natural Language Processing and Machine Learning: A Systematic Review

```yaml
{
  "title": "Requirement Formalisation using Natural Language Processing and Machine Learning: A Systematic Review",
  "publication_display": "2023-03-18 (arXiv v1)",
  "arxiv_initial_submission": "2023-03-18",
  "arxiv_latest_visible_version": null,
  "category": "stage2_bounded",
  "category_label": "Stage 2 明文時間窗",
  "paper_native_time_conclusion": "有。正式納入條件在 Stage 2 I1 明定發表時間為 2012-01 至 2022-03。",
  "normalized_window_or_rule": "2012-01-01 至 2022-03-31 (inclusive)",
  "screening_time_notes": [
    "criteria_md 備註此文另有 PRISMA-like selection process，包含 de-duplication 與 title/abstract screening。",
    "arXiv 摘要明寫最終選入 47 篇相關研究，時間落在 2012–2022。"
  ],
  "repo_caveat": "無額外 repo fallback；cutoff_json 直接對應 Stage 2 I1。",
  "time_evidence": "Published between January 2012 and March 2022.",
  "extra_note": "paper-level time rule 與摘要中的最終納入年份範圍一致。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2303.13365",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2303.13365.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2303.13365.md"
  }
}
```

### 2307.05527 — The Ethical Implications of Generative Audio Models: A Systematic Literature Review

```yaml
{
  "title": "The Ethical Implications of Generative Audio Models: A Systematic Literature Review",
  "publication_display": "2023-07-07 (arXiv v1; comments 顯示 AIES '23)",
  "arxiv_initial_submission": "2023-07-07",
  "arxiv_latest_visible_version": null,
  "category": "stage2_bounded",
  "category_label": "Stage 2 明文時間窗",
  "paper_native_time_conclusion": "有。Stage 2 I5 明定 submitted/published 必須落在 2018-02-01 至 2023-02-01。",
  "normalized_window_or_rule": "2018-02-01 至 2023-02-01 (inclusive)",
  "screening_time_notes": [
    "Stage 1 與 Stage 2 使用同一個 temporal window。",
    "ACM 查詢使用 past-5-years filter；arXiv 查詢使用同一個 date_range。",
    "criteria_md 另外限定分析證據僅看 paper 本文與附錄，不看外部 supplementary。"
  ],
  "repo_caveat": "無額外 repo fallback；cutoff_json 直接沿用 Stage 2 I5。",
  "time_evidence": "Temporal window: submitted/published within 2018-02-01 to 2023-02-01.",
  "extra_note": "這是少數 search window 與 eligibility window 完全對齊的案例。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2307.05527",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2307.05527.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_corrected_3papers/2307.05527.md"
  }
}
```

### 2312.05172 — From Lengthy to Lucid: A Systematic Literature Review on NLP Techniques for Taming Long Sentences

```yaml
{
  "title": "From Lengthy to Lucid: A Systematic Literature Review on NLP Techniques for Taming Long Sentences",
  "publication_display": "2023-12-08 (arXiv v1); latest visible version 2026-01-31 (v2)",
  "arxiv_initial_submission": "2023-12-08",
  "arxiv_latest_visible_version": "2026-01-31",
  "category": "stage2_bounded",
  "category_label": "Stage 2 明文時間窗",
  "paper_native_time_conclusion": "有。Stage 2 I1 明定 publication date between 2000 and 2025。",
  "normalized_window_or_rule": "2000-01-01 至 2025-12-31 (inclusive)",
  "screening_time_notes": [
    "Stage 1 對 2000–2022 每個資料庫只看前 300 筆；對 2023–2025 每庫只看 30 筆。",
    "Stage 2 E4 另加一條時間相關 quality/citation gate：2017 以前的研究若 citations < 10 則排除。",
    "摘要另提興趣自 2005 起上升、2017 後顯著增長，但這是趨勢描述，不是 eligibility rule。"
  ],
  "repo_caveat": "無 repo fallback；但要注意 2025 上界顯然對應較晚版本內容，不能只用 v1 理解。",
  "time_evidence": "Publication date between 2000 and 2025.",
  "extra_note": "此 paper 的 time policy 與 later arXiv revision 相容；若只看初始上傳時間會誤判。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2312.05172",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2312.05172.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2312.05172.md"
  }
}
```

### 2405.15604 — Text Generation: A Systematic Literature Review of Tasks, Evaluation, and Challenges

```yaml
{
  "title": "Text Generation: A Systematic Literature Review of Tasks, Evaluation, and Challenges",
  "publication_display": "2024-05-24 (arXiv v1); latest visible version 2024-08-29 (v3)",
  "arxiv_initial_submission": "2024-05-24",
  "arxiv_latest_visible_version": "2024-08-29",
  "category": "stage2_bounded",
  "category_label": "Stage 2 明文時間窗",
  "paper_native_time_conclusion": "依 cutoff_json/criteria_md，Stage 2 I1 將手動評估候選文獻限制在 2017–2023。",
  "normalized_window_or_rule": "2017-01-01 至 2023-12-31 (inclusive; repo 以 Stage 2 優先)",
  "screening_time_notes": [
    "Stage 1 R3 先排除 2016 或更早。",
    "Stage 1 R5 每個 query × year 取 influential citations 排名前 5。",
    "Stage 1 R6-R7 對 <=2021 的 papers 加 citations 門檻；2022–2023 放寬。",
    "摘要卻寫 review comprises 244 selected papers between 2017 and 2024。"
  ],
  "repo_caveat": "存在 paper-internal discrepancy：criteria 正規化為 2017–2023，但 arXiv 摘要寫 2017–2024。",
  "time_evidence": "Manually assessed candidate works are within years 2017 to 2023 (titles and abstracts manually assessed for relevance).",
  "extra_note": "這篇建議列為人工複核優先案例。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2405.15604",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2405.15604.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2405.15604.md"
  }
}
```

### 2503.04799 — Direct Speech to Speech Translation: A Review

```yaml
{
  "title": "Direct Speech to Speech Translation: A Review",
  "publication_display": "2025-03-03 (arXiv v1)",
  "arxiv_initial_submission": "2025-03-03",
  "arxiv_latest_visible_version": null,
  "category": "stage2_bounded",
  "category_label": "Stage 2 明文時間窗",
  "paper_native_time_conclusion": "有。Stage 2 I2 明定 published between 2016 and 2024。",
  "normalized_window_or_rule": "2016-01-01 至 2024-12-31 (inclusive)",
  "screening_time_notes": [
    "可抽出的 criteria 沒有更細的 search-date 或 year-specific filtering pipeline。",
    "criteria_md 註明 underrepresented languages / acoustic variation 是討論焦點，不是 eligibility filter。"
  ],
  "repo_caveat": "無 repo fallback。",
  "time_evidence": "Published between 2016 and 2024.",
  "extra_note": "這篇的時間規則乾淨直接，幾乎只有一條主要窗口。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2503.04799",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2503.04799.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2503.04799.md"
  }
}
```

### 2507.07741 — Code-Switching in End-to-End Automatic Speech Recognition: A Systematic Literature Review

```yaml
{
  "title": "Code-Switching in End-to-End Automatic Speech Recognition: A Systematic Literature Review",
  "publication_display": "2025-07-10 (arXiv v1)",
  "arxiv_initial_submission": "2025-07-10",
  "arxiv_latest_visible_version": null,
  "category": "stage2_bounded",
  "category_label": "Retrieval 寬窗 + final analysis 窄窗",
  "paper_native_time_conclusion": "有兩層：Stage 1 retrieval 先抓 2014-01-01 到 2025-02-27；Stage 2/analysis set 再聚焦 2018–2024。",
  "normalized_window_or_rule": "retrieval: 2014-01-01 至 2025-02-27; analysis set: 2018-01-01 至 2024-12-31",
  "screening_time_notes": [
    "Candidate papers 由 Semantic Scholar API 擷取。",
    "Stage 2 I3 明寫 analysis set focuses on papers published between 2018 and 2024。",
    "cutoff_json 註記依優先序採 Stage 2 I3 作最終 cutoff。"
  ],
  "repo_caveat": "這篇要區分『候選集時間窗』與『最終分析集時間窗』；repo 取後者。",
  "time_evidence": "Analysis set focuses on papers published between 2018 and 2024 (the resulting eligible set for analysis).",
  "extra_note": "這是 retrieval window 與 final analysis window 不同的典型例子。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2507.07741",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2507.07741.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2507.07741.md"
  }
}
```

### 2510.01145 — Automatic Speech Recognition (ASR) for African Low-Resource Languages: A Systematic Literature Review

```yaml
{
  "title": "Automatic Speech Recognition (ASR) for African Low-Resource Languages: A Systematic Literature Review",
  "publication_display": "2025-10-01 (arXiv v1)",
  "arxiv_initial_submission": "2025-10-01",
  "arxiv_latest_visible_version": null,
  "category": "stage2_bounded",
  "category_label": "Stage 2 明文時間窗",
  "paper_native_time_conclusion": "有。Stage 2 I2 明定 published between January 2020 and July 2025。",
  "normalized_window_or_rule": "2020-01-01 至 2025-07-31 (inclusive)",
  "screening_time_notes": [
    "Stage 1 R7 與 Stage 2 I2 使用相同時間窗。",
    "selection 流程中會去重，且 quality score < 3/5 直接排除。",
    "摘要再次確認 search for studies published between January 2020 and July 2025。"
  ],
  "repo_caveat": "無 repo fallback。",
  "time_evidence": "Published between January 2020 and July 2025.",
  "extra_note": "這篇的時間條件在 retrieval、eligibility、abstract 三處高度一致。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2510.01145",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2510.01145.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2510.01145.md"
  }
}
```

## B. Stage 2 明文寫「無年份限制」

這一組明確寫出「不要用年份排除」，但 paper 仍可能在結果段呈現實際納入年份範圍。

### 2409.13738 — NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods

```yaml
{
  "title": "NLP4PBM: A Systematic Review on Process Extraction using Natural Language Processing with Rule-based, Machine and Deep Learning Methods",
  "publication_display": "2024-09-10 (arXiv v1)",
  "arxiv_initial_submission": "2024-09-10",
  "arxiv_latest_visible_version": null,
  "category": "stage2_no_restriction",
  "category_label": "Stage 2 明文寫『無年份限制』",
  "paper_native_time_conclusion": "沒有年份限制。Stage 2 I8 明寫 do not exclude by year。",
  "normalized_window_or_rule": "無時間窗；time filtering disabled",
  "screening_time_notes": [
    "Stage 1 先去重，再用 title/abstract/author keywords 做 eligibility screening。",
    "Stage 1 有一個時間相關 tie-break：若多篇對應同一 contribution，只保留 most recent paper。",
    "paper 正文結果段寫 search queries executed in June 2023，找到的 papers span 2011–2023。",
    "Table 2 metadata year 欄也寫 From 2011 to 2023；PRISMA flow 為 524 -> 405 -> 70 -> 20。"
  ],
  "repo_caveat": "cutoff_json 正確地把 enabled 設為 false；沒有套用 manual fallback。",
  "time_evidence": "No publication-year restriction (i.e., do not exclude by year).",
  "extra_note": "這篇是目前清楚區分『無 formal 年份限制』與『實際納入 corpus 落在 2011–2023』的代表案例。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2409.13738",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2409.13738.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_corrected_3papers/2409.13738.md"
  }
}
```

## C. 只有 retrieval-stage 的時間窗

這一組只有檢索範圍或候選集的時間窗，沒有獨立的 Stage 2 年份納排條件。

### 2306.12834 — Natural Language Processing in Electronic Health Records in Relation to Healthcare Decision-making: A Systematic Review

```yaml
{
  "title": "Natural Language Processing in Electronic Health Records in Relation to Healthcare Decision-making: A Systematic Review",
  "publication_display": "2023-06-22 (arXiv v1)",
  "arxiv_initial_submission": "2023-06-22",
  "arxiv_latest_visible_version": null,
  "category": "retrieval_only",
  "category_label": "只有 retrieval-stage 時間窗",
  "paper_native_time_conclusion": "只有檢索期限制。Stage 1 指定 search period 為 2016–2022；Stage 2 沒有另外明定年份納入條件。",
  "normalized_window_or_rule": "2016-01-01 至 2022-12-31 (repo 以 Stage 1 fallback 正規化)",
  "screening_time_notes": [
    "Stage 1 R1: search period 2016–2022。",
    "摘要寫明先從 11 個資料庫 screening 261 篇，再納入 127 篇做 full-text review。",
    "criteria_md 備註 full-text quality examination 存在，但未抽出明確 rubric/threshold。"
  ],
  "repo_caveat": "cutoff_json 註記沒有 Stage 2 time rule，因此 fallback 到 Stage 1 R1。",
  "time_evidence": "Search period: 2016–2022.",
  "extra_note": "這種情況比較像『搜尋範圍有年份界線』，而不是『最終納入標準明文按年份排除』。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2306.12834",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2306.12834.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2306.12834.md"
  }
}
```

### 2407.17844 — Innovative Speech-Based Deep Learning Approaches for Parkinson's Disease Classification: A Systematic Review

```yaml
{
  "title": "Innovative Speech-Based Deep Learning Approaches for Parkinson's Disease Classification: A Systematic Review",
  "publication_display": "2024-07-25 (arXiv v1); latest visible version 2024-09-24 (v4)",
  "arxiv_initial_submission": "2024-07-25",
  "arxiv_latest_visible_version": "2024-09-24",
  "category": "retrieval_only",
  "category_label": "只有 retrieval-stage 時間窗",
  "paper_native_time_conclusion": "只有 retrieval-stage 的年份條件。Stage 1 R5 設 year filter = 2020 onwards；Stage 2 無額外年份條件。",
  "normalized_window_or_rule": "自 2020-01-01 起；無 paper-native 上界",
  "screening_time_notes": [
    "Stage 1 R1 明寫 search performed in April 2024。",
    "Stage 1 同時排除 neuroimaging 相關研究，並以 title/abstract/keywords 手動辨識 DL 關鍵詞。",
    "摘要說 review 基於 2020-01 至 2024-03 的 33 篇研究。"
  ],
  "repo_caveat": "cutoff_json 依 Stage 1 R5 建立開區間下界；沒有 Stage 2 time rule。",
  "time_evidence": "Year filter: 2020 onwards.",
  "extra_note": "這篇的實際 review corpus 上界可從摘要看成 2024-03，但那是結果描述，不是獨立的 Stage 2 rule。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2407.17844",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2407.17844.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2407.17844.md"
  }
}
```

### 2507.18910 — A Systematic Review of Key Retrieval-Augmented Generation (RAG) Systems: Progress, Gaps, and Future Directions

```yaml
{
  "title": "A Systematic Review of Key Retrieval-Augmented Generation (RAG) Systems: Progress, Gaps, and Future Directions",
  "publication_display": "2025-07-25 (arXiv v1)",
  "arxiv_initial_submission": "2025-07-25",
  "arxiv_latest_visible_version": null,
  "category": "retrieval_only",
  "category_label": "只有 retrieval-stage 時間窗",
  "paper_native_time_conclusion": "只有 Stage 1 的時間 coverage：2017 到 mid-2025 結束；Stage 2 沒有獨立年份條件。",
  "normalized_window_or_rule": "2017-01-01 至 2025-06-30 (repo 將 'end of mid 2025' 正規化為 2025-06-30)",
  "screening_time_notes": [
    "Initial screening 先 merge results + remove duplicates，再看 abstracts/titles。",
    "若 work 只談 retrieval 或只談 generation（沒有 integration），在初篩時會被 set aside for possible exclusion。",
    "Stage 2 明示 preprints 也納入；notes 還說 corpus 不限於 peer-reviewed，亦考慮 technical reports / industry white papers。"
  ],
  "repo_caveat": "cutoff_json 只有 Stage 1 R6 可用，因此把 mid-2025 正規化成 2025-06-30。",
  "time_evidence": "Publication time coverage: documents published from 2017 up to the end of mid 2025.",
  "extra_note": "這篇同時放寬 publication type，因此『時間窗』與『來源型態』要分開處理。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2507.18910",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2507.18910.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2507.18910.md"
  }
}
```

### 2601.19926 — The Grammar of Transformers: A Systematic Review of Interpretability Research on Syntactic Knowledge in Language Models

```yaml
{
  "title": "The Grammar of Transformers: A Systematic Review of Interpretability Research on Syntactic Knowledge in Language Models",
  "publication_display": "2026-01-09 (arXiv v1)",
  "arxiv_initial_submission": "2026-01-09",
  "arxiv_latest_visible_version": null,
  "category": "retrieval_only",
  "category_label": "只有 retrieval-stage 時間窗",
  "paper_native_time_conclusion": "只有 retrieval-stage upper bound。Stage 1 R1 寫 cut-off date for inclusion: up to July 31, 2025；Stage 2 沒有額外 lower bound。",
  "normalized_window_or_rule": "publication_date <= 2025-07-31",
  "screening_time_notes": [
    "snowballing 來自 6 篇既有 reviews；若某 review 的 cited-by >100，只檢查 top 30–40%。",
    "relevance assessment protocol 是 title -> abstract -> full text。",
    "Stage 2 的時間相關內容主要只有 publication type，沒有再補年份下界。"
  ],
  "repo_caveat": "cutoff_json 直接採 Stage 1 R1 作為 cutoff fallback。",
  "time_evidence": "Cut-off date for inclusion: up to July 31, 2025.",
  "extra_note": "這篇是『有明文 upper bound、無明文 lower bound』的乾淨案例。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2601.19926",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2601.19926.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_corrected_3papers/2601.19926.md"
  }
}
```

## D. 沒有 paper-native 時間規則，repo 手動補上 upper bound

這一組的 cutoff_json 為了讓 pipeline 可 deterministic 執行，手動把 review paper 自己的發表日期映射成 upper bound；這不是 paper-native criterion。

### 2310.07264 — Classification of Dysarthria based on the Levels of Severity. A Systematic Review

```yaml
{
  "title": "Classification of Dysarthria based on the Levels of Severity. A Systematic Review",
  "publication_display": "2023-10-11 (arXiv v1)",
  "arxiv_initial_submission": "2023-10-11",
  "arxiv_latest_visible_version": null,
  "category": "repo_fallback_only",
  "category_label": "無 paper-native 時間規則，repo 補上 upper bound",
  "paper_native_time_conclusion": "沒有找到 paper-native 的發表時間限制。criteria 只規範主題與關鍵詞，不規範年份。",
  "normalized_window_or_rule": "無明文視窗；repo 為可執行性手動加上 end_date = 2023-10-11",
  "screening_time_notes": [
    "Stage 1 要求 main keywords 出現在 title/abstract/keywords。",
    "criteria_md 備註 paper 採 two-stage process（screening -> eligibility）。",
    "摘要寫 sources include electronic databases and grey literature，但未給年份界線。"
  ],
  "repo_caveat": "cutoff_json 明寫這是 manual no-time mapping：把 review 自身的 publication date 當作 pipeline 的 upper bound，而不是 paper 的原生納入條件。",
  "time_evidence": "No explicit publication-time restriction in criteria. Applied the review paper's own publication date as the upper bound: 2023-10-11...",
  "extra_note": "這類 case 需要在 downstream pipeline 中避免把 repo upper bound 誤讀成 SR 自己的納入標準。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2310.07264",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2310.07264.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2310.07264.md"
  }
}
```

### 2401.09244 — Cross-lingual Offensive Language Detection: A Systematic Review of Datasets, Transfer Approaches and Challenges

```yaml
{
  "title": "Cross-lingual Offensive Language Detection: A Systematic Review of Datasets, Transfer Approaches and Challenges",
  "publication_display": "2024-01-17 (arXiv v1); latest visible version 2026-02-12 (v3)",
  "arxiv_initial_submission": "2024-01-17",
  "arxiv_latest_visible_version": "2026-02-12",
  "category": "repo_fallback_only",
  "category_label": "無 paper-native 時間規則，repo 補上 upper bound",
  "paper_native_time_conclusion": "criteria 中沒有明文的 publication-year restriction。",
  "normalized_window_or_rule": "無明文視窗；repo 以 2024-01-17 作為 deterministic upper bound",
  "screening_time_notes": [
    "Stage 1 R1 明寫 search conducted on 2023-07-29。",
    "Stage 1 R26 之後還有從相關 survey 做 snowballing。",
    "paper 本身沒有把年份寫成 Stage 2 的排除或納入條件。"
  ],
  "repo_caveat": "cutoff_json 明確說這是 manual no-time mapping；end_date 不是 paper-native criterion。",
  "time_evidence": "No explicit publication-time restriction in criteria. Applied the review paper's own publication date as the upper bound: 2024-01-17...",
  "extra_note": "若後續 pipeline 想忠實重現 paper 原意，應把這篇視為『無明文年份限制』，而非『截止 2024-01-17』。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2401.09244",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2401.09244.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2401.09244.md"
  }
}
```

### 2509.11446 — Large Language Models (LLMs) for Requirements Engineering (RE): A Systematic Literature Review

```yaml
{
  "title": "Large Language Models (LLMs) for Requirements Engineering (RE): A Systematic Literature Review",
  "publication_display": "2025-09-14 (arXiv v1)",
  "arxiv_initial_submission": "2025-09-14",
  "arxiv_latest_visible_version": null,
  "category": "repo_fallback_only",
  "category_label": "無 paper-native 時間規則，repo 補上 upper bound",
  "paper_native_time_conclusion": "criteria 沒有明文的 publication-time restriction。",
  "normalized_window_or_rule": "無明文視窗；repo 手動設 end_date = 2025-09-14",
  "screening_time_notes": [
    "Stage 1 以 Scopus 為主，另有 issue-to-issue 補充搜尋。",
    "摘要明寫 review examines 74 primary studies published between 2023 and 2024。",
    "因此 paper 的實際 corpus 有明顯時間集中，但 criteria 本身沒有把它寫成 Stage 2 年份門檻。"
  ],
  "repo_caveat": "cutoff_json 的 upper bound 是 pipeline-friendly fallback，不是 paper-native eligibility rule。",
  "time_evidence": "No explicit publication-time restriction in criteria. Applied the review paper's own publication date as the upper bound: 2025-09-14...",
  "extra_note": "這篇與 2409 對照很有意思：一篇 formal no restriction、另一篇 formal silent，但兩者都有實際 corpus 年份範圍。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2509.11446",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2509.11446.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2509.11446.md"
  }
}
```

## E. Retrieval 下界 + repo upper bound 的混合型

這一組在 paper 文本中有 retrieval lower bound，但 final selection 沒有明文 upper bound；repo 因重現性需求補上 upper bound。

### 2511.13936 — Preference-Based Learning in Audio Applications: A Systematic Analysis

```yaml
{
  "title": "Preference-Based Learning in Audio Applications: A Systematic Analysis",
  "publication_display": "2025-11-17 (arXiv v1)",
  "arxiv_initial_submission": "2025-11-17",
  "arxiv_latest_visible_version": null,
  "category": "mixed_retrieval_plus_repo_upper",
  "category_label": "Retrieval 下界 + repo upper bound",
  "paper_native_time_conclusion": "paper 文本明確把 candidate works 限定為 2020 onward；但 final selection rule 本身沒有另寫 upper bound。repo 為重現性加上 upper bound = review 發表日。",
  "normalized_window_or_rule": "start_date = 2020-01-01; repo practical end_date = 2025-11-17",
  "screening_time_notes": [
    "Stage 1 另外對 arXiv-only subset 設 year-wise citation cutoffs：2020>=28, 2021>=22, 2022>=32, 2023>=90, 2024>=13, 2025>=1。",
    "若 keyword change 讓結果多出 >100 篇，作者會抽樣決定保留/刪除該 keyword。",
    "final deterministic gate 是『Preference learning + Audio + Not survey』，不是另一條年份規則。"
  ],
  "repo_caveat": "cutoff_json 明說 upper bound 來自 review paper publication date，屬於 pipeline reproducibility choice。",
  "time_evidence": "2020-stage retrieval is scoped to recent work (2020 onward), and review publication boundary is used as an upper bound: 2025-11-17...",
  "extra_note": "這篇最好不要被簡化成單純的 [2020, 2025-11-17] stage2 window；它其實是 retrieval policy + citation gate + repo upper bound 的組合。",
  "sources": {
    "arxiv_abs": "https://arxiv.org/abs/2511.13936",
    "cutoff_json": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/cutoff_jsons/2511.13936.json",
    "criteria_md": "https://raw.githubusercontent.com/Sologa/NLP_PRISMA_Reviews/master/criteria_mds/2511.13936.md"
  }
}
```

## 結尾備註

1. 這份稽核的核心目的，是把 `paper-native rule` 與 `repo normalization` 分清楚，避免 downstream screening 把兩者混為一談。
2. 若之後要把這份結果直接接到 deterministic screening pipeline，最需要額外人工確認的是：2405.15604、2312.05172、以及所有 `repo_fallback_only` / `mixed_retrieval_plus_repo_upper` 類別。
3. 2409.13738 已納入本次總表，並沿用先前較完整的 direct paper reading 結果。