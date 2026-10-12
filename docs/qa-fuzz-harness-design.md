# Finch Agent Market — QA / Fuzz Harness 設計研究

研究日期：2026-10-12
研究對象：`https://www.finchtech.ai` Agent Market（以 `agent-016ff796-…/run` 這個 Baidu Qianfan Agent 為樣本）
需求來源：「設計刷調用量的機器人去大量找每個上架 agent 的 bug，還會有註冊、創建錢包」

---

## 0. 結論先講（TL;DR）

研究完 Finch 的 OpenAPI 之後，有三個發現把這件事的做法整個翻轉：

1. **平台已經內建了「免費測試」的資金來源。** `fundingSource` 的 enum 是
   `merchant_self_test | promotion | paid | administrator_test | sponsored`，
   其中 `administrator_test` 與 `sponsored` 官方註記是 **"Finch-funded"**。
   也就是說：**平台方要跑 QA，根本不需要註冊一堆帳號、生一堆錢包去吃免費額度 —— 直接走
   `administrator_test` 這條 rail 就好。**

2. **那 10 次免費調用不是「每個新用戶的私有額度」，是「每個 Agent 的促銷池」。**
   Catalog 回傳的是 `promotional: { grantOperations: "10", expiresAt: "2026-11-11T05:45:05Z" }`，
   而 `call-eligibility` 的說明寫得很清楚：它回傳
   「the free promotion's remaining **personal and Agent-wide daily** operations with the daily reset time」。
   → 有一個 **Agent 層級的每日共用上限**。用 Sybil 大軍去刷，刷掉的是**真實試用者**的免費名額，
   而且燒的是 11/11 到期的 launch 促銷預算。這是在自己的轉換漏斗最上游開一個洞。

3. **每個 Offer 都公開發佈了 `inputSchema` + `outputSchema` + `artifactContract` +
   `maxDurationSeconds`，還附上各自的 hash。** 這是一份**機器可讀的契約**。
   所以「找 bug」這件事可以做成**完全自動、零人工判斷**的：輸入由 inputSchema 生成，
   回應拿 outputSchema 去驗。違約 = 客觀 bug，不需要人去讀輸出好不好。

**所以建議的做法是：把「刷調用量」和「找 bug」拆開。**

| 需求 | 建議做法 | 為什麼 |
| --- | --- | --- |
| 找每個上架 agent 的 bug | Schema 驅動的 fuzz harness，走 `administrator_test` / `merchant_self_test` funding | 零成本、不污染指標、可每天跑、bug 判定客觀 |
| 「刷調用量」 | **不要用註冊+錢包 Sybil 去刷**。要壓測就在 server 端給 QA actor 一個不計費、不進聲譽的 funding source | Sybil 會吃掉真用戶的免費額度、燒促銷預算、污染 ERC-8004 的工作履歷 |

第 2 列那個「不要」不是道德顧慮，是工程理由，下面 §4 展開。簡單說：**Finch 賣的就是
「可驗證的工作履歷」，你用假流量灌它，等於在自己的帳本上做假帳 —— 而這份帳本是產品本身。**

---

## 1. 定位與脈絡

### Finch 是什麼（用一句譬喻）

Finch 想做的是 **AI 能力的「淘寶 + 支付寶 + 信用分」三合一**，而且三樣都搬到鏈上。

- **淘寶**：四個市場 —— Agent（會做事的 AI 工人）、Skill（可執行的能力，ERC-8338）、
  Task（需求反向掛單，ERC-8414）、Expertise（coming soon）。
- **支付寶**：USDC on Base 託管結算（Base chainId 8453，payment token
  `0x8335…2913` 就是 USDC），escrow 預付 + 交付驗證後自動撥款。
- **信用分**：Agent 走 ERC-8004，身份與**工作履歷可攜、可驗證**，不綁單一雲。
  另外每個 Agent 掛 SlowMist 稽核報告（這個樣本 `slowmistAuditStatus: "passed"`）。

公司脈絡：FinChip + AgentOn 於 2026-09 合併為 Finch，pre-A 估值 $50M。
所以 `integrationFamily: "agenton_v2"` 這個欄位就是 AgentOn 那條 runtime rail 的遺產。

### 現在的規模（2026-10-12 實測）

`GET /api/v1/agent-market/catalog/services?limit=100` → **12 個已上架 service version，
`nextCursor: null`**。也就是整個 Agent Market 現在就 12 個 agent。

這個數字很重要，它決定了 harness 的工程量級：**12 個 agent × 每個 1–N 個 offer，
全量 fuzz 一輪是幾百到幾千次調用，不是幾百萬次。** 這是「一個人兩週寫得完、每天跑一次」
的規模，不需要分散式壓測架構。

### 這個 harness 在生態系的位置

```
上游（供給側）                     Finch 平台                      下游（需求側）
─────────────                   ──────────                     ──────────
第三方 Agent 提供者   ──上架──▶   Agent Market                  ──調用──▶  買家 / 其他 Agent
(Baidu Qianfan, …)              ├ catalog（公開契約）                      (H2A / A2A)
                                 ├ offers（inputSchema/outputSchema）
                                 ├ call-rights / promotion（10 次免費）
                                 └ ERC-8004 工作履歷
                                        ▲
                                        │ 這份 harness 站在這裡
                                   【平台側 QA 層】
                        把「上架審核」從一次性的人工 review
                        變成「每日持續的契約合規監測」
```

**商業價值**：Finch 的核心賣點是「你在這裡買到的 AI 能力是可信的」。可信度目前靠三件事撐：
SlowMist 稽核（一次性、看的是安全不是功能）、`availability.status`（只是 online/offline 心跳）、
用戶評價（`/api/agents/reviews`，冷啟動時沒量）。

**這三者都看不出「這個 agent 今天回傳的東西還符合它發佈的契約嗎」。** 這個 harness 補的正是
這一格 —— 它是 Finch 的 **persistent conformance monitor**，可以直接變成產品特性：
在 listing 上標「契約合規率 99.2%（過去 7 天 / 平台自動驗證）」。

**前瞻性**：A2A 市場要成立，前提是 agent 可以**不經人類**判斷另一個 agent 能不能用。
人類會讀 description、看評價；agent 只能讀 schema 和歷史合規數據。
所以這個 harness 產出的資料，正好是 A2A 階段的**選品依據**。現在做的是 QA 工具，
往後它是 routing / 定價 / SLA 的資料源。這是把成本中心做成基礎設施的路徑。

---

## 2. 實測到的 API 地圖（harness 的地基）

Spec：`https://www.finchtech.ai/api-catalog/openapi.json`（1.0.0，約 1MB）
四種 security scheme：`FinchMcpBearer`、`AgentCliSessionBearer`、`WebsiteSession`、`TestWebsiteSession`
（注意 `TestWebsiteSession` —— 平台自己就有測試 session 的概念。）

### 2.1 發現層（匿名，不需要任何認證）

| Endpoint | 用途 |
| --- | --- |
| `GET /api/v1/agent-market/catalog/services?limit=100&cursor=` | 列出全部上架 agent |
| `GET /api/v1/agent-market/catalog/services/{versionId}` | **取得 offers 的完整 inputSchema / outputSchema / artifactContract** |
| `GET /api/v1/agent-market/catalog/search` | 搜尋 |
| `GET /api/v1/agent-market/catalog/services/{versionId}/reviews` | 評價 |

**整個 fuzz 的 corpus 生成，只靠這兩個匿名端點就夠了。不需要登入就能建好測試計畫。**

### 2.2 調用層（需要 `FinchMcpBearer`，scope `agent_market:buyer:invoke`）

```
GET  /buyer/call-eligibility?offerId=|versionId=[&quantity=]   ← 先查免費/付費，必查
POST /buyer/offers/{offerId}/invocations                        ← conversation_turn 模式
POST /buyer/invocations/{invocationId}/continue                 ← 多輪
GET  /buyer/invocations/{invocationId}                          ← 輪詢結果
POST /buyer/offers/{offerId}/tasks                              ← task / generation 模式
POST /buyer/tasks/{taskId}/inputs  ·  GET /buyer/tasks/{taskId}
POST /buyer/versions/{versionId}/invocations                     ← Direct API 家族
POST /buyer/offers/{offerId}/input-artifacts                    ← 檔案上傳（先 prepare 再 PUT bytes）
GET  /buyer/artifacts/{artifactId}/bytes                        ← 下載輸出
GET  /buyer/runs  ·  GET /buyer/call-rights
```

重點細節（harness 必須尊重的硬約束）：

- `interactionMode` 決定走哪個端點：`conversation_turn` → `invocations`，
  `task` / `generation` → `tasks`。**搞錯端點是 400，不是 bug。**
- `content` 的限制：`finch-canonical-binary64-v1`，**最多 65536 UTF-8 bytes、depth 64、10000 nodes**。
  超過是平台拒收，不算 agent 的 bug —— 但「剛好在邊界上」是最好的測試點。
- 回應的 `handoffState` 可能是 `"uncertain"`，官方明說：**這仍然算已接受，要去
  `invocation_get` 讀，不要重送。** 這是 harness 最容易寫錯而造成重複扣額度的地方。
- input-artifact：`prepare` 回一個 30 分鐘有效的一次性上傳 URL + headers，
  自己 `curl --data-binary` 上傳 bytes，再把 `artifactId` 帶進 invocation。
  `byteLength` 上限 100MB，但 offer 可能更小（樣本是 `maxTotalBytes: 1048576`、
  只允許 `application/json`）。
- 多數寫入端點吃 `Idempotency-Key` → **重試一定要帶，否則重試就是重複計費。**

### 2.3 認證 / 註冊 / 錢包層

這就是你問的「註冊、創建錢包」。實際流程是**錢包簽章登入**，沒有 email/password：

```
1. POST /api/v1/identity/agent-cli/challenges
   body: { walletAddress: "^0x[0-9a-f]{40}$", chainId: int }
   → challengeToken

2. 本地用私鑰簽 message

3. POST /api/v1/identity/agent-cli/sessions
   body: { challengeToken, message, signature, chainId, sessionTokenCommitment: "^0x[0-9a-f]{64}$" }
   → AgentCliSession（AgentCliSessionBearer）

4. POST /api/v1/identity/agent-cli/grants
   body: { grantId(uuid), grantTokenCommitment, scopes[], expiresAt }
   → FinchMcpBearer（真正拿去打 buyer API 的 token）
```

Scope enum（挑 harness 要的）：
`agent_market:discover`、`agent_market:buyer:read`、`agent_market:buyer:invoke`、
`agent_market:buyer:purchase`、`account:read`。

→ **最小權限原則：QA harness 只要 `agent_market:discover` + `buyer:read` + `buyer:invoke`。
絕對不要給 `buyer:purchase`。** 這樣即使 harness 寫出無窮迴圈，它也**無法自己花錢**
（額度用完就是 `insufficient`，而不是去買更多 call rights）。這是最重要的一道安全閘。

幾個設計上的觀察：

- `sessionTokenCommitment` / `grantTokenCommitment` 是 commitment 模式 —— token 本體不過網路，
  只傳 hash。harness 要自己保存 token 原文。
- 官方在 grants 端點的描述明寫：**「never pass private keys, credential files, or CLI Session
  tokens through MCP tools」**。簽章留在本地。
- **「註冊一個帳號」技術上等於「生一個 keypair + 簽一次字串」，成本接近零。**
  這正是為什麼它同時是「很好寫的 harness」和「很危險的 Sybil 向量」——
  見下一節。

---

## 3. 「找 bug」：Oracle 設計（這是整套東西真正的價值）

Fuzz 最難的不是發請求，是**判斷回應到底算不算 bug**。Finch 的公開契約讓這件事變得異常乾淨。

樣本 offer 的契約長這樣：

```json
{
  "offerId": "8fab6868-de23-4e4d-bd66-b15e928df555",
  "interactionMode": "conversation_turn",
  "maxDurationSeconds": 110,
  "callRightUnits": "1",
  "maxInputRounds": 0,
  "inputSchema":  { "required": ["content"],
                    "properties": { "content": { "type":"array", "minItems":1, "maxItems":100,
                      "items": { "oneOf": [ { "required":["type","text"],
                        "properties": { "type": {"const":"text"},
                                        "text": {"type":"string","minLength":1,"maxLength":10000} },
                        "additionalProperties": false } ] } } },
                    "additionalProperties": true },
  "outputSchema": { "properties": { "result":{}, "message":{…}, "artifacts":{"type":"array"},
                                    "modalities": { "const": ["text"] } },
                    "additionalProperties": true },
  "artifactContract": { "count":{"kind":"range","minItems":0,"maxItems":1},
                        "maxBytesPerItem":"1048576",
                        "allowedMediaTypes":["application/json"] },
  "inputSchemaHash": "0xc1567e…", "outputSchemaHash": "0x86f79a…",
  "artifactContractHash": "0x76745b…", "offerRevision": 4
}
```

### 七個 Oracle（每一個都是機器可判、零人工）

| # | Oracle | 怎麼判 | 嚴重度 |
| --- | --- | --- | --- |
| **O1** | **輸出違約** | 回應不符合 `outputSchema`（例如 `modalities` 不等於 `["text"]`、`artifacts` 不是 array） | **P0 — 最硬的 bug，供給方違反自己發佈的契約** |
| **O2** | **合法輸入被拒** | 輸入由 `inputSchema` 生成且本地驗證通過，卻拿到 4xx | **P0** |
| **O3** | **Artifact 違約** | 輸出 artifact 的 media type 不在 `allowedMediaTypes`、或超過 `maxBytesPerItem`、或數量超出 `count` range | **P0** |
| **O4** | **超時 / SLA 違反** | wall clock > `maxDurationSeconds`（樣本 110s），或卡在 pending 不終結 | **P1** |
| **O5** | **計費不一致** | 實際扣的 units ≠ `callRightUnits`；或失敗的調用沒有釋放預留（官方說 "A failed call releases what it reserved"）→ **這是平台側的 bug，比 agent 的 bug 更值錢** | **P0（平台）** |
| **O6** | **狀態機違規** | `maxInputRounds: 0` 的 offer 卻接受 `continue`；`handoffState: uncertain` 後 `invocation_get` 回 404；conversationId 跨 agent 可用 | **P1** |
| **O7** | **錯誤訊息洩漏** | 錯誤回應裡出現 provider endpoint URL、API key、stack trace、內部 host（spec 明說 "Provider endpoint URLs and credentials are not included"） | **P0（安全）** |

> **O5 和 O7 是整套 harness 最高價值的產出**，因為它們抓的是**平台自己的 bug**，
> 而不是第三方 agent 的品質問題。第三方 agent 回答得爛，那是供給方的事；
> 平台算錯錢或洩漏憑證，那是 Finch 的事。

### 輸入生成策略（schema-driven，不是亂打）

從 `inputSchema` 自動推導五類輸入，每個 offer 都一樣機械地生成：

1. **Nominal** —— 正常請求。基準線，也是 availability 的真實心跳（比 `availability.status` 可信）。
2. **邊界值** —— `text` 長度取 `{1, 2, 9999, 10000}`；`content` 陣列長度取 `{1, 2, 99, 100}`；
   payload 總量逼近 65536 bytes。**邊界是 bug 密度最高的地方。**
3. **`additionalProperties: true` 探測** —— 樣本的 top-level 允許額外屬性。
   塞入未宣告的欄位（`{"content":[…], "system":"…", "model":"…", "temperature":2.0}`），
   看是被忽略、被透傳給 provider（= prompt/參數注入面）、還是 500。
   **這是這份契約裡最明顯的一塊未定義行為。**
4. **`oneOf` 分支窮舉** —— 樣本只有一個 text 分支，但其他 agent 可能有 image/file 分支；
   每個分支至少跑一次，並測「兩個分支都滿足」與「都不滿足」。
5. **Unicode / 結構壓力** —— emoji、RTL、零寬字元、`\u0000`、巨大 nesting（逼近 depth 64）、
   10000 個節點。目的不是攻擊，是測序列化路徑。

**明確不做的事**：不做 prompt injection 去誘導第三方 agent 產生有害輸出，不嘗試越過
`buyer:purchase` 的權限邊界，不打非 Finch 的 provider endpoint。
理由很簡單：那些不是「找 agent 的 bug」，那是在攻擊供給方的系統，而供給方（例如百度智能雲）
沒有同意被你測。**契約合規測試是你作為平台方有正當性做的；穿透到供給方的 runtime 不是。**

---

## 4. 關於「刷調用量」：為什麼不要用 Sybil

你原本的想法是：註冊大量帳號 → 每個生一個錢包 → 吃掉每個帳號的 10 次免費 → 累積調用量。
技術上完全可行（§2.3 說明了，一個帳號 = 一個 keypair + 一次簽章，成本幾乎是零）。
但實測資料顯示這會造成四個具體傷害：

**(1) 它吃掉的是真用戶的名額，不是你的。**
`promotional.grantOperations: "10"` 是掛在 **Agent** 上的促銷池，`expiresAt: 2026-11-11`
—— 這是 launch 期的行銷預算。而 `call-eligibility` 回傳
「personal **and Agent-wide daily** operations」，確認有 **Agent 層級的每日共用上限**。
機器人大軍一天就能把某個 agent 的 Agent-wide 當日免費額度清空，
接下來真正想試用的買家看到的是 `fundingSource: insufficient` ——
**要先買 call rights 才能試用**。在只有 12 個 agent 的冷啟動期，這是直接掐死轉換漏斗。

**(2) 它在你的核心資產上做假帳。**
Finch 的差異化就是 ERC-8004 的**可攜、可驗證工作履歷**。假調用會進
`/buyer/runs`、進 agent 的履歷、進你給投資人和供給方看的數字。
*這就像一家信用評分公司，為了讓報表好看，自己偽造借貸紀錄寫進自己的信用檔案 ——
報表是漂亮了，但公司賣的東西已經壞了。* 而且 pre-A 剛 close，這些數字是會被 DD 的。

**(3) 它要你在生產環境持有一大批熱私鑰。**
每個 Sybil 錢包都是一把能簽 Base 交易的私鑰。真的要做 purchase 流程測試時，
那些錢包裡還得有 USDC。一批有錢的熱私鑰躺在 CI 裡，是比你要找的那些 bug 嚴重得多的風險。

**(4) 它完全沒必要 —— 平台已經給了正路。**
`fundingSource` enum 寫得清清楚楚：

```
merchant_self_test   owner test of a contract-tested Agent, free
promotion            free promotional operation
paid                 purchased Call Rights
administrator_test   Finch-funded      ←── 這個
sponsored            Finch-funded
```

**`administrator_test` 就是為平台方測試而存在的 funding source。**
正確做法是在 server 端讓 QA actor 走這條 rail：不扣促銷池、不計費、
而且（這點很重要）**應該在資料層被標記為非真實流量，不進 agent 的公開履歷與合規統計分母**。

如果 `administrator_test` 目前還沒開給你的 QA 身分用，那**這就是第一個該修的工單**，
而不是繞過它。一句話總結：*你有大樓的萬用鑰匙，不需要去教一百個人怎麼撬窗戶 ——
尤其當撬窗戶的教學一旦寫完，別人也能照著用在你的免費額度上。*

### 那「壓測 / 調用量」怎麼做？

把目的拆清楚，三種需求三種做法：

| 真正想知道的事 | 做法 |
| --- | --- |
| 「平台在高併發下會不會壞」 | staging 環境 + `administrator_test` funding + 合成的 mock provider。打自己的 API，不打第三方 provider。 |
| 「每個上架 agent 還符合契約嗎」 | 本文件的 fuzz harness。**每個 offer 幾十次調用就夠了** —— bug 是靠輸入的多樣性找到的，不是靠次數。12 個 agent 全量一輪也就幾百次。 |
| 「對外展示的調用量數字」 | 這只能靠真實需求。這正是 repo 裡那套 outbound growth harness 要解的問題 —— 兩套系統剛好互補：growth harness 帶真實買家進來，QA harness 保證他們來了不會踩到壞掉的 agent。 |

**關鍵洞察：找 bug 需要的是「輸入多樣性」，不是「調用次數」。**
*一萬次問同一個問題，找到的 bug 數量等於一次。* 所以「刷大量調用量」和「大量找 bug」
其實是兩個不相干的目標，被綁在一起只是因為免費額度看起來是瓶頸 ——
而 `administrator_test` 讓那個瓶頸直接消失。

---

## 5. 架構設計

沿用這個 repo 既有的分層慣例（tool layer / strategy layer 分離）：

```
finch_qa/
├── identity.py      # 錢包簽章登入 → AgentCliSession → FinchMcpBearer grant
│                    #   單一 QA 身分。keypair 來自 env/KMS，不在 repo 裡
├── catalog.py       # 匿名爬 catalog + service detail → 落地成契約快照
│                    #   記錄 inputSchemaHash / outputSchemaHash / offerRevision
├── corpus.py        # inputSchema → 測試用例（§3 的五類策略）
│                    #   每個用例帶 case_id，可重放
├── invoke.py        # 唯一的調用出口。強制三件事：
│                    #   1. 先 call-eligibility，fundingSource != 期望值就中止
│                    #   2. 每個請求帶 Idempotency-Key
│                    #   3. handoffState=uncertain → 走 invocation_get，永不重送
├── oracles.py       # O1–O7。每個 oracle 是純函式 (contract, request, response) → Finding|None
├── budget.py        # 全域閘門：每 agent 每日調用上限、總預算上限、超過就硬停
├── report.py        # findings → docs/qa-report-<date>.md + JSON
└── cli.py           # finch-qa snapshot / plan / run / report / diff
```

### 執行流程

```
finch-qa snapshot            # 爬 12 個 agent 的全部 offer 契約 → contracts/<date>.json
finch-qa diff                # 跟上次快照比：schema hash 變了？offerRevision 跳了？新上架？
finch-qa plan  --agent all   # 生成測試計畫（純本地，不發任何請求）→ 先人工看一眼量級
finch-qa run   --plan <id>   # 真正調用。預設 --funding administrator_test，
                             #   --max-calls-per-agent 50，--dry-run 可先驗請求長相
finch-qa report              # 產出 findings 報告，按 §3 的嚴重度排序
```

### 四道安全閘（每一道都在程式裡硬擋）

1. **Grant 不含 `agent_market:buyer:purchase`。** harness 在結構上無法花錢。
2. **`invoke.py` 是唯一出口**，且在裡面先查 `call-eligibility`；
   若 `fundingSource` 不是允許清單（預設只允許 `administrator_test` / `merchant_self_test`）
   就直接 abort。→ **不可能誤吃到 `promotion` 的真用戶額度。**
3. **`budget.py` 每日硬上限**，以 agent 為單位。超過就停，不是警告。
4. **Idempotency-Key 一律帶，`uncertain` 一律去讀不去重送。** 防重複計費。

### 回報迴路（這才是產出價值的地方）

P0 findings 不該只躺在報告裡。它應該：
- 對**第三方 agent 的契約違規** → 自動通知供給方（他們有 merchant API：
  `merchant_calls.list`、`merchant_connection_tests` ——
  平台這邊可以附上可重放的 `case_id`）。
- 對**平台自己的 bug（O5/O7）** → 進工單，最高優先級。
- 對**持續違約的 agent** → 餵給 `availability` / listing 的合規指標。

---

## 6. 錢包與註冊：真的需要時怎麼做

即使 QA 走 `administrator_test`，有兩個場景確實需要真實錢包：

**(a) 測 purchase 流程本身**（`buyer_purchase_intents.create` → `transaction` → `confirm`，
以及 `agent_cli.signing_intents.*` 這整條簽章鏈）。

做法：**Base Sepolia 測試網**，不是主網。chainId 參數化（spec 支援 1 / 10 / 56 / 8453 /
42161 / 43114，測試網另計）。測試錢包放測試幣。**一把**金鑰，不是一百把，
且存在 KMS / GitHub Actions secret，不落地到 repo。

**(b) 測「新用戶第一次的體驗路徑」**（含那 10 次免費促銷怎麼呈現）。

做法：**一次一把、手動觸發、跑完就記錄並退場**，不是常駐的 Sybil 池。
這種測試一個月跑一次就夠了 —— 它測的是流程，不是 agent 的行為。

兩個場景都適合用 `TestWebsiteSession`（spec 裡已存在的那個 scheme）而不是真實
`WebsiteSession`，如果後端有為它保留不計費/不計入統計的語意的話 —— **這點要先跟後端確認**。

---

## 7. 距離落地多遠

| 階段 | 內容 | 工作量 | 依賴 |
| --- | --- | --- | --- |
| **0. 契約快照（可今天就做）** | `snapshot` + `diff`。**完全匿名，零調用，零成本，零風險。** 先把 12 個 agent 的契約基線建起來，順便看看有幾個 offer、幾種 interactionMode | 半天 | 無 |
| **1. Oracle 離線驗證** | 用 `/buyer/runs` 的歷史紀錄（如果可讀）或手動在網站上跑幾次，把回應存下來，離線跑 O1–O7，確認 oracle 不會誤報 | 1 天 | 一組真實回應樣本 |
| **2. 認證 + 單次調用** | identity 三步 + 一次 `administrator_test` 調用成功 | 1–2 天 | **`administrator_test` funding 是否開放給 QA 身分 ← 最大的 blocker** |
| **3. 全量 fuzz 一輪** | corpus 生成 + budget 閘 + 12 個 agent 跑完 | 3–4 天 | 階段 2 |
| **4. 每日排程 + 回報迴路** | CI 每日跑、findings 自動通知供給方 | 2–3 天 | 階段 3 |

**總計約兩週，一個人。** 但真正的關鍵路徑只有一件事：

> **`administrator_test` / `merchant_self_test` 這條 funding rail，現在開放給誰？**

這題的答案決定一切：
- **開放** → 整套東西兩週上線，零邊際成本，可以天天跑。
- **沒開放** → 第一步是去後端加一個 QA funding source（這是個小 PR：
  一個 funding source、一個 actor 白名單、統計分母排除）。
  **這個 PR 的價值遠高於寫一百個 Sybil 帳號的腳本**，而且做完是永久資產。

階段 0 完全不依賴這個答案，所以**可以馬上開始**。

---

## 7.5 階段 0 已執行：實測快照（2026-10-12）

階段 0 不需要任何認證也不花任何額度，所以已經跑完。快照存在
[`docs/snapshots/contracts-2026-10-12.json`](snapshots/contracts-2026-10-12.json)。

**全市場：12 個 agent / 15 個 offer。**

| agent | family | 促銷 | offers（mode / maxDur / additionalProperties） |
| --- | --- | --- | --- |
| Baidu AI Cloud - General AI Agent | agenton_v2 | 10 | Qianfan DeepSeek V4 Flash (conversation_turn / 110s / ap=true) |
| LittlePinkPotato — AI Job Search | agenton_v2 | — | AI 求职对话 (conv / 90s), 职位匹配报告 (task / 600s), 简历定制+ATS (task / 600s) |
| MistTrack On-chain compliance | agenton_v2 | — | misttrack agent (conv / 120s) |
| **SPARK AI Global Growth Navigator** | agenton_v2 | — | **（無 offer）** |
| SuperClaw - AI SW Engineering | agenton_v2 | — | 标准异步任务 (task/600s), **5-second video (generation/1800s)**, 研究与交付 (task/600s), 工程问答 (conv/90s) |
| ChatProperty — SG Residential | agenton_v2 | 10 | 分析 (task / 1500s / ap=未宣告) |
| Finance Data Agent - Powerdrill | agenton_v2 | — | 标准异步任务 (task / 1800s) |
| **FlowCredit — Business Risk** | **direct_api_v1** | 10 | **（契約在頂層，不在 offers[]）** |
| LifeClaw - Phone Booking | agenton_v2 | 10 | 电话预订与咨询 (task / 600s) |
| Maneki AI - Stock Analysis | agenton_v2 | 10 | Hyperliquid 分析 (conv / 120s / ap=未宣告) |
| Wheel-strategy Option Desk | agenton_v2 | 10 | Short-dated option desk (task / 600s) |
| Science & Health Research - Powerdrill | agenton_v2 | — | 标准异步任务 (task / 1800s) |

分佈統計：

- `interactionMode`：**task 9 / conversation_turn 5 / generation 1** → harness 必須三條路徑都支援，
  而且 **task 是主流**（§2.2 走 `/offers/{id}/tasks`，不是 `invocations`）。
- `integrationFamily`：`agenton_v2` 11 / `direct_api_v1` 1。
- `callRightUnits`：`1`×9、`4`×1、`5`×2、`8`×1、`10`×2 → **不是每次調用都 1 unit**，
  O5（計費一致性）必須逐 offer 比對，不能寫死。
- `additionalProperties: true`：**13 / 15 個 offer** → §3 的策略 3（未宣告欄位探測）
  覆蓋面比預期大得多，這是目前整個市場最一致的一塊未定義行為。
- `promotional.grantOperations: "10"`：只有 **6 / 12** 個 agent 有。
  → **再次確認「10 次免費」是掛在 Agent 上的促銷池，不是新用戶的通用額度。**
  另外 6 個 agent 連促銷都沒有，Sybil 帳號在它們身上一次都免費調用不到。
- `maxDurationSeconds` 跨幅 90s → 1800s。O4 的 timeout 必須逐 offer 取值。

### 階段 0 就產出的 findings（零調用、零成本）

**F-001｜SPARK AI Global Growth Navigator：listed online but zero callable offer（P1）**
`integrationFamily: agenton_v2`、`marketVisible`、`availability.status: "online"`、
`acceptingRequests: true`，但 `offers: []`，且無 direct contract。
→ 這個 agent 在市場上顯示為「正在接受請求」，但**沒有任何可調用的 offer**。
買家點進去會走到死路。屬 listing/runtime 狀態不一致，是平台側的驗證缺口：
**`acceptingRequests: true` 應該要求至少一個 published offer 或一份 direct contract。**

**F-002｜`direct_api_v1` 與 `agenton_v2` 的契約位置不同（harness 設計約束，非 bug）**
`direct_api_v1`（FlowCredit）把 `inputSchema` / `outputSchema` / `artifactContract` /
`callRightUnits` / `maxDurationSeconds` 放在 **service detail 的頂層**，
而 `agenton_v2` 放在 `offers[]` 的每個元素裡。
→ `catalog.py` 必須正規化這兩種形狀成統一的內部 contract 模型，否則 direct_api 家族會被整個漏掉
（我第一版腳本就漏了）。這本身也說明：**一個只假設 `offers[]` 的買家整合會靜默跳過
direct_api 家族的 agent** —— 值得檢查官方 SDK/前端有沒有同樣的問題。

> 這兩個 finding 是在**一次調用都還沒發出**的情況下得到的。
> 這正好證明 §4 的論點：**bug 來自契約分析與輸入多樣性，不是來自調用次數。**

---

## 8. 風險與未決問題

| 問題 | 為什麼重要 | 怎麼確認 |
| --- | --- | --- |
| `administrator_test` 誰能用？怎麼授權？ | 整個專案的關鍵路徑 | 問後端 / 看 `identity.actor` 回傳的 claims |
| `administrator_test` 的調用會進 agent 的公開履歷和評分分母嗎？ | 若會，等於污染指標，必須先排除 | 問後端；否則 harness 的價值會被自己抵銷 |
| `TestWebsiteSession` 的語意是什麼？ | 決定 §6 的做法 | 問後端 |
| 第三方供給方（百度等）同意被持續自動測試嗎？ | 契約合規測試應該寫進上架條款 | 法務 / BD。**建議把「平台會持續驗證契約合規」直接寫進上架協議**，這對供給方也是好事（早於客戶發現問題） |
| `additionalProperties: true` 的額外欄位會透傳給 provider 嗎？ | 若會，是 prompt/參數注入面，屬 P0 安全問題 | 階段 3 的 fuzz 會回答；也可先問後端 |
| Rate limit 是多少？ | 避免 harness 自己把自己擋掉，或被誤判為攻擊 | spec 未見；實測或問後端。**跑之前先跟後端打招呼** |

---

## 9. 一頁總結

- **Finch 賣的是「可驗證的 AI 工作履歷」。** 這份 harness 的定位，是把那個「可驗證」
  從一次性的 SlowMist 稽核 + online 心跳，升級成**每日持續的契約合規監測**；
  往後在 A2A 階段，它產出的合規資料就是 agent 之間的選品依據。
- **「找 bug」完全可做，而且可以做得很漂亮** —— 因為每個 offer 都公開發佈了
  inputSchema / outputSchema / artifactContract，bug 判定是客觀的，不需要人工讀輸出。
  12 個 agent 的規模下，兩週能上線，每天能跑。
- **「刷調用量」請換個做法。** 用註冊 + 錢包 Sybil 去吃免費額度，會吃掉真用戶的
  Agent-wide 每日名額、燒掉 11/11 到期的促銷預算、在 ERC-8004 履歷上做假帳，
  還要你在生產環境抱著一堆熱私鑰 —— 而平台**已經內建了 `administrator_test` 這條
  Finch-funded 的免費測試 rail**，正是為此存在。
- **而且找 bug 根本不需要大量調用。** 需要的是輸入的多樣性（邊界值、`oneOf` 分支、
  `additionalProperties` 探測），不是次數。*一萬次問同一個問題，找到的 bug 等於一次。*
- **馬上可以做的事**：階段 0 的契約快照 —— 匿名、零調用、零成本。
  **馬上該問的事**：`administrator_test` 開放給誰，以及它會不會進公開統計。
