# Git Clone

## Input

```
$ARGUMENTS = [ssh-host:repo-path] [target-path]
```

所有參數皆為選填，未提供的會互動詢問使用者。

- `ssh-host`：`~/.ssh/config` 中的 Host 名稱
- `repo-path`：遠端 repo 路徑（如 `group/project.git`）
- `target-path`：clone 目標的完整路徑（如 `~/code/php`、`~/projects/my-app`）

---

## Execution Flow

### Step 1: 收集參數（解析 + 問答補齊）

1. 嘗試從 `$ARGUMENTS` 解析已提供的參數：
   - 若含 `:` 的段落 → 以第一個 `:` 分隔為 `ssh-host` 和 `repo-path`
   - 剩餘段落 → `target-path`

2. 讀取 `~/.ssh/config`，提取所有 Host 名稱備用

3. **補齊缺少的參數**（依序，每次詢問使用者）：

   **若缺 ssh-host**：
   - 列出所有可用 SSH hosts
   - 問：「請選擇 SSH host：」

   **若缺 repo-path**：
   - 問：「請輸入 repo 路徑（如 `group/project.git`）：」

   **若缺 target-path**：
   - 列出常用目錄（`ls ~/code/` 的子目錄）
   - 問：「請指定 clone 目標路徑（如 `~/code/php`）：」

### Step 2: 推導最終路徑

1. 展開 `target-path` 中的 `~`
2. 判斷 `target-path` 的意義：
   - 若是已存在的目錄 → 從 `repo-path` 推導 repo 名（去 `.git` 後綴），最終路徑為 `<target-path>/<repo-name>`
   - 若不存在但父目錄存在 → 直接使用 `target-path`
3. 從 repo-path 推導 repo 名的規則：
   - `group/project.git` → `project`
   - `vincent/my-app` → `my-app`

### Step 3: 驗證

並行執行以下檢查：

1. **SSH Host 驗證**：確認 `ssh-host` 存在於 `~/.ssh/config`
2. **父目錄驗證**：確認最終路徑的父目錄存在
3. **衝突檢查**：確認最終 clone 目標路徑不存在

| 檢查項 | 失敗處理 |
|--------|---------|
| SSH host 不存在 | 列出所有可用 SSH hosts，中止 |
| 父目錄不存在 | 報錯：「父目錄 `{parent}` 不存在」，中止 |
| 目標路徑已存在 | 報錯：「`{target}` 已存在」，中止 |

### Step 4: 確認並執行

1. 組合完整 clone 命令：
   ```
   git clone <ssh-host>:<repo-path> <final-target-path>
   ```

2. 向使用者顯示即將執行的命令，等待使用者確認

3. 使用者確認後，執行 `git clone`

### Step 5: 報告結果

成功後報告：
```
已將 <ssh-host>:<repo-path> clone 至 <final-target-path>
```

---

## 安全規則

- **確認命令**：clone 前必須經使用者確認完整命令
- **不覆蓋**：目標路徑已存在時直接中止，不覆蓋
- **不改配置**：不修改 SSH config 或 git config
- **僅 clone**：此技能只做 clone，不做 push、pull 或其他 git 操作

---

## Error Handling

| 錯誤情境 | 處理方式 |
|----------|---------|
| SSH host 不存在 | 列出可用 hosts，中止 |
| 父目錄不存在 | 報錯中止 |
| 目標路徑已存在 | 報錯中止 |
| clone 失敗 | 顯示 git 錯誤訊息 |
