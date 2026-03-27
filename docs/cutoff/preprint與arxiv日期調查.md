# 其他 SR 的 preprint 接受情況與 arXiv 首版提交日期調查

日期：2026-03-27

## 目的

本文件回答兩個問題：

1. 其他 systematic review（SR）是否接受 preprint，且是否因此引入 `submitted_date` 作為正式時間條件。
2. `refs/<paper>/metadata.json` 與 reference-level metadata 中，來源為 arXiv 的資料是否能取得「第一版提交日期」。

## 結論摘要

### 問題 1：其他 SR 是否接受 preprint，且是否因此新增 `submitted_date`

結論：

- repo 內不同 SR 對 preprint 的態度是 paper-specific，不是全域統一規則。
- 有些 SR 接受或納入 arXiv / 非 peer-reviewed 研究。
- 有些 SR 明確排除 preprint。
- 目前 repo 的 cutoff schema 與 runtime **沒有任何一篇**真正使用 `submitted_date` 或 `date_field: "submitted"`。
- 因此，現況不是「其他 SR 已普遍因接受 preprint 而導入 submitted_date」，而是「不同 paper 各自處理 preprint，但 cutoff 實作仍統一落在 `published` 語義」。

### 問題 2：arXiv 來源 metadata 能否取得第一版提交日期

結論：

- 可以。
- 現有 metadata 抓取來源是 `arxiv_export_api`，會保留 arXiv Atom feed 的 `published` 與 `updated`。
- 在 arXiv 語義下，`published` 對應首次公開提交時間，可作為 first-submission / `submitted_date` 候選值。
- `updated` 對應後續版本更新時間。
- 但目前 pipeline 沒有把這個值正式升格成獨立欄位 `submitted_date`；flatten 後多半只留下粗化後的 `published_date`。

## 問題 1 詳查

### 1.1 其他 SR 是否有接受 preprint

有，但不是每篇都接受。

#### 接受或納入 preprint / arXiv 的例子

`2307.05527`：

- 原文 search strategy 明確擴展到 arXiv。
- 原文指出新增的 440 篇 arXiv 候選中，只有 65% 是 peer reviewed，表示 corpus 明確包含非 peer-reviewed / preprint。
- 原文 eligibility 並使用 `submitted or published` 的時間語義。

證據：

- [2307.05527.pdf](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2307.05527/2307.05527.pdf)
- [2307.05527.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/cutoff_jsons/2307.05527.json#L83)
- [report.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/cutoff_semantic_audit_all16_2026-03-26/report.md#L106)

`2511.13936`：

- current cutoff JSON 中有 `arxiv_only` 的條件化 citation rule，表示 paper 對 arXiv 論文有獨立處理。
- 但這不等於它把 `submitted_date` 納入 cutoff；其 `time_policy.date_field` 仍然是 `published`。

證據：

- [2511.13936.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/cutoff_jsons/2511.13936.json#L34)
- [2511.13936.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/cutoff_jsons/2511.13936.json#L87)

#### 明確排除 preprint 的例子

`2306.12834`：

- cutoff semantic audit 直接摘錄原文：`Research works that were published as a preprint, with preliminary work or without peer review, were excluded.`

證據：

- [report.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/screening/results/cutoff_semantic_audit_all16_2026-03-26/report.md#L99)

### 1.2 其他 SR 是否因此引入 `submitted_date`

結論：**沒有。**

本次檢查結果如下：

- 全部 `cutoff_jsons/*.json` 的 `time_policy.date_field` 仍是 `published`。
- 沒有任何 cutoff JSON 使用 `date_field: "submitted"`。
- repo 內也沒有正式 `submitted_date` 欄位被 current cutoff/runtime 使用。

直接證據：

- [2307.05527.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/cutoff_jsons/2307.05527.json#L52)
- [2409.13738.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/cutoff_jsons/2409.13738.json#L117)
- [2511.13936.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/cutoff_jsons/2511.13936.json#L95)
- [2601.19926.json](/Users/xjp/Desktop/NLP_PRISMA_Reviews/cutoff_jsons/2601.19926.json#L37)

runtime 也沒有真正支援 `submitted`：

- CLI 選項雖然列出 `submitted`，但註解直接寫 `submitted 會映射到 published`。

證據：

- [topic_pipeline.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/scripts/topic_pipeline.py#L131)
- [topic_pipeline.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/screening/vendor/scripts/topic_pipeline.py#L438)

因此，現況應理解為：

- repo 已經遇到某些 paper 接受 preprint 的情境；
- 但尚未在正式 cutoff schema/runtime 中完成 `submitted_date` 的一級支援。

## 問題 2 詳查

### 2.1 `refs/<paper>/metadata.json` 能否取得 arXiv 首版提交日期

可以。

目前各 SR 主 paper 的 `refs/<paper>/metadata.json` 都來自 `arxiv_export_api`，且保留：

- `id`，例如 `http://arxiv.org/abs/2409.13738v1`
- `published`
- `updated`
- `raw_atom_entry`

證據：

- [2307 metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2307.05527/metadata.json#L3)
- [2409 metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2409.13738/metadata.json#L3)
- [2511 metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2511.13936/metadata.json#L3)
- [2601 metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2601.19926/metadata.json#L3)

在 arXiv Atom API 中：

- `published` = 首次提交 / 首次公開時間
- `updated` = 最新版本更新時間

例如：

- `2401.09244v3` 的主 paper metadata 中：
  - `published = 2024-01-17T14:44:27Z`
  - `updated = 2026-02-12T12:17:54Z`

證據：

- [2401 metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2401.09244/metadata.json#L35)

### 2.2 reference-level arXiv metadata 能否取得首版提交日期

也可以。

`scripts/download/collect_title_abstracts_priority.py` 的 arXiv parser 會顯式抓：

- `published`
- `updated`
- `comment`
- `journal_ref`

證據：

- [collect_title_abstracts_priority.py](/Users/xjp/Desktop/NLP_PRISMA_Reviews/scripts/download/collect_title_abstracts_priority.py#L956)

在 `title_abstracts_full_metadata.jsonl` 中，arXiv reference 也保留完整 source metadata。

例 1：`1811.01609v3`

- `published = 2018-11-05T11:02:29Z`
- `updated = 2020-10-06T19:14:50Z`
- `comment` 顯示後續正式刊載資訊

證據：

- [2307 full metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2307.05527/metadata/title_abstracts_full_metadata.jsonl#L85)

例 2：`1802.06006v3`

- `published = 2018-02-14T18:24:41Z`
- `updated = 2018-10-12T06:27:26Z`

證據：

- [2307 full metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2307.05527/metadata/title_abstracts_full_metadata.jsonl#L215)

例 3：`2207.10639v1`

- `published = 2022-07-14T18:56:54Z`
- `updated = 2022-07-14T18:56:54Z`

證據：

- [2401 full metadata](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2401.09244/metadata/title_abstracts_full_metadata.jsonl#L205)

### 2.3 現在真正缺的是什麼

缺的不是「抓不到」。

缺的是：

- current flattened metadata 沒有正式欄位 `submitted_date`
- cutoff runtime 也不會讀 `published`/`updated` 原始 arXiv 時間戳來區分 first submission 與 later revision

目前 flatten 後通常只剩：

- `source = arxiv`
- `source_id = 1802.06006v3`
- `published_date = 2018`

也就是：

- 拿得到精確 first-submission timestamp
- 但 downstream cutoff 只吃粗化後的 `published_date`

證據：

- [2307 metadata rows](/Users/xjp/Desktop/NLP_PRISMA_Reviews/refs/2307.05527/metadata/title_abstracts_metadata.jsonl#L214)

## 最後判定

### 對問題 1 的直接回答

- 其他 SR 有的接受 preprint，有的不接受。
- 這件事是 per-paper 決策，不是 repo 全域規則。
- 目前沒有證據顯示「其他 SR 已經因此正式導入 `submitted_date` 作為 cutoff 時間欄位」。

### 對問題 2 的直接回答

- `refs/<paper>/metadata.json` 與 reference-level arXiv full metadata 都可以取得 arXiv 第一版提交日期。
- 這個值目前存在於 arXiv Atom 的 `published` 欄位。
- 但 repo 目前尚未把它轉成 current cutoff 可直接使用的正式 `submitted_date` 欄位。

## 建議理解方式

如果未來某篇 paper 的 source-faithful criteria 明確要求：

- `submitted or published`

那麼：

- 從資料取得角度，repo 已具備實作條件；
- 從 schema / runtime 角度，repo 目前尚未正式完成這條路徑。

換句話說：

- 資料層可行；
- cutoff 實作層尚未落地。
