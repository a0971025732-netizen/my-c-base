# Run 014 — Nexus Valhalla 人類端排查報告

- 日期：2026-11-16
- 路徑：人類瀏覽器端（錢包簽名登入，clientKind=H，全 15 筆判定正確）
- Agent：`Nexus Valhalla: build, backtest and deploy your AI trading agents`，`02afef6f-2db9-4e54-a19b-5ad1d7d518c3`，by **trainflow**，`DIRECT CALL`（Direct API V1），單價 0.8 USDC，免費額度 10
- 選定方式：從未測且不會對外撥打電話的 agent 中隨機抽出
- 帳號：3 個全新錢包 — C1 `75bbed70`（4 筆）、C2 `1c468c1b`（6 筆）、C3 `a014bd1b`（5 筆）
- 時間：15 筆跨 **236 分鐘**，4 小時內隨機叢集（最短間隔 1.8 分、最長 51.0 分）
- 平台頁面自述：Offers completed 16、Success rate 76.2%、Avg. response ~11.7s、Rating 4.3（1 則評價）

## 本輪的方法學偏差（先說明）

使用者要求「各用英文調用」。**這個 agent 沒有任何文字輸入框** —— 整個介面只有三個必填下拉（Days / Model / Symbol），沒有 textarea、沒有對話框。所以「真人用英文模糊表達」這個維度在此 agent 上無法施測。

替代作法：把「真人的隨意」表現成**不看說明、隨手亂選的參數組合**，涵蓋 18 種可能組合中的 11 種。這是偏離原要求的替代,在此明確標示,而非默默置換。

## 總結

| 指標 | 結果 |
|---|---|
| 送出成功 | **15 / 15** |
| 回傳結果 | **13 / 15**（約 15 秒內） |
| 逾時無結果 | 2 / 15（183s / 185s，超過公告的 2 分鐘上限） |
| 計費正確 | ✅ 只有成功回傳才扣，逾時 0 扣費 |
| 交付品質 | ✅ 真實、逐筆、可驗證的回測明細 |
| **致命問題** | ❌ **回測視窗被凍結在 2026-11-02，與今天差 13 天** |

額度驗證（跑完後讀頁面）：C1 10→7、C2 10→4、C3 10→6，**合計 13 次扣費 = 13 次成功回傳**。計費與實際交付完全一致。

## 逐筆結果

| # | 時間(分) | 間隔 | 帳號 | Symbol | Days | Model | 耗時 | 額度 | 結果 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.8 | +1.8 | C1 | EURUSD | 2d | deepseek-v4-flash | 18s | 10→9 | ✅ |
| 2 | 52.8 | +51.0 | C1 | BTCUSD | 2d | deepseek-v4-flash | 18s | 9→8 | ✅ |
| 3 | 59.8 | +7.0 | C1 | EURUSD | 1d | deepseek-v4-flash | 15s | 8→7 | ✅ |
| 4 | 67.3 | +7.5 | C2 | BTCUSD | 2d | deepseek-v4-flash | 16s | 10→9 | ✅ |
| 5 | 69.2 | +1.9 | C2 | EURUSD | 1d | qwen3-30b-a3b | 14s | 9→8 | ✅ |
| 6 | 71.8 | +2.6 | C2 | EURUSD | 1d | qwen3-30b-a3b | 15s | 8→7 | ✅ |
| 7 | 107.5 | +35.7 | C1 | BTCUSD | 1d | qwen3-30b-a3b | **183s** | 7→7 | ❌ 逾時 |
| 8 | 121.5 | +14.0 | C2 | BTCUSD | 2d | gpt-4o-mini | 15s | 7→6 | ✅ |
| 9 | 124.6 | +3.1 | C2 | EURUSD | 2d | qwen3-30b-a3b | 16s | 6→5 | ✅ |
| 10 | 137.4 | +12.8 | C2 | XAUUSD | 1d | deepseek-v4-flash | 17s | 5→4 | ✅ |
| 11 | 141.3 | +3.9 | C3 | EURUSD | 1d | qwen3-30b-a3b | 16s | 10→9 | ✅ |
| 12 | 148.0 | +6.7 | C3 | XAUUSD | 2d | gpt-4o-mini | 16s | 9→8 | ✅ |
| 13 | 160.2 | +12.2 | C3 | XAUUSD | 2d | gpt-4o-mini | 16s | 8→7 | ✅ |
| 14 | 207.2 | +47.0 | C3 | XAUUSD | 1d | gpt-4o-mini | **185s** | 7→7 | ❌ 逾時 |
| 15 | 235.2 | +28.0 | C3 | EURUSD | 2d | gpt-4o-mini | 17s | 7→6 | ✅ |

## ✅ 做對的三件事

### 1. 交付是真的，而且密度很高

每筆回傳逐筆交易明細與完整績效指標，例如 XAUUSD 1d：

```
Trades  short 3894.78 → 3919.23  SL  pnl -244.50  R -1.00    exit_reason sl
        long  3946.52 → 3948.05  --  pnl  +15.61  R +0.16    exit_reason eod_flat
Metrics Trades 2 | Wins 1 | Losses 1 | Win rate 0.5 | Total r -0.8393
        Max dd r 1 | Expectancy r -0.4196 | Realized usd -228.89
        Peak equity 10000 → Finish equity 9771.11 | Arena pass false
Diag    Timeframe M30 | Bars 454 | Warmup bars 408 | Data source CAR | Parse fails 0
```

含進出場價、停損停利、R multiple、出場原因、權益曲線起訖、暖身 bar 數與資料來源。**不同 symbol / days 回傳的內容確實不同**，不是樣板。這是目前測過交付密度最高的 agent。

### 2. 計費正確

13 次成功扣 13，2 次逾時 0 扣費。與 Aident、Revor 一致，優於 FlowCredit。

### 3. 速度穩定

13 筆成功全部落在 **14–18 秒**，變異極小，與頁面公告的 ~11.7s 量級相符。

## ❶ 致命問題：回測視窗被凍結在兩週前

**每一筆**回應都帶著同一組過期時間戳：

| 欄位 | 值 | 今天 |
|---|---|---|
| `Cache` | 2026-11-03T06:02 ~ 14:44 | 2026-11-16 |
| `Window End` | 2026-11-02 | — |
| `Prompt brief` | "a 1-day replay ending **2026-11-03T00:00:00+00:00**" | — |

也就是說：使用者選「Days = 1」，預期拿到的是**最近一天**的回測；實際拿到的是 **2026-11-02 那一天**的回測，落後 13 天，而且這個落差每過一天就多一天。

這對一個回測產品是**產品定義層級的失效**，不是資料新鮮度的小瑕疵：

- 回測的全部價值在於「用這個策略跑最近的市況會怎樣」。固定跑兩週前的某一天，等同於交付一個與使用者意圖無關的答案。
- UI 完全沒有提示。欄位叫「Days」，不叫「Replay date」，也沒有任何地方寫明視窗終點是固定的。使用者付了 0.8 USDC，拿到看起來很專業的報表，不會想到日期是錯的。
- 連續兩次選同一組參數（#12 與 #13，XAUUSD 2d gpt-4o-mini），結果是同一份快取。付兩次費、拿同一份東西，使用者無從得知。

→ **建議（最高優先）**：若視窗確實綁定快取，UI 必須顯式顯示「回測區間：2026-10-30 ~ 2026-11-02（快取於 2026-11-03）」，並在快取超過 N 天時阻擋計費或標示為過期；若意圖是滾動視窗，則是後端快取金鑰未納入當日日期的 bug。

## ❷ 結果無法回頭查，API 直接拒絕

關掉頁面後，使用者再也拿不回自己付費買到的結果：

- 重新登入同一帳號開啟 run 頁 → **Run history 區塊是空的**，只剩歡迎語。
- 用同一帳號查 `/api/agent-market/tasks/{id}` → **HTTP 403**，`AGENT_MARKET_ACCESS_DENIED` / `"This run is unavailable."`
- 其餘路由（`/invocations/{id}`、`/runs/{id}`、`/invocations/{id}/result`）皆 404，代表 `tasks/{id}` 是對的路由，是**存取被拒**而非不存在。

對照 Aident 與 Revor，同一支 API 以帳號自身身分查詢是可以拿到 task 內容的。此處付費者查詢自己的 run 被拒，是明確的權限或持久化缺陷。13 筆付費結果目前等同不存在。

→ **建議**：direct call 的結果必須與 task 模式一樣持久化並列入 Run history；`AGENT_MARKET_ACCESS_DENIED` 若是刻意設計，也不該套用在 run 的發起人身上。

## ❸ 逾時沒有任何錯誤訊息

#7 與 #14 跑了 183 / 185 秒（公告上限 2 分鐘），頁面沒有出現任何錯誤、提示或重試入口，就只是停在原處。不扣費是對的，但使用者端看到的是「我按了送出，然後什麼都沒發生」。

這與 Run 011 Iris 的靜默逾時、Run 013 Revor 的 `failureMessage: null` 是**同一條跨 agent 缺陷**：平台在失敗路徑上一律沉默。

## ❹ 統計口徑會誤導人

#1（EURUSD 2d）回傳：`Trades 1 | Wins 1 | Losses 0 | Win rate 1 | Arena pass true`。

整個回測視窗只成交 1 筆，就報出「勝率 100%、Arena 通過」。樣本數為 1 的勝率沒有統計意義，但介面把它和樣本數 23 的結果以同樣格式並列。對一個會被拿來決定是否投入真錢的產品，建議在樣本數低於門檻時抑制勝率顯示或標註不可靠。

## ❺ 「部分範例無法安全對應到此輸入表單」—— 第三次出現

```
Some examples cannot be safely mapped to this input form and are hidden.
Complete the published fields; missing parameters are not guessed.
```

這段文字此前已在 **TrainFlow** 與 **Aident** 上看到，本輪是第三個。Nexus Valhalla 與 TrainFlow 同屬賣家 `trainflow`。新使用者最先點的就是「Try an example」，而這條路徑在三個 agent 上都是死的。

這是平台級的表單對應缺陷，不是個別 agent 的設定失誤。

## ❻ DIRECT CALL 的 POST 回應語意不一致（次要）

送出後 POST 回 `202 / awaiting_dispatch`，但結果其實在 15 秒內就渲染到頁面上。`awaiting_dispatch` 與實際行為不符，會讓任何依賴該狀態輪詢的整合方誤判為非同步任務。

（註：本輪前期我自己就因為這個欄位誤判為「無輸出」，後續實際停留在頁面觀察 4 分鐘才確認結果其實早就回來了。）

## 對照既有結論

| Agent | 交付 | 計費 | 結果可回查 | 失敗時是否說明 |
|---|---|---|---|---|
| **Nexus Valhalla** | ✅ 密度最高 | ✅ 正確 | ❌ 403 / 空 | ❌ 沉默 |
| Revor | ✅ 25 家真實公司 | ✅ 正確 | ✅ | ❌ 沉默 |
| SCOUT | ✅ 結構化報告 | ✅ | ✅ | — |
| Finance Data | ✅ 真實數據（慢） | ✅ | ✅ | — |
| Iris | ⚠️ 有地址才行 | ✅ 失敗不收費 | ✅ | ❌ 靜默逾時 |
| Aident | ❌ 0 條線索 | ✅ 正確 | ✅ | ❌ 沉默 |
| Wheel | ⚠️ 永遠 submitted | 扣費 | — | ❌ |
| FlowCredit | ❌ 樣板 | ❌ 收費不出貨 | — | ❌ |

**新增的跨 agent 結論**：前三輪的共通缺陷是「失敗時沉默」。本輪揭露了更麻煩的一類 —— **成功時也會騙人**。Nexus Valhalla 每一項外顯訊號都是綠的（15 秒回應、報表詳盡、計費精確、`Ok true`、`Arena pass`），唯一錯的是沒有顯示在任何地方的日期。使用者沒有任何介面線索可以察覺。

這指向平台規範的第二條缺口：**凡是輸出綁定時間視窗的 agent，必須在結果中顯示該視窗，且平台應對過期快取計費設限。** 第一條缺口（輸入不足必須回問）解決的是使用者白花錢；這一條解決的是使用者花了錢、拿到錯的東西還不知道。
