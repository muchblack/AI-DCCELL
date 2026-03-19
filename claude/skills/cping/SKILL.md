---
name: cping
description: Test connectivity with AI provider (gemini/codex/opencode/droid/claude). Triggers on: 測試連線, 連得上嗎, ping provider, test connection, 通不通, 能連嗎, provider 活著嗎, is provider alive.
metadata:
  short-description: Test AI provider connectivity
---

# Ping AI Provider

Test connectivity with specified AI provider.

## Usage

The first argument must be the provider name:
- `gemini` - Test Gemini
- `codex` - Test Codex
- `opencode` - Test OpenCode
- `droid` - Test Droid
- `claude` - Test Claude

## Execution (MANDATORY)

Use `ccb-ping` wrapper to avoid conflict with system `ping`:
```
Bash(ccb-ping $PROVIDER)
```

## Examples

- `/cping gemini`
- `/cping codex`
- `/cping claude`
