#!/usr/bin/env bash
# herdr-dev 自動批准迴圈：只放行白名單內的指令，其他一律停下交給 main 判斷。
#
# 用法：
#   approve-loop.sh <pane> <host_worktree> [<container_prefix>]
#
#   pane              worker／reviewer 的 herdr pane id，例如 w2:p2
#   host_worktree     該 pane 的 worktree 絕對路徑（host 端）
#   container_prefix  容器指令的固定前綴（逐字比對，不是 regex），例如
#                     "podman exec -w /var/www/html/proj/.herdr-dev/worktrees/worker-vin-86 cashier-php "
#                     省略則不放行任何容器指令
#
# 放行：
#   - 以 container_prefix 開頭的指令
#   - git -C <host_worktree> …、cd <host_worktree> && git …
#   - 一般 git 子指令：add commit diff status log show rev-parse merge-base ls-files
# 一律停下（印出 NEEDS_REVIEW）：
#   - 任何 herdr 指令、rm -rf、curl、wget
#   - git push／reset／checkout／switch／worktree／branch／rebase／clean／stash
#   - 不在白名單內的其他指令
#
# 結束時只印一行：STATUS=<idle|done|…>、NEEDS_REVIEW: <指令> 或 LOOP_LIMIT。
# 每次放行記錄在 <project>/.herdr-dev/approved-<worktree 名稱>.log。
#
# 以 run_in_background 執行；搭配不帶 --wait 的 `herdr agent prompt` 使用，
# 由本腳本負責等待。只在 codex 的批准對話框格式上驗證過（指令列以 "  $ " 開頭）；
# 其他 provider 的對話框格式不同時，會停在 NEEDS_REVIEW，不會誤放行。

set -u
P="${1:?pane}"
WT="${2:?host worktree path}"
PREFIX="${3:-}"
LOG="$(dirname "$(dirname "$WT")")/approved-$(basename "$WT").log"

status() {
    herdr agent get "$P" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['agent']['agent_status'])"
}

dangerous() {
    printf '%s' "$1" | grep -qE 'rm -rf|(^|[;&| ])herdr |curl |wget |git (push|reset|checkout|switch|worktree|branch|rebase|clean|stash)'
}

allowed() {
    local cmd="$1"
    dangerous "$cmd" && return 1
    [[ -n "$PREFIX" && "$cmd" == "$PREFIX"* ]] && return 0
    [[ "$cmd" == "git -C $WT "* || "$cmd" == "cd $WT && git "* ]] && return 0
    printf '%s' "$cmd" | grep -qE '^git (add|commit|diff|status|log|show|rev-parse|merge-base|ls-files)( |$)'
}

for _ in $(seq 1 200); do
    st=$(status)
    if [ "$st" != "blocked" ]; then
        herdr agent wait "$P" --timeout 1800000 >/dev/null 2>&1
        st=$(status)
        [ "$st" = "blocked" ] || { echo "STATUS=$st"; exit 0; }
    fi

    cmd=$(herdr agent read "$P" --source recent-unwrapped --lines 25 \
        | grep -E '^\s+\$ ' | tail -1 | sed -E 's/^\s+\$ //')

    if [ -n "$cmd" ] && allowed "$cmd"; then
        herdr pane send-keys "$P" enter >/dev/null
        echo "$(date +%T) approved: ${cmd:0:160}" >> "$LOG"
        sleep 2
    else
        echo "NEEDS_REVIEW: ${cmd:-<no command line found>}"
        exit 0
    fi
done
echo "LOOP_LIMIT"
