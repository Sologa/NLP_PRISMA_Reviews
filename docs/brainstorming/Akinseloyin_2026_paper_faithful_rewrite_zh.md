# Akinseloyin 2026 原篇方法與 code 的 paper-faithful 轉寫

日期：2026-04-15  
語言：繁體中文  
定位：把 **Akinseloyin 2026 原 paper** 與其公開 **GitHub code** 轉寫成適合本 repo 使用的判讀筆記  
用途：釘死「原 paper 到底怎麼做」、以及「哪些做法不能再被混稱成 paper 原法」

---

## 1. 先講結論

### 最重要的三句話

1. 原 paper 不是 `2 juniors + 1 SeniorLead`。  
   原 paper 比較接近 **`3 個 primary QA models` + `1 個 adjudicator`**。

2. 原 paper 沒有 `core / non-core criterion` 這一層人工路由。  
   它的基本單位是 **criteria-derived QA questions**，不是人工指定哪條 criterion 比較重要。

3. 原 paper研究的是 **title + abstract 的 abstract screening / ranking**，不是 repo 現在這種 `Stage 1 + Stage 2 full-text`。

---

## 2. paper 基本資料

- 論文標題：*Large language model-based multiagent collaboration for abstract screening toward automated systematic reviews*
- 作者：Opeoluwa Akinseloyin, Xiaorui Jiang, Vasile Palade
- 期刊：*Biology Methods and Protocols*
- 年份：2026
- DOI：<https://doi.org/10.1093/biomethods/bpag006>
- 論文頁面：<https://academic.oup.com/biomethods/article/doi/10.1093/biomethods/bpag006/8460762>
- 公開 code repo：<https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening>

---

## 3. 原 paper 的任務到底是什麼

白話講，原 paper 做的不是我們 repo 現在這種：

- Stage 1 看 title/abstract
- Stage 2 看 full text
- 最後算分類 F1

它做的是：

- 把 **title + abstract** 串在一起
- 把 screening 轉成 **question-answering**
- 讓多個 LLM 對同一組 QA 問題作答
- 再把答案轉成 ranking score
- 最後用 `MAP`、`WSS@95%`、`Recall@k%` 這類 prioritization 指標評估

所以原 paper 的主體其實比較像：

- `ranking / prioritization workflow`

而不是：

- `final include/exclude classification workflow`

---

## 4. 原 paper 的最小工作單位是什麼

### 術語版

`criteria-derived QA questions`

### 白話版

不是直接把一整段 criteria 丟給模型問「收不收」。  
而是先把 review criteria 拆成一組對齊的 **是/否問題**，再逐題回答。

從 paper 與公開 code 來看，這組問題在實作上固定是：

- **5 個 yes/no questions**

code 證據：

- `GPT_Questions.py` 直接要求模型「generate 5 unique yes or no questions」
- `Claude.py` / `GPT.py` / `Gemini.py` / `Adjudicator.py` 都用 `range(5)` 處理問題欄位

因此，原 paper 比較接近：

- `question-level QA decomposition`

而不是：

- human-defined `core / non-core criterion`

---

## 5. 原 paper 到底用了幾個 junior

### 精確說法

原 paper 沒有用 `junior` 這個詞。  
它用的詞是：

- `primary QA models`

### 如果硬翻成我們 repo 慣用說法

最接近的是：

- **3 個 junior-like QA agents**
- 再加 **1 個 adjudicator**

### 為什麼是 3，不是 2

paper 本文在實驗設定裡明寫：

- `Three primary QA models`

而且列出的三個 primary models 是：

- GPT
- Claude
- Gemini

公開 code 也完全對齊：

- `Claude.py`
- `GPT.py`
- `Gemini.py`

而 `Adjudicator.py` 會同時讀入：

- `Claude.csv`
- `Gemini.csv`
- `GPT.csv`

所以這件事可以直接講死：

> **原 paper 不是兩個 junior。原 paper 是三個 primary QA models。**

---

## 6. 原 paper 的 workflow 長什麼樣

### 6.1 QA 問題生成

先把 review criteria 轉成 5 個 yes/no questions。

對應 code：

- `GPT_Questions.py`

### 6.2 第一輪獨立 QA

三個 primary QA models 各自獨立回答同一組問題。

對應 code：

- `Claude.py`
- `GPT.py`
- `Gemini.py`

### 6.3 三種 collaboration strategy

原 paper 重點不是只有一條流程，而是比較三種協作策略：

1. `Soft-Vote`
2. `Multi-agent Debate (MAD)`
3. `LLM-based Adjudication`

這三種是並列被比較的方法，不是全部硬串成同一條。

### 6.4 Debate round

在 `MAD` 路線裡，每個 model 會看到其他兩個 model 的回答與理由，然後決定要不要修改自己的答案。

對應 code：

- `Claude_2.py`
- `GPT2.py`
- `Gemini_2.py`

白話講：

- 這不是 free-form 聊天
- 是每個 agent 看到 peers 的答案後，**重答同一題**

### 6.5 Adjudication

`Adjudicator.py` 會看三個 primary models 的答案與理由，再做綜合判定。

這裡有一個重要細節：

- paper 與 code 都支持「有一個較強的 adjudicator」
- 但 code repo 目前的 `Adjudicator.py` 讀的是 `Claude.csv / Gemini.csv / GPT.csv`
- **不是** `Claude2.csv / Gemini2.csv / GPT2.csv`

也就是說，在公開 code 裡：

- `debate` 路線
- `adjudication` 路線

是**並列變體**，不是一條必然串接的單一路線。

---

## 7. paper 與 code 的模型配置

### paper 本文寫的模型

paper 本文的 primary models 是：

- GPT-4o Mini
- Claude 3 Haiku
- Gemini 1.5 Flash

adjudicator 是：

- Gemini 1.5 Pro

### code repo 目前主分支顯示的模型

公開 repo 的 README / code 目前寫的是：

- GPT-4o-mini
- Claude 3 Haiku
- Gemini 2.0 Flash
- adjudicator：Gemini 2.5 Pro

所以要注意：

- **workflow 骨架是一致的**
- **但 GitHub main branch 的具體 model version 已和 paper 內文不完全相同**

這不影響我們判斷 workflow 結構，但寫文件時要明說，不能把 repo main branch 當成 paper 當時完全原封不動的執行版本。

---

## 8. 原 paper 沒做什麼

下面這些東西，**不能再說成是原 paper 的做法**：

1. `2 juniors + 1 SeniorLead`
2. `core / non-core criterion`
3. `只有核心 criterion 衝突才送 senior`
4. `Stage 1 title/abstract -> Stage 2 full text`
5. `paper-specific semantic trap routing`
6. `F1` 作為 paper 的主評估指標

白話講：

- 原 paper 有 `decomposition`
- 原 paper 有 `multi-agent`
- 原 paper 有 `adjudicator`

但它**沒有**我們之前想像的那種：

- 手工挑重點 criterion
- 再讓部分 case selective route 到 senior

---

## 9. 如果要在本 repo 走 `paper-faithful A`，最低限度要保留哪些骨架

### 必須保留

1. `criteria -> aligned QA questions`
2. `3 個 primary QA models`
3. `每個 model 都回答同一組問題`
4. `可選的 debate 變體`
5. `獨立 adjudicator 變體`
6. `明確區分 primary models 與 adjudicator`

### 不能偷換成別的東西

1. 不准把 `3 primary QA models` 改講成 `2 juniors`
2. 不准把人工指定 `core criterion` 說成原 paper 的 question decomposition
3. 不准把 repo 的 stage-split full-text flow 包裝成 paper 原法

---

## 10. 對本 repo 的直接含義

如果我們現在說：

> `#2` 一律採 `paper-faithful A`

那意思就應該是：

- 我們之後討論 `#2`，要以 `question-level QA decomposition + 3 primary QA agents + optional debate/adjudication` 為骨架

而不是：

- `2 juniors + SeniorLead`
- `core/non-core criterion`
- `手工 senior route gate`

也就是說：

> **`criterion ledger` 可以保留，但它必須回到對齊問題、逐題回答、再聚合的 paper-faithful 骨架；不能再混進人工 core-routing。**

---

## 11. 本 repo 目前應標記為 `絕對不行` 的混稱

以下混稱一律視為錯誤：

1. 把 `Akinseloyin 2026` 寫成 `2 juniors + 1 SeniorLead`
2. 把 `core/non-core criterion` route gate 寫成 paper 原法
3. 把 `title/abstract + full-text stage split` 寫成 paper 原法
4. 把 repo extension 寫成 paper-faithful reproduction

---

## 12. 來源

### Paper

- OUP 論文頁面：<https://academic.oup.com/biomethods/article/doi/10.1093/biomethods/bpag006/8460762>

### Code

- GitHub repo：<https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening>
- README：<https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/README.md>
- Questions generator：<https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/GPT_Questions.py>
- Initial QA：
  - <https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/Claude.py>
  - <https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/GPT.py>
  - <https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/Gemini.py>
- Debate：
  - <https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/Claude_2.py>
  - <https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/GPT2.py>
  - <https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/Gemini_2.py>
- Adjudicator：<https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/Adjudicator.py>
- Ranking：<https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/Rank.py>
- Metrics：<https://github.com/Ope-Akinseloyin/Multi_LLM-Citation-Screening/blob/main/work.py>
