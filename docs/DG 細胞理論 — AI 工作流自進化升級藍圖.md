---
category: 資源/技術
created: 2026-03-17
tags: [ai-workflow, self-evolution, architecture, claude-code, ccb]
---

# DG 細胞理論 — AI 工作流自進化升級藍圖

> 以《機動武鬥傳G 鋼彈》惡魔鋼彈 DG 細胞的三大理論作為隱喻框架，
> 對照現有 Claude Code + CCB 多 AI 協作工作流體系，分析可升級之處。

## 三大理論概述

| 理論 | 原始概念 | 映射到 AI 工作流 |
|------|---------|-----------------|
| 自我再生 Self-Regeneration | 只要核心還在，就能極短時間回復原狀 | 工作流容錯、自動降級、狀態恢復 |
| 自我增殖 Self-Multiplication | 感染生物/機械，數量幾何級數增加 | 改進自動擴散、跨 skill 共享、新專案自動繼承 |
| 自我進化 Self-Evolution | 根據環境/對手自動調整進化 | 學習記憶、自適應閾值、動態路由 |

---

## 一、自我再生（Self-Regeneration）

### 現有能力（已具備）

| 機制 | 所在 Skill | 說明 |
|------|-----------|------|
| MLX → Claude 降級 | `/dev`, `/mlx-reason`, `/linus-analyze` | MLX 不可達時 Claude 接手 |
| Ollama → Claude 降級 | `/dev`, `/ollama-code` | Ollama 不可達時 Claude 接手 |
| 狀態持久化 | `.ccb/state.json`, `.dev-state.json` | 工作進度可跨 session 恢復 |
| `/dev --resume` | `/dev` | 從中斷點續接 |
| `/continue` | context-transfer | 載入上次 session 脈絡 |
| AutoLoop daemon | `/tr` | 步驟完成後自動觸發下一步 |

### 缺口與升級方案

| 缺口 | 影響 | 升級方案 |
|------|------|---------|
| 無瞬態重試（transient retry） | 網路抖動即判定失敗 | 加入 3 次指數退避重試（MLX/Ollama/cross-review） |
| 無回滾機制 | 中間步驟成功但後續失敗，狀態不一致 | 引入 checkpoint + rollback（寫入前快照 state.json） |
| state.json 無完整性驗證 | 手動編輯後可能損壞 | 加入 JSON Schema 驗證 + 自動修復 |
| 無死鎖偵測 | 跨 AI 非同步通訊可能永遠等待 | 加入 timeout watchdog（超時自動降級/跳過） |
| Provider 健康探測被動式 | 要手動 `/cping` | 各 skill 執行前自動 pre-flight health check |

---

## 二、自我增殖（Self-Multiplication）

### 現有能力（已具備）

| 機制 | 說明 |
|------|------|
| 抽象角色系統 | CLAUDE.md Role Assignment，一處改全域生效 |
| 共用文件 | `~/.claude/skills/docs/` 放 protocol/format，多 skill 共享 |
| Instinct 系統 | `/learn` 提取的 instinct 在新 session 自動載入 |

### 缺口與升級方案

| 缺口 | 影響 | 升級方案 |
|------|------|---------|
| Prompt 優化各自為政 | `/mlx-code` 和 `/ollama-code` 各自維護 `prompts.json`，學到的教訓不共享 | 統一 prompt registry：一處學習，全域受益 |
| 審查模板重複 | Linus 3-tier review 在多個 skill 各寫一份 | 抽出共用 review engine，各 skill 呼叫同一套 |
| 新專案冷啟動 | 每個新專案從零開始，不繼承已學到的 corrections | 全域 corrections pool：跨專案共享常見錯誤模式 |
| Skill 模板無自動繁殖 | 建新 skill 需手動搭建結構 | skill scaffold 生成器：從模板一鍵生成新 skill |
| 跨平台適配器手動維護 | `/dev` 有 3 個 adapter，新增平台需手寫 | adapter 自動發現 + 註冊機制 |

---

## 三、自我進化（Self-Evolution）

### 現有能力（已具備）

| 機制 | 說明 |
|------|------|
| corrections JSONL | `/dev` 記錄 MLX/Ollama 失敗，注入下次 context |
| Prompt 自動優化 | `/mlx-code`、`/ollama-code` 失敗 2 次後自動改寫 prompt template |
| Instinct 學習 | `/learn` 從觀察中提取模式 → 審批 → 載入行為準則 |
| Rubric 評分 | `/all-plan` Phase 4 用 Rubric A 量化計畫品質 |

### 缺口與升級方案

| 缺口 | 影響 | 升級方案 |
|------|------|---------|
| 學習記憶無 TTL | `corrections.jsonl` 無限增長，舊資料稀釋新教訓 | 加入衰減機制：保留最近 N 條 + 高嚴重度永久保留 |
| 閾值靜態不可調 | Rubric 通過分 7.0、max attempts 2-3 都是硬編碼 | 引入自適應閾值：根據歷史通過率動態調整 |
| 無 skill 效能追蹤 | 不知道哪個 skill 常失敗、哪個 provider 常超時 | 加入 skill telemetry：記錄成功率、耗時、降級頻率 |
| 無工作流自動重組 | 固定流程，無法根據任務特性跳過不需要的階段 | 智慧流程裁剪：簡單任務自動跳過 inspiration/cross-review |
| Provider 選擇靜態 | 角色→Provider 映射固定 | Provider 能力評分：根據歷史表現動態路由（表現差的自動降權） |
| Instinct 無跨域遷移 | code-style instinct 不會影響 testing 或 architecture 決策 | 跨域 instinct 關聯分析：發現隱性模式連結 |

---

## 升級藍圖總覽

```
                    ┌─────────────────────────┐
                    │   DG Cell Core Engine    │
                    │  (新增統一基礎層)         │
                    └────────┬────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
   │  再生模組    │   │  增殖模組    │   │  進化模組    │
   │ Regeneration │   │ Multiply    │   │ Evolution   │
   ├─────────────┤   ├─────────────┤   ├─────────────┤
   │• 瞬態重試    │   │• Prompt 統一 │   │• Telemetry  │
   │• Checkpoint  │   │  Registry   │   │• 自適應閾值  │
   │• State 驗證  │   │• Review     │   │• Provider   │
   │• Timeout     │   │  Engine     │   │  動態路由    │
   │  Watchdog   │   │• Corrections│   │• 記憶衰減    │
   │• Health     │   │  Pool       │   │• 流程裁剪    │
   │  Pre-flight │   │• Scaffold   │   │• Instinct   │
   │             │   │  Generator  │   │  Cross-link │
   └─────────────┘   └─────────────┘   └─────────────┘
```

## 建議實作順序

1. **再生模組優先** — 它是其他兩者的基礎（系統不穩定，學習和擴散都無意義）
2. **增殖模組次之** — 建立共享機制後，進化的成果才能自動擴散
3. **進化模組最後** — 在穩定且共享的基礎上，加入智慧調適

## 現有體系盤點數據（2026-03-17）

- **Skills 總數**：31 個
- **Agents 總數**：5+ 個（laravel-simplifier, context-manager, frontend-developer, pragmatic-ui-architect, backend-architect）
- **AI Providers**：Claude (designer/executor), Gemini (inspiration), Codex (reviewer), Ollama (LAN coder), MLX (local reasoner)
- **狀態管理**：`.ccb/state.json` + `.dev-state.json` + `corrections.jsonl` + instincts
- **通訊協定**：Async Ask Pattern, FileOpsREQ/RES, Role-Based Routing

---

> 分析日期：2026-03-17
> 分析者：Claude Opus 4.6（軍機處大臣）
> 狀態：研究完成，待陛下裁示實作優先序
