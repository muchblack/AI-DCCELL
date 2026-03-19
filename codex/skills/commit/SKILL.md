---
name: commit
description: Create a git commit with proper message following project conventions
disable-model-invocation: true
argument-hint: "[-m message]"
---

# Git Commit 技能

建立一個結構良好的 git commit。

## 流程

### 步驟 1：檢視變更狀態

並行執行以下三個命令：

git status
git diff
git log --oneline -5

- git status：查看未追蹤與已修改的檔案（不使用 -uall）
- git diff：查看暫存與未暫存的變更內容
- git log --oneline -5：參考近期 commit 訊息風格

### 步驟 2：分析變更並草擬 commit message

根據變更內容，草擬 commit 訊息：

- 語言：繁體中文
- 格式：1-2 句，聚焦「為什麼」而非「什麼」
- 分類：準確反映變更性質（新增功能用「新增」、修正用「修正」、改善用「改善」等）
- 簡潔：不列舉每個檔案，描述整體變更目的

### 步驟 3：暫存檔案

- 優先使用 git add <具體檔案> 而非 git add -A
- 絕對不 commit 含有敏感資訊的檔案（.env, credentials, secrets）
- 若發現敏感檔案，警告使用者

### 步驟 4：執行 commit

使用 HEREDOC 格式確保訊息格式正確：

git commit -m "$(cat <<'EOF'
commit 訊息

Co-Authored-By: Codex <noreply@openai.com>
EOF
)"

### 步驟 5：驗證

執行 git status 確認 commit 成功。

## 引數處理

- /commit：自動分析變更並草擬訊息
- /commit -m "訊息"：使用指定的訊息，仍加上 Co-Authored-By

若 $ARGUMENTS 包含 -m，提取其後的訊息直接使用。否則執行完整分析流程。

## 安全規則

- 不 push：commit 後不自動推送到遠端
- 不 amend：永遠建立新 commit，不修改既有 commit
- Hook 失敗：pre-commit hook 失敗時，修復問題後建立新 commit（不使用 --amend，因為原 commit 未成功）
- 無變更不 commit：若沒有未追蹤或已修改的檔案，告知使用者無需 commit
- 不跳過 hook：不使用 --no-verify 或 --no-gpg-sign
- 不動 git config：不修改任何 git 設定
