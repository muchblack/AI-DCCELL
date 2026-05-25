#!/bin/bash
# ask-headless.sh — Headless provider delegation via CLI subprocess.
# Bypasses tmux/wezterm pane, calls provider CLI directly.
#
# Usage: ask-headless.sh <provider> <message> [--timeout <seconds>]
#
# Supported providers: gemini, codex

set -euo pipefail

PROVIDER="${1:-}"
shift || true
TIMEOUT_SEC=3600
MESSAGE_PARTS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout)
            TIMEOUT_SEC="${2:-3600}"
            shift 2
            ;;
        *)
            MESSAGE_PARTS+=("$1")
            shift
            ;;
    esac
done

MESSAGE="${MESSAGE_PARTS[*]}"

if [[ -z "$PROVIDER" || -z "$MESSAGE" ]]; then
    echo "[ERROR] Usage: ask-headless.sh <provider> <message>" >&2
    exit 1
fi

case "$PROVIDER" in
    gemini)
        if ! command -v gemini &>/dev/null; then
            echo "[ERROR] gemini CLI not found in PATH" >&2
            exit 1
        fi
        timeout "$TIMEOUT_SEC" gemini -p "$MESSAGE" 2>/dev/null
        ;;
    codex)
        if ! command -v codex &>/dev/null; then
            echo "[ERROR] codex CLI not found in PATH" >&2
            exit 1
        fi
        WORK_DIR="${CCB_WORK_DIR:-$(pwd)}"
        timeout "$TIMEOUT_SEC" codex exec --full-auto -C "$WORK_DIR" "$MESSAGE" 2>/dev/null
        ;;
    *)
        echo "[ERROR] Headless mode not supported for provider: $PROVIDER" >&2
        echo "[INFO] Supported: gemini, codex" >&2
        exit 1
        ;;
esac
