# 全自動試錯流程設計

**自動創建錢包 → 註冊 → 多場景 prompt 調用 → 試錯收斂 → 自動退場**

研究日期：2026-10-12
前兩份是「測什麼 / 為什麼」：[契約 fuzz](qa-fuzz-harness-design.md)、[全新旅程](virgin-journey-harness-design.md)
**本文件是「流程怎麼跑」** —— 一條無人看管、可重複、可收斂的流水線。

---

## 0. 流程全貌

```
                    ┌──────────────────── ORCHESTRATOR ────────────────────┐
                    │  讀 catalog → 排場景 → 算需要幾個帳號 → 派工 → 收斂  │
                    └──┬────────────────────────────────────────────────┬──┘
                       │ 派工（每個 worker 一個乾淨容器）              │ 回報
          ┌────────────▼────────────┐                                  │
          │   WORKER（單次使用）     │  ← 一個帳號 = 一個單次測試夾具   │
          └────────────┬────────────┘                                  │
                       │                                               │
   S1 ───────────────► S2 ──────────► S3 ────────► S4 ────────► S5 ────┘
  生錢包            註冊拿 grant     場景裝填      執行調用      試錯收斂
  (離線,0 網路)     (challenge→      (配額內排程   (3 種 mode    (變異/最小化
                     sign→session     8 個場景)     分派+輪詢)    /指紋化)
                     →grant)
                       │                                               │
                       └──────────────► S6 退場（額度交棒 / 銷毀容器）◄┘
                                               │
                                     ┌─────────▼─────────┐
                                     │  S7 TRIAGE & 出單  │
                                     │  去重→嚴重度→通報  │
                                     └───────────────────┘
```

一句話：**Orchestrator 把「要測的場景總數」除以「每個帳號的免費配額」，
算出要生幾個帳號，然後每個帳號在一個用完即丟的容器裡從生錢包開始走完全程。**

### 流水線的核心常數

| 常數 | 值 | 來源 |
| --- | --- | --- |
| 每個帳號免費配額 | **10 ops** | `promotional.grantOperations` |
| 每個帳號跑的場景數 | **8** | 留 2 次給配額邊界測試（第 10→11 次） |
| 市場規模 | 12 agent / 15 offer | 實測 catalog |
| 場景類別 | 10 類（§4） | 本設計 |
| **一次全量 sweep** | 15 offer × 10 類 ≈ **150 個 case** | |
| **→ 需要帳號數** | 150 ÷ 8 ≈ **19 個** | **這就是艦隊規模，不是幾千個** |

> 配額不是障礙，它是**排程單位**。10 次免費額度剛好切成「8 個場景 + 2 次邊界測試」，
> 所以「一個帳號」自然成為流水線的批次大小。

---

## 1. Worker 生命週期狀態機

每個 worker 是一個獨立容器裡的獨立帳號。狀態機必須**可從任何狀態復原**，
因為 worker 會死（容器被回收、網路斷、CLI 卡住），而死掉的 worker 不能讓整個 sweep 停擺。

```
        ┌─────────┐
        │ SPAWNED │  容器起來，FINCHTECH_HOME 空的
        └────┬────┘
             ▼
        ┌─────────┐   失敗→ WALLET_FAILED（本地 bug，P0，不耗配額）
        │ WALLETED│  有地址，私鑰在本地 chmod 600
        └────┬────┘
             ▼
        ┌─────────┐   失敗→ REGISTER_FAILED（註冊流程 bug，P0）
        │REGISTERED│  有 AgentCLI Session
        └────┬────┘
             ▼
        ┌─────────┐   失敗→ GRANT_FAILED
        │ GRANTED │  有 FinchMcpBearer（只含 discover + buyer:read + buyer:invoke）
        └────┬────┘
             ▼
        ┌─────────┐   這一步決定這個帳號值不值得繼續
        │  PROBED │  讀到 call-eligibility：確認 fundingSource 與剩餘配額
        └────┬────┘
             ▼
        ┌─────────┐◄──┐ 每個場景一次往返
        │EXERCISING│  │ 跑完一個場景就 checkpoint，死了可續跑
        └────┬────┘───┘
             ▼
        ┌─────────┐
        │ DRAINED │  配額用盡或場景跑完
        └────┬────┘
             ▼
        ┌─────────┐
        │ RETIRED │  findings 上繳、帳號交棒溫熱池、容器銷毀
        └─────────┘
```

**每次狀態轉移都寫一筆 checkpoint 到 orchestrator**（不是寫在容器裡 —— 容器會消失）。
所以 worker 在 `EXERCISING` 第 5 個場景時死掉，orchestrator 知道：
這個帳號還剩 3 次配額、已完成 5 個 case，可以起一個新容器**用同一個推導出的私鑰**接著跑。
這是「單一種子推導」真正的運維價值：**worker 可丟棄，帳號不可丟棄。**

---

## 2. S1 — 自動創建錢包

```
輸入：journey_index（整數）
輸出：address、本地 keystore
網路：零。這一步完全離線。
```

**流程**

1. 從 KMS 取 master seed（整個系統只有這一個 secret）。
2. 推導 `m/44'/60'/0'/0/<journey_index>` → 私鑰。
3. 兩條 variant 二選一（orchestrator 指派）：
   - **A. CLI 自己生**：`finch wallet create` → 測 CLI 的生成路徑。
     地址由 CLI 決定，回寫進帳本。
   - **B. 匯入推導的金鑰**：寫 `key.hex`（64 hex，`chmod 600`）→ `finch wallet use --file key.hex`
     → 測匯入路徑與權限檢查。地址可預測。
4. 斷言：`$FINCHTECH_HOME` 權限 `700`、金鑰檔 `600`、`finch wallet list` 的輸出正確。
5. **洩密掃描**：這一步的 stdout/stderr 絕不得出現私鑰（CLI 明確承諾過）。命中即 P0。

**為什麼要兩條 variant**：A 測「新手點兩下就有錢包」的路，B 測「我已經有錢包要搬進來」的路。
後者是老用戶遷移的路徑，壞了不會有人回報，因為他直接走了。

**為什麼用推導而不是隨機生成一堆私鑰**：只有一個 secret 要保管；任何歷史帳號都能重新推導回來
（續跑、查帳、清理殘留資產）；可以把「index 0–999」整段預先登記為 QA 地址。

---

## 3. S2 — 自動註冊

這是最關鍵也最容易壞的一段。**同一個註冊流程要用兩種 transport 各跑一遍**，
因為它們走不同的 code path，而壞的地方不一樣：

### Transport A：走 CLI（模擬正常用戶）

```
finch login --chain-id <AUTH_CHAIN>        # auth chain 輪替 7 條：1,10,56,8453,42161,43114,1776
finch mcp doctor                            # 5 項 check 全綠才算註冊成功
finch status                                # 身分對齊
```

### Transport B：直打 API（模擬第三方整合者）

```
POST /api/v1/identity/agent-cli/challenges   { walletAddress(小寫), chainId }
  → challengeToken
本地簽 message
POST /api/v1/identity/agent-cli/sessions     { challengeToken, message, signature,
                                               chainId, sessionTokenCommitment }
  → AgentCliSession
POST /api/v1/identity/agent-cli/grants       { grantId(uuid), grantTokenCommitment,
                                               scopes[](ASCII 字典序!), expiresAt }
  → FinchMcpBearer
```

**scopes 固定只要三個**（ASCII 排序後）：

```
agent_market:buyer:invoke
agent_market:buyer:read
agent_market:discover
```

**絕不申請 `agent_market:buyer:purchase`。** 這讓整條流水線在結構上**無法花錢** ——
即使試錯迴路寫出無窮迴圈，額度用盡就是 `insufficient`，而不是自動去買更多。
這是整個系統最重要的一道安全閘，而且它是**結構性的**，不靠紀律。

### 註冊階段的自動斷言

| 斷言 | 為什麼 |
| --- | --- |
| 7 條 auth chain 每條至少跑一次 | `1776` 在 auth 清單但不在 market 清單裡，這條路只有真的用它登入才走得到 |
| Transport B 刻意送 EIP-55 大小寫地址 | API pattern 是 `^0x[0-9a-f]{40}$` 只吃小寫；錢包 UI 給的都是 checksummed → 第三方整合必踩。要看錯誤訊息有沒有說清楚 |
| scopes 亂序 / 重複 / 空 / >16 個 | 驗證 `x-finch-order: ascii_lexicographic` 的錯誤訊息是否可行動 |
| challenge 重用、過期、換 key 簽、改 chainId | 註冊安全性 |
| 每一步後 SIGKILL 再復原 | CLI 有約 98 處本地狀態錯誤路徑，只有真的被打斷才觸發 |

---

## 4. S3 — 場景裝填（prompt 與場景矩陣）

**這一步完全離線，不花配額。** Orchestrator 先把所有 case 生成好、排程好，才派工。

每個 case = `(offerId, 場景類別, 具體輸入, 預期判定)`。
輸入的生成來源有兩個：**offer 自己公佈的 `inputSchema`**（機械生成邊界值）
＋ **場景庫**（人寫的語意場景，每個 agent 的 description 決定它該會做什麼）。

### 十類場景

| # | 類別 | 怎麼生 | 在找什麼 |
| --- | --- | --- | --- |
| **C1** | **本職任務** | 從 agent 的 `description` 推它宣稱會做的事，寫 3 個正常請求 | 基準線。也是比 `availability.status` 可信的真實心跳 |
| **C2** | **schema 邊界** | 機械生成：`text` 長度 `{1, 2, maxLength-1, maxLength}`；陣列長度 `{minItems, minItems+1, maxItems-1, maxItems}` | bug 密度最高的地方 |
| **C3** | **空白與歧義** | 空字串、純空白、純標點、單一 emoji、只有一個換行 | 零輸入處理。常見 500 來源 |
| **C4** | **語言與編碼** | 中英日混排、RTL、零寬字元、組合字、代理對、`\u0000` | 序列化路徑 |
| **C5** | **未宣告欄位** | top-level 塞 `system` / `model` / `temperature` / `role` 等未宣告欄位 | **13/15 個 offer 是 `additionalProperties: true`** → 被忽略？被透傳給 provider？還是 500？這是全市場最一致的一塊未定義行為 |
| **C6** | **長上下文** | payload 逼近 65536 bytes 上限、深度逼近 64、節點數逼近 10000 | 平台的 canonical JSON 編碼邊界 |
| **C7** | **格式要求** | 要求輸出 JSON / 表格 / 指定欄位 | 回應能不能通過它自己發佈的 `outputSchema` |
| **C8** | **多輪與狀態** | `continue` 續談；對 `maxInputRounds: 0` 的 offer 硬送 continue；拿 A agent 的 `conversationId` 去 B agent | 狀態機違規 |
| **C9** | **檔案輸入** | 依 `artifactContract` 生成：合法 media type、不合法 media type、`maxBytesPerItem` ±1、數量超出 `count` range | 檔案路徑的契約執行 |
| **C10** | **能力外請求** | 問 agent 明顯做不到的事（問股票 agent 幫你訂機票） | **應該優雅拒絕，不該 500 或沉默超時。** 這是真實用戶最常做的事 |

> **明確不做**：不設計誘導第三方 agent 產生有害輸出的 prompt。那不是找 bug，
> 那是在攻擊供給方的模型，而供給方（百度、Powerdrill 等）沒同意被這樣測。
> C1–C10 測的是**契約與健壯性**，這是平台方有正當性做的事。

### 場景如何塞進配額

```
一個帳號 = 8 個場景 + 2 次邊界測試

分配原則：一個帳號只打一個 offer（避免跨 offer 污染），8 個場景抽樣覆蓋 C1–C10
         最後 2 次用來撞配額邊界（第 10 次成功 → 第 11 次必須是 insufficient）
```

**一次全量 sweep：15 offer × 10 類 ≈ 150 case ÷ 8 ≈ 19 個帳號。**

---

## 5. S4 — 執行調用

### 依 `interactionMode` 分派（實測：task 9 / conversation_turn 5 / generation 1）

```
conversation_turn → POST /buyer/offers/{offerId}/invocations
                    （續談時帶 conversationId）
task / generation → POST /buyer/offers/{offerId}/tasks
                    （需要補輸入時 POST /buyer/tasks/{taskId}/inputs）
direct_api_v1     → POST /buyer/versions/{versionId}/invocations
                    （契約在 service detail 頂層，不在 offers[]）
```

### 每次調用的硬規則（寫死在唯一的調用出口裡）

1. **先 `call-eligibility`**。`fundingSource` 不是 `promotion`（本流程預期值）就中止並記錄
   —— 這同時是 T1 的偵測器：無促銷的 agent 會回 `insufficient`。
2. **一律帶 `Idempotency-Key`**，key = `hash(journey_index, case_id, attempt)`。
3. **`handoffState: "uncertain"` 絕不重送**，改輪詢 `invocation_get` / `tasks/{id}`。
   這是 API 明文要求的，也是最容易讓新用戶自己吃掉免費額度的坑。
4. **輪詢上限取該 offer 的 `maxDurationSeconds`**（實測跨幅 90s–1800s），不要寫死。
5. 調用前後各讀一次 eligibility，比對實際扣減 == 該 offer 的 `callRightUnits`
   （實測有 1 / 4 / 5 / 8 / 10 五種值，不能假設是 1）。

### 結果分類（這是試錯迴路的輸入）

每個 case 執行完歸成六類之一：

| 分類 | 意義 | 下一步 |
| --- | --- | --- |
| `PASS` | 回應符合 outputSchema，時間內完成 | 丟棄，不佔配額了 |
| `CONTRACT_VIOLATION` | 回應不符合它自己發佈的 outputSchema / artifactContract | **→ 進試錯迴路最小化** |
| `REJECTED_VALID` | 合法輸入被拒（本地已先用 inputSchema 驗過） | **→ 進試錯迴路最小化** |
| `TIMEOUT` | 超過 `maxDurationSeconds` 或卡住不終結 | → 重跑一次確認非偶發，再最小化 |
| `BILLING_MISMATCH` | 扣減 ≠ `callRightUnits`，或失敗未釋放預留 | **→ 平台側 bug，最高優先，不需最小化直接出單** |
| `LEAK` | 回應或錯誤訊息出現 provider endpoint / 憑證 / stack trace | **→ 安全，直接出單** |
| `GRACEFUL_REFUSAL` | 能力外請求被優雅拒絕（C10 的預期結果） | PASS 的一種 |

---

## 6. S5 — 試錯收斂迴路（這才是「試錯」的核心）

沒有這一段，整條流水線就只是個會發請求的機器人。**有了這一段，它才會自己把 bug 挖深。**

```
          ┌──────────────┐
          │ 執行一個 case │
          └──────┬───────┘
                 ▼
          ┌──────────────┐  PASS 且已見過的指紋
          │   分類 + 指紋 ├──────────────────────► 丟棄（不值得花配額）
          └──────┬───────┘
                 │ 有趣（新指紋 / 非 PASS / 延遲異常）
                 ▼
          ┌──────────────┐
          │  變異擴散     │  同一個 case 往外長 3–5 個鄰居：
          │  (MUTATE)    │  · 長度 ±1 / ×2
          └──────┬───────┘  · 換語言 / 換編碼
                 │          · 加一個未宣告欄位
                 │          · 換 oneOf 分支
                 ▼          · 同一輸入打另一個 offer（是個別 agent 還是全平台？）
          ┌──────────────┐
          │  最小化       │  二分刪減：能刪的欄位刪掉、能縮的長度縮短
          │  (SHRINK)    │  直到再刪一個字就不再復現
          └──────┬───────┘
                 ▼
          ┌──────────────┐
          │  可重放最小用例 │  → 存進 corpus，成為永久回歸測試
          └──────────────┘
```

### 指紋化（去重的關鍵）

```
fingerprint = hash(結果分類, 錯誤碼, outputSchema 違規的欄位路徑,
                   HTTP status, 正規化後的錯誤訊息骨架)
```

**正規化**：把訊息裡的 UUID、時間戳、trace ID、數字全部換成佔位符，
這樣「同一個 bug 的 50 次觸發」會收斂成一個指紋。
→ 報告裡呈現的是**不同的 bug 數**，不是觸發次數。這是報告有沒有人願意看的分野。

### 配額感知的試錯預算

變異會長出新 case，但配額是有限的。所以：

```
每個帳號：8 個種子場景
發現「有趣」的 case 時：變異預算從「還沒跑的種子場景」裡借
                        （一個確認的 bug 比三個沒跑的正常場景有價值）
配額用完 → orchestrator 起一個新帳號接手未完成的變異隊列
```

**關鍵設計**：變異隊列是**全局的**，存在 orchestrator，不在 worker 裡。
所以「某個 agent 在長輸入上有問題」這個線索，可以跨帳號、跨 sweep 持續追下去。
*就像偵查工作：線人（帳號）會換，案卷（變異隊列）要留著。*

### 最小化為什麼非做不可

一個「6000 字的中日混排 + 三個未宣告欄位 + 99 個陣列元素」的 repro，
供給方收到會直接忽略。
最小化之後變成「`content: [{type:"text", text:"​"}]` 回 500」——
這個供給方會修。**最小化是讓 finding 真的被修掉的那一步。**

---

## 7. S6 — 自動退場

```
配額用盡 / 場景跑完
   │
   ├─► findings + checkpoint 上繳 orchestrator
   ├─► 帳號狀態寫 burned，交棒給溫熱池（剩餘額度給契約 fuzz 用，不浪費）
   ├─► 容器銷毀（連 FINCHTECH_HOME 一起，不留殘留）
   └─► 若指派了退場 variant，先跑：
         finch logout        （驗證遠端撤銷）
         finch logout --local（驗證只清本地、remoteRevoked: false）
         wallet 切換 / 跨版本升級後的 grants/ 清理
```

**一個容器只跑一個帳號，跑完即銷毀。** 不可以復用 ——
殘留的 `~/.finchtech` 會讓下一個帳號不再是全新的，整個流程的前提就塌了。

---

## 8. S7 — Triage 與自動出單

```
findings（含指紋）
   │
   ├─ 指紋已存在且已出單 ─────► 只累加 occurrence，不重複出單
   ├─ 指紋已存在但已標記修復 ──► 回歸！升級嚴重度，重新出單
   └─ 新指紋
        │
        ├─ BILLING_MISMATCH / LEAK ───► 平台工單，P0，立即通知
        ├─ CONTRACT_VIOLATION ────────► 供給方通報（附最小 repro + case_id）
        ├─ REJECTED_VALID ────────────► 供給方或平台（看是 schema 還是 runtime）
        └─ TIMEOUT ───────────────────► 併入該 agent 的 SLA 統計
```

**出單內容必須包含**：最小化後的請求原文、offer 的 `inputSchemaHash` /
`outputSchemaHash` / `offerRevision`（證明測的是哪個版本的契約）、
remote trace ID、以及一行可直接重放的命令。

**跨 sweep 的趨勢表**才是這套系統真正交付的東西：

```
agent / offer | 契約合規率 | 平均延遲 | SLA 違反 | 開放 findings
```

這張表可以直接變成產品特性（listing 上標「契約合規率 99.2%，平台每日自動驗證」），
也是往後 A2A 階段 agent 之間自動選品的依據。

---

## 9. 排程器與全局控制

```
orchestrator
├── catalog 同步       每日：抓 catalog，diff schema hash / offerRevision / 新上架
│                             → 契約變了就自動重排該 offer 的全部場景
├── 觸發條件           · CLI 新版發佈（npm dist-tags 輪詢，實測幾天一次）
│                      · catalog diff 有變
│                      · 每日定時全量 sweep
│                      · 手動
├── 併發控制           預設 4 個 worker 併行（不是 400；見下）
├── 預算閘             每日每 agent 調用上限；超過硬停，不是警告
├── 促銷池水位         調用前讀 call-eligibility 的 Agent-wide 剩餘，
│                      低於保留水位（50%）就今天換一個 offer
└── 變異隊列           全局持久化，跨帳號跨 sweep
```

### 為什麼併發是 4 而不是 400

一次全量 sweep 是 150 個 case。併發 4、每個 case 平均 30 秒 → 約 20 分鐘跑完。
**再快沒有意義，而且**：

- 併發 400 會撞 rate limit，你量到的是自己的 429，不是 agent 的 bug。
- 併發 400 會在幾分鐘內把某個 agent 的 Agent-wide 當日免費額度清空，
  讓真正想試用的買家看到「請先購買 Call Rights」。
- **找 bug 靠的是輸入多樣性，不是併發量。** 一萬次問同一個問題，找到的 bug 等於一次。

真的要測「平台在高併發下會不會壞」是另一回事，那該用 staging + mock provider 打自己的 API，
不要打第三方供給方的 runtime。兩個目標分開，各用對的工具。

---

## 10. 資料模型（四張表就夠）

```
accounts        index, address, derivation_path, state(virgin|in_flight|burned),
                variant(auth_chain, wallet_mode, transport, cli_version),
                free_ops_granted, free_ops_used, created_at, handed_off

cases           case_id, offer_id, version_id, scenario_class(C1..C10),
                input_json, generated_from(schema|library|mutation),
                parent_case_id,            -- 變異來源，可追溯譜系
                offer_revision, input_schema_hash

runs            run_id, case_id, account_index, attempt,
                funding_source, units_charged, latency_ms,
                outcome(PASS|CONTRACT_VIOLATION|...), fingerprint,
                remote_trace_id, raw_request, raw_response

findings        fingerprint, first_seen_run, occurrences, severity,
                owner(platform|provider), minimal_case_id,
                status(open|reported|fixed|regressed), ticket_url
```

`cases.parent_case_id` 是試錯迴路的脊椎 —— 它讓你能回答
「這個 bug 是從哪個種子場景、經過幾次變異挖出來的」，
下次就知道該往哪個方向多投配額。

---

## 11. 落地順序

| 階段 | 做什麼 | 工作量 | 可驗收的產出 |
| --- | --- | --- | --- |
| **P1** | S1+S2 走通一個帳號：容器 → 生錢包 → 註冊 → 拿 grant → 讀到 eligibility | 2–3 天 | **一個全自動生出來的帳號，印出它的 `fundingSource`** |
| **P2** | S3+S4：場景庫 C1–C3 + 唯一調用出口（eligibility / idempotency / uncertain 三條硬規則） | 2–3 天 | 一個帳號跑完 8 個場景的報告 |
| **P3** | S5 試錯迴路：分類、指紋、變異、最小化 | 3 天 | **一份最小化後、可重放的 repro** |
| **P4** | S6+S7+排程器：艦隊、退場、去重出單、趨勢表 | 3 天 | 每日自動 sweep 的合規率趨勢表 |
| **P5** | 場景庫補到 C4–C10 + 7 條 auth chain + Transport B（直打 API） | 2–3 天 | 全量 sweep |

**約兩週半。P1 的三天內就會知道一件事**：把第一個帳號指向一個**沒有促銷**的 agent，
看它的第一個回應是不是 `insufficient` —— 那是你 onboarding 漏斗最頂端的洞，
一個全新零餘額帳號就能量出來。

### 兩個前置依賴

1. **QA 地址白名單**（半天的後端工）：把 index 0–999 的推導地址登記一張表，
   讓這些 run 可以從公開聲譽統計的分母排除。
   流程本身毫髮無損 —— 一樣真的註冊、真的簽章、真的調用、真的被計費，
   只是**事後**標記，讓你賣的那本 ERC-8004 工作履歷保持乾淨。
2. **TEST 環境是否與 PROD 等價**（問後端）：
   `/auth.md` 說「targets production, **not TEST**」、OpenAPI 有 `TestWebsiteSession`、
   CLI 有 `PRODUCTION_NOT_AVAILABLE` → **TEST 環境確實存在。**
   如果它的註冊 / 錢包 / 配額路徑與 PROD 等價，**整條流水線可以在 TEST 無限量跑** ——
   配額不再是排程單位，促銷池水位和白名單都不需要了。
   **這是整個設計成本最大的分叉點，值得第一個問。**

---

## 12. 一頁總結

- **流程是一條流水線，批次單位是「一個帳號」**：
  S1 離線生錢包 → S2 註冊拿 grant（只拿三個 scope，**不拿 purchase**，結構上無法花錢）
  → S3 離線裝填 8 個場景 → S4 執行（eligibility / idempotency / 不重送 uncertain 三條硬規則）
  → S5 試錯收斂（分類 → 指紋 → 變異 → 最小化）→ S6 退場交棒 → S7 去重出單。
- **配額不是障礙，是排程單位。** 10 次免費 = 8 個場景 + 2 次邊界測試。
  150 個 case ÷ 8 ≈ **19 個帳號一輪全量**。艦隊是十幾個，不是幾千個。
- **worker 可丟棄，帳號不可丟棄。** checkpoint 在 orchestrator、私鑰由單一種子推導
  → 容器死掉可以用同一個帳號接著跑，剩餘配額不浪費。
- **試錯迴路是這套東西和「笨機器人」的分野**：變異擴散讓它自己挖深，
  最小化讓 finding 真的會被修，指紋化讓報告呈現「幾個 bug」而不是「幾次報錯」。
  變異隊列放在全局，所以線索能跨帳號、跨 sweep 追下去。
- **併發 4 不是 400。** 找 bug 靠輸入多樣性不靠併發；併發拉高只會讓你量到自己的 429，
  並且清空真實買家的當日免費試用名額。
- **三天內可驗收的第一槍**：第一個自動生成的帳號，指向一個沒有促銷的 agent，
  看它的第一個回應。那就是 onboarding 漏斗最頂端那個洞的量化。
