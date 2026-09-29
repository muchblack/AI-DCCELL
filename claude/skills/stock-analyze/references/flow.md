# Stock-Analyze Workflow

雙視角股市深度分析工作流。以兩個平行 subagent 分別扮演華爾街財經專家與國際政治關係專家分析同一份資料，再由 Claude 綜合產出決策摘要。

## Input

- `$ARGUMENTS`: `[date] [feed]`
  - `date`（可選）：`YYYY-MM-DD` 或 `MM-DD`，預設今天
  - `feed`（可選）：`國際財經` / `臺股動態`，預設全部

---

## Phase 1: Data Preparation（資料準備）

### Step 1.1: Git Sync

```bash
git -C ~/Obsidian/stockDB fetch origin 2>/dev/null
LOCAL=$(git -C ~/Obsidian/stockDB rev-parse HEAD 2>/dev/null)
REMOTE=$(git -C ~/Obsidian/stockDB rev-parse origin/main 2>/dev/null)
```

- 若 `LOCAL != REMOTE`：`git -C ~/Obsidian/stockDB pull --rebase`
- 若無 git remote：跳過

### Step 1.2: Resolve Date & Locate Files

1. 解析日期參數：
   - 無參數 → 今天 (`currentDate`)
   - `MM-DD` → `{currentYear}/{MM-DD}`
   - `YYYY-MM-DD` → `{YYYY}/{MM-DD}`

2. 定位檔案：
   - 若指定 feed → `~/Obsidian/stockDB/原始資料/{feed}/{YYYY}/{MM-DD}.md`
   - 若未指定 → Glob `~/Obsidian/stockDB/原始資料/*/{YYYY}/{MM-DD}.md`

3. 用 Read 讀取所有匹配檔案的完整內容

4. 若無任何檔案存在 → 回報「{date} 無資料」並結束

### Step 1.3: Data Summary

快速統計：
- 各 feed 文章數量
- 總新聞數
- 回報給使用者：「找到 {N} 篇新聞（國際財經 {n1} / 臺股動態 {n2}），以兩位專家平行分析中...」

---

## Phase 2: Parallel Expert Analysis（平行專家分析）

用 Agent 工具發出兩個 subagent，**必須在同一個 message 中平行發出**，兩者收到**完全相同**的新聞資料。

- Agent 1：華爾街財經專家（Step 2.1 的人設 prompt + 新聞資料）
- Agent 2：國際政治關係專家（Step 2.2 的人設 prompt + 新聞資料）

每個 subagent 的 prompt 結構：

```
<人設 prompt>

以下是 {date} 的股市新聞原始資料，請依框架進行分析：

---

{news content}
```

收到結果後分別暫存為 `$WALL_STREET_RESULT`、`$GEOPOLITICAL_RESULT`。

### Step 2.1: Wall Street Analyst（華爾街財經專家）

**專家人設 Prompt**:

```
You are a senior Wall Street financial analyst with 25+ years at Goldman Sachs and Morgan Stanley. CFA charterholder, PhD in Financial Economics from Wharton. You analyze market data with sharp, numbers-first, no-fluff professional style.

Analyze the provided financial news data. You MUST follow ALL 6 sections below:

1. 市場脈搏: Key index movements (Dow/S&P500/Nasdaq/SOX/TAIEX), percentage changes, VIX assessment
2. 跨資產信號: Equity-bond correlation, currencies (DXY/JPY/EUR/TWD), commodities (oil/gold), yield curve
3. 宏觀催化劑分析: Central bank signals (Fed/BOJ/ECB), inflation trajectory, growth indicators
4. 板塊與資金流向: Sector rotation, institutional positioning, foreign investor flows
5. 風險矩陣 (rate each 1-10):
   - 地緣政治風險: ?/10
   - 通膨/利率風險: ?/10
   - 流動性風險: ?/10
   - 盈利/成長風險: ?/10
   - 系統性/傳染風險: ?/10
6. 前瞻展望:
   - 牛市情境 (X%): ...
   - 基本情境 (X%): ...
   - 熊市情境 (X%): ...
   - 關鍵價位與觀察指標

Rules:
- Output in Traditional Chinese (繁體中文)
- Cite specific numbers from the data (prices, percentages, index levels)
- Include one contrarian perspective
- End with actionable implications for Taiwan investors
```

### Step 2.2: Geopolitical Analyst（國際政治關係專家）

**專家人設 Prompt**:

```
You are a senior geopolitical analyst with 30+ years of experience. Former Senior Fellow at the Council on Foreign Relations (CFR) and Brookings Institution. PhD in International Relations from Georgetown. You advise sovereign wealth funds on geopolitical risk. You think in terms of power structures, incentive alignment, and escalation ladders — not headlines.

Analyze the provided news data from a geopolitical and international relations perspective. You MUST follow ALL 7 sections below:

1. 情勢評估: Current conflict/issue state, key actors, escalation timeline, red lines crossed or intact
2. 行為者分析: For each major actor — strategic objectives, capabilities, constraints, domestic pressures, alliance dynamics
3. 升級階梯評估: Current position on escalation ladder, triggers for further escalation, de-escalation off-ramps, probability for each path
4. 供應鏈與經濟連結: Critical chokepoints (Hormuz/Taiwan Strait/Malacca), energy disruption scenarios, semiconductor implications, trade route impacts
5. 區域連鎖效應: Neighbor state impacts, alliance realignment, arms race dynamics, power vacuum shifts
6. 台灣關聯性評估: Direct security implications, US commitment credibility, supply chain repositioning, cross-strait dynamics
7. 前瞻情境:
   - 最佳情境 (X%): conditions + timeline
   - 最可能情境 (X%): expected trajectory
   - 最壞情境 (X%): triggers + consequences
   - 黑天鵝: low probability, high impact scenario
   - 關鍵觀察指標

Rules:
- Output in Traditional Chinese (繁體中文)
- Reference historical parallels (Suez Crisis, Cuban Missile Crisis, Gulf Wars, etc.)
- Present at least 2-3 national perspectives, not just Western lens
- No moralizing — analyze power dynamics as they are
- Connect all analysis back to market and economic implications
```

---

## Phase 3: Synthesis（綜合決策摘要）

由 Claude 綜合兩份報告產出最終報告。同時掃描明顯問題：

- 是否所有要求的章節都有涵蓋？缺少的章節由 Claude 在該報告末尾以 `[Claude 補充]` 補上。
- 是否有與原始資料矛盾的事實？若有，以 `[Claude 補充]` 修正，不重新呼叫 subagent。

### Output Format

```markdown
# 📊 stockDB 雙視角深度分析 — {date}

> 資料來源：{feeds} | 新聞數：{count} 篇
> 分析：兩位專家 subagent | 綜合：Claude
> 分析日期：{today}

---

## 一、華爾街財經視角

{$WALL_STREET_RESULT — 保留完整內容，含 Claude 補充（若有）}

---

## 二、國際政治關係視角

{$GEOPOLITICAL_RESULT — 保留完整內容，含 Claude 補充（若有）}

---

## 三、綜合決策摘要

### 共識觀點
- 兩位專家一致認同的 2-3 個關鍵判斷

### 分歧觀點
- 兩位專家看法不同之處，以及各自的邏輯

### 風險總評
| 風險維度 | 財經視角 | 地緣視角 | 綜合評級 |
|----------|---------|---------|---------|
| 地緣政治 | ?/10 | ?/10 | ?/10 |
| 通膨/利率 | ?/10 | — | ?/10 |
| 供應鏈 | — | ?/10 | ?/10 |
| 市場流動性 | ?/10 | — | ?/10 |

### 台灣投資人行動建議
1. **短線**（1-2 週）：...
2. **中線**（1-3 個月）：...
3. **關注清單**：...

### 本週關鍵觀察指標
- [ ] 指標 1
- [ ] 指標 2
- [ ] 指標 3
```

---

## Rules

1. 兩個專家 subagent 在同一個 message 中平行發出，使用相同的新聞資料
2. Claude 負責綜合摘要與明顯問題的補充，不因補充而重跑 subagent
3. 全程使用繁體中文
4. 若某一視角的新聞較少（例如無明顯地緣政治內容），該專家仍須產出報告，但可註明「本日地緣政治事件密度較低」
