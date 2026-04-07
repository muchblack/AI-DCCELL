# Corrections Schema (Unified)

> 統一 corrections 記錄格式，供所有 skill 共用。

## 檔案位置

`~/.claude/skills/memory/corrections.jsonl`

## Schema

```json
{
  "timestamp": "ISO 8601 (e.g. 2026-03-06T10:15:00Z)",
  "provider": "mlx | ollama",
  "artifact_type": "plan | code",
  "task_summary": "一行任務摘要 (max 100 chars)",
  "language": "PHP | TypeScript | Python | ... (code only, plan 留空)",
  "project_type": "laravel | react | django | infra-skills | ...",
  "framework": "Laravel 11 | Next.js 15 | Django 5 | ... (optional)",
  "quality_score": "good | passable | garbage (code) | pass | supplemented | takeover (plan)",
  "issues": ["issue 1", "issue 2"],
  "corrections": ["fix 1", "fix 2"],
  "severity": "minor | major | critical",
  "takeover": false,
  "routed_by": "smart-router | manual | default (optional)",
  "route_reason": "reason string from route-task.sh (optional)",
  "route_correct": true
}
```

## 欄位說明

| 欄位            | 必要      | 說明                                         |
| --------------- | --------- | -------------------------------------------- |
| `timestamp`     | Y         | 記錄時間                                     |
| `provider`      | Y         | 產出 AI（mlx/ollama）                        |
| `artifact_type` | Y         | plan 或 code                                 |
| `task_summary`  | Y         | 簡述任務                                     |
| `language`      | code only | 程式語言                                     |
| `project_type`  | Y         | 專案類型（用於篩選注入）                     |
| `framework`     | N         | 框架（更精確篩選）                           |
| `quality_score` | Y         | 評分結果                                     |
| `issues`        | Y         | 發現的問題                                   |
| `corrections`   | Y         | 套用的修正                                   |
| `severity`      | Y         | minor/major/critical                         |
| `takeover`      | Y         | Claude 是否全面接管                          |
| `routed_by`     | N         | 路由來源：smart-router / manual / default    |
| `route_reason`  | N         | route-task.sh 回傳的 reason                  |
| `route_correct` | N         | 路由決策是否正確（takeover=true 時為 false） |

## 注入規則

注入 context 時：

1. 按 `project_type` 篩選（必要時加 `language`/`framework`）
2. 取最近 5 筆（newest first）
3. `severity: critical` 的記錄不受 5 筆限制，永遠注入

## 剪枝規則

- 總量上限：100 筆
- 超過時 FIFO 淘汰（`severity: critical` 豁免）
- 超過 90 天的 `severity: minor` 自動標記過期
- 執行：`bash ~/.claude/skills/scripts/prune-corrections.sh`

## 來源 Skill

以下 skill 在 review 後會寫入 corrections：

- `/dev` — Phase 4 (plan review) + Phase 8 (code review)
- `/mlx-code` — Step 4 (standalone code review)
- `/ollama-code` — Step 4 (standalone code review)
- `/mlx-reason` — Step 4 (standalone reasoning review)
