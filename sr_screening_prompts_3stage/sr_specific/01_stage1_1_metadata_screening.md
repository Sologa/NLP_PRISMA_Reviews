# Prompt 1 — Stage 1.1（Metadata 可程式化初篩：年份 / long-short）

> **只用 metadata + Python**  
> 本步驟只做「可程式化」初篩：  
> (1) 發表年份門檻（>= 2019）  
> (2) long / short paper（只在有明確 metadata 證據時才判 short；無證據則保守 unknown）

```text
- 角色：SR Screening（Stage 1.1 metadata prefilter）單 agent
- 你會收到：`title_abstracts_metadata.jsonl`（JSONL，一行一筆 paper metadata）
- 你的任務：
  1) 解析每筆的 publication_year / publication_date，判斷是否 >= 2019
  2) 從 metadata 推斷 paper 是否為 short paper（僅限「有明確線索」；禁止臆測）
  3) 產出 Stage 1.2（Prompt 3）要用的清單與檔案（供下載）

- 限制（硬性）：
  1) 全程以 `key`（bibkey）作為唯一識別與 join key。禁止用 title 做 join。
  2) 本階段允許寫程式；但只能使用 metadata 檔內資訊；禁止上網查年份/頁數/track。
  3) 本階段不讀 full text；也不允許用 abstract 內容去猜 long/short（只能用結構化 metadata 欄位）。
  4) 無法判定就填 null/unknown，不可猜。

================================================
A. 解析 publication year（>=2019）
================================================
- 優先使用欄位（依序嘗試）：
  1) publication_date / published_date / date
  2) year
  3) 其他明確年份欄位（若存在）
- 支援格式：YYYY / YYYY-MM / YYYY-MM-DD / ISO datetime（取前 10）
- 若完全無法取得年份：publication_year=null，pub_ge_2019=null

================================================
B. long / short paper（只在有「明確證據」時判 short）
================================================
你只能在 metadata 中找到以下「明確訊號」時，才可判定 short：
- paper_type / track / category / venue_track 明確寫：
  "short paper" / "short" / "poster" / "demo" / "extended abstract"
- 或 pages 欄位存在且明確小於某閾值（若 metadata 有可靠頁數欄位）
  - 注意：若 pages 欄位不可信/缺失/格式混亂 → short_paper=null

若無明確訊號：
- short_paper = null
- short_paper_reason = "no explicit metadata evidence"

================================================
C. Stage 1.1 決策
================================================
- stage1_1_excluded = true 當且僅當：
  - pub_ge_2019 == false  （年份不符）
  - 或 short_paper == true（明確 short）
- 其餘：
  - stage1_1_excluded = false
  - eligible_for_stage1_2 = true

================================================
D. 輸出（必須提供下載）
================================================
請用 Python 產出：

1) `stage1_1_metadata_screening.jsonl`
- 仍為 JSONL（一行一筆）
- 保留原始欄位
- 新增欄位至少包含：
  - key
  - publication_year
  - publication_date_parsed
  - pub_ge_2019
  - pub_ge_2019_reason
  - short_paper (true/false/null)
  - short_paper_reason
  - stage1_1_excluded (true/false)
  - eligible_for_stage1_2 (true/false)

2) `stage1_1_metadata_screening.csv`
- 至少包含：key, title, publication_year, pub_ge_2019, short_paper, stage1_1_excluded, eligible_for_stage1_2

3) `stage1_1_excluded_keys.txt` 與 `stage1_1_eligible_keys.txt`

================================================
E. 回覆文字（summary）
================================================
請在回覆中提供：
- 總筆數 N
- pub_ge_2019=true/false/null 的數量
- short_paper=true/false/null 的數量
- stage1_1_excluded 的數量
- eligible_for_stage1_2 的數量
- key 缺失/重複的數量（列出前 50 個；完整清單另存檔）

最後提供所有輸出檔案下載連結。
```