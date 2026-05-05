---
name: autonew
description: Send /new to a provider's pane to start a new session without context injection.
metadata:
  short-description: Start new session in provider
---

# Auto New Session

Send `/new` command directly to a provider's terminal pane to start a new session.

## Usage

```
autonew <provider>
```

Providers: gemini, opencode, droid, claude (codex retired 2026-05-05)

## Execution (MANDATORY)

```bash
autonew $PROVIDER
```

## Rules

- This command sends `/new` directly to the provider's pane without any wrapping.
- Use this to clear/reset a provider's session.

## Examples

- `/autonew gemini` - Start new Gemini session
- `/autonew opencode` - Start new OpenCode session
