# 專案指引

## 可用角色與技能

### 預設角色 — 清朝軍機處大臣（全域 CLAUDE.md 定義）
適用於：核心邏輯、資料結構、系統架構、程式碼品質分析

| 技能 | 說明 |
|------|------|
| `/linus-analyze` | 五層 Linus 式需求分析 + 決策輸出 |
| `/linus-review` | 程式碼品味三層評分（🟢🟡🔴） |
| `/all-plan` | 協作式規劃（designer + inspiration + reviewer） |
| `/review` | 正式雙審查（Claude + Cross-reviewer） |
| `/tp` | 建立任務計畫 |
| `/tr` | 執行 AutoFlow 步驟 |

### 前端開發
| Agent / Skill | 說明 |
|---------------|------|
| `/react-best-practices` | React/Next.js 效能優化 40+ 規則 |

### 開發流程
| Skill | 說明 |
|-------|------|
| `/herdr-dev` | 需求驅動開發：worker TDD → reviewer 審查；依任務類型帶入 `task-checks.md` 檢查項 |

### 協作
| Skill | 說明 |
|-------|------|
| `/ask <provider>` | 委派任務給 AI（gemini/codex/opencode/droid） |
| `/cping <provider>` | 測試 AI provider 連線 |
| `/pend <provider>` | 查看最新回覆 |
| `/file-op` | 委派 Codex 進行檔案操作 |
