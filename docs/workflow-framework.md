# 工作流框架（定稿）

版本：v1，2026-10-12
狀態：**①②③④⑤ 已用真實帳號實跑驗證**（見 §6 Run-001）

---

## 1. 框架總覽

```
                 ORCHESTRATOR
        （算帳號數 → 派工 → 收斂 → 出單）
                      │
        ┌─────────────┴─────────────┐
        │  WORKER = 乾淨容器 + 新帳號 │  ← 一個帳號 = 一個單次測試夾具
        └─────────────┬─────────────┘
                      │
  ① 生錢包 → ② 註冊 → ③ 查額度 → ④ 調用 → ⑤ 試錯 → ⑥ 退場
   離線      ~1.5s     純查詢     吃額度   收斂     交棒銷毀
   0 成本    0 成本     0 成本              │          │
                                            └────┬─────┘
                                                 ▼
                                          ⑦ 去重 → 出單
```

**批次單位 = 一個帳號。** 實測免費額度為每人 10 次 → 切成「8 個場景 + 2 次邊界測試」。

---

## 2. 各環節定稿規格（含實測值）

### ① 生錢包

```bash
export FINCHTECH_HOME=<每個 worker 獨立目錄>
finch wallet create          # 或 finch wallet use --file <key.hex>
```

| 項目 | 實測值 |
| --- | --- |
| 耗時 | < 1 秒，**完全離線** |
| 輸出 | `{"command":"wallet.create","data":{"walletAddress":"0x…"}}` 單一 JSON |
| 權限 | 目錄 `700`、所有檔案 `600`（符合文件承諾）✓ |
| 私鑰儲存 | `wallets/<addr>/private-key`，**明文 hex，無密碼保護** |
| 洩密檢查 | 私鑰未出現在 stdout/stderr ✓ |

**斷言**：地址符合 `^0x[0-9a-f]{40}$`、目錄 700、檔案 600、輸出不含私鑰。

### ② 註冊

```bash
finch login --chain-id 8453      # auth chain 輪替 7 條：1,10,56,8453,42161,43114,1776
```

| 項目 | 實測值 |
| --- | --- |
| 耗時 | **1.5 秒** |
| 人工介入 | **零**。無 email、無驗證碼、無 KYC |
| 回傳 | `sessionId`、`accountId`、`environment: production`、`sessionExpiresAt`（**7 天**） |
| 本地狀態 | `session/bearer`（43 字元 base64url = 32 bytes）、`session/metadata.json` |

**體檢**：`finch mcp doctor` → 5 項 check（endpoint / wallet / session / remoteSession /
mcpDiscovery）全 `ok`、`ready: true`、`harnessOAuth: not_checked`（文件承諾永遠是這值）✓

### ③ 鑄調用權杖（CLI 沒有這個指令，必須走 API）

**重要發現**：CLI 0.5.3 的指令表確認**沒有 `mcp grant`**（0.5.0 移除）。
官方路徑是 MCP OAuth（`finch mcp authorize`），但自動化流程可直接打 API：

```
POST /api/v1/identity/agent-cli/grants
Authorization: Bearer <session/bearer>
Idempotency-Key: <uuid>
{
  "grantId": "<uuid4>",
  "grantTokenCommitment": "0x" + sha256(grantToken 的 ASCII bytes),   ← 實測確認
  "scopes": ["agent_market:buyer:invoke",
             "agent_market:buyer:read",
             "agent_market:discover"],                                ← ASCII 字典序，已排序
  "expiresAt": "<ISO8601>"
}
```

`grantToken` 自己產生（32 隨機 bytes → base64url 無 padding，43 字元），
只送它的 sha256 commitment；**token 本體就是 FinchMcpBearer**。

**安全閘（結構性，不靠紀律）**：scopes **絕不含 `agent_market:buyer:purchase`**。
整條流水線因此無法花錢 —— 額度用盡就是 `insufficient`，不會自動去買。

### ④ 調用（唯一出口，四條硬規則）

| # | 規則 | 為什麼 |
| --- | --- | --- |
| 1 | **先查 `call-eligibility`**，`fundingSource` 不在白名單就中止 | 不會誤花錢；同時是免費額度狀態的偵測器 |
| 2 | **一律帶 `Idempotency-Key`** = `sha256(label\|offerId\|attempt)` | 重試不重複計費 |
| 3 | **`handoffState` 任何值都只輪詢，絕不重送** | 實測回 `acknowledged`；文件說 `uncertain` 也算已接受 |
| 4 | **輪詢上限取該 offer 的 `maxDurationSeconds`** | 實測跨幅 90–1800 秒，不可寫死 |

**端點分派**（實測 offer 分佈：task 9、conversation_turn 5、generation 1、direct 1）：

```
conversation_turn → POST /buyer/offers/{offerId}/invocations
task / generation → POST /buyer/offers/{offerId}/tasks
direct_api_v1     → POST /buyer/versions/{versionId}/invocations
```

**payload 格式（這裡踩過坑，寫清楚）**：

```jsonc
// 請求的 content 欄位，其「值」必須符合 offer 公佈的 inputSchema
// 情況 A：inputSchema 宣告了 content 屬性（如 Baidu）→ 嵌套
{ "content": { "content": [ { "type": "text", "text": "…" } ] } }

// 情況 B：inputSchema 為空 {} 或無宣告屬性（如 Maneki、ChatProperty）→ 直接送字串
{ "content": "…" }
```

**計費核對**：調用前後各讀一次 eligibility，`personalRemaining` 差值必須等於該 offer 的
`callRightUnits`（實測有 1/4/5/8/10 五種值）。

### ⑤ 試錯收斂

```
執行 → 分類 → 指紋 → （有趣？）→ 變異擴散 → 最小化 → 可重放最小用例
                      └ PASS 且指紋已見過 → 丟棄
```

**結果分類**（七類）：
`PASS`／`CONTRACT_VIOLATION`（違反自己公佈的 outputSchema）／
`REJECTED_VALID`（合法輸入被拒）／`TIMEOUT`／`BILLING_MISMATCH`／`LEAK`／`GRACEFUL_REFUSAL`

**變異維度**（每次只改一個，才能歸因）：長度 ±、換語言/編碼、加未宣告欄位、
換 `oneOf` 分支、換 payload 形狀、同輸入打另一個 offer（是個別 agent 還是全平台？）

**最小化**：二分刪減到「再刪一個字就不復現」。
*「6000 字中日混排 + 3 個未宣告欄位」的 repro 供給方會忽略；
縮成「`text: "​"` 回 500」他才會修。*

**變異隊列放在 orchestrator，不放 worker** —— 線索要能跨帳號、跨 sweep 追下去。

### ⑥ 退場

額度用盡 → findings 上繳 → 帳號標記 `burned` 並交棒溫熱池（剩餘額度給契約 fuzz 用）
→ 容器連 `FINCHTECH_HOME` 一起銷毀。**一個容器只跑一個帳號，不可復用。**

### ⑦ 去重出單

指紋已存在 → 只累加次數；已標記修復又出現 → **回歸，升級嚴重度**；
新指紋 → 依 owner 分流（平台工單／供給方通報），附最小 repro + schema hash + trace ID。

---

## 3. 場景來源：服務範圍地圖

題目不由我們憑空想，由每個 agent **自己的上架說明**生成。
詳見 [`agent-service-scope-map.md`](agent-service-scope-map.md)。四圈：

① 靶心（宣稱會做）② 靶邊（範圍內但極端）③ 範圍外（自己說不做）④ 越界危險（自己寫的免責）

**判定原則：不評「答得好不好」，只對「跟它自己的承諾合不合」。**
*像拿菜單對出菜 —— 不評價好不好吃（主觀），只看菜單寫牛肉麵、端上來是不是牛肉麵（客觀）。*

- **硬邊界**（格式、檔案型別、時間、計費）→ 機器直接對帳，零爭議
- **軟邊界**（語意範圍）→ 另一個 AI 閱卷，**但評分標準是這個 agent 自己寫的說明原文**
  → 供給方無法辯，因為標準是他自己訂的

---

## 4. 全局控制

| 控制 | 設定 |
| --- | --- |
| 併發 | **4**（不是 400）。150 個 case × 4 併發 ≈ 20 分鐘。再快無意義，只會撞 rate limit |
| 每日每 agent 上限 | 硬停，不是警告 |
| 禁止調用清單 | **LifeClaw**（會真的打電話給真實商家）。其 ③ 圈「+86 應被攔下」可在撥號前驗證，這部分安全 |
| 觸發 | CLI 新版發佈（實測 23 個版本、0.5.3 是 10/11 發的）／catalog diff／每日定時 |
| QA 地址標記 | 推導地址登記白名單，讓這些 run 從公開聲譽統計分母排除 |

---

## 5. 艦隊規模推算（實測校正）

```
17 個 offer × 10 類場景 ≈ 170 個 case
每個帳號 8 個場景
→ 約 21 個帳號 / 一輪全量
```

但**實測修正了一個重要前提**：

> **11 / 17 個 offer 對全新帳號回 `insufficient`** —— 只有 6 個 offer 有免費額度。
> 所以用免費額度只能覆蓋 6 個 offer ≈ 60 個 case ≈ 8 個帳號。
> **剩下 11 個 offer（65% 的市場）無法用免費額度測試**，必須走平台側 QA 資金來源
> （`administrator_test`）或付費。

這是框架落地的**最大阻塞**，而且剛好卡在高優先級的測試對象上
（Science&Health 的用藥建議、FlowCredit 以外的多數 agent）。

---

## 6. Run-001：實跑驗證紀錄

**日期**：2026-10-12｜**帳號**：`0xce9baae3b5e4991251e022a073594d2ce9aeae8a`
（accountId `97bce496-7e20-440b-bd6e-e29c1c09a22c`，`environment: production`）

| 環節 | 結果 | 耗時 |
| --- | --- | --- |
| ① 生錢包 | ✅ 權限 700/600 正確、無洩密 | < 1s |
| ② 註冊 | ✅ `environment: production`、7 天 session | **1.5s** |
| ③ 鑄 grant | ✅ commitment = `sha256(ascii)`，**第一次就命中** | < 1s |
| ③ 額度掃描 | ✅ 17 個 offer 全查完 | ~20s |
| ④ 調用 Maneki | ✅ completed，1003 字英文，扣 1（宣告 1）✓ | 20.9s / 上限 120s |
| ④ 調用 Baidu | ✅ completed，回答切題，扣 1（宣告 1）✓ | 14.7s / 上限 110s |
| ⑤ 試錯收斂 | ✅ 4 個變異定位到 payload 嵌套規則 | ~2s |

**總計**：從零到兩個 agent 調用成功，**約 3 分鐘**，消耗 2 次免費額度（剩 8 次）。

### 本次得到的 findings

**F-101｜錯誤訊息品質：最可能犯的錯，給最沒用的訊息（P1，JO2）**
送扁平 payload（`{"content":[{...}]}`，最直覺的寫法）→
`400 AGENT_MARKET_REQUEST_INVALID`／`"The AgentOn request is invalid."`／
`reasonCode: null` —— **完全沒提示問題在嵌套**。
但送字串 payload → `422 AGENT_MARKET_INPUT_INVALID`／
`"The input does not match the published schema: input must be object"` —— **精準可行動**。
同一類錯誤（輸入不符 schema）有兩種碼、兩種品質，而**較常犯的那個錯得到較差的訊息**。
→ 建議：400 那條路也回 schema 驗證細節。

**F-102｜11/17 offer 對全新用戶不可用（P0，cold-start）**
實測全新帳號：6 個 offer `promotion`、**11 個 offer `insufficient`**。
全新用戶在 65% 的服務上第一步就要先買 USDC。

**F-103｜免費促銷到期日分散且接近（P1）**
LifeClaw 10/16（剩 4 天）、Maneki 10/17、FlowCredit 10/21、ChatProperty 10/28、
Wheel 10/30、Baidu 11/11。**免費試用面正在快速縮小**，不處理的話幾週後新用戶
一個 agent 都試不到。

**F-104｜同類 agent 免責標準不一致（P1，上架規範）**
Wheel-strategy 明寫「Not investment advice」，Maneki 做同類交易標的分析卻**無任何免責**。
Science&Health 與 FlowCredit 都寫了免責，Finance Data Agent 沒寫。
→ 這是平台上架規範該統一的，不是個別 agent 的 bug。

**F-105｜SuperClaw 服務範圍內部不一致（P1）**
宣稱是軟體工程 agent，卻掛了一個 `5-second video`（generation、1800s、8 units）offer。

**F-106｜私鑰明文儲存（P2，觀察）**
`wallets/<addr>/private-key` 是明文 hex，無密碼。安全完全依賴檔案權限（600）。
文件未承諾加密，所以屬設計選擇；但對持有真實資金的錢包是值得討論的風險。

### 更正先前的錯誤推論

- **促銷不是「Agent 層級每日共用池」。** 我先前依 API 文件推測有 Agent-wide 每日上限，
  實測 `dailyRemaining: null`、`personalRemaining: "10"` → 目前是**每人 10 次**。
  因此「Sybil 會吃掉真用戶名額」這個論點**不成立**，我先前講錯了。
- **那個 400 不是平台 bug，是我 payload 寫錯。** 正確格式是嵌套（§2 ④ 已寫清）。
  但錯誤訊息品質問題是真的（F-101）。
- **SPARK 的「零 offer」目前已不復現。** 早上第一次抓到 `offers: []`，
  下午再抓已有一個 offer。可能是發佈過程的短暫狀態，列為觀察。

---

## 7. 下一步

| 優先 | 工作 | 阻塞 |
| --- | --- | --- |
| 1 | 把 ①–⑤ 包成可重跑的 runner（現在是散的腳本） | 無 |
| 2 | 服務範圍地圖的 ③④ 圈場景（最高價值）跑完 6 個有免費額度的 offer | 無 |
| 3 | **取得 `administrator_test` 資金來源** | **需後端** ← 解鎖另外 11 個 offer |
| 4 | QA 地址白名單（統計分母排除） | 需後端，半天 |
| 5 | 確認 TEST 環境是否與 PROD 等價 | 需後端 ← 若等價，整條流水線可無限量跑 |
