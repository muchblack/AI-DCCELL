#!/usr/bin/env bash
# route-task.sh — 智慧模型路由決策
# 根據任務特徵 + provider 可用性 + 歷史表現，選擇最佳 AI provider。
#
# 用法: route-task.sh --type <reasoning|coding> --complexity <simple|medium|complex> \
#                      --lines <estimated_lines> --files <file_count> \
#                      --lang <language> --security <true|false>
#
# 輸出: JSON { provider, reason, fallback }
#
# Provider 選項:
#   claude  — 直接寫（最強推理，但最貴）
#   ollama  — LAN GPU 寫碼（中等品質，免費）
#   mlx     — 本地推理/分析（快速，免費）

set -euo pipefail

# ── 預設值 ──
TASK_TYPE="coding"
COMPLEXITY="medium"
EST_LINES=50
FILE_COUNT=1
LANGUAGE=""
SECURITY="false"
CORRECTIONS_FILE="$HOME/.claude/skills/memory/corrections.jsonl"

# ── 解析參數 ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)       TASK_TYPE="$2";   shift 2 ;;
    --complexity) COMPLEXITY="$2";  shift 2 ;;
    --lines)      EST_LINES="$2";   shift 2 ;;
    --files)      FILE_COUNT="$2";  shift 2 ;;
    --lang)       LANGUAGE="$2";    shift 2 ;;
    --security)   SECURITY="$2";    shift 2 ;;
    *) shift ;;
  esac
done

# ── Health check（只檢查需要的 provider） ──
HC_SCRIPT="$HOME/.claude/skills/scripts/health-check.sh"
OLLAMA_OK=false
MLX_OK=false

if [[ -x "$HC_SCRIPT" ]]; then
  hc_result=$(bash "$HC_SCRIPT" mlx ollama 2>/dev/null) || hc_result='{}'

  if command -v jq >/dev/null 2>&1; then
    [[ $(echo "$hc_result" | jq -r '.ollama.status // "down"') == "ok" ]] && OLLAMA_OK=true
    [[ $(echo "$hc_result" | jq -r '.mlx.status // "down"') == "ok" ]] && MLX_OK=true
  else
    echo "$hc_result" | grep -q '"ollama":{"status":"ok"' && OLLAMA_OK=true
    echo "$hc_result" | grep -q '"mlx":{"status":"ok"' && MLX_OK=true
  fi
fi

# ── 查歷史 takeover 率 ──
TAKEOVER_RATE=0
if [[ -n "$LANGUAGE" && -f "$CORRECTIONS_FILE" ]] && command -v jq >/dev/null 2>&1; then
  # 取該語言最近 10 筆 code corrections 的 takeover 率
  TAKEOVER_RATE=$(tail -20 "$CORRECTIONS_FILE" 2>/dev/null | \
    jq -s --arg lang "$LANGUAGE" '
      [.[] | select(.language == $lang and .artifact_type == "code")] | last(10) |
      if length == 0 then 0
      else ([.[] | select(.takeover == true)] | length) / length
      end
    ' 2>/dev/null) || TAKEOVER_RATE=0
fi

# ── 路由決策 ──
emit() {
  local provider="$1" reason="$2" fallback="${3:-claude}"
  printf '{"provider":"%s","reason":"%s","fallback":"%s"}\n' "$provider" "$reason" "$fallback"
  exit 0
}

# Rule 1: 安全敏感 → Claude（不信任弱模型）
if [[ "$SECURITY" == "true" ]]; then
  emit "claude" "security-sensitive"
fi

# Rule 2: 推理/分析類 → MLX 優先
if [[ "$TASK_TYPE" == "reasoning" ]]; then
  if $MLX_OK; then
    emit "mlx" "local-reasoning" "claude"
  else
    emit "claude" "mlx-down-fallback"
  fi
fi

# Rule 3: 小修改（<20 行 + 單檔案）→ Claude 直接（省往返開銷）
if [[ "$EST_LINES" -lt 20 && "$FILE_COUNT" -le 1 ]]; then
  emit "claude" "small-edit-overhead"
fi

# Rule 4: 歷史 takeover 率 > 40% → Claude（該語言 Ollama 品質不可靠）
if command -v bc >/dev/null 2>&1; then
  high_takeover=$(echo "$TAKEOVER_RATE > 0.4" | bc -l 2>/dev/null) || high_takeover=0
  if [[ "$high_takeover" == "1" ]]; then
    emit "claude" "high-takeover-rate-${LANGUAGE}"
  fi
fi

# Rule 5: 複雜架構設計 → Claude（需要最強推理）
if [[ "$COMPLEXITY" == "complex" && "$TASK_TYPE" == "coding" && "$EST_LINES" -gt 200 ]]; then
  if $OLLAMA_OK; then
    # 大型 complex 仍用 Ollama，但提醒拆分
    emit "ollama" "complex-large-split-recommended" "claude"
  else
    emit "claude" "ollama-down-fallback"
  fi
fi

# Rule 6: 中等以上 → Ollama（標準寫碼路徑）
if [[ "$EST_LINES" -ge 20 ]]; then
  if $OLLAMA_OK; then
    emit "ollama" "standard-coding" "claude"
  else
    emit "claude" "ollama-down-fallback"
  fi
fi

# Rule 7: 兜底
emit "claude" "fallback"
