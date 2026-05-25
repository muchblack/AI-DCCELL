---
name: headless
description: "Toggle CCB headless mode on/off. When ON, /ask gemini and /ask codex use CLI subprocess instead of tmux pane. Triggers on: 切換 headless, toggle headless, headless 模式, headless mode, 切換模式, 免 tmux, 不用 pane."
user_invocable: true
---

# headless

Toggle CCB headless mode (subprocess vs tmux pane for /ask gemini and /ask codex).

## Execution

Run the following command using the Bash tool:

```bash
bash ~/.claude/skills/scripts/ccb-headless.sh
```

Report the output to the user. The command will print either:
- `Headless mode ON (subprocess mode)` — /ask gemini and /ask codex now use CLI subprocess directly
- `Headless mode OFF (pane mode)` — /ask gemini and /ask codex now use tmux pane
