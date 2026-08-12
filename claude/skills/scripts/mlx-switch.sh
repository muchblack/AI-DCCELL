#!/usr/bin/env bash
# mlx-switch.sh — Switch MLX server on port 8090 between Coder-14B (default, via launchd) and Gemma (VLM, on-demand).
# Reason: M4 Pro 24GB cannot host both at once; boot-time default is Coder-14B for opencode, Gemma is on-demand for VLM tasks.
#
# Usage:
#   mlx-switch.sh coder      Switch 8090 back to Qwen2.5-Coder-14B (mlx_lm.server, via launchd) — boot default
#   mlx-switch.sh gemma      Switch 8090 to Gemma-4-26b (mlx_vlm.server, manual nohup)
#   mlx-switch.sh status     Show which model is currently loaded on 8090
#
# Side effects: unloads/loads ~/Library/LaunchAgents/com.mlx.server.plist; writes /tmp/mlx-gemma.log

set -euo pipefail

PORT=8090
PLIST="$HOME/Library/LaunchAgents/com.mlx.server.plist"
PYTHON="$HOME/.pyenv/versions/3.12.3/bin/python3"
CODER_PATH="$HOME/.cache/huggingface/hub/models--lmstudio-community--Qwen2.5-Coder-14B-Instruct-MLX-4bit/snapshots/4275f1d1fd379c8a5e8cc655c5a57ef03b912a29"
GEMMA_PATH="$HOME/.local/share/mlx-models/gemma-4-26b-a4b-it-4bit"
GEMMA_LOG="/tmp/mlx-gemma.log"
GEMMA_PIDFILE="/tmp/mlx-gemma.pid"

wait_port_free() {
  local timeout=${1:-30} elapsed=0
  while lsof -iTCP:$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do
    [[ $elapsed -ge $timeout ]] && { echo "ERROR: port $PORT still busy after ${timeout}s" >&2; return 1; }
    sleep 1
    elapsed=$((elapsed + 1))
  done
}

wait_port_ready() {
  local timeout=${1:-120} elapsed=0
  while ! curl -sf "http://localhost:$PORT/v1/models" >/dev/null 2>&1; do
    [[ $elapsed -ge $timeout ]] && { echo "ERROR: server on $PORT not responding after ${timeout}s" >&2; return 1; }
    sleep 2
    elapsed=$((elapsed + 2))
  done
}

current_kind() {
  if pgrep -f "mlx_lm.server.*--port $PORT" >/dev/null 2>&1; then
    echo "coder"
  elif pgrep -f "mlx_vlm.server.*--port $PORT" >/dev/null 2>&1; then
    echo "gemma"
  else
    echo "none"
  fi
}

cmd_status() {
  local kind; kind=$(current_kind)
  case $kind in
    coder)
      echo "[8090] Qwen2.5-Coder-14B (mlx_lm.server, via launchd)"
      echo "  pid: $(pgrep -f "mlx_lm.server.*--port $PORT" | head -1)"
      echo "  log: /tmp/mlx-server.log"
      ;;
    gemma)
      echo "[8090] Gemma-4-26b-a4b (mlx_vlm.server, manual nohup)"
      echo "  pid: $(cat $GEMMA_PIDFILE 2>/dev/null || pgrep -f "mlx_vlm.server.*--port $PORT" | head -1)"
      echo "  log: $GEMMA_LOG"
      ;;
    none)
      echo "[8090] no MLX server running"
      ;;
  esac
}

cmd_coder() {
  local kind; kind=$(current_kind)
  if [[ $kind == "coder" ]]; then
    echo "Already on Coder-14B."
    return 0
  fi

  if [[ $kind == "gemma" ]]; then
    echo ">>> Killing Gemma process..."
    if [[ -f $GEMMA_PIDFILE ]]; then
      kill "$(cat $GEMMA_PIDFILE)" 2>/dev/null || true
      rm -f "$GEMMA_PIDFILE"
    fi
    pkill -f "mlx_vlm.server.*--port $PORT" 2>/dev/null || true
    wait_port_free 30
  fi

  echo ">>> Loading launchd plist (launchd starts Coder-14B)..."
  launchctl load "$PLIST"

  echo ">>> Waiting for Coder-14B to be ready (model load takes ~30-60s)..."
  wait_port_ready 120

  echo ">>> Done. Coder-14B is live on port $PORT."
  cmd_status
}

cmd_gemma() {
  local kind; kind=$(current_kind)
  if [[ $kind == "gemma" ]]; then
    echo "Already on Gemma-4-26b."
    return 0
  fi

  echo ">>> Unloading launchd plist (stops Coder, prevents auto-restart)..."
  launchctl unload "$PLIST" 2>/dev/null || true

  echo ">>> Waiting for port $PORT to free..."
  wait_port_free 30

  echo ">>> Starting mlx_vlm.server with Gemma-4-26b..."
  nohup "$PYTHON" -m mlx_vlm.server \
    --model "$GEMMA_PATH" \
    --port $PORT \
    > "$GEMMA_LOG" 2>&1 &
  echo $! > "$GEMMA_PIDFILE"

  echo ">>> Waiting for Gemma to be ready (model load takes ~30-60s)..."
  wait_port_ready 120

  echo ">>> Done. Gemma-4-26b is live on port $PORT."
  cmd_status
}

case "${1:-status}" in
  coder)  cmd_coder ;;
  gemma)  cmd_gemma ;;
  status) cmd_status ;;
  *)
    echo "Usage: $(basename "$0") {coder|gemma|status}" >&2
    exit 1
    ;;
esac
