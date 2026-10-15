#!/usr/bin/env bash
# herdr-dev 結果等待：只在「結果檔第一行等於本次 dispatch_id 且 pane 已停下」時才返回。
#
# 為什麼：agy／codex 常在還沒做完時回報 done／idle，approve-loop 也會在
# pane 短暫停下時提早退出。每次提早返回都會喚醒 main 讀一整輪脈絡，
# 只為了得出「還在跑」。本腳本把這些假完成吞在背景裡，main 只被叫醒一次。
#
# 用法：
#   wait-result.sh <pane> <result_file> <dispatch_id> [--approve <host_worktree> [<container_prefix>]]
#
#   pane          worker／reviewer 的 herdr pane id，例如 wJ:p5
#   result_file   report.md／verdict.md／brief-verdict.md 的路徑
#   dispatch_id   本次 brief 第一行的 id，例如 vin-129-4
#   --approve     worker 用：每輪改跑 approve-loop.sh（自動批准白名單指令）
#
# 結束時只印一行：
#   RESULT_READY             結果檔已是本次 dispatch_id，pane 已停下
#   NEEDS_REVIEW: <指令>      approve-loop 遇到白名單外的指令，交給 main 判斷
#   BLOCKED                  pane 卡在 blocked（未用 --approve 時），交給 main 看畫面
#   SETTLED_NO_RESULT        pane 已停下約 2 分鐘仍沒有本次結果檔：視為死掉的工作
#   TIMEOUT                  超過 WAIT_RESULT_MAX_SECONDS（預設 5400 秒）
#
# 以 run_in_background 執行。測試：bash scripts/test-wait-result.sh

set -u
P="${1:?pane}"
FILE="${2:?result file}"
ID="${3:?dispatch_id}"
shift 3
APPROVE_WT=""; APPROVE_PREFIX=""
if [ "${1:-}" = "--approve" ]; then
  APPROVE_WT="${2:?host worktree}"; APPROVE_PREFIX="${3:-}"
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
MAX="${WAIT_RESULT_MAX_SECONDS:-5400}"
IDLE_LIMIT="${WAIT_RESULT_IDLE_CHECKS:-6}"
NAP="${WAIT_RESULT_NAP:-20}"
START=$(date +%s)
idle_checks=0

status() { herdr agent get "$P" 2>/dev/null | grep -o '"agent_status":"[a-z_]*"' | head -1 | cut -d'"' -f4; }
ready() { [ "$(head -1 "$FILE" 2>/dev/null)" = "dispatch_id: $ID" ]; }

while :; do
  s="$(status)"
  case "$s" in
    idle|done)
      if ready; then echo RESULT_READY; exit 0; fi
      idle_checks=$((idle_checks + 1))
      [ "$idle_checks" -ge "$IDLE_LIMIT" ] && { echo SETTLED_NO_RESULT; exit 0; }
      sleep "$NAP"   # agent wait 對已停下的 pane 會立刻返回，這裡必須睡，否則空轉
      ;;
    blocked)
      idle_checks=0
      if [ -z "$APPROVE_WT" ]; then echo BLOCKED; exit 0; fi
      ;;
    *) idle_checks=0 ;;
  esac

  [ $(( $(date +%s) - START )) -ge "$MAX" ] && { echo TIMEOUT; exit 0; }

  if [ -n "$APPROVE_WT" ]; then
    out="$("$HERE/approve-loop.sh" "$P" "$APPROVE_WT" "$APPROVE_PREFIX" 2>&1 | tail -1)"
    case "$out" in NEEDS_REVIEW*) echo "$out"; exit 0 ;; esac
  elif [ "$s" != idle ] && [ "$s" != done ]; then
    herdr agent wait "$P" --timeout 60000 >/dev/null 2>&1 || sleep "$NAP"
  fi
done
