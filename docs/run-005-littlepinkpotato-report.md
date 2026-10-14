# Run-005 粉土豆（LittlePinkPotato）三個 offering 測試

日期：2026-10-14
Agent：LittlePinkPotato — AI Job Search & Resume Agent
提問風格：**簡體中文、人類語氣** —— 不完整、少標點、斷句隨意、表達不清楚
帳號：`acct-003`（2 筆）、`acct-002`（1 筆）

---

## 0. 結果一覽

| Offer | 模式 | 宣告單位 | 提問 | 結果 | 實扣 |
| --- | --- | --- | --- | --- | --- |
| AI 求职对话 | conversation | 5 | `想找数据分析的活 新加坡 三年经验 有合适的不` | ✅ completed 33.3s，478 字，答得好 | **1 次** |
| 简历定制 + ATS 评分 | task | 4 | `简历想改下 我产品经理 三年 做过电商 想投字节那种 大厂产品岗 帮我弄下` | ⚠️ input_required，要簡歷 | **0 次** |
| 职位匹配报告 | task | 10 | `后端 五年 python go 都会 想去新加坡 香港也行 远程最好 看看有啥岗` | ⚠️ input_required，要簡歷 | **0 次** |

---

## 1. 我自己要更正的兩件事

### 更正一：免費額度是「次數」，不是「單位」

我原本說「三個 offering 合計 19 單位 > 免費額度 10，所以必須拆成兩個帳號跑」。**這是錯的。**

實測：`AI 求职对话` 宣告 **5 單位**，`eligibility` 也回 `requiredUnits: 5`，
但調用後 `personalRemaining` 只從 **10 → 9**，也就是**扣 1 次**。

所以：

```
promotional.grantOperations: "10"   ← 10 次「操作」
availableOperations: "10"           ← 單位是 operations
requiredUnits: 5                    ← 這是「付費時」要消耗的 Call Rights 單位
```

**免費促銷以「次數」計價，每次調用算 1 次，不管這個 offer 標價 5、10 還是 4 單位。**
`requiredUnits` 只在用購買的 Call Rights 付費時才生效。

→ 一個帳號本來就能跑完三個 offering，不需要拆帳號。我多慮了。

> **對新用戶是好事**：粉土豆最貴的 offer（职位匹配报告，10 單位 = 0.5 USDC）
> 在免費額度下跟最便宜的一樣只算 1 次。免費試用期間，貴的 offer 反而「划算」。

### 更正二：追問計費不是「都會收」，而是「各家不一樣」

Run-002／003 我觀察到 ChatProperty、Maneki、Wheel 的 `input_required` **都收 1 次**，
因此寫了「追問一律收費」。

**粉土豆兩次 `input_required` 都扣 0 次**（9→9、10→10）。

所以正確的說法是：**同樣是「請補充資訊」，有的 agent 收費、有的不收，平台沒有統一政策。**

| Agent | `input_required` 是否扣額度 |
| --- | --- |
| ChatProperty | **扣 1** |
| Maneki | **扣 1** |
| Wheel Option Desk | **扣 1** |
| **LittlePinkPotato** | **扣 0** |

這讓「追問計費需要平台政策」這條待辦**更站得住腳** —— 現在有了直接對照組，
不是「應該免費」的主觀主張，而是「同一個市場裡兩種做法並存」的客觀不一致。

---

## 2. P1｜兩個 task offer 回了位元組完全相同的追問，而且內容對不上其中一個

兩次 `input_required` 的追問文字**雜湊完全相同**（`e9df960d54d4b26a`）：

```
请把你的简历内容贴过来（工作经历、技能、学历都可以简单写），我才能帮你匹配职位。
Please paste your résumé (roles, skills, education) so I can match you to jobs.
```

**問題在「职位匹配报告」上是對的，但用在「简历定制 + ATS 评分」上是錯的。**

「简历定制 + ATS 评分」這個 offer 的自述是：

> Resume tailoring — rewrite your resume **against a specific JD**.
> Returns a structured resume plus **ATS keyword-match analysis**. Delivered as text and DOCX/PDF.

它要做的是「拿簡歷去對一份職缺描述做改寫 + ATS 評分」，所以它至少要**兩樣東西：簡歷 + JD**。
但它只要了簡歷，而且理由寫成「我才能帮你**匹配职位**」—— 那是另一個 offer 的用途。

→ **追問文案是從「职位匹配报告」直接複製過來的，沒有針對這個 offer 改寫。**
使用者照著貼了簡歷之後，大概率還要再被追問一次 JD，或者得到一個不是他要的結果。

---

## 3. 表現好的部分：對話型 offer 完全接得住不工整的簡體中文

提問：`想找数据分析的活 新加坡 三年经验 有合适的不`
（沒有標點、用「活」不用「工作」、「有合适的不」是口語反問）

回答（節錄）：

> 有的，新加坡数据分析师市场需求挺旺盛。三年经验的话，你可以瞄准 **Data Analyst 或
> Senior Data Analyst** 这两个职级，月薪大概在 **SGD 5,000 到 7,000** 之间，具体看公司
> 规模和行业。科技公司、金融机构和电商平台需求最大，像字节跳动新加坡这种大厂，数据分析
> 师年薪能到 **SGD 80K 到 110K**。
>
> 技能方面，**SQL、Python、Tableau 或 Power BI 是标配**，如果会 R 或有机器学习基础会加分。
> 金融科技和电商领域特别看重业务理解能力，不只是跑数据，还得能提出洞察推动决策。
>
> 建议多关注本地招聘平台比如 LinkedIn、JobStreet…

**把三個資訊點（數據分析／新加坡／三年經驗）全部接住**，回了職級、薪資區間、
需求產業、技能要求、求職管道。語言也自動對齊簡體中文。**33.3 秒，品質好。**

這跟 Run-003 的規律一致：**對話型 offer 對口語輸入寬容，task 型 offer 一律先要結構化輸入。**

---

## 4. 這個 agent 的狀態從 Run-001 以來變了

| | Run-001（10/12） | Run-005（10/14） |
| --- | --- | --- |
| 免費促銷 | **無**，三個 offer 全回 `insufficient` | **有**，`grantOperations: 10`，到期 2026-11-12 |
| 每日 Agent 上限 | — | **`dailyRemaining: 99`** |

**兩個連帶影響：**

1. **「11/17 個 offer 新用戶不能免費用」這個統計正在改善**，需要重新掃一次才準。
2. **這是第一個 `dailyRemaining` 有值的 agent。** 我在 Run-002 曾更正過「促銷沒有
   Agent 層級每日共用池」—— 那句話也不完整。正確的是：**這個池存在，但由每個 agent
   各自設定**。Baidu／Maneki 是 `null`（無上限），粉土豆設了每日 100。

   實測三次調用後，`dailyRemaining` 從 99 → 98 → 96，**跨帳號共用**
   （前兩次用 acct-003、第三次用 acct-002，數字是連續遞減的）。
   這證實了每日池確實是 Agent 層級、所有人共用的。

---

## 5. 附錄：完整提問與原始回應

### ① AI 求职对话（conversation_turn，5 單位，acct-003）

**Q**：`想找数据分析的活 新加坡 三年经验 有合适的不`
**事前**：`fundingSource=promotion` 個人剩餘 10 當日 Agent 剩餘 99
**結果**：`completed`，33.3s（上限 90s），478 字元，實扣 1 次 → 剩 9

### ② 简历定制 + ATS 评分（task，4 單位，acct-003）

**Q**：`简历想改下 我产品经理 三年 做过电商 想投字节那种 大厂产品岗 帮我弄下`
**事前**：個人剩餘 9 當日 Agent 剩餘 98
**結果**：`input_required`，13.2s，**實扣 0 次** → 仍剩 9
**追問**：`请把你的简历内容贴过来…我才能帮你匹配职位。`（文案錯置，見 §2）

### ③ 职位匹配报告（task，10 單位，acct-002）

**Q**：`后端 五年 python go 都会 想去新加坡 香港也行 远程最好 看看有啥岗`
**事前**：個人剩餘 10 當日 Agent 剩餘 96
**結果**：`input_required`，11.7s，**實扣 0 次** → 仍剩 10
**追問**：與 ② 位元組完全相同

原始資料：[`snapshots/run-005-littlepinkpotato.json`](snapshots/run-005-littlepinkpotato.json)

---

## 6. 新增待辦

| 優先 | 問題 | 歸屬 |
| --- | --- | --- |
| **P1** | 「简历定制 + ATS 评分」的追問文案是從「职位匹配报告」複製的，說「帮你匹配职位」而非改寫簡歷；且只要簡歷不要 JD，與它自述的功能不符 | 供給方 |
| **P1（加強）** | 追問計費各家不一（粉土豆不收、ChatProperty／Maneki／Wheel 收）→ 需要平台政策 | **平台政策** |
| **P2** | 重新全市場掃描免費額度狀態（粉土豆已從無促銷變有促銷，統計需更新） | 下一輪 |
