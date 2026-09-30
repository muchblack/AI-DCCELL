#!/usr/bin/env bash
# 更新外部 skill submodule：抓上游 → 看 diff → 確認 → 檢查 → commit
#
# 用法：
#   scripts/update-vendor.sh                  # 列出所有外部 skill 與目前版本
#   scripts/update-vendor.sh security-audit   # 更新指定的 skill
#   scripts/update-vendor.sh open-seo-advisor
#
# 不會 push；確認沒問題後自行 git push。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

# name|submodule 路徑|SKILL.md 相對於 submodule 的路徑|檢查指令（在 skill 目錄內執行，可為空）
VENDORS=(
    "security-audit|vendor/security-audit-skill|skills/security-audit|node --test validate-findings.test.cjs validate-coverage-ledger.test.cjs"
    "open-seo-advisor|claude/skills/open-seo-advisor|.|"
)

list() {
    for entry in "${VENDORS[@]}"; do
        IFS='|' read -r name path _ _ <<< "${entry}"
        echo "  ${name}  $(git -C "${path}" log -1 --format='%h %cs')  (${path})"
    done
}

find_entry() {
    for entry in "${VENDORS[@]}"; do
        [[ "${entry%%|*}" == "$1" ]] && { echo "${entry}"; return; }
    done
    return 1
}

if [[ $# -eq 0 ]]; then
    echo "外部 skill："
    list
    exit 0
fi

entry="$(find_entry "$1")" || { echo "未知的 skill：$1"; list; exit 1; }
IFS='|' read -r name path skill_rel check <<< "${entry}"

git submodule update --init "${path}"
old="$(git -C "${path}" rev-parse HEAD)"
branch="$(git -C "${path}" remote show origin | sed -n 's/.*HEAD branch: //p')"
git -C "${path}" fetch --quiet origin "${branch}"
new="$(git -C "${path}" rev-parse "origin/${branch}")"

if [[ "${old}" == "${new}" ]]; then
    echo "${name} 已是最新（${old:0:7}）"
    exit 0
fi

echo "=== ${name}: ${old:0:7} → ${new:0:7} ==="
git -C "${path}" log --oneline "${old}..${new}"
echo
git -C "${path}" diff --stat "${old}" "${new}"
echo
echo "=== SKILL.md 差異 ==="
git -C "${path}" diff "${old}" "${new}" -- "${skill_rel}/SKILL.md" || true
echo
read -r -p "套用這次更新？[y/N] " ans
[[ "${ans}" == "y" || "${ans}" == "Y" ]] || { echo "已取消，維持 ${old:0:7}"; exit 0; }

git -C "${path}" checkout --quiet "${new}"

rollback() {
    echo "$1，退回 ${old:0:7}"
    git -C "${path}" checkout --quiet "${old}"
    exit 1
}

[[ -f "${path}/${skill_rel}/SKILL.md" ]] || rollback "找不到 ${path}/${skill_rel}/SKILL.md（上游改了結構）"

if [[ -n "${check}" ]]; then
    echo "=== 檢查：${check} ==="
    (cd "${path}/${skill_rel}" && eval "${check}") || rollback "檢查失敗"
fi

git add "${path}"
git commit -m "更新外部 skill ${name}：${old:0:7} → ${new:0:7}"
echo "已 commit，確認後 git push"
