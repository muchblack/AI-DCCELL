#!/usr/bin/env bash
# jev.sh — 直連 TypeSafe Jev（System One）評估端點
# 用法:
#   jev.sh <request.json>   送出請求，成功時把回應 JSON 印到 stdout
#   jev.sh --check          有 key 印 jev=on，沒有印 jev=off
#
# key 來源：環境變數 TYPESAFE_API_KEY，沒有就讀 ~/.config/typesafe/.env
# Exit: 0 成功 / 2 沒有 key / 其他 = 呼叫失敗（逾時、非 2xx）
# 呼叫端一律把非 0 當成「這次沒有 Jev 訊號」，不阻擋流程。
# API: https://docs.typesafe.ai/api.md

set -uo pipefail

if [ -z "${TYPESAFE_API_KEY:-}" ] && [ -f "$HOME/.config/typesafe/.env" ]; then
  set -a; . "$HOME/.config/typesafe/.env"; set +a
fi

if [ "${1:-}" = "--check" ]; then
  [ -n "${TYPESAFE_API_KEY:-}" ] && echo jev=on || echo jev=off
  exit 0
fi

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "Usage: jev.sh <request.json> | --check" >&2
  exit 64
fi

[ -n "${TYPESAFE_API_KEY:-}" ] || exit 2

# key 走 process substitution，不出現在指令列（ps 看不到）
curl -sS -f --max-time 10 "${TYPESAFE_BASE_URL:-https://api.typesafe.ai}/v1/systemone" \
  -H @<(printf 'Authorization: Bearer %s\n' "$TYPESAFE_API_KEY") \
  -H "Content-Type: application/json" \
  -d @"$1"
