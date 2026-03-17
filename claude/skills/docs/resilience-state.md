# Resilience State Protocol

統一容錯與自動恢復協定，供所有 skill 參照。

## 腳本總覽

| 腳本 | 路徑 | 用途 |
|------|------|------|
| `health-check.sh` | `~/.claude/skills/scripts/health-check.sh` | Provider 健康檢查（MLX/Ollama/Gemini/Codex） |
| `retry.sh` | `~/.claude/skills/scripts/retry.sh` | 指數退避重試（含 jitter） |
| `watchdog.sh` | `~/.claude/skills/scripts/watchdog.sh` | 超時殺進程 |
| `validate-state.sh` | `~/.claude/skills/scripts/validate-state.sh` | state.json 結構驗證 + 自動修復 |

## 統一超時

| Provider | 超時秒數 | 用於 |
|----------|---------|------|
| MLX | 180s | inference, analyze |
| Ollama | 300s | code generation |
| CrossReview | 120s | ask codex/gemini review |
| HealthCheck | 2s per provider | pre-flight |

## health-check.sh

```bash
# 檢查全部
bash ~/.claude/skills/scripts/health-check.sh
# 指定 provider
bash ~/.claude/skills/scripts/health-check.sh mlx ollama
```

**輸出**: JSON `{ provider: { status, models[], latency_ms, error? } }`
**Exit**: 0=全部正常, 1=部分失敗, 2=全部失敗

**status 值**:
- `ok` — 可用，model 已載入
- `no_model` — 服務在線但無可用模型
- `down` — 不可達

## retry.sh

```bash
bash ~/.claude/skills/scripts/retry.sh [-n 3] [-b 1] [-m 30] -- COMMAND [ARGS...]
```

- `-n`: 最大重試次數（預設 3）
- `-b`: 初始退避秒數（預設 1）
- `-m`: 最大退避秒數（預設 30）
- 退避公式: `base * 2^(attempt-1) + random_jitter`
- **Exit 124** = 重試耗盡

## watchdog.sh

```bash
bash ~/.claude/skills/scripts/watchdog.sh TIMEOUT_SECS COMMAND [ARGS...]
```

- 超時先 SIGTERM，1 秒後 SIGKILL
- **Exit 124** = 超時

## validate-state.sh

```bash
bash ~/.claude/skills/scripts/validate-state.sh [STATE_FILE]
```

**驗證項目**:
1. 必要欄位: taskName, objective, steps, current
2. step 結構: index, title, status, attempts, substeps
3. 孤兒 cursor: current 指向不存在的 step/substep

**自動修復**: 缺欄位補預設值，孤兒 cursor 重導至第一個未完成 step

**Checkpoint**: 修復前自動備份至 `.ccb/.checkpoints/`，FIFO 保留 10 份

**Exit**: 0=valid, 1=repaired, 2=unrecoverable

## Skill 整合模式

### Pre-flight 模式（推薦）

在耗費 token 呼叫 provider 前，先做 health check：

```bash
# 檢查 MLX 是否可用
result=$(bash ~/.claude/skills/scripts/health-check.sh mlx)
status=$(echo "$result" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['mlx']['status'])")
if [ "$status" != "ok" ]; then
  echo "MLX down, falling back to Claude direct"
fi
```

### Retry + Watchdog 組合

```bash
# 重試 3 次，每次限時 180 秒
bash ~/.claude/skills/scripts/retry.sh -n 3 -b 2 -- \
  bash ~/.claude/skills/scripts/watchdog.sh 180 \
    curl -s http://localhost:8090/v1/chat/completions ...
```

### State 變更前驗證

每次修改 state.json 前，先執行 validate-state.sh 確保結構完整：

```bash
bash ~/.claude/skills/scripts/validate-state.sh .ccb/state.json
rc=$?
if [ $rc -eq 2 ]; then
  echo "State unrecoverable, manual intervention needed"
  exit 1
fi
# rc=0 或 1 都可繼續（1 表示已自動修復）
```

## Fallback 決策樹

```
Provider 呼叫前
  ├─ health-check → down?
  │   └─ 直接 fallback（不浪費 token）
  ├─ health-check → ok
  │   └─ watchdog(TIMEOUT) + retry(N)
  │       ├─ 成功 → 繼續
  │       └─ exhaustion (exit 124)
  │           └─ fallback to Claude direct
  └─ health-check → no_model
      └─ 警告 + fallback
```
