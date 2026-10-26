# Run 010 — 交易/財經類 Agent 多帳號人類端排查報告

- 日期：2026-10-26
- 路徑：人類瀏覽器端（錢包簽名登入，clientKind=H）
- 帳號：3 個（1 舊 + 2 新錢包），一帳號固定一語言，分布於简体中文 / 英文
- 時間分散：A、B 跨 ~2 小時真實時間（第 1、第 2 小時叢集），C 於第 3 小時補跑，整體落在 4 小時窗內三個時段叢集
- 提問風格：模糊、口語、真人隨意打字

## 帳號與調用

| 帳號 | accountId | 類型 | 語言 | 傾向 | 筆數 |
|---|---|---|---|---|---|
| A | `dd3128cc` | 舊 (acct-002) | 英文 | 股市 | 3 |
| B | `d1d9b4de` | 新錢包 | 简体中文 | 加密/交易 | 7 |
| C | `ff68dd08` | 新錢包 | 英文 | 加密/交易 | 4 |

全部 clientKind=**H**（人類端分類正確，錢包簽名登入未被誤判為 agent）。

## 逐筆結果（14 筆）

| 時段 | 帳號 | Agent | 提問 | 結果 | 延遲 | 扣費 |
|---|---|---|---|---|---|---|
| 5.5m | A | TrainFlow | can i still chase eth or nah | NO_MSGBOX | — | 無 |
| 22.4m | A | Maneki | hows aapl doing rn | TIMEOUT / deadline_exceeded | 238s | 無 |
| 26.9m | A | Finance Data | whats nvda like after earnings | ✅ CHARGED | 168s | 9→8 |
| 89.6m | B | TrainFlow | 黄金现在能不能进 白话点 | NO_MSGBOX | — | 無 |
| 93.4m | B | TrainFlow | 原油最近波动大么 | NO_MSGBOX | — | 無 |
| 97.8m | B | TrainFlow | 以太坊 还能追吗 随便看看 | NO_MSGBOX | — | 無 |
| 99.2m | B | Finance Data | 标普500 波动大不大 随便讲 | ✅ CHARGED | 63s | 10→9 |
| 102.7m | B | TrainFlow | 以太坊 还能追吗 随便看看 | NO_MSGBOX | — | 無 |
| 105.8m | B | TrainFlow | 原油最近波动大么 | NO_MSGBOX | — | 無 |
| 116.8m | B | TrainFlow | 以太坊 还能追吗 随便看看 | NO_MSGBOX | — | 無 |
| +1m | C | FlowCredit | what does this onchain addr even do | ⚠️ CHARGED 但不出貨 | 5s | 10→9 |
| +5.8m | C | TrainFlow | oil been volatile or what | NO_MSGBOX | — | 無 |
| +9.2m | C | TrainFlow | can i still chase eth or nah | NO_MSGBOX | — | 無 |
| +13.1m | C | TrainFlow | is gold a buy right now | NO_MSGBOX | — | 無 |

## 各 Agent 排查結論

### ✅ Finance Data Agent（Powerdrill）— 正常，品質佳
2/2 真實出貨，語言完美對齊，能承接模糊口語提問：
- A（英）「whats nvda like after earnings」→ 真實拉取 NVDA Q2 FY2027 財報，revenue $96.2B 超預期 +4.3%、Data Center +117% YoY 等具體數據。
- B（简中）「标普500 波动大不大 随便讲」→ 以「随便聊聊」的口語回覆，給出 VIX≈19.45、近月 +25%、2025 vs 2026 波動區間對比，語氣與提問一致。
- 缺點：延遲偏高（63–168s），但有出貨。

### ❌ Maneki AI（美股分析）— 逾時不出貨
1/1 `deadline_exceeded`（平台側 123s / 我方計 238s），**未扣費**（至少失敗不收錢）。延續先前多次「Maneki 收不出分析」的問題。

### ⚠️ FlowCredit（商業風險情報）— 收費但不出貨
1/1 **扣了 1 credit**，但只回框架樣板文字（"DIRECT RESULT Validated / executed in the protected Runtime"），**沒有任何真實的鏈上地址分析內容**。屬收費不出貨，是本輪最該追的 bug。

### ❌ TrainFlow Nexus — 瀏覽器送不出（10/10 NO_MSGBOX）
全部 10 筆都抓不到訊息框。TrainFlow 的 run 頁**不是對話框 UI**（無 `textarea`，應為 generation/direct_api 表單模式），純瀏覽器自動化的訊息框選擇器對它不適用。
- 雙重意義：(1) 我方驅動限制（需補 generation 表單送出邏輯）；(2) **平台發現——各 agent run 頁互動模式不一致**，對以對話框為前提的自動化/輔助工具不友善。

## 關鍵發現彙總

1. **收費不出貨**再現兩例：FlowCredit（扣費回樣板）、Maneki（逾時，未扣費）。FlowCredit 扣了錢卻無內容，優先追。
2. **Finance Data 是本類唯一穩定出貨**的 agent，且多語言、承接模糊提問能力好。
3. **run 頁互動模式不一致**：對話型（Finance Data/Maneki）vs 表單型（TrainFlow）混用，自動化與輔助工具難以統一接入。
4. 人類錢包登入路徑 clientKind 全部正確判為 H，無誤判。
