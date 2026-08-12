# CCB Init — Config Flow

Q&A-driven config generation. After Step 9 (config written), execution
continues to the Keychain Fix step (unless `--skip-keychain` was passed).

AskUserQuestion hard limit: **max 4 options per question** — every question
below is designed within that budget; keep it that way when editing.

## Input

From `$ARGUMENTS`:
- `--template <name>` → skip Q&A, apply template directly
- `--skip-config` → skip config step entirely, go straight to Keychain Fix
- `--skip-keychain` → skip keychain step after config is written

---

## Step 1: Detect Existing Config

Check if `.ccb/ccb.config` exists:

```bash
cat .ccb/ccb.config 2>/dev/null
```

- **Found** → **必須**先用 AskUserQuestion 問過使用者，不可因為「config 已存在」就直接跳到
  Keychain Fix。選項：
  - A) 用問答重新設定（清除現有）
  - B) 直接編輯現有設定
  - C) 跳過 config，只修 Keychain
- **Not found** → go to Step 2

If `--skip-config` flag → skip to Keychain Fix.
If `--template <name>` → skip to Step 6.

---

## Step 2: Q&A — 需要哪些視窗？

用 AskUserQuestion（multiSelect: true）問：

> 這個專案需要哪些 CCB 視窗能力？（可多選）

選項（恰好 4 個，勿再增）：
- **平行 coding workers** — 多個 AI 同時在獨立 worktree 寫程式碼（`work` 視窗）
- **codeReview 審查** — 多 AI 程式碼審查群組，由 main 扇出派審（`codeReview` 視窗，`/ccb-dev` 依賴此視窗）
- **analysis 分析視窗** — agy 擔任深度分析、研究、規劃，與 coding 分離
- **都不需要，只要主控台** — 只有 main:claude 一個視窗

> **analysis 是獨立疊加視窗，不參與 Step 4 模板推導**：有勾選就在 `[windows]`
> 額外加一行 `analysis = "analyst:agy"`（前提：agy provider 可用，見 Step 3）。
> 過去曾把 analysis 塞進組合表導致漏加——維持獨立處理。

---

## Step 3: Q&A — Provider 可用性

如果選了 workers 或 codeReview，用 AskUserQuestion（multiSelect: true）問：

> 除了 claude（永遠可用）之外，目前哪些 CCB provider 可以使用？（可多選；都不勾 = 只有 claude）

選項：
- codex
- agy
- opencode
- gemini

一個都沒勾（只有 claude）→ 推導 `solo` 模板，跳過 Step 3b/3C。

---

## Step 3b: Q&A — Worker 組成（有選 workers 且非 solo 時執行）

用 AskUserQuestion（multiSelect: true）問：

> work 視窗要加入哪些 provider 的 worker？

選項由 Step 3 選出的可用 provider 動態生成（排除 claude，claude 固定在 main）。
每個選項格式：`<provider>（worker N）`，依序編號。

範例（全部可用時）：
- codex（worker1）
- agy（worker2）
- opencode（worker3）

用戶勾選哪些，work window 就放哪些，依序命名為 worker1、worker2、worker3…。
未勾選的 provider 不出現在 work 視窗。

---

## Step 3C: Q&A — CodeReview 組成（有選 codeReview 且非 solo 時執行）

用 AskUserQuestion（multiSelect: true）問：

> codeReview 視窗要加入哪些 provider 的 worker？

選項由 Step 3 選出的可用 provider 動態生成（排除 claude，claude 固定在 main）。
每個選項格式：`<provider>（worker N）`，依序編號。

範例（全部可用時）：
- codex（reviewer1）
- agy（reviewer2）
- opencode（reviewer3）

用戶勾選哪些，codeReview window 就放哪些，依序命名為 reviewer1、reviewer2、reviewer3…。
未勾選的 provider 不出現在 codeReview 視窗。
worker 與 reviewer 可用同一 provider（例如 codex 同時當 worker1 與 reviewer2）。

---

## Step 4: 推導最終模板（唯一一張表）

| coding workers | codeReview | 模板 |
|:-:|:-:|------|
| ❌ | ❌ | `minimal` |
| ❌ | ✅ | `inspect`（main + codeReview） |
| ✅ | ❌ | `standard` 去掉 codeReview，worker 依 3b |
| ✅ | ✅ | `standard`（work + codeReview），worker 依 3b、reviewer 依 3C |
| ✅（只有 claude） | 任意 | `solo` |

推導完模板後，**再檢查 Step 2 是否勾選了 analysis**：有勾 → 在最終 config 的
`[windows]` 加一行 `analysis = "analyst:agy"`，跟上面模板判斷完全獨立、不互相影響。

---

## Step 5: Edit Mode（已有 config 時選 B）

Show current config. Ask what to change:
- A) 新增/移除 window
- B) 修改某 window 的 agents/providers
- C) 調整 sidebar 比例
- D) 完整重新跑問答流程

完成後跳至 Step 7。

---

## Step 6: Apply Template（--template 直接指定時）

Load from `references/templates.md`. If `standard` or `inspect`: warn:
> ⚠️ 此模板預設用到 codex 和 agy provider，若 provider 不可用，對應視窗將啟動失敗。
> `standard` 的 opencode worker 變體另需 opencode provider。
> analysis window 需要 agy provider。

If `quad`: warn:
> ⚠️ 此模板需要 codex、opencode、agy 三個 provider 都存在且健康，任一不可用則對應視窗啟動失敗。

Ask for confirmation, then go to Step 7.

---

## Step 7: 生成並確認 Config

先算出 Step 7b 的過期 agent 目錄清單，一併顯示給用戶確認後才寫入：

```
以下是即將寫入的 .ccb/ccb.config：

[config 內容]

以下 .ccb/agents/ 目錄不在新 config 名單內，將一併刪除：
  - claude/（舊版無 window 命名時期殘留）
  - agy/
  （若無過期目錄則省略此段）

確認寫入？（Y / 修改 / 取消）
```

---

## Step 7b: 清除過期 Agent 目錄

`.ccb/agents/<name>/` 是 CCB 依 `[windows]` 裡的 agent 名稱建立的隔離 HOME
（Keychain symlink、auth.json 等）。當新 config 換了一批 agent 名稱（例如從
單純的 `claude/agy/codex` 換成 `worker1/worker2/reviewer1/reviewer2/analyst`），
舊名稱的目錄不會被 CCB 自動清掉，會變成孤兒垃圾殘留舊的認證狀態，且會讓
Keychain Fix 之後去修一個新 config 根本不會用到的 agent。

**寫入新 config 前，比對新 config 的 `[windows]` 定義出的 agent 名稱集合，
把 `.ccb/agents/` 底下不在這個集合裡的目錄整個刪除。**

判斷邏輯（從 `[windows]` 每個 value 依逗號切開，取 `:` 前面的字串即 agent 名稱）：

```bash
python3 - <<'PYEOF'
import pathlib, re

config_path = pathlib.Path(".ccb/ccb.config")
agents_dir = pathlib.Path(".ccb/agents")

text = config_path.read_text() if config_path.exists() else ""
names = set()
in_windows = False
for line in text.splitlines():
    line = line.strip()
    if line.startswith("["):
        in_windows = (line == "[windows]")
        continue
    if not in_windows or "=" not in line:
        continue
    _, value = line.split("=", 1)
    value = value.strip().strip('"')
    for entry in value.split(","):
        name = entry.strip().split(":")[0].strip()
        if name:
            names.add(name)

if agents_dir.is_dir():
    for d in sorted(agents_dir.iterdir()):
        if d.is_dir() and d.name not in names:
            print(d)
PYEOF
```

這段只是拿來**算出清單**（給 Step 7 顯示、讓用戶確認）；真正的刪除動作放在
Step 8，確認過後才執行 `rm -rf`。

- 只有 Step 1 選 A（重新設定）或全新建立（原本沒有 config）時才需要跑這個比對。
- Step 5 Edit Mode（僅調整 sidebar 比例、小幅修改）通常 agent 名稱集合不變，
  比對結果會是空清單，不會誤刪還在用的 agent。
- `.ccb/agents/` 不存在（尚未跑過 CCB）→ 沒有東西可清，略過。

---

## Step 8: Write Config

先刪除 Step 7b 算出的過期 agent 目錄（若 Step 7 用戶已確認）：

```bash
mkdir -p .ccb
# 對 Step 7b 列出的每個過期目錄執行：
rm -rf .ccb/agents/<stale-name>
```

再 Write `.ccb/ccb.config` using Write tool。

---

## Step 9: Report Config

```
✅ .ccb/ccb.config 已寫入
🗑  已清除過期 agent 目錄：claude/, agy/
```

（第二行僅在 Step 7b 有清單時出現）

→ 繼續執行 Keychain Fix（除非 `--skip-keychain`）。

---

## Principles

1. 問答推導，而非直接選模板
2. 一次一問（AskUserQuestion 每次只問一件事）
3. 顯示再確認，用戶確認後才寫入
4. provider 警告必做（涉及 codex/agy 時）
5. 不改 CCB 源碼
6. 寫新 config 前清掉不在新名單內的過期 agent 目錄，避免殘留舊 Keychain/auth 狀態誤導後續修復
