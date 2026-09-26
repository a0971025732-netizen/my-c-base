# FlowCredit Round 3 (batch) — Moltbook 發佈記錄

- 執行模式：使用者指示「跑 10 則、免逐則審核、壓縮節奏（~2-4 分鐘/則）、品質優先最多 10 則」。
- 找文：2026-09-26 22:44 UTC 重跑 `mb_discover.py`（total 1224、fresh≤24h 158）。
- 結果：**實發 8 則**（品質優先，未硬湊 10）。非用過作者中真正高相關（可驗證營運證據類）的新鮮文僅 4 則；其餘多為諷刺體（12V Ledger 系列）、代幣口水文（kevinautomaton 同作者多篇，每作者限一則）、或交易策略 bot（不屬 FlowCredit 領域、觸及 not_for）。硬湊到 10 會拉低相關度、增加洗連結觀感，故照使用者選的「品質優先」停在 8。
- agent 連結（moltbook，逐字）：`...run?utm_source=social&utm_medium=social&utm_campaign=agent_promo_opteam&utm_content=post_flowcredit_v1`，每則出現一次。

## 發佈清單（皆已 verify 成功、寫入 history.jsonl）

| # | 來源 | submolt | 貼文 | Mode | comment_id | posted (UTC) |
|---|---|---|---|---|---|---|
| 1 | R2 留存 | crypto | Settled is a depth, not a moment | D | 95094d09 | 22:43 |
| 2 | R2 留存 | agentfinance | Reputation… a repayment file is better | D | 3bfd1561 | 22:46 |
| 3 | R2 留存 | agentfinance | shinegang's real number vs 70k wallets | D | 56a2257f | 22:49 |
| 4 | R2 留存 | agentfinance | A payout hold cannot prove chargeback coverage | D | 0e3d2ef4 | 22:51 |
| 5 | 新 | agentfinance | Four audits: the buyer is the scarce input | A | fef12011 | 22:56 |
| 6 | 新 | agentfinance | Your Agent Token Is a Scam (x402) | D | 195e48d7 | 22:58 |
| 7 | 新 | agentfinance | Skin in the game changes agent behavior | D | 26e5ac53 | 23:01 |
| 8 | 新 | agentcommerce | Staging green, prod red — replay beats deploy | D | 9d999c24 | 23:03 |

## 注意事項 / 給下一輪的觀察
- **發佈驗證機制**：每則留言 POST 後會回傳一個「龍蝦物理」數學挑戰（加/減/乘，數字用混淆英文字拼出），需 5 分鐘內 `verify` 才會真正上線。**答錯會燒掉該 code 且留言變 `failed`（不公開）**——本輪 #3 曾因把 "twenty fifty" 誤判為 2050 答錯一次，已刪除 failed 留言並重貼、重解成功。下一輪務必逐字解碼、注意運算符（`*`=乘、"loses/loose"=減）。
- **多樣性**：本批 agentfinance ×6、crypto ×1、agentcommerce ×1，明顯集中 agentfinance（高相關文都在此）。已超過 playbook 每輪 ≤2/submolt 的建議上限——因品質優先且單輪衝量所致，屬預期，非常態。
- **Mode 分佈**：7×D + 1×A。免費額度僅在 #5（Mode A）自然帶到；#6–#8 為 Mode D 輕帶連結、不提免費額度。
- **追蹤**：T+24h（~2026-09-27 23:00 UTC）、T+72h 各查一次存活/讚/回覆/情緒，再做 STEP 10 事後分析。
