---
name: worklog
description: 手動寫入或查看 Obsidian 工作日誌（按專案分資料夾）。Use when user wants to manually add a work log entry or review today's log.
argument-hint: "[view | add <內容> | week]"
---

# 工作日誌技能

手動操作 Obsidian 工作日誌（自動記錄由 PostToolUse hook 處理）。

## 日誌位置

按專案資料夾分開，每個專案獨立目錄：

```
$OBSIDIAN_VAULT/myWiki/20-領域/工作日誌/YYYY/<專案名稱>/YYYY-MM-DD.md
```

專案名稱取自當前工作目錄的 basename（如 `podman`、`集點系統`）。
環境變數 `OBSIDIAN_VAULT` 未設定時，fallback 為 `~/Obsidian`。

## 子命令

### `/worklog` 或 `/worklog view` — 查看今日日誌

1. 取得 `OBSIDIAN_VAULT`（fallback `~/Obsidian`）、今日日期、當前專案名稱（basename of cwd）
2. 讀取 `$VAULT/myWiki/20-領域/工作日誌/YYYY/<專案名稱>/YYYY-MM-DD.md`
3. 若檔案不存在，建立目錄與檔案（含 frontmatter 標頭與標題），然後顯示已建立的空白日誌
4. 若存在，顯示完整內容

### `/worklog add <內容>` — 手動追加記錄

1. 取得今日日期、當前時間、專案名稱
2. 確認日誌檔案路徑，不存在則建立目錄與檔案（含 frontmatter 標頭）
3. 追加格式：

```markdown
## HH:MM — 手動記錄
<內容>
```

4. 回報寫入成功

### `/worklog week` — 查看本週日誌摘要

1. 計算本週一至今日的日期範圍
2. 掃描 `$VAULT/myWiki/20-領域/工作日誌/YYYY/` 下所有專案子目錄
3. 依序讀取每日每專案的日誌檔案
4. 彙整為摘要表格：

```markdown
| 日期 | 專案 | commit 數 | 摘要 |
|------|------|----------|------|
```

## 日誌檔案格式

```markdown
---
date: YYYY-MM-DD
type: worklog
---

# YYYY-MM-DD 工作日誌

## HH:MM [`hash`]
commit message（自動由 hook 寫入）

## HH:MM — 手動記錄
自由文字內容（由 /worklog add 寫入）
```

## 自動記錄（Hook）

commit 後的自動記錄由 `~/.claude/hooks/worklog.sh` 處理（PostToolUse hook），本 skill 僅負責手動操作與查閱。

## 引數處理

- `/worklog` 或 `/worklog view`：查看今日日誌（當前專案）
- `/worklog add <內容>`：手動追加（當前專案）
- `/worklog week`：本週全專案摘要

若 $ARGUMENTS 為空或 `view`，執行查看。若以 `add` 開頭，提取後續文字追加。若為 `week`，執行週摘要。
