---
name: tr
description: Execute current step in AutoFlow workflow. Use when running /tr or continuing task execution.
---

Execute current step with local-first code routing (Ollama/MLX → Claude). Claude performs all `.ccb/*` state management directly (preflight/finalize/split) via Read/Edit/Write/Bash. Reasoning second-opinions route to local MLX via `/mlx-reason`. No codex dependency.

For full instructions, see `references/flow.md`
