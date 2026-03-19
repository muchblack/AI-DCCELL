---
name: push
description: Push commits to remote repository with safety checks
disable-model-invocation: true
argument-hint: "[remote] [branch]"
---

# Git Push 技能

將本地 commit 推送至遠端倉庫。

## 流程

### 步驟 1：檢查狀態

並行執行：

git status
git branch -vv

- 確認工作區是否乾淨（有未 commit 的變更時提醒使用者先 commit）
- 確認當前分支與遠端追蹤關係

### 步驟 2：顯示待推送 commit

git log @{upstream}..HEAD --oneline

若無遠端追蹤分支，改用：

git log --oneline -10

並告知使用者這是首次推送此分支。

若無待推送的 commit，告知使用者並結束。

### 步驟 3：確認推送目標

向使用者報告：
- 當前分支名稱
- 遠端名稱與分支
- 待推送的 commit 數量與摘要

若推送目標為 main 或 master，明確警告使用者並等待確認。

### 步驟 4：執行推送

- 有遠端追蹤分支：git push
- 首次推送：git push -u origin <branch>
- 指定引數：git push <remote> <branch>

### 步驟 5：驗證

git log @{upstream}..HEAD --oneline

確認無剩餘未推送 commit，回報推送成功。

## 引數處理

- /push：推送當前分支到追蹤的遠端
- /push origin feature-x：推送到指定遠端與分支

若 $ARGUMENTS 非空，解析為 <remote> <branch> 使用。

## 安全規則

- 不 force push：絕對不使用 --force 或 --force-with-lease（除非使用者明確要求）
- main/master 警告：推送到 main 或 master 時，先顯示警告並列出所有待推送 commit，等待使用者確認
- 不修改 git config：不更動任何 git 設定
- 工作區髒時提醒：有未 commit 的變更時，建議使用者先執行 /commit
