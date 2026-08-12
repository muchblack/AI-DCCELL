# CCB Config Templates

## minimal — 輕量探索型

適用：問答、內容生成、靜態站、非 git 專案、個人快速探索。

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "65%"
comms_height = "15%"
tips_height = "20%"
comms_limit = 3
```

特性：
- 只有 main window，單一 claude agent
- 無 worktree，無 review panel
- 資源佔用最小

---

## standard — 標準開發型（推薦預設）

適用：正式開發專案，需要平行 coding + codeReview 審查（`/ccb-dev` 的標準地形）。

### opencode worker 變體（實戰驗證配置）

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"
work = "worker1:codex(worktree), worker2:opencode(worktree)"
codeReview = "reviewer1:agy, reviewer2:codex"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "50%"
comms_height = "15%"
tips_height = "35%"
comms_limit = 3
```

### 無 opencode 變體

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"
work = "worker1:codex(worktree), worker2:agy(worktree)"
codeReview = "reviewer1:agy, reviewer2:codex"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "50%"
comms_height = "15%"
tips_height = "35%"
comms_limit = 3
```

特性：
- main：指揮中心（claude），負責分派、綜整、審查扇出
- work：多 worker + worktree，支援平行開發（實際組成依 Q&A Step 3b）
- codeReview：審查群組（實際組成依 Q&A Step 3C）；main 直接扇出派審每一位 reviewer
- **前提**：所列 provider 存在且健康

---

## inspect — 審查型（main + codeReview，無 work）

適用：程式碼審查、安全 audit、架構評估、PR review。需要多 AI 審查但不需要平行 coding。

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"
codeReview = "reviewer1:agy, reviewer2:codex"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "55%"
comms_height = "15%"
tips_height = "30%"
comms_limit = 3
```

特性：
- main：指揮中心（claude），扇出派審、綜整判決
- codeReview：審查群組（reviewer1:agy + reviewer2:codex）
- **無 work 視窗** — 不需要平行 coding workers
- **前提**：需要 agy 和 codex provider 存在且健康

---

## analysis — 分析視窗（可疊加於任何模板）

適用：需要深度分析、研究、規劃的專案，agy 擔任專職分析師，與 coding workers 職責分離。

### 疊加於 standard（最完整，= newmetalwork2 現役配置）

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"
work = "worker1:codex(worktree), worker2:opencode(worktree)"
codeReview = "reviewer1:agy, reviewer2:codex"
analysis = "analyst:agy"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "50%"
comms_height = "15%"
tips_height = "35%"
comms_limit = 3
```

### 疊加於 minimal（輕量 + 分析）

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"
analysis = "analyst:agy"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "60%"
comms_height = "15%"
tips_height = "25%"
comms_limit = 3
```

特性：
- `analyst:agy` 專責深度分析、文件研究、架構評估，不參與 coding
- analysis 視窗可疊加於任何現有模板，不干擾 work / review 視窗
- **前提**：需要 agy provider

---

## quad — 四主控台平行型

適用：需要同時直接對話多個 top-level agent（不分 worker/reviewer 角色），例如比較
不同 provider 對同一問題的回應，或個別獨立地在各自視窗使用 codex/opencode/agy，
而非透過 main 分派任務。

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"
codex = "codex:codex"
opencode = "opencode:opencode"
agy = "agy:agy"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "60%"
comms_height = "15%"
tips_height = "25%"
comms_limit = 3
```

特性：
- 四個視窗、四個 provider，各自獨立主控台，無 work/codeReview 階層區分
- 視窗名稱直接採用 provider 名稱，一眼對應
- 每個視窗互相看不到彼此對話，需靠 `/ask` 手動傳遞
- **前提**：需要 codex、opencode、agy 三個 provider 都存在且健康

---

## solo — 單機無 CCB provider

適用：只有 claude，其他 provider 不可用或不需要。

```toml
version = 2
entry_window = "main"

[windows]
main = "main:claude"
work = "worker1:claude(worktree), worker2:claude(worktree)"

[ui.sidebar]
mode = "every_window"
width = "15%"
bottom_height = 20

[ui.sidebar.view]
agents_height = "60%"
comms_height = "15%"
tips_height = "25%"
comms_limit = 3
```

特性：
- 全部 claude，無外部 provider 依賴
- worktree 仍可用（需 git repo）
- 適合 codex/agy 離線時的降級方案

---

## Provider 可選清單

| Provider | 說明 | worktree 支援 |
|----------|------|--------------|
| `claude` | 本地 claude，永遠可用 | ✅ |
| `codex` | OpenAI Codex（需 CCB 掛載） | ✅ |
| `agy` | Agy agent（需 CCB 掛載） | ✅ |
| `gemini` | Google Gemini（需 CCB 掛載） | ✅ |
| `opencode` | OpenCode（需 CCB 掛載） | ✅ |
| `llama` | 本地 llama.cpp（需本機有 llama-server，port 8080） | ❌ |
| `mlx` | 本地 MLX（需本機有 MLX 服務） | ❌ |
| `ollama` | LAN Ollama（需區網有 Ollama） | ❌ |

---

## Config 欄位說明

### `[windows]`
每個 key 是視窗名稱，value 是逗號分隔的 `agent:provider` 清單。
- `(worktree)` 後綴：讓該 agent 在獨立 git worktree 工作，避免互相干擾
- 同一視窗多個 agent 會並列顯示

### `[ui.sidebar]`
| 欄位 | 說明 |
|------|------|
| `mode` | `every_window`（每個視窗都顯示）或 `main_only` |
| `width` | sidebar 寬度（百分比或像素） |
| `bottom_height` | 底部區塊高度（列數） |

### `[ui.sidebar.view]`
| 欄位 | 說明 |
|------|------|
| `agents_height` | agents 列表佔 sidebar 的比例 |
| `comms_height` | 通訊記錄區比例 |
| `tips_height` | 提示區比例 |
| `comms_limit` | 通訊記錄顯示條數上限 |
