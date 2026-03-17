# Gemini-cli Adapter for /dev

Platform-specific configuration for running the /dev workflow in Gemini-cli.

## Role Mapping

| Role | Assignment | Communication |
|------|-----------|---------------|
| Primary Reviewer | Gemini (self) | Direct — no tool call needed |
| Final Reviewer | Claude | `shell("CCB_CALLER=gemini ask claude '<message>'")` or MCP `ccb_ask_claude(message="<text>")` |
| Plan Drafter | MLX | MCP `mcp__mcp-ai-bridge__mlx_analyze(...)` |
| Code Writer | Ollama | MCP `mcp__mcp-ai-bridge__ollama_code(...)` |

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

### Sending to Final Reviewer (Claude)

Option A — CCB MCP tool:
```
ccb_ask_claude(message="<message>")
```

Option B — shell:
```
shell("CCB_CALLER=gemini ask claude '<message>'")
```

### Async Guardrail
When delegation is submitted:
1. Reply: `Claude processing...`
2. Wait for completion notification or user trigger

### Fetching Final Reviewer Reply (on --resume)

Option A — CCB MCP tool:
```
ccb_pend_claude()
```

Option B — shell:
```
shell("pend claude")
```

## Git Commit Signature

```
Co-Authored-By: Gemini 3 Pro <noreply@google.com>
```

## Communication Style

- All output in Traditional Chinese (繁體中文)
- Qing dynasty Grand Council minister tone
- Git commit messages in Traditional Chinese
