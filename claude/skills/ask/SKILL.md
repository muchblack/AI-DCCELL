---
name: ask
description: Async via ask, end turn immediately; use when user explicitly delegates to any AI provider (gemini/codex/opencode/droid); NOT for questions about the providers themselves.
metadata:
  short-description: Ask AI provider asynchronously
---

# Ask AI Provider (Async)

Send the user's request to specified AI provider asynchronously.

## Usage

The first argument must be the provider name, followed by the message:
- `gemini` - Send to Gemini
- `codex` - Send to Codex
- `opencode` - Send to OpenCode
- `droid` - Send to Droid

## Headless Mode

When `/tmp/.ccb-headless` exists, gemini and codex use CLI subprocess instead of tmux pane.
Toggle with: `bash ~/.claude/skills/scripts/ccb-headless.sh`

Headless uses `gemini -p` and `codex exec --full-auto` — no terminal pane needed.
Other providers (opencode, droid) always use the daemon path.

## Execution (MANDATORY)

**Step 1**: Check headless flag and provider:

```
if [ -f /tmp/.ccb-headless ] && { [ "$PROVIDER" = "gemini" ] || [ "$PROVIDER" = "codex" ]; }
→ Headless path
else
→ Daemon path
```

**Headless path** (gemini/codex only):

```
Bash(bash ~/.claude/skills/scripts/ask-headless.sh $PROVIDER "$MESSAGE")
```

- This runs synchronously and returns the reply directly.
- Do NOT follow the Async Guardrail — the reply is already in the output.
- Present the reply to the user normally.

**Daemon path** (default):

```
Bash(CCB_CALLER=claude ask $PROVIDER "$MESSAGE")
```

- Follow the **Async Guardrail** rule in CLAUDE.md (mandatory).
- If output contains `CCB_ASYNC_SUBMITTED`, end your turn immediately.

## Rules

- If submit fails (non-zero exit):
  - Reply with exactly one line: `[Provider] submit failed: <short error>`
  - End your turn immediately.

## Examples

- `/ask gemini What is 12+12?`
- `/ask codex Refactor this code`
- `/ask opencode Analyze this bug`
- `/ask droid Execute this task`

