#!/usr/bin/env bash
# watchdog.sh — Timeout watchdog for long-running commands
# 用法: watchdog.sh TIMEOUT_SECS COMMAND [ARGS...]
# 在 TIMEOUT_SECS 秒內完成 → 傳回命令原始 exit code
# 超時 → 殺掉進程，exit 124
#
# 範例:
#   watchdog.sh 180 curl -s http://localhost:8090/v1/chat/completions ...
#   watchdog.sh 300 ollama run qwen3.5:9b "hello"

set -uo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: watchdog.sh TIMEOUT_SECS COMMAND [ARGS...]" >&2
  exit 1
fi

TIMEOUT_SECS="$1"
shift

if ! printf '%s' "$TIMEOUT_SECS" | grep -qE '^[0-9]+$'; then
  echo "watchdog.sh: invalid timeout '$TIMEOUT_SECS'" >&2
  exit 1
fi

# 執行命令於背景
"$@" &
CMD_PID=$!

# watchdog 計時器
(
  sleep "$TIMEOUT_SECS"
  # 先 TERM 再 KILL
  kill -TERM "$CMD_PID" 2>/dev/null
  sleep 1
  kill -KILL "$CMD_PID" 2>/dev/null
) &
WATCHDOG_PID=$!

# 等待命令完成
wait "$CMD_PID" 2>/dev/null
CMD_RC=$?

# 清理 watchdog
kill "$WATCHDOG_PID" 2>/dev/null
wait "$WATCHDOG_PID" 2>/dev/null

# 判斷是否被 watchdog 殺掉
# SIGTERM=143, SIGKILL=137
if [ $CMD_RC -eq 143 ] || [ $CMD_RC -eq 137 ]; then
  echo "watchdog.sh: command timed out after ${TIMEOUT_SECS}s" >&2
  exit 124
fi

exit $CMD_RC
