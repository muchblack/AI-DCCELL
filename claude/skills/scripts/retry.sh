#!/usr/bin/env bash
# retry.sh — Transient retry with exponential backoff + jitter
# 用法: retry.sh [OPTIONS] -- COMMAND [ARGS...]
#   -n NUM    最大重試次數 (預設 3)
#   -b SECS   初始退避秒數 (預設 1)
#   -m SECS   最大退避秒數 (預設 30)
# Exit: 命令的 exit code，或 124 (exhaustion)
#
# 範例:
#   retry.sh -- curl -s http://localhost:8090/v1/models
#   retry.sh -n 5 -b 2 -- some_flaky_command

set -uo pipefail

MAX_RETRIES=3
BASE_DELAY=1
MAX_DELAY=30

while [ $# -gt 0 ]; do
  case "$1" in
    -n) MAX_RETRIES="$2"; shift 2 ;;
    -b) BASE_DELAY="$2"; shift 2 ;;
    -m) MAX_DELAY="$2"; shift 2 ;;
    --) shift; break ;;
    *)  break ;;
  esac
done

if [ $# -eq 0 ]; then
  echo "Usage: retry.sh [OPTIONS] -- COMMAND [ARGS...]" >&2
  exit 1
fi

_jitter() {
  # 回傳 0 ~ $1 之間的隨機毫秒（整數），用於 sleep 小數
  local max_ms=$1
  if [ "$max_ms" -le 0 ]; then
    echo "0"
    return
  fi
  # RANDOM 是 bash 內建，0-32767
  echo $(( RANDOM % max_ms ))
}

_min() {
  if [ "$1" -lt "$2" ]; then echo "$1"; else echo "$2"; fi
}

attempt=0
while true; do
  "$@"
  rc=$?

  if [ $rc -eq 0 ]; then
    exit 0
  fi

  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$MAX_RETRIES" ]; then
    echo "retry.sh: exhausted $MAX_RETRIES attempts, last exit=$rc" >&2
    exit 124
  fi

  # 指數退避: base * 2^(attempt-1)，上限 MAX_DELAY
  delay=$((BASE_DELAY * (1 << (attempt - 1))))
  delay=$(_min "$delay" "$MAX_DELAY")

  # 加 jitter: 0 ~ delay*500 毫秒（即 0 ~ delay/2 秒）
  jitter_ms=$(_jitter $((delay * 500)))
  jitter_sec=$(python3 -c "print(f'{${jitter_ms}/1000:.3f}')" 2>/dev/null || echo "0")

  total_sleep=$(python3 -c "print(f'{${delay}+${jitter_ms}/1000:.3f}')" 2>/dev/null || echo "$delay")

  echo "retry.sh: attempt $attempt/$MAX_RETRIES failed (exit=$rc), retrying in ${total_sleep}s..." >&2
  sleep "$total_sleep"
done
