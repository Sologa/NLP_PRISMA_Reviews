# Cutoff Gold-Positive 問題診斷備忘錄

Date: 2026-03-26

## 結論先行

`gold-positive cutoffed` 代表「gold 標成應保留的 paper，被 cutoff 直接砍掉」。

這不是一般 precision 問題，而是 pre-review hard filter 的 recall 問題。一旦在 cutoff 階段被砍掉，後面的 reviewer、senior adjudication、fulltext evidence 都不會再有機會修正。

本次 `cutoff-only` audit 顯示：

| Paper | Gold+ total | Gold+ cutoffed | 主風險 |
| --- | ---: | ---: | --- |
| `2307.05527` | 171 | 16 | cutoff window 與 benchmark gold scope 可能不一致 |
| `2409.13738` | 21 | 0 | 這篇不是主問題，可當 control |
| `2511.13936` | 30 | 9 | cutoff lower bound 與 gold scope 明顯衝突 |
| `2601.19926` | 336 | 3 | 日期 parsing 過嚴，屬實作層 bug |

參考工件：

- `screening/results/cutoff_only_audit_2026-03-26/summary.json`
- `screening/results/cutoff_only_audit_2026-03-26/report.md`

## 為什麼這件事嚴重

- `gold-positive cutoffed` 是 hard false negative。
- 這種錯誤發生在 reviewer 之前，所以不是 prompt tuning 或 senior routing 可以補救的問題。
- 如果 cutoff layer 的語義和 gold benchmark 的語義不一致，後面所有分數都會建立在錯的 candidate universe 上。
- 如果 cutoff layer 只是 parser 太嚴，也會把本來應該保留的 paper 機械式刪掉。

## 現在已知的三種 failure mode

### 1. `2307.05527`: window 與 gold scope 可能不一致

`cutoff_jsons/2307.05527.json` 的 active window 是 `2018-02-01 .. 2023-02-01`。

但被 cutoff 掉的 16 個 gold-positive 幾乎全部都是 `2017` 或 `2018-01-01` 類型的 metadata 日期，例如：

- `arik_neural_2018` -> `2018-01-01` -> `before_start`
- `zhou2018voice` -> `2018-01-01` -> `before_start`
- `kameoka_convs2s-vc_2020` -> metadata 其實是 `2018` -> `before_start`
- `wilkinson_generative_2019` -> metadata 其實是 `2018` -> `before_start`

這表示至少有兩種可能：

- review paper 的 hard cutoff 窗口本來就比 gold benchmark 更窄；
- 或 metadata 使用的是 arXiv first-posted / preprint date，但 gold 是依照 evidence-base inclusion 在更寬鬆語義下整理。

不管是哪一種，現象都不是 reviewer 判斷錯，而是 cutoff 層先把 gold-positive 砍掉。

### 2. `2511.13936`: lower bound 與 gold benchmark 明顯衝突

`cutoff_jsons/2511.13936.json` 的 active lower bound 是 `2020-01-01`。

但被 cutoff 掉的 9 個 gold-positive 全都在 `2010-2018`：

- `yang2010ranking`
- `cao2012combining`
- `cao2015speaker`
- `lotfian2016practical`
- `lotfian2016retrieving`
- `parthasarathy2016using`
- `parthasarathy2017ranking`
- `parthasarathy2018preference`
- `lopes2017modelling`

這是目前最明顯的語義衝突 case：

- 如果 `Published from 2020 onward` 是 review paper 自己真的要當 hard retrieval/screening gate，那這 9 篇不應該出現在 gold-positive。
- 如果這 9 篇本來就是 benchmark 中應保留的 evidence base，那 `2020 onward` 就不能在目前 pipeline 中被當作 pre-review hard filter 直接套到 benchmark universe。

換句話說，`2511` 比較不像 parser bug，而像是「cutoff artifact 的 operational semantics 和 benchmark target semantics 並不一致」。

### 3. `2601.19926`: parser bug / normalization bug

`2601.19926` 沒有 substantive window mismatch 的跡象。被 cutoff 掉的 3 個 gold-positive 都是：

- `Warstadt:etal:2020` -> `2020-12`
- `ettinger_what_2020` -> `2020-12`
- `kuncoro-etal-2020-syntactic` -> `2020-12`

它們的 cutoff status 全部是 `unparseable_published_date`。

這與目前 parser 實作一致：`scripts/screening/cutoff_time_filter.py` 只接受

- `%Y-%m-%d`
- `%Y/%m/%d`
- `%B %d, %Y`
- `%b %d, %Y`
- `%Y`

但不接受 `%Y-%m`。

所以 `2601` 的問題不是 review paper 語義，而是 cutoff parser 對 `YYYY-MM` 過嚴，導致機械式 false exclude。

## 2409.13738 的角色

`2409.13738` 在本次 audit 裡 `gold-positive cutoffed = 0`。

它不應該是這次 root cause 分析的主戰場。更好的用法是把它當 control：

- cutoff layer 可以 work；
- 問題不是「所有 paper 都被 cutoff 搞壞」；
- 真正需要解釋的是為什麼 `2307`、`2511`、`2601` 會出現不同型態的 gold-positive cutoffed。

## 外部分析時一定要看的原始來源

如果要請 ChatGPT 或其他外部模型分析，必須先看這三篇 SR 原文 PDF，而不是只看衍生 criteria 檔：

- `refs/2307.05527/2307.05527.pdf`
- `refs/2511.13936/2511.13936.pdf`
- `refs/2601.19926/2601.19926.pdf`

補充：

- `refs/<paper_id>/<paper_id>.md` 在這三篇目前不是乾淨的正文 markdown，不適合作為主要閱讀來源。
- `2409.13738` 可以不看原文或只當對照，不是這次主問題。

## 外部分析最需要回答的問題

1. `2307` 和 `2511` 的 `gold-positive cutoffed`，到底是 benchmark 定義與 review paper 原文不一致，還是 cutoff artifact 把 retrieval-time clause 誤升格成 screening-time hard filter？
2. `2511` 的 `Published from 2020 onward` 在原文中，究竟是 search-space / retrieval convenience，還是作者真的把它當 evidence eligibility 的 hard boundary？
3. `2307` 的 `2018-02-01` 下界，在原文中是否應該直接裁掉 `2018-01` 類 paper，還是 benchmark gold 其實採用了較寬鬆的 evidence-base 定義？
4. `2601` 是否只需要 parser normalization 修正即可清除這 3 筆 FN？
5. 修正應該落在哪一層：
   - `cutoff_jsons`
   - `cutoff_time_filter.py`
   - benchmark interpretation
   - 或某篇 paper 的 special-case policy

## 建議的判讀順序

1. 先讀 `AGENTS.md`。
2. 再讀 `docs/chatgpt_current_status_handoff.md`。
3. 再讀 `screening/results/results_manifest.json`。
4. 再讀本次 audit：
   - `screening/results/cutoff_only_audit_2026-03-26/summary.json`
   - `screening/results/cutoff_only_audit_2026-03-26/report.md`
5. 再讀三個 active cutoff files：
   - `cutoff_jsons/2307.05527.json`
   - `cutoff_jsons/2511.13936.json`
   - `cutoff_jsons/2601.19926.json`
6. 最後一定要看三篇 SR 原文 PDF：
   - `refs/2307.05527/2307.05527.pdf`
   - `refs/2511.13936/2511.13936.pdf`
   - `refs/2601.19926/2601.19926.pdf`

## 現階段最保守的 repo-level判斷

- 不應把 `gold-positive cutoffed` 視為小誤差。
- `2601` 幾乎可以直接視為 parser bug。
- `2511` 大概率是 benchmark scope 與 cutoff semantics 的硬衝突。
- `2307` 很可能也是 scope/semantics mismatch，但需要回到原文核實 `2018-02-01` 的語義邊界。
- 在完成原文核實前，不應草率把這三篇的問題統一歸因成同一種 cutoff bug。
