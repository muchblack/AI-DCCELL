# Claude Code Adapter for /dev

Platform-specific configuration for running the /dev workflow in Claude Code.

## Role Mapping

| Role | Assignment | Communication |
|------|-----------|---------------|
| Primary Reviewer | Claude (self) | Direct — no tool call needed |
| Final Reviewer | Gemini | `Bash(CCB_CALLER=claude ask gemini "<message>")` |
| Plan Drafter | MLX | `mcp__mcp-ai-bridge__mlx_analyze(...)` |
| Code Writer | Ollama | `mcp__mcp-ai-bridge__ollama_code(...)` |

## MCP Tool Syntax

### MLX Analyze
```
mcp__mcp-ai-bridge__mlx_analyze(
  requirement="<text>",
  context="<text>",
  thinking=true
)
```

### Ollama Code
```
mcp__mcp-ai-bridge__ollama_code(
  task="<text>",
  context="<text>",
  language="<lang>"
)
```

## Async Pattern

### Sending to Final Reviewer (Gemini)
```bash
Bash(CCB_CALLER=claude ask gemini "<message>")
```

### Async Guardrail (MANDATORY)
When output contains `[CCB_ASYNC_SUBMITTED`:
1. Reply exactly: `Gemini processing...`
2. **END TURN IMMEDIATELY**
3. Do NOT poll, sleep, or call pend

### Fetching Final Reviewer Reply (on --resume)
```bash
Bash(pend gemini)
```

## Git Commit Signature

```
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Communication Style

- All output in Traditional Chinese (繁體中文)
- Qing dynasty Grand Council minister tone
- Git commit messages in Traditional Chinese
