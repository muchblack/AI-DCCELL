---
name: tr
description: Execute current step in AutoFlow workflow. Use when running /tr or continuing task execution.
---

Execute current step with local-first code routing (Ollama/MLX → Claude → Codex fallback). Claude writes code directly when routed locally; Codex handles state management (preflight/finalize/split).

For full instructions, see `references/flow.md`
For templates, see `templates/`
