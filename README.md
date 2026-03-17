# AI-DCCELL

> DG 細胞理論 — AI 工作流自進化升級體系

基於《機動武鬥傳G 鋼彈》惡魔鋼彈 DG 細胞的三大理論，為 Claude Code + CCB 多 AI 協作工作流建立的自我再生、自我增殖、自我進化基礎設施。

## 快速開始

```bash
git clone <repo-url> AI-DCCELL
cd AI-DCCELL
chmod +x bootstrap.sh
./bootstrap.sh
```

Bootstrap 會自動：
1. 建立 `~/.claude/` 下的 symlink（agents, skills, CLAUDE.md）
2. 設定腳本執行權限
3. 初始化 memory 目錄
4. 驗證 MLX / Ollama 環境

## 目錄結構

```
AI-DCCELL/
├── bootstrap.sh          # 一鍵部署腳本
├── setup.sh              # Legacy 部署腳本
├── claude/
│   ├── CLAUDE.md          # 全域 Claude 指令（軍機處大臣角色）
│   ├── agents/            # Agent 定義（.md）
│   │   ├── engineering/   # 工程類 agent
│   │   ├── design/        # 設計類 agent
│   │   └── testing/       # 測試類 agent
│   └── skills/            # Skill 定義
│       ├── scripts/       # 共用基礎腳本（DG Cell Core）
│       ├── docs/          # 協定文件
│       ├── memory/        # 學習記憶（corrections, telemetry）
│       ├── dev/           # 端對端開發工作流
│       ├── mlx-code/      # MLX 寫碼 + 審查
│       ├── ollama-code/   # Ollama 寫碼 + 審查
│       ├── linus-review/  # Linus 風格程式碼品味審查
│       ├── linus-analyze/ # 五層需求分析
│       └── ...            # 其他 30+ skills
├── project-template/      # 新專案範本
└── sample.md              # 範例文件
```

## DG 細胞三大模組

### 自我再生（Regeneration）

系統容錯與自動恢復。

| 腳本 | 功能 |
|------|------|
| `health-check.sh` | Provider 健康檢查（3 秒內回傳 JSON） |
| `retry.sh` | 指數退避重試 + jitter |
| `watchdog.sh` | 超時殺進程（exit 124） |
| `validate-state.sh` | state.json 驗證 + 自動修復 + checkpoint |

### 自我增殖（Multiplication）

知識共享與自動擴散。

| 項目 | 功能 |
|------|------|
| `linus-review/rubric.md` | 3-tier 評分唯一定義 |
| `memory/corrections.jsonl` | 統一 corrections pool（含 metadata 篩選） |
| `prune-corrections.sh` | 剪枝（FIFO 100 + critical 永久 + 90 天 minor 過期） |
| `scaffold.sh` | Skill 骨架生成器（simple/intermediate/complex） |
| MCP Bridge per-provider key | prompts.json 隔離（避免 race condition） |

### 自我進化（Evolution）

效能追蹤與智慧裁剪。

| 項目 | 功能 |
|------|------|
| `telemetry.sh` | Skill 呼叫記錄（provider, duration, result, fallback） |
| `telemetry-report.sh` | 效能報告（成功率、耗時、降級頻率） |
| `complexity-classifier.md` | 任務複雜度分類（simple/medium/complex） |
| Smart Trimming | 簡單任務自動跳過 cross-review |

## 體系數據

- **Skills**: 35+
- **Agents**: 5+ categories
- **AI Providers**: Claude, Gemini, Codex, Ollama (LAN), MLX (local)
- **通訊協定**: Async Ask Pattern, FileOpsREQ/RES, Role-Based Routing

## 環境需求

- macOS（Apple Silicon 推薦）
- Python 3.10+
- Claude Code CLI
- 選配：MLX Server (localhost:8090)、Ollama (LAN)、CCB 基礎設施

## 相關連結

- [DG 細胞理論藍圖](docs/DG%20細胞理論%20—%20AI%20工作流自進化升級藍圖.md) — 設計文件
- [DG 細胞理論實作紀錄](docs/DG%20細胞理論實作紀錄.md) — 三大模組開發過程
- [MCP AI Bridge](https://github.com/muchblack/mcp-ai-bridge) — 多 AI Provider 橋接層
- [Claude Code Bridge (CCB)](https://github.com/bfly123/claude_code_bridge) — 多 AI 協作通訊基礎設施
