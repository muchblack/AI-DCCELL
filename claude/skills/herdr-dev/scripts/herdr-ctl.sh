#!/usr/bin/env bash
# herdr-dev 後端 adapter：同一組動詞同時支援 TUI 版 herdr（`herdr agent …`）
# 和 Herdr desktop 的 herdr-core（`hc …`）。herdr-dev 的 SKILL.md、flow.md、
# 腳本只呼叫這裡的動詞；整個 skill 只有這支檔案直接下 herdr／hc 指令。
#
# 後端判斷（依序）：
#   1. HERDR_BACKEND=hc|tui        手動覆寫
#   2. 有 HC_TERMINAL_ID            → hc（在 Herdr desktop 的 pane 裡）
#   3. `herdr agent list` 跑得起來  → tui
#   4. 都不行                       → 印錯誤，exit 3
#
# 用法（<id>：TUI 是 pane id，例如 w2:p2；hc 是 t4，遠端是 machine/t4）：
#   herdr-ctl.sh backend                  印 tui 或 hc
#   herdr-ctl.sh list                     每行 <id>\t<agent>\t<status>\t<cwd>
#                                         agent 名稱正規化：antigravity→agy、claude-code→claude
#   herdr-ctl.sh status <id>              印 idle|working|blocked|done|unknown 其中一個
#                                         （hc 的 error 視為 blocked：都需要人看畫面）
#   herdr-ctl.sh prompt <id> <text>       貼上並送出，不等待；stdout 不印東西
#                                         （pane 卡在 blocked 時兩個後端都會拒絕，exit 非 0）
#   herdr-ctl.sh wait <id> <秒>           等到不是 working；逾時（仍 working）exit 124
#   herdr-ctl.sh read <id> <行數>         印出最近 N 行畫面（去掉畫面底部的空白行）
#   herdr-ctl.sh keys <id> <key>...       送按鍵：enter、esc、y、down、ctrl+c…
#   herdr-ctl.sh start <agent> <cwd> [--pane <id>] [-- <agent 參數>...]
#                                         開 agent，印出它的 id
#                                         hc：新開終端機（hc run --bg --cwd），codex 自動加 --no-daemon
#                                         tui：必須給 --pane（一個停在 shell prompt 的既有 pane，
#                                              不是的話 exit 2、什麼都不送），
#                                              先 cd 到 <cwd> 再啟動 agent
#
# 測試：bash scripts/test-herdr-ctl.sh

set -uo pipefail

die() { echo "herdr-ctl: $*" >&2; exit "${2:-2}"; }

backend() {
    case "${HERDR_BACKEND:-}" in
        hc|tui) echo "$HERDR_BACKEND"; return ;;
        "") ;;
        *) die "HERDR_BACKEND 只能是 hc 或 tui（目前是 '$HERDR_BACKEND'）" 3 ;;
    esac
    if [ -n "${HC_TERMINAL_ID:-}" ]; then echo hc; return; fi
    if herdr agent list >/dev/null 2>&1; then echo tui; return; fi
    die "找不到 herdr 後端：沒有 HC_TERMINAL_ID，herdr agent list 也跑不起來" 3
}

# stdin 的 JSON → 依 $1 指定的 python 表達式印出結果；解析失敗印空字串
jq_py() { python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
$1"; }

norm_status() {
    case "$1" in
        idle|working|blocked|done) echo "$1" ;;
        error) echo blocked ;;
        *) echo unknown ;;
    esac
}

B="$(backend)" || exit $?
verb="${1:-}"; [ $# -gt 0 ] && shift

case "$B:$verb" in
    *:backend) echo "$B" ;;

    tui:list)
        herdr agent list | jq_py '
for a in d["result"]["agents"]:
    print("\t".join([a.get("pane_id",""), a.get("agent") or "-", a.get("agent_status") or "unknown", a.get("cwd","")]))' ;;
    hc:list)
        hc ls --json | jq_py '
m={"antigravity":"agy","claude-code":"claude"}
for t in d["terminals"]:
    ag=t.get("agent") or "-"
    print("\t".join([t.get("address",""), m.get(ag,ag), t.get("status") or "unknown", t.get("cwd","")]))' ;;

    tui:status)
        norm_status "$(herdr agent get "${1:?id}" 2>/dev/null | jq_py 'print(d["result"]["agent"].get("agent_status",""))')" ;;
    hc:status)
        norm_status "$(hc get "${1:?id}" --json 2>/dev/null | jq_py 'print((d.get("status") or {}).get("state",""))')" ;;

    tui:prompt) herdr agent prompt "${1:?id}" "${2:?text}" >/dev/null ;;
    hc:prompt)  hc send "${1:?id}" "${2:?text}" >/dev/null ;;

    *:wait)
        id="${1:?id}"; secs="${2:?seconds}"
        if [ "$B" = tui ]; then
            # TUI 逾時（或任何失敗）exit 非 0
            herdr agent wait "$id" --timeout "$((secs * 1000))" >/dev/null 2>&1 || exit 124
        else
            # hc 逾時也是 exit 0：看 JSON。reason=timeout，或因為有訊息給呼叫者而提早結束
            # （status 仍是 working）都算沒等到
            r="$(hc wait "$id" --timeout "$secs" --json 2>/dev/null | jq_py '
print("busy" if d.get("reason")=="timeout" or d.get("status")=="working" else "ok")')"
            [ "$r" = ok ] || exit 124
        fi
        exit 0 ;;

    *:read)
        id="${1:?id}"; n="${2:?lines}"
        if [ "$B" = tui ]; then
            herdr agent read "$id" --source recent-unwrapped --lines "$n"
        else
            # hc 的 --lines 是「畫面上方再往回看幾行」，畫面本身另外整頁印出；
            # 去掉底部空白行後取最後 N 行，對齊 TUI recent 的語意
            # 畫面忙碌時 hc 會在最後補一行「[hc] incomplete: …」，不是畫面內容，濾掉
            hc read "$id" --lines "$n" | awk '/^\[hc\] incomplete/{next} {a[++k]=$0} NF{last=k} END{for(i=1;i<=last;i++) print a[i]}' | tail -n "$n"
        fi ;;

    tui:keys) herdr pane send-keys "${1:?id}" "${@:2}" >/dev/null ;;
    hc:keys)  hc keys "${1:?id}" "${@:2}" >/dev/null ;;

    *:start)
        agent="${1:?agent}"; cwd="${2:?cwd}"; shift 2; pane=""
        [ "${1:-}" = --pane ] && { pane="${2:?pane id}"; shift 2; }
        [ "${1:-}" = -- ] && shift
        args=("$@")
        if [ "$B" = tui ]; then
            [ -n "$pane" ] || die "tui 後端的 start 需要 --pane <既有 pane id>"
            # 前景行程群組就是 shell 本身才算停在 prompt；否則 cd 會被當成 prompt 打進還在跑的 agent
            at_shell="$(herdr pane process-info --pane "$pane" 2>/dev/null | jq_py '
i=d["result"]["process_info"]; print("yes" if i["shell_pid"]==i["foreground_process_group_id"] else "no")')"
            [ "$at_shell" = yes ] || die "pane $pane 不在 shell prompt（前景還有程式在跑），先結束它再 start"
            herdr pane run "$pane" "cd $(printf '%q' "$cwd")" >/dev/null || exit $?
            [ ${#args[@]} -gt 0 ] && args=(-- "${args[@]}")   # 沒參數就不帶 --，跟改版前的呼叫一模一樣
            herdr agent start "$agent" --kind "$agent" --pane "$pane" "${args[@]}" >/dev/null || exit $?
            echo "$pane"
        else
            # herdr-core 的 PATH 不一定有 ~/.local/bin（2026-11-04 實測 spawn_failed），
            # 先在呼叫端解析成絕對路徑
            prog=("$(command -v "$agent" || echo "$agent")")
            [ "$agent" = codex ] && prog+=(--no-daemon); prog+=("${args[@]}")
            # --outlive-parent：worker／reviewer 要活得比 main 久，跟 TUI pane 一樣
            # --no-notify：子終端機的狀態變化不要打字進 main，main 只靠 wait-result.sh 叫醒
            hc run --bg --outlive-parent --no-notify --cwd "$cwd" --json "${prog[@]}" \
                | jq_py 'print(d["address"])'
        fi ;;

    *) die "未知動詞 '$verb'。可用：backend list status prompt wait read keys start" ;;
esac
