# Moltbook 推廣留言 — 交接文件

給接手的雲端 Claude Code session。先讀完這份再動手，尤其是第 2、6、7 節。
每日流程的規格在 `docs/finch-outreach-prompt.md`（v1.2），agent 資料在 `profiles/`。

寫於 2026-09-26。狀態以第 1 節的指令現查為準，不要信文件裡的快照。

---

## 0. 一分鐘版

- **目標**：替 Finch 上架的 agent（目前是 FlowCredit）在 **Moltbook** 引流。做法是在別人的新鮮貼文底下留一則「拿掉產品也有價值」的英文留言，並帶上 agent 連結（含 UTM）。
- **分工**：這個 repo／雲端 session **只做 Moltbook**。X 由使用者的 Mac 負責（本機專案 `~/Documents/x-outreach-agent`，用 x-use + 瀏覽器 cookie），**這裡不碰 X**。
- **怎麼連進 Moltbook**：Moltbook 只有 API 金鑰（`moltbook_...`），沒有 OAuth。金鑰放在環境變數 `MOLTBOOK_API_KEY`，`mb_publish.py` 會直接讀。
- **怎麼發**：兩段式。先交審（`review.md`），使用者逐則回「通過／修改／捨棄」，**通過的才發**。發出去收不回。

## 1. 接手第一步：現查狀態

```bash
cd /home/user/my-c-base
git log --oneline -5
python3 -c "import os;v=os.environ.get('MOLTBOOK_API_KEY','');print('key', 'set' if v else 'MISSING', len(v), v[:9]+'...')"   # 不印整把金鑰
cd runs/flowcredit-r1
python3 -c "import mb_publish as m;s,d=m.call('GET','/agents/me');a=d.get('agent',d);print(s,a.get('name'),a.get('is_claimed'),d.get('debug'))"
python3 mb_publish.py check 9caabb3b-3d7a-4955-89b6-aa959809f6f2   # #1 的原文還在嗎
tail -30 review.md
cat approved.json
```

`/agents/me` 回 200 才能發。回 401 的話請看第 2 節。

**2026-09-26 21:00 UTC 快照（僅供參考）**
- FlowCredit Round 1：找文 1,224 篇，其中 24 小時內 145 篇，精讀 12 篇，交審 3 則。
- #1（m/agentfinance，dealwork.ai 買方集中度）：**已通過、尚未發佈**，一直卡在金鑰。文字在 `approved_1.txt`，時效到 **2026-09-27 18:17 UTC**。
- #2（m/crypto，DePIN 供給對帳）：使用者還沒回覆。
- #3（m/agentfinance，「真營收」標準）：還沒回覆，而且 2026-09-27 00:20 UTC 後已超過 24 小時時效，視同作廢。
- `history.jsonl` 還不存在，也就是一則都還沒發。

## 2. 連進 Moltbook：金鑰與代理（踩過的雷）

- Moltbook 只支援 `Authorization: Bearer moltbook_...`。官方 `skill.md` 明寫沒有 OAuth，也不能用 X 登入。
- **雷：網路代理會蓋掉你帶的金鑰。** 如果雲端環境設定的「API credentials」裡有 moltbook 條目，代理會對 `moltbook.com` 和 `www.moltbook.com` 強制注入它，覆蓋程式送出的 `Authorization`。那個值開頭是 `MOLTBOOK...`（錯誤），Moltbook 就一律回 `401 Invalid API key`，debug 欄位裡是 `keyPrefix: "MOLTBOOK..."`。換 `X-API-Key` 或網址參數也沒用。
  - **解法**：API credentials 裡**不要有** moltbook 條目，只在「環境變數」放 `MOLTBOOK_API_KEY`。改完要**開新 session** 才生效。
  - 判斷方式：debug 的 `keyPrefix` 如果是 `MOLTBOOK...`（大寫），代表代理還在注入；如果是 `moltbook_...` 卻仍然 401，代表金鑰本身錯了，請使用者到 https://www.moltbook.com/login 的後台重新產生。
- 讀取端點（`/posts`、`/search`）不用金鑰也能用，找文不受影響。
- 金鑰**絕不**印出、貼進對話、寫進檔案或 git。只能印開頭 9 個字和長度。
- 詳細比較見 `docs/account-connection.md`。

## 3. 每輪流程（摘要；完整規格是 `docs/finch-outreach-prompt.md`）

| STEP | 做什麼 | 產出 |
|---|---|---|
| 1 | Problem Profile，已有就沿用並修正 | `profiles/<agent>.yaml` |
| 2 | 找文：17 個相關 submolt 的 new 牌 + 語意搜尋，只取 24h 內 | `runs/<round>/mb_pool.json`（用 `mb_discover.py`） |
| 3 | 硬門檻 → Opportunity Score（100 分）→ 多樣性控制 → 每輪配額：**Moltbook 5 則，其中 Mode D ≤ 1** | 精讀清單 `mb_detail.json` |
| 4–5 | 貼文分析、寫留言（英文，60–180 字，Mode A/B/C/D），每則自評 25 分 | 草稿 |
| 6 | **交審**：寫進 `runs/<round>/review.md`，在對話裡請使用者逐則回覆 | 使用者裁定 |
| 7 | 只發通過的：`check` → `post` → 5 分鐘內 `verify` → `log`。**兩則之間至少隔 15 分鐘** | `history.jsonl` |
| 8 | T+24h、T+72h 追蹤讚數、回覆、存活 | 更新 `history.jsonl` |
| 10 | 事後分析報告，規則寫回 `playbook.md` | 報告 |

新的一輪就開新資料夾 `runs/<agent>-r<N>/`，把 `mb_discover.py`、`mb_publish.py` 複製過去，再改裡面的搜尋詞與 UTM。

### 發佈指令（`runs/flowcredit-r1/`）

```bash
python3 mb_publish.py check  <post_id>                   # 原文還在、沒被鎖？
python3 mb_publish.py post   <post_id> approved_<n>.txt  # 發留言，回傳驗證題
python3 mb_publish.py verify <verification_code> <answer> # 5 分鐘內答
python3 mb_publish.py log    <post_id> <comment_id> <n>  # 寫入 repo 根目錄的 history.jsonl
```

`post` 會先檢查留言裡的 agent 連結剛好出現一次，不符合就拒發。
注意：驗證題流程是照 Moltbook 文件寫的，**還沒實際跑通過**。第一次發的時候要看清楚回傳格式，必要時修改 `mb_publish.py`。

## 4. FlowCredit 的規則（`profiles/flowcredit.yaml`）

- Moltbook 連結一律用 `utm_source=social` 那一條，**逐字**使用，不改參數。
- `not_for`：投資建議、價格判斷、借貸／授信決策、審計意見。核心在講這些的貼文直接淘汰。
- 不提 TAI／CCI（定義未確認，CCI 容易和交易指標混淆）。
- 提到開發者時只能說「a QS top-11 university team」，而且只在自然的時候提；不能說成是 Finch 做的。
- 免費額度：每個帳號 10 次，要自然帶到，不寫成促銷。Mode D 不提免費額度。

## 5. 使用者的偏好

- 用繁體中文溝通；做研究時要涵蓋「定位、脈絡、商業價值、前瞻性、上下游、生態系定位、解決問題、應用場景、離落地多遠」，並深入淺出、多用譬喻。
- 交審格式照 `runs/flowcredit-r1/review.md`：每則附分數明細、Mode、原文摘要、分析重點、留言草稿、自評。
- 使用者不想處理憑證細節。卡在設定時，給**一步到位**的操作，不要列一堆選項。

## 6. 技術硬限制與已知問題

- 代理會覆蓋 `Authorization`（見第 2 節）。這是 Round 1 卡了一整晚的原因。
- 系統 Python 的 `urllib` 走代理沒有問題，但**不要**把 `Authorization` 寫死在程式裡。
- `mb_pool.json` 很大（約 1.6 萬行）。新的一輪不要沿用，也不要整份讀進上下文；用 `jq` 或 Python 篩選。
- 雲端容器用完就會被回收：任何狀態（`history.jsonl`、`review.md`、`approved.json`）都要 commit 並 push。
- 開發分支：`claude/epic-planck-mke1vw`（已包含 `claude/quirky-archimedes-v7awr9` 的全部內容）。

## 7. 不可以做的事

- 不可以發使用者沒通過的留言，也不可以自己改過文字就發。修改版必須是使用者給的，或使用者確認過的。
- 不可以在同一串回覆兩次，也不可以跟以前的留言高度相似（README 的 non-negotiables）。
- 不可以印出、提交或貼出任何金鑰或 cookie。
- 不可以碰 X：不找文、不發文、不用 `X_AUTH_TOKEN`／`X_CT0`。X 由 Mac 端負責。
- 不可以為了湊額度放寬門檻。誠實的空結果是對的。

## 8. 檔案地圖

```
HANDOFF.md                         這份
README.md                          harness 架構與 non-negotiables
docs/finch-outreach-prompt.md      每輪的完整規格（STEP 0–10）
docs/account-connection.md         X / Moltbook 連線方式比較
docs/PLAYBOOK.md, phase0-report.md harness 的 playbook 與工具研究
profiles/flowcredit.yaml           FlowCredit Problem Profile（使用者已確認）
runs/flowcredit-r1/
  mb_discover.py                   找文（submolt new + 語意搜尋）
  mb_pool.json / mb_detail.json    候選池 / 精讀
  review.md                        交審清單 + 發佈狀態紀錄
  approved.json, approved_1.txt    已通過的留言
  mb_publish.py                    發佈工具（check / post / verify / log）
history.jsonl                      Moltbook 已發留言（第一次 log 時建立）
history_x.jsonl, runs/flowcredit-x-r*/  X 的紀錄，由 Mac 上的 X session 寫入（見 docs/HANDOFF-X.md），這裡不要改
docs/HANDOFF-X.md                  給 Mac 上負責 X 的 session 的交接
finch_harness/                     Python harness（Reddit/X 為主，Moltbook 目前用 runs/ 下的腳本）
```

---

## 9. 接手 Prompt（開新 session 時整段貼上）

```
你在 a0971025732-netizen/my-c-base 的分支 claude/epic-planck-mke1vw 上接手 Moltbook 推廣留言工作。
先完整讀 HANDOFF.md，再照第 1 節現查狀態，用繁體中文回報：
(1) MOLTBOOK_API_KEY 是否有效（/agents/me 的狀態碼與 keyPrefix，不要印出金鑰）；
(2) FlowCredit Round 1 #1 的原文是否還在、是否還在時效內；
(3) review.md 裡還沒裁定的項目。

如果金鑰有效，而且 #1 還在時效內：直接發佈 #1（使用者已通過），流程是 check → post → verify → log，
發完把留言連結、history.jsonl 那一行和 review.md 的狀態更新 commit 並 push。
如果 401：依 HANDOFF.md 第 2 節判斷是代理注入還是金鑰本身錯誤，用一句話告訴我要改哪裡，其他什麼都不要做。

規則：只做 Moltbook，不碰 X；沒有我明確通過的留言一律不發；金鑰不進對話、不進 git。
之後新的一輪照 docs/finch-outreach-prompt.md 的 STEP 1–10 進行，交審格式照 runs/flowcredit-r1/review.md。
```
