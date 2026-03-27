# Cutoff Gold-Positive 問題診斷備忘錄

Date: 2026-03-26
Revision note: 已對齊 `2511.13936` / `2601.19926` cutoff policy 變更後的 current disk state。

## 結論先行

`gold-positive cutoffed` 代表「gold 標成應保留的 paper，被 cutoff 直接砍掉」。

這不是一般 precision 問題，而是 pre-review hard filter 的 recall 問題。一旦在 cutoff 階段被砍掉，後面的 reviewer、senior adjudication、fulltext evidence 都不會再有機會修正。

但 current rerun 顯示，`2511` 與 `2601` 的主要 cutoff 問題現在都已經被修正：

| Paper | Gold+ total | Gold+ cutoffed | current 狀態 |
| --- | ---: | ---: | --- |
| `2307.05527` | 171 | 16 | 仍有 cutoff/gold scope 張力，尚未在這次修復範圍內解決 |
| `2409.13738` | 21 | 0 | 一直不是主問題，可視為 control |
| `2511.13936` | 30 | 0 | 原先的 lower-bound derivation 問題已移除，cutoff 不再誤殺 gold positives |
| `2601.19926` | 336 | 0 | `%Y-%m` parser bug 已修復，`2020-12` 類 metadata 不再被誤判 |

參考工件：

- `screening/results/cutoff_only_audit_2026-03-26/summary.json`
- `screening/results/cutoff_only_audit_2026-03-26_rerun_2511_2601_new_cutoff/summary.json`
- `screening/results/cutoff_semantic_audit_all16_2026-03-26/summary.json`
- `screening/results/publication_date_parse_audit_2026-03-26/summary.json`

## 1. `2511.13936`：原本是 derivation / semantics 問題，現在已修正

舊版 `cutoff_jsons/2511.13936.json` 把 `published from 2020 onward` 投影成全域 pre-review lower bound，會把一批 `2010-2018` 的 gold-positive 直接砍掉。

current cutoff file 已改成不再把那個 retrieval-time 描述硬投影為全域 hard lower bound；對 current runtime 而言：

- `gold_positive_cutoffed = 0`
- `parthasarathy2018preference` 這類 case 現在是 `cutoff_pass = true`
- `2511` 的問題已不再是 cutoff 先砍掉正確 paper，而是 reviewer / Stage 1 本身如何讀 preference signal

所以現在最準的一句話是：

> `2511` 的 cutoff mismatch 已經修掉；剩下的錯誤應回到 reviewer 判讀與 evidence interpretation 層分析。

## 2. `2601.19926`：原本是 `%Y-%m` parser bug，現在已修正

舊 parser 不接受 `%Y-%m`，所以 `2020-12` 會被標成 `unparseable_published_date`，像：

- `Warstadt:etal:2020`
- `ettinger_what_2020`
- `kuncoro-etal-2020-syntactic`

current parser 已接受 `%Y-%m`，publication-date parse audit 也顯示：

- `papers_with_year_month_issues_after = []`
- `2601.19926` 不再有 `2020-12` 型 unparseable case
- `gold_positive_cutoffed = 0`

所以現在最準的一句話是：

> `2601` 的 cutoff 問題已經不是語義問題，而是已修復完成的 parser bug。

## 3. `2409.13738` 與 `2307.05527` 的角色

- `2409` 在 current 與舊 audit 中都沒有 `gold-positive cutoffed` 問題，它仍適合當 control。
- `2307` 仍保留明顯的 cutoff/gold scope tension；這一篇不能直接套用 `2511` / `2601` 的修法敘事。

## 4. 現階段最保守的 repo-level 判斷

- 不應把 `gold-positive cutoffed` 視為小誤差。
- 但對 `2511` 與 `2601`，current evidence 已支持「主要 cutoff 問題已解決」。
- `2511` 現在不該再被描述成 `current cutoff mismatch`；它應回到 reviewer / QA error taxonomy。
- `2601` 現在不該再被描述成 `current parser-only issue`；parser fix 已落地，current cutoff excludes = `0`。
- `2307` 仍需要保留 scope / semantics mismatch 的獨立診斷。

## 5. 建議的閱讀順序

1. `AGENTS.md`
2. `docs/chatgpt_current_status_handoff.md`
3. `screening/results/results_manifest.json`
4. `screening/results/2511.13936_full/CURRENT.md`
5. `screening/results/2601.19926_full/CURRENT.md`
6. 再看：
   - `screening/results/cutoff_only_audit_2026-03-26_rerun_2511_2601_new_cutoff/summary.json`
   - `screening/results/cutoff_semantic_audit_all16_2026-03-26/summary.json`
   - `screening/results/publication_date_parse_audit_2026-03-26/summary.json`

## 6. 一句話版本

- `2511`: cutoff derivation 問題已修正，current 誤差不再來自 cutoff 先砍 paper。
- `2601`: `%Y-%m` parser bug 已修正，current cutoff 不再誤殺 `2020-12` 類正例。
- `2307`: 仍保留獨立的 cutoff/gold scope 張力，不能混為同一類。
