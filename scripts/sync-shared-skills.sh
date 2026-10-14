#!/usr/bin/env bash
# 依 shared-skills.txt 把 claude/skills/ 下的 skill 以 symlink 掛給 Codex 與 Antigravity（agy）
#
# 用法：scripts/sync-shared-skills.sh
#
# - 只動「指向本 repo 的 symlink」：清單外的會被移除，清單內的建立或修正
# - 目標位置已有實體目錄（CLI 自己的版本）時跳過，不覆蓋
# - ~/.codex/skills 裡指向 claude/skills 的舊 symlink 一併清掉，改由 ~/.agents/skills 提供，避免重複載入

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="${ROOT}/shared-skills.txt"
SRC="${ROOT}/claude/skills"

# CLI 名稱|skill 目錄
TARGETS=(
    "codex|${HOME}/.agents/skills"
    "agy|${HOME}/.gemini/config/skills"
)

# 清單中要掛給 $1 的 skill 名稱
wanted() {
    sed 's/#.*//' "${MANIFEST}" | while read -r name flags; do
        [[ -z "${name}" ]] && continue
        [[ " ${flags} " == *" !$1 "* ]] && continue
        echo "${name}"
    done
}

# 移除 $1 目錄中指向 $2 前綴、但不在 $3（換行分隔清單）中的 symlink
prune() {
    local dir="$1" prefix="$2" keep="$3" link
    for link in "${dir}"/*; do
        [[ -L "${link}" ]] || continue
        [[ "$(readlink "${link}")" == "${prefix}"/* ]] || continue
        grep -qxF "$(basename "${link}")" <<< "${keep}" && continue
        rm "${link}"
        echo "  - $(basename "${link}")"
    done
}

for target in "${TARGETS[@]}"; do
    IFS='|' read -r cli dir <<< "${target}"
    echo "[${cli}] ${dir}"
    mkdir -p "${dir}"
    names="$(wanted "${cli}")"

    prune "${dir}" "${ROOT}" "${names}"

    while read -r name; do
        src="${SRC}/${name}"
        dst="${dir}/${name}"
        if [[ ! -f "${src}/SKILL.md" ]]; then
            echo "  ! ${name}：找不到 ${src}/SKILL.md"
        elif [[ -L "${dst}" && "$(readlink "${dst}")" == "${src}" ]]; then
            :
        elif [[ -e "${dst}" && ! -L "${dst}" ]]; then
            echo "  ! ${name}：已有實體目錄，跳過"
        else
            ln -sfn "${src}" "${dst}"
            echo "  + ${name}"
        fi
    done <<< "${names}"

    echo "  共 $(find "${dir}" -maxdepth 1 -type l | wc -l | tr -d ' ') 個 symlink"
done

echo "[codex] 清理 ~/.codex/skills 舊的重複連結"
prune "${HOME}/.codex/skills" "${SRC}" ""
