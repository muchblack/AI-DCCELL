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
#   - cd <host_worktree> && …
#   - git 子指令：add commit diff status log show rev-parse merge-base ls-files
#     （git -C <host_worktree> 視同一般 git，同樣只放行這些子指令）
#   - 還原 composer 造成的資產雜訊：git [-C <host_worktree>] checkout -- public/
#     （逐字比對，checkout 的其他用法照樣停下）
#   - 以 && 串接、且每一段都符合上述規則的指令
# 任一段含 ; & | ` < > $( 就整串停下（防止夾帶指令），容器指令也一樣
# 一律停下（印出 NEEDS_REVIEW）：
#   - 任何 herdr 指令、rm -rf、curl、wget、--output（git diff/log/show 可藉此寫任意檔）
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
WT="${2:?host worktree path}"; WT="${WT%/}"
PREFIX="${3:-}"
LOG="$(dirname "$(dirname "$WT")")/approved-$(basename "$WT").log"

status() {
    herdr agent get "$P" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['agent']['agent_status'])"
}

dangerous() {
    printf '%s' "$1" | grep -qE 'rm -rf|(^|[;&| ])herdr |curl |wget |--output|git( -[cC] [^ ]+)* (push|reset|checkout|switch|worktree|branch|rebase|clean|stash)'
}

# composer install 會改到 public/ 的 Filament 資產空白，brief 要求 worker 還原
restore_public() {
    [[ "$1" =~ ^git\ checkout\ --\ public/?$ ]]
}

# 每一段都不得含 shell 控制字元：; & | ` < > $( 一律視為可能夾帶別的指令
has_shell_meta() {
    [[ "$1" =~ [\;\&\|\`\<\>] || "$1" == *'$('* ]]
}

single_allowed() {
    local cmd="$1"
    has_shell_meta "$cmd" && return 1
    # git -C <本 worktree> 視同一般 git，走同一份子指令白名單；其他 -C 路徑不會符合
    [[ "$cmd" == "git -C $WT/ "* ]] && cmd="git ${cmd#"git -C $WT/ "}"
    [[ "$cmd" == "git -C $WT "* ]] && cmd="git ${cmd#"git -C $WT "}"
    restore_public "$cmd" && return 0
    dangerous "$cmd" && return 1
    [[ -n "$PREFIX" && "$cmd" == "$PREFIX"* ]] && return 0
    printf '%s' "$cmd" | grep -qE '^git (add|commit|diff|status|log|show|rev-parse|merge-base|ls-files)( |$)'
}

# 以 && 拆段，每段各自檢查；cd 只允許切到本 worktree
allowed() {
    local seg
    while IFS= read -r seg || [ -n "$seg" ]; do
        seg="$(printf '%s' "$seg" | sed -E 's/^ +| +$//g')"
        [[ "$seg" == "cd $WT" ]] && continue
        single_allowed "$seg" || return 1
    done < <(printf '%s' "$1" | sed 's/&&/\n/g')
}

# 取最後一個 "  $ " 指令列，並把 codex 折行的續行（直到空行或選項列）併回同一條，
# 否則只會檢查第一行，續行夾帶的內容不經白名單（2026-10-22）
extract_cmd() {
    awk '/^[[:space:]]+\$ /{c=$0; sub(/^[[:space:]]+\$ /,"",c); on=1; next}
         on && /^[[:space:]]*($|›|[0-9]+\.)/{on=0; next}
         on{l=$0; sub(/^[[:space:]]+/,"",l); c=c " " l}
         END{print c}'
}

for _ in $(seq 1 200); do
    st=$(status)
    if [ "$st" != "blocked" ]; then
        herdr agent wait "$P" --timeout 1800000 >/dev/null 2>&1
        st=$(status)
        [ "$st" = "blocked" ] || { echo "STATUS=$st"; exit 0; }
    fi

    cmd=$(herdr agent read "$P" --source recent-unwrapped --lines 25 | extract_cmd)

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
