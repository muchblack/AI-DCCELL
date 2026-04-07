#!/usr/bin/env bash
# hf-image.sh — Hugging Face Inference API image generator
# Calls HF text-to-image / image-to-image endpoints via curl.
#
# Usage:
#   hf-image.sh --prompt "a cat on the moon"
#   hf-image.sh --prompt "..." --model stabilityai/stable-diffusion-xl-base-1.0 --ratio 16:9
#   hf-image.sh --prompt "..." --mode i2i --input-image /path/to/img.png
#   hf-image.sh --history 5
#   hf-image.sh --refine
#
# Environment:
#   HF_TOKEN — Hugging Face API token (required, never logged)
#
# Output:
#   JSON to stdout (success or error). Warnings to stderr.

set -uo pipefail

# ── Defaults ──
DEFAULT_MODEL="black-forest-labs/FLUX.1-schnell"
DEFAULT_RATIO="1:1"
DEFAULT_MODE="t2i"
DEFAULT_OUTPUT_DIR="$HOME/Documents/hf-images"
CURL_TIMEOUT=60

# ── Variables ──
PROMPT=""
MODEL="$DEFAULT_MODEL"
MODE="$DEFAULT_MODE"
RATIO="$DEFAULT_RATIO"
SEED=""
NEGATIVE_PROMPT=""
GUIDANCE=""
STEPS=""
SCHEDULER=""
INPUT_IMAGE=""
OUTPUT_DIR="$DEFAULT_OUTPUT_DIR"
HISTORY_COUNT=""
DO_REFINE=false

# ── Timing ──
ts_ms() {
  python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || echo 0
}

# ── JSON helpers (jq with python3 fallback) ──
json_get() {
  local json="$1" key="$2"
  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -r "$key" 2>/dev/null
  else
    python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d$(echo "$key" | sed "s/\.\([^[.]*\)/['\1']/g"))" <<< "$json" 2>/dev/null
  fi
}

# ── Output helpers ──
emit_ok() {
  local path="$1" model="$2" dur="$3" w="$4" h="$5" seed="${6:-null}"
  printf '{"status":"ok","path":"%s","model":"%s","duration_ms":%s,"width":%s,"height":%s,"seed":%s}\n' \
    "$path" "$model" "$dur" "$w" "$h" "$seed"
}

emit_error() {
  local code="$1" msg="$2" dur="$3"
  msg=$(echo "$msg" | sed 's/"/\\"/g' | tr '\n' ' ' | head -c 200)
  printf '{"status":"error","code":"%s","message":"%s","duration_ms":%s}\n' "$code" "$msg" "$dur"
}

# ── Ratio mapping ──
ratio_to_wh() {
  case "$1" in
    1:1)  echo "1024 1024" ;;
    16:9) echo "1344 768"  ;;
    9:16) echo "768 1344"  ;;
    4:3)  echo "1152 896"  ;;
    3:4)  echo "896 1152"  ;;
    *)    echo >&2 "Warning: unknown ratio '$1', using 1:1"; echo "1024 1024" ;;
  esac
}

# ── Model param filter ──
filter_params() {
  local model="$1"
  local short_model
  short_model=$(basename "$model")

  case "$short_model" in
    FLUX.1-schnell)
      [ -n "$GUIDANCE" ]        && echo >&2 "Warning: --guidance ignored for FLUX.1-schnell" && GUIDANCE=""
      [ -n "$STEPS" ]           && echo >&2 "Warning: --steps ignored for FLUX.1-schnell"    && STEPS=""
      [ -n "$SCHEDULER" ]       && echo >&2 "Warning: --scheduler ignored for FLUX.1-schnell" && SCHEDULER=""
      [ -n "$NEGATIVE_PROMPT" ] && echo >&2 "Warning: --negative-prompt ignored for FLUX.1-schnell" && NEGATIVE_PROMPT=""
      [ "$MODE" = "i2i" ]       && { emit_error "unsupported" "FLUX.1-schnell does not support i2i" 0; exit 1; }
      ;;
    FLUX.1-dev)
      [ -n "$SCHEDULER" ]       && echo >&2 "Warning: --scheduler ignored for FLUX.1-dev" && SCHEDULER=""
      [ -n "$NEGATIVE_PROMPT" ] && echo >&2 "Warning: --negative-prompt ignored for FLUX.1-dev" && NEGATIVE_PROMPT=""
      [ "$MODE" = "i2i" ]       && { emit_error "unsupported" "FLUX.1-dev does not support i2i" 0; exit 1; }
      ;;
    stable-diffusion-xl-base-1.0)
      # SDXL supports all params
      ;;
    *)
      echo >&2 "Warning: unknown model '$model', sending all params as-is"
      ;;
  esac
}

# ── Build parameters JSON ──
build_params_json() {
  local params=""
  local first=true

  add_param() {
    local key="$1" val="$2" is_num="${3:-false}"
    if [ -n "$val" ]; then
      [ "$first" = true ] && first=false || params="${params},"
      if [ "$is_num" = true ]; then
        params="${params}\"${key}\":${val}"
      else
        params="${params}\"${key}\":\"${val}\""
      fi
    fi
  }

  add_param "width" "$WIDTH" true
  add_param "height" "$HEIGHT" true
  [ -n "$SEED" ]             && add_param "seed" "$SEED" true
  [ -n "$GUIDANCE" ]         && add_param "guidance_scale" "$GUIDANCE" true
  [ -n "$STEPS" ]            && add_param "num_inference_steps" "$STEPS" true
  [ -n "$NEGATIVE_PROMPT" ]  && add_param "negative_prompt" "$NEGATIVE_PROMPT"
  [ -n "$SCHEDULER" ]        && add_param "scheduler" "$SCHEDULER"

  echo "{${params}}"
}

# ── History: append ──
history_append() {
  local prompt="$1" model="$2" path="$3" dur="$4"
  local hfile="$OUTPUT_DIR/history.jsonl"
  local next_id=1

  if [ -f "$hfile" ] && [ -s "$hfile" ]; then
    local last_id
    last_id=$(tail -1 "$hfile" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('id',0))" 2>/dev/null) || last_id=0
    next_id=$((last_id + 1))
  fi

  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local params_json
  params_json=$(build_params_json)

  local entry
  entry=$(python3 -c "
import json, sys
prompt = sys.stdin.read().strip()
print(json.dumps({
  'id': $next_id,
  'timestamp': '$ts',
  'prompt': prompt,
  'model': '$model',
  'params': json.loads('$params_json'),
  'path': '$path',
  'duration_ms': $dur
}, ensure_ascii=False))
" <<< "$prompt" 2>/dev/null)

  if [ -n "$entry" ]; then
    echo "$entry" >> "$hfile"
  fi
}

# ── History: list ──
history_list() {
  local count="${1:-5}"
  local hfile="$OUTPUT_DIR/history.jsonl"

  if [ ! -f "$hfile" ] || [ ! -s "$hfile" ]; then
    echo "No history found." >&2
    exit 0
  fi

  tail -n "$count" "$hfile"
  exit 0
}

# ── Refine: load last entry ──
refine_load() {
  local hfile="$OUTPUT_DIR/history.jsonl"

  if [ ! -f "$hfile" ] || [ ! -s "$hfile" ]; then
    emit_error "no_history" "No history found for --refine" 0
    exit 1
  fi

  local last
  last=$(tail -1 "$hfile")

  PROMPT=$(json_get "$last" ".prompt")
  MODEL=$(json_get "$last" ".model")
  SEED=$(json_get "$last" ".params.seed" 2>/dev/null) || SEED=""
  [ "$SEED" = "null" ] && SEED=""
  local w h
  w=$(json_get "$last" ".params.width" 2>/dev/null) || w=""
  h=$(json_get "$last" ".params.height" 2>/dev/null) || h=""
  GUIDANCE=$(json_get "$last" ".params.guidance_scale" 2>/dev/null) || GUIDANCE=""
  [ "$GUIDANCE" = "null" ] && GUIDANCE=""
  STEPS=$(json_get "$last" ".params.num_inference_steps" 2>/dev/null) || STEPS=""
  [ "$STEPS" = "null" ] && STEPS=""

  echo >&2 "Refine: reloaded prompt='${PROMPT:0:50}...' model=$MODEL seed=$SEED"
}

# ── Parse arguments ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)           PROMPT="$2";           shift 2 ;;
    --model)            MODEL="$2";            shift 2 ;;
    --mode)             MODE="$2";             shift 2 ;;
    --ratio)            RATIO="$2";            shift 2 ;;
    --seed)             SEED="$2";             shift 2 ;;
    --negative-prompt)  NEGATIVE_PROMPT="$2";  shift 2 ;;
    --guidance)         GUIDANCE="$2";         shift 2 ;;
    --steps)            STEPS="$2";            shift 2 ;;
    --scheduler)        SCHEDULER="$2";        shift 2 ;;
    --input-image)      INPUT_IMAGE="$2";      shift 2 ;;
    --output-dir)       OUTPUT_DIR="$2";       shift 2 ;;
    --history)
      if [[ "${2:-}" =~ ^[0-9]+$ ]]; then
        HISTORY_COUNT="$2"; shift 2
      else
        HISTORY_COUNT="5"; shift
      fi
      ;;
    --refine|--revive)  DO_REFINE=true;        shift ;;
    -h|--help)
      sed -n '2,/^$/p' "$0" | sed 's/^# //' | sed 's/^#//'
      exit 0
      ;;
    *)
      echo >&2 "Unknown option: $1"
      exit 1
      ;;
  esac
done

# ── Handle --history ──
if [ -n "$HISTORY_COUNT" ]; then
  history_list "$HISTORY_COUNT"
fi

# ── Handle --refine ──
if [ "$DO_REFINE" = true ]; then
  refine_load
fi

# ── Validate HF_TOKEN ──
if [ -z "${HF_TOKEN:-}" ]; then
  emit_error "token_invalid" "HF_TOKEN environment variable is not set. Get your token at https://huggingface.co/settings/tokens" 0
  exit 1
fi

# ── Validate prompt ──
if [ -z "$PROMPT" ]; then
  emit_error "invalid_input" "Missing --prompt" 0
  exit 1
fi

# ── Resolve dimensions ──
read -r WIDTH HEIGHT <<< "$(ratio_to_wh "$RATIO")"

# ── Filter params by model ──
filter_params "$MODEL"

# ── Validate i2i input ──
if [ "$MODE" = "i2i" ]; then
  if [ -z "$INPUT_IMAGE" ]; then
    emit_error "invalid_input" "i2i mode requires --input-image" 0
    exit 1
  fi
  if [ ! -f "$INPUT_IMAGE" ]; then
    emit_error "invalid_input" "Input image not found: $INPUT_IMAGE" 0
    exit 1
  fi
fi

# ── Prepare output ──
mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
OUTPUT_FILE="$OUTPUT_DIR/${TIMESTAMP}.png"
API_URL="https://router.huggingface.co/hf-inference/models/${MODEL}"

# ── Build request body ──
PARAMS_JSON=$(build_params_json)

if [ "$MODE" = "i2i" ]; then
  IMG_B64=$(base64 < "$INPUT_IMAGE" | tr -d '\n')
  BODY=$(printf '{"inputs":"%s","parameters":%s}' "$IMG_B64" "$PARAMS_JSON")
else
  # Build JSON body safely via python3
  BODY=$(python3 -c "
import json, sys
prompt = sys.stdin.read()
params = json.loads('$PARAMS_JSON')
print(json.dumps({'inputs': prompt, 'parameters': params}))
" <<< "$PROMPT" 2>/dev/null)
fi

# ── Temp files ──
TMPDIR_HF="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_HF"' EXIT
RESP_BODY="$TMPDIR_HF/response"
RESP_HEADERS="$TMPDIR_HF/headers"

# ── Execute API call ──
do_request() {
  local start end http_code
  start=$(ts_ms)

  local curl_exit=0
  http_code=$(curl -s -w '%{http_code}' \
    --max-time "$CURL_TIMEOUT" \
    -H "Authorization: Bearer $HF_TOKEN" \
    -H "Content-Type: application/json" \
    -D "$RESP_HEADERS" \
    -d "$BODY" \
    -o "$RESP_BODY" \
    "$API_URL" 2>/dev/null) || curl_exit=$?

  end=$(ts_ms)
  local dur=$(( end - start ))

  # curl exit 28 = timeout, 6 = DNS fail, 7 = connection refused
  if [ "$curl_exit" -ne 0 ]; then
    if [ "$curl_exit" -eq 28 ]; then
      http_code="TIMEOUT"
    else
      http_code="NETWORK"
    fi
  fi

  echo "$http_code $dur"
}

# First attempt
read -r HTTP_CODE DURATION <<< "$(do_request)"

# Retry on 503
if [ "$HTTP_CODE" = "503" ]; then
  echo >&2 "Model loading (503), retrying in 10s..."
  sleep 10
  read -r HTTP_CODE DURATION <<< "$(do_request)"
fi

# ── Handle response ──
case "$HTTP_CODE" in
  200)
    # Verify we got an image (not JSON error)
    CONTENT_TYPE=$(grep -i "^content-type:" "$RESP_HEADERS" 2>/dev/null | head -1 | tr -d '\r' | awk '{print $2}')
    if echo "$CONTENT_TYPE" | grep -qi "image"; then
      cp "$RESP_BODY" "$OUTPUT_FILE"
      emit_ok "$OUTPUT_FILE" "$MODEL" "$DURATION" "$WIDTH" "$HEIGHT" "${SEED:-null}"
      history_append "$PROMPT" "$MODEL" "$OUTPUT_FILE" "$DURATION"
    else
      # Got JSON error response despite 200
      ERR_MSG=$(cat "$RESP_BODY" 2>/dev/null | head -c 200)
      emit_error "unknown" "Unexpected response: $ERR_MSG" "$DURATION"
      exit 1
    fi
    ;;
  401)
    emit_error "token_invalid" "Invalid or expired HF_TOKEN. Check your token at https://huggingface.co/settings/tokens" "$DURATION"
    exit 1
    ;;
  429)
    emit_error "rate_limited" "Rate limited by Hugging Face API. Please wait and try again." "$DURATION"
    exit 1
    ;;
  503)
    emit_error "model_loading" "Model is still loading after retry. Try again in a few minutes." "$DURATION"
    exit 1
    ;;
  TIMEOUT)
    emit_error "timeout" "Request timed out after ${CURL_TIMEOUT}s" "$DURATION"
    exit 1
    ;;
  NETWORK)
    emit_error "network" "Connection failed to router.huggingface.co" "$DURATION"
    exit 1
    ;;
  *)
    ERR_MSG=$(cat "$RESP_BODY" 2>/dev/null | head -c 200)
    emit_error "unknown" "HTTP $HTTP_CODE: $ERR_MSG" "$DURATION"
    exit 1
    ;;
esac
