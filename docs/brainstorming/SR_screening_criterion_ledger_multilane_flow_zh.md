# `#2 criterion ledger` 舊流程圖否決說明

日期：2026-04-15  
語言：繁體中文  
狀態：`rejected` / `do not implement`

---

## 這份舊流程圖為什麼被撤下

這份文件原先把下面幾件事混在一起：

- `criterion ledger`
- `兩位 junior + SeniorLead`
- `core / non-core criterion`
- `只讓部分 case route 到 senior`

經查 **Akinseloyin 2026 原 paper** 與其公開 code 後，已確認：

- 這不是 paper-faithful `#2`
- 這是 repo 自己額外長出的 routing / adjudication extension
- 在目前你已指定的 `paper-faithful A` 路線下，這種流程圖 **絕對不採用**

---

## 這份舊流程圖裡哪些觀念不能再留

以下觀念不能再被拿來描述 `Akinseloyin 2026` 原法：

1. `core criterion` 才送 senior
2. `core criterion` `UNCLEAR` 才送 senior
3. `兩位 junior + SeniorLead` 就等於原 paper
4. `title/abstract -> full text` 的 stage-split 流程就是原 paper

---

## 後續應改看哪份文件

請改看：

- [Akinseloyin_2026_paper_faithful_rewrite_zh.md](/Users/xjp/Desktop/NLP_PRISMA_Reviews/docs/brainstorming/Akinseloyin_2026_paper_faithful_rewrite_zh.md)

那份文件會以 paper 與 code 為準，重新整理：

- 原 paper 的 QA 單位
- primary QA models 的數量
- peer-review / debate round
- adjudicator 的角色
- 哪些是 paper 原法
- 哪些是 repo extension
