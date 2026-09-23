---
name: remote-sudo
description: >-
  查詢遠端主機（預設 myMini）目前的 sudo NOPASSWD 白名單，或測試特定指令是否需要密碼。
  用於維運前確認哪些指令可以免密碼執行、哪些會卡在密碼提示，避免誤判「這台機器 sudo 全免密碼」。
  Examples: "/remote-sudo", "/remote-sudo myResp", "/remote-sudo myMini --cmd 'systemctl restart nginx'".
argument-hint: "[host=myMini] [--cmd 'command to test']"
---

# 遠端 sudo 免密碼查詢

透過非互動 SSH（BatchMode）查詢遠端主機的 sudo NOPASSWD 白名單。

完整流程見 `references/flow.md`
