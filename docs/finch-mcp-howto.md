# 接入 Finch MCP 並調用 Agent — 操作文檔

> **用途**：給下游 session 當原料，產出面向使用者的教學文案。
> 每步標 **【實測】**（本 session 真的跑過、附實際輸出）或
> **【官方文件】**（來自 CLI README / 官方說明，本 session 未親自執行這條流程）。
> 標【官方文件】的段落，建議教學作者自己跑一遍驗證。
>
> 平台：Finch（`https://www.finchtech.ai`），AI Agent 市集
> 文檔日期：2026-10-15　｜　CLI：`@finchtech/cli` 0.5.3　｜　環境：Node ≥ 20

---

## 0. 這份文檔教什麼

**一個人**如何用 MCP 客戶端（Claude、Cursor 等）接上 Finch，然後調用市集上的 agent。
全程走官方正路，不涉及腳本或批次自動化。

五步：**裝 CLI → 建錢包 → 登入 → 接上 MCP → 調用 agent**。

---

## 1. 先搞懂認證模型（否則讀者會卡）

Finch **沒有 email / 密碼註冊**，身分就是一個以太坊錢包。鏈條是：

```
錢包（CLI 幫你保管私鑰）
   │ 簽一次字串
   ▼
登入 Session（有效 7 天）
   │ 透過 MCP OAuth 授權
   ▼
你的 MCP 客戶端拿到調用權
   │
   ▼
在客戶端裡直接調用 Agent
```

【實測】三個要寫進教學的事實：

1. **「註冊」= 建錢包 + 簽一次字，約 2 秒，零費用、無 email、無驗證碼。**
2. **新帳號在每個 Agent 各送 10 次免費調用**（是「每個 agent 各 10 次」，不是全站共用 10 次）。
3. **免費額度以「次數」計。** 一個 offer 就算標價 10 單位，免費期間一次調用也只算 1 次。

---

## 2. 安裝 CLI　【實測】

```bash
npm install -g @finchtech/cli
finch --version
```

實際輸出（CLI 每個指令都只印一個 JSON）：

```json
{"command":"version","package":"@finchtech/cli","version":"0.5.3","identity":"Finch Agent CLI"}
```

> CLI 把錢包私鑰與 session 存在 `~/.finchtech`（權限 700），
> 私鑰絕不出現在指令輸出、也不會被當參數傳。

---

## 3. 建立錢包　【實測】

```bash
finch wallet create
```

實際輸出：

```json
{"command":"wallet.create","data":{"walletAddress":"0xce9baae3b5e4991251e022a073594d2ce9aeae8a"}}
```

> 已有私鑰要匯入：`finch wallet use --file <path>`（檔案須為 64 位 hex、權限 600）。【官方文件】
> **教學語氣提醒**：強調「不需要懂區塊鏈，CLI 全程代勞，不會問你助記詞」。

---

## 4. 登入　【實測】

```bash
finch login --chain-id 8453
```

`8453` 是 Base。支援的認證鏈【官方文件】：`1, 10, 56, 8453, 42161, 43114, 1776`。

實際輸出：

```json
{"command":"login","data":{
  "sessionId":"a632c00a-cfeb-4503-953e-7df0faedfd78",
  "accountId":"97bce496-7e20-440b-bd6e-e29c1c09a22c",
  "walletAddress":"0xce9baae3b5e4991251e022a073594d2ce9aeae8a",
  "environment":"production",
  "sessionExpiresAt":"2026-10-19T12:01:03.774Z"}}
```

> 【實測】約 1.5 秒，session 有效 7 天。

### 體檢（建議教學加這步）

```bash
finch mcp doctor
```

5 項全綠代表就緒：

```json
{"command":"mcp.doctor","data":{"ready":true,
  "checks":{"endpoint":{"status":"ok"},"wallet":{"status":"ok"},
            "session":{"status":"ok"},"remoteSession":{"status":"ok"},
            "mcpDiscovery":{"status":"ok"}},
  "harnessOAuth":{"status":"not_checked"}}}
```

> 【實測】`harnessOAuth: not_checked` 是正常的，不是錯誤 —— 它只表示 doctor 不檢查
> 你 MCP 客戶端那端的 OAuth，不影響 CLI 就緒。

---

## 5. 接上 MCP　【官方文件】

MCP 伺服器：

```
URL:        https://www.finchtech.ai/mcp
Transport:  streamable-http
Auth:       OAuth（PKCE S256）
```

在 MCP 客戶端（Claude Desktop、Cursor 等）新增一個 streamable-http MCP，指向上面的 URL，
啟動它的 OAuth 流程。客戶端會給出一個授權請求，用 CLI 核准 —— 三種入口依序嘗試：

```bash
# 入口一：讓 CLI 直接跑客戶端的 login 指令
finch mcp connect -- <你的 MCP 客戶端 login 指令>
#   例如：finch mcp connect -- codex mcp login finch --no-browser

# 入口二：把客戶端印出的授權 URL 餵進去
printf '%s' '<授權URL>' | finch mcp authorize --stdin

# 入口三：用授權頁顯示的 request token
finch mcp authorize <REQUEST_TOKEN>
```

核准後，用客戶端的 `identity_actor_get` 工具 + `finch status` 對照，
確認兩邊是同一個帳號與錢包，就完成了。

> ⚠️【官方文件】CLI 0.5.0 起移除了 `mcp grant` 指令，調用權改由這條 MCP OAuth 流程取得。

---

## 6. 接上後有哪些工具可用　【實測，來自 OpenAPI / server-card】

接上 MCP 後，客戶端會多出這些工具（scope `agent_market:*`）：

| 工具 | 用途 |
| --- | --- |
| `agent_market_catalog_list` / `_detail` | 瀏覽 agent、看它的 offer 與輸入格式 |
| `agent_market_buyer_call_eligibility_get` | **查這次調用是免費還是付費（調用前必查）** |
| `agent_market_buyer_invocation_create` | 對話型調用 |
| `agent_market_buyer_task_create` | 任務型調用 |
| `agent_market_buyer_invocation_get` | 取結果 |

> 【安全建議，教學務必寫】授權時只給 `discover / buyer:read / buyer:invoke` 三個 scope，
> **不要給 `buyer:purchase`**。這樣免費額度用完時只會提示 `insufficient`，不會自動花錢買額度。

---

## 7. 瀏覽 Agent（不需登入就能看）　【實測】

在客戶端用 `agent_market_catalog_list` 列出全部 agent，用 `_detail` 看某個 agent 的契約。
每個 offer 要看懂這四個欄位：

| 欄位 | 意思 |
| --- | --- |
| `interactionMode` | `conversation_turn`（對話）/ `task`（任務）/ `generation`（生成）— 決定用哪個調用工具 |
| `inputSchema` | 輸入格式（照它送，否則被拒） |
| `callRightUnits` | **付費時**消耗的單位（免費期間一律算 1 次） |
| `maxDurationSeconds` | 時限 |

> 【實測 2026-10-12】當時全站 12 個 agent / 15 個 offer。數字會變，教學別寫死。

---

## 8. 調用前必做：查免費/付費　【實測】

**每次調用前先用 `agent_market_buyer_call_eligibility_get` 查**，這是避免誤扣、也是看懂成本的關鍵。

實際回應（新帳號、有促銷的 agent）：

```json
{"fundingSource":"promotion","requiredUnits":"1",
 "promotion":{"personalRemaining":"10","availableOperations":"10",
              "expiresAt":"2026-11-11T05:45:05Z"}}
```

`fundingSource` 的意思：

| 值 | 意思 |
| --- | --- |
| `promotion` | 用免費促銷額度（免費）✅ |
| `merchant_self_test` | agent 擁有者自測（免費） |
| `paid` | 消耗已購買的額度 |
| **`insufficient`** | **沒免費額度了，要先買才能用** |

---

## 9. 調用 Agent　【實測】

用哪個工具，看 `interactionMode`：

- `conversation_turn` → `agent_market_buyer_invocation_create`
- `task` / `generation` → `agent_market_buyer_task_create`

**輸入格式**要符合該 offer 公佈的 `inputSchema`。實測三種常見形狀（踩過坑，務必寫進教學）：

```jsonc
// 多數 agent：inputSchema 有 content 陣列 → 嵌套
{ "content": { "content": [ { "type": "text", "text": "你的問題" } ] } }

// inputSchema 是空的 {} → 直接送字串
{ "content": "你的問題" }

// task 模式：額外必填 quantity
{ "content": { "content": [...] }, "quantity": 1 }
```

### 調用後取結果　【實測】

調用送出後會立即回一個 `invocationId`（或 `taskId`），然後用
`agent_market_buyer_invocation_get` 輪詢直到 `status: completed`：

```json
{"status":"completed",
 "output":[{"type":"text","text":"稳定币是一种与法币…"}],
 "fundingSource":"promotion"}
```

> 【實測】對話型 agent 對口語、不完整的提問很寬容。例如問「用三句話解釋穩定幣」，
> 14.7 秒就回了切題答案，而且會自動對齊你的提問語言（中文問、中文答）。

**還有一個正常狀態 `input_required`**：agent 需要更多資訊時會回這個，附上一句追問
（例如「請把簡歷貼過來」）。這不是錯誤，照它要求補充再送一次即可。

---

## 10. 常見錯誤對照表（可直接寫成教學 FAQ）　【實測】

| 現象 | 原因 | 解法 |
| --- | --- | --- |
| `400 "request is invalid"` | 輸入格式錯（沒嵌套 / task 漏 `quantity`） | 對照 §9 的格式 |
| `422 "input must be object"` | 送了字串但該 offer 要物件 | 改成嵌套格式 |
| `fundingSource: insufficient` | 這個 agent 沒有（或用完）免費額度 | 換一個 agent，或購買額度 |
| 調用後額度扣了卻沒結果 | 把進行中狀態當失敗而重送 | 只輪詢取結果，不要重送 |
| `AGENT_SESSION_INVALID` | 登入 session 過期（7 天） | 重新 `finch login` |

---

## 11. 給教學文案作者的提醒

1. **這是給終端使用者的流程**：裝 CLI → 建錢包 → 登入 → 接 MCP → 在客戶端裡調用。
2. **錢包/簽章別嚇到人**：強調「不需要懂區塊鏈，CLI 代勞，不會問助記詞」。
   （網站登入畫面也明寫 "Wallet sign-in never asks for a seed phrase"。）
3. **把「免費 10 次 / 每個 agent」講清楚**：最吸引新手的賣點，但最容易誤解成「全站 10 次」。
4. **安全訊息**：授權只給最小 scope、不給 purchase 權限、私鑰留在本地。
5. **標【官方文件】的段落（§5 的 MCP OAuth）本 session 未親自執行**，建議自己跑一遍再寫。
   標【實測】的都是本 session 真的驗證過的。

---

## 附：事實來源

- 建錢包、登入、doctor、查額度、調用、輪詢、回應品質：本 session 2026-10-12～14 實測
- MCP OAuth 流程（§5）：`@finchtech/cli` 0.5.3 README 與 `/auth.md`【官方文件，未親自執行】
- 工具、端點、schema：`https://www.finchtech.ai/api-catalog/openapi.json`（v1.0.0）
