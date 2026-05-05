# Stock-Analyze Workflow

雙視角股市深度分析工作流。循序呼叫本地 MLX 以兩種專家人設分析，再由 Claude 綜合產出決策摘要。

## Input

- `$ARGUMENTS`: `[date] [feed]`
  - `date`（可選）：`YYYY-MM-DD` 或 `MM-DD`，預設今天
  - `feed`（可選）：`國際財經` / `臺股動態`，預設全部

---

## Phase 1: Data Preparation（資料準備）

### Step 1.1: MLX Health Check

```bash
result=$(bash ~/.claude/skills/scripts/health-check.sh mlx)
```

- `status: "ok"` → 繼續
- `status: "down"` or `"no_model"` → 告知使用者 MLX 不可用，回退為 Claude Agent 模式（見 Fallback 章節）

### Step 1.2: Git Sync

```bash
git -C ~/Obsidian/stockDB fetch origin 2>/dev/null
LOCAL=$(git -C ~/Obsidian/stockDB rev-parse HEAD 2>/dev/null)
REMOTE=$(git -C ~/Obsidian/stockDB rev-parse origin/main 2>/dev/null)
```

- 若 `LOCAL != REMOTE`：`git -C ~/Obsidian/stockDB pull --rebase`
- 若無 git remote：跳過

### Step 1.3: Resolve Date & Locate Files

1. 解析日期參數：
   - 無參數 → 今天 (`currentDate`)
   - `MM-DD` → `{currentYear}/{MM-DD}`
   - `YYYY-MM-DD` → `{YYYY}/{MM-DD}`

2. 定位檔案：
   - 若指定 feed → `~/Obsidian/stockDB/原始資料/{feed}/{YYYY}/{MM-DD}.md`
   - 若未指定 → Glob `~/Obsidian/stockDB/原始資料/*/{YYYY}/{MM-DD}.md`

3. 用 Read 讀取所有匹配檔案的完整內容

4. 若無任何檔案存在 → 回報「{date} 無資料」並結束

### Step 1.4: Data Summary

快速統計：
- 各 feed 文章數量
- 總新聞數
- 回報給使用者：「找到 {N} 篇新聞（國際財經 {n1} / 臺股動態 {n2}），以本地 MLX 循序分析中...」

### Step 1.5: Data Truncation（資料截斷策略）

MLX 本地模型 context 有限（~8K tokens 有效輸入）。若新聞原文過長：

1. 計算所有新聞的大概字數
2. 若超過 **6000 字**，按時間倒序保留最新的文章，直到總字數在 6000 字以內
3. 在分析結果中註明「因 MLX context 限制，已截取最近 {N} 篇（共 {total} 篇）」
4. 截斷後的資料同時用於兩次 MLX 呼叫，確保兩位專家分析同一份資料

---

## Phase 2: Sequential MLX Expert Analysis（循序 MLX 專家分析）

**IMPORTANT**: MLX 為單模型本地推理，無法平行處理。兩次呼叫必須循序執行。

### Step 2.1: Wall Street Analyst（華爾街財經專家）

使用 `mcp__mcp-ai-bridge__mlx_chat` 工具：

```
mcp__mcp-ai-bridge__mlx_chat(
  systemPrompt: "<Wall Street system prompt — 見下方>",
  message: "<完整新聞資料>",
  maxTokens: 4096
)
```

**System Prompt**:

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

**Message**: 完整新聞資料（或截斷後的資料），前面加上：
```
以下是 {date} 的股市新聞原始資料，請依框架進行分析：

---

{news content}
```

收到結果後暫存為 `$WALL_STREET_RESULT`。

### Step 2.2: Geopolitical Analyst（國際政治關係專家）

使用 `mcp__mcp-ai-bridge__mlx_chat` 工具：

```
mcp__mcp-ai-bridge__mlx_chat(
  systemPrompt: "<Geopolitical system prompt — 見下方>",
  message: "<完整新聞資料>",
  maxTokens: 4096
)
```

**System Prompt**:

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

**Message**: 同 Step 2.1 使用的相同新聞資料。

收到結果後暫存為 `$GEOPOLITICAL_RESULT`。

---

## Phase 3: Claude Quality Review（Claude 品質審閱）

Claude 對兩份 MLX 報告進行快速品質檢查（非完整四維審閱，僅掃描明顯問題）：

### 檢查項目

1. **框架完整性**：是否所有要求的章節都有涵蓋？缺少的章節由 Claude 補充。
2. **數據引用**：是否有引用具體數字？若 MLX 忽略了關鍵數據點，Claude 補入。
3. **明顯謬誤**：是否有與原始資料矛盾的事實性錯誤？若有，Claude 修正。

- 若兩份報告品質可接受 → 直接進入 Phase 4
- 若有缺漏或錯誤 → Claude 在報告末尾附加 `[Claude 補充]` 段落修正，不重新呼叫 MLX

---

## Phase 4: Synthesis（綜合決策摘要）

由 Claude（Grand Secretary 角色）綜合兩份報告產出最終報告。

### Output Format

```markdown
# 📊 stockDB 雙視角深度分析 — {date}

> 資料來源：{feeds} | 新聞數：{count} 篇
> 分析引擎：本地 MLX (Gemma4-26B) | 綜合：Claude
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

## Fallback: MLX Unavailable（MLX 不可用回退方案）

若 Phase 1 健康檢查發現 MLX 不可用：

1. 告知使用者：「MLX 不可用，回退為 Claude Agent 模式」
2. 改用 Agent 工具平行發出兩個 subagent：
   - Agent 1: `wall-street-analyst` 人設 + 新聞資料
   - Agent 2: `geopolitical-analyst` 人設 + 新聞資料
3. 兩個 Agent **必須在同一個 message 中平行發出**
4. 其餘流程（Phase 3 品質審閱跳過，Phase 4 綜合）不變

---

## Rules

1. Phase 2 使用 `mcp__mcp-ai-bridge__mlx_chat`，以 `systemPrompt` 注入專家人設
2. 兩次 MLX 呼叫**循序執行**（本地單模型，無法平行）
3. 新聞資料超過 6000 字時必須截斷，兩次呼叫使用相同截斷資料
4. Claude 負責品質審閱與綜合摘要，不再額外呼叫 MLX
5. 全程使用繁體中文
6. 若某一視角的新聞較少（例如無明顯地緣政治內容），MLX 仍須產出報告，但可註明「本日地緣政治事件密度較低」
7. `maxTokens` 設為 4096，確保 MLX 有足夠空間產出完整分析
