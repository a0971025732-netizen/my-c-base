# 補充：從官網登入 / 註冊 Finch — 人類網頁路徑

> **用途**：補上 `finch-mcp-howto.md` 缺的一塊 —— 不裝 CLI、直接在
> **官網瀏覽器**完成登入/註冊並調用 agent 的流程。給下游 session 當教學文案原料。
>
> 每段標 **【實測】**（本 session 用真實瀏覽器跑過、附實際畫面與網路行為）或
> **【僅見入口】**（登入視窗裡看得到這個選項，但本 session 未親自走完，教學作者需自行驗證）。
>
> 平台：Finch（`https://www.finchtech.ai`）　｜　文檔日期：2026-10-15

---

## 0. 先講最關鍵的一句

**Finch 官網沒有「填 email + 設密碼」那種傳統註冊。**
在官網，「登入」和「註冊」是同一個動作 —— **你用某個身分（錢包 / Passkey / 社群帳號）
第一次通過驗證，帳號就自動建立了**，不需要另外填表。

這點務必在教學開頭講清楚，否則使用者會一直找「註冊按鈕」。

---

## 1. 進入點：從哪裡開始登入　【實測】

打開任何一個 agent 的頁面（例如市集裡點進一個 agent 的 **Run** 頁），
畫面上會有兩個入口，點任一個都會跳出登入視窗：

- 右上角的 **「Log In」**
- 頁面中間綠色橫幅 **「Log in to claim your free credits.」**（登入領免費額度）

> 【實測】未登入時，聊天輸入框可以打字，但送出鈕是灰的、寫著
> 「Log in to send a message and claim your free credits.」—— 逼你先登入。

---

## 2. 登入視窗裡有哪些方式　【實測畫面】

點開後，標題是 **「Log In to Finch」**，底下一句 **「Choose a login method.」**，
提供這些方式：

| 方式 | 說明（畫面原文） | 本文狀態 |
| --- | --- | --- |
| **社群帳號** | "Use a social account already linked to Finch." 支援 **Google、GitHub、X、Discord** | 【僅見入口】 |
| **Passkey Log In** | "Passkey secrets stay in your credential manager." | 【僅見入口】 |
| **Wallet Log In** | "Wallet sign-in never asks for a seed phrase." | **【實測，走完全程】** |
| **CLI Log In** | 給已經用 CLI 登入的人 | 【僅見入口】 |
| **Have a legacy API key?** | 舊版 API key 登入 | 【僅見入口】 |

> 【實測】登入方式查詢自 `GET /api/auth/social/providers`，實際回傳
> `providers: ["google","github","x","discord"]`。

**教學建議**：對一般沒有加密錢包的使用者，**社群帳號登入（Google 等）是門檻最低的入口**，
教學主線建議用它；錢包登入則寫成「進階 / 已有錢包的人」。
（但注意：社群與 Passkey 本 session 未親自驗證，見 §5。）

---

## 3. 【實測完整走通】錢包登入 / 註冊這條路

這是本 session 唯一從頭走到底、且**成功建立帳號並調用 agent** 的網頁路徑。

### 步驟

1. 點「Wallet Log In」。
2. 畫面顯示兩步進度：**① Connect wallet → ② Sign to log in**。
3. 點 **「Connect wallet」**，跳出錢包選擇視窗（RainbowKit），列出
   MetaMask、Coinbase Wallet、Rabby、Trust、Phantom、OKX、TokenPocket 等。
4. 選你的瀏覽器錢包（例如 MetaMask），在錢包裡核准連線。
5. 連上後點 **「Sign message」**，錢包跳出一段**要你簽名的訊息**（不是交易、不花 gas）。
6. 簽完 → 帳號建立完成。

### 【實測】簽名時看到的訊息全文

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

> **教學要點**：簽名**只是證明「這個錢包是你的」，不會動你的錢、不花手續費、
> 也絕不會問助記詞**。畫面上 Finch 也明寫 "Wallet sign-in never asks for a seed phrase"。
> 這句話對消除新手恐懼很重要，建議教學原樣引用。

### 【實測】背後發生的事（給技術向教學參考）

```
POST /api/auth/wallet/challenge   → 201（拿到待簽訊息）
（使用者在錢包簽名）
POST /api/auth/wallet/verify      → 200（驗證通過，建立 session）
GET  /api/me                      → 200（帳號就緒）
```

`/api/me` 回傳確認帳號已建立：

```json
{"accountId":"3c2903ed-7c3f-43d2-ac7d-7d4d161ede9b",
 "authMethod":"wallet","clientKind":"H",
 "walletBinding":{"walletAddress":"0x02b5…d341"},
 "sessionExpiresAt":"2026-10-21T03:34:15.586Z"}
```

> 【實測】登入 session 有效 **7 天**（`sessionExpiresAt`）。

---

## 4. 【實測】登入後就能調用，不用再裝任何東西

登入成功後，agent 頁面立刻變化：

- 左側出現 **「Free Uses: 10 / 10 remaining」**（免費 10 次），下方標 **Valid until**（到期日）。
- 聊天送出鈕從灰色變成可按的 **「Send message (use 1 free credit)」**。

接著就是最單純的使用：

1. 在聊天框輸入問題（例如「穩定幣跟一般加密貨幣差在哪 簡單講」）。
2. 點 **「Send message (use 1 free credit)」**。
3. 等 agent 回覆出現，左上角免費次數變成 **9 / 10**。

> 【實測】整個過程完全在瀏覽器裡完成，不需要 CLI、不需要寫任何程式。
> agent 回答會自動對齊你的提問語言（中文問、中文答），回覆品質良好。

### 【實測】網站的免費額度怎麼顯示

畫面把兩種額度分開顯示，這個設計很清楚，教學可以直接照搬解釋：

| 畫面文字 | 意思 |
| --- | --- |
| **Free Uses: 9 / 10 remaining** | 免費試用次數（每個 agent 各 10 次） |
| **Available credits: 0** | 你另外用 USDC 買的額度（新帳號是 0） |

> 【實測】網站的免費次數與 CLI/API 路徑**是同一套額度、同一個後端**，不是兩套帳。
> 「1 Credit per request」= 每次調用 1 次。

---

## 5. 本 session 未親自驗證、教學作者需自行確認的部分

誠實標註，避免下游把「沒驗證的」當成「實測的」寫出去：

| 項目 | 狀態 | 原因 |
| --- | --- | --- |
| **社群登入（Google / GitHub / X / Discord）** | 【僅見入口】 | 需要真實第三方帳號，本 session 未走。**但這很可能是一般使用者的主流入口**，教學主線若用它，請務必自己跑一遍截圖。 |
| **Passkey 登入** | 【僅見入口】 | 需要 WebAuthn 裝置/驗證器，未測 |
| **手機錢包（掃 QR / WalletConnect）** | 未覆蓋 | 測試環境擋掉了 WalletConnect 中繼站，只測到「桌面瀏覽器擴充錢包」這條 |
| **購買 credits（USDC on Base）** | 未測 | 畫面有「Buy Credits」「Estimated payment: 0.015 USDC」，流程存在但本 session 未走鏈上付款 |

---

## 6. 給教學文案作者的提醒

1. **開頭破除誤解**：官網沒有傳統 email/密碼註冊，「登入 = 註冊」，第一次驗證就建好帳號。
2. **分層級寫入口**：
   - 最低門檻（主線）：**社群帳號登入**（但需作者自行驗證，§5）
   - 進階：**錢包登入**（本文 §3 已完整實測，可直接採用）
3. **消除錢包恐懼**：強調「簽名不花錢、不是交易、不問助記詞」，直接引用官網原句。
4. **把「免費 10 次 / 每個 agent」講清楚**：最吸引新手的點，別讓人誤會成全站 10 次。
5. **登入後即用**：純網頁使用者不需要碰 CLI，§4 那三步就是全部。
6. **標【僅見入口】的方式請先自己跑過再寫**；標【實測】的（錢包登入全程 + 調用）可直接採信。

---

## 附：事實來源

- 錢包登入全程、簽名訊息、`/api/me`、免費額度顯示、網頁調用：本 session 2026-10-14 真實瀏覽器實測（見 `docs/run-004-human-web-path-report.md`）
- 登入方式清單：登入視窗畫面 + `GET /api/auth/social/providers` 實際回傳
- 社群 / Passkey / 手機錢包 / 購買流程：僅見入口或未覆蓋，需自行驗證
