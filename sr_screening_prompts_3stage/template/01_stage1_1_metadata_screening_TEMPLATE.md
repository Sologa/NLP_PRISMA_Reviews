# Prompt 1 — Stage 1.1（Metadata 可程式化初篩：年份 / long-short）【模板】

> **只用 metadata + Python**  
> 本步驟只做「可程式化」初篩：  
> (1) 發表年份門檻（>= {{MIN_PUBLICATION_YEAR}}）  
> (2) long / short paper（依你的 SR 定義）

```text
- 角色：SR Screening（Stage 1.1 metadata prefilter）單 agent
- 你會收到：`title_abstracts_metadata.jsonl`
- 你的任務：
  1) 解析 publication_year / publication_date，判斷是否 >= {{MIN_PUBLICATION_YEAR}}
  2) 從 metadata 推斷 paper 是否為 short paper（只在有明確 metadata 證據時）
  3) 產出 Stage 1.2（Prompt 3）要用的檔案（供下載）

- 限制（硬性）：
  1) 全程以 `key`（bibkey）作為唯一識別與 join key。禁止用 title 做 join。
  2) 本階段允許寫程式；但只能使用 metadata 檔內資訊；禁止上網查年份/頁數/track。
  3) 本階段不讀 full text；也不允許用 abstract 內容去猜 long/short（只能用結構化 metadata 欄位）。
  4) 無法判定就填 null/unknown，不可猜。

================================================
A. 解析 publication year（>= {{MIN_PUBLICATION_YEAR}}）
================================================
- 優先使用欄位（依序嘗試）：
  1) publication_date / published_date / date
  2) year
  3) 其他明確年份欄位（若存在）
- 支援格式：YYYY / YYYY-MM / YYYY-MM-DD / ISO datetime（取前 10）
- 若完全無法取得年份：publication_year=null，pub_ge_min_year=null

================================================
B. long / short paper（依你的 SR 定義；只在有「明確證據」時判 short）
================================================
請把你的 short paper 判定規則寫清楚（只能用 metadata 欄位）：

- 明確 short 訊號（範例，請自行替換/增減）：
  {{SHORT_PAPER_METADATA_SIGNALS}}

- 若無明確訊號：
  short_paper = null
  short_paper_reason = "no explicit metadata evidence"

================================================
C. Stage 1.1 決策
================================================
- stage1_1_excluded = true 當且僅當：
  - pub_ge_min_year == false
  - 或 short_paper == true（明確 short）
- 其餘：
  - stage1_1_excluded = false
  - eligible_for_stage1_2 = true

================================================
D. 輸出（必須提供下載）
================================================
請用 Python 產出：

1) `stage1_1_metadata_screening.jsonl`（保留原欄位 + 新增以下欄位）
- publication_year / publication_date_parsed
- pub_ge_min_year / pub_ge_min_year_reason
- short_paper / short_paper_reason
- stage1_1_excluded / eligible_for_stage1_2

2) `stage1_1_metadata_screening.csv`

3) `stage1_1_excluded_keys.txt` 與 `stage1_1_eligible_keys.txt`

================================================
E. 回覆文字（summary）
================================================
請回覆：
- 總筆數 N
- pub_ge_min_year=true/false/null 的數量
- short_paper=true/false/null 的數量
- stage1_1_excluded 的數量
- eligible_for_stage1_2 的數量
並提供所有輸出檔案下載連結。
```