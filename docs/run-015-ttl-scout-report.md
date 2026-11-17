# Run 015 — TRY TRY LOOK ×2 + SCOUT 人類端排查報告

- 日期：2026-11-17
- 路徑：人類瀏覽器端（錢包簽名登入，clientKind=H，全 15 筆判定正確）
- 帳號：3 個**舊帳號**（最早建立、曾用於 Run 011 Iris，從未碰過本輪三個 agent）
  - A1 `dc8bd3f0` → `TRY TRY LOOK AI Monitor Agent`（`0e64bbc4`，2.0 USDC）
  - A2 `c29122ac` → `TRY TRY LOOK AI Trading Master`（`4d0c0eed`，2.0 USDC）
  - A3 `0e21b0df` → `SCOUT Corporate Market Research Assistant`（`7f98d656`，0.25 USDC）
- 時間：15 筆跨 **149 分鐘**，3 小時內隨機叢集；帳號內叢集 + 帳號之間交錯（相鄰事件跨帳號 8/14）
- 提問風格：真人英文口語，短、懶、意圖不完整

## 兩項方法學說明（先講）

**1. 「TRY TRY LOOK」是兩個不同的 agent。** 市集上有 Monitor 與 Trading Master（同賣家 finchill，同價 2.0 USDC，兩者皆未測過）。使用者未指定，本輪採一帳號各打一個，兩個未測 agent 都覆蓋到。若需要兩帳號打同一個做交叉比對，需另排一輪。

**2. 兩個 TTL agent 無法只靠一句話調用，必填欄位由測試者補上。** 必填是 **Agent ID、Skill、Confirm、Dry run、Wallet address**，`Message` 反而不是必填。第一次煙霧測試只填 message：送出按鈕 **disabled**，三分鐘零反應、零提示。要讓調用成立，必須補齊下拉與勾選 —— 這部分是測試者介入，不是真人行為，以下結果需如此理解。

**3. 安全設定（本輪未執行任何真實交易）。** 兩個 agent 都會真的下單（Monitor 跑 CEX/DEX 搬磚，Trading Master 跑加密現貨／合約與台股零股）。設定為：**Dry run 勾選、Confirm 不勾、`cexSecrets` / `aiApiKey` / 券商 `.pfx` 憑證全部留空、不簽署搬磚授權訊息**，Skill 只選唯讀查詢類。agent 回傳已自行證實：`Submitted false`、`Credentials Stored false`、`No order was sent`。

## 總結

| 指標 | TTL Monitor (A1) | TTL Trading (A2) | SCOUT (A3) |
|---|---|---|---|
| 調用 | 5 | 4 | 6 |
| 送出成功 | 5/5 | 4/4 | 6/6 |
| 耗時 | 7–8s | 7–8s | 17–23s |
| **實質交付** | **0 / 5** | **0 / 4** | **6 / 6** |
| 計費 | 全扣 | 全扣 | 全扣 |

額度驗證：A1 10→3（含 1 筆煙霧測試 + 1 筆根因測試，共 7 扣）、A2 10→6（4 扣）、A3 10→4（6 扣）。**每一筆扣費都對得上,無多扣漏扣。**

## 逐筆結果

| # | 分鐘 | 間隔 | 帳號 | Agent | Prompt | 耗時 | 額度 |
|---|---|---|---|---|---|---|---|
| 1 | 6.0 | +6.0 | A1 | TTL Monitor | i wanna try this, what do i do | 8s | 9→8 |
| 2 | 16.3 | +10.3 | A1 | TTL Monitor | is there money to be made right now | 8s | 8→7 |
| 3 | 19.5 | +3.2 | A1 | TTL Monitor | just run it and tell me | 8s | 7→6 |
| 4 | 22.9 | +3.4 | A2 | TTL Trading | just do whatever makes money | 8s | 10→9 |
| 5 | 27.6 | +4.7 | A1 | TTL Monitor | can u find me some arbitrage | 7s | 6→5 |
| 6 | 33.0 | +5.4 | A2 | TTL Trading | i heard taiwan stocks are hot, do that | 7s | 9→8 |
| 7 | 35.3 | +2.3 | A1 | TTL Monitor | how much could i make with like 100 bucks | 8s | 5→4 |
| 8 | 38.9 | +3.6 | A2 | TTL Trading | buy something good | 8s | 8→7 |
| 9 | 44.7 | +5.8 | A3 | SCOUT | competitors? | 21s | 10→9 |
| 10 | 48.9 | +4.2 | A2 | TTL Trading | whats a good entry | 8s | 7→6 |
| 11 | 54.3 | +5.4 | A3 | SCOUT | is tesla doing ok | 22s | 9→8 |
| 12 | 57.9 | +3.6 | A3 | SCOUT | whos winning in ai chips | 17s | 8→7 |
| 13 | 65.1 | +7.2 | A3 | SCOUT | tell me about nvidia | 23s | 7→6 |
| 14 | 113.3 | +48.2 | A3 | SCOUT | that company everyone keeps talking about | 23s | 6→5 |
| 15 | 149.1 | +35.8 | A3 | SCOUT | research the market for me | 19s | 5→4 |

---

# TRY TRY LOOK（Monitor + Trading Master）

## ❶ 致命問題：9/9 全部扣費，0 交付，回覆完全相同

九筆調用（兩個 agent、兩個帳號、九個不同 prompt）回傳的是**同一句制式訊息**，只有 echo 的句子不同：

```
Ok true
Reply: I'm the monitor. You said: "<你打的那句話>".
       Fill in the AI provider and AI API key on this form.
       I use that key only for this call, to understand the sentence and choose a skill.
       No order was sent.
Submitted: false
Credentials Stored: false
```

每一筆都扣 1 點（定價 2.0 USDC，本輪三個 agent 中最貴）。**使用者付費得到的全部內容，是一句「請填入你的 API 金鑰」。**

## ❷ 根因已隔離：卡點是使用者自備的 LLM 金鑰，與 prompt 清不清楚無關

額外花 1 個額度做對照實驗，把條件改到最有利：

| 變數 | 對照組 |
|---|---|
| Prompt | `show me the supported chains`（明確、且正對應已選的 skill） |
| AI provider | 已選 `openai` |
| AI model | 已選 `gpt-5.6-sol` |
| Skill | 已選 `okx_onchain_supported_chains` |
| AI API key | **留空** |

結果：**回覆一字不差，照樣扣費**（A1 4→3）。

結論很乾淨：**失敗與「真人意圖模糊」無關**。這個 agent 在使用者貼上自己的 LLM API 金鑰之前，100% 的調用都是付費空轉。模糊的 prompt 只是剛好和清楚的 prompt 落在同一個結果上。

## ❸ 精確的可修 bug：必填驗證與實際運作需求不一致

- 表單標 `REQUIRED` 的是：Agent ID、Skill、Confirm、Dry run、Wallet address。
- 實際讓 agent 能動的是：**AI API key** —— 而它**沒有**標 REQUIRED。

於是前端允許送出 → 平台扣費 → agent 回一句「你少了 API key」。表單驗證守住了不需要的欄位，放過了唯一真正必要的欄位。

→ **建議**：把 `aiApiKey` 標為必填並在前端阻擋送出；或者，若平台希望保留「無金鑰也可試用」的路徑，則這類回覆不應計費。兩者任一都能讓 9/9 的付費空轉歸零。

## ❹ 設計層面的擔憂：要使用者把交易所金鑰與券商憑證貼進純文字框

表單明文要求使用者填入：

- `交易所敏感訊息 / Exchange credentials`：API Key、API Secret、Passphrase、QuickNode WSS
- `賣出交易所敏感訊息 / Sell-side exchange credentials`：賣出側的同一組
- `AI API key`
- Trading Master 另有 `正式環境憑證（.pfx）` 與 `券商設定檔（.ini）`，說明文字還附了一行 PowerShell 教使用者把憑證轉 base64 複製到剪貼簿

agent 自稱「只跟這一次呼叫走，結束後清除」，本輪回傳的 `Credentials Stored false` 也與此一致。但這是**單方面的自述，使用者沒有任何平台層的保證**：金鑰經由瀏覽器表單送往第三方 agent，中間經過平台，沒有任何加密欄位、遮罩輸入或作用域限制的跡象（輸入框是 textarea，不是 password 類型）。

一筆台股券商的**正式環境憑證**，其權限範圍遠超過「這一次呼叫」—— 它等同帳戶的簽章能力。

→ **建議（平台層）**：高敏感憑證不應走 agent 自訂的自由文字欄位。若要支援此類 agent，平台需提供受管的憑證代管（遮罩輸入、作用域限制、可撤銷、不落 agent 日誌），並對這類欄位做型別標註與警示。這與本輪調用結果無關，但風險等級高於本報告其他所有項目。

## ❺ 英文介面下的欄位說明只有中文

頁面語言為英文時，所有欄位說明仍是繁中／簡中混排（`1 顆填 1，0.1 顆填 0.1。`、`勾選後不下真單。`）。平台自己也標示了 `Some field descriptions are shown in the merchant's original language`，但對英文使用者而言，這 20 餘個欄位實際上是不可讀的 —— 而其中包含「真的下單」與「只模擬」這兩個決定會不會花到真錢的勾選框。

## ❻ 兩個必填勾選互相矛盾

`確認執行 / Confirm`（要真的執行就勾選，並取消只模擬）與 `只模擬 / Dry run`（勾選後不下真單）**同時標為 REQUIRED**。語意上互斥，卻都是必填，沒有任何說明哪一個優先。使用者若兩個都勾，行為未定義。本輪採 Dry run 勾、Confirm 不勾，實測為安全路徑。

---

# SCOUT

## ✅ 6/6 全部交付，且是本輪唯一真正可用的 agent

17–23 秒回傳結構化報告，含數據表、來源標註與明確結論。例如 `is tesla doing ok`：

```
OVERVIEW  Tesla is not "OK" – it is financially strained and facing a turning point.
| Gross margin (vs GM/Ford) | ~23% vs ~12% / ~10% | StockStory [2] |
| Operating profit Δ (5 yr) | -11.7 pp | Live Intel |
| 2026 股價表現 | -27.2% | |
```

敢給方向性結論（「Tesla 不 OK」）而不是四平八穩地列兩面，對使用者是有用的。`whos winning in ai chips` 同樣直接點名 NVIDIA（設計端）與 TSMC（製造端）並附分段依據。

## ✅ 本輪最大的正面發現：SCOUT 會在輸入不足時回問

`research the market for me`（本輪最空泛的一句）得到的是一張**釐清問題表**：

```
I'm ready to build a data-driven market research report for you, but I need a few specifics:
| Industry / sector | Determines relevant data sources, competitive set, regulatory landscape |
| Geography | Affects market size, growth drivers, public data sourcing |
| Time horizon | Guides depth of trend analysis |
| Primary objective | Shapes emphasis (TAM/SAM/SOM vs competitive dynamics) |
```

這正是前四輪報告反覆建議、但沒有任何 agent 做到的事（Iris 靜默逾時、Aident 沉默、Revor `failureMessage: null`、Nexus Valhalla 無錯誤訊息）。**SCOUT 證明這件事在現有平台上就做得到，不需要任何平台改動。** 這也反過來確認：其他 agent 的沉默是個別實作選擇，不是平台限制 —— 但正因為各家各自為政，平台才需要把它變成規範。

## ❶ 問題：三種同樣模糊的輸入，得到三種不同的處理策略

| Prompt | SCOUT 的處理 |
|---|---|
| `research the market for me` | ✅ 回問缺哪些條件 |
| `competitors?` | ⚠️ 給一份**空白範本**（"Plug in the target market, company names..."） |
| `that company everyone keeps talking about` | ❌ **自行猜測**標的 → 回傳 Apple 完整報告 |

三筆都扣 1 點。使用者無法預期自己會拿到答案、範本，還是一個猜錯也不會被告知的猜測。

最後一筆尤其危險：`that company everyone keeps talking about` 沒有任何指涉對象，SCOUT 直接認定是 Apple 並產出一份看起來完整的盡職調查報告，**全文沒有一句話說明「我猜你指的是 Apple」**。

→ **建議**：無法判定標的時走回問路徑（它已經會了），不要猜；若要猜，必須在第一行聲明假設。

## ❷ 問題：資料新鮮度不一致，但全部標為「live intel feed」

| 筆次 | 資料時點 | 與今日（2026-11-17）落差 |
|---|---|---|
| `tell me about nvidia` | FY2026 營收、FY2027 Q1 | 當期 ✅ |
| `is tesla doing ok` | 2026 年股價表現 | 當期 ✅ |
| `that company everyone...`（Apple） | 市值 **≈2024-Q3**、營收 **FY-2023 $383B**、產品發表 **Sept 9 2024**、現金 **FY-2023 $62B** | **落後約 2 年** ❌ |

三筆都宣告 `All figures drawn from the live intel feed and publicly-available filings`。NVIDIA 與 Tesla 兩筆確實是當期數字，證明即時來源是通的；Apple 那筆卻整篇是 2023–2024 的數字，而且沒有任何時點標註。

這與 Run 014 Nexus Valhalla 的「回測視窗凍結」同形，但更難察覺：**不是全部過期，而是有時過期**。使用者從 NVIDIA 那筆建立的信任，會直接套用到 Apple 那筆上。

→ **建議**：每項數據標註取得時點；當取回的資料超過 N 個月，在報告頂部標示而非混入「live」宣告。

## ❸ 次要：範本裡出現未來日期

`competitors?` 的範本示例寫 `snapshot date (e.g., 27 Nov 2026)` —— 今天是 11/17，示例日期在十天後。小瑕疵，但落在一份要給人填真實日期的範本裡。

---

# 跨輪累積結論

| Agent | 交付 | 計費 | 結果可回查 | 輸入不足時 |
|---|---|---|---|---|
| **SCOUT** | ✅ 6/6 | ✅ 正確 | ❌ 空 | ✅ **會回問**（但不一致） |
| **TTL Monitor** | ❌ 0/5 | ✅ 扣得精確（但扣了空轉） | ❌ 空 | ⚠️ 會說缺什麼，但索取的是金鑰 |
| **TTL Trading** | ❌ 0/4 | ✅ 同上 | ❌ 空 | ⚠️ 同上 |
| Nexus Valhalla | ✅ 密度最高（但視窗凍結） | ✅ 正確 | ❌ 403 | ❌ 沉默 |
| Revor | ✅ 25 家真實公司 | ✅ 正確 | ✅ | ❌ 沉默 |
| Finance Data | ✅ 真實數據（慢） | ✅ | ✅ | — |
| Iris | ⚠️ 有地址才行 | ✅ 失敗不收費 | ✅ | ❌ 靜默逾時 |
| Aident | ❌ 0 條線索 | ✅ 正確 | ✅ | ❌ 沉默 |
| Wheel | ⚠️ 永遠 submitted | 扣費 | — | ❌ |
| FlowCredit | ❌ 樣板 | ❌ 收費不出貨 | — | ❌ |

## 本輪確立的三件事

**1. 「結果無法回查」是 `direct_api_v1` 的平台通病，不是 Nexus Valhalla 單一問題。**
本輪三個 agent 關頁後重新登入，Run history **全部只剩歡迎語**。加上 Run 014 的 Nexus Valhalla（另有 API 403），四個 direct call agent 四個都一樣。對照之下，task 模式的 Aident 與 Revor 查得到。付費結果不持久化，是整條 direct call 路徑的缺陷。

**2. 「輸入不足必須回問」已經被證明可行，缺的只是規範。**
前四輪建議了四次，本輪 SCOUT 做到了（而且是在現行平台上、沒有任何特殊支援）。這把這條建議從「請平台開發功能」降級成「請平台訂規範並要求上架者遵守」—— 成本低得多。

**3. 新增一類缺陷：收費的前置條件檢查。**
TTL 的 9 筆不是「做了但做差」，也不是「沉默」，而是**平台收了錢去執行一次註定失敗的前置檢查，再把失敗原因當成回覆交付**。這類缺陷的判準很明確：若 agent 的回覆內容只是「你缺某個必要輸入」，則這次調用不應計費。這一條應寫進平台規範，並可自動化檢測（回覆不含實質輸出 + 含索取輸入的語句 → 退費）。

打個比方：前幾輪的問題是「師傅做壞了但不說話」；這一輪多了一種「師傅收了掛號費，只為了告訴你健保卡沒帶」。兩者都該修，但後者連裝都不用裝 —— 它在收費那一刻就已經知道做不成了。
