# AI-DCCELL

> **多 AI 協作工作流的自進化基礎設施** — 會自我再生、自我增殖、自我進化的 Claude Code 體系。

以《機動武鬥傳G 鋼彈》惡魔鋼彈 **DG 細胞**的三大理論為隱喻框架，把 Claude Code 多 AI 協作工作流，打造成一套容錯可恢復、改進可擴散、行為可演化的工程基礎設施。

---

## 30 秒上手

```bash
git clone <repo-url> AI-DCCELL
cd AI-DCCELL
chmod +x bootstrap.sh
./bootstrap.sh
```

`bootstrap.sh` 會依序完成（共 4 個階段）：

1. **[1/4]** 建立 `~/.claude/` 下的 symlink（`CLAUDE.md`、`agents/`、`skills/`）
2. **[1b/4]** 部署 Codex 設定（`~/.codex/AGENTS.md`、`~/.codex/skills/`）
3. **[1c/4]** 部署 Gemini 設定（`~/.gemini/GEMINI.md`、`~/.gemini/skills/`）
4. **[2/4]** 設定 scripts 執行權限
5. **[3/4]** 初始化 memory 目錄（telemetry）
6. **[4/4]** 執行 health check，驗證 Gemini / Codex / provider 連線

### 外部 Skill（git submodule）

下列外部 skill 以 submodule 鎖定版本（放在 `vendor/`，再以 symlink 掛到 `claude/skills/`）：

| Skill | 上游 | submodule |
|---|---|---|
| `security-audit` | cloudflare/security-audit-skill | `vendor/security-audit-skill` |
| `open-seo-advisor` | mars-tw/open-seo-advisor-skill | `claude/skills/open-seo-advisor` |
| `ui-ux-pro-max`、`banner-design`、`brand`、`design`、`design-system`、`slides`、`ui-styling` | nextlevelbuilder/ui-ux-pro-max-skill | `vendor/ui-ux-pro-max-skill` |
| `find-skills` | vercel-labs/skills | `vendor/vercel-skills` |

`bootstrap.sh` 會自動初始化這些 submodule。已部署的機器 pull 之後補跑：

```bash
git pull && git submodule update --init
```

更新上游版本（會先顯示 diff、確認後跑檢查再 commit，不會自動 push）：

```bash
scripts/update-vendor.sh                  # 列出目前版本
scripts/update-vendor.sh security-audit
```

### 本地修補

以下外部 skill 直接複製進 `claude/skills/`（非 submodule），並加了本地修改。重新同步上游時會被覆蓋，同步後要補回：

| Skill | 上游 | 本地修改 | 日期 |
|---|---|---|---|
| `grill-with-docs` | mattpocock/skills | `SKILL.md` 末段：程式碼／文件事實標 `EXTRACTED: <path:line>` 或 `INFERRED: <why>`，只有 EXTRACTED 能寫進 CONTEXT.md／ADR（與 herdr-dev verdict 的 CRITICAL 須 EXTRACTED 成對） | 2026-10-12 |

找回原文：`git log -p -- claude/skills/<skill>`。

部署後可隨時用健康檢查確認 provider 狀態：

```bash
claude/skills/scripts/health-check.sh
```

---

## DG 細胞理論：神話與工程的對照

這套體系的核心是把鋼彈設定中的三大「生存本能」，落地成具體的腳本與工作流。**不是 vibe，是可執行的檔案。**

| DG 細胞理論 | 原始設定 | 工程實作 |
|------------|---------|---------|
| **自我再生** Regeneration | 核心未毀即可瞬間復原 | 健康檢查、指數退避重試、超時殺進程、狀態快照與修復 |
| **自我增殖** Multiplication | 感染後幾何級數擴散 | Skill 骨架生成、評分 rubric 單一來源 |
| **自我進化** Evolution | 依環境/對手自動進化 | 呼叫遙測、效能報告 |

### 自我再生（Regeneration）— 容錯與自動恢復

| 腳本 | 功能 |
|------|------|
| `scripts/health-check.sh` | Provider 健康檢查（秒級回傳 JSON 狀態） |
| `scripts/retry.sh` | 指數退避重試 + jitter |
| `scripts/watchdog.sh` | 超時殺進程（exit 124） |

搭配 `/herdr-dev --resume` 與 provider 降級鏈（→ Claude），中斷可從斷點續接。

### 自我增殖（Multiplication）— 知識共享與擴散

| 項目 | 功能 |
|------|------|
| `scripts/scaffold.sh` | Skill 骨架生成器（simple / intermediate / complex） |
| `linus-review/rubric.md` | 三級評分（🟢🟡🔴）的唯一定義來源 |

### 自我進化（Evolution）— 效能追蹤與智慧路由

| 項目 | 功能 |
|------|------|
| `scripts/telemetry.sh` | Skill 呼叫記錄（provider、耗時、結果、是否降級） |
| `scripts/telemetry-report.sh` | 效能報告（成功率、耗時、降級頻率） |

---

## 角色體系：軍機處與 Human-in-the-Loop

體系雖高度自動化，**最終否決權永遠在使用者（朕）手上**。各 AI 對應一個抽象角色，skill 只引用角色、不綁死 provider：

| 角色 | Provider | 職責 |
|------|----------|------|
| `designer` / `executor` | Claude | 規劃、架構、寫碼（軍機處大臣） |
| `inspiration` | Gemini | 創意發想（僅供參考，不盲從） |
| `reviewer` | Codex | 評分品質閘門；Codex 不可用時由 Claude 直接審查 |

**Peer Review 鐵律**：`designer` 在「寫碼前（Plan Review）」與「回報前（Code Review）」兩個檢查點，必須送 `reviewer` 評分（overall ≥ 7.0 且無單項 ≤ 3 才算通過）。

---

## 目錄結構

```
AI-DCCELL/
├── bootstrap.sh           # 一鍵部署（Claude + Codex + Gemini）
├── setup.sh               # Legacy 部署腳本
├── claude/
│   ├── CLAUDE.md          # 全域 Claude 指令（軍機處大臣角色）
│   ├── agents/            # 9 類、共 44 個 agent 定義
│   │   ├── engineering/   # 12      ├── marketing/          # 7
│   │   ├── studio-operations/ # 5   ├── design/             # 5
│   │   ├── testing/       # 5       ├── project-management/ # 3
│   │   ├── product/       # 3       ├── analysis/           # 2
│   │   └── bonus/         # 2
│   └── skills/            # 約 50 個 skill 定義
│       ├── scripts/       # 17 個共用基礎腳本（DG Cell Core）
│       ├── docs/          # 協定文件（smart-router 等）
│       ├── memory/        # 學習記憶（telemetry）
│       └── ...            # herdr-dev, linus-review,
│                          #   linus-analyze, tp, tr, magi, 命理三件套 等
├── codex/
│   ├── AGENTS.md          # Codex 角色與 Rubric 定義
│   └── skills/            # 16 個 Codex 端 skill
├── .gemini/
│   ├── GEMINI.md          # Gemini 角色定義
│   └── skills/            # 4 個 Gemini 端 skill
├── docs/                  # DG 細胞理論藍圖 + 實作紀錄
├── project-template/      # 新專案範本（CLAUDE.md）
└── sample.md              # 範例文件
```

---

## 體系數據

- **Skills**：約 50 個（涵蓋開發工作流、程式碼審查、命理三件套、影像生成、求職、股市分析等）
- **Agents**：9 類、共 44 個
- **基礎腳本**：17 個（`claude/skills/scripts/`）
- **AI Providers**：Claude、Gemini、Codex、opencode、droid
- **通訊協定**：Async Ask Pattern、FileOpsREQ/RES、Role-Based Routing、Linus 式 Peer Review

---

## 環境需求

- macOS（Apple Silicon 推薦）
- Python 3.10+
- Claude Code CLI

---

## 相關連結

- [DG 細胞理論藍圖](docs/DG%20細胞理論%20—%20AI%20工作流自進化升級藍圖.md) — 設計文件
- [DG 細胞理論實作紀錄](docs/DG%20細胞理論實作紀錄.md) — 三大模組開發過程
