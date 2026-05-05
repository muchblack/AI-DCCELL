# Async Ask Pattern (cask/gask/oask)

Use this pattern only when the user explicitly delegates to Gemini/OpenCode.
Do not use it for questions about the tools themselves.

## Command Map

- Gemini -> `gask` (health: `gping`)
- OpenCode -> `oask` (health: `oping`)

(codex retired 2026-05-05; cask removed)

## Execution (MANDATORY)

Linux/macOS/WSL:

```bash
Bash(<cask|gask|oask> <<'EOF'
<user request, verbatim>
EOF
, run_in_background=true)
```

Windows PowerShell:

```powershell
Bash(@"
<user request, verbatim>
"@ | <cask|gask|oask>, run_in_background=true)
```

## Rules

- End the current turn immediately after submission.
- Wait for the Bash notification callback; do not poll or use `*pend/*end` unless explicitly requested.
- If Bash fails, report the error and suggest `cping/gping/oping`.
