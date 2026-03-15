# Source-Faithful vs Operational 對照報告（2409 / 2511）

Date: 2026-03-15  
Benchmark root: `screening/results/source_faithful_vs_operational_2409_2511_runA`

## 1. 本輪範圍與固定條件

本輪只比較兩組 criteria：

- Operational（production）
  - `criteria_jsons/2511.13936.json`
  - `criteria_jsons/2409.13738.json`
- Source-faithful
  - `docs/ChatGPT/2511.13936.source_faithful_rewrite.json`
  - `docs/ChatGPT/2409.13738.source_faithful_rewrite.json`

本輪明確未改：

- Stage 1 aggregation（`>=4 include` / `<=2 exclude` / else `SeniorLead`）
- `SeniorLead` 機制與單點裁決
- runtime prompts（`scripts/screening/runtime_prompts/runtime_prompts.json`）
- `topic_pipeline.py` 判決邏輯
- 其他 paper criteria

## 2. 實作與執行方式

新增最小實作：

- `scripts/screening/bench_source_faithful_vs_operational.sh`
- `scripts/screening/summarize_source_faithful_vs_operational.py`

執行矩陣：

- papers: `2511.13936`, `2409.13738`
- variants: `operational`, `source_faithful`
- repeats: `3`
- 每輪固定：`TOP_K=0`, `ENABLE_FULLTEXT_REVIEW=1`, `FULLTEXT_REVIEW_MODE=inline`, `FORCE_PREPARE_INPUTS=0`
- 評分口徑：`positive_mode=include_or_maybe`

彙總檔：

- `screening/results/source_faithful_vs_operational_2409_2511_runA/summary.json`

## 3. 2511 對照結果

### 3.1 Stage 1（mean of 3 runs）

| Variant | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| operational | 28.00 | 4.33 | 49.67 | 2.00 | 0.8671 | 0.9333 | 0.8984 |
| source-faithful | 28.00 | 6.33 | 47.67 | 2.00 | 0.8170 | 0.9333 | 0.8705 |

### 3.2 Combined（mean of 3 runs）

| Variant | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| operational | 27.67 | 3.00 | 51.00 | 2.33 | 0.9022 | 0.9222 | 0.9120 |
| source-faithful | 25.33 | 2.33 | 51.67 | 4.67 | 0.9161 | 0.8444 | 0.8784 |

### 3.3 重點解讀（2511）

- 回退到 source-faithful 後，`combined recall` 顯著下降（`0.9222 -> 0.8444`），`FN` 幾乎翻倍（mean `2.33 -> 4.67`）。
- source-faithful 在 combined precision 略高（`+0.0139`），但是以 recall 明顯退化換來，整體 `F1` 下降（`-0.0337`）。
- 穩定性也變差：Stage 1 unstable keys `8 -> 14`。

結論：`2511` 目前 performance 的主要改善確實來自 operational hardening，不是原文 criteria 自然就能達到同等 runtime 表現。

## 4. 2409 對照結果

### 4.1 Stage 1（mean of 3 runs）

| Variant | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| operational | 21.00 | 18.67 | 38.33 | 0.00 | 0.5295 | 1.0000 | 0.6923 |
| source-faithful | 20.67 | 10.00 | 47.00 | 0.33 | 0.6738 | 0.9841 | 0.7999 |

### 4.2 Combined（mean of 3 runs）

| Variant | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| operational | 21.00 | 11.67 | 45.33 | 0.00 | 0.6430 | 1.0000 | 0.7827 |
| source-faithful | 19.67 | 6.00 | 51.00 | 1.33 | 0.7662 | 0.9365 | 0.8427 |

### 4.3 重點解讀（2409）

- 這次重跑下，source-faithful 對 `2409` 的 precision/FP 顯著改善（combined FP mean `11.67 -> 6.00`）。
- 但 recall 出現可見退化（combined `1.0000 -> 0.9365`，FN mean `0 -> 1.33`），且 combined unstable keys `2 -> 9`。
- 換句話說：source-faithful 在 `2409` 不是「硬 FP 回來」，而是「硬 FP 進一步壓低，但同時引入 recall 與穩定性成本」。

## 5. Spot-check（13 案）

格式：`operational: Stage1 -> Combined` vs `source-faithful: Stage1 -> Combined`（3 runs 判決摘要）

## 5.1 2511 指定案例

1. `lotfian2016retrieving`（gold=true）  
operational：`maybe, maybe, maybe -> include, include, include`  
source-faithful：`maybe, maybe, maybe -> include, include, include`  
差異邊界：無實質差異；兩版都先保留、後段納入。

2. `han2020ordinal`（gold=true）  
operational：`include, include, include -> include, include, include`  
source-faithful：`include, include, maybe -> include, maybe, exclude`  
差異邊界：source-faithful 對 ordinal/ranking 的 operational語義較鬆散，缺少 operational 版本對「ordinal signal 作為 learning-role 證據」的明確 gate，導致 combined 不穩與 FN 風險。

3. `parthasarathy2018preference`（gold=true）  
operational：`maybe, maybe, maybe -> include, include, include`  
source-faithful：`maybe, maybe, maybe -> include, include, include`  
差異邊界：兩版一致。

4. `parthasarathy2016using`（gold=true）  
operational：`include/include/include -> include/include/include`  
source-faithful：`include/maybe/include -> include/include/include`  
差異邊界：source-faithful 在 Stage 1 少了 operational 對 relative-label/rank-order 的強陽性提示，導致輕微波動。

5. `chumbalov2020scalable`（gold=true）  
operational：`exclude, exclude, exclude -> exclude, exclude, exclude`  
source-faithful：`maybe, maybe, exclude -> maybe, exclude, exclude`  
差異邊界：operational 的 audio-core gate 一致排除；source-faithful 對「multimodal including audio」更寬，造成 maybe/exclude 擺動，但仍未穩定收進（仍是殘餘 FN 問題）。

## 5.2 2409 指定案例

1. `etikala2021extracting`（gold=true）  
operational：`include/include/include -> include/include/include`  
source-faithful：`include/include/include -> maybe/maybe/maybe`  
差異邊界：source-faithful 對 IC.1/IC.4 confirmatory 條件更嚴格，combined 轉保守。

2. `honkisz2018concept`（gold=true）  
operational：`include/include/include -> include/include/include`  
source-faithful：`include/include/maybe -> include/include/include`  
差異邊界：source-faithful Stage 1 稍保守，但 combined 最終仍納入。

3. `goncalves2011let`（gold=true）  
operational：`include/include/include -> include/include/include`  
source-faithful：`exclude/maybe/maybe -> exclude/include/include`  
差異邊界：source-faithful 對「concrete method + experiments」判準在此案有波動，導致真陽性不穩（曾出現 FN）。

4. `kourani_process_modelling_with_llm`（gold=false）  
operational：`include/include/include -> include/include/include`  
source-faithful：`include/include/maybe -> exclude/maybe/maybe`  
差異邊界：source-faithful 的 paper-type/peer-review gate（EC.1）與 confirmatory 門檻更嚴，硬 FP 被壓低。

5. `grohs2023large`（gold=false）  
operational：`include/include/include -> include/include/include`  
source-faithful：`include/include/include -> maybe/exclude/exclude`  
差異邊界：source-faithful 對方法與實證完備性要求較高，減少 FP 但增加不穩。

6. `bellan2020qualitative`（gold=false）  
operational：`include/include/include -> include/include/include`  
source-faithful：`exclude/exclude/exclude -> exclude/exclude/exclude`  
差異邊界：source-faithful 對 IC.4 / EC.4（method concreteness + experiments）更強硬，成功清除此 hard FP。

7. `bellan2021process`（gold=false）  
operational：`include/include/include -> exclude/include/exclude`  
source-faithful：`include/maybe/include -> maybe/exclude/exclude`  
差異邊界：兩版都不穩，但 source-faithful 在 combined 較偏排除，FP 壓低。

8. `lopez2021challenges`（gold=false）  
operational：`maybe/include/include -> maybe/maybe/maybe`  
source-faithful：`exclude/maybe/exclude -> exclude/maybe/exclude`  
差異邊界：source-faithful 對 IC.3/EC.3「specifically process extraction」更嚴，降低 FP；但仍有邊界波動。

## 6. 哪些提升來自合理 operationalization、哪些可能屬超譯

### 6.1 2511

- 可被支持的 operational gain：
  - Audio-domain / preference-signal / learning-role 三層 gate 的明確化，確實提升 runtime 可判定性與穩定性。
  - source-faithful 回退後，combined FN 增加與不穩加劇，顯示 operational hardening 有實質貢獻。
- 仍需注意的邊界：
  - `chumbalov2020scalable` 仍是高爭議樣本，顯示 audio 邊界政策仍需獨立定義。

### 6.2 2409

- 這次資料顯示 source-faithful 可直接壓低一批 hard FP family（尤其 Bellan 系列、部分 LLM adjacency）。
- 但成本是 recall 與穩定性下降（true-positive 邊界案如 `goncalves2011let`、`halioui2018bioinformatic` 出現 FN）。
- 因此 `2409` 的 production 取捨不是單純「哪個 F1 高」，而是「是否接受 recall 退化與更高波動」。

## 7. 三個最重要結論（明確回答）

1. `2511`：目前 production criteria 是否應維持 operational v2，而不是退回 source-faithful rewrite？  
**是。應維持 operational v2。**  
理由：source-faithful 回退造成 combined recall 顯著下降與 FN 增加，整體 F1 退化。

2. `2409`：目前 production criteria 是否應維持 stage-split / boundary-hardening 方向，而不是退回 source-faithful rewrite？  
**是，production 應維持 stage-split / boundary-hardening 方向，不建議整體退回 source-faithful。**  
理由：雖然 source-faithful 本次 precision/F1 較高，但同時帶來 recall 下滑與更高不穩定；對 screening 生產流程（recall 敏感）風險偏高。

3. 是否應採雙層設計（source-faithful baseline + operational production criteria）？  
**是，建議明確採雙層設計。**  
- Layer A：`paper-grounded source-faithful baseline`（忠於原文 IC/EC）  
- Layer B：`production operational criteria`（明確聲明為 reviewer-operational projection）  
這樣可以同時保留可追溯性與實務可用性，避免「忠實改寫」與「生產優化」混在同一層。

## 8. 產物清單

- Benchmark driver：`scripts/screening/bench_source_faithful_vs_operational.sh`
- Summary script：`scripts/screening/summarize_source_faithful_vs_operational.py`
- Raw outputs：`screening/results/source_faithful_vs_operational_2409_2511_runA/...`
- Machine summary：`screening/results/source_faithful_vs_operational_2409_2511_runA/summary.json`
