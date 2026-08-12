---
name: ccb-role
description: >-
  建立、綁定、列出、移除本地 CCB 自訂 Role。Role 是可跨專案複用的 agent 行為定義，
  比單次 memory 注入更持久。支援建立 coordinator 模式（自動 dispatch 到其他 agent）。
  Triggers on: ccb-role, 建立 role, 自訂 role, create role, custom role,
  ccb role, 建 role, role 建立, bind role, 綁定 role, 移除 role.
  Examples: "/ccb-role create", "/ccb-role list", "/ccb-role bind <role-id> <agent>",
  "/ccb-role remove <role-id>".
argument-hint: "create | list | bind <role-id> <agent>:<provider> | show <role-id> | remove <role-id>"
---

# CCB Role 管理

管理本地自訂 CCB Role，放在 `~/.roles/installed/<namespace>.<name>/current/`。

## 指令對照

| 指令 | 說明 |
|------|------|
| `create` | 互動式建立新 Role（Q&A 推導） |
| `list` | 列出所有已安裝 Role 及狀態 |
| `bind <role-id> <agent>:<provider>` | 將 Role 綁定到指定 agent |
| `show <role-id>` | 顯示 Role 的 memory.md 與 role.toml |
| `remove <role-id>` | 移除本地 Role 目錄（需確認） |

完整 create 流程見 `references/create-flow.md`。
Role 模板見 `references/role-templates.md`。

> ⚠️ **coordinator 模式警告**：實戰中 agy 綁 coordinator 曾「只敘述、不執行」——
> 聲稱已轉派但從未真的跑 `ask`，覆蓋率靜默歸零。coordinator 建議只綁 claude
> provider，且模板已內建自證機制：轉派必附 job id 回執，無回執不得聲稱已轉派。
> 需要全員覆蓋的審查請改用 main 直接扇出（見 `/ccb-dev`）。
