---
name: cping
description: Test connectivity with AI provider (gemini/opencode/droid/claude).
metadata:
  short-description: Test AI provider connectivity
---

# Ping AI Provider

Test connectivity with specified AI provider.

## Usage

The first argument must be the provider name:

- `gemini` - Test Gemini
- `opencode` - Test OpenCode
- `droid` - Test Droid
- `claude` - Test Claude

(codex retired 2026-05-05)

## Execution (MANDATORY)

Use `ccb-ping` wrapper to avoid conflict with system `ping`:

```
Bash(ccb-ping $PROVIDER)
```

## Examples

- `/cping gemini`
- `/cping opencode`
- `/cping claude`
