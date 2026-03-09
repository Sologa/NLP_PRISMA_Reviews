# criteria_jsons 轉換與邏輯規格

本資料夾用來放「可直接被 screening pipeline 使用」的 `criteria.json` 檔案。

本文檔定義兩件事：
1. `criteria.json` 的標準格式與布林邏輯。
2. `criteria_mds/*.md` 轉成 `criteria_jsons/*.json` 的解析規則（目前實作）。

---

## 1) 標準 JSON 格式

建議每個檔案是一個 top-level object，格式如下：

```json
{
  "topic": "Paper title or short topic name",
  "topic_definition": "One-sentence topic definition",
  "summary": "Optional summary",
  "summary_topics": [
    {
      "id": "S1",
      "description": "Topic cluster description"
    }
  ],
  "inclusion_criteria": {
    "required": [
      {
        "criterion": "Must satisfy A",
        "source": "criteria_mds/xxxx.md",
        "topic_ids": ["S1"]
      }
    ],
    "any_of": [
      {
        "label": "At least one option in this group",
        "options": [
          {
            "criterion": "Option 1",
            "source": "criteria_mds/xxxx.md",
            "topic_ids": ["S1"]
          },
          {
            "criterion": "Option 2",
            "source": "criteria_mds/xxxx.md",
            "topic_ids": ["S1"]
          }
        ]
      }
    ]
  },
  "exclusion_criteria": [
    {
      "criterion": "Exclude if B",
      "source": "criteria_mds/xxxx.md",
      "topic_ids": ["S1"]
    }
  ],
  "sources": [
    "criteria_mds/xxxx.md"
  ]
}
```

另外也允許外層包裝：

```json
{
  "structured_payload": {
    "...": "same schema as above"
  }
}
```

---

## 2) 邏輯語意（Screening Decision Semantics）

在 screening 階段，邏輯語意是：

1. `inclusion_criteria.required`
   - 全部都必須成立（AND）。
2. `inclusion_criteria.any_of`
   - 每個 group 內至少一條 option 成立（OR in group）。
   - 若有多個 group，group 之間同時需要成立（AND across groups）。
3. `exclusion_criteria`
   - 任一條成立就排除（OR）。

實務上可寫成：

```text
INCLUDE if:
  all(required) AND all(group_any_true) AND none(exclusion_true)
else EXCLUDE/MAYBE
```

---

## 3) 目前 `criteria_mds -> criteria_jsons` 轉換規則

目前實作在：

- `scripts/screening/prepare_review_smoke_inputs.py`
  - `_parse_criteria_markdown()`
  - `_clean_criterion_line()`
  - `_load_criteria_payload()`

### 3.1 Topic 來源

1. 若 markdown 第一個 `# ` 標題存在，使用該標題當 `topic` 與 `topic_definition`。
2. 否則使用檔名 stem（例如 `2409.13738`）。

### 3.2 區塊辨識

只解析兩個區塊：

1. Inclusion Criteria
2. Exclusion Criteria

判斷規則（大小寫不敏感）：

1. Inclusion header regex：
   - `^(?:#{1,6}\s*)?inclusion criteria\b`
2. Exclusion header regex：
   - `^(?:#{1,6}\s*)?exclusion criteria\b`

### 3.3 條件行辨識

只有符合條件前綴的行會被當成 criterion：

1. Inclusion item regex：
   - `^(?:I\d+[\.:]|\d+[\.)]|[-*])\s*`
2. Exclusion item regex：
   - `^(?:E\d+[\.:]|\d+[\.)]|[-*])\s*`

可接受例子：

1. `I1. ...`
2. `I2: ...`
3. `1. ...`
4. `1) ...`
5. `- ...`
6. `* ...`

### 3.4 清洗規則

每條行會經過以下清洗：

1. 移除前綴 `- ` 或 `* `。
2. 移除前綴 `I<number>.` / `I<number>:`。
3. 移除前綴 `<number>.` / `<number>)`。
4. trim 空白。
5. 若清洗後字串以 `:` 或 `：` 結尾，視為小標題，不納入條件。

### 3.5 區塊終止規則

當進入 inclusion/exclusion 模式後，遇到下列情況會結束當前模式：

1. 新的 `## ...` 且不含 `criteria`。
2. `---` 分隔線。

### 3.6 不會被轉入 JSON 的內容

下列內容目前不會轉進 `criteria.json`：

1. Stage 1 Retrieval Criteria（R1, R2...）。
2. Screening Question Set（Q1, Q2...）。
3. Notes、補充說明、非 item 行敘述文字。

### 3.7 產出結構（目前 parser 的實際輸出）

`_parse_criteria_markdown()` 會產生：

1. `summary_topics` 固定單一 topic id：`S1`。
2. `inclusion_criteria` 目前只產生 `required`。
3. `inclusion_criteria.any_of` 不會自動從 markdown 推斷。
4. `source` 固定寫成該 markdown 相對路徑。

若 inclusion/exclusion 都解析不到，會直接失敗（報錯退出）。

---

## 4) 在 Review Prompt 中如何被看見

review 階段會做以下轉換：

1. 讀入 `criteria.json`（或 `structured_payload`）。
2. 轉成純文字：
   - inclusion = `topic_definition` + `required` + `any_of`（若有）。
   - exclusion = `exclusion_criteria[].criterion`。
3. 交給 LatteReview `TitleAbstractReviewer`。

目前 LatteReview 會把 prompt 做 `clean_text`，因此換行最終會被壓成單行空白分隔。

---

## 5) 轉換命令（單檔與批次）

以下命令可把 `criteria_mds` 轉成 `criteria_jsons`（不依賴 metadata）：

### 5.1 單檔

```bash
python3 - <<'PY'
import json
from pathlib import Path
from scripts.screening.prepare_review_smoke_inputs import _parse_criteria_markdown

src = Path("criteria_mds/2409.13738.md")
dst = Path("criteria_jsons/2409.13738.json")
payload = _parse_criteria_markdown(src)
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[ok] {src} -> {dst}")
PY
```

### 5.2 批次

```bash
python3 - <<'PY'
import json
from pathlib import Path
from scripts.screening.prepare_review_smoke_inputs import _parse_criteria_markdown

src_dir = Path("criteria_mds")
dst_dir = Path("criteria_jsons")
dst_dir.mkdir(parents=True, exist_ok=True)

for src in sorted(src_dir.glob("*.md")):
    if src.name.startswith("README") or src.name.startswith("AGENT_PROMPT"):
        continue
    dst = dst_dir / f"{src.stem}.json"
    payload = _parse_criteria_markdown(src)
    dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] {src} -> {dst}")
PY
```

---

## 6) 建議的人工驗收清單

每次轉換後，建議至少檢查：

1. `topic_definition` 是否是你要的主題句。
2. `required` 是否完整且沒有漏掉關鍵條件。
3. `exclusion_criteria` 是否完整且沒有誤把說明行當條件。
4. `source/topic_ids` 是否正確。
5. 是否有需要手動改成 `any_of` 群組的條件（目前 parser 不自動分組）。

