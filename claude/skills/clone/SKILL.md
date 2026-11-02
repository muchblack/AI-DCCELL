---
name: clone
description: "用 ~/.ssh/config 的 SSH host 執行 git clone，可一次給齊參數或逐步問答。 Triggers on: clone repo, git clone, 拉 repo, 拉專案, 下載 repo, clone 下來, 把 repo 拉下來."
model: claude-sonnet-5
argument-hint: "[ssh-host:repo-path] [target-path]"
---

# Git Clone

使用 SSH config 中已配置的 host，將 repo clone 至指定路徑。
支援互動問答——未提供的參數會逐一詢問。

完整流程見 `references/flow.md`
