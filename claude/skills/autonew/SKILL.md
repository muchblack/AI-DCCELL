---
name: autonew
description: Send /new to a provider's pane to start a new session without context injection. Triggers on: 重開 session, 新 session, new session, reset session, 重啟對話, fresh start, 清空 provider.
metadata:
  short-description: Start new session in provider
---

# Auto New Session

Send `/new` command directly to a provider's terminal pane to start a new session.

## Usage

```
autonew <provider>
```

Providers: gemini, codex, opencode, droid, claude

## Execution (MANDATORY)

```bash
autonew $PROVIDER
```

## Rules

- This command sends `/new` directly to the provider's pane without any wrapping.
- Use this to clear/reset a provider's session.

## Examples

- `/autonew gemini` - Start new Gemini session
- `/autonew codex` - Start new Codex session
