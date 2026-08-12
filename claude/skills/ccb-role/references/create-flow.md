# CCB Role — Create Flow

## 輸入解析

從 `$ARGUMENTS` 讀取：
- `create` → 進入完整 Q&A 流程
- `create --template <name>` → 跳過 Q&A，直接套用模板，從 Step 5 開始

---

## Step 1：Role 身份

用 AskUserQuestion 問：

> 這個 Role 的命名空間是什麼？

選項：
- **localroles**（Recommended）— 本地私有，不發布到 catalog
- **myroles** — 個人跨機器使用
- 自訂（Other）

接著問 Role 名稱（kebab-case，如 `code-reviewer`、`data-analyst`）。

組合為 `<namespace>.<name>`，例如 `localroles.code-reviewer`。

---

## Step 2：Role 用途

用 AskUserQuestion 問：

> 這個 Role 的主要能力是什麼？

選項（自訂 purpose 走內建 Other，勿另列選項）：
- **程式碼審查（code review）** — 審查 diff、品質、風險
- **協調者（coordinator）** — 接任務後 dispatch 給其他 agent，彙整結果
- **分析師（analyst）** — 深度研究、文件分析、架構評估

---

## Step 3：Coordinator 模式（選了「協調者」時執行）

> ⚠️ 先告知使用者：coordinator 綁 agy 實測會假轉派（只敘述不執行），
> 建議綁 claude provider。模板 memory.md 內建「轉派必附 job id 回執」鐵律。

用 AskUserQuestion 問：

> 協調者要 dispatch 給哪個 agent？

讀取 `.ccb/agents/*/agent.json` 列出現有 agent 名稱供選擇（Other 可自訂）。

再問 dispatch 模式：

> 需要等待 target agent 回傳結果後再彙整，還是 fire-and-forget？

選項：
- **等待彙整（--callback）**（Recommended）— 等 target 回來後合併兩份結果一起回覆
- **Fire-and-forget（--silence）** — 自己先回，target 在背景跑，結果各自呈現

---

## Step 4：Provider 與綁定

用 AskUserQuestion 問：

> 這個 Role 要綁定到哪個 agent？

讀取 `.ccb/agents/*/agent.json` 列出現有 agent 名稱供選擇（Other 可自訂新名稱）。

再問 provider（從被選 agent 的 `agent.json` 自動取得，若未存在則問）：
- claude
- codex
- agy
- opencode

---

## Step 5：推導並預覽生成檔案

依據 Step 1-4 的輸入，從 `references/role-templates.md` 取對應模板，
插入實際值（id、name、purpose、target agent、dispatch mode）。

顯示三個檔案的完整預覽：
1. `role.toml`
2. `memory.md`
3. `adapters/ccb/adapter.toml`

問確認：
- A) 確認，寫入並綁定
- B) 修改某欄位（重問對應步驟）
- C) 取消

---

## Step 6：寫入 Role 檔案

```bash
ROLE_DIR="$HOME/.roles/installed/<namespace>.<name>/current"
mkdir -p "$ROLE_DIR/adapters/ccb"
```

用 Write 工具寫入：
- `$ROLE_DIR/role.toml`
- `$ROLE_DIR/memory.md`
- `$ROLE_DIR/adapters/ccb/adapter.toml`

輸出：`✅ Role 檔案已寫入 ~/.roles/installed/<id>/current/`

---

## Step 7：綁定到 Agent

⚠️ `ccb roles add <role-id>:<provider>` 使用 adapter.toml 的 `default_agent_name`
自動推導 agent 名稱，**無法直接指定任意 agent name**。
若 default_agent_name 與現有 agent 不符，會產生錯誤或錯誤綁定。

**推薦做法：直接寫入 `ccb.config` 的 `[agents.<name>]` 段落**：

```toml
# 在 .ccb/ccb.config 末尾追加
[agents.<agent-name>]
role = "<role-id>"
```

這是最直接、最可控的綁定方式，不依賴 CCB daemon 在執行中。

`ccb roles add` 適用於：role 的 `default_agent_name` 剛好等於要綁定的 agent 名稱時。

輸出：
```
✅ Role <role-id> 已綁定到 <agent>（ccb.config [agents] 段落）
   執行 ccb reload 或 ccb -n 讓 CCB 重建 runtime 後生效
```

---

## 其他指令實作

### list

```bash
ccb roles list 2>&1
```

補充顯示 `~/.roles/installed/localroles.*` 下的本地 role，
標示哪些已綁定到 `.ccb/agents/*/agent.json`（role 欄位非 null）。

### bind <role-id> <agent>:<provider>

若 role 的 `default_agent_name` 剛好等於目標 agent → `ccb roles add <role-id>:<provider>`。
否則（或指令失敗）→ 寫入 `.ccb/ccb.config` 的 `[agents.<name>]` 段落（同 Step 7）。
不要直接改 agent.json——那是 runtime 產物，CCB 重建時會被覆蓋。

### show <role-id>

讀取並顯示：
- `~/.roles/installed/<role-id>/current/role.toml`
- `~/.roles/installed/<role-id>/current/memory.md`

### remove <role-id>

確認後執行：
```bash
rm -rf ~/.roles/installed/<role-id>
```

並移除 `.ccb/ccb.config` 中所有 `role = "<role-id>"` 的綁定行
（`[agents.<name>]` 段落）；agent.json 由 CCB 重建 runtime 時自然跟上。

---

## 注意

- Role 路徑必須用真實 `$HOME`（`/Users/$(id -un)`），不可用 CCB session 內的 `$HOME`。
- `ccb roles add` 需要 CCB daemon 在執行中；若不在，改用直接寫 agent.json。
- Role 寫入後需 `ccb -n` 讓 CCB 重建 runtime 才會 projection 到 agent 的隔離 HOME。
- `memory.md` 是 role 的核心行為，修改後需 `ccb -n` 才生效。
