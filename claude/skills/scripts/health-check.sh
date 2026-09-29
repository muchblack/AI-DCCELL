#!/usr/bin/env bash
# health-check.sh — Provider health pre-flight
# 3 秒內返回所有 provider 狀態 JSON（含 model loaded 偵測）
# 用法: health-check.sh [provider...]
#   無參數 = 檢查全部 (codex, agy, gemini, hf)；gemini/codex/agy 以 herdr pane 是否存在判定
#   指定 = 只檢查指定 provider
# 輸出: JSON { provider: { status, models[], latency_ms, error? } }
# Exit: 0=全部正常, 1=部分失敗, 2=全部失敗

set -euo pipefail

TIMEOUT_SEC=2

TMPDIR_HC="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_HC"' EXIT

ALL_PROVIDERS=(codex agy gemini hf)

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

# herdr agent pane 偵測：有至少一個該 agent 的 pane 即視為可用
check_herdr_agent() {
  local name=$1 start end out count latency
  start=$(ts_ms)
  out=$(_run_with_timeout "$TIMEOUT_SEC" herdr agent list 2>/dev/null) || out=""
  end=$(ts_ms)
  latency=$(( end - start ))

  if [ -z "$out" ]; then
    printf '{"status":"down","models":[],"latency_ms":%d,"error":"herdr agent list failed"}' "$latency"
    return
  fi

  count=$(python3 -c "
import json,sys
try:
  d=json.loads(sys.stdin.read())
  print(sum(1 for a in d['result']['agents'] if a.get('agent')==sys.argv[1]))
except Exception:
  print(0)
" "$name" <<< "$out" 2>/dev/null) || count=0

  if [ "$count" -gt 0 ] 2>/dev/null; then
    printf '{"status":"ok","models":["%s"],"latency_ms":%d}' "$name" "$latency"
  else
    printf '{"status":"down","models":[],"latency_ms":%d,"error":"no herdr pane for %s"}' "$latency" "$name"
  fi
}

check_gemini() { check_herdr_agent gemini; }
check_codex()  { check_herdr_agent codex; }
check_agy()    { check_herdr_agent agy; }

check_hf() {
  local start end status latency
  start=$(ts_ms)

  if [ -z "${HF_TOKEN:-}" ]; then
    end=$(ts_ms)
    latency=$(( end - start ))
    printf '{"status":"no_token","models":[],"latency_ms":%d,"error":"HF_TOKEN not set"}' "$latency"
    return
  fi

  local http_code
  http_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT_SEC" \
    -H "Authorization: Bearer $HF_TOKEN" \
    "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell" 2>/dev/null) || http_code="000"

  end=$(ts_ms)
  latency=$(( end - start ))

  case "$http_code" in
    200) printf '{"status":"ok","models":["FLUX.1-schnell"],"latency_ms":%d}' "$latency" ;;
    401) printf '{"status":"bad_token","models":[],"latency_ms":%d,"error":"invalid HF_TOKEN"}' "$latency" ;;
    *)   printf '{"status":"down","models":[],"latency_ms":%d,"error":"HTTP %s"}' "$latency" "$http_code" ;;
  esac
}

# 並行執行所有 provider 檢查
for p in "${PROVIDERS[@]}"; do
  case "$p" in
    gemini) check_gemini > "$TMPDIR_HC/gemini.json" 2>/dev/null & ;;
    codex)  check_codex  > "$TMPDIR_HC/codex.json"  2>/dev/null & ;;
    agy)    check_agy    > "$TMPDIR_HC/agy.json"    2>/dev/null & ;;
    hf)     check_hf     > "$TMPDIR_HC/hf.json"     2>/dev/null & ;;
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
