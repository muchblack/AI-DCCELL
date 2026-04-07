#!/usr/bin/env bash
# mlx-chat.sh — MLX 本地模型通用呼叫工具
# 封裝 MLX server（localhost:8090）的 HTTP API，支援 system prompt、溫度、max tokens。
#
# 用法:
#   mlx-chat.sh "message"                          # 基本呼叫
#   mlx-chat.sh -s "system prompt" "message"       # 帶 system prompt
#   mlx-chat.sh -s "system" -t 0.3 -m 4096 "msg"  # 完整參數
#   echo "long text" | mlx-chat.sh --stdin          # stdin 模式（避免 shell 字元問題）
#   echo "long text" | mlx-chat.sh --stdin -s "system prompt"
#   mlx-chat.sh -f /tmp/input.txt -s "system"      # 從檔案讀取
#
# 環境變數:
#   MLX_HOST    — MLX server 位址（預設 localhost）
#   MLX_PORT    — MLX server 端口（預設 8090）
#   MLX_MODEL   — 模型路徑（預設自動偵測）
#
# 輸出:
#   純文字（message.content），思考鏈輸出到 stderr
#   若 content 為空但有 reasoning，輸出 reasoning 到 stdout（fallback）

set -euo pipefail

# ── 預設值 ──
MLX_HOST="${MLX_HOST:-localhost}"
MLX_PORT="${MLX_PORT:-8090}"
MLX_MODEL="${MLX_MODEL:-}"
SYSTEM_PROMPT=""
TEMPERATURE=0.3
MAX_TOKENS=4096
USE_STDIN=false
INPUT_FILE=""
USER_MESSAGE=""

# ── 解析參數 ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--system)    SYSTEM_PROMPT="$2";  shift 2 ;;
    -t|--temp)      TEMPERATURE="$2";    shift 2 ;;
    -m|--max-tokens) MAX_TOKENS="$2";    shift 2 ;;
    --stdin)        USE_STDIN=true;       shift ;;
    -f|--file)      INPUT_FILE="$2";     shift 2 ;;
    -h|--help)
      sed -n '2,/^$/p' "$0" | sed 's/^# //' | sed 's/^#//'
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
    *)
      USER_MESSAGE="$1"
      shift
      ;;
  esac
done

# ── 讀取輸入 ──
if [[ "$USE_STDIN" == true ]]; then
  USER_MESSAGE="$(cat)"
elif [[ -n "$INPUT_FILE" ]]; then
  if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: file not found: $INPUT_FILE" >&2
    exit 1
  fi
  USER_MESSAGE="$(cat "$INPUT_FILE")"
fi

if [[ -z "$USER_MESSAGE" ]]; then
  echo "Error: no message provided. Use positional arg, --stdin, or -f <file>" >&2
  exit 1
fi

# ── 自動偵測模型 ──
if [[ -z "$MLX_MODEL" ]]; then
  MLX_MODEL=$(curl -sf "http://${MLX_HOST}:${MLX_PORT}/v1/models" 2>/dev/null \
    | python3 -c "import sys,json; models=json.load(sys.stdin)['data']; print(models[-1]['id'])" 2>/dev/null) || {
    echo "Error: MLX server not reachable at ${MLX_HOST}:${MLX_PORT}" >&2
    exit 2
  }
fi

# ── 組裝 messages ──
MESSAGES_JSON=$(python3 -c "
import json, sys
messages = []
system = '''$SYSTEM_PROMPT'''
if system.strip():
    messages.append({'role': 'system', 'content': system})
# 從 stdin 讀 user message 避免 shell 跳脫問題
user_msg = sys.stdin.read()
messages.append({'role': 'user', 'content': user_msg})
print(json.dumps(messages, ensure_ascii=False))
" <<< "$USER_MESSAGE") || {
  # fallback: 用檔案傳遞避免 Unicode 問題
  TMPFILE=$(mktemp /tmp/mlx-chat-XXXXXX.json)
  trap 'rm -f "$TMPFILE"' EXIT
  python3 -c "
import json, sys
messages = []
system = sys.argv[1]
if system.strip():
    messages.append({'role': 'system', 'content': system})
with open(sys.argv[2], 'r') as f:
    messages.append({'role': 'user', 'content': f.read()})
with open(sys.argv[3], 'w') as f:
    json.dump(messages, f, ensure_ascii=False)
" "$SYSTEM_PROMPT" <(echo "$USER_MESSAGE") "$TMPFILE"
  MESSAGES_JSON=$(cat "$TMPFILE")
}

# ── 組裝 request body ──
REQUEST_BODY=$(python3 -c "
import json, sys
messages = json.loads(sys.argv[1])
body = {
    'model': sys.argv[2],
    'messages': messages,
    'max_tokens': int(sys.argv[3]),
    'temperature': float(sys.argv[4])
}
print(json.dumps(body, ensure_ascii=False))
" "$MESSAGES_JSON" "$MLX_MODEL" "$MAX_TOKENS" "$TEMPERATURE")

# ── 呼叫 MLX server ──
RESPONSE=$(curl -sf --max-time 180 \
  "http://${MLX_HOST}:${MLX_PORT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY" 2>/dev/null) || {
  echo "Error: MLX request failed (timeout or connection error)" >&2
  exit 3
}

# ── 解析回應 ──
python3 -c "
import json, sys

resp = json.loads(sys.argv[1])

# 檢查錯誤
if 'error' in resp:
    print('Error:', resp['error'], file=sys.stderr)
    sys.exit(4)

msg = resp['choices'][0]['message']
content = msg.get('content', '')
reasoning = msg.get('reasoning', '')

# 輸出思考鏈到 stderr（可用 2>/dev/null 隱藏）
if reasoning:
    print('[thinking]', reasoning[:500], file=sys.stderr)

# 輸出最終回答
if content:
    print(content)
elif reasoning:
    # Gemma 4 有時只有 reasoning 沒有 content（max_tokens 不夠）
    print(reasoning, file=sys.stdout)
    print('Warning: no content field, falling back to reasoning output', file=sys.stderr)
else:
    print('Error: empty response from MLX', file=sys.stderr)
    sys.exit(5)
" "$RESPONSE"
