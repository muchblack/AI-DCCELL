#!/usr/bin/env bash
#
# Claude Code 配置一鍵部署腳本
# 將 agentSkill/claude/ 下的 agents、skills、CLAUDE.md
# 以 symlink 方式連結到 ~/.claude/
#
# 用法：cd agentSkill && ./setup.sh
#

set -euo pipefail

# === 顏色定義 ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# === 路徑設定 ===
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/claude"
TARGET_DIR="${HOME}/.claude"
BACKUP_DIR="${TARGET_DIR}/backup-$(date +%Y%m%d-%H%M%S)"

# === 檢查 source 目錄存在 ===
if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo -e "${RED}錯誤：找不到 ${SOURCE_DIR} 目錄${NC}"
    echo "請確認在 agentSkill/ 目錄下執行此腳本"
    exit 1
fi

# === 建立 ~/.claude/ ===
mkdir -p "${TARGET_DIR}"

echo "================================================"
echo "  Claude Code 配置部署"
echo "================================================"
echo ""
echo "來源：${SOURCE_DIR}"
echo "目標：${TARGET_DIR}"
echo ""

# === 部署函數 ===
deploy_item() {
    local name="$1"
    local source_path="${SOURCE_DIR}/${name}"
    local target_path="${TARGET_DIR}/${name}"

    if [[ ! -e "${source_path}" ]]; then
        echo -e "${YELLOW}跳過：${name}（來源不存在）${NC}"
        return
    fi

    # 若目標已是正確的 symlink，跳過
    if [[ -L "${target_path}" ]]; then
        local current_target
        current_target="$(readlink "${target_path}")"
        if [[ "${current_target}" == "${source_path}" ]]; then
            echo -e "${GREEN}✓ ${name}（symlink 已正確）${NC}"
            return
        fi
        # symlink 指向錯誤位置，移到備份
        echo -e "${YELLOW}  備份舊 symlink：${name}${NC}"
        mkdir -p "${BACKUP_DIR}"
        mv "${target_path}" "${BACKUP_DIR}/${name}.old-link"
    elif [[ -e "${target_path}" ]]; then
        # 真實檔案/目錄存在，備份
        echo -e "${YELLOW}  備份：${name} → ${BACKUP_DIR}/${name}${NC}"
        mkdir -p "${BACKUP_DIR}"
        mv "${target_path}" "${BACKUP_DIR}/${name}"
    fi

    # 建立 symlink
    ln -s "${source_path}" "${target_path}"
    echo -e "${GREEN}✓ ${name} → ${source_path}${NC}"
}

# === 執行部署 ===
echo "--- 部署中 ---"
echo ""

deploy_item "agents"
deploy_item "skills"
deploy_item "CLAUDE.md"

echo ""

# === 驗證 ===
echo "--- 驗證 ---"
echo ""

AGENT_COUNT=$(find "${TARGET_DIR}/agents" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
SKILL_COUNT=$(find "${TARGET_DIR}/skills" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
CLAUDE_MD_OK="否"
[[ -f "${TARGET_DIR}/CLAUDE.md" ]] && CLAUDE_MD_OK="是"

echo "  Agents：${AGENT_COUNT} 個"
echo "  Skills：${SKILL_COUNT} 個目錄"
echo "  CLAUDE.md：${CLAUDE_MD_OK}"

if [[ -d "${BACKUP_DIR}" ]]; then
    echo ""
    echo -e "${YELLOW}舊檔案已備份至：${BACKUP_DIR}${NC}"
fi

echo ""
echo "================================================"
echo -e "${GREEN}  部署完成！開啟 Claude Code 即可使用。${NC}"
echo "================================================"
echo ""
echo "提示："
echo "  - 在 agentSkill/claude/ 中修改 agent/skill，所有專案立即生效"
echo "  - CLAUDE.md 部署為全域配置（~/.claude/CLAUDE.md）"
echo "  - 專案級 CLAUDE.md 範本在 agentSkill/project-template/"
echo "  - 移除部署：rm ~/.claude/agents ~/.claude/skills ~/.claude/CLAUDE.md"
