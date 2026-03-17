#!/usr/bin/env bash
# telemetry.sh — Skill invocation telemetry logger
# 用法: telemetry.sh record SKILL PROVIDER DURATION_MS RESULT [--fallback] [--error MSG]
#       telemetry.sh query [--skill X] [--provider X] [--last N]
#
# record: 記錄一筆 skill 呼叫
#   SKILL:       skill 名稱 (e.g. dev, mlx-code, ollama-code)
#   PROVIDER:    AI provider (e.g. mlx, ollama, gemini, claude)
#   DURATION_MS: 耗時毫秒
#   RESULT:      ok | passable | garbage | error | timeout | fallback
#   --fallback:  標記此次為降級呼叫
#   --error MSG: 附加錯誤訊息
#
# query: 查詢 telemetry 資料
#   --skill X:    篩選特定 skill
#   --provider X: 篩選特定 provider
#   --last N:     最近 N 筆 (預設 20)
#
# 資料位置: ~/.claude/skills/memory/telemetry.jsonl

set -uo pipefail

TELEMETRY_FILE="${TELEMETRY_FILE:-$HOME/.claude/skills/memory/telemetry.jsonl}"

case "${1:-}" in
  record)
    shift
    if [ $# -lt 4 ]; then
      echo "Usage: telemetry.sh record SKILL PROVIDER DURATION_MS RESULT [--fallback] [--error MSG]" >&2
      exit 1
    fi

    SKILL="$1"; PROVIDER="$2"; DURATION_MS="$3"; RESULT="$4"
    shift 4

    FALLBACK=false
    ERROR_MSG=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --fallback) FALLBACK=true; shift ;;
        --error) ERROR_MSG="$2"; shift 2 ;;
        *) shift ;;
      esac
    done

    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Build JSON
    python3 -c "
import json, sys
entry = {
    'timestamp': '$TIMESTAMP',
    'skill': '$SKILL',
    'provider': '$PROVIDER',
    'duration_ms': int('$DURATION_MS'),
    'result': '$RESULT',
    'fallback': $( [ "$FALLBACK" = "true" ] && echo "True" || echo "False" )
}
error_msg = '''$ERROR_MSG'''
if error_msg:
    entry['error'] = error_msg
print(json.dumps(entry, ensure_ascii=False))
" >> "$TELEMETRY_FILE"

    echo "ok"
    ;;

  query)
    shift
    if [ ! -f "$TELEMETRY_FILE" ]; then
      echo "[]"
      exit 0
    fi

    FILTER_SKILL=""
    FILTER_PROVIDER=""
    LAST_N=20
    while [ $# -gt 0 ]; do
      case "$1" in
        --skill) FILTER_SKILL="$2"; shift 2 ;;
        --provider) FILTER_PROVIDER="$2"; shift 2 ;;
        --last) LAST_N="$2"; shift 2 ;;
        *) shift ;;
      esac
    done

    export FILTER_SKILL FILTER_PROVIDER LAST_N
    python3 << 'PYEOF'
import json, os, sys

telemetry_file = os.environ.get("TELEMETRY_FILE", os.path.expanduser("~/.claude/skills/memory/telemetry.jsonl"))
filter_skill = os.environ.get("FILTER_SKILL", "")
filter_provider = os.environ.get("FILTER_PROVIDER", "")
last_n = int(os.environ.get("LAST_N", "20"))

entries = []
with open(telemetry_file, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            if filter_skill and e.get("skill") != filter_skill:
                continue
            if filter_provider and e.get("provider") != filter_provider:
                continue
            entries.append(e)
        except json.JSONDecodeError:
            pass

entries = entries[-last_n:]
print(json.dumps(entries, ensure_ascii=False, indent=2))
PYEOF
    ;;

  *)
    echo "Usage: telemetry.sh {record|query} ..." >&2
    exit 1
    ;;
esac
