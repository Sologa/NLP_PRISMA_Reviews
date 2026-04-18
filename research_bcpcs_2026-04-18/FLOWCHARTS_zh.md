# BCPCS 流程圖

這份文件用中文流程圖說明 BCPCS 的資料流、實驗流和 artifact flow。這些圖是方法導讀，不是新的 protocol。

## 1. 方法總覽

```mermaid
flowchart TD
    A[Source-faithful stage criteria<br/>criteria_stage1 / criteria_stage2] --> B[Typed eligibility graph<br/>型別化資格 claim]
    B --> C1[Support retrieval<br/>找支持證據]
    B --> C2[Refute retrieval<br/>找反駁 / 排除證據]
    C1 --> D[Evidence ledger<br/>證據帳本]
    C2 --> D
    D --> E[Stage-aware missingness<br/>階段感知缺證據狀態]
    E --> F[Graph / lattice decision<br/>由規則圖推導 verdict]
    F --> G1[Auto include / exclude<br/>自動判定]
    F --> G2[Route to SeniorLead / human<br/>送 senior 或人工 adjudication]
    G1 --> H[Metrics by coverage<br/>分開報 auto-only / selective / assisted]
    G2 --> H
```

重點：

- LLM 不直接自由輸出 final verdict。
- LLM 或 verifier 只能幫忙填 evidence ledger。
- Final verdict 要由 graph/lattice 推導。
- 不確定 case 必須 route，不可假裝自動解決。

## 2. Stage 1 / Stage 2 的缺證據處理

```mermaid
flowchart TD
    A[Candidate paper] --> B{Stage?}
    B -->|Stage 1| C[Title + abstract only]
    B -->|Stage 2| D[Full text + metadata]
    C --> E{Claim observable from title/abstract?}
    E -->|Yes| F[Require support/refute span]
    E -->|No| G[missingness_reason = not_observed_stage1<br/>or deferred_to_stage2]
    D --> H{Evidence unresolved?}
    H -->|No| I[Support/refute/unknown with quote]
    H -->|Yes| J[Classify reason:<br/>semantic_non_fit<br/>retrieval_failure<br/>metadata_ambiguity<br/>source_gold_tension<br/>evidence_incomplete]
    F --> K[Evidence ledger]
    G --> K
    I --> K
    J --> K
```

重點：

- Stage 1 的 `not observed` 不能自動當成 `NO`。
- Stage 2 的 unknown 也不能只寫 unknown，必須區分原因。

## 3. Artifact flow

```mermaid
flowchart TD
    A[Existing repo inputs<br/>read-only] --> A1[runtime_prompts.json]
    A --> A2[criteria_stage1 / criteria_stage2]
    A --> A3[cutoff_jsons]
    A --> A4[refs metadata + gold]
    A --> A5[results_manifest]

    A1 --> B[Prototype scripts in src]
    A2 --> B
    A3 --> B
    A4 --> B
    A5 --> B

    B --> C1[runs/dry_run_loader]
    B --> C2[runs/baseline_recheck]
    B --> C3[runs/schema_validation]
    B --> C4[runs/smoke]

    C1 --> D[reports]
    C2 --> D
    C3 --> D
    C4 --> D
```

重點：

- 左邊都是 read-only existing repo inputs。
- 所有新輸出都在 `research_bcpcs_2026-04-18/`。
- 不寫 production paths。

## 4. Benchmark 路線

```mermaid
flowchart TD
    A[Freeze leakage protocol] --> B[Choose split<br/>leave-one-review-out preferred]
    B --> C[Build claim graphs<br/>without rewriting criteria]
    C --> D[Build / freeze boundary atlas<br/>train/dev only]
    D --> E[Run internal diagnostic]
    E --> F[Run ablations with same splits]
    F --> G[Human validate evidence spans]
    G --> H{External public benchmark feasible?}
    H -->|Yes| I[Run external generalization]
    H -->|No| J[Document licensing / reconstruction blocker]
    I --> K[Conference-readiness assessment]
    J --> K
```

重點：

- `leakage_control.md` 必須先 freeze。
- Boundary atlas 不能從 held-out FP/FN 建。
- Internal diagnostic 不能當唯一 conference evidence。

## 5. Selective routing 的報告方式

```mermaid
flowchart TD
    A[All candidates] --> B{BCPCS confidence / evidence completeness}
    B -->|High confidence + complete evidence| C[Auto decision]
    B -->|Boundary / missing / conflict| D[Route]
    C --> E[Auto-only metrics]
    D --> F[SeniorLead / human adjudication]
    F --> G[Assisted metrics]
    C --> H[Selective final metrics]
    F --> H
    H --> I[Report coverage, abstention, route rate, cost]
```

必須分開報：

- Auto-only F1
- Selective final F1
- Senior/human-assisted F1
- Coverage
- Abstention rate
- Routed-case count
- Cost

不能把 assisted final F1 偽裝成 fully automated F1。
