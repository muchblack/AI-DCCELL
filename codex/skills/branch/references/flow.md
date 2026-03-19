# 從需求文件建立 Git 分支

## Input

```
$ARGUMENTS = <markdown-file> [--from <base-branch>]
```

- `markdown-file`（必填）：需求文件路徑（.md）
- `--from <base-branch>`（選填，預設 `main`）

---

## Execution Flow

### Step 1: 解析引數

1. 從 `$ARGUMENTS` 解析：
   - 提取 `--from <branch>` 旗標（若存在），其值為基底分支名稱
   - 剩餘部分為需求文件路徑
2. 若無引數或未提供檔案路徑：
   - 報錯：「用法：`/branch <markdown-file> [--from <base-branch>]`」
   - 中止執行

### Step 2: 讀取需求文件

1. 使用 Read 工具讀取指定的 Markdown 檔案
2. 若檔案不存在或無法讀取：
   - 報錯：「找不到需求文件：`{path}`」
   - 中止執行

### Step 3: 生成分支名稱

1. **提取前綴**：從文件內容中識別專案代碼或票號
   - 常見格式：`CMS123`、`PROJ-456`、`ABC-789`、`T001` 等
   - 搜尋模式：大寫字母開頭 + 數字組合（如 `[A-Z]+[-]?\d+`）
   - 若找到多個候選，選擇最先出現或最顯著的（標題、首段）
   - 若完全找不到前綴，直接使用功能名（不加前綴）

2. **生成功能名**：根據需求內容摘要
   - 提取核心功能描述，轉為簡潔的 kebab-case（2-4 個單詞）
   - 範例：`user-auth`、`topic-collection`、`payment-integration`

3. **組合分支名稱**：
   - 有前綴：`前綴_功能名`（如 `CMS123_user-auth`）
   - 無前綴：直接使用功能名（如 `user-auth`）

4. **使用者確認**：
   - 顯示生成的分支名稱
   - 向使用者確認或讓其修改
   - 若使用者提供替代名稱，採用使用者的版本

### Step 4: 飛行前檢查

並行執行以下 git 命令：

```bash
git rev-parse --is-inside-work-tree
git branch --list <branch-name>
git ls-remote --heads origin <branch-name>
git status --porcelain
git rev-parse --verify <base-branch>
```

根據結果處理：

| 檢查項                 | 失敗處理                                              |
| ---------------------- | ----------------------------------------------------- |
| 非 git 倉庫            | 報錯中止：「當前目錄不是 git 倉庫」                   |
| 分支已存在（本地）     | 詢問使用者是否切換至該分支（`git checkout <branch>`） |
| 分支僅存在遠端         | 詢問使用者是否 checkout 並追蹤遠端分支                |
| 工作區有未 commit 變更 | 警告使用者，建議先 `/commit` 或 stash，等待確認       |
| 基底分支不存在         | 報錯中止：「基底分支 `{base}` 不存在」，列出可用分支  |

### Step 5: 建立分支

```bash
git checkout -b <branch-name> <base-branch>
```

成功後報告：

```
已從 `{base-branch}` 建立並切換至分支 `{branch-name}`
```

---

## 安全規則

- **不推送**：建立分支後不推送至遠端，推送由使用者自行處理
- **不 force push**：絕對不使用 --force
- **不刪除分支**：此技能只建立分支，不刪除
- **不改 git config**：不更動任何 git 設定
- **髒工作區**：有未 commit 的變更時，警告使用者並等待確認
- **確認分支名**：分支名稱必須經使用者確認後才建立

---

## Error Handling

| 錯誤情境       | 處理方式             |
| -------------- | -------------------- |
| 無引數         | 顯示用法說明         |
| 檔案不存在     | 報錯中止             |
| 找不到前綴     | 僅用功能名，不加前綴 |
| 分支已存在     | 提議切換，不重複建立 |
| 基底分支不存在 | 列可用分支，中止     |
| 非 git 倉庫    | 報錯中止             |
