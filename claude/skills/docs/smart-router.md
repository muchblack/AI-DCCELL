# Smart Router — 智慧模型路由

> 根據任務特徵動態選擇最佳 AI provider，取代硬編碼規則。

## 腳本

`~/.claude/skills/scripts/route-task.sh`

## 用法

```bash
bash ~/.claude/skills/scripts/route-task.sh \
  --type coding \
  --complexity medium \
  --lines 80 \
  --files 3 \
  --lang PHP \
  --security false
```

## 輸出

```json
{ "provider": "ollama", "reason": "standard-coding", "fallback": "claude" }
```

## 路由規則（優先順序）

| #   | 條件                    | 路由               | 原因                     |
| --- | ----------------------- | ------------------ | ------------------------ |
| 1   | `security=true`         | claude             | 安全敏感，不信任弱模型   |
| 2   | `type=reasoning`        | mlx → claude       | 推理分析用本地 MLX       |
| 3   | `lines<20 && files<=1`  | claude             | 小修改，往返開銷 > 收益  |
| 4   | 該語言 takeover 率 >40% | claude             | 歷史品質不可靠           |
| 5   | `complex && lines>200`  | ollama（建議拆分） | 大任務仍用 GPU，但應拆分 |
| 6   | `lines>=20`             | ollama             | 標準寫碼路徑             |
| 7   | 兜底                    | claude             | 所有不匹配的情況         |

## 資料來源

- **Health check**: `~/.claude/skills/scripts/health-check.sh`（2 秒超時）
- **歷史表現**: `~/.claude/skills/memory/corrections.jsonl`（takeover 率計算）

## 自適應回饋

corrections.jsonl 新增欄位：

- `routed_by`: smart-router / manual / default
- `route_reason`: 路由原因
- `route_correct`: 路由是否正確（takeover=true → false）

takeover 率計算取最近 10 筆同語言 code corrections，超過 40% 則自動將該語言路由到 Claude。

## 整合位置

以下 skill 在寫碼前應呼叫 route-task.sh：

- CLAUDE.md Default Coding Flow（主入口）
- `/dev` Phase 5（Ollama Code 前可加路由判斷）
- `/ollama-code`、`/mlx-code`（可在入口處驗證路由建議）
