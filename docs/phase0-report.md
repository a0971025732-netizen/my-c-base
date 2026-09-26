# Phase 0 — Harness 初始化研究報告

> 研究日期：2026-09-26　｜　Stars 皆為當日 GitHub API 實測值
> 產出物：`harness/tool_registry.yaml`（持久化 Tool Registry）、`harness/strategy.yaml`（策略基線）、`finch_harness/`（執行程式）

---

## 一句話總結（譬喻）

把 Harness 想成一間**餐廳廚房**：

- **Tool Layer 是廚具**，包括爐子（PRAW）、烤箱（Tweepy）、冰箱（SQLite）和試菜師（Claude judge）。這些買一次就長期用，壞了才換。
- **Strategy Layer 是菜單**。每來一位新客人（新 Agent），就依口味調整。
- **人工審核是出菜前的主廚試吃**。沒有主廚點頭，任何一盤菜都不能端出去。

在 X 上，平台規定**只能由客人自己拿**：系統只能備好菜（草稿加 intent 連結），不能替客人送到桌上（自動回覆）。

---

## 1. 定位

Finch Outbound Harness 是一台**「有揭露的情境式推薦引擎」**，不是群發機器人。

它的工作是在 Reddit 和 X 上找到「這個 Agent 真的能幫上忙」的對話。系統先寫一則即使拿掉連結也有價值的回覆，並標明身份（「我在 Finch 工作」），經人工核准後才發出。

## 2. 脈絡

| 時間 | 事件 | 對本系統的影響 |
| --- | --- | --- |
| 2023-06 | Reddit API 開始收費 | 大量第三方工具停止運作 |
| 2025-11 | Reddit **Responsible Builder Policy**：API 存取改為人工申請與審核 | 沒拿到核准，PRAW 就不能用。這是 Reddit 自動化的**第一道關卡** |
| 2026-02-23 | X API **限制程式化回覆**：原作者必須先 @你 或引用你，才能用 API 回覆 | 「搜尋關鍵字後自動回覆」在技術上被封鎖（X 自動化規則本來就禁止） |
| 2026-05 → 09 | X API 全面改為 pay-per-use（讀一則約 $0.005，發一則約 $0.015，含連結的貼文約 $0.20） | 搜尋有成本，所以要先做語意篩選再擴大抓取 |

**結論：** 2026 年兩大平台都在打擊「LLM 生成的推廣回覆」。能長期運作的做法只有**高品質、揭露身份、人工把關、低頻率**。

## 3. 解決的問題

1. **找得到**：對話分散在上千個社群裡，而且用詞很少剛好等於產品關鍵字。系統用語意查詢加上相鄰主題來解決。
2. **挑得準**：100 分的機會評分，其中 Agent fit 設為硬門檻，避免在不相關的串裡硬塞連結。
3. **寫得好**：35 分的品質閘門、推廣強度 ≤2、最多重寫兩次。
4. **不重複、不洗版**：同一串只回一次，與歷史回覆做相似度比對，每個社群有上限。
5. **學得會**：每次活動後產出 KEEP / CHANGE / TEST / DROP，並自動帶到下一次。

## 4. 商業價值

- **獲客成本**：相較於付費廣告，一則被原 PO 感謝的回覆在搜尋引擎和 Reddit 上的**長尾曝光可以持續數月甚至數年**。
- **意圖品質**：流量來自「正在問問題的人」，比廣告受眾的意圖高出一個層級。
- **品牌風險控管**：揭露身份加上人工審核，避免「被抓到假裝路人」這種對品牌殺傷力最大的公關事件。
- **成本估算（每次活動）**：X 讀取 100–300 則約 $0.5–1.5；Claude 評分加生成約數美元；人工審核約 15–30 分鐘。

## 5. 上下游與生態系定位

```
上游（資料來源）            本系統（中游：判斷＋內容＋把關）          下游（轉換）
Reddit Data API  ─┐                                                  ┌─> Finch Agent 頁面
X API v2         ─┼─> 發現 → 評分 → 草稿 → 品質閘門 → 人工審核 → 發布 ─┼─> 試用 / 使用
Web search / MCP ─┘        ↑                                  │      └─> Finch analytics（CSV 匯入）
                           └──────── Campaign Memory ←── 量測 ←┘
```

在生態系裡，本系統介於「社群聆聽工具」（例如 Brand24、GummySearch 類，只負責找）和「社群發文工具」（例如 Buffer 類，只負責發）之間。它補上的是中間那段「**判斷＋撰寫＋守規**」。

## 6. 工具選型（GitHub 篩選結果）

| 能力 | 選用 | Stars | 層級 | 理由 |
| --- | --- | ---: | --- | --- |
| Reddit 搜尋 / 讀串 / 留言 / 量測 | **praw-dev/praw** | 4,260 | Preferred | 官方 API 的標準封裝，BSD-2，2026-09-25 仍有提交，0 open issues |
| X 搜尋 / 量測 | **tweepy/tweepy** | 11,181 | Preferred | 官方 v2 API，MIT，文件完整 |
| X 回覆 | **X Web Intent（人工）** | – | – | **MANUAL REVIEW REQUIRED**。API 回覆已被封鎖，且違反自動化規則 |
| 網頁搜尋 | Claude WebSearch / API web_search | – | 一方 | 結果經 `finch import` 進入同一條流水線 |
| 語意判斷 / 生成 / 評審 | Claude（anthropic SDK，structured outputs） | – | 一方 | 預設模型 `claude-opus-5`，已啟用伺服器端 refusal fallback |
| 儲存 / 記憶 | SQLite | – | 內建 | 零維運，單檔即可備份 |
| Finch 點擊 / 使用 | CSV 匯入 | – | – | **MANUAL REVIEW REQUIRED**。要等 Finch 提供 analytics API |

**淘汰名單（保留作為稽核紀錄）：**

| 工具 | Stars | 淘汰原因 |
| --- | ---: | --- |
| d60/twikit | 4,695 | 使用 X 內部 API 和帳號 cookie，違反服務條款 |
| vladkens/twscrape | 2,803 | 多帳號輪替，與「不建立假身份」衝突 |
| nirholas/XActions | 545 | 用瀏覽器自動留言，等於規避平台限制 |
| bisguzar/twitter-scraper | 4,005 | 已封存（archived） |
| xdevplatform/xdk-python | 47 | 官方出品但低於 50 stars，Tweepy 已涵蓋相同功能。若 Tweepy 跟不上 API 變動再重新評估 |
| karanb192/reddit-mcp-buddy | 837 | 只能讀取，與 PRAW 重疊。可選用於互動式探索 |

## 7. 應用場景

- **新 Agent 上線冷啟動**：丟入 URL，一小時內產出 5–8 則高品質回覆等待審核。
- **長青型 Agent 的常態曝光**：每週跑一次，用記憶避免重複，逐步收斂到最有效的社群和風格。
- **市場研究（副產品）**：被評為 qualified 的對話本身就是使用者痛點的第一手資料。

## 8. 前瞻性

- **平台只會更嚴**：兩大平台都在針對 LLM 推廣內容加強執法。以「揭露＋人工審核＋品質閘門」為核心的設計，是少數能持續合規的路線。
- **可替換性**：Tool Layer 和 Strategy Layer 分離。未來加入 Hacker News、Discord、LinkedIn 時，只要新增一個 discovery/publishing adapter。
- **量測閉環**：Finch 一旦提供 analytics API，只需替換 `import_conversions`，轉換資料就能直接回饋到風格和社群的權重。

## 9. 距離實際落地還有多遠

| 項目 | 狀態 | 缺什麼 |
| --- | --- | --- |
| 程式與流程 | ✅ 完成，離線端到端測試通過 | — |
| Claude 判斷與生成 | ⚠️ 程式就緒 | `ANTHROPIC_API_KEY`（沒有的話，由 Claude Code 對話中的 orchestrator 或人工撰寫草稿） |
| Reddit 搜尋與發布 | ⚠️ 程式就緒 | **Reddit Data API 核准**，時程不可控（數天到數週）。核准前只能用公開 JSON 唯讀搜尋，並人工貼文 |
| X 搜尋與量測 | ⚠️ 程式就緒 | `X_BEARER_TOKEN` 加上預付 credits |
| X 回覆 | 🔒 永久人工 | 平台政策所致，並非技術問題 |
| Finch 轉換資料 | ⚠️ CSV 匯入 | Finch analytics 匯出或 API |
| 本雲端環境的網路 | ❌ reddit.com / x.com 被 egress proxy 擋住 | 需要在允許這些網域的環境中執行（或調整環境網路政策） |

**譬喻：** 車已經造好也通過試車（測試全部通過），現在還差**駕照**（Reddit API 核准）、**油**（X credits 和 Claude API key），以及**一條能上路的道路**（開放網路的執行環境）。

## 10. 重新研究的觸發條件

只有在以下情況才重跑 Phase 0：實作失敗、套件被棄用、平台 API 或政策變更、repo 停止維護、出現明顯更好的替代方案，或缺少必要能力。其餘時候，每次活動都直接載入 Registry。

---

### 參考來源

- [X's automation development rules](https://help.x.com/en/rules-and-policies/x-automation)
- [X Developers：限制程式化回覆公告](https://x.com/XDevelopers/status/2026084506822730185)
- [X API pay-per-usage pricing](https://docs.x.com/x-api/getting-started/pricing)
- [Reddit Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)
- [Reddit Data API in 2026（申請流程整理）](https://www.redditapis.com/blogs/reddit-data-api-2026)
- GitHub：[praw-dev/praw](https://github.com/praw-dev/praw)、[tweepy/tweepy](https://github.com/tweepy/tweepy)、[d60/twikit](https://github.com/d60/twikit)、[vladkens/twscrape](https://github.com/vladkens/twscrape)、[xdevplatform/xdk-python](https://github.com/xdevplatform/xdk-python)、[karanb192/reddit-mcp-buddy](https://github.com/karanb192/reddit-mcp-buddy)
