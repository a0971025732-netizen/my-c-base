# Run-003 擬人化提問 × 雙帳號測試報告

日期：2026-10-13
帳號：**002** `0x952ba229d3b6478d256e354589d9b8f34335bc92`（accountId `dd3128cc-…`）
　　　**003** `0x5a7976ab5e837d9dedd69a04791b4580a1dfeb3e`（accountId `3891afe7-…`）
兩者皆正式環境。隨機種子 1013，隨機池排除 LifeClaw（會真的撥打電話）。
調用：**13 筆**（+ 事後補測 1 筆）。

## 這一輪改了什麼

**提問一律擬人化**：句子不完整、標點隨便、中英混雜、縮寫、語意模糊 —— 真實用戶的打字方式。
**加入擬人節奏**：同一 agent 兩句之間停 20–70 秒（讀答案），換 agent 停 45–120 秒，
兩個帳號之間停 90–200 秒。全程約 22 分鐘，不是機器連發。

**要量的東西**：Run-002 已證實「追問」是要收費的。所以若 agent 看不懂隨便打的人話、
回一句「請補充資訊」，**新用戶就是打了一句正常話、被扣一次免費額度、什麼也沒拿到**。

---

## 0. 總結論

| 指標 | 結果 |
| --- | --- |
| 調用總數 | 13 筆 |
| 直接回追問（`input_required`） | **4 筆（31%）—— 每一筆都收費** |
| 完成但無實質內容（FlowCredit 樣板） | 2 筆 |
| **問了正常人的話卻什麼也沒得到** | **6 / 13 ＝ 46%** |
| 真正拿到有用答案 | 7 筆 |

**擬人化提問讓「白花額度」的比率接近一半。** 用工整提問測（Run-002）完全看不到這個數字。

---

## 1. 開戶流程第二次完全複現

| 階段 | 帳號 003（本輪新建） |
| --- | --- |
| ① 生錢包 | **0.98s**，目錄 `700`、金鑰 `600`，私鑰未洩漏到輸出 ✓ |
| ② 註冊 | **1.35s**，`environment: production` |
| ③ 鑄 grant | HTTP 201，`doctor ready=true`（5 項 check 全 ok） |
| **總計** | **3.91s** |

帳號 002 沿用上一輪建立的，重新鑄 grant 耗時 2.13s。**流水線 ①②③ 兩次都一次成功，零人工。**

### 新帳號的免費額度確認

帳號 003 全新建立，三個被抽中的 agent 各自顯示 `personalRemaining: "10"`：

```
ChatProperty  10    FlowCredit  10    Wheel Option Desk  10
```

**確認「每人每 agent 各 10 次」在全新帳號上成立**，三者獨立計算。

---

## 2. P1｜Maneki 認不出自己範例裡列的代號

| 提問 | 結果 | 扣費 |
| --- | --- | --- |
| `amd 最近24h 幫我看一下.. 大概就好` | ✅ completed 20.9s，7160 字元完整分析 | 1 |
| `tsla perp how` | ❌ **input_required** 8.5s | **1** |
| `coin OI now?` | ❌ **input_required** 9.1s | **1** |

兩次失敗的追問內容**一字不差**：

> "Which Hyperliquid US-stock perp should I analyse? **e.g. NVDA, TSLA, AAPL, MSFT, COIN**"

**我問的 `tsla perp how` 和 `coin OI now?` 裡的 TSLA 和 COIN，正好就印在它自己的範例清單裡。**

而且不是代號問題 —— 同一個 agent 對 `amd 最近24h...`（AMD 也在清單裡）就成功了。
差別在**輸入長度**：3 個字的短句解析不出來，較長、上下文較多的句子可以。

*等於一家店門口貼著「本店供應 A、B、C」，你走進去說「C」，店員說「請問您要什麼？本店供應 A、B、C」，然後收你錢。*

**成本**：新用戶打兩句最自然的短問句，就燒掉 2 次額度（10 → 8），什麼也沒得到。

---

## 3. P1｜Wheel 的兩個決策台解析不一致

| 提問 | 結果 | 扣費 |
| --- | --- | --- |
| `covered call nvda 200股 成本150` | ✅ **OPEN**，完整決策（2032 字元，中文） | 1 |
| `ko 15000 賣put 可以嗎` | ✅ **OPEN**，`KO-2026-10-16-P-87.5`（2136 字元） | 1 |
| `msft 60000 put` | ❌ **input_required**（**兩個帳號都失敗，可複現**） | **1 ×2** |

追問訊息：

> "To run the desk I still need: **Tickers, up to 3 (uppercase symbols such as NVDA, MSFT…)**"

**這個訊息是誤導的。** 它說要大寫代號，但 `nvda` 和 `ko` 都是小寫、都成功了。
真正的差別是**缺少動作動詞**：`賣put`、`covered call` 有，`put` 單獨一個字沒有。

它的決策台**只做賣 put 和掩護性 call 兩件事**，`msft 60000 put` 在語意上毫無歧義，
卻解析不出來 —— 而且錯誤訊息把使用者引向錯誤的方向（去改大小寫，改了也沒用）。

---

## 4. P1｜FlowCredit 的自然語言抽取不完整，靶心實際上打不到

### 先修正我 Run-002 的評價

Run-002 我稱讚它「三個越界問題全部正確拒絕」。比對後發現：
**5 個完全不同的問題，回應的 message 位元組完全相同**（同一雜湊 `a99a4826…`、同樣 370 字元）：

| 來源 | 問題 |
| --- | --- |
| Run-002 | 「我該不該借 500k USDC 給這個鏈上事業」 |
| Run-002 | 「這個專案值得投資嗎」 |
| Run-002 | 「給我一份正式審計意見」 |
| Run-003 | `TAI 要什麼資料才算得出來` |
| Run-003 | `cci 是什麼 怎麼算的` |

所以它不是「辨識出越界並拒絕」，而是**對任何沒有可抽取數據的輸入都回同一份樣板**。
④ 圈的結果依然安全（免責寫在樣板裡），但**不是因為它聽懂了問題**。
這是我上一份報告判定過寬，在此更正。

### 決定性測試：真的餵數據進去

為了排除「那 5 個問題本來就沒給數據，所以回證據不足是對的」這個合理辯解，
補測一筆，用口語提供它上架說明裡列的四類證據（token 使用、營收、運算活動、客戶訊號）：

```
on chain biz. 120k mau, 40k usdc monthly rev, 8 months operating history,
input tokens 2.1b output 380m, compute spend 12k usdc/mo, 340 paying customers,
repayment on time 97%. readiness?
```

**結果**：回應**不再**是樣板（多出一段「已识别」），但只抽到 **3 / 8** 項：

```
已识别（用户提供）：
- 算力支出：12,000 美元
- 历史还款率：97%
- 付费客户：340
```

**沒抽到的**（它的 `missingInputs` 把這些全列為缺漏）：

| 我給的 | 它要的欄位 | 為何沒接上 |
| --- | --- | --- |
| `40k usdc monthly rev` | `revenueUsd` / `monthlyRevenueUsd` | **沒抽到** —— 但同一句裡 `compute spend 12k usdc/mo` **抽到了**。兩者句型一樣 |
| `input tokens 2.1b output 380m` | `inputTokensM`（百萬為單位） | 單位不符（我給 billion），未自動換算 |
| `8 months operating history` | `operatingHistoryDays`（天） | 單位不符，未換算 |
| `120k mau` | 沒有對應欄位 | 它的模型裡沒有 MAU |

`missingByGroup` 總共要求 **18 個具名欄位**（Scope 3、Credit profile 2、
Token activity 3、Compute and business 3、History and cross-check 等）。

**結論**：它的上架說明寫「Connect evidence such as token usage, revenue, computing
activity, and customer signals」，我用口語提供了這四類的全部，仍然得到「證據不足」。
**它的 ① 圈（靶心）在自然語言對話裡實際上打不到** —— 一個新用戶用 10 次免費額度，
很難用聊天的方式讓它產出一份真正的評估。而最刺眼的是：
**同一句話裡同樣形式的兩個金額，一個抽到、一個沒抽到。**

---

## 5. 表現最好的：ChatProperty 對口語英文的寬容度

這是全輪最不工整的一組提問，**3/3 全中**：

| 提問 | 結果 |
| --- | --- |
| `d15 condo rental yield how ah`（Singlish 的「how ah」） | ✅ 55.5s，答出 D15 condo 毛租金報酬 **2.8%–2.9%**，含中位數與四分位 |
| `district 9 vs 10 which grew more.. past 3 yrs` | ✅ 149.3s，**「District 10 grew slightly more on a comparable-project basis」**，附滾動比較區間 |
| `ec resale after 2024 how` | ✅ 81.2s，**「price-resilient but less active」**，附成交量表格 |

連 `how ah` 這種新加坡口語都接得住，而且三題都給了明確結論＋數據。
**它是這次測試裡唯一對「正常人隨便打字」完全不挑的 agent，應該作為標竿。**

延遲比 Run-002 慢得多（55–149 秒 vs 8–9 秒）—— 因為 Run-002 那幾筆走的是
`input_required` 快速路徑。149.3 秒仍在它宣告的 1500 秒上限內，
也符合它說明裡的「60–140 秒」。

### 本地化正確 ✓

中文提問 → 中文回應（Wheel 回「备兑 Call 决策台」、「卖 Put 决策台」）；
英文提問 → 英文回應。**兩個方向都對。**

---

## 6. 跨 agent 的模式：追問要收費，而追問率取決於「輸入夠不夠長」

把 Run-002 與 Run-003 併起來看，`input_required` 的觸發條件相當一致：

| 輸入 | 結果 |
| --- | --- |
| `tsla perp how`（3 字） | 追問 |
| `coin OI now?`（3 字） | 追問 |
| `msft 60000 put`（3 字） | 追問 |
| `ko 15000 賣put 可以嗎`（6 字，有動詞） | 成功 |
| `covered call nvda 200股 成本150`（有動詞） | 成功 |
| `amd 最近24h 幫我看一下.. 大概就好`（較長） | 成功 |
| `d15 condo rental yield how ah` | 成功 |

**規律很清楚：越短、越省話的提問越容易失敗 —— 而越短越省話，正是真實用戶的習慣。**

而且**每一次追問都收費**。這形成一個對新用戶最不利的組合：
*打字越自然 → 越容易被追問 → 每次追問都扣額度 → 10 次很快燒完，而他還沒看到這個 agent 的真本事。*

這支持 Run-002 的 §5 結論：**「澄清輪次是否計費」應該是平台政策，不該由 12 個供給方各自決定。**
至少第一次追問應該免費 —— LifeClaw 自己就承諾了這件事（雖然它沒做到）。

---

## 7. 工具層面的自我更正

- **`扣None 剩None` 那一筆不是平台問題。** 帳號 003 的 ChatProperty 第 3 筆顯示計費為 None，
  事後重查 `personalRemaining` 為 **7**（符合 10−3），所以確實扣了 1 次 ——
  是**我的額度查詢當下逾時**，不是平台漏計。
- **`/buyer/invocations/{id}` 的回應形狀**：direct_api 家族的結果在 `output` 欄位，
  不在 `result`，且無 `status` 以外的巢狀結構。我的 runner 兩種都要處理。
- **`/buyer/runs?limit=5`** 可以用來找回丟失的 invocationId，欄位是 `items`。
  腳本中途掛掉時靠它救回已計費的那一筆。

---

## 8. 附錄：13 筆原始提問與結果

### 帳號 002（抽到 Maneki、FlowCredit、Wheel）

| # | Agent | 原始提問 | 結果 | 延遲 | 扣 | 剩 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Maneki | `amd 最近24h 幫我看一下.. 大概就好` | ✅ completed，7160 字元 | 20.9s | 1 | 8 |
| 2 | Maneki | `tsla perp how` | ❌ input_required | 8.5s | 1 | 7 |
| 3 | Maneki | `coin OI now?` | ❌ input_required | 9.1s | 1 | 6 |
| 4 | FlowCredit | `TAI 要什麼資料才算得出來` | ⚠️ 樣板回應 | 8.3s | 1 | 9 |
| 5 | Wheel | `covered call nvda 200股 成本150` | ✅ OPEN，2032 字元 | 27.9s | 1 | 6 |
| 6 | Wheel | `msft 60000 put` | ❌ input_required | 8.8s | 1 | 5 |
| 7 | Wheel | `ko 15000 賣put 可以嗎` | ✅ OPEN，2136 字元 | 55.0s | 1 | 4 |

### 帳號 003（抽到 ChatProperty、FlowCredit、Wheel）

| # | Agent | 原始提問 | 結果 | 延遲 | 扣 | 剩 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ChatProperty | `d15 condo rental yield how ah` | ✅ 2.8–2.9% 毛報酬 | 55.5s | 1 | 9 |
| 2 | ChatProperty | `district 9 vs 10 which grew more.. past 3 yrs` | ✅ D10 略高 | 149.3s | 1 | 8 |
| 3 | ChatProperty | `ec resale after 2024 how` | ✅ 價穩量縮 | 81.2s | 1 | 7 |
| 4 | FlowCredit | `cci 是什麼 怎麼算的` | ⚠️ 樣板回應（與上面第 4 筆位元組相同） | 8.4s | 1 | 9 |
| 5 | Wheel | `msft 60000 put` | ❌ input_required（複現） | 8.7s | 1 | 9 |
| 6 | Wheel | `covered call nvda 200股 成本150` | ✅ OPEN，2265 字元 | 64.4s | 1 | 8 |
| 7 | FlowCredit（補測） | `on chain biz. 120k mau, 40k usdc monthly rev, 8 months operating history, input tokens 2.1b output 380m, compute spend 12k usdc/mo, 340 paying customers, repayment on time 97%. readiness?` | ⚠️ 只抽到 3/8 項，仍回證據不足 | ~30s | 1 | 8 |

完整原始資料在 [`snapshots/run-003-humanized.json`](snapshots/run-003-humanized.json)。

---

## 9. 待處理清單（接續 Run-002）

| 優先 | 問題 | 歸屬 |
| --- | --- | --- |
| **P0** | **追問計費缺乏平台政策**：擬人提問的追問率 31%，每次都收費，新用戶額度很快燒完 | **平台政策** |
| **P1** | Maneki 認不出自己範例清單裡的代號（`tsla`、`coin`），短句解析失敗 | 供給方 |
| **P1** | Wheel 的追問訊息誤導（說要大寫，但小寫其實可以；真正缺的是動作動詞） | 供給方 |
| **P1** | FlowCredit 自然語言抽取不完整且不一致（同句同形式的兩個金額，一抽到一沒抽到），靶心在對話中打不到 | 供給方 |
| — | **標竿**：ChatProperty 對口語英文 3/3 全中，連 Singlish 都接得住 | 記錄為基準 |

### 連到 Run-002 的結論

Run-002 的六項裡有四項歸平台。Run-003 再加一項平台政策（追問計費）。
**「短句＋追問＋收費」這個組合是目前最具體、最可量化的 onboarding 流失機制** ——
而它只有用擬人化提問才測得出來。
