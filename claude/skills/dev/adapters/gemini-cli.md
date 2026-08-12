# Gemini-cli Adapter for /dev

Platform-specific configuration for running the /dev workflow in Gemini-cli.

## Role Mapping

| Role | Assignment | Communication |
|------|-----------|---------------|
| Primary Reviewer | Gemini (self) | Direct — no tool call needed |
| Final Reviewer | Claude | `shell("CCB_CALLER=gemini ask claude '...'")`  or MCP `ccb_ask_claude(message="<text>")` |
| Code Writer | worker1 (codex + localroles.coder) | `shell("CCB_CALLER=gemini ask worker1 '...'")`  or MCP `ccb_ask_worker1(message="<text>")` |

## CCB Ask Pattern

### Sending to Code Writer (worker1)

Option A — shell:
```
shell("CCB_CALLER=gemini ask worker1 '<task>'")
```

Option B — MCP:
```
ccb_ask_worker1(message="<task>")
```

### Sending to Final Reviewer (Claude)

Option A — shell:
```
shell("CCB_CALLER=gemini ask claude '<message>'")
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

Option B — shell:
```
shell("pend claude")
shell("pend worker1")
```

## Git Commit Signature

```
Co-Authored-By: Gemini 3 Pro <noreply@google.com>
```

## Communication Style

- All output in Traditional Chinese (繁體中文)
- Qing dynasty Grand Council minister tone
- Git commit messages in Traditional Chinese
