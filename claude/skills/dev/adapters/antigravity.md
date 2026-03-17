# Antigravity Adapter for /dev

Platform-specific configuration for running the /dev workflow in Antigravity IDE.

## Role Mapping

| Role | Assignment | Communication |
|------|-----------|---------------|
| Primary Reviewer | Gemini (self) | Direct — no tool call needed |
| Final Reviewer | Claude | `run_command("CCB_CALLER=gemini ask claude '<message>'")`  or MCP `ccb_ask_claude(message="<text>")` |
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

Option B — run_command:
```
run_command("CCB_CALLER=gemini ask claude '<message>'")
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

Option B — run_command:
```
run_command("pend claude")
```

## Git Commit Signature

```
Co-Authored-By: Gemini 3 Pro <noreply@google.com>
```

## Communication Style

- All output in Traditional Chinese (繁體中文)
- Qing dynasty Grand Council minister tone
- Git commit messages in Traditional Chinese

## Antigravity-Specific Notes

- Antigravity uses step-numbered workflows, but /dev can run as a single-step skill
- Use `// turbo` prefix for safe commands (git status, git diff) to auto-execute
- State file `.dev-state.json` is accessible via standard file read/write
- Conversation state is stored as protobuf in `~/.gemini/antigravity/conversations/`
