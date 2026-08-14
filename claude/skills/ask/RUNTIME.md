# Async Ask

Use this to submit a delegation request, then stop — via CCB `ask`, or via
herdr in a herdr-architecture project.

## Transport Detection (run first, before picking a command form)

Two transports exist, and they are not interchangeable — a herdr project's
`.ccb/` may still contain leftover config from a prior architecture, so don't
trust `.ccb/ccb.config`'s mere presence.

```bash
herdr agent list 2>/dev/null
```

- Returns an entry whose `cwd` matches this project's root and whose `agent`
  matches the requested target name (e.g. `codex`, `agy`, `opencode`) →
  **herdr transport**. Use "Herdr Transport" below, not `command ask`.
- No live herdr match, but `.ccb/ccb.config` exists in the project root →
  **CCB transport**, the "Decision Card" / `command ask` flow further down.
  Confirm it's actually mounted first (`ccb doctor` → `ccbd_state: mounted`);
  treat `project ccbd is unmounted; run ccb first` as proof it isn't, not a
  transient error to retry.
- Neither → delegation isn't available in this project. Say so; don't guess
  a transport or silently fall back to doing the work solo without flagging
  the gap.

### Herdr Transport

Herdr has no CCB-style async queue — dispatch is a synchronous "prompt and
wait" call. Get the non-blocking property from the calling tool's own
backgrounding, not from a herdr-native async flag; there isn't one.

```bash
# 1. Resolve the pane: pane_id where cwd == this project's root and
#    agent == the requested target name (codex / agy / opencode / ...)
herdr agent list

# 2. Long messages go through a scratch file, not inline args — shell-quoting
#    a multi-paragraph brief into a CLI argument is asking for corruption.
#    Write $MESSAGE to a scratch file first.

# 3. Submit + wait in one call. Run this call itself backgrounded — it can
#    take a long time and re-enters this session (as a task notification)
#    when it settles.
herdr agent prompt <pane_id> "Read <scratch-file> and respond. Write your findings to <reply-file> when done." --wait --timeout 900000
```

When the wait settles: `herdr agent get <pane_id>` for the state, then either
`herdr agent read <pane_id> --source recent-unwrapped --lines 60` or read
`<reply-file>` if the prompt asked the target to write one. `blocked` means
either an approval prompt (`herdr agent send-keys <pane_id> <key>`) or a real
question for the user — read the pane to tell which. If this call behaves
unexpectedly, the `herdr-dev` skill's "Herdr Dispatch Pattern" section has
the full state-machine detail — this section only covers the common path for
a one-off ask.

### CCB Transport

## Decision Card

Before every ask, decide:

1. Need delegation? If no, answer directly.
2. Dependency gate:
   - Default: do not use `--chain`.
   - Use `--chain` only when the current active CCB task cannot finish until
     this exact child result arrives. Then stop for continuation.
   - Communication tests, batch sends, notifications, and independent work do
     not become chain dependencies merely because replies are requested.
3. Result intent:
   - `--silence`: publish/execute task; success result not needed. Failures,
     blockers, risks, or required next actions still surface.
   - `--compact`: result wanted, but only distilled
     findings/status/risks/blockers/next actions.
   - `+ --artifact-reply`: consultation/analysis/report where full text should
     be preserved.
   - plain `ask`: short question or short handoff where inline text is enough.
4. Request fidelity:
   - `+ --artifact-request`: exact transient input
     (logs/output/diffs/copied contents/config/JSON/YAML/table/structured text).
     Prefer repo paths when the target can read files directly.
   - `--artifact-io`: request and reply both need artifacts.

## Guardrails

- Do not probe `--chain`; if unsure there is an active parent job, use plain
  `ask`.
- If CCB says `ask --chain requires an active parent job`, retry once with
  plain `ask` for user-requested delegation.
- Never add `--chain` merely to make a rejected plain ask succeed. If the work
  is independent and no success result is needed, use `--silence`; otherwise
  report the routing limitation instead of inventing a dependency.
- `--chain` and `--silence` usually conflict; avoid mixing unless explicit.
- Avoid `--silence --artifact-reply`; silence means no caller result needed; artifact-reply preserves one.
- Artifact flags are orthogonal to `--chain`, `--silence`, and `--compact`.
  They preserve content, not dependency shape.
- Automatic spill for text over 4 KiB is a fallback, not the primary rule.
- `--artifact-*` modes are CCB/daemon managed; targets do not write artifact reply files.
- Plain nested `ask` from an active CCB task is rejected. Use `--chain` only
  for a real child dependency; use `--silence` for independent no-result work.
- In `A --silence -> B`, B still runs an active job. B-to-C depends on whether B needs C's result.
- In task chains, each needed-result hop uses `--chain`; CCB then propagates continuations.
- Finish an inbound CCB task in its current turn.
- If the original caller is a registered CCB agent, CCB routes that turn's
  terminal result through the existing lineage; do not open a new `ask` to
  report completion to the original caller.
- Direct CLI submitters read terminal results from control output such as
  `watch` or `trace`.
- If the current task is a CCB result-chain continuation, answer the current task
  directly with the final result. Do not use `ask`, `--chain`, or
  `--silence` to send that final result to the original caller; CCB routes the
  continuation completion upstream.
- `--silence` is not an active-job correction channel. Use
  `ccb followup <active_job_id> --message "<correction>"` only when the target
  provider supports exact active-turn injection; only `injected` is success.
  On `rejected`, `too_late`, or `terminal`, cancel and resubmit the complete
  corrected task instead of queueing a correction as ordinary work.
- A `completed` CCB job means provider execution ended normally; it does not by
  itself prove business acceptance.
- `ask get`, `pend`, `watch`, and `ping` are diagnostics-only commands for
  explicit debugging requests, not normal ask workflow tools.
- Do not manually append output-policy text; stable reply policy comes from managed CCB memory, and `ask` adds only requested compact/silent mode metadata.

Always send `MESSAGE` through the `<<'EOF' ... EOF` heredoc below. No other form
is allowed. Use no flags or insert selected flags before `"$TARGET"`:

```bash
command ask "$TARGET" <<'EOF'
$MESSAGE
EOF
```

```bash
command ask --chain --artifact-reply "$TARGET" <<'EOF'
$MESSAGE
EOF
```

- Sender is inferred from the current CCB workspace.
- `TARGET=all` broadcasts.
- After the command returns, immediately end the turn. Do not wait for a reply,
  do not run `ask get` / `pend` / `ping` / `watch`, do not poll.
- For `--chain`, report only that delegation was submitted.
