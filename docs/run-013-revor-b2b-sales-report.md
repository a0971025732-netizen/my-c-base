# Run 013 — Revor AI Global B2B Sales Agent 人類端排查報告

- 日期：2026-11-15
- 路徑：人類瀏覽器端（錢包簽名登入，clientKind=H，全 8 筆判定正確）
- Agent：`Revor AI Global B2B Sales Agent`，`da36c1ff-f1a3-4258-bff1-c0fa4e3edae1`，`interactionMode = task`（對話框型），單價 0.5 USDC，免費額度 10
- 選定方式：從 10 個未測且 online 的 agent 中隨機抽出
- 帳號：2 個全新錢包 — B1 `71415bff`（英，5 筆）、B2 `1b597c29`（英，3 筆）
- 時間：8 筆跨 119 分，3 小時內隨機叢集（間隔 +2.1 / +27.8 / +20.2 / +2.8 / +4.9 / +2.0 / +33.5 / +25.9 分）
- 提問風格：真人外貿賣家口吻，短、懶、意圖不完整

## 總結：目前測過交付品質最好的 agent

| 指標 | 結果 |
|---|---|
| 送出成功 | **8 / 8** |
| 真實交付 | **4 / 8**（每筆 25 家公司） |
| 被拒 | 4 / 8（`AGENT_MARKET_RUNTIME_REJECTED`） |
| 計費正確 | ✅ 只有 completed 扣費 |

額度驗證：B1 10→8（2 completed / 3 rejected）、B2 10→8（2 completed / 1 rejected）。**4 次成功 = 4 次扣費，被拒 0 扣費。**

## 逐筆結果

| # | 帳號 | Prompt | 狀態 | rev | 交付 |
|---|---|---|---|---|---|
| 1 | B1 | whos buying auto parts overseas | `completed` | 29 | ✅ 25 家 |
| 2 | B2 | whos buying auto parts overseas | `completed` | 25 | ✅ 25 家 |
| 3 | B1 | who imports this stuff, any idea | `failed` | 2 | ❌ REJECTED |
| 4 | B1 | we export furniture, who should i talk to | `failed` | 2 | ❌ REJECTED |
| 5 | B2 | find companies that buy from china | `completed` | 21 | ✅ 25 家 |
| 6 | B2 | need a list of leads for my factory | `failed` | 2 | ❌ REJECTED |
| 7 | B1 | help me with sales idk where to start | `failed` | 2 | ❌ REJECTED |
| 8 | B1 | any buyers in the us for led lights | `completed` | 20 | ✅ 25 家 |

## ✅ 做對的三件事

### 1. 交付是真的

每筆成功回傳 25 家真實公司，含可驗證網址、產業標籤、業務描述，以及逐條匹配依據：

```
PR Distribution  | prdistribution.ca | 魁北克市汽車/工業用品進口商，45 年
                 | match 60 | criteria: buys_auto_parts_overseas (partial, 1 ref)
Worldpac Canada  | worldpac.ca       | 進口 OE 品質汽車替換件
                 | match 75 | criteria: buys_auto_parts_overseas (partial, 2 refs)
```

並附搜尋過程統計：`verified` / `qualified` / `verify_cap: 125` / `stop_reason: goal_reached`。對照 Aident（0 條線索）與 FlowCredit（樣板文字），這是實質交付。

### 2. 計費正確

被拒的 4 筆完全不扣費。與 Aident 一致、優於 FlowCredit。

### 3. 有合理的輸入護欄

無法轉成檢索查詢的提問會被**拒絕執行**，而不是硬跑後交出 0 條結果。這在設計上優於 Aident 的「收費 + completed + 零交付」。

## ❶ 主要問題：被拒時完全不說原因

4 筆 `failed` 的 `failureMessage` 全是 **null**。平台只給了錯誤碼 `AGENT_MARKET_RUNTIME_REJECTED`，使用者端得不到任何可行動的說明。

對照成功與失敗的分界線（非常一致）：

| 成功 | 失敗 |
|---|---|
| whos buying **auto parts** overseas | who imports **this stuff**, any idea |
| find companies that buy **from china** | we export **furniture**, who should i talk to |
| any buyers in the **us** for **led lights** | need a list of leads for **my factory** |
| | **help me with sales** idk where to start |

判準不只是「有沒有提到產品」—— `we export furniture` 有產品仍被拒。真正的判準是**能否改寫成一句明確檢索查詢**：成功的四筆都被轉成了 `Companies buying auto parts overseas`、`Companies that buy from China`、`US buyers of LED lights`。

護欄是對的，**但沉默是錯的**。一句「我需要知道你賣什麼產品、想找哪個市場」就能把 4 次失敗轉成 4 次成功。這和 Run 011 Iris 的結論同形：agent 知道自己缺什麼，卻不開口問。

→ 建議：`RUNTIME_REJECTED` 必須帶可讀的 `failureMessage`，並在 UI 呈現。

## ❷ 次要問題：25 家裡只有少數是完整命中

`returned_count: 25`，但 `progress.full` 只有 **10**（另一筆僅 **1**）。前幾名的 `match.status` 是 `partial`、`matched: 0`，代表部分符合也被塞進名單湊到 25 家。

使用者看到「25 家公司」會認為都是合格線索。建議在輸出中明確區分完整命中與部分命中的數量。

## ❸ 未觸發的邊界（待測）

serviceBoundary 寫明 Email / LinkedIn / WhatsApp 外聯需要先連接發送帳號授權。本輪 8 筆全無授權，但沒有一筆被導向外聯功能 —— 所有成功的都落在 Company Discovery。**「授權前提不滿足」這條路徑本輪未驗證。**

## 對照既有結論

| Agent | 交付 | 計費 | 失敗時是否說明 |
|---|---|---|---|
| **Revor** | ✅ 25 家真實公司 | ✅ 正確 | ❌ 沉默 |
| SCOUT | ✅ 結構化報告 | ✅ | — |
| Finance Data | ✅ 真實數據（慢） | ✅ | — |
| Iris | ⚠️ 有地址才行 | ✅ 失敗不收費 | ❌ 靜默逾時 |
| Aident | ❌ 0 條線索 | ✅ 正確 | ❌ 沉默 |
| Wheel | ⚠️ 永遠 submitted | 扣費 | ❌ |
| FlowCredit | ❌ 樣板 | ❌ 收費不出貨 | ❌ |
| Maneki / TrainFlow | ❌ | — | ❌ |

**跨 agent 的共通缺陷更清楚了**：平台上品質最好與最差的 agent，在「輸入不足時」的行為完全一樣 —— 沉默。Revor 證明了底層能力到位時交付可以很好，所以這不是 agent 能力問題，而是**平台缺少一條「輸入不足必須回問」的規範**。這是單點投入、全站受益的修法。
