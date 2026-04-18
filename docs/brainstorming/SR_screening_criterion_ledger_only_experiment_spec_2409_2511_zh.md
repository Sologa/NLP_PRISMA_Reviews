# `#2 criterion ledger` 舊規格否決說明

日期：2026-04-15  
語言：繁體中文  
狀態：`rejected` / `do not implement`

---

## 結論

本檔先前描述的 `#2 criterion ledger` 規格，核心是：

- `2 juniors + 1 SeniorLead`
- 由人或本地設計去區分 `core / non-core criterion`
- 只有命中 `core` 衝突或 `core` `UNCLEAR` 才送 senior

這一版設計在查核 **Akinseloyin 2026 原 paper** 與其公開 **GitHub code** 後，已正式判定為：

- **不是原 paper 的 paper-faithful 方法**
- **不能再被描述成 Akinseloyin 2026 的原始做法**
- **在目前這條 `#2 paper-faithful A` 路線下，絕對不採用**

---

## 為什麼被否決

### 1. 原 paper 不是兩個 junior

原 paper 在實驗設定中明確使用：

- `3` 個 primary QA models
- 再加 `1` 個較強的 adjudicator

若硬翻成我們 repo 常用說法，比較接近：

- `3 個 junior-like QA agents`
- `1 個 adjudicator`

而不是：

- `2 juniors + 1 SeniorLead`

### 2. 原 paper 沒有 `core / non-core criterion` 這種手工路由層

原 paper 的單位是：

- 先把 selection criteria 轉成一組對齊的 QA 問題
- 多個 QA models 回答同一組問題
- 再做 voting / debate / adjudication

原 paper **沒有**：

- human-defined `core criterion`
- codex-defined `core criterion`
- 只看 `core` 衝突才送 senior 的 gate

### 3. 原 paper 不是 `Stage 1 / Stage 2 full-text` 結構

原 paper研究的是：

- `title + abstract` 的 abstract screening

不是：

- title/abstract Stage 1
- full-text Stage 2

因此把它直接翻成我們 repo 的 stage-split full-text 流程，而又說成 paper 原法，會混淆方法邊界。

### 4. 原 paper 的 adjudicator 是看所有 primary QA models 的回答

paper-faithful 的重點是：

- 多個 primary QA models 回答同一組 criteria-derived QA questions
- adjudicator 直接綜合這些回答與理由

不是：

- 先人工挑哪些 criterion 比較重要
- 再讓 senior 只處理那一部分

---

## 在目前 `#2 paper-faithful A` 路線下，哪些做法絕對不行

以下做法一律視為 **絕對不採用**：

1. 把 `Akinseloyin 2026` 說成 `2 juniors + 1 SeniorLead`
2. 用 human 來指定 `core / non-core criterion`
3. 用 Codex 或本地 agent 先手工指定 `core / non-core criterion`
4. 用 `core / non-core` senior gate 來宣稱自己在重現原 paper
5. 把 abstract-screening paper 直接改寫成 stage1/full-text stage2，卻不明講這是 repo extension

---

## 替代文件

請改看：

- [Akinseloyin_2026_paper_faithful_rewrite_zh.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/brainstorming/Akinseloyin_2026_paper_faithful_rewrite_zh.md)

這份新文件會直接交代：

- 原 paper 到底怎麼做
- 原 code 到底怎麼串
- 到底用了幾個 primary QA models
- 哪些部分可以稱為 paper-faithful
- 哪些部分不能再混稱
