# Antigravity Adapter for /dev

Platform-specific configuration for running the /dev workflow in Antigravity IDE.

## Role Mapping

| Role | Assignment | Communication |
|------|-----------|---------------|
| Primary Reviewer | Gemini (self) | Direct — no tool call needed |
| Final Reviewer | Claude | `run_command("CCB_CALLER=gemini ask claude '...'")` or MCP `ccb_ask_claude(message="<text>")` |
| Code Writer | worker1 (codex + localroles.coder) | `run_command("CCB_CALLER=gemini ask worker1 '...'")`  or MCP `ccb_ask_worker1(message="<text>")` |

## CCB Ask Pattern

### Sending to Code Writer (worker1)

Option A — run_command:
```
run_command("CCB_CALLER=gemini ask worker1 '<task>'")
```

Option B — MCP:
```
ccb_ask_worker1(message="<task>")
```

### Sending to Final Reviewer (Claude)

Option A — run_command:
```
run_command("CCB_CALLER=gemini ask claude '<message>'")
```

Option B — MCP:
```
ccb_ask_claude(message="<message>")
```

## Async Guardrail

When delegation is submitted:
1. Reply: `claude processing...` (or `worker1 processing...`)
2. **END TURN IMMEDIATELY**

## Fetching Reply (on --resume)

Option A — MCP:
```
ccb_pend_claude()    # for Final Reviewer
ccb_pend_worker1()   # for Code Writer (if used async)
```

Option B — run_command:
```
run_command("pend claude")
run_command("pend worker1")
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

- Use `// turbo` prefix for safe commands (git status, git diff) to auto-execute
- State file `.dev-state.json` is accessible via standard file read/write
- Conversation state is stored as protobuf in `~/.gemini/antigravity/conversations/`
