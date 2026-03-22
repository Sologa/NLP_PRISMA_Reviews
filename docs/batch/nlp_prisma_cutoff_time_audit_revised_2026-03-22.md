# NLP_PRISMA_Reviews `cutoff_jsons/` 稽核與修正版建議（2026-03-22）

## 1. 本次修正版的核心結論

這一版修正的重點不是重新判 paper 有沒有時間限制，而是先把 `cutoff_jsons/` 在 pipeline 中的**角色**釐清，再回頭檢查每個 JSON 是否把這個角色寫對。

依 `cutoff_jsons/README.md`，這個資料夾的用途有兩個：

1. 把 `criteria_mds/*.md` 裡的時間條件獨立出來，和主題/方法條件分流。
2. 讓時間過濾可 deterministic 執行，不交由 agent 主觀判斷。

同一份 README 也明寫：

1. `Stage 2 Screening Criteria` 優先。
2. 只有在 `Stage 2` 沒有時間條件時，`Stage 1 Retrieval Criteria` 才能作為 fallback。
3. 現階段程式**尚未直接讀** `cutoff_jsons/*.json`；建議流程是先人工驗收，再把 `start_date/end_date` 映射到執行參數或 workspace cutoff artifact。

所以 `cutoff_jsons` 最好拆成兩個層次來理解：

1. **source-faithful**：只記錄 paper 原文真的支持的時間規則。
2. **operational**：為了今天重跑 live retrieval / screening pipeline 而額外補的 snapshot date、publication-date cap、workspace cutoff。

前一版報告的問題，就是把這兩層混在一起。

## 2. 對 2409.13738 的直接回答

### 問題

你問的重點是：

`2409.13738` 裡面，`search 在 2023 年 6 月執行`、以及 `2024 年 8 月之後的出版物不會被納入`，是不是**復現 screening 必要流程**之一？

### 精確答案

**不是 source-faithful screening 必要條件。**

更精確地說：

1. 這篇 paper 的 `IC.1` 明寫 **there was no restriction on time period**，所以 source-faithful 的 `cutoff_json` 應維持 `enabled = false`。
2. `Our search queries were executed in June 2023` 是 **retrieval 的執行時間**，不是 inclusion/exclusion criterion。
3. `publications after the preparation of this manuscript (August 2024) will also not be included` 是 **limitations / provenance**，不是 screening 規則。

若今天真的要重跑 pipeline，`June 2023` 可以另外存成 `operational.retrieval_snapshot_date`；但它不應回寫成 source-faithful `time_policy.end_date`。

而 `August 2024` 更不適合當 screening cutoff：它晚於真正的 search time，只能當 manuscript preparation provenance。

## 3. 總覽：16 個 `cutoff_jsons/*.json` 的修正建議

| 類別 | 件數 | 說明 |
|---|---:|---|
| 可直接保留（source-faithful） | 5 |  |
| 可保留但需加 provenance/補充條件 | 3 |  |
| 需改標為 Stage 1 retrieval fallback | 4 |  |
| 需移除人工 publication-date fallback | 3 |  |
| 需拆成 source-faithful 與 operational 兩部分 | 1 |  |

### 3.1 建議用的新語義

建議把原本單一 `time_policy` 的意義拆成：

```json
{
  "paper_id": "2409.13738",
  "source_md": "criteria_corrected_3papers/2409.13738.md",
  "source_faithful": {
    "policy_status": "explicit_window | explicit_no_restriction | stage1_retrieval_fallback | not_stated",
    "time_policy": {
      "enabled": false,
      "date_field": "published",
      "start_date": null,
      "start_inclusive": true,
      "end_date": null,
      "end_inclusive": false,
      "timezone": "UTC"
    }
  },
  "operational": {
    "retrieval_snapshot_date": "2023-06",
    "time_policy": null
  },
  "evidence": [
    {
      "section": "Stage 2 Eligibility / Screening Criteria",
      "criterion_id": "I8",
      "text": "No publication-year restriction."
    },
    {
      "section": "Methods/Results provenance",
      "criterion_id": "N/A",
      "text": "Search queries executed in June 2023."
    }
  ],
  "normalization_notes": [
    "search execution date is provenance for deterministic reruns, not a source-faithful screening cutoff"
  ]
}
```

關鍵是新增：

1. `source_faithful.policy_status`：區分 `explicit_window`、`explicit_no_restriction`、`stage1_retrieval_fallback`、`not_stated`。
2. `operational.retrieval_snapshot_date` / `operational.time_policy`：用來放今天重跑 pipeline 時額外需要的 deterministic 邊界。
3. 對 `2312.05172`、`2511.13936` 這類有時間相依的次級規則，再補 `secondary_filters` 或等價欄位。

## 4. 每個檔案應如何修正

### 4.1 `2303.13365.json`

**Current class**: `explicit_stage2_window`

**Current policy**: 2012-01-01 ≤ published ≤ 2022-03-31

**Source files**: `cutoff_jsons/2303.13365.json` ← `criteria_mds/2303.13365.md`

**Key evidence**: Stage 2 I1: “Published between January 2012 and March 2022.”

**Source-faithful fix**: 實質不需改動；保留現有 time_policy。

**Operational fix**: 可選地補一個 provenance 欄位，例如 policy_origin = stage2_inclusion。

**Reason**: evidence.text 直接支持 time_policy，符合 cutoff_jsons/README 的標準語意。

**Note**: 屬於乾淨的 Stage 2 明文時間限制。

### 4.2 `2306.12834.json`

**Current class**: `stage1_retrieval_fallback`

**Current policy**: 2016-01-01 ≤ published ≤ 2022-12-31

**Source files**: `cutoff_jsons/2306.12834.json` ← `criteria_mds/2306.12834.md`

**Key evidence**: Stage 1 R1: “Search period: 2016–2022.”; Stage 2 has no time rule.

**Source-faithful fix**: 不要再把它表述成『paper 的 screening 年份限制』；改標為 stage1_retrieval_fallback，或移到 source_faithful.retrieval_time_policy。

**Operational fix**: 若 pipeline 需要 deterministic candidate retrieval，可保留 2016–2022，但 applies_to 應標為 candidate_retrieval。

**Reason**: README 明示 Stage 2 優先，Stage 1 只能在 Stage 2 無時間條件時作 fallback；因此它可用，但語義上不是最終 screening rule。

**Note**: 日期本身可用；問題在於 provenance 標記不足。

### 4.3 `2307.05527.json`

**Current class**: `explicit_stage2_window`

**Current policy**: 2018-02-01 ≤ published ≤ 2023-02-01

**Source files**: `cutoff_jsons/2307.05527.json` ← `criteria_corrected_3papers/2307.05527.md`

**Key evidence**: Stage 2 I5: “Temporal window: submitted/published within 2018-02-01 to 2023-02-01.”

**Source-faithful fix**: 實質不需改動；保留現有 time_policy。

**Operational fix**: 可補 policy_origin = stage2_inclusion；Stage 1 同窗格可留在 notes。

**Reason**: Stage 2 與 Stage 1 都支持同一窗口，現有 JSON 基本正確。

**Note**: 這是最標準的 source-faithful cutoff。

### 4.4 `2310.07264.json`

**Current class**: `manual_metadata_fallback`

**Current policy**: published ≤ 2023-10-11 (from review publication date)

**Source files**: `cutoff_jsons/2310.07264.json` ← `criteria_mds/2310.07264.md`

**Key evidence**: criteria_mds 明寫 publication time: “None explicitly stated.”；現有 JSON 用 review publication date 當 upper bound。

**Source-faithful fix**: 把 source-faithful cutoff 改成 not_stated（或 time_policy = null），不要再用 metadata 人工補 end_date。

**Operational fix**: 若 pipeline 真要 live rerun 時加保守上界，應放到獨立 operational artifact，而不是 source-faithful cutoff_json。

**Reason**: 目前 evidence.text 無法逐字支持 enabled=true 與 end_date；這違反 README 的驗收原則。

**Note**: 這類 case 最需要 schema 增補『not_stated』，不能硬塞成 enabled=true。

### 4.5 `2312.05172.json`

**Current class**: `explicit_stage2_window_but_incomplete`

**Current policy**: 2000-01-01 ≤ published ≤ 2025-12-31

**Source files**: `cutoff_jsons/2312.05172.json` ← `criteria_mds/2312.05172.md`

**Key evidence**: Stage 2 I1: “Publication date between 2000 and 2025.”; Stage 2 E4: pre-2017 papers with <10 citations are excluded.

**Source-faithful fix**: 保留主 time_policy，但需補一個 secondary conditional rule，表達 E4 的『時間 + citation』聯合排除。

**Operational fix**: 若要重建 retrieval，Stage 1 的『first 300 / 30 records』應另存為 retrieval controls，不該塞進 time_policy。

**Reason**: 現有 JSON 只保留主時間窗，遺漏了時間相關的次級排除條件，因此對 deterministic screening 來說不完整。

**Note**: 建議擴充 schema：secondary_filters / conditional_filters。

### 4.6 `2401.09244.json`

**Current class**: `manual_metadata_fallback`

**Current policy**: published ≤ 2024-01-17 (from review publication date)

**Source files**: `cutoff_jsons/2401.09244.json` ← `criteria_mds/2401.09244.md`

**Key evidence**: Stage 1 R1: “Search conducted on July 29, 2023.”; Stage 2 has no publication-time rule.

**Source-faithful fix**: source-faithful 應改成 not_stated / null，不要用 2024-01-17 當 screening cutoff。

**Operational fix**: 若要 deterministic rerun，優先用 retrieval_snapshot_date = 2023-07-29，而不是 review publication date。

**Reason**: search conducted on 某日是 retrieval provenance，不是 paper 作者寫的 screening 年份限制；但它比 publication date 更接近 candidate-set snapshot。

**Note**: 這是『search date ≠ screening cutoff』的典型例子。

### 4.7 `2405.15604.json`

**Current class**: `explicit_stage2_window_analysis_scope`

**Current policy**: 2017-01-01 ≤ published ≤ 2023-12-31

**Source files**: `cutoff_jsons/2405.15604.json` ← `criteria_mds/2405.15604.md`

**Key evidence**: Stage 2 I1: “Manually assessed candidate works are within years 2017 to 2023.”

**Source-faithful fix**: 日期可保留，但建議加 provenance 註記：這更像 manual-assessment / analysis-set scope，而非抽象的 topic-level inclusion axiom。

**Operational fix**: Stage 1 citation / influential-citation sampling 規則應另存，不應混入 cutoff_json 的 time_policy。

**Reason**: 目前 time range 大致合理，但語意上應避免被讀成『paper 寫了絕對的 publication-year exclusion clause』。

**Note**: 屬於可用但應加語意標籤的 case。

### 4.8 `2407.17844.json`

**Current class**: `stage1_retrieval_fallback`

**Current policy**: published ≥ 2020-01-01

**Source files**: `cutoff_jsons/2407.17844.json` ← `criteria_mds/2407.17844.md`

**Key evidence**: Stage 1 R5: “Year filter: 2020 onwards.”; Stage 2 has no time rule.

**Source-faithful fix**: 保留為 retrieval_fallback 或移到 operational/retrieval scope；不要表述成 paper screening cutoff。

**Operational fix**: 若 pipeline 需要 candidate-space reproduction，可維持 open-ended lower bound published ≥ 2020。

**Reason**: 它是檢索年限，不是最終 eligibility rule。

**Note**: 與 2306、2507.18910、2601.19926 同類。

### 4.9 `2409.13738.json`

**Current class**: `explicit_no_restriction`

**Current policy**: enabled = false (no publication-year restriction)

**Source files**: `cutoff_jsons/2409.13738.json` ← `criteria_corrected_3papers/2409.13738.md`

**Key evidence**: Paper IC.1: “there was no restriction on time period”; corrected criteria I8: “No publication-year restriction.”

**Source-faithful fix**: 維持現狀，不應改成有 end_date 的 time_policy。

**Operational fix**: 若要今日 live rerun 仍接近原 candidate set，可另外存 retrieval_snapshot_date ≈ 2023-06；August 2024 只能算 manuscript provenance，不應當 cutoff。

**Reason**: June 2023 是 search execution timing；August 2024 是 limitation/provenance；兩者都不是 source-faithful screening rule。

**Note**: 這正是 source-faithful 與 operational 必須拆開的案例。

### 4.10 `2503.04799.json`

**Current class**: `explicit_stage2_window`

**Current policy**: 2016-01-01 ≤ published ≤ 2024-12-31

**Source files**: `cutoff_jsons/2503.04799.json` ← `criteria_mds/2503.04799.md`

**Key evidence**: Stage 2 I2: “Published between 2016 and 2024.”

**Source-faithful fix**: 實質不需改動；保留現有 time_policy。

**Operational fix**: 可補 provenance 欄位，標示 stage2_inclusion。

**Reason**: Stage 2 明文支持，屬乾淨 case。

### 4.11 `2507.07741.json`

**Current class**: `explicit_stage2_window_analysis_scope`

**Current policy**: 2018-01-01 ≤ published ≤ 2024-12-31

**Source files**: `cutoff_jsons/2507.07741.json` ← `criteria_mds/2507.07741.md`

**Key evidence**: Stage 2 I3: “Analysis set focuses on papers published between 2018 and 2024.”; Stage 1 R3 retrieved 2014 to 2025-02-27.

**Source-faithful fix**: 保留 Stage 2 2018–2024 作 final analysis-set window，但加 provenance：policy_origin = stage2_analysis_scope。

**Operational fix**: 若 pipeline 要復現 candidate retrieval，另存 Stage 1 的 2014-01-01 至 2025-02-27。

**Reason**: 目前 JSON 選 Stage 2 沒錯，但應清楚區分 final analysis scope 與 initial retrieval window。

**Note**: 這類 case 在報告裡不能只說『paper 有時間限制』，必須說明是 final analysis set。

### 4.12 `2507.18910.json`

**Current class**: `stage1_retrieval_fallback`

**Current policy**: 2017-01-01 ≤ published ≤ 2025-06-30

**Source files**: `cutoff_jsons/2507.18910.json` ← `criteria_mds/2507.18910.md`

**Key evidence**: Stage 1 R6: “documents published from 2017 up to the end of mid 2025.”; Stage 2 has no time rule.

**Source-faithful fix**: 改標為 stage1_retrieval_fallback / candidate_retrieval，不要表述成 screening time limit。

**Operational fix**: 若 pipeline 要做 deterministic retrieval，可保留此 window；mid-2025 → 2025-06-30 的 normalization 可以保留。

**Reason**: 這是合理的檢索覆蓋範圍，但不是 paper 作者的 final eligibility year rule。

**Note**: 此 review 還納入 preprints/industry white papers，更說明 time window 屬 search coverage。

### 4.13 `2509.11446.json`

**Current class**: `manual_metadata_fallback`

**Current policy**: published ≤ 2025-09-14 (from review publication date)

**Source files**: `cutoff_jsons/2509.11446.json` ← `criteria_mds/2509.11446.md`

**Key evidence**: criteria_mds 明寫 publication time: none explicitly stated; current JSON injects review publication date as upper bound.

**Source-faithful fix**: 把 source-faithful 狀態改成 not_stated / null，移除 manual publication-date upper bound。

**Operational fix**: 若之後真的要 operational cap，應獨立存放，且優先找 search snapshot / database export 時間，而不是直接用 review publication date。

**Reason**: 目前 evidence 無法支持 enabled=true；與 README 的 evidence-based 規範不相容。

**Note**: 與 2310、2401 同類。

### 4.14 `2510.01145.json`

**Current class**: `explicit_stage2_window`

**Current policy**: 2020-01-01 ≤ published ≤ 2025-07-31

**Source files**: `cutoff_jsons/2510.01145.json` ← `criteria_mds/2510.01145.md`

**Key evidence**: Stage 2 I2: “Published between January 2020 and July 2025.”

**Source-faithful fix**: 實質不需改動；保留現有 time_policy。

**Operational fix**: 可補 provenance = stage2_inclusion；Stage 1 同窗格留在 notes 即可。

**Reason**: 是直接的 Stage 2 明文時間窗。

### 4.15 `2511.13936.json`

**Current class**: `mixed_stage1_plus_manual_upper_bound`

**Current policy**: start = 2020-01-01 (retrieval scope); end = 2025-11-17 (manual review publication date)

**Source files**: `cutoff_jsons/2511.13936.json` ← `criteria_mds/2511.13936.md`

**Key evidence**: Stage 1 R3: “Candidate works are restricted to publication years 2020 onward.”; no explicit Stage 2 upper bound; arXiv subset has year-wise citation gates.

**Source-faithful fix**: 拆成兩部分：保留 lower bound 2020 onward 但標為 stage1_retrieval_fallback；移除 manual end_date = 2025-11-17。

**Operational fix**: 若需要 operational end cap，單獨存為 operational_cutoff.end_date；另外應補 arXiv year-wise citation cutoffs 作 secondary conditional filter。

**Reason**: 現有 JSON 把 source-backed lower bound 和人工注入 upper bound 混在一起，且遺漏 citation-dependent gate。

**Note**: 這篇與 2409 一樣，很適合 source-faithful vs operational 雙軌表示。

### 4.16 `2601.19926.json`

**Current class**: `stage1_retrieval_fallback`

**Current policy**: published ≤ 2025-07-31

**Source files**: `cutoff_jsons/2601.19926.json` ← `criteria_corrected_3papers/2601.19926.md`

**Key evidence**: Corrected criteria explicitly say R1 cut-off date is a Stage 1 retrieval / candidate-identification rule, not eligibility screening.

**Source-faithful fix**: 保留日期但一定要改 provenance：stage1_retrieval_fallback / candidate_identification；不要再稱為 screening cutoff。

**Operational fix**: 若 pipeline 需要 deterministic candidate retrieval，可保留 published ≤ 2025-07-31。

**Reason**: source_md 已明確說這是 retrieval rule；目前 JSON 雖可用，但語義過度強化。

**Note**: 這是 repo 自己 corrected criteria 已經把 retrieval/screening 分開寫清楚的案例。

## 5. 我對前一版報告的修正

前一版最大的問題，是把以下三種東西一起叫作「時間限制」：

1. paper 原文真的寫出的 Stage 2 screening time rule；
2. 只有 Stage 1 retrieval 才有的 search window；
3. 為了今天重跑 pipeline 才人工補上的 operational upper bound。

這一版改成：

1. 先判定每一個 JSON 應歸於哪一層。
2. 再決定是否保留日期本身。
3. 最後才說它能不能用於 deterministic rerun。

因此，這一版不再把 `2409.13738` 的 `June 2023` 或 `August 2024` 說成 paper 本身的 screening cutoff。

## 6. 建議的 repo-level 修補策略

### 6.1 最小修補

1. 保留現有檔名不變。
2. 在每個 JSON 新增 `policy_origin` / `policy_status` / `applies_to`。
3. 禁止把 `review publication date` 直接寫回 `time_policy.end_date`，除非 evidence 有逐字支持。

### 6.2 較乾淨的修補

1. `cutoff_jsons/` 只放 source-faithful。
2. 另建 `operational_cutoffs/` 或 workspace-level artifact 存 rerun snapshot。
3. 對 `not_stated` 與 `secondary_filters` 做 schema 擴充。

### 6.3 為什麼這樣比較好

1. 不會把 paper 原文沒寫的規則誤包裝成 source evidence。
2. 又能保留今天重跑 pipeline 時所需的 deterministic 邊界。
3. `2409.13738` 和 `2511.13936` 這兩個最容易混淆的 case，會自然變清楚。

## 7. Machine-readable appendix

```json
[
  {
    "paper_id": "2303.13365",
    "status": "keep",
    "current_class": "explicit_stage2_window",
    "current_policy": "2012-01-01 ≤ published ≤ 2022-03-31",
    "source_path": "criteria_mds/2303.13365.md",
    "json_path": "cutoff_jsons/2303.13365.json",
    "source_faithful_fix": "實質不需改動；保留現有 time_policy。",
    "operational_fix": "可選地補一個 provenance 欄位，例如 policy_origin = stage2_inclusion。",
    "reason": "evidence.text 直接支持 time_policy，符合 cutoff_jsons/README 的標準語意。",
    "notes": "屬於乾淨的 Stage 2 明文時間限制。"
  },
  {
    "paper_id": "2306.12834",
    "status": "relabel_stage1",
    "current_class": "stage1_retrieval_fallback",
    "current_policy": "2016-01-01 ≤ published ≤ 2022-12-31",
    "source_path": "criteria_mds/2306.12834.md",
    "json_path": "cutoff_jsons/2306.12834.json",
    "source_faithful_fix": "不要再把它表述成『paper 的 screening 年份限制』；改標為 stage1_retrieval_fallback，或移到 source_faithful.retrieval_time_policy。",
    "operational_fix": "若 pipeline 需要 deterministic candidate retrieval，可保留 2016–2022，但 applies_to 應標為 candidate_retrieval。",
    "reason": "README 明示 Stage 2 優先，Stage 1 只能在 Stage 2 無時間條件時作 fallback；因此它可用，但語義上不是最終 screening rule。",
    "notes": "日期本身可用；問題在於 provenance 標記不足。"
  },
  {
    "paper_id": "2307.05527",
    "status": "keep",
    "current_class": "explicit_stage2_window",
    "current_policy": "2018-02-01 ≤ published ≤ 2023-02-01",
    "source_path": "criteria_corrected_3papers/2307.05527.md",
    "json_path": "cutoff_jsons/2307.05527.json",
    "source_faithful_fix": "實質不需改動；保留現有 time_policy。",
    "operational_fix": "可補 policy_origin = stage2_inclusion；Stage 1 同窗格可留在 notes。",
    "reason": "Stage 2 與 Stage 1 都支持同一窗口，現有 JSON 基本正確。",
    "notes": "這是最標準的 source-faithful cutoff。"
  },
  {
    "paper_id": "2310.07264",
    "status": "remove_manual",
    "current_class": "manual_metadata_fallback",
    "current_policy": "published ≤ 2023-10-11 (from review publication date)",
    "source_path": "criteria_mds/2310.07264.md",
    "json_path": "cutoff_jsons/2310.07264.json",
    "source_faithful_fix": "把 source-faithful cutoff 改成 not_stated（或 time_policy = null），不要再用 metadata 人工補 end_date。",
    "operational_fix": "若 pipeline 真要 live rerun 時加保守上界，應放到獨立 operational artifact，而不是 source-faithful cutoff_json。",
    "reason": "目前 evidence.text 無法逐字支持 enabled=true 與 end_date；這違反 README 的驗收原則。",
    "notes": "這類 case 最需要 schema 增補『not_stated』，不能硬塞成 enabled=true。"
  },
  {
    "paper_id": "2312.05172",
    "status": "augment_secondary",
    "current_class": "explicit_stage2_window_but_incomplete",
    "current_policy": "2000-01-01 ≤ published ≤ 2025-12-31",
    "source_path": "criteria_mds/2312.05172.md",
    "json_path": "cutoff_jsons/2312.05172.json",
    "source_faithful_fix": "保留主 time_policy，但需補一個 secondary conditional rule，表達 E4 的『時間 + citation』聯合排除。",
    "operational_fix": "若要重建 retrieval，Stage 1 的『first 300 / 30 records』應另存為 retrieval controls，不該塞進 time_policy。",
    "reason": "現有 JSON 只保留主時間窗，遺漏了時間相關的次級排除條件，因此對 deterministic screening 來說不完整。",
    "notes": "建議擴充 schema：secondary_filters / conditional_filters。"
  },
  {
    "paper_id": "2401.09244",
    "status": "remove_manual_use_search_date",
    "current_class": "manual_metadata_fallback",
    "current_policy": "published ≤ 2024-01-17 (from review publication date)",
    "source_path": "criteria_mds/2401.09244.md",
    "json_path": "cutoff_jsons/2401.09244.json",
    "source_faithful_fix": "source-faithful 應改成 not_stated / null，不要用 2024-01-17 當 screening cutoff。",
    "operational_fix": "若要 deterministic rerun，優先用 retrieval_snapshot_date = 2023-07-29，而不是 review publication date。",
    "reason": "search conducted on 某日是 retrieval provenance，不是 paper 作者寫的 screening 年份限制；但它比 publication date 更接近 candidate-set snapshot。",
    "notes": "這是『search date ≠ screening cutoff』的典型例子。"
  },
  {
    "paper_id": "2405.15604",
    "status": "keep_with_provenance_note",
    "current_class": "explicit_stage2_window_analysis_scope",
    "current_policy": "2017-01-01 ≤ published ≤ 2023-12-31",
    "source_path": "criteria_mds/2405.15604.md",
    "json_path": "cutoff_jsons/2405.15604.json",
    "source_faithful_fix": "日期可保留，但建議加 provenance 註記：這更像 manual-assessment / analysis-set scope，而非抽象的 topic-level inclusion axiom。",
    "operational_fix": "Stage 1 citation / influential-citation sampling 規則應另存，不應混入 cutoff_json 的 time_policy。",
    "reason": "目前 time range 大致合理，但語意上應避免被讀成『paper 寫了絕對的 publication-year exclusion clause』。",
    "notes": "屬於可用但應加語意標籤的 case。"
  },
  {
    "paper_id": "2407.17844",
    "status": "relabel_stage1",
    "current_class": "stage1_retrieval_fallback",
    "current_policy": "published ≥ 2020-01-01",
    "source_path": "criteria_mds/2407.17844.md",
    "json_path": "cutoff_jsons/2407.17844.json",
    "source_faithful_fix": "保留為 retrieval_fallback 或移到 operational/retrieval scope；不要表述成 paper screening cutoff。",
    "operational_fix": "若 pipeline 需要 candidate-space reproduction，可維持 open-ended lower bound published ≥ 2020。",
    "reason": "它是檢索年限，不是最終 eligibility rule。",
    "notes": "與 2306、2507.18910、2601.19926 同類。"
  },
  {
    "paper_id": "2409.13738",
    "status": "keep_no_restriction",
    "current_class": "explicit_no_restriction",
    "current_policy": "enabled = false (no publication-year restriction)",
    "source_path": "criteria_corrected_3papers/2409.13738.md",
    "json_path": "cutoff_jsons/2409.13738.json",
    "source_faithful_fix": "維持現狀，不應改成有 end_date 的 time_policy。",
    "operational_fix": "若要今日 live rerun 仍接近原 candidate set，可另外存 retrieval_snapshot_date ≈ 2023-06；August 2024 只能算 manuscript provenance，不應當 cutoff。",
    "reason": "June 2023 是 search execution timing；August 2024 是 limitation/provenance；兩者都不是 source-faithful screening rule。",
    "notes": "這正是 source-faithful 與 operational 必須拆開的案例。"
  },
  {
    "paper_id": "2503.04799",
    "status": "keep",
    "current_class": "explicit_stage2_window",
    "current_policy": "2016-01-01 ≤ published ≤ 2024-12-31",
    "source_path": "criteria_mds/2503.04799.md",
    "json_path": "cutoff_jsons/2503.04799.json",
    "source_faithful_fix": "實質不需改動；保留現有 time_policy。",
    "operational_fix": "可補 provenance 欄位，標示 stage2_inclusion。",
    "reason": "Stage 2 明文支持，屬乾淨 case。",
    "notes": ""
  },
  {
    "paper_id": "2507.07741",
    "status": "keep_with_provenance_note",
    "current_class": "explicit_stage2_window_analysis_scope",
    "current_policy": "2018-01-01 ≤ published ≤ 2024-12-31",
    "source_path": "criteria_mds/2507.07741.md",
    "json_path": "cutoff_jsons/2507.07741.json",
    "source_faithful_fix": "保留 Stage 2 2018–2024 作 final analysis-set window，但加 provenance：policy_origin = stage2_analysis_scope。",
    "operational_fix": "若 pipeline 要復現 candidate retrieval，另存 Stage 1 的 2014-01-01 至 2025-02-27。",
    "reason": "目前 JSON 選 Stage 2 沒錯，但應清楚區分 final analysis scope 與 initial retrieval window。",
    "notes": "這類 case 在報告裡不能只說『paper 有時間限制』，必須說明是 final analysis set。"
  },
  {
    "paper_id": "2507.18910",
    "status": "relabel_stage1",
    "current_class": "stage1_retrieval_fallback",
    "current_policy": "2017-01-01 ≤ published ≤ 2025-06-30",
    "source_path": "criteria_mds/2507.18910.md",
    "json_path": "cutoff_jsons/2507.18910.json",
    "source_faithful_fix": "改標為 stage1_retrieval_fallback / candidate_retrieval，不要表述成 screening time limit。",
    "operational_fix": "若 pipeline 要做 deterministic retrieval，可保留此 window；mid-2025 → 2025-06-30 的 normalization 可以保留。",
    "reason": "這是合理的檢索覆蓋範圍，但不是 paper 作者的 final eligibility year rule。",
    "notes": "此 review 還納入 preprints/industry white papers，更說明 time window 屬 search coverage。"
  },
  {
    "paper_id": "2509.11446",
    "status": "remove_manual",
    "current_class": "manual_metadata_fallback",
    "current_policy": "published ≤ 2025-09-14 (from review publication date)",
    "source_path": "criteria_mds/2509.11446.md",
    "json_path": "cutoff_jsons/2509.11446.json",
    "source_faithful_fix": "把 source-faithful 狀態改成 not_stated / null，移除 manual publication-date upper bound。",
    "operational_fix": "若之後真的要 operational cap，應獨立存放，且優先找 search snapshot / database export 時間，而不是直接用 review publication date。",
    "reason": "目前 evidence 無法支持 enabled=true；與 README 的 evidence-based 規範不相容。",
    "notes": "與 2310、2401 同類。"
  },
  {
    "paper_id": "2510.01145",
    "status": "keep",
    "current_class": "explicit_stage2_window",
    "current_policy": "2020-01-01 ≤ published ≤ 2025-07-31",
    "source_path": "criteria_mds/2510.01145.md",
    "json_path": "cutoff_jsons/2510.01145.json",
    "source_faithful_fix": "實質不需改動；保留現有 time_policy。",
    "operational_fix": "可補 provenance = stage2_inclusion；Stage 1 同窗格留在 notes 即可。",
    "reason": "是直接的 Stage 2 明文時間窗。",
    "notes": ""
  },
  {
    "paper_id": "2511.13936",
    "status": "split_mixed",
    "current_class": "mixed_stage1_plus_manual_upper_bound",
    "current_policy": "start = 2020-01-01 (retrieval scope); end = 2025-11-17 (manual review publication date)",
    "source_path": "criteria_mds/2511.13936.md",
    "json_path": "cutoff_jsons/2511.13936.json",
    "source_faithful_fix": "拆成兩部分：保留 lower bound 2020 onward 但標為 stage1_retrieval_fallback；移除 manual end_date = 2025-11-17。",
    "operational_fix": "若需要 operational end cap，單獨存為 operational_cutoff.end_date；另外應補 arXiv year-wise citation cutoffs 作 secondary conditional filter。",
    "reason": "現有 JSON 把 source-backed lower bound 和人工注入 upper bound 混在一起，且遺漏 citation-dependent gate。",
    "notes": "這篇與 2409 一樣，很適合 source-faithful vs operational 雙軌表示。"
  },
  {
    "paper_id": "2601.19926",
    "status": "relabel_stage1",
    "current_class": "stage1_retrieval_fallback",
    "current_policy": "published ≤ 2025-07-31",
    "source_path": "criteria_corrected_3papers/2601.19926.md",
    "json_path": "cutoff_jsons/2601.19926.json",
    "source_faithful_fix": "保留日期但一定要改 provenance：stage1_retrieval_fallback / candidate_identification；不要再稱為 screening cutoff。",
    "operational_fix": "若 pipeline 需要 deterministic candidate retrieval，可保留 published ≤ 2025-07-31。",
    "reason": "source_md 已明確說這是 retrieval rule；目前 JSON 雖可用，但語義過度強化。",
    "notes": "這是 repo 自己 corrected criteria 已經把 retrieval/screening 分開寫清楚的案例。"
  }
]
```