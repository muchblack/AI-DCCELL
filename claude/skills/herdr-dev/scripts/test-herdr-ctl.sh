#!/usr/bin/env bash
# herdr-ctl.sh 的回歸測試：用假的 herdr／hc 放在 PATH 前面，兩個後端的每個動詞都測。
#   bash scripts/test-herdr-ctl.sh
# 假指令把收到的參數記進 $T/calls，並依 $T/state 回應狀態。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CTL="$HERE/herdr-ctl.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
fail=0

cat > "$TMP/bin/herdr" <<'EOF'
#!/usr/bin/env bash
echo "herdr $*" >> "$T/calls"
s=$(cat "$T/state" 2>/dev/null || echo idle)
case "$1 $2" in
  "agent list") [ -f "$T/tui_down" ] && exit 1
    echo '{"result":{"agents":[{"pane_id":"w2:p2","agent":"codex","agent_status":"working","cwd":"/p"},{"pane_id":"w2:p3","agent":"agy","agent_status":"done","cwd":"/p"}]}}' ;;
  "agent get") echo "{\"result\":{\"agent\":{\"agent_status\":\"$s\"}}}" ;;
  "agent read") printf 'line1\nline2\n' ;;
  "agent wait") [ "$s" = working ] && exit 1; exit 0 ;;
  "pane process-info") fg=100; [ -f "$T/pane_busy" ] && fg=200
    echo "{\"result\":{\"process_info\":{\"shell_pid\":100,\"foreground_process_group_id\":$fg}}}" ;;
esac
exit 0
EOF
cat > "$TMP/bin/hc" <<'EOF'
#!/usr/bin/env bash
echo "hc $*" >> "$T/calls"
s=$(cat "$T/state" 2>/dev/null || echo idle)
case "$1" in
  ls) echo '{"terminals":[{"address":"t4","agent":"codex","status":"idle","cwd":"/p"},{"address":"t5","agent":"antigravity","status":"working","cwd":"/q"},{"address":"t6","agent":null,"status":null,"cwd":"/r"}]}' ;;
  get) echo "{\"address\":\"$2\",\"status\":{\"app\":\"codex\",\"state\":\"$s\"},\"state\":\"live\"}" ;;
  read) printf 'h1\nh2\nscreen1\nscreen2\n\n\n[hc] incomplete: older output may be missing\n' ;;
  wait) if [ "$s" = working ]; then echo '{"reason":"timeout","status":"working"}'; else echo '{"reason":"status","status":"idle"}'; fi ;;
  run) echo '{"address":"t9","agent":"codex","state":"live"}' ;;
  send) [ "$s" = blocked ] && { echo '{"error":{"kind":"blocked"}}' >&2; exit 9; } ;;
esac
exit 0
EOF
chmod +x "$TMP/bin/herdr" "$TMP/bin/hc"
# start 會用 command -v 把 agent 解析成絕對路徑：放假的 codex／agy 讓結果可預期
printf '#!/bin/sh\n' > "$TMP/bin/codex"; cp "$TMP/bin/codex" "$TMP/bin/agy"; chmod +x "$TMP/bin/codex" "$TMP/bin/agy"

ctl() { T="$TMP" PATH="$TMP/bin:$PATH" bash "$CTL" "$@"; }
eq() { # <name> <want> <got>
  if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1"; echo "  want: $(printf '%q' "$2")"; echo "  got:  $(printf '%q' "$3")"; fail=1; fi; }
called() { grep -qxF -- "$2" "$TMP/calls" && echo "ok   $1" || { echo "FAIL $1: no call [$2]"; sed 's/^/  /' "$TMP/calls"; fail=1; }; }
reset() { : > "$TMP/calls"; echo "${1:-idle}" > "$TMP/state"; rm -f "$TMP/tui_down" "$TMP/pane_busy"; }

# ---- 後端判斷
reset
eq "detect: HERDR_BACKEND wins"  hc  "$(HERDR_BACKEND=hc  HC_TERMINAL_ID= ctl backend)"
eq "detect: HERDR_BACKEND=tui"   tui "$(HERDR_BACKEND=tui HC_TERMINAL_ID=t3 ctl backend)"
eq "detect: HC_TERMINAL_ID → hc" hc  "$(HERDR_BACKEND= HC_TERMINAL_ID=t3 ctl backend)"
eq "detect: herdr works → tui"   tui "$(HERDR_BACKEND= HC_TERMINAL_ID= ctl backend)"
touch "$TMP/tui_down"
HERDR_BACKEND= HC_TERMINAL_ID= ctl backend >/dev/null 2>&1; eq "detect: none → exit 3" 3 "$?"
HERDR_BACKEND=bogus ctl backend >/dev/null 2>&1; eq "detect: bad override → exit 3" 3 "$?"

for B in tui hc; do
  export HERDR_BACKEND=$B
  if [ $B = tui ]; then ID=w2:p2; else ID=t4; fi

  reset
  if [ $B = tui ]; then
    eq "$B list" "$(printf 'w2:p2\tcodex\tworking\t/p\nw2:p3\tagy\tdone\t/p')" "$(ctl list)"
  else
    eq "$B list (agent names normalized)" "$(printf 't4\tcodex\tidle\t/p\nt5\tagy\tworking\t/q\nt6\t-\tunknown\t/r')" "$(ctl list)"
  fi

  for s in idle working blocked done; do reset $s; eq "$B status $s" $s "$(ctl status $ID)"; done
  reset weird; eq "$B status unknown" unknown "$(ctl status $ID)"
  [ $B = hc ] && { reset error; eq "hc status error → blocked" blocked "$(ctl status $ID)"; }

  reset
  out=$(ctl prompt $ID "do it now"); rc=$?
  eq "$B prompt rc" 0 "$rc"; eq "$B prompt quiet" "" "$out"
  if [ $B = tui ]; then called "tui prompt call" "herdr agent prompt $ID do it now"
  else called "hc prompt call" "hc send $ID do it now"; fi

  reset idle; ctl wait $ID 90; eq "$B wait settled → 0" 0 "$?"
  if [ $B = tui ]; then called "tui wait ms" "herdr agent wait $ID --timeout 90000"
  else called "hc wait seconds" "hc wait $ID --timeout 90 --json"; fi
  reset working; ctl wait $ID 5; eq "$B wait still working → 124" 124 "$?"

  reset
  if [ $B = tui ]; then
    eq "tui read" "$(printf 'line1\nline2')" "$(ctl read $ID 25)"
    called "tui read call" "herdr agent read $ID --source recent-unwrapped --lines 25"
  else
    eq "hc read (trailing blanks dropped, last N)" "$(printf 'h2\nscreen1\nscreen2')" "$(ctl read $ID 3)"
    called "hc read call" "hc read $ID --lines 3"
  fi

  reset
  ctl keys $ID esc y >/dev/null
  if [ $B = tui ]; then called "tui keys" "herdr pane send-keys $ID esc y"
  else called "hc keys" "hc keys $ID esc y"; fi

  reset
  if [ $B = tui ]; then
    ctl start codex /wt >/dev/null 2>&1; eq "tui start without --pane → exit 2" 2 "$?"
    eq "tui start prints pane" w2:p4 "$(ctl start codex /wt --pane w2:p4)"
    called "tui start cd" "herdr pane run w2:p4 cd /wt"
    called "tui start agent" "herdr agent start codex --kind codex --pane w2:p4"
    ctl start codex /wt --pane w2:p4 -- -a untrusted >/dev/null
    called "tui start agent args" "herdr agent start codex --kind codex --pane w2:p4 -- -a untrusted"
    reset; touch "$TMP/pane_busy"
    ctl start codex /wt --pane w2:p4 >/dev/null 2>&1; eq "tui start on busy pane → exit 2" 2 "$?"
    grep -qE 'pane run|agent start' "$TMP/calls" && { echo "FAIL tui start on busy pane sent input"; fail=1; } || echo "ok   tui start on busy pane sends nothing"
  else
    eq "hc start prints address" t9 "$(ctl start codex /wt)"
    called "hc start codex" "hc run --bg --outlive-parent --no-notify --cwd /wt --json $TMP/bin/codex --no-daemon"
    ctl start agy /wt >/dev/null
    called "hc start agy" "hc run --bg --outlive-parent --no-notify --cwd /wt --json $TMP/bin/agy"
    ctl start codex /wt -- -a untrusted >/dev/null
    called "hc start codex args" "hc run --bg --outlive-parent --no-notify --cwd /wt --json $TMP/bin/codex --no-daemon -a untrusted"
  fi

  ctl bogus >/dev/null 2>&1; eq "$B unknown verb → exit 2" 2 "$?"
done

reset blocked; HERDR_BACKEND=hc ctl prompt t4 x 2>/dev/null; eq "hc prompt on blocked → non-zero" 9 "$?"

[ $fail = 0 ] && echo "ALL PASS"; exit $fail
