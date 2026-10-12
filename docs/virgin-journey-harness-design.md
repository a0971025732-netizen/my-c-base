# Finch — 全新用戶旅程 Harness（Virgin Journey Harness）設計

研究日期：2026-10-12
前一份：[`qa-fuzz-harness-design.md`](qa-fuzz-harness-design.md)（契約 fuzz，走 `administrator_test`）
研究對象：`@finchtech/cli` 0.5.3（2026-10-11 發佈）、`/auth.md`、Identity API

---

## 0. 修正：上一份設計錯在哪

上一份我主張「平台方跑 QA 不需要註冊帳號、不需要生錢包，走 `administrator_test` 就好」。

**這個主張對契約 fuzz 是對的，對你真正要測的東西是錯的。**

`administrator_test` 這條 rail 的前提是：**你已經有 Account、有 wallet、有 active AgentCLI
Session、有 MCP grant、有額度。** 它從已經溫熱的身分出發 —— 而那正是你要測的那段路的*終點*。
用一個已經配置好的身分去測 onboarding，等於**派一個已經住在屋裡的人去測門鎖**。

具體說，有三類 bug 在結構上不可能被溫熱身分看到：

1. **本地狀態與權限路徑。** CLI 0.5.3 的 `dist/finch.js` 裡，本地狀態錯誤碼出現約 **98 次**：
   `CLI_STATE_CORRUPT`(37)、`CLI_STATE_PERMISSIONS_INVALID`(29)、`CLI_STATE_NOT_FOUND`(24)、
   `CLI_STATE_CONFLICT`(8)。這些只有在**真實檔案系統上、從沒有 `~/.finchtech` 開始、
   並且在中途被打斷**時才會觸發。API 層測不到，溫熱身分測不到。

2. **第一次的額度語意。** 全新帳號的 `call-eligibility` 會回什麼？促銷的 10 次怎麼呈現？
   第 10 次到第 11 次的邊界長什麼樣？**一個已經有 call rights 的身分永遠走不到
   `fundingSource: insufficient` 那條分支** —— 而那是新用戶最可能撞上的一條。

3. **不可逆的首次順序。** `login` → `grant` → MCP OAuth 的先後、升級後第一個 stateful
   指令會清掉 `grants/`、`wallet` 切換會撤銷 OAuth refresh family。
   這些都是**一次性狀態轉移**，一個帳號只能體驗一次。

而 CLI 已經發了 **23 個版本，0.5.3 是昨天（10-11）發的**，0.5.0 還移除了
`creator …`、`operation show`、`skill search`、`mcp grant …` 四組指令。
**變動最頻繁的就是 onboarding 這條路** —— 它最需要每個 release 都有人從零走一遍。

所以：**兩套 harness，不是一套。**

| | Harness A：契約 Fuzz | Harness B：全新旅程（本文件） |
| --- | --- | --- |
| 身分 | 一個長期溫熱身分 | **每條旅程一個全新帳號 + 新錢包** |
| 資金 | `administrator_test` | **真實促銷額度 / 測試網 USDC** |
| 找什麼 | 上架 agent 的契約違規 | **CLI 與用戶端的首哩路 bug** |
| 規模 | 15 offer × 數十輸入 ≈ 數百次調用 | **每 release 約 24 條旅程 × 2–3 次調用** |
| 判定 | outputSchema 比對 | 旅程可完成性 + 錯誤可行動性 |

### 關鍵的量級重構：帳號是「單次使用的測試夾具」

你要的是「大量註冊去刷」，但資料顯示真正該要的是**另一個東西**：

> **一個帳號只能「全新」一次。** 它用過一次就永遠溫熱了。
> 所以 Harness B 要的不是「同時有很多帳號」，是「**持續供應新鮮帳號**」。

這個重構把規模從「幾千個 Sybil」降到「每個 CLI release 二十幾條旅程」，
而每條旅程只用掉 2–3 次免費調用（驗證第一次成功、第二次累計、以及耗盡邊界）。
**那 10 次免費額度，用途剛好就是這個。** 不是拿來堆調用量的，是拿來讓新用戶
（和測試新用戶的機器人）走完第一哩路的。

跑完的帳號不浪費：它降級成 Harness A 的溫熱身分繼續服役，剩下的免費額度拿去跑契約 fuzz。

---

## 1. 虛擬用戶旅程地圖

這是從 CLI README、`/auth.md` 和 Identity API 實際還原出來的完整路徑。
每一格都是一個可斷言的測試步驟。

| 階段 | 動作 | 只有全新帳號才看得到的東西 |
| --- | --- | --- |
| **J0 乾淨機器** | 全新 container：無 `~/.finchtech`、Node ≥ 20 | 預設狀態目錄的建立與 `chmod 700`（CLI 說它自己會建並保護） |
| **J1 安裝** | `npm install -g @finchtech/cli`、`finch --version`、`finch --help` | 全新安裝的 PATH 衝突（README 特別提供 `finchtech` 作為備用執行檔 → 說明這個坑真實存在）；**server 拒絕 < 0.4.0 的 CLI** 並給升級指示 |
| **J2 錢包** | `finch wallet create`（生新身分）或 `finch wallet use --file <PATH>`（匯入 32-byte hex，64 hex digits，`0x` 可選，需 `chmod 600`） | 首次匯入是**離線**的並直接設為 current；`wallet list` / `wallet show` 在零狀態下的輸出；金鑰檔權限不對時的 `CLI_STATE_PERMISSIONS_INVALID` |
| **J3 登入** | `finch login --chain-id <ID>`，auth chain ∈ **{1, 10, 56, 8453, 42161, 43114, 1776}** | challenge → 本地簽章 → session（`sessionTokenCommitment`）整條；**pending login 的復原**（README：切換錢包前必須先復原 pending login） |
| **J4 體檢** | `finch mcp doctor`（5 項 check：endpoint / wallet / local Session / remote Session authority / MCP discovery，各自 `ok｜missing｜invalid｜unavailable｜skipped`；exit 0 = ready、2 = 不健康） | **零狀態下 doctor 的輸出是否可行動** —— 新用戶第一次跑 doctor 看到的就是一堆 `missing`，那些 guidance 真的能把他救回來嗎 |
| **J5 MCP 授權** | 三個入口依序：`finch mcp connect -- <client login cmd>`、`finch mcp authorize --stdin`、`finch mcp authorize <REQUEST_TOKEN>`。PKCE S256 + 精確註冊的 redirect URI + RFC 9207 issuer 檢查 | loopback HTTP callback vs HTTPS callback（proxied workstation / web editor）兩條路；`MCP_AUTHORIZATION_FLOW_FAILED` 的三種 `login_command_{failed,not_started,timeout}` |
| **J6 身分對齊** | MCP `identity_actor_get` 對比 `finch status` | `MCP_CLI_WALLET_MISMATCH`；`harnessOAuth.status` **永遠是 `not_checked`**（即 doctor 說 ready 也不保證 OAuth 能用）→ 新用戶會被這個誤導嗎 |
| **J7 第一次調用** | `call-eligibility` → `invocations` / `tasks` → 輪詢 | **整個 harness 的核心**：零餘額帳號的 eligibility 分支、促銷 10 次的呈現、扣減、耗盡邊界 |
| **J8 第一次付費** | `purchase transaction` → `purchase submit`（USDC approve + AgentService Vault 兩筆）→ Call Rights；`purchase vault` | 第一次 approve 的 allowance 從 0 開始；`PURCHASE_INTENT_DENIED`；revert 後的 zero-allowance 清理 |
| **J9 退場與復原** | `finch logout` / `logout --local`、`wallet use <ADDR>` 切換、跨版本升級 | 升級後第一個 stateful 指令會**移除過時的 `grants/`**；logout 會撤銷 OAuth refresh family；`site open`（60 秒一次性 handoff）/ `site login <URL>`（5 分鐘） |

---

## 2. 只有全新帳號看得見的 bug —— 我已經預測到的七個具體陷阱

這些是研究階段就從契約和文件推出來的，每一個都寫成 Harness B 的首批測試用例。

### T1｜6/12 個 agent 沒有促銷 → 全新用戶在它們身上一次免費調用都做不到（P0，cold-start 致命）

[上一份的階段 0 快照](snapshots/contracts-2026-10-12.json)顯示：
`promotional.grantOperations: "10"` 只存在於 **6 個 agent**，另外 6 個完全沒有。

→ 一個剛裝好 CLI、剛生好錢包、USDC 餘額為 0 的新用戶，點進那 6 個 agent 的任何一個，
得到的第一個回應是 **`fundingSource: insufficient`**：**請先去 Base 上買 USDC、approve、
購買 Call Rights，才能試用。**

這是 onboarding 漏斗上最致命的一格，而且**只有零餘額的全新帳號看得見**。
*就像一間餐廳門口寫著「歡迎試吃」，但一半的攤位要先辦會員卡充值才給你碰筷子。*
Harness B 的第一條旅程就該是「全新用戶 × 無促銷 agent」，把那個錯誤訊息的原文抓出來，
看它有沒有告訴用戶下一步該做什麼。

### T2｜auth chain `1776` 不在 market chain 清單裡（P1）

`dist/finch.js` 裡有兩份鏈清單：

```
[1, 10, 56, 8453, 42161, 43114]          ← 6 條
[1, 10, 56, 8453, 42161, 43114, 1776]    ← 7 條，多了 1776
```

而 README 說 `finch login --help` 列出的 production auth chain 是 7 條（含 1776），
但「Market transaction chains come from Remote MCP/API plans and are **independent of**
the login chain」。

→ 一個用 `finch login --chain-id 1776` 入門的新用戶，走到 J8 付費時會撞上
**auth chain 與 market chain 不一致**。這條路只有「真的拿 1776 登入過的帳號」能走到。
旅程 variant 矩陣必須涵蓋全部 7 條 auth chain。

### T3｜raw API 只吃小寫地址，但每個錢包 UI 給的都是 EIP-55 checksummed（P1，非 CLI 客戶端）

`POST /api/v1/identity/agent-cli/challenges` 的 schema 是：

```json
{ "walletAddress": { "type": "string", "pattern": "^0x[0-9a-f]{40}$" } }
```

**只接受全小寫。** CLI 自己會正規化（README：「accept canonical lowercase or valid EIP-55
input and are normalized to lowercase before request validation」），
但**任何不經 CLI 的整合**（自寫腳本、MetaMask `eth_accounts` 回傳值、Etherscan 複製來的地址）
拿到的都是 EIP-55 大小寫混合 → **直接 400，而錯誤訊息很可能只說 pattern 不符。**

這題只有「自己手寫一次註冊流程」才會撞到。所以 Harness B 必須有一條**不經 CLI、
直接打 Identity API** 的旅程 variant —— 這也正好是第三方開發者接入時走的路。

### T4｜grant scopes 必須嚴格 ASCII 字典序（P1）

```json
"scopes": { "description": "Strictly ASCII-lexicographically sorted unique grant scopes.",
            "x-finch-order": "ascii_lexicographic" }
```

→ 手寫整合時 scopes 順序寫錯就失敗。測試點：亂序、重複、空陣列、超過 16 個、
以及**錯誤訊息有沒有告訴你「請排序」**（而不是只回一個 schema 錯誤）。

### T5｜本地狀態的 98 條錯誤路徑（P0–P1，只有真機 + 中斷才觸發）

`CLI_STATE_CORRUPT` / `CLI_STATE_PERMISSIONS_INVALID` / `CLI_STATE_NOT_FOUND` /
`CLI_STATE_CONFLICT` 合計約 98 處。README 描述的情境包括：
「Incomplete wallet files require recovery from backup」、
「other partial or corrupt Session state requires explicit repair」、
「A pending login must be recovered before switching」。

→ 測法見 §6 的 JO4：**在旅程的每一步之後 SIGKILL，再用文件說的復原指令救回。**
README 列出的所有 `recover` 路徑就是測試矩陣本身。

### T6｜`handoffState: "uncertain"` 發生在新用戶的第一次調用時（P0，會吃掉他的免費額度）

API 明寫：「"uncertain" is still accepted, so read it with
`agent_market_buyer_invocation_get` instead of resubmitting」。

→ 新用戶（和任何沒讀完文件的整合）看到 uncertain 的本能反應是**重送**。
如果 server 端沒有用 idempotency 擋住，他的 10 次免費額度會被自己的重試吃掉。
測試點：在 uncertain 狀態下重送同一個請求（帶 / 不帶 `Idempotency-Key`），
核對實際扣減的 ops 數。這是 §6 JO3 的旗艦用例。

### T7｜跨版本升級旅程（P1）

0.5.0 移除了四組指令；「On the first stateful command after upgrading, the CLI removes
obsolete `grants/` files」；README 裡還有一句明顯的文件 bug：
**0.3.0 那段寫「Upgrade with `npm install -g @finchtech/cli@0.5.2`」** —— 版本號對不上段落主題，
而 latest 已經是 0.5.3。

→ 旅程 variant：用 0.4.0 / 0.4.1 / 0.5.0 建立帳號 → 升到 0.5.3 → 確認 session 仍可用、
`grants/` 清理沒有弄壞授權、被移除的指令給出可行動的訊息。

---

## 3. 帳號艦隊設計

### 3.1 金鑰：一顆種子，不是 N 把金鑰

不要產生並保存 N 個獨立私鑰。用**單一 master seed（放 KMS / CI secret）**
按 BIP-32 路徑推導：

```
m/44'/60'/0'/0/<journey_index>
```

好處全是運維上的：
- 只有**一個** secret 要保護、輪替、審計。
- 任何一條歷史旅程都能**重新推導**出同一個地址 → 可回頭查帳、可清理殘留資產。
- 帳本只需要存 index，不存金鑰材料。
- 可以預先把「index 0–999 是 QA 地址」整段登記進白名單（見 §4a）。

J2 的兩個 variant 分別對應：`wallet create`（CLI 自己生）與
`wallet use --file`（寫入推導出的私鑰檔，`chmod 600`）。**兩條都要測** ——
前者測 CLI 的生成路徑，後者測匯入路徑與權限檢查。

### 3.2 帳號帳本（`accounts.jsonl`）

```jsonc
{ "index": 42, "address": "0x…", "state": "burned",
  "variant": { "authChainId": 1776, "walletMode": "import",
               "firstAgent": "no_promo", "firstMode": "task", "cliVersion": "0.5.3" },
  "createdAt": "2026-10-12T…", "freeOpsUsed": 3, "freeOpsGranted": 0,
  "journeyId": "J-0042", "findings": ["T1-confirmed", "T2-confirmed"],
  "handedOffToHarnessA": true }
```

`state`：`virgin` → `in_flight` → `burned`。
**`burned` 永不再用於 virgin 測試**，但會交棒給 Harness A 當溫熱身分（額度不浪費）。

### 3.3 規模：正交抽樣，不是全組合

variant 維度：
`authChainId`(7) × `walletMode`(2) × `firstAgent`(promo / no-promo) ×
`firstMode`(conversation_turn / task / generation) × `transport`(CLI / 直打 API) ×
`cliVersion`(current / upgrade-from)

全組合是 336 條，沒必要。用**正交陣列抽樣**取覆蓋每個維度每個水準至少一次的
最小集合 → **約 24 條旅程 / release**。
再加上固定的 7 條：7 條 auth chain 各一條 happy path（因為 T2）。

**總計約 30 條旅程 × 2–3 次免費調用 ≈ 每個 release 不到 90 次調用。**
這個量級不會逼近任何上限 —— 這點很重要，見 §4b。

### 3.4 隔離：每條旅程一個會被銷毀的容器

J0「乾淨機器」不是比喻，是前提。每條旅程：

```
docker run --rm -e FINCHTECH_HOME=/home/qa/.finchtech node:20 → 跑完即銷毀
```

**不可以用同一個容器跑兩條旅程** —— 殘留的 `~/.finchtech` 會讓第二條不再是 virgin。
這也順便讓 T5 的權限測試變乾淨（可以故意把 `FINCHTECH_HOME` 設成 `chmod 777` 看它怎麼反應）。

### 3.5 測試網優先

J8（付費）走 **Base Sepolia**，主網只留 1–2 條 smoke。
J0–J7 不涉及鏈上轉帳，可以直接在 PROD 跑 —— 這是促銷額度真正的用途。

---

## 4. 兩道我仍然建議保留的護欄（便宜，且完全不影響旅程真實性）

這兩條不是「不要從零走一遍」的替代品 —— 旅程走的是**一模一樣的 code path**，
護欄只在旅程之外作用。

### (a) QA 錢包地址白名單（一張表的工）

把推導出的 QA 地址（例如 index 0–999）登記在一張表，讓這些帳號的 run
可以**從公開聲譽統計與 agent 評分的分母中排除**。

- 旅程本身毫髮無損：它照樣真的註冊、真的簽章、真的調用、真的被計費。
- 只是**事後**在資料層標記，讓 Finch 賣的那本 ERC-8004 工作履歷保持乾淨。
- 成本：一張 address 表 + 統計查詢加一個 `NOT IN`。半天的後端工。

這是我上一份文件裡唯一仍然該堅持的東西，而它跟你要測的東西**不衝突**。

### (b) 促銷池保留水位（防 harness 失控，平常不會觸發）

旅程的第一次調用前，先讀 `call-eligibility` 回傳的 Agent-wide 當日剩餘；
低於保留水位（例如 50%）就今天改派另一個 agent。

依 §3.3 的量級（每 release < 90 次調用），**這條護欄平常根本不會觸發**。
它存在的理由只有一個：當有人把 `--journeys 24` 手滑打成 `2400` 時，
它會停下來，而不是把某個 agent 的當日免費試用名額清空。

---

## 5. 為什麼這件事自動化起來意外地順：CLI 是為自動化設計的

README 裡有一句決定性的話：

> **"Every command prints exactly one JSON value, so there is no `--json` option."**

加上這些：

- 穩定的公開錯誤碼（`CLI_*`、`API_*`、`AGENT_MARKET_*`、`MCP_*`）
- exit code 語意固定（`0` = ok / ready，`2` = 無效輸入或不健康）
- 每個失敗都帶 next-step hint：`fix_request`、`retry`、`login`、`recover`、`contact_support`
- 本地失敗帶 local trace ID，遠端失敗保留原始 domain envelope + remote trace ID

→ **CLI 的輸出契約和 agent 的 schema 契約一樣是機器可驗的。**
整條旅程可以寫成宣告式的 journey spec：

```yaml
# journeys/J-core-promo-conv.yaml
variant: { authChainId: 8453, walletMode: create, firstAgent: promo, firstMode: conversation_turn }
steps:
  - id: J1-install
    run: npm install -g @finchtech/cli@${CLI_VERSION}
  - id: J1-version
    run: finch --version
    assert: { exit: 0, json: { version: "${CLI_VERSION}" } }
  - id: J2-wallet
    run: finch wallet create
    assert: { exit: 0, json: { address: { matches: "^0x[0-9a-f]{40}$" } } }
    capture: { address: $.address }
    secrets_scan: true          # JO5：stdout/stderr 不得出現私鑰
  - id: J2-perms
    shell: stat -c '%a' $FINCHTECH_HOME
    assert: { stdout: "700" }
  - id: J3-login
    run: finch login --chain-id ${authChainId}
    assert: { exit: 0 }
  - id: J4-doctor
    run: finch mcp doctor
    assert:
      exit: 0
      json:
        ready: true
        readinessScope: "cli_session_and_mcp_discovery"
        harnessOAuth.status: "not_checked"     # 文件承諾永遠是這個值
  - id: J7-eligibility
    api: GET /api/v1/agent-market/buyer/call-eligibility?offerId=${offerId}
    assert:
      json:
        fundingSource: "promotion"
        # 全新帳號的促銷剩餘應該等於 grantOperations
        promotion.remainingPersonal: { equals: "${grantOperations}" }
  - id: J7-first-call
    api: POST /api/v1/agent-market/buyer/offers/${offerId}/invocations
    body: { content: [{ type: text, text: "hello" }] }
    assert: { status: 202, json: { handoffState: { in: [accepted, uncertain] } } }
    on_uncertain: poll            # JO3：絕不重送
  - id: J7-decrement
    api: GET /api/v1/agent-market/buyer/call-eligibility?offerId=${offerId}
    assert: { json: { promotion.remainingPersonal: { equals: "${grantOperations} - 1" } } }
```

同一份 spec 換 variant 就產生一條新旅程。**`journeys/` 目錄就是回歸測試套件**，
每次 CLI 發版（頻率是幾天一次）全跑一遍。

---

## 6. 旅程層 Oracle

Harness A 的 oracle 判「輸出符不符合 schema」。Harness B 的 oracle 判的是**旅程品質**：

| # | Oracle | 怎麼判 | 嚴重度 |
| --- | --- | --- | --- |
| **JO1** | **旅程可完成性** | 一個照著文件做的全新用戶能不能走到第一次成功調用。任何一步需要文件沒寫的知識 = 失敗 | **P0** |
| **JO2** | **錯誤可行動性** | 每個失敗必須有 next-step hint，**而且照著做真的能修**。harness 自動執行 hint 建議的指令，看是否脫困 | **P0** —— 這是 onboarding 最常壞、最少被測的一格 |
| **JO3** | **額度會計正確性** | 實際扣減的 ops == 實際成功的調用數。重點用例：uncertain 後重送、失敗調用是否釋放預留（API 承諾 "A failed call releases what it reserved"）、第 10→11 次邊界 | **P0** |
| **JO4** | **狀態可復原性** | 在每一步之後 SIGKILL，用文件列出的 recover 指令救回。README 的所有 recover 路徑 = 測試矩陣 | **P0** |
| **JO5** | **不洩密** | README 明文承諾「secrets are never accepted as command arguments or emitted to stdout」。**掃描整條旅程的全部 stdout/stderr，找私鑰、session bearer、grant token、OAuth authorization code、upload Authorization header** —— 命中一次就是 P0 | **P0（安全）** |
| **JO6** | **冪等性** | 重跑同一個指令不得重複扣費、重複廣播交易。`purchase submit` 的 checkpoint 紀律、`AGENT_MARKET_IDEMPOTENCY_CONFLICT` 的行為 | **P0（資金）** |
| **JO7** | **版本相容** | 舊 CLI 被拒時訊息可行動（server 拒 < 0.4.0）；升級後 `grants/` 清理不破壞授權；被移除的指令給出遷移指示 | **P1** |

**JO5 是最容易自動化、價值最高的一個。** 它不需要任何語意判斷：
把旅程的全部輸出收集起來，用推導出的私鑰、session token、grant token 當關鍵字去 grep。
零誤報，而且一旦命中就是最高級別的安全問題。既然文件明確承諾了，就應該有東西天天驗證它。

**JO4 的做法**也很機械：旅程 spec 裡每一步標 `interruptible: true`，
runner 就會為那一步額外生成一條「執行到這裡 → SIGKILL → 跑 recover → 斷言恢復」的子旅程。
一條 10 步的旅程自動展開成 10 條中斷旅程。

---

## 7. 落地路線

| 階段 | 內容 | 工作量 | 前提 |
| --- | --- | --- | --- |
| **A. Journey runner + 一條 happy path** | container 隔離、spec 解析、JSON 斷言、J0–J7 走通一條（promo agent / conversation_turn / chain 8453） | 3–4 天 | 無（PROD 促銷額度就夠） |
| **B. 艦隊 + variant 矩陣** | master seed 推導、`accounts.jsonl` 帳本、正交抽樣產生 ~30 條旅程、7 條 auth chain 全覆蓋 | 3 天 | QA 地址白名單那張表（§4a） |
| **C. 中斷注入 + 洩密掃描** | JO4 自動展開、JO5 全輸出掃描、JO3 的 uncertain 重送用例 | 3 天 | A |
| **D. 付費旅程（J8）** | Base Sepolia、USDC approve + vault、`purchase` 全部 recover 路徑 | 2–3 天 | 測試網 USDC；**TEST 環境問題的答案（見 §8）** |
| **E. CI 接線** | 每次 `@finchtech/cli` 發版自動觸發（npm registry webhook / 輪詢 dist-tags）＋跨版本升級旅程 | 2 天 | A–C |

**總計約兩週半。** 第一條可跑的旅程在 3–4 天內就會出現，
而且**它大概就會立刻確認 T1**（無促銷 agent 的新用戶死路）。

建議的執行順序理由：**先做 A 並刻意把第一條旅程指向一個「無促銷」的 agent**。
那是成本最低、結論最硬的一槍 —— 它直接量化你 onboarding 漏斗最上面那個洞。

---

## 8. 未決問題（按對設計的影響排序）

| # | 問題 | 為什麼關鍵 |
| --- | --- | --- |
| **1** | **有沒有 TEST 環境，它的 onboarding 跟 PROD 等價嗎？** `/auth.md` 說「The `finch-market` Skill targets production, **not TEST**」，OpenAPI 有 `TestWebsiteSession` scheme，CLI 有 `PRODUCTION_NOT_AVAILABLE` 錯誤碼 → **TEST 環境確實存在。** | 如果 TEST 的註冊/錢包/額度路徑與 PROD 等價，**絕大多數旅程可以在 TEST 跑**：無限量、不碰真實促銷池、不污染履歷 —— 我 §4 的兩道護欄都變成多餘。這是整個設計最大的分叉點，**應該第一個問後端。** |
| **2** | 那 6 個沒有 `promotional` 的 agent 是刻意的還是漏配？ | 決定 T1 是「產品決策」還是「上架流程的 bug」。若是後者，這是上架流程該加的一道驗證。 |
| **3** | chain `1776` 是什麼，為何只是 auth chain？ | 決定 T2 是設計意圖還是不一致。 |
| **4** | Identity / invoke 的 rate limit 是多少？ | 30 條旅程並行可能被誤判為攻擊。**開跑前先跟後端打招呼。** |
| **5** | `administrator_test` 會不會進公開統計？ | Harness A 的前置問題，與本文件獨立。 |

---

## 9. 一頁總結

- **我上一份錯在用溫熱身分測冷啟動。** `administrator_test` 繞過的正是你要測的那段路。
  **你是對的：不從註冊 + 錢包從零走一遍，CLI 端和用戶端的首哩路問題看不到。**
- **證據支持你：** CLI 已發 23 版、0.5.3 是昨天的、0.5.0 還移掉四組指令；
  程式裡本地狀態錯誤路徑約 **98 處**。變動最頻繁、最少被測的就是 onboarding。
- **但量級要重構：一個帳號只能「全新」一次 —— 它是單次使用的測試夾具。**
  所以要的不是幾千個 Sybil 同時刷，是**持續供應新鮮帳號**：
  每個 CLI release 約 30 條旅程 × 2–3 次免費調用。那 10 次免費額度，正確用途就是這個。
  跑完的帳號降級成 Harness A 的溫熱身分，額度一點不浪費。
- **研究階段已經預測到七個陷阱**，最硬的是 **T1**：
  **6/12 個 agent 完全沒有促銷額度 → 全新零餘額用戶在它們身上一次免費調用都做不到，
  第一個回應就是「請先去 Base 買 USDC」。** 這只有零餘額帳號看得見，
  而它就在你 onboarding 漏斗的最頂端。
- **CLI 意外地好自動化**：「每個指令只印一個 JSON 值」+ 穩定錯誤碼 + exit code + next-step hint
  → 旅程可以寫成宣告式 spec，`journeys/` 就是回歸套件。
  JO5（洩密掃描）零誤報、JO4（中斷復原）可自動展開。
- **兩道便宜的護欄**：QA 地址白名單（讓真實旅程的 run 不污染公開履歷，半天後端工）
  與促銷池保留水位（防手滑，平常不觸發）。兩者都**不改變旅程走的 code path**。
- **第一個該問的問題**：TEST 環境的 onboarding 跟 PROD 等價嗎？
  若等價，旅程可以無限量跑，兩道護欄都不需要了。
