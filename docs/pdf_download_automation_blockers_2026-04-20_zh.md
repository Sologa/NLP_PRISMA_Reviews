# PDF 自動下載受阻說明

日期：2026-04-20

## 背景

在本次 `refs/` 缺失 PDF 補齊作業中，除了使用一般命令列下載、腳本下載與 headless browser 下載之外，也額外做了人工比對與人工瀏覽器確認。

需要特別記錄的是：

- 部分論文**並不是沒有公開 PDF**
- 也**不是 metadata / bib / tex source 對應錯誤**
- 問題在於：站點對「無人值守下載」與「真人瀏覽器下載」採用了不同處理路徑

因此，「open access」不等於「可穩定全自動下載」。

## 本次受影響案例

### 1. `wei2020study`

- 本地條目標題：
  - `A study of deep learning approaches for medication and adverse drug event extraction from clinical text`
- 對應 PDF 端點：
  - `https://pmc.ncbi.nlm.nih.gov/articles/PMC6913210/pdf/ocz063.pdf`
- 人工比對結論：
  - 與本地 `bib/metadata` 為同一篇
  - 首頁資訊對上 `JAMIA`, `27(1)`, `2020`, `13–21`

### 2. `mcneer2021building`

- 本地條目標題：
  - `Building longitudinal medication dose data using medication information extracted from clinical notes in electronic health records`
- 對應 PDF 端點：
  - `https://pmc.ncbi.nlm.nih.gov/articles/PMC7973457/pdf/ocaa291.pdf`
- 人工比對結論：
  - 與本地 `bib/metadata` 為同一篇
  - 首頁資訊對上 `JAMIA`, `28(4)`, `2021`, `782–790`

### 3. `brhanemeskel2022amharic`

- 本地條目標題：
  - `Amharic Speech Search Using Text Word Query Based on Automatic Sentence-like Segmentation`
- 對應 PDF 端點：
  - `https://www.mdpi.com/2076-3417/12/22/11727/pdf`
- 人工比對結論：
  - 與本地 `bib/metadata` 為同一篇
  - 首頁資訊對上 `Applied Sciences`, `2022`, `12(22):11727`

## 為什麼 agent 不能穩定自動下載

### 類型 A：PMC / NIH 的下載驗證頁

受影響：

- `wei2020study`
- `mcneer2021building`

對這兩篇，直接請求 PDF 端點時，伺服器不是回 PDF，而是回一個 HTML 頁面，頁面標題為：

- `Preparing to download ...`

頁面內容會載入 NIH/PMC 的 JavaScript 驗證流程，並要求先完成 cookie / challenge 驗證，再提供真正的 PDF。

這代表：

- `curl`
- `urllib`
- 一般 shell script
- 簡單的 headless 抓取

都可能只拿到 HTML 防護頁，而不是 PDF bytes。

因此，這不是「找不到 PDF」，而是站點明確區分了：

- 真人瀏覽器下載
- 自動化／無人值守下載

### 類型 B：Publisher / CDN 的 WAF 或 403 阻擋

受影響：

- `brhanemeskel2022amharic`

對這篇，MDPI 的 PDF 端點在本環境下對命令列與一般自動化請求回：

- `403 Forbidden`

這類行為通常來自 CDN / WAF 規則。實務上常見現象是：

- 一般瀏覽器可正常開啟 landing page
- 命令列或某些自動化請求型態被擋下

所以這也不是「沒有 OA PDF」，而是**OA PDF 不保證可被 unattended downloader 直接抓取**。

## 對全自動流程的含義

如果未來要把 PDF 補齊完全納入 pipeline，不能假設：

1. 有 DOI 就能自動抓
2. 有 PMC/MDPI 頁面就能自動抓
3. open access 就代表一定有穩定直鏈

更準確的假設應該是：

1. 有些來源可穩定自動抓
2. 有些來源需要特定下載協議或頁面動作
3. 有些來源在特定時間點、特定 IP、特定 client 型態下會阻擋 automation

## 本次觀察到的三種下載模式

### 模式 1：可直接自動抓

例如部分 Semantic Scholar mirror、部分 publisher PDF 直鏈、部分 institutional repository。

此類來源會直接回：

- `Content-Type: application/pdf`
- PDF 檔頭 `%PDF-`

### 模式 2：可自動抓，但要模擬站點實際下載行為

例如本次的 `bittar2019text`。

該篇一開始看起來像是 IOS Press 的 PDF 直鏈不可用，但實際檢查文章頁後發現：

- 真正下載入口是表單 `POST /Download/Pdf`
- 並非單純 `GET /pdf/doi/...`

在依照站點實際流程送出 POST 後，最後仍可程式化取得 PDF。

這種情況說明：

- 有些「看似不能自動下載」的來源，其實只是不能用錯的 URL 模式下載

### 模式 3：人工瀏覽器可下載，但無法保證全自動

本次 3 篇受阻案例屬於這一類。

這類情況的特徵是：

- metadata 與 paper identity 已確認
- 也能定位到正確 PDF 端點
- 但端點對 automation 回 challenge page 或 403

## 建議的 pipeline 設計

若未來要做穩定的 PDF 補齊流程，建議採分層 fallback：

1. 先查本地現有 PDF 庫
2. 再查可穩定直抓的鏡像與 repository
3. 再查 publisher 是否有可程式化下載入口
4. 若命中 challenge / WAF / anti-bot，標記為 `manual_required`

不建議把最後一層站點防護硬塞成「一定要全自動過關」的前提，因為這取決於：

- 站方規則
- 當下 IP / 網段
- User-Agent / cookie 狀態
- JS challenge 機制是否變更

這些條件都不屬於 repo 內可完全控制的穩定工程邊界。

## 本次結論

截至 2026-04-20，本次 3 篇受阻論文的情況可總結為：

- `wei2020study`：
  - 同篇已確認
  - 受 PMC/NIH `Preparing to download ...` 驗證頁阻擋
- `mcneer2021building`：
  - 同篇已確認
  - 受 PMC/NIH `Preparing to download ...` 驗證頁阻擋
- `brhanemeskel2022amharic`：
  - 同篇已確認
  - 受 MDPI / CDN `403 Forbidden` 阻擋

因此，這三篇之所以需要人工瀏覽器下載，原因是：

- **站點防護機制阻止了可靠的無人值守下載**
- **不是因為條目對應不明，也不是因為文獻不存在公開 PDF**

