# Claude Code Adapter for /dev

Platform-specific configuration for running the /dev workflow in Claude Code.

## Role Mapping

| Role | Assignment | Communication |
|------|-----------|---------------|
| Primary Reviewer | Claude (self) | Direct — no tool call needed |
| Plan Reviewer | analyst (agy, localroles.analyst) | `Bash(CCB_CALLER=main ask analyst "...")` |
| Code Reviewer | reviewer1 (coordinator → reviewer2) | `Bash(CCB_CALLER=main ask reviewer1 "...")` |
| Code Writer (primary) | worker2 (opencode, localroles.coder) | `Bash(CCB_CALLER=main ask worker2 "...")` |
| Code Writer (fallback) | worker1 (codex, localroles.coder) | `Bash(CCB_CALLER=main ask worker1 "...")` |

## CCB Ask Pattern

### Sending to Plan Reviewer (analyst)
```bash
CCB_CALLER=main ask analyst <<'EOF'
<plan review message>
EOF
```

### Sending to Code Writer (worker2 primary, worker1 fallback)
```bash
CCB_CALLER=main ask worker2 <<'EOF'
Implement the following plan. Output only the final code; do not write files.

Plan:
<implementation steps>

Existing code context:
<relevant file contents>

Language: <lang>
Historical corrections (avoid repeating):
<last 5 corrections>
EOF
```
If worker2 times out (>5 min), switch to `worker1` with the same message.

### Sending to Code Reviewer (reviewer1)
reviewer1 (code-review-coordinator) will automatically dispatch to reviewer2 and synthesize both verdicts.
```bash
CCB_CALLER=main ask reviewer1 <<'EOF'
<code review message>
EOF
```

## Async Guardrail (MANDATORY)

When output contains `[CCB_ASYNC_SUBMITTED`:
1. Reply exactly: `reviewer1 processing...` (or `worker1 processing...`)
2. **END TURN IMMEDIATELY**
3. Do NOT poll, sleep, or call pend

## Fetching Reply (on --resume)

```bash
pend analyst     # for Plan Reviewer (Phase 2)
pend reviewer1   # for Code Reviewer (Phase 6)
pend worker2     # for Code Writer primary
pend worker1     # for Code Writer fallback
```

## Git Commit Signature

```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

## Communication Style

- All output in Traditional Chinese (繁體中文)
- Qing dynasty Grand Council minister tone
- Git commit messages in Traditional Chinese
