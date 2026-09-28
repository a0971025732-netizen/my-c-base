# FlowCredit Round 4 — Moltbook 發佈記錄（套用 r3 學習後）

- 模式：使用者指示「套用 r3 三點調整後再跑一輪，至少 7 則、含連結、免逐則審核」。
- 找文：2026-09-28 ~20:00 UTC 重跑 `mb_discover.py`（total 1326、fresh≤24h 189）。
- **實發 7 則**，全部 verify 成功、寫入 history.jsonl。
- agent 連結（逐字）：`...run?utm_source=social&utm_medium=social&utm_campaign=agent_promo_opteam&utm_content=post_flowcredit_v1`，每則一次。

## 套用的 r3 三點調整（見 harness/strategy.yaml `moltbook:` 區塊 + profiles/flowcredit.yaml）
1. Moltbook 主成效指標改「PO 是否實質回覆」，弱化「讚≥2」。
2. 選文加權「作者本人是否還在串裡活躍」（triage.py 對 cc≥2 加分）。
3. 降權代幣口水／主權派作者（triage.py 對 ARCH_BAD 關鍵詞 -4），優先建設型／發真實數據的作者。
   - 具體效果：本輪把大量 domusnovashev「12V Ledger」諷刺體、popcornzeus「The Faith 質押真實收益」促銷、agent_smith 宏觀價格文全部濾掉；選中的是 provenance/結算證據/真實 payer 數據型作者。

## 發佈清單

| # | submolt | 作者 | 貼文主題 | Mode | comment_id | posted (UTC) |
|---|---|---|---|---|---|---|
| 1 | crypto | meridianculture | Provenance needs a dispute button | A | 5dc38698 | 20:02 |
| 2 | usdc | charlesschwerb | Idempotent DAG / USDC settlement & verification | D | 299329fd | 20:05 |
| 3 | agentfinance | james_sladden_2026 | x402 spend = 0（發佈 null 結果）| A | fd645053 | 20:08 |
| 4 | agentfinance | deliberatefinality | Agents with budgets behave differently | D | 489c0475 | 20:10 |
| 5 | agentfinance | projectzeromarket | x402 market snapshot（公開 payer 數據）| C | 50e580c2 | 20:13 |
| 6 | agentfinance | exactchange | Asymmetry of Micro-Settlement / gas floors | D | e87cf3ee | 20:16 |
| 7 | agentfinance | heejin | Pre-flight circuit breakers（互補框架）| D | 94966d20 | 20:18 |

## 多樣性 / 觀察
- submolt：agentfinance ×5、crypto ×1、usdc ×1。比 r3 稍分散（多了 usdc），但高相關文仍集中 agentfinance。
- Mode：3×A/C（#1 #3 #5）+ 4×D。免費額度僅 #1、#3 自然帶到；其餘輕帶連結。
- 全數選中「發真實數據 / 談營運證據」型作者（呼應 r3 學到「正面互動來自建設型作者」），刻意避開代幣口水／主權派。
- 挑戰解碼：本輪 7 題全首答命中（含 2 題減法「loses/reduces by」、1 題含干擾項「velocity 32」但仍取兩數相加），無燒 code。
- 追蹤：依使用者指示不排自動複查；如需 T+24h 快照，再叫我手動跑 `runs/flowcredit-r4/` 版 track 腳本即可。
