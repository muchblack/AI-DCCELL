#!/usr/bin/env bash
#
# AI-DCCELL Bootstrap
# 一鍵部署 Claude Code + CCB 多 AI 協作工作流體系
#
# 功能：
#   1. 建立 ~/.claude 下的 symlink（agents, skills, CLAUDE.md）
#   2. 確保 scripts 有執行權限
#   3. 建立 memory 目錄（corrections, telemetry）
#   4. 執行 health-check 驗證環境
#
# 用法：
#   git clone <repo> && cd AI-DCCELL && ./bootstrap.sh
#   或
#   cd agentSkill && ./bootstrap.sh
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/claude"
TARGET_DIR="${HOME}/.claude"

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  AI-DCCELL Bootstrap${NC}"
echo -e "${CYAN}  DG 細胞理論 — AI 工作流自進化升級${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# === 前置檢查 ===
if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo -e "${RED}錯誤：找不到 ${SOURCE_DIR}${NC}"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}錯誤：需要 python3${NC}"
    exit 1
fi

# === Step 1: Symlink 部署 ===
echo -e "${CYAN}[1/4] Symlink 部署${NC}"
mkdir -p "${TARGET_DIR}"

deploy_link() {
    local name="$1"
    local src="${SOURCE_DIR}/${name}"
    local dst="${TARGET_DIR}/${name}"

    if [[ ! -e "${src}" ]]; then
        echo -e "  ${YELLOW}跳過：${name}（來源不存在）${NC}"
        return
    fi

    if [[ -L "${dst}" ]]; then
        local current
        current="$(readlink "${dst}")"
        if [[ "${current}" == "${src}" ]]; then
            echo -e "  ${GREEN}✓ ${name}（已正確）${NC}"
            return
        fi
        rm "${dst}"
    elif [[ -e "${dst}" ]]; then
        local backup
        backup="${TARGET_DIR}/backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "${backup}"
        mv "${dst}" "${backup}/${name}"
        echo -e "  ${YELLOW}備份：${name} → ${backup}/${NC}"
    fi

    ln -s "${src}" "${dst}"
    echo -e "  ${GREEN}✓ ${name} → ${src}${NC}"
}

deploy_link "agents"
deploy_link "skills"
deploy_link "CLAUDE.md"
echo ""

# === Step 1b: Codex Symlink 部署 ===
echo -e "${CYAN}[1b/4] Codex 部署${NC}"
CODEX_DIR="${HOME}/.codex"
CODEX_SRC="${SCRIPT_DIR}/codex/AGENTS.md"
CODEX_DST="${CODEX_DIR}/AGENTS.md"
mkdir -p "${CODEX_DIR}"

if [[ -L "${CODEX_DST}" ]]; then
    current="$(readlink "${CODEX_DST}")"
    if [[ "${current}" == "${CODEX_SRC}" ]]; then
        echo -e "  ${GREEN}✓ AGENTS.md（已正確）${NC}"
    else
        rm "${CODEX_DST}"
        ln -s "${CODEX_SRC}" "${CODEX_DST}"
        echo -e "  ${GREEN}✓ AGENTS.md → ${CODEX_SRC}${NC}"
    fi
elif [[ -e "${CODEX_DST}" ]]; then
    mv "${CODEX_DST}" "${CODEX_DST}.bak.$(date +%Y%m%d-%H%M%S)"
    echo -e "  ${YELLOW}備份：AGENTS.md${NC}"
    ln -s "${CODEX_SRC}" "${CODEX_DST}"
    echo -e "  ${GREEN}✓ AGENTS.md → ${CODEX_SRC}${NC}"
else
    ln -s "${CODEX_SRC}" "${CODEX_DST}"
    echo -e "  ${GREEN}✓ AGENTS.md → ${CODEX_SRC}${NC}"
fi
echo ""

# === Step 1c: Gemini Symlink 部署 ===
echo -e "${CYAN}[1c/4] Gemini 部署${NC}"
GEMINI_DIR="${HOME}/.gemini"
GEMINI_SRC="${SCRIPT_DIR}/.gemini/GEMINI.md"
GEMINI_DST="${GEMINI_DIR}/GEMINI.md"
mkdir -p "${GEMINI_DIR}"

if [[ -L "${GEMINI_DST}" ]]; then
    current="$(readlink "${GEMINI_DST}")"
    if [[ "${current}" == "${GEMINI_SRC}" ]]; then
        echo -e "  ${GREEN}✓ GEMINI.md（已正確）${NC}"
    else
        rm "${GEMINI_DST}"
        ln -s "${GEMINI_SRC}" "${GEMINI_DST}"
        echo -e "  ${GREEN}✓ GEMINI.md → ${GEMINI_SRC}${NC}"
    fi
elif [[ -e "${GEMINI_DST}" ]]; then
    mv "${GEMINI_DST}" "${GEMINI_DST}.bak.$(date +%Y%m%d-%H%M%S)"
    echo -e "  ${YELLOW}備份：GEMINI.md${NC}"
    ln -s "${GEMINI_SRC}" "${GEMINI_DST}"
    echo -e "  ${GREEN}✓ GEMINI.md → ${GEMINI_SRC}${NC}"
else
    ln -s "${GEMINI_SRC}" "${GEMINI_DST}"
    echo -e "  ${GREEN}✓ GEMINI.md → ${GEMINI_SRC}${NC}"
fi
echo ""

# === Step 2: Scripts 執行權限 ===
echo -e "${CYAN}[2/4] Scripts 執行權限${NC}"
SCRIPTS_DIR="${SOURCE_DIR}/skills/scripts"
if [[ -d "${SCRIPTS_DIR}" ]]; then
    chmod +x "${SCRIPTS_DIR}"/*.sh 2>/dev/null || true
    count=$(ls "${SCRIPTS_DIR}"/*.sh 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  ${GREEN}✓ ${count} 個腳本已設定執行權限${NC}"
else
    echo -e "  ${YELLOW}跳過：scripts 目錄不存在${NC}"
fi
echo ""

# === Step 3: Memory 目錄 ===
echo -e "${CYAN}[3/4] Memory 目錄初始化${NC}"
MEMORY_DIR="${SOURCE_DIR}/skills/memory"
mkdir -p "${MEMORY_DIR}"
touch "${MEMORY_DIR}/corrections.jsonl" 2>/dev/null || true
touch "${MEMORY_DIR}/telemetry.jsonl" 2>/dev/null || true
echo -e "  ${GREEN}✓ memory/ 目錄就緒${NC}"
echo ""

# === Step 4: Health Check ===
echo -e "${CYAN}[4/4] 環境驗證${NC}"
HC="${SCRIPTS_DIR}/health-check.sh"
if [[ -x "${HC}" ]]; then
    result=$(bash "${HC}" mlx ollama 2>/dev/null) || result="{}"
    mlx_status=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('mlx',{}).get('status','skip'))" 2>/dev/null || echo "skip")
    ollama_status=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ollama',{}).get('status','skip'))" 2>/dev/null || echo "skip")

    [[ "$mlx_status" == "ok" ]] && echo -e "  ${GREEN}✓ MLX: ok${NC}" || echo -e "  ${YELLOW}⚠ MLX: ${mlx_status}${NC}"
    [[ "$ollama_status" == "ok" ]] && echo -e "  ${GREEN}✓ Ollama: ok${NC}" || echo -e "  ${YELLOW}⚠ Ollama: ${ollama_status}${NC}"
else
    echo -e "  ${YELLOW}跳過：health-check.sh 不存在${NC}"
fi

# === 驗證統計 ===
echo ""
AGENT_COUNT=$(find -L "${TARGET_DIR}/agents" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
SKILL_COUNT=$(find -L "${TARGET_DIR}/skills" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
SCRIPT_COUNT=$(ls "${SCRIPTS_DIR}"/*.sh 2>/dev/null | wc -l | tr -d ' ')

CODEX_OK="✗"
[[ -L "${CODEX_DST}" ]] && CODEX_OK="✓"
GEMINI_OK="✗"
[[ -L "${GEMINI_DST}" ]] && GEMINI_OK="✓"

echo -e "${CYAN}================================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""
echo "  Agents:  ${AGENT_COUNT} 個"
echo "  Skills:  ${SKILL_COUNT} 個"
echo "  Scripts: ${SCRIPT_COUNT} 個"
echo "  Codex:   ${CODEX_OK} AGENTS.md"
echo "  Gemini:  ${GEMINI_OK} GEMINI.md"
echo ""
echo "  提示："
echo "    - 修改 claude/ 下的內容，所有專案立即生效"
echo "    - 移除部署：rm ~/.claude/{agents,skills,CLAUDE.md}"
echo "    - 查看效能：bash ~/.claude/skills/scripts/telemetry-report.sh"
echo ""
