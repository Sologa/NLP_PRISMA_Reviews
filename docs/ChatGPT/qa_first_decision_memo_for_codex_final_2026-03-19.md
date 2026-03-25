# QA-first 決策備忘錄（給 Codex 的專業版）

## 結論先行

我的判斷是：還有且只剩下一次值得做的合法微調。它必須窄到只碰 2409 的 Stage 2 外掛 policy，而且只測一件事：保留 explicit preprint / non-peer-reviewed 直接負證據，撤掉這次 follow-up 裡會壓掉 recall 的 target/closure 收緊。這一輪如果還回不到 0.8333，就停。

## 1. Current-State Recap

1.1 目前 production runtime 仍然是 `scripts/screening/runtime_prompts/runtime_prompts.json`。這一點在 `AGENTS.md`、`docs/chatgpt_current_status_handoff.md`、`screening/results/results_manifest.json` 三處都一致。

1.2 目前 production criteria 仍然是 `criteria_stage1/<paper_id>.json` 與 `criteria_stage2/<paper_id>.json`。`criteria_jsons/*.json` 只是歷史參考，不是 current production criteria。

1.3 目前 metrics authority 也沒有改。`2409` 與 `2511` 仍然用 `stage_split_criteria_migration` 的 metrics files；所以今天所有 QA-first 實驗都只能拿來跟這個 current baseline 比，不能直接自稱取代 production。

1.4 workflow invariants 也沒有被改掉。Stage 1 仍是兩位 junior reviewer；兩位都 `>=4` 直接 include；兩位都 `<=2` 直接 exclude；其他一律送 `SeniorLead`；`SeniorLead` 必須保留。

1.5 因此，這次 QA-first 相關 bundle 的定位都很清楚：它們是 experiment-only branch，不是 production replacement。

## 2. Verified Interpretation Of The Latest Report

先把你要求我先驗證的 7 件事說清楚。整體上，7 件事都成立，但第 1 點要加一個註解：這裡的 hygiene clean 指的是 final outputs 的 protected title/topic literal leakage 已清到 0，不是說整個 rerun 過程完全沒有 validation retry。

2.1 `v1 second-pass` 已把 hygiene 清乾淨：成立。second-pass 報告把 `2409` topic leak 與 `2511` title/topic leak 都判成 PASS，final outputs 的 exact-literal hits 為 0。要加的註解是：`2511` 的 run manifest 還是記錄了 validation failures，這比較像 retry / validation 過程訊號，不等於 final contamination 還在。

2.2 `2511` 在 `v1 second-pass` 下明顯比 v0 好：成立。`qa+synthesis` 的 Combined F1 從 v0 的 `0.8519` 升到 second-pass 的 `0.8727`，Stage 1 F1 也從 `0.8727` 升到 `0.8772`。但它仍然沒有超過 current production 的 `0.7692`。

2.3 `2409` 在 `v1 second-pass` 下顯著變差：成立。`qa+synthesis` 的 Combined F1 從 v0 的 `0.8333` 掉到 `0.7500`，也低於 current production 的 `0.8235`。這不是小波動，是整條 shared repair 線在 `2409` 上還沒站穩。

2.4 `2409 stage2 follow-up` 在不動 global layer 的前提下是可執行的：成立。follow-up framing 與 report 都明說，這輪是透過既有 `STAGE_SPECIFIC_POLICY_MD` hook，把一個 `2409` 專用、Stage 2 專用、`qa+synthesis` 專用的外掛 policy 掛進去，沒有改 shared template semantics、global policy、production runtime prompt 或 formal criteria。

2.5 但 `2409 stage2 follow-up` 只能把 precision 拉高，無法把 Combined F1 救回 `0.8333`：成立。Combined precision 從 second-pass 的 `0.7000` 拉到 `0.8333`，但 Combined recall 從 `0.8571` 掉到 `0.7143`，最後 Combined F1 只有 `0.7692`。

2.6 因此目前不能宣稱 shared patch 已經穩定：成立。second-pass 的 shared repair 已經證明 hygiene repair 有效，也證明 `2511` 的 defer-overfire 有被拉回來；但同一輪又把 `2409` 拉壞，所以 shared patch 不能叫 stable。

2.7 也不能宣稱只靠 `2409` Stage 2 external policy 就能救回 `2409`：成立。follow-up 明確失敗，自己的 exit decision 也說得很直接：這條外掛 policy 值得保留為『失敗但有訊號』的分支，但不能說它已經救回 `2409`。

3.1 對整條 QA-first experiment 線來說，最新的 `2409 stage2 follow-up` 其實不是成功報告，而是一份把問題範圍再縮小一次的報告。它成功驗證的不是『2409 已經救回來』，而是『在 global/shared layer 完全凍結時，Stage 2 paper-specific external policy 的確可以把 precision 往上拉，但這一版 policy 的副作用是 recall 掉太多』。

3.2 它否定掉的說法有兩個。第一，不能再說 second-pass 之後只要補一條 `2409` Stage 2 closure policy，`2409` 就會自然回到 v0 的 `0.8333`。第二，不能再把現在這條 shared patch 當成已經 ready to scale 的共用解。

3.3 它跟 v0、v1 first-pass、v1 second-pass 的差異也很清楚。v0 與 v1 first-pass 都曾經把 `2409 qa+synthesis` 的 Combined F1 放到 `0.8333`，但 first-pass 還有 hygiene 問題。v1 second-pass 把 hygiene 清乾淨，卻把 `2409` 拉到 `0.7500`。這次 follow-up 再把 precision 拉高，卻只回到 `0.7692`。也就是說，latest report 的真正意義不是『快成功了』，而是『只靠這條 Stage 2 external policy 還不夠，而且它的好處與壞處已經分得很清楚了』。

### 2.4 指標總表

#### 2409.13738

| 版本 | Stage 1 F1 | Combined F1 | Combined Precision | Combined Recall | 解讀 |
| --- | ---: | ---: | ---: | ---: | --- |
| current production | 0.7500 | 0.8235 | 0.7000 | 1.0000 | 現行 production 參考線。 |
| v0 qa+synthesis | 0.7119 | 0.8333 | 0.7407 | 1.0000 | 首次 QA-first 高點；但當時還沒有後來的 hygiene/global repair。 |
| v1 first-pass | 0.5753 | 0.8333 | 0.7407 | 1.0000 | Combined 沒掉，但 Stage 1 collapse，且 hygiene 未完全乾淨。 |
| v1 second-pass | 0.6774 | 0.7500 | 0.7000 | 0.8571 | hygiene 清乾淨，但 2409 明顯惡化。 |
| 2409 stage2 follow-up | 0.6897 | 0.7692 | 0.8333 | 0.7143 | precision 上升、recall 下滑，仍救不回 0.8333。 |

#### 2511.13936

| 版本 | Stage 1 F1 | Combined F1 | Combined Precision | Combined Recall | 解讀 |
| --- | ---: | ---: | ---: | ---: | --- |
| current production | 0.7407 | 0.7692 | 0.9091 | 0.6667 | 現行 production 參考線。 |
| v0 qa+synthesis | 0.8727 | 0.8519 | 0.9583 | 0.7667 | v0 主要靠高 precision。 |
| v1 first-pass | 0.6383 | 0.8571 | 0.9231 | 0.8000 | Combined 比 v0 略高，但 Stage 1 defer flood 太重。 |
| v1 second-pass | 0.8772 | 0.8727 | 0.9600 | 0.8000 | 相對 v0 明顯更好；hygiene 也乾淨。 |

## 3. What Paths Are Still Legally Open

4.1 還合法、而且還有資訊價值的實驗路徑，只剩一條真的值得談：再做一次極窄的 `2409` Stage 2 micro-adjustment。它必須完全沿用現有 stage-specific policy hook，不碰任何 shared/global/production 檔。內容也不能再是『更強的 closure hardening』，而只能做一個更乾淨的 ablation：保留已被驗證有用的 explicit preprint / non-peer-reviewed publication-form direct negative，撤掉或放鬆這次 follow-up 裡會壓掉 recall 的 target/closure wording。

4.2 這條路為什麼不違規：因為它仍然是 experiment-only、paper-specific、Stage 2 specific、`qa+synthesis` only，而且走的是既有 `stage_specific_policy_manifest.yaml` hook，不是修改 formal criteria，也不是改 global policy，更不是去動 production runtime。

4.3 這條路為什麼還有資訊價值：因為目前這次 follow-up 同時混了兩種效果。第一個效果是 publication-form explicit negative，這看起來是真的有用；第二個效果是 target/closure 收得太緊，這看起來是真的傷 recall。再做一次更窄的 ablation，資訊價值就在於把這兩件事拆開。如果拆開之後還是不行，就可以很有把握地說：在 freeze 條件下，`2409` 這條路真的到頭了。

4.4 這條路的主要風險也很明確。第一，它大概率只會是小幅修正，不是大翻盤。第二，如果 rerun 還會混進 stage-level drift，解讀會變髒。第三，一旦這次還是救不回 `0.8333`，就沒有再往下做第四條 patch 的正當性了。

4.5 除了這一條以外，另一條合法且合理的路其實就是不再 patch，直接整理結論。這不算實驗，但它是完全合法、而且已經足夠 defensible 的決策路徑。理由是：最新 follow-up 已經把『Stage 2 external policy 只能修 precision、救不回整體』這件事證得很清楚。

### feasible remaining experiment

存在，但只剩一個值得做的 micro-adjustment：`2409`、Stage 2、`qa+synthesis`、外掛 policy-only。再寬一點就開始踩到 freeze 邊界，再窄不到這個程度就沒有足夠資訊價值。

### decision threshold

停止 patch 的門檻應該是：最後這個 clean ablation 仍無法把 `2409` Combined F1 拉回至少 `0.8333`，或結果依然無法乾淨歸因於 stage2-only policy。之所以說現在已經很接近這個點，是因為 follow-up 已經證明：在 freeze 條件下，stage2 external policy 可以調 precision，但單靠它還不能把整體線救回來。

## 4. What Paths Should Be Ruled Out Now

5.1 再動 global/shared layer：現在就該排除。這是你明講的 freeze 條件，而且 current repo state 也沒有授權這樣做。任何建議如果偷偷建立在改 global template semantics、global policy、production runtime、production criteria 之上，都是違規。

5.2 現在就跑 `qa-only`：不值得做。second-pass 與 follow-up 都還沒有把 `2409 qa+synthesis` 這條 production-nearer 路線站穩，現在去跑 `qa-only` 只會把實驗樹再長出去，但不會回答眼前最重要的決策問題。

5.3 現在就跑四篇 regression / stability pass：不值得做。這一輪 shared patch 對 `2409` 還沒有過關，現在擴跑只會把一個還沒定稿的 patch 拿去做更大面積的驗證。

5.4 再做更強的 `2409` closure hardening：應排除。這次 follow-up 已經證明更強的 closure 會先把 precision 拉上來，再把 recall 壓下去。往更硬的方向推，基本上只會更糟。

5.5 任何把 derived hardening 回寫成 formal criteria 的路：應排除。這違反 current methodology rule，也會把這條 QA-first 線重新變成 criteria-supertranslation 線。

5.6 任何試圖拿這次結果直接宣稱 shared patch stable、或宣稱 `2409` 已被 stage-specific Stage 2 policy 救回來：都應排除。現在的證據根本不支持這兩句話。

## 5. Read-This-First File List

6.1 最少必讀。

`AGENTS.md`、`docs/chatgpt_current_status_handoff.md`、`screening/results/results_manifest.json`、`screening/results/2409.13738_full/CURRENT.md`、`screening/results/2511.13936_full/CURRENT.md`、`screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/REPORT_zh.md`、`screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/REPORT_zh.md`。這組就夠你重新建立 current state，並理解 latest decision point 到底卡在哪裡。

6.2 要追根因再讀。

`screening/results/qa_first_v0_2409_2511_2026-03-18/run_manifest.json`、`screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/REPORT_zh.md`、`screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/run_manifest.json`、`screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/run_manifest.json`、`screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/run_manifest.json`、`screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json`、`screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`。這組會把數字鏈補齊，方便你對比 v0、v1 first-pass、v1 second-pass、follow-up 到底各自做了什麼。

6.3 只有真的要做下一輪微調才讀。

`qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/EXPERIMENT_FRAMING.md`、`qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/2409_stage2_closure_policy.md`、`qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/stage_specific_policy_manifest.yaml`、`screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/2409.13738__qa+synthesis/latte_fulltext_review_results.json`、`screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/latte_fulltext_review_results.json`。這組不是拿來重新理解 current state，而是拿來做最後一次非常窄的 policy ablation。

## 6. Final Recommendation

7.1 我的最終建議選項是：`再做一次極窄的 2409 micro-adjustment`。

7.2 但我要把限制講得非常死。這次 micro-adjustment 只能改 `2409`、只能改 Stage 2、只能改 `qa+synthesis`、只能改外掛 policy 文件，不能發明新 hook，不能碰 shared/global layer，不能碰 production runtime，不能碰 formal criteria，不能順便擴到 `2511`、`qa-only`、四篇 regression。

7.3 這次 micro-adjustment 應該窄到只剩一個問題：保留 explicit preprint / non-peer-reviewed 直接負證據；把這次 follow-up 裡會讓 `goossens2023extracting`、`qian2020approach`、`vda_extracting_declarative_process`、`neuberger2023beyond` 這類 case 掉 recall 的 target/closure wording 拿掉或放鬆。換句話說，這不是再做『更強 hardening』，而是把這次 follow-up 裡已經被證明有效的 publication-form 子規則，跟明顯有害的 recall-killing 子規則拆開。

7.4 decision threshold 也要先寫死。如果這一輪還是回不到 `0.8333`，或者結果沒有辦法乾淨地解釋成這個 stage2-only ablation 的效果，而是又混進別的 drift，那就直接停止 patch，整理結論。不要再做第四輪、不要再找新的 global 藉口、不要再把限制偷偷放寬。

7.5 也就是說：我不是建議你延長這條線；我是建議你只做最後一個還有資訊價值的 clean ablation。這一輪跑完，不管成敗，都應該把 decision 收斂。

## Appendix: evidence anchors read

1. `AGENTS.md`
1. `docs/chatgpt_current_status_handoff.md`
1. `screening/results/results_manifest.json`
1. `screening/results/2409.13738_full/CURRENT.md`
1. `screening/results/2511.13936_full/CURRENT.md`
1. `criteria_stage1/2409.13738.json`
1. `criteria_stage2/2409.13738.json`
1. `criteria_stage1/2511.13936.json`
1. `criteria_stage2/2511.13936.json`
1. `scripts/screening/runtime_prompts/runtime_prompts.json`
1. `screening/results/qa_first_v0_2409_2511_2026-03-18/REPORT_zh.md`
1. `screening/results/qa_first_v0_2409_2511_2026-03-18/run_manifest.json`
1. `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/REPORT_zh.md`
1. `screening/results/qa_first_v1_global_repair_2409_2511_2026-03-18/run_manifest.json`
1. `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/REPORT_zh.md`
1. `screening/results/qa_first_v1_global_repair_second_pass_2409_2511_2026-03-19/run_manifest.json`
1. `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/REPORT_zh.md`
1. `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/run_manifest.json`
1. `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/stage1_f1.json`
1. `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/combined_f1.json`
1. `screening/results/qa_first_v1_2409_stage2_followup_2026-03-19/2409.13738__qa+synthesis/latte_fulltext_review_results.json`
1. `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/manifest.json`
1. `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/EXPERIMENT_FRAMING.md`
1. `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/2409_stage2_closure_policy.md`
1. `qa_first_experiments/qa_first_experiment_v1_2409_stage2_followup_2026-03-19/templates/policies/stage_specific_policy_manifest.yaml`
1. `screening/results/2409.13738_full/stage1_f1.stage_split_criteria_migration.json`
1. `screening/results/2409.13738_full/combined_f1.stage_split_criteria_migration.json`
1. `screening/results/2511.13936_full/stage1_f1.stage_split_criteria_migration.json`
1. `screening/results/2511.13936_full/combined_f1.stage_split_criteria_migration.json`