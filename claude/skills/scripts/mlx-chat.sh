#!/usr/bin/env bash
# mlx-chat.sh — 呼叫本地 MLX Gemma 4 的通用工具
# 用法:
#   mlx-chat.sh "user message"
#   mlx-chat.sh -s "system prompt" "user message"
#   mlx-chat.sh -s "system prompt" -t 0.3 -m 2048 "user message"
#   echo "user message" | mlx-chat.sh --stdin
#   echo "user message" | mlx-chat.sh --stdin -s "system prompt"
#
# 選項:
#   -s SYSTEM    系統提示詞
#   -t TEMP      溫度 (預設 0.7)
#   -m TOKENS    最大回應 token 數 (預設 4096)
#   -j           輸出完整 JSON (預設只輸出文字)
#   --stdin      從 stdin 讀取 user message
#   --raw        不加預設 system prompt
#
# 輸出: 模型回應文字 (預設) 或完整 JSON (-j)
# Exit: 0=成功, 1=參數錯誤, 2=server 無回應, 3=推理失敗
#
# 範例:
#   mlx-chat.sh "用繁體中文解釋 MoE 架構"
#   mlx-chat.sh -s "You are a code reviewer" -t 0.3 "Review this function..."
#   cat prompt.txt | mlx-chat.sh --stdin -s "Analyze this requirement"

set -uo pipefail

MLX_HOST="${MLX_HOST:-localhost}"
MLX_PORT="${MLX_PORT:-8090}"
MLX_MODEL="${MLX_MODEL:-/Users/huai-chitzeng/.local/share/mlx-models/gemma-4-26b-a4b-it-4bit}"
MLX_URL="http://${MLX_HOST}:${MLX_PORT}/v1/chat/completions"

SYSTEM_PROMPT=""
TEMPERATURE="0.7"
MAX_TOKENS="4096"
JSON_OUTPUT=false
FROM_STDIN=false
RAW_MODE=false

while [ $# -gt 0 ]; do
  case "$1" in
    -s) SYSTEM_PROMPT="$2"; shift 2 ;;
    -t) TEMPERATURE="$2"; shift 2 ;;
    -m) MAX_TOKENS="$2"; shift 2 ;;
    -j) JSON_OUTPUT=true; shift ;;
    --stdin) FROM_STDIN=true; shift ;;
    --raw) RAW_MODE=true; shift ;;
    --) shift; break ;;
    -*) echo "Unknown option: $1" >&2; exit 1 ;;
    *)  break ;;
  esac
done

# 讀取 user message
if [ "$FROM_STDIN" = true ]; then
  USER_MSG=$(cat)
elif [ $# -gt 0 ]; then
  USER_MSG="$1"
else
  echo "Usage: mlx-chat.sh [-s system] [-t temp] [-m tokens] \"message\"" >&2
  echo "       echo \"message\" | mlx-chat.sh --stdin [-s system]" >&2
  exit 1
fi

if [ -z "$USER_MSG" ]; then
  echo "Error: empty user message" >&2
  exit 1
fi

# 健康檢查
if ! curl -s --max-time 2 "http://${MLX_HOST}:${MLX_PORT}/v1/models" >/dev/null 2>&1; then
  echo "Error: MLX server unreachable at ${MLX_HOST}:${MLX_PORT}" >&2
  exit 2
fi

# Model ID: 使用 MLX_MODEL（已有預設值）
MODEL_ID="$MLX_MODEL"

# 組裝 messages JSON
MESSAGES="[]"
if [ -n "$SYSTEM_PROMPT" ]; then
  MESSAGES=$(python3 -c "
import json,sys
msgs = [{'role':'system','content':sys.argv[1]}, {'role':'user','content':sys.argv[2]}]
print(json.dumps(msgs, ensure_ascii=False))
" "$SYSTEM_PROMPT" "$USER_MSG")
elif [ "$RAW_MODE" = true ]; then
  MESSAGES=$(python3 -c "
import json,sys
msgs = [{'role':'user','content':sys.argv[1]}]
print(json.dumps(msgs, ensure_ascii=False))
" "$USER_MSG")
else
  MESSAGES=$(python3 -c "
import json,sys
msgs = [
  {'role':'system','content':'You are a helpful assistant. Respond concisely and accurately.'},
  {'role':'user','content':sys.argv[1]}
]
print(json.dumps(msgs, ensure_ascii=False))
" "$USER_MSG")
fi

# 組裝 request body
REQUEST_BODY=$(python3 -c "
import json,sys
body = {
  'model': sys.argv[1],
  'messages': json.loads(sys.argv[2]),
  'max_tokens': int(sys.argv[3]),
  'temperature': float(sys.argv[4])
}
print(json.dumps(body, ensure_ascii=False))
" "$MODEL_ID" "$MESSAGES" "$MAX_TOKENS" "$TEMPERATURE")

# 呼叫 MLX
START_MS=$(python3 -c 'import time; print(int(time.time()*1000))')

RESPONSE=$(curl -s --max-time 300 "$MLX_URL" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY" 2>/dev/null)

END_MS=$(python3 -c 'import time; print(int(time.time()*1000))')
DURATION_MS=$(( END_MS - START_MS ))

if [ -z "$RESPONSE" ]; then
  echo "Error: empty response from MLX server" >&2
  exit 3
fi

# 檢查是否有 error
HAS_ERROR=$(python3 -c "
import json,sys
try:
  r=json.loads(sys.stdin.read())
  print('yes' if 'error' in r else 'no')
except: print('yes')
" <<< "$RESPONSE")

if [ "$HAS_ERROR" = "yes" ]; then
  echo "Error: MLX inference failed" >&2
  python3 -c "
import json,sys
try:
  r=json.loads(sys.stdin.read())
  print(r.get('error','unknown error'))
except Exception as e:
  print(f'parse error: {e}')
" <<< "$RESPONSE" >&2
  exit 3
fi

# 輸出結果
if [ "$JSON_OUTPUT" = true ]; then
  # 附加 duration_ms 到 JSON
  python3 -c "
import json,sys
r=json.loads(sys.stdin.read())
r['duration_ms']=${DURATION_MS}
print(json.dumps(r, ensure_ascii=False, indent=2))
" <<< "$RESPONSE"
else
  python3 -c "
import json,sys
r=json.loads(sys.stdin.read())
content=r['choices'][0]['message']['content']
print(content)
" <<< "$RESPONSE"
fi
