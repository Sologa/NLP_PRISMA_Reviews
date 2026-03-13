# 2511 Criteria Operationalization v2 Report

Date: 2026-03-13  
Paper ID: `2511.13936`  
Run tag: `criteria_2511_opv2`

## 1. Scope（本輪只改 criteria，不改 code）

本輪只做以下兩件事：

1. 修改 `criteria_jsons/2511.13936.json`（重寫 `topic_definition`、`inclusion_criteria.required`、`exclusion_criteria`）。
2. 產生本報告 `docs/criteria_2511_operationalization_v2_report.md`。

明確未改動：

- `scripts/screening/vendor/src/pipelines/topic_pipeline.py`
- `scripts/screening/runtime_prompts/runtime_prompts.json`
- Stage 1 routing/aggregation 規則
- SeniorLead 機制
- fulltext workflow / missing_fulltext handling
- 其他三篇 criteria

## 2. 原 criteria 的模糊點

原版本雖有主題方向，但 reviewer 在 title/abstract 階段缺少可執行邊界，主要模糊點是：

1. `audio-domain` 證據強度未分級：speech/emotion/ranking 出現時，何時可推定 audio core 不夠清楚。
2. `preference-signal` 與 `ordinal/classification/eval ranking` 的等價性未切開。
3. `learning-role`（訊號是否進入 objective/loss/reward/label construction）未作硬性 gate。
4. `negative overrides` 不夠明確，導致同類邊界 case 在 junior/senior 間漂移。

## 3. v2 改法（operational decision table）

本次在不改 JSON schema 前提下，把規則改成 reviewer 可直接執行的 4 層 gate：

1. Audio-domain gate（必須）
- 正向證據：`speech`、`spoken calls/dialogue`、`SER`、`acoustic/audio/voice/paralinguistic`、語音語料語境（如 IEMOCAP/SEMAINE）。
- 多模態：必須是 audio core，不接受 peripheral audio。

2. Preference-signal gate（必須）
- 正向證據：`pairwise comparison`、`relative labels`、`rank/rank-order supervision`、`preference optimization`、比較判斷導出的 supervision。
- 不等價：純 scalar rating、純分類、純 ordinal 標註（未進入偏好/排序學習）、純 evaluation ranking。

3. Learning-role gate（必須）
- preference/ranking 訊號必須進入 training objective/loss/reward/label construction/model selection。
- 若只在 benchmark/reporting/annotation 描述，不算 inclusion。

4. Negative overrides（一票否決）
- 純 SER 分類/回歸且無 preference/rank learning component。
- ordinal intensity 但未形成 preference/rank learning objective。
- ranking 僅作報告或評測。
- 非 audio domain，或 multimodal 中 audio 非核心。

## 4. Before/After 指標比較（雙基準）

### 4.1 Stage 1（include_or_maybe）

| Version | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `senior_no_marker` (historical) | 0.5686 | 0.9667 | 0.7160 | 29 | 22 | 32 | 1 |
| `senior_prompt_tuned` (historical) | 0.8125 | 0.8667 | 0.8387 | 26 | 6 | 48 | 4 |
| `criteria_2511_opv2` (this run) | 0.8056 | 0.9667 | 0.8788 | 29 | 7 | 47 | 1 |

重點：

- 對 `senior_no_marker`：FP `22 -> 7`，precision 大幅上升，recall 持平。
- 對 `senior_prompt_tuned`：precision 略低 (`0.8125 -> 0.8056`)，但 recall 明顯更高 (`0.8667 -> 0.9667`)；整體 F1 更高。

### 4.2 Combined（base + fulltext）

| Version | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `senior_no_marker` (historical) | 0.7105 | 0.9000 | 0.7941 | 27 | 11 | 43 | 3 |
| `senior_prompt_tuned` (historical) | 0.8387 | 0.8667 | 0.8525 | 26 | 5 | 49 | 4 |
| `criteria_2511_opv2` (this run) | 0.8788 | 0.9667 | 0.9206 | 29 | 4 | 50 | 1 |

重點：

- 對 `senior_no_marker`：precision、recall、F1 全面提升。
- 對 `senior_prompt_tuned`：precision 與 recall 同時提升。

### 4.3 驗收門檻檢查

- Stage 1 precision > 0.5686：`0.8056`（通過）
- Combined precision > 0.7105：`0.8788`（通過）
- Combined recall >= 0.8667：`0.9667`（通過）

## 5. 哪些 FP 被修掉、是否有 recall 代價

## 5.1 典型 FP 修復

Stage 1 相較 `senior_no_marker`，移除 16 個 FP（代表例）：

- `google_scholar_hindex`, `harzing2007pop`（非目標研究）
- `cao2007learning`, `christiano2017deep`, `gao2023scaling`, `metallinou2013annotation`（偏通用排序/偏好學習，非 audio-core）
- `huang2022mulan`, `lotfian2017building`, `pan2022effects`, `rix2001perceptual`, `team2024gemini` 等（邊界外或非核心）

Combined 相較 `senior_no_marker`，移除 8 個 FP（代表例）：

- `google_scholar_hindex`, `huang2022mulan`, `lopes2015sonancia`, `lotfian2017building`, `team2024gemini` 等。

## 5.2 新增 FP / FN 風險

- Stage 1 新增 FP：`wester2015we`（1 筆）
- Combined 新增 FP：`mckeown2011semaine`（1 筆）
- FN 方面：
  - Stage 1：仍是 `chumbalov2020scalable`（與 no-marker 相同）
  - Combined：FN 由 `3 -> 1`，整體 recall 反而上升（非新增 recall 代價）

## 6. Spot-check（5 指定案例）

## 6.1 `lotfian2016retrieving`（gold=true）

- 舊版不穩定點：stage1 為 `maybe (senior:3)`，理由集中在「未明講 audio」。
- 新版判定：stage1 仍 `maybe`，但 reasoning 已按三個 gate 明確拆解（preference-signal + learning-role 成立，audio-domain 證據不足）。
- combined：舊/新皆 `include (junior:5,5)`。
- 對 gold 邊界：新規則可讀性明顯提升，但 stage1 仍偏保守。

## 6.2 `han2020ordinal`（gold=true）

- 舊版不穩定點：stage1 需 senior 介入 (`5/3 -> senior 4`)。
- 新版判定：stage1 直接 `include (junior:5,5)`，一致性提升。
- combined：舊/新皆 include（新版本更早在 stage1 穩定收進）。
- 對 gold 邊界：更一致且符合 gold。

## 6.3 `parthasarathy2018preference`（gold=true）

- 舊版不穩定點：stage1 `maybe`，主因仍是 audio 明示不足。
- 新版判定：stage1 仍 `maybe`，但明確指出 preference-signal 與 learning-role 已成立，卡在 audio-domain gate。
- combined：舊/新皆 `include (junior:5,5)`。
- 對 gold 邊界：整體可追溯性改善。

## 6.4 `parthasarathy2016using`（gold=true）

- 舊版不穩定點：stage1 已 include，但 junior 分數仍有落差 (`4,5`)。
- 新版判定：stage1 變成 `include (junior:5,5)`，穩定度提升。
- combined：舊/新皆 include。
- 對 gold 邊界：更符合且更穩定。

## 6.5 `chumbalov2020scalable`（gold=true）

- 舊版不穩定點：stage1 `exclude (senior:1)`，理由是非 audio-domain（movie actors 等）。
- 新版判定：stage1 仍 `exclude (senior:1)`，理由更結構化（preference-signal/learning-role 有，但 audio gate 不成立）。
- combined：此筆未進 fulltext 審查，最終仍為排除路徑。
- 對 gold 邊界：此筆與 gold 標註存在張力（gold=true 但 abstract 對 audio 證據弱），屬殘餘邊界問題。

## 7. 結論：剩餘問題是否仍是 criteria？

本輪結果顯示，`2511` 的主要痛點確實是 criteria operationalization；只改 criteria 就能同時提升 precision 與 recall（尤其 combined F1 顯著上升）。

仍有殘餘問題，但已縮小到少數邊界 case（例如 `chumbalov2020scalable` 這種與 gold 標註張力較高的案例），其性質更像：

1. 標註邊界與 reviewer-operational boundary 的衝突；
2. 或需進一步定義「audio-domain 推定」在極弱證據下的容忍度。

換言之，這一輪後 `2511` 的主問題已不再是廣泛的 criteria 模糊，而是少數高爭議樣本的邊界政策問題。
