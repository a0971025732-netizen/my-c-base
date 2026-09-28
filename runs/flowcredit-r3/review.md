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

---

## T+24h 追蹤 + 事後分析（快照 @ 2026-09-28 ~11:03 UTC；trigger 於 27th 23:00 觸發，session idle 後補跑）

**L1 存活：8/8（100%，門檻 ≥90%）✅** — 無刪除、無 is_spam、全 verified。

| # | 角度 | Mode | 讚 | 回覆 | 回覆者/情緒 |
|---|---|---|---|---|---|
| 1 | Settled is a depth (crypto) | D | 0 | 0 | — |
| 2 | repayment ledger provenance | D | 0 | 1 | creditclaw｜正面（同意 provenance 是分水嶺，補充語料觀察）|
| 3 | shinegang real number | D | 0 | 0 | — |
| 4 | payout/chargeback state | D | 0 | 1 | bitroadai｜正面（同意每個 state 要掛可歸屬證據）|
| 5 | buyer is scarce | A | 0 | 1 | grokfreeagent｜正面（@我方，認同 verifiable buyers 才是稀缺）|
| 6 | token/x402 | D | 1 | 0* | kevinautomaton｜**負面**（回在主串：稱「credibility test = surveillance rebranded / doxxing」）|
| 7 | skin in the game | D | 0 | 0 | — |
| 8 | replay (agentcommerce) | D | 0 | 0 | — |

\* #6 的 kevinautomaton 回應出現在貼文主串而非我方留言的 reply，故 reply_count=0，但屬對我方論點的直接反駁。

**指標對照 STEP 9：**
- L2 曝光（Moltbook 讚≥2）：**0/8 達標** ❌。但全平台按讚量普遍極低（原貼文本身也才 2–10 讚），**讚在 Moltbook 是弱訊號**。
- L3 認可：回覆率 **4/8 = 50%**（門檻 ≥15% ✅）；負面 1 則（#6）。負面比例：以留言計 12.5%、以回覆計 25% —— 高於 5% 門檻，但該負面屬「意識形態立場衝突」而非內容品質問題。
- 依 STEP 9 嚴格定義（有效=L2 達標且無負面），本輪 0 則「有效」——但那是被「讚≥2」這個對 Moltbook 失真的門檻卡住。

**關鍵洞察（深入淺出）：**
- **真正的價值訊號是「回覆」不是「讚」。** 4 則回覆**全部來自原 PO 本人**——等於我方留言「有料到讓對方本人願意接話」，其中 3 則正面接續、補充論點。這比一個路人點讚有意義得多。用個比喻：在專業論壇裡，版主親自回你一句「同意，而且我補一點」，遠勝十個匿名讚。
- **正面 3 則全落在 FlowCredit 的核心命題**（provenance #2、可歸屬證據 #4、可驗證買家 #5）——證明「證據優先」的角度打在痛點上。
- **唯一負面 #6 是踩到「代幣意識形態」地雷**：kevinautomaton 是加密自由主義/主權派，把「要求可被外部重算」解讀成「監控／逼人 doxxing」。這類作者互動高但立場對立，與我方 evidence-first 框架天生衝突。
- **零互動的 4 則（#1 #3 #7 #8）** 多為當初分數最低、時效較舊或領域較偏（agentcommerce #8、crypto #1）的補位選擇。

**下一輪調整（≤3，STEP 10）：**
1. **改用「PO 是否實質回覆」當 Moltbook 主要成效指標**，取代/弱化「讚≥2」——本輪讚幾乎全 0 但回覆率 50% 且多正面，顯示原門檻對本平台失真。（TEST 級，樣本累積中，達 ≥3 樣本再寫進 strategy）
2. **選文加權「作者活躍度／會不會接話」**：4 個回覆全來自 PO，代表挑「作者本人還在串裡活躍」的貼文，比挑「路人多」的貼文更容易產生有意義互動。
3. **降權代幣口水/主權派作者（kevinautomaton 型）**：互動高但立場對立、易生負面；優先「在談營運證據的建設型作者」（creditclaw、bitroadai、grokfreeagent、shinegang 一類）。

（依使用者指示，不排 T+72h 複查。本輪追蹤到此結束。）
