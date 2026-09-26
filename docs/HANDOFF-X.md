# X 推廣留言（FlowCredit）— 交接給 Mac 上負責 X 的 session

給在使用者 Mac 上 `~/Documents/x-outreach-agent` 開的 Claude Code session。
你原本負責 Enid 的求職引流（見該專案的 `HANDOFF.md`）。這份文件是**新增的第二個任務**：替 Finch 上架的 agent **FlowCredit** 在 X 上做推廣留言。

- **分工**：雲端 session 負責 Moltbook（repo `a0971025732-netizen/my-c-base`，分支 `claude/epic-planck-mke1vw`）。**X 全部由你負責**，因為只有你這台 Mac 有可用的 x-use 與 cookie。
- 寫於 2026-09-26。狀態以實際查詢為準。

---

## 0. 一分鐘版

- **目標**：在 X 上找「正在煩惱怎麼判斷一個鏈上／Web3 業務是不是真的」的新鮮貼文，留一則**拿掉產品也有價值**的回覆，並帶上 FlowCredit 的連結（含 UTM）。
- **工具**：沿用你現有的 x-use + cookie + `bin/xsearch` + stage → publish。**不用 X API**。從 2026-02-23 起，X API 會拒絕對「沒有 @ 你或引用你」的貼文做程式化回覆，所以只能走瀏覽器。
- **流程**：找文 → 篩選打分 → 寫草稿 → **交給使用者審核** → 通過的才 stage 並 publish → 追蹤成效。
- **這是另一個 campaign**：規則、連結、額度都和 Enid 的求職引流分開，不要混用，也不要為了 FlowCredit 放寬 Enid 那邊的規則。

## 1. 開工前：先取得 FlowCredit 的資料，並向使用者確認一件事

```bash
cd ~/Documents
git clone https://github.com/a0971025732-netizen/my-c-base.git   # 已經 clone 過就 git -C my-c-base pull
cd my-c-base && git checkout claude/epic-planck-mke1vw
# 必讀：
#   docs/finch-outreach-prompt.md   每輪完整規格（STEP 0–10；X 的部分照這份）
#   profiles/flowcredit.yaml        FlowCredit Problem Profile（使用者已確認）
#   runs/flowcredit-r1/review.md    交審卡片的格式範例（Moltbook 版）
```

**向使用者確認（只問這一題）**：FlowCredit 的回覆要用哪個 X 帳號發？是 `enid_main`（@0xenid_），還是另一個帳號？如果是另一個帳號，要照 `x-outreach-agent/HANDOFF.md` 第 2 節重新匯入 cookie。確認之前不要 stage 任何草稿。

## 2. FlowCredit 重點（完整內容見 `profiles/flowcredit.yaml`）

- **X 專用連結（逐字使用、只出現一次、不改參數）**：
  `https://www.finchtech.ai/market/chips/agent-e96e9a01-50aa-4686-bd0e-1aa9cdfcf967/run?utm_source=x&utm_medium=social&utm_campaign=agent_promo_opteam&utm_content=post_flowcredit_v1`
  注意這條是 `utm_source=x`，Moltbook 用的是另一條，不要搞混。
- **它解決什麼**：判斷一個鏈上業務有沒有真實營運（使用量、營收、算力、客戶），產出可追溯到證據的風險評級，檢查做決策前還缺哪些資料，並標出可疑數據。同樣的證據會得到同樣的結果。
- **不適用（`not_for`，命中就淘汰）**：投資建議、「該不該買這個幣」、價格預測、借貸／授信決策、審計意見、智能合約安全審計。
- **免費額度**：每個帳號 10 次，自然帶到就好（Mode D 不提）。
- **不提** TAI／CCI。開發者只在自然的時候說「a QS top-11 university team」，**不能說成是 Finch 做的**，也不能說「我做的」。
- **目標讀者**：Web3 BD／合作夥伴團隊、企業採購與風控、DePIN／AI 算力／鏈上 SaaS 創辦人、生態基金評審、鏈上分析師。

## 3. 每輪流程（X 版，出自 `docs/finch-outreach-prompt.md`）

| STEP | X 的做法 |
|---|---|
| 2 找文 | `bin/xsearch search "<詞>" ... --limit 15 --out /tmp/fc.json`。搜尋詞 = `problem_mapping` 的使用者說法 + `trigger_topics` × 意圖模板（how do I / any tool for / alternative to / workflow / 有沒有工具 / 大家都怎麼）。**中英文都搜**。**時效 < 6 小時，最好 < 2 小時**。候選池目標 40–60 篇 |
| 3 篩選 | 硬門檻：超過時效、已鎖、bot／spam、7 天內對同一作者或同一串留過言、敏感話題、留言 > 200、命中 `not_for`。接著打 Opportunity Score（100 分）：≥70 用 Mode A/B/C，50–69 用 Mode D，<50 淘汰。同主題每輪 ≤ 2 則 |
| 3 配額 | **每輪 8 則，全部帶連結，Mode D ≤ 2**。中英混合，依原文語言 |
| 5 寫 | 1–3 句，講重點；語言跟隨原文（繁簡也跟）；首句不出現產品名；必須提到原文的具體細節。禁用 game-changer、revolutionary、check out、must-try、連續 emoji、全大寫。自評 25 分，**≥ 20 才交審** |
| 6 交審 | 用 `runs/flowcredit-r1/review.md` 的卡片格式列給使用者。使用者逐則回「通過／修改／捨棄」。超過時效一半的標「⚠️ 即將過期」 |
| 7 發佈 | 只 stage 並 publish **通過的**。間隔隨機 8–20 分鐘：`PUBLISH_GAP="480,1200" ./bin/publish`。發佈前再確認原文還在 |
| 8 追蹤 | T+24h、T+72h：存活、讚、回覆、回覆情緒 |
| 10 報告 | 每輪結束：L1–L4 達標率、最佳／最差 3 則、下一輪最多 3 條調整 |

X 的有效標準：T+24h 按讚 ≥ 3，且沒有負面回覆。

## 4. 套用到你現有工具時的注意事項（重要）

- **連結規則衝突**：`stage_drafts.py` 會拒絕「目標貼文以外的任何網址」，那是 Enid campaign 的規則，所以 FlowCredit 的草稿會被擋。
  **做法**：替 FlowCredit 建一份獨立設定（例如 `config/campaigns/flowcredit.json`：允許的連結 = 上面那條 X 連結、`daily_caps`、`not_for` 關鍵字、禁用詞），並讓 `stage_drafts.py`／`cycle.py` 可以用 `--campaign flowcredit` 切換。**預設行為（Enid campaign）一行都不改**。
- **額度分開記**：FlowCredit 不佔 Enid 的每日額度（4 帶連結 + 2 純互動），反過來也一樣。帳本要能區分 campaign（例如 ledger 加 `campaign` 欄位）。
- **同一時間只能有一個發布程序**。兩個 campaign 的 publish 要排隊，不能同時跑，發布期間也不要另外開 xsearch。
- **長度**：x-use 超過 270 字元會靜默截斷。連結經 t.co 縮短後算 24，所以**本文上限 246**。
- **非 BMP 字元（多數 emoji，如 🤣）會讓草稿永久報廢**。FlowCredit 的語氣本來就不用 emoji，lint 照樣要擋。
- **先證明瀏覽器活著，再碰草稿**（`publish_one.py` 的 exit 3 機制）。cookie 失效時不要發。
- **Mac 要保持醒著**：用 `caffeinate -i ./bin/publish`。

## 5. 紀錄放哪裡（兩邊不打架）

- 你的操作紀錄照舊放在 `x-outreach-agent/state/`。
- 另外把 FlowCredit 在 X 的**交審清單與成效**寫回 `my-c-base`，讓兩個平台的週報可以合併：
  - `runs/flowcredit-x-r<N>/review.md`：交審卡片與裁定
  - `history_x.jsonl`（repo 根目錄）：每則已發一行，欄位照 `docs/finch-outreach-prompt.md` STEP 7：`post_url, comment_url, platform=x, author, topic, mode, lang, score, posted_at, utm, 內容摘要`，另加 `round`
- 只動上面這兩類檔案。push 前先 `git pull --rebase origin claude/epic-planck-mke1vw`，因為雲端 session 也會 push Moltbook 的檔案（`runs/flowcredit-r*/`、`history.jsonl`）。

## 6. 不可以做的事

- 不可以發使用者沒通過的留言。
- 不可以貼 FlowCredit X 連結以外的網址，也不可以改連結參數。
- 不可以把 x-use 的 `draft_mode` 關掉，或繞過草稿直接發。
- 不可以在同一串回覆兩次，或和最近 30 則留言高度相似。
- 不可以印出、提交或貼出 cookie。`vendor/x-use/config/*cookies*`、`data/` 絕不進 git。
- 不可以為了湊滿 8 則放寬門檻。誠實的空結果是對的。
- 刪除率 > 20% 或帳號被限制：立即停止，並回報使用者。

## 7. 順手可做（Enid campaign，非 FlowCredit）

1. **9/30 週報前**回填 7 則已發留言的互動數（`xsearch profile @0xenid_` → `cycle.py metrics`），不然週報第 2、3 節會是空的。
2. 把輸入方式從 `send_keys` 改成用 JS 插入文字（`document.execCommand('insertText', …)`），🤣 之類的 emoji 就能打。這是 x-use 的第 4 處本地修改，要記在 HANDOFF 第 3 節。
3. `bin/publish` 啟動前先比對本機 Chrome 主版本和 `chrome_version_main`，不一致就停下來提醒。

---

## 8. 接手 Prompt（在 Mac 的 `~/Documents/x-outreach-agent` 開 Claude Code，整段貼上）

```
你除了原本的 Enid 求職引流，現在新增負責 FlowCredit 在 X 的推廣留言。Moltbook 由另一個雲端 session 負責，你只做 X。
1. 先讀本專案的 HANDOFF.md（Enid campaign 的規則與技術雷區），
   再 clone 或 pull https://github.com/a0971025732-netizen/my-c-base（分支 claude/epic-planck-mke1vw），
   完整讀 docs/HANDOFF-X.md，接著讀 docs/finch-outreach-prompt.md 和 profiles/flowcredit.yaml。
2. 照本專案 HANDOFF.md 第 1 節現查狀態（doctor 應為 5 PASS、沒有 publish 程序在跑），用繁體中文回報。
3. 問我：FlowCredit 要用哪個 X 帳號發。
4. 照 HANDOFF-X.md 第 4 節，替 FlowCredit 建獨立的 campaign 設定，不改 Enid campaign 的預設行為；先 dry-run 驗證。
5. 跑 FlowCredit X Round 1：找文（< 6h，中英文）→ 篩選打分 → 寫 8 則以內 → 用 review.md 卡片格式交給我審。
   我回「通過」的才 stage 並 publish，間隔 8–20 分鐘；發完寫進 my-c-base 的 runs/flowcredit-x-r1/ 和 history_x.jsonl，然後 push。
規則：沒有我明確通過的一律不發；只貼 FlowCredit 的 X 連結；cookie 不進對話、不進 git；不為了湊數放寬門檻。
```
