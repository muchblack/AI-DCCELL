---
name: pend
description: View latest reply from AI provider (gemini/codex/opencode/droid/claude). Triggers on: 看回覆, 看結果, 回了什麼, 回覆了嗎, check reply, view reply, 有回應了嗎, gemini 回了嗎, codex 回了嗎.
metadata:
  short-description: View latest AI provider reply
---

# Pend - View Latest Reply

View the latest reply from specified AI provider.

## Usage

The first argument must be the provider name:
- `gemini` - View Gemini reply
- `codex` - View Codex reply
- `opencode` - View OpenCode reply
- `droid` - View Droid reply
- `claude` - View Claude reply

Optional: Add a number N to show the latest N conversations.

## Execution (MANDATORY)

```bash
pend $ARGUMENTS
```

## Examples

- `/pend gemini`
- `/pend codex 3`
- `/pend claude`
