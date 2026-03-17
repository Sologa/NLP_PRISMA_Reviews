# ChatGPT 全新對話串修正版指令包

這個 package 是用來修正前一版指令的錯誤。

前一版錯在三件事：

1. 它把目標收窄到 `2409/2511`，但你真正要的是 **general Stage 1 / Stage 2 QA generation prompts**
2. 它沒有要求 **所有 SR 都生成 QA**
3. 它沒有把「一定要詳讀所有 SR 的 PDF」與「最後打包成 zip」寫死

這個修正版 package 改成以下目標：

1. 產出 **兩份 general prompt**
   - 一份用來生成 Stage 1 QA
   - 一份用來生成 Stage 2 QA
2. 要求 ChatGPT **詳讀全部 16 篇 SR 的 PDF**
3. 要求 ChatGPT **對全部 16 篇 SR 都生成 QA**
4. 要求 ChatGPT 最後交付：
   - 報告
   - general Stage 1 prompt
   - general Stage 2 prompt
   - 全部 16 篇 SR 的 QA
   - PDF 閱讀紀錄
   - revision log
   - 並在工具環境允許時打包成一個 zip

## Repo URL

GitHub repo URL：

1. `https://github.com/Sologa/NLP_PRISMA_Reviews`

## Package contents

1. `README_zh.md`
2. `MASTER_PROMPT_zh.md`
3. `ALL_SR_MANIFEST_zh.md`

## 建議使用方式

把整個 package 提供給新的 ChatGPT 對話串。  
若只能貼一個檔案，就貼：

1. `MASTER_PROMPT_zh.md`

但若可以上傳多個檔案，建議把三個檔案都提供給它。

