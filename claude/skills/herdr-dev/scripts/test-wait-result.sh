#!/usr/bin/env bash
# wait-result.sh 的回歸測試：用假的 herdr／hc 指令模擬 pane 狀態序列，
# 經 herdr-ctl.sh 在 HERDR_BACKEND=tui 和 hc 下各跑一次。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
fail=0

# 假 herdr／hc：取狀態時依序吐出 $TMP/states 的下一個（用完就停在最後一個）；
# 吐出 WRITE 時同時把本次結果寫進結果檔，模擬 pane 做完；wait 立刻返回。
cat > "$TMP/next" <<'EOF'
n=$(cat "$T/i" 2>/dev/null || echo 0)
s=$(sed -n "$((n + 1))p" "$T/states"); [ -z "$s" ] && s=$(tail -1 "$T/states")
echo $((n + 1)) > "$T/i"
if [ "$s" = WRITE ]; then printf 'dispatch_id: x-2\nverdict: PASS\n' > "$T/result.md"; s=done; fi
EOF
cat > "$TMP/bin/herdr" <<'EOF'
#!/usr/bin/env bash
if [ "$1 $2" = "agent get" ]; then
  . "$T/next"; echo "{\"result\":{\"agent\":{\"agent_status\":\"$s\"}}}"
fi
exit 0
EOF
cat > "$TMP/bin/hc" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  get) . "$T/next"; echo "{\"status\":{\"app\":\"codex\",\"state\":\"$s\"},\"state\":\"live\"}" ;;
  wait) echo '{"reason":"status","status":"idle"}' ;;
esac
exit 0
EOF
chmod +x "$TMP/bin/herdr" "$TMP/bin/hc"

run() { # <name> <expected> <states...>
  name=$1 want=$2; shift 2
  printf '%s\n' "$@" > "$TMP/states"; rm -f "$TMP/i"
  printf 'dispatch_id: x-1\nverdict: PASS\n' > "$TMP/result.md"   # 上一輪的舊檔
  # WAIT_RESULT_MAX_SECONDS：測試壞掉時最多卡 10 秒，不會掛 90 分鐘
  got=$(T="$TMP" PATH="$TMP/bin:$PATH" WAIT_RESULT_NAP=0 WAIT_RESULT_IDLE_CHECKS=3 WAIT_RESULT_MAX_SECONDS=10 \
        bash "$HERE/wait-result.sh" p1 "$TMP/result.md" x-2)
  if [ "$got" = "$want" ]; then echo "ok   $HERDR_BACKEND $name"; else echo "FAIL $HERDR_BACKEND $name: want $want got $got"; fail=1; fi
}

for HERDR_BACKEND in tui hc; do
  export HERDR_BACKEND
  run "stale done then real result"   RESULT_READY      done working idle working WRITE
  run "never writes result"           SETTLED_NO_RESULT done done done done
  run "blocked without --approve"     BLOCKED           working blocked
  run "result already there"          RESULT_READY      WRITE
done
run "error counts as blocked"         BLOCKED           working error

exit $fail
