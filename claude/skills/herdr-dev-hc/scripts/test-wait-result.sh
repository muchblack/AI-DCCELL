#!/usr/bin/env bash
# wait-result.sh 的回歸測試：用假的 herdr 指令模擬 pane 狀態序列。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
fail=0

# 假 herdr：`agent get` 依序吐出 $TMP/states 的下一個狀態（用完就停在最後一個）；
# 吐出 WRITE 時同時把本次結果寫進結果檔，模擬 pane 做完；`agent wait` 立刻返回。
cat > "$TMP/bin/herdr" <<'EOF'
#!/usr/bin/env bash
if [ "$1 $2" = "agent get" ]; then
  n=$(cat "$T/i" 2>/dev/null || echo 0)
  s=$(sed -n "$((n + 1))p" "$T/states"); [ -z "$s" ] && s=$(tail -1 "$T/states")
  echo $((n + 1)) > "$T/i"
  if [ "$s" = WRITE ]; then printf 'dispatch_id: x-2\nverdict: PASS\n' > "$T/result.md"; s=done; fi
  echo "{\"agent_status\":\"$s\"}"
fi
exit 0
EOF
chmod +x "$TMP/bin/herdr"

run() { # <name> <expected> <states...>
  name=$1 want=$2; shift 2
  printf '%s\n' "$@" > "$TMP/states"; rm -f "$TMP/i"
  printf 'dispatch_id: x-1\nverdict: PASS\n' > "$TMP/result.md"   # 上一輪的舊檔
  got=$(T="$TMP" PATH="$TMP/bin:$PATH" WAIT_RESULT_NAP=0 WAIT_RESULT_IDLE_CHECKS=3 \
        bash "$HERE/wait-result.sh" p1 "$TMP/result.md" x-2)
  if [ "$got" = "$want" ]; then echo "ok   $name"; else echo "FAIL $name: want $want got $got"; fail=1; fi
}

run "stale done then real result"   RESULT_READY      done working idle working WRITE
run "never writes result"           SETTLED_NO_RESULT done done done done
run "blocked without --approve"     BLOCKED           working blocked
run "result already there"          RESULT_READY      WRITE

exit $fail
