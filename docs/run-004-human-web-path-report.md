# Run-004 人類端（網站）路徑測試報告

日期：2026-10-14
方法：真實 Chromium + Playwright，注入標準 EIP-1193 錢包（全新 keypair，簽章用 ethers 在本機完成）
帳號：`0x02b55fa89d0c54da3d6987e18039900b23a4d341`（accountId `3c2903ed-7c3f-43d2-ac7d-7d4d161ede9b`）

## 為什麼這一輪重要

Run-001～003 全走 **CLI／API**（`AgentCliSessionBearer`）—— 那是**開發者路徑**。
網站走的是 **`WebsiteSession`**，**完全不同的認證機制**，而真實用戶只會走這條。
這是一整塊沒測過的面。

**結果：人類端完整跑通，全自動，從零到調用成功。**

---

## 0. 走通的完整動線

```
匿名開啟 agent 頁
   → 點「Log in to claim your free credits.」
   → 選「Wallet Log In」（不需要社群帳號）
   → 錢包自動連上（EIP-6963）
   → 點「Sign message」
      POST /api/auth/wallet/challenge   201
      （錢包簽一次字串）
      POST /api/auth/wallet/verify      200
   → GET /api/me                        200  ← 帳號建立完成
   → 畫面顯示「Free Uses: 10 / 10 remaining」
   → 在聊天框輸入 → 點「Send message (use 1 free credit)」
      POST /api/agent-market/conversations/{id}   200
   → agent 回覆出現，額度變成「Free Uses: 9 / 10 remaining」
```

**全程只需要一次簽章。沒有 email、沒有驗證碼、沒有 CAPTCHA、沒有看到速率限制。**

---

## 1. 網站要求簽的那段訊息（只有走人類端才看得到）

```
finch-wallet-auth-v1
Request ID: 74f60cda-cb81-451c-9452-c86157277cfa
Origin: https://www.finchtech.ai
Wallet: 0x02b55fa89d0c54da3d6987e18039900b23a4d341
Chain ID: 8453
Nonce: iiJppAQ-fcYAydwaQt7_uw
Issued At: 2026-10-14T03:34:14.577Z
Expiration Time: 2026-10-14T03:39:14.577Z
```

**安全要素評估：齊全。**

| 要素 | 有沒有 | 說明 |
| --- | --- | --- |
| Domain binding | ✅ `Origin` | 防止釣魚站拿去別處重放 |
| Wallet binding | ✅ `Wallet` | 綁定簽署者 |
| Chain binding | ✅ `Chain ID: 8453` | |
| Nonce | ✅ | 防重放 |
| 簽發時間 | ✅ `Issued At` | |
| **有效期** | ✅ **5 分鐘** | 短且合理 |

**一個觀察（不是 bug，是取捨）**：這是自訂格式 `finch-wallet-auth-v1`，**不是標準的
EIP-4361（SIWE）**。差別在於：錢包（MetaMask、Rabby 等）會把標準 SIWE 訊息渲染成
友善的結構化畫面並附安全提示，而自訂格式只能顯示成一段原始文字。

*等於同樣一份合約，一份是排版清楚的制式表格，一份是手寫的紙條 ——
內容一樣完整，但使用者對後者比較難一眼確認自己在簽什麼。*

對一個要求用戶簽章才能登入的金融類平台，改用標準 SIWE 格式會讓用戶端的信任感高一截。

---

## 2. 人類端與開發者端的差異

| | 人類端（網站） | 開發者端（CLI／API） |
| --- | --- | --- |
| 認證 | `WebsiteSession`（cookie） | `AgentCliSessionBearer` → `FinchMcpBearer` |
| 登入方式 | Passkey／**Wallet**／CLI／legacy API key／社群（google, github, x, discord） | 錢包簽章 |
| **`clientKind`** | **`"H"`** | **`"A"`** |
| Session 長度 | **7 天** | 7 天 |
| 建立耗時 | 約 20 秒（含人點擊） | **3.9 秒**（全自動） |
| 額度呈現 | 「Free Uses: 9 / 10 remaining」+「Available credits: 0」 | `promotion.personalRemaining: "9"` |

### `clientKind` 是個好設計，而且對我們有用

平台已經在資料層區分**人類客戶端（H）與 agent 客戶端（A）**。
這直接解決了我先前提的「QA 地址白名單」需求的一半 ——
**流量來源本來就可以分流統計**，不需要另外建表就能把 agent 端流量從人類端指標裡拆開。

### 額度是同一套，沒有兩套帳 ✅

網站顯示的「Free Uses: 9/10」背後打的就是
`GET /api/v1/agent-market/buyer/call-eligibility?offerId=…&quantity=1` ——
**跟 CLI 路徑同一個端點、同一個配額**。畫面另外把「免費次數」與「已購買 credits」
分成兩個數字顯示（Free Uses: 9/10 remaining ／ Available credits: 0），**這個分法很清楚，是好設計。**

畫面也顯示促銷有效期「Valid until: 2026-11-12」，與 API 的 `expiresAt` 一致。

---

## 3. 發現

### H-1｜P1：OpenAPI 規格與實作不符（v1 API 的認證方式）

OpenAPI 規格裡 `/api/v1/agent-market/buyer/call-eligibility` 的 `security` **只列了
`FinchMcpBearer`**。但實測網站**用 cookie session 直接打這個端點就通了**（200）。

→ 規格漏列了 `WebsiteSession`。對照之下，`/api/skills/envelope` 這類端點就有正確列出
三種 scheme（`AgentCliSessionBearer, TestWebsiteSession, WebsiteSession`），
所以**不是設計如此，是 v1 agent-market 那組的 security 標註漏了**。

**影響**：第三方整合者讀規格會以為非得走 MCP OAuth 拿 grant 不可，
而實際上網站 session 就能用。這會讓整合門檻看起來比實際高。

### H-2｜P2：文案說要「claim」，實際上不用

按鈕寫「Log in to **claim** your free credits.」，但登入完成後**不需要任何領取動作**，
畫面直接就顯示 10 次。文案暗示有一個額外步驟，實際沒有。

小事，但新用戶登入後會去找「領取」按鈕，找不到會疑惑。

### H-3｜P2：匿名載入就產生 401

每次匿名開啟 agent 頁，`POST /api/usage` 都回 **401**，在瀏覽器 console 留下錯誤。
不影響功能，但：
- 所有匿名訪客都會觸發，量很大
- console 的噪音會淹掉真正的錯誤，之後排查問題時礙事

匿名訪客的用量回報應該靜默跳過，或走一個不需要認證的端點。

### H-4｜確認：人類端的帳號創建同樣完全可自動化

這一輪用的是**真實瀏覽器、真實網站程式碼路徑**（不是繞過 UI 直接打 API），
全程只需要：**一個錢包 + 一次簽章**。

沒有 email 驗證、沒有驗證碼、沒有 CAPTCHA、沒有觀察到速率限制。
每個新帳號在**每個 agent** 上各拿到 10 次免費。

這跟 CLI 路徑是同一個面，但現在確認**瀏覽器端也一樣** ——
也就是說擋 CLI 不會有用，兩條路都通。

> 這不是說一定要加 CAPTCHA（那會傷害真實用戶的轉換）。
> 但它是個應該被知道的事實：**免費額度的發放目前只靠「持有一個錢包地址」把關，
> 而產生錢包地址的成本是零。** 如果促銷預算要擴大，這是需要先想清楚的地方。

---

## 4. agent 回答品質（人類端）

提問：`穩定幣跟一般加密貨幣差在哪 簡單講`（擬人化、不工整）

回答（繁體中文，完整切題，自動對上提問語言）：

> 差別就在「會不會大漲大跌」。
> - **一般加密貨幣（如比特幣、以太坊）**：價值會隨市場供需劇烈波動，可能一天漲 20%，
>   也可能隔天跌 50%，適合投資或投機。
> - **穩定幣（如 USDT、USDC）**：價值刻意跟美元（或黃金）掛鉤，1 顆穩定幣幾乎永遠等於 1 美元。
>   它是為了當作「數位現金」或轉帳媒介，讓交易不受到價格暴漲暴跌的影響。
>
> **簡單講**：穩定幣是「數位版的美元」，求穩；一般加密貨幣是「賭漲跌的資產」，求波動。

**語言自動對齊（繁中問 → 繁中答）、用了比喻、結構清楚。** 這一題的品質比我在
Run-001 用工整提問拿到的回答更好。

---

## 5. 這一輪的限制

- **WalletConnect（掃 QR 連手機錢包）測不到。** `api.web3modal.org` 與
  `pulse.walletconnect.org` 被測試環境的網路政策擋住。
  本輪測的是**瀏覽器擴充套件錢包**那條路（桌機主流）。手機用戶那條路仍未覆蓋。
- **Passkey 登入未測**（需要 WebAuthn 虛擬驗證器，Playwright 支援，但這輪沒做）。
- **社群登入（google/github/x/discord）未測** —— 需要真實第三方帳號，
  不適合由自動化流程建立。
- **購買 credits（USDC on Base）未測** —— 需要測試網或真實資金。
  畫面顯示「Estimated payment: 0.015 USDC」、「Buy Credits」按鈕，流程存在但未走。

---

## 6. 待處理清單（接續 Run-002／003）

| 優先 | 問題 | 歸屬 |
| --- | --- | --- |
| **P1** | OpenAPI 的 v1 agent-market 端點漏列 `WebsiteSession`，整合門檻看起來比實際高 | **平台** |
| **P2** | 登入簽章用自訂格式而非標準 EIP-4361／SIWE，錢包無法結構化顯示 | **平台（體驗／信任）** |
| **P2** | 文案說要 claim，實際不用 | **平台（文案）** |
| **P2** | 匿名載入即產生 `POST /api/usage` 401 console 錯誤 | **平台** |
| — | **好設計，記錄下來**：`clientKind` H／A 分流、免費次數與已購 credits 分開顯示、簽章訊息的安全要素齊全（domain／nonce／5 分鐘過期） | — |

### 跨輪總結

- Run-002：6 項待辦，4 項歸平台
- Run-003：再加 1 項平台政策（追問計費）
- Run-004：再加 4 項，**全部歸平台**

**到目前為止累計 11 項待辦，其中 9 項是平台側的一次性工作** ——
規格標註、上架規範、錯誤訊息、計費政策、文案。
不需要逐一去跟 12 個供給方溝通，這仍然是整個排查最有價值的結論。

---

## 7. 下一步可做

1. **Passkey 登入路徑**（Playwright 的虛擬 WebAuthn 驗證器可以做，不需要真實裝置）
2. **購買 credits 流程** —— 需要 Base Sepolia 或少量真實 USDC，會走到
   `purchase transaction → approve → vault` 整條鏈上流程
3. **人類端的服務範圍靶** —— 把 Run-002 的四圈測試改在網站上跑，
   比對「同一個問題、兩條路徑」的回應是否一致（這能測出網站層有沒有額外的
   前處理或後處理）
