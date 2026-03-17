#!/usr/bin/env bash
# health-check.sh — Provider health pre-flight
# 3 秒內返回所有 provider 狀態 JSON（含 model loaded 偵測）
# 用法: health-check.sh [provider...]
#   無參數 = 檢查全部 (mlx, ollama, gemini, codex)
#   指定 = 只檢查指定 provider
# 輸出: JSON { provider: { status, models[], latency_ms, error? } }
# Exit: 0=全部正常, 1=部分失敗, 2=全部失敗

set -euo pipefail

MLX_HOST="${MLX_HOST:-localhost}"
MLX_PORT="${MLX_PORT:-8090}"
OLLAMA_HOST="${OLLAMA_HOST:-192.168.1.206}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
TIMEOUT_SEC=2

TMPDIR_HC="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_HC"' EXIT

ALL_PROVIDERS=(mlx ollama gemini codex)

if [ $# -gt 0 ]; then
  PROVIDERS=("$@")
else
  PROVIDERS=("${ALL_PROVIDERS[@]}")
fi

ts_ms() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import time; print(int(time.time()*1000))'
  elif command -v perl >/dev/null 2>&1; then
    perl -MTime::HiRes=time -e 'printf "%d\n", time()*1000'
  else
    echo 0
  fi
}

check_mlx() {
  local start end resp models status
  start=$(ts_ms)
  resp=$(curl -s --max-time "$TIMEOUT_SEC" "http://${MLX_HOST}:${MLX_PORT}/v1/models" 2>/dev/null) || resp=""
  end=$(ts_ms)
  local latency=$(( end - start ))

  if [ -z "$resp" ]; then
    printf '{"status":"down","models":[],"latency_ms":%d,"error":"unreachable"}' "$latency"
    return
  fi

  if command -v jq >/dev/null 2>&1; then
    models=$(echo "$resp" | jq -c '[.data[]?.id // empty]' 2>/dev/null) || models="[]"
  else
    models=$(python3 -c "
import json,sys
try:
  d=json.loads(sys.stdin.read())
  print(json.dumps([m['id'] for m in d.get('data',[])]))
except: print('[]')
" <<< "$resp" 2>/dev/null) || models="[]"
  fi

  local count
  if command -v jq >/dev/null 2>&1; then
    count=$(echo "$models" | jq 'length' 2>/dev/null) || count=0
  else
    count=$(python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())))" <<< "$models" 2>/dev/null) || count=0
  fi

  if [ "$count" -gt 0 ] 2>/dev/null; then
    status="ok"
  else
    status="no_model"
  fi

  printf '{"status":"%s","models":%s,"latency_ms":%d}' "$status" "$models" "$latency"
}

check_ollama() {
  local start end resp models status
  start=$(ts_ms)
  resp=$(curl -s --max-time "$TIMEOUT_SEC" "http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags" 2>/dev/null) || resp=""
  end=$(ts_ms)
  local latency=$(( end - start ))

  if [ -z "$resp" ]; then
    printf '{"status":"down","models":[],"latency_ms":%d,"error":"unreachable"}' "$latency"
    return
  fi

  if command -v jq >/dev/null 2>&1; then
    models=$(echo "$resp" | jq -c '[.models[]?.name // empty]' 2>/dev/null) || models="[]"
  else
    models=$(python3 -c "
import json,sys
try:
  d=json.loads(sys.stdin.read())
  print(json.dumps([m['name'] for m in d.get('models',[])]))
except: print('[]')
" <<< "$resp" 2>/dev/null) || models="[]"
  fi

  local count
  if command -v jq >/dev/null 2>&1; then
    count=$(echo "$models" | jq 'length' 2>/dev/null) || count=0
  else
    count=$(python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())))" <<< "$models" 2>/dev/null) || count=0
  fi

  if [ "$count" -gt 0 ] 2>/dev/null; then
    status="ok"
  else
    status="no_model"
  fi

  printf '{"status":"%s","models":%s,"latency_ms":%d}' "$status" "$models" "$latency"
}

_run_with_timeout() {
  # macOS 無 timeout 指令，用背景進程 + kill 替代
  local secs=$1; shift
  "$@" &
  local pid=$!
  (sleep "$secs" && kill "$pid" 2>/dev/null) &
  local watchdog=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  kill "$watchdog" 2>/dev/null
  wait "$watchdog" 2>/dev/null
  return $rc
}

check_gemini() {
  local start end output status latency
  start=$(ts_ms)
  output=$(_run_with_timeout "$TIMEOUT_SEC" gping 2>&1) || output="fail: $output"
  end=$(ts_ms)
  latency=$(( end - start ))

  if echo "$output" | grep -qi "ok\|success\|healthy"; then
    status="ok"
    printf '{"status":"ok","models":["gemini"],"latency_ms":%d}' "$latency"
  else
    local err
    err=$(echo "$output" | tr '"' "'" | tr '\n' ' ' | head -c 200)
    printf '{"status":"down","models":[],"latency_ms":%d,"error":"%s"}' "$latency" "$err"
  fi
}

check_codex() {
  local start end output status latency
  start=$(ts_ms)
  output=$(_run_with_timeout "$TIMEOUT_SEC" cping 2>&1) || output="fail: $output"
  end=$(ts_ms)
  latency=$(( end - start ))

  if echo "$output" | grep -qi "ok\|success\|healthy"; then
    status="ok"
    printf '{"status":"ok","models":["codex"],"latency_ms":%d}' "$latency"
  else
    local err
    err=$(echo "$output" | tr '"' "'" | tr '\n' ' ' | head -c 200)
    printf '{"status":"down","models":[],"latency_ms":%d,"error":"%s"}' "$latency" "$err"
  fi
}

# 並行執行所有 provider 檢查
for p in "${PROVIDERS[@]}"; do
  case "$p" in
    mlx)    check_mlx    > "$TMPDIR_HC/mlx.json"    2>/dev/null & ;;
    ollama) check_ollama > "$TMPDIR_HC/ollama.json" 2>/dev/null & ;;
    gemini) check_gemini > "$TMPDIR_HC/gemini.json" 2>/dev/null & ;;
    codex)  check_codex  > "$TMPDIR_HC/codex.json"  2>/dev/null & ;;
    *) echo "Unknown provider: $p" >&2 ;;
  esac
done

wait

# 組合 JSON 輸出
ok_count=0
total=0

output="{"
first=true
for p in "${PROVIDERS[@]}"; do
  f="$TMPDIR_HC/${p}.json"
  if [ -f "$f" ] && [ -s "$f" ]; then
    result=$(cat "$f")
  else
    result='{"status":"skip","models":[],"latency_ms":0,"error":"check not executed"}'
  fi

  if [ "$first" = true ]; then
    first=false
  else
    output="${output},"
  fi
  output="${output}\"${p}\":${result}"

  total=$((total + 1))
  if echo "$result" | grep -q '"status":"ok"'; then
    ok_count=$((ok_count + 1))
  fi
done
output="${output}}"

echo "$output"

# Exit code
if [ "$ok_count" -eq "$total" ]; then
  exit 0
elif [ "$ok_count" -gt 0 ]; then
  exit 1
else
  exit 2
fi
