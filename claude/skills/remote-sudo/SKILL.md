---
name: remote-sudo
description: "查詢遠端主機（預設 myMini）的 sudo NOPASSWD 白名單，或測試指令是否需要密碼；維運前確認哪些指令可免密碼執行。"
argument-hint: "[host=myMini] [--cmd 'command to test']"
---

# 遠端 sudo 免密碼查詢

透過非互動 SSH（BatchMode）查詢遠端主機的 sudo NOPASSWD 白名單。

完整流程見 `references/flow.md`
