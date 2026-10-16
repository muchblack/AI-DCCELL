---
name: obs-telegram
description: 把 myNote Telegram bot 在 myMini 上收到的 Inbox Item，透過 SSH rsync 拉回 Mac 並放進 Obsidian vault 的收件匣，交給既有的 /obs compile 處理。Triggers on: telegram inbox 同步, obs-telegram, 拉 inbox, 拉 telegram 筆記, sync inbox from mymini, myNote 同步, pull inbox.
metadata:
  short-description: myMini → Mac 的 Telegram Inbox Item 同步
disable-model-invocation: true
---

# obs-telegram — myMini → Mac 的 Telegram Inbox Item 同步

依 [ADR 0004](/Users/huai-chitzeng/code/python/myNote/docs/adr/0004-sync-inbox-via-ssh-rsync.md)：myNote bot 搬到 `myMini` 常駐後（ADR 0003），Inbox Item 檔案寫在 `myMini` 上，這個 skill 負責用既有的 SSH 存取把它們拉回 Mac，並接進 Obsidian vault 既有的「收件匣 → `/obs compile`」流程——不另外造一個處理 pipeline。

## 子命令一覽

| 子命令 | 用途 |
|--------|------|
| `pull` | rsync 從 `myMini` 拉回 myNote 本機 `inbox/`（預設唯讀對遠端，不刪除遠端檔案） |
| `pull --delete-remote` | 同 `pull`，但拉回並驗證本機存在後，列清單經使用者確認再刪除對應遠端檔案（破壞性、opt-in，非預設） |
| `stage` | 把本機 `inbox/` 的檔案搬進 `$OBSIDIAN_VAULT/myWiki/00-收件匣`，交給 `/obs compile` |
| `sync`（預設） | `pull` + `stage` 一次做完，並提示下一步跑 `/obs compile`（可加 `--delete-remote`） |

For full instructions, see `references/flow.md`
