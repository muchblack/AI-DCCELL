---
name: clone
description: >-
  Git clone 使用 ~/.ssh/config 中的 SSH host，互動式指定參數。
  可一次給齊或逐步問答。
  Examples: "/clone hemidemi:group/project.git ~/code/php",
  "/clone", "/clone hemidemi:tintint/spec-collection".
argument-hint: "[ssh-host:repo-path] [target-path]"
---

# Git Clone

使用 SSH config 中已配置的 host，將 repo clone 至指定路徑。
支援互動問答——未提供的參數會逐一詢問。

完整流程見 `references/flow.md`
