---
category: 資源/技術
created: 2026-03-17
tags: [ai-workflow, self-evolution, implementation, claude-code, ccb, dg-cell]
---

# DG 細胞理論實作紀錄

> 基於《DG 細胞理論 — AI 工作流自進化升級藍圖》，於 2026-03-17 一次完成三大模組的實作。

## 背景

Claude Code + CCB 多 AI 協作工作流體系已有 31 個 skills、5+ agents、5 個 AI providers。以惡魔鋼彈 DG 細胞的三大理論作為框架，對體系進行系統性升級：再生 → 增殖 → 進化。

## 一、自我再生（DG-Cell-Regeneration）

### 目標
為 AI 多 Agent 工作流建立統一的容錯與自動恢復基礎層。

### 交付物

| 腳本 | 功能 | 驗收結果 |
|------|------|---------|
| `health-check.sh` | Provider 健康檢查（MLX/Ollama/Gemini/Codex） | 2.1 秒全量檢查，含 model loaded 偵測 |
| `retry.sh` | 指數退避重試 + jitter | 3 次退避 (1.4s → 2.7s)，exhaustion exit 124 |
| `watchdog.sh` | 超時殺進程 | SIGTERM → SIGKILL，exit 124 |
| `validate-state.sh` | state.json 結構驗證 + 自動修復 | 缺欄位補齊、孤兒 cursor 修復、checkpoint FIFO 10 份 |

### 協定文件
- `docs/resilience-state.md` — 統一容錯協定，含 fallback 決策樹

### 整合點
- `/tr` — Step 0.5 resilience pre-flight
- `/ollama-code`, `/mlx-code`, `/mlx-reason`, `/linus-analyze` — Step 0 health check

### 技術決策
- macOS 無 `timeout` 指令 → 用背景進程 + kill 替代（`_run_with_timeout`）
- validate-state 用 Python 實作（jq 做不好複雜修復邏輯）
- 環境變數傳遞給 Python heredoc 需 `export` 才能在 `<< 'EOF'` 中讀取

---

## 二、自我增殖（DG-Cell-Multiplication）

### 目標
建立跨 skill 知識共享與自動擴散機制。

### 交付物

| 項目 | 說明 |
|------|------|
| `linus-review/rubric.md` | 3-tier 評分唯一定義（原 4 份副本改為引用） |
| `memory/schema.md` | 統一 corrections schema（含 project_type/language/framework） |
| `memory/corrections.jsonl` | 全域 corrections pool（3 筆 legacy 資料已 migrate） |
| `scripts/prune-corrections.sh` | 剪枝腳本：FIFO 100 上限 + critical 永久保留 + 90 天 minor 過期 |
| `scripts/scaffold.sh` | Skill 骨架生成器：Simple / Intermediate / Complex 三種 tier |
| MCP Bridge `prompts.ts` | `loadTemplate(action, provider)` 支援 per-provider key 查找 |

### Gemini Cross-Review 結果
審查發現兩個 Critical：
1. **Context Contamination** — 全域 corrections 需加 metadata 篩選 → 已修正，加入 `project_type`/`language`/`framework`
2. **Atomic Write** — prompts.json 物理 race condition → 已修正，改為 per-provider key（`ollama_code`/`mlx_code`）

### 整合點
- `/mlx-code`, `/ollama-code` — Step 4.5 corrections 自動回饋
- `/dev` — corrections 路徑改為全域 `~/.claude/skills/memory/corrections.jsonl`
- Linus review 4 份副本 → 統一引用 `rubric.md`

---

## 三、自我進化（DG-Cell-Evolution）

### 目標
為 AI 工作流加入效能追蹤與智慧裁剪，實現自適應進化基礎。

### 交付物

| 項目 | 說明 |
|------|------|
| `scripts/telemetry.sh` | Telemetry logger：`record` 記錄 + `query` 查詢 |
| `scripts/telemetry-report.sh` | Dashboard：per-skill / per-provider 成功率、平均耗時、降級頻率 |
| `docs/complexity-classifier.md` | 任務複雜度分類規則（simple/medium/complex） |

### 複雜度裁剪規則

| 等級 | 跳過的 Phase |
|------|-------------|
| simple | Phase 3 (plan cross-review) + Phase 7 (code cross-review) |
| medium | Phase 3 (plan cross-review) |
| complex | 不跳過 |

使用者可加 `--full-review` 強制走完整流程。

### 暫緩項目（待數據累積）
- 自適應閾值（根據歷史通過率動態調整）
- Provider 動態路由（根據歷史表現降權/升權）
- Instinct 跨域遷移（instinct 數量不足以分析）

---

## 總覽

```
┌─────────────────────────┐
│   DG Cell Core Engine    │
│  (統一基礎層 — 已完成)    │
└────────┬────────────────┘
         │
  ┌──────┼──────────────────┐
  │      │                  │
┌─▼────┐ ┌▼─────┐ ┌────────▼┐
│ 再生  │ │ 增殖  │ │  進化    │
│  ✅   │ │  ✅   │ │   ✅    │
└──────┘ └──────┘ └─────────┘
```

### 數量統計

| 類別 | 數量 |
|------|------|
| 新建腳本 | 8 |
| 新建協定/規則文件 | 4 |
| 修改的 Skill | 6（mlx-code, ollama-code, dev, mlx-reason, linus-analyze, tr） |
| MCP Bridge 改動 | 2 檔案（prompts.ts, router.ts） |
| 備份位置 | `~/podman/DCCell/` |

### 受影響 Skill 一覽

| Skill | 再生 | 增殖 | 進化 |
|-------|------|------|------|
| `/dev` | — | corrections 路徑 + rubric 引用 | complexity + trimming |
| `/mlx-code` | health check | rubric 引用 + corrections 回饋 | telemetry |
| `/ollama-code` | health check | rubric 引用 + corrections 回饋 | telemetry |
| `/mlx-reason` | health check | — | — |
| `/linus-analyze` | health check | — | — |
| `/tr` | validate-state pre-flight | — | — |

---

## 後續演進方向

1. **自適應閾值** — telemetry 數據累積 50+ 筆後，可分析歷史通過率動態調整 Rubric 通過分
2. **Provider 動態路由** — 根據 telemetry 的 provider 成功率/耗時自動降權表現差的 provider
3. **Instinct 跨域遷移** — 待 instinct 數量足夠後，分析 code-style 與 testing 領域的隱性關聯

---

> 實作日期：2026-03-17
> 實作者：Claude Opus 4.6（軍機處大臣）
> 總耗時：單一 session 完成三大模組
> 關聯文件：[[DG 細胞理論 — AI 工作流自進化升級藍圖]]
