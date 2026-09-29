---
name: ask
description: Send a request to another agent for collaboration via herdr in a herdr-architecture project.
metadata:
  short-description: Ask agent
---

Use this when the user asks you to delegate to another agent for
collaboration via herdr in a herdr-architecture project.

## Transport Detection (run first)

```bash
herdr agent list 2>/dev/null
```

- Returns an entry whose `cwd` matches this project's root and whose `agent`
  matches the requested target name (e.g. `codex`, `agy`, `opencode`) →
  use "Herdr Transport" below.
- No live herdr match → delegation isn't available in this project. Say so;
  don't guess a transport or silently fall back to doing the work solo
  without flagging the gap.

## Herdr Transport

Herdr dispatch is a synchronous "prompt and wait" call. Get the non-blocking
property from the Bash tool's own backgrounding (`run_in_background: true`),
not from a herdr-native async flag; there isn't one.

```bash
# 1. Resolve the pane: pane_id where cwd == this project's root and
#    agent == the requested target name (codex / agy / opencode / ...)
herdr agent list

# 2. Long messages go through a scratch file, not inline args — shell-quoting
#    a multi-paragraph brief into a CLI argument is asking for corruption.
#    Write $MESSAGE to a scratch file first.

# 3. Submit + wait in one call. Run this call itself via Bash
#    run_in_background:true — it can take a long time and re-enters this
#    session (as a task notification) when it settles.
herdr agent prompt <pane_id> "Read <scratch-file> and respond. Write your findings to <reply-file> when done." --wait --timeout 900000
```

When the wait settles: `herdr agent get <pane_id>` for the state, then either
`herdr agent read <pane_id> --source recent-unwrapped --lines 60` or read
`<reply-file>` if the prompt asked the target to write one. `blocked` means
either an approval prompt (`herdr agent send-keys <pane_id> <key>`) or a real
question for the user — read the pane to tell which. If this call behaves
unexpectedly, the `herdr-dev` skill's "Herdr Dispatch Pattern" section has
the full state-machine detail (stalls, repeated approval cycles, stale-pane
context) — this section only covers the common path for a one-off ask.

## Guardrails

- Need delegation? If no, answer directly.
- After submitting, end the turn; do not poll. The backgrounded call
  re-enters this session when it settles.
- A pane status of `idle`/`done` is not proof of completion: `agent read`
  the screen first (some providers report idle at an approval dialog).
- Never approve a command that will fail for environment reasons; `esc` and
  send a corrective prompt instead.
