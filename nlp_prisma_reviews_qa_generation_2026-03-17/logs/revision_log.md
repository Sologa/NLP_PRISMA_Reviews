# Revision Log

## Round 0 — 初稿
1. **這一版的核心設計原則**  
   先把每篇 SR 的原始 eligibility 拆成「metadata-only / title-abstract observable / full-text-only」，再直接生成 QA question set，而不是先重寫 criteria。
2. **這一版最大的問題**  
   初稿容易把某些 paper 的特定負向例子（例如 2409 的 process prediction、2511 的 ratings conversion、2307 的 audio-only output）寫得太像 general rule；另外 metadata 與 semantic QA 的分層還不夠穩。
3. **下一輪要修什麼**  
   強化「paper-specific negative family 只能留在該 paper QA」的約束，並把 metadata checks 與正文 QA 徹底分開。

## Round 1 — 第一輪自我批判
1. **這一版的核心設計原則**  
   把 Stage 1 嚴格限制在 title/abstract observable evidence，凡是不穩定可觀測的條件全部 defer 到 Stage 2；同時要求每題都有 state / missingness 欄位。
2. **這一版最大的問題**  
   雖然做了 stage split，但一些 paper 的 Stage 2 仍然在暗示最終 verdict，且 conflict handling 還不夠清楚；另外對 criteria 稀疏的 paper（如 2507.07741、2405.15604）仍有過度補寫風險。
3. **下一輪要修什麼**  
   去掉任何 verdict 語氣，加入顯式的 `conflict_note`、`resolves_stage1` 邏輯，並對 criteria 稀疏的 paper 採 conservative QA。

## Round 2 — 第二輪修正
1. **這一版的核心設計原則**  
   將 General Prompt 與各 paper QA 都改成 synthesis-ready schema：question、expected answer form、quote requirement、location requirement、state、missingness、Stage 2 conflict note；且明示不得把 retrieval gate、historical hardening、hidden guidance 寫回 criteria。
2. **這一版最大的問題**  
   部分 prompts 雖已不直接要求 include/exclude verdict，但還缺少對「workflow support ≠ formal criteria」的明確保護；2511 / 2409 這種 fragile review 還需要更強的 anti-contamination wording。
3. **下一輪要修什麼**  
   在 final 版中加入 source-faithful guardrails，明文禁止把 operational hardening、source reputation、year/citation retrieval filters 等偷渡成 canonical criteria。

## Final — 最終版
1. **這一版的核心設計原則**  
   最終版以 source-faithful QA generation 為中心：先完整閱讀 SR PDF，再抽出 metadata-only、Stage 1 observable、Stage 2 canonical/confirmatory 三層訊息；僅生成 evidence-extraction QA，不生成 verdict；所有 hardening 僅能以 workflow support 身分存在。
2. **這一版最大的問題**  
   某些原始 SR（尤其 2405、2507.07741）本身 criteria 較寬或較稀疏，因此 Stage 2 多半是 confirmatory relevance QA，而不是密集 hard-criteria closure。這不是缺陷，而是 source-faithful 的結果。
3. **下一輪要修什麼**  
   若後續要接 repo runtime，可再把這些 QA 問題集映射到 evidence synthesis object 與 reviewer handoff schema，但仍不得回寫成新的 production criteria。
