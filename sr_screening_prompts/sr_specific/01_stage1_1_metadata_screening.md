# Prompt 1 — Stage 1.1（Metadata 可程式化初篩：年份 / paper language / long-short）

> **test-time / SR screening**  
> 你只會看到：`title_abstracts_metadata.jsonl`（一行一筆）。  
> 你必須用程式，只根據 metadata 做「可程式化判斷」的初篩：  
> (1) 發表年份門檻（>= 2019）  
> (2) paper 類型是否為 short paper（若 metadata 有明確線索）  
> (3) paper 文字語言是否為英文（預設 SR 只納入英文 paper；用 metadata 或對 title+abstract 做語言偵測）

```text
你現在只會收到我上傳的一個檔案：title_abstracts_metadata.jsonl（JSONL，一行一筆 paper metadata）。
請你用 Python 程式處理這個檔案，完成 Stage 1.1（metadata 初篩），並輸出結果檔供我下載。

【硬性要求】
1) 全程以每筆資料中的 `key` 欄位（bibkey）作為唯一識別與 join key。禁止用 title 做 join。
2) 本階段允許寫程式；但只能使用 metadata 檔內資訊，不准上網查年份/頁數/語言。
3) 這一步只做「可程式化」判斷，不讀 full text。
4) 對於無法從 metadata 判定的欄位，一律標記 unknown/null，不可猜測。

--------------------------------
A) 年份判斷（對應 SR 的 I1）
--------------------------------
對每筆新增欄位：
- `publication_year`：int 或 null
- `publication_date_parsed`：ISO YYYY-MM-DD 或 null
- `publication_year_source`："publication_date" / "year_field" / "unknown"
- `pub_ge_2019`：true/false/null
- `pub_ge_2019_reason`：簡短原因（如 "year=2021" / "missing date" / "parse failed: ..."）

解析規則：
- 優先讀 `publication_date`（若存在），支援 YYYY / YYYY-MM / YYYY-MM-DD / 常見日期字串。
- 若 publication_date 不存在或解析失敗，fallback 用 `year` 或其他明確年份欄位。
- 若仍無法取得年份：publication_year=null、pub_ge_2019=null。

--------------------------------
B) long / short paper（有明確證據才排除）
--------------------------------
新增欄位：
- `paper_length_category`："long" / "short" / "unknown"
- `paper_length_source`：例如 "paper_type_field" / "pages_field" / "unknown"
- `paper_length_evidence`：把用到的原 metadata 欄位值原樣抄進來
- `paper_length_inferred_by_heuristic`：true/false（只有用 pages 推算才 true）

判斷規則（保守）：
- 若 metadata 有欄位明確表示 short/long（paper_type/track/submission_type/venue_track 含 "short paper"/"long paper"/"full paper" 等），直接依其判定。
- 若沒有明確類型，但有可解析頁數：
  - 可用保守 heuristic：頁數 <= 4 判 short；頁數 >= 8 判 long；介於 5–7 判 unknown。
  - 並把 paper_length_inferred_by_heuristic=true。
- 若都沒有：unknown。

--------------------------------
C) Paper 文字語言（預設只納入英文 paper）
--------------------------------
新增欄位：
- `paper_language_is_english`：true/false/null
- `paper_language_detected`：例如 "en"/"zh"/"unknown"
- `paper_language_source`："metadata_field" / "langdetect_title_abstract" / "heuristic" / "unknown"
- `paper_language_evidence`：你用來判斷的內容摘要（例如 metadata 的 language 欄位值、或偵測用的文字長度等）
- `paper_language_reason`：簡短說明（如 "metadata language=en" / "langdetect=en" / "too short to detect"）

判斷規則：
1) 若 metadata 本身有欄位 `language/lang/paper_language`（或類似）且值明確：
   - en/English → true
   - zh/Chinese/… → false
2) 否則，對 (title + abstract) 做語言偵測：
   - 優先使用語言偵測套件（如 langdetect / fasttext 若環境可用）
   - 若套件不可用：用保守 heuristic（例如：非拉丁字元比例很高 → 非英文；或包含大量中文/日文/韓文範圍字元 → 非英文）
3) 若 title+abstract 太短/缺失導致無法判定 → paper_language_is_english=null（不要亂猜）

--------------------------------
D) Stage 1.1 決策（只決定是否進入 Stage 1.2）
--------------------------------
新增欄位：
- `stage1_1_decision`："pass" / "exclude" / "maybe"
- `stage1_1_reason`：字串陣列（列出造成 pass/exclude/maybe 的原因）
- `eligible_for_stage1_2`：true/false

決策硬規則（請照順序套用）：
1) 若 pub_ge_2019 == false → exclude
2) 若 paper_language_is_english == false → exclude
3) 若 paper_length_category == "short" 且「有明確類型證據」（不是純 heuristic 推斷）→ exclude
4) 若以上都未觸發 exclude，且 pub_ge_2019==true 且 paper_language_is_english==true 且 paper_length_category!="short" → pass
5) 其他（任何關鍵欄位為 null/unknown、或 paper_length 只有 heuristic 推斷）→ maybe

注意：
- Stage 1.1 的 exclude 只表示「不進入下一輪」，不代表你已完整看過 paper 內容。
- 任何缺 abstract 或語言判不出來的，請用 maybe，不要直接 exclude（避免誤殺）。

--------------------------------
【輸出檔案（請提供下載）】
1) JSONL：`stage1_1_metadata_screening.jsonl`（保留原欄位 + 新增欄位，維持原順序）
2) CSV：`stage1_1_metadata_screening.csv`
   - 至少包含：key, title, publication_year, pub_ge_2019, paper_language_is_english, paper_length_category, stage1_1_decision, stage1_1_reason
3) key 清單：
   - `stage1_1_pass_keys.txt`
   - `stage1_1_maybe_keys.txt`
   - `stage1_1_exclude_keys.txt`
4) 若有 invalid/missing key：
   - `stage1_1_key_issues.csv`（列出行號、原始資料、問題描述）

【回覆中請給 summary】
- 總筆數
- pass/maybe/exclude 各多少
- pub_ge_2019=true/false/null 各多少
- paper_language_is_english=true/false/null 各多少
- paper_length_category=long/short/unknown 各多少
並提供所有輸出檔案下載連結。
```