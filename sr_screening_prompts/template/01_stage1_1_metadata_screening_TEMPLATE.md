# TEMPLATE Prompt 1 — Stage 1.1（Metadata 可程式化初篩：年份 / paper language / long-short）

> **test-time / SR screening（General Template）**  
> 你只會看到：`title_abstracts_metadata.jsonl`。  
> 本 prompt 只做「可程式化判斷」的 prefilter：  
> - 年份門檻：`{{MIN_PUBLICATION_YEAR}}`（例如 2019）  
> - paper 文字語言限制（常見：只納入英文 paper）：`{{PAPER_LANGUAGE_REQUIRED}}`（例如 English；若不限制填 "NONE"）  
> - short/long 或 publication type（若 metadata 有明確線索）：`{{SHORT_PAPER_POLICY}}`

```text
你現在只會收到我上傳的一個檔案：title_abstracts_metadata.jsonl（JSONL，一行一筆 paper metadata）。
請你用 Python 程式處理這個檔案，完成 Stage 1.1（metadata 初篩），並輸出結果檔供我下載。

【硬性要求】
1) 全程以 `key`（bibkey）作為唯一識別與 join key。禁止用 title 做 join。
2) 本階段允許寫程式；但只能使用 metadata 檔內資訊，不准上網查年份/頁數/語言。
3) 不讀 full text。

--------------------------------
A) 年份門檻（可程式化）
--------------------------------
門檻：{{MIN_PUBLICATION_YEAR}}（含）

新增欄位（建議）：
- `publication_year`：int 或 null
- `publication_date_parsed`：ISO YYYY-MM-DD 或 null
- `publication_year_source`："publication_date" / "year_field" / "unknown"
- `year_threshold`：{{MIN_PUBLICATION_YEAR}}
- `pub_ge_year_threshold`：true/false/null
- `pub_ge_year_threshold_reason`：簡短原因

--------------------------------
B) Paper 文字語言限制（常見：只納入英文）
--------------------------------
限制：{{PAPER_LANGUAGE_REQUIRED}}
- 若填 "NONE"：本段落只做偵測、不做排除
- 若填 "English"：非英文 → 直接 Stage1.1 exclude

新增欄位（建議）：
- `paper_language_is_required_language`：true/false/null
- `paper_language_detected`："en"/"zh"/...
- `paper_language_source`："metadata_field" / "langdetect_title_abstract" / "heuristic" / "unknown"
- `paper_language_reason`：簡短說明

偵測規則（可程式化）：
1) metadata 有 language/lang 欄位就用它
2) 否則對 (title+abstract) 做語言偵測（langdetect 或保守 heuristic）
3) 太短/缺失 → null（不要亂猜）

--------------------------------
C) long/short 或 publication type（依 SR 設定）
--------------------------------
政策：{{SHORT_PAPER_POLICY}}
（例如：明確 short paper 直接排除；或不排除 short；或只排除非 peer-reviewed 等）

新增欄位（建議）：
- `paper_length_category`："long"/"short"/"unknown"
- `paper_length_source` / `paper_length_evidence`
- `paper_length_inferred_by_heuristic`：true/false

--------------------------------
D) Stage 1.1 決策（只決定是否進入 Stage 1.2）
--------------------------------
新增欄位：
- `stage1_1_decision`："pass" / "exclude" / "maybe"
- `eligible_for_stage1_2`：true/false
- `stage1_1_reason`：字串陣列

決策規則（請保守、可配置）：
1) 若 pub_ge_year_threshold==false → exclude
2) 若 paper language 限制啟用且 paper_language_is_required_language==false → exclude
3) 依 {{SHORT_PAPER_POLICY}} 判斷是否排除 short（只在有明確證據時排除）
4) 以上都未觸發且關鍵欄位都明確滿足 → pass
5) 其他 → maybe

--------------------------------
【輸出檔案（請提供下載）】
1) stage1_1_metadata_screening.jsonl
2) stage1_1_metadata_screening.csv
3) stage1_1_pass_keys.txt / stage1_1_maybe_keys.txt / stage1_1_exclude_keys.txt

回覆請給 summary（pass/maybe/exclude 分布、年份/語言判定分布）。
```