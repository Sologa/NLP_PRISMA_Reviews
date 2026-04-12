# 2409.13738 Effort Comparison

## 分數比較

| Variant | Scope | Stage 1 F1 | Delta vs current stage1 | Combined F1 | Delta vs current combined |
| --- | --- | ---: | ---: | ---: | ---: |
| `current authority` | `2409 only` | 0.7500 | +0.0000 | 0.7500 | +0.0000 |
| `gpt-5.4 low` | `2409 + 2511` | 0.7727 | +0.0227 | 0.7692 | +0.0192 |
| `gpt-5.4 xhigh` | `2409 only` | 0.8085 | +0.0585 | 0.8095 | +0.0595 |
| `gpt-5.4-mini low` | `2409 + 2511` | 0.7727 | +0.0227 | 0.8095 | +0.0595 |
| `gpt-5.4-mini xhigh` | `2409 + 2511` | 0.7727 | +0.0227 | 0.8095 | +0.0595 |

## 重點

- 在 `2409` 上，`gpt-5.4 xhigh` 是目前這組 single-reviewer two-stage runs 裡最好的分數。
- `gpt-5.4` 從 `low -> xhigh` 有實質提升：Stage 1 `+0.0358`，Combined `+0.0403`。
- `gpt-5.4-mini` 在 `2409` 上從 `low -> xhigh` 沒有看到分數提升。
- `gpt-5.4-mini low` 和 `gpt-5.4-mini xhigh` 的 `2409` Combined F1 都已達 `0.8095`，與 `gpt-5.4 xhigh` 持平。
- `gpt-5.4 xhigh` 的優勢主要出現在 Stage 1，Stage 1 F1 `0.8085` 明顯高於其他這幾條 run 的 `0.7727`。

## 成本註記

- `gpt-5.4 low` 實測 run-level cost: `$1.574133`，但這是 `2409 + 2511` 兩篇一起跑的成本。
- `gpt-5.4 xhigh` 實測 full-success cost: `$2.676520`，這是 `2409 only`，且包含 stage1 / stage2 retries 的總成本。
- 因為 scope 不同，而且 `xhigh` 這次包含 recovery attempts，上述兩個成本只能作為 run-level 參考，不能直接視為同範圍單篇 apples-to-apples 成本。
