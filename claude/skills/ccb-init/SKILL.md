---
name: ccb-init
description: >-
  Bootstrap a new CCB project: write .ccb/ccb.config (via Q&A or template),
  then auto-fix macOS Keychain symlinks for claude/agy agents so /login works in CCB panes,
  set inherit_auth: false for codex agents to prevent shared refresh_token conflicts,
  and write a project-root opencode.json (permission: allow) so opencode workers auto-confirm.
  One command: config Q&A + auth fixes + opencode auto-confirm.
  Triggers on: ccb-init, ccb init, 初始化 ccb, 新專案 ccb, bootstrap ccb.
  Examples: "/ccb-init", "/ccb-init --template standard", "/ccb-init --template minimal".
argument-hint: "[--template minimal|standard|inspect|quad|solo] [--skip-keychain] [--skip-config] [--skip-opencode]"
---

# CCB Init — Project Bootstrap

Bootstrap a CCB project in three steps:

1. **Config** — create or update `.ccb/ccb.config` (Q&A or template); when
   writing a new config, stale `.ccb/agents/<name>/` directories no longer
   referenced by the new `[windows]` definitions are deleted first (after
   user confirmation) so old Keychain/auth state doesn't linger
2. **Fix** — run `/ccb-fix-keychain` logic for all agents:
   - `claude` / `agy`：symlink `Library/Keychains` in isolated HOME
   - `codex`：set `inherit_auth: false` + clear stale shared `auth.json`
3. **opencode auto-confirm** — if the config has any `opencode` agent, write a
   project-root `opencode.json` with `"permission": "allow"` so opencode workers
   run tools without permission prompts (required for unattended CCB dispatch).
   Skip with `--skip-opencode`. See `references/opencode-permission.md`.

For full config Q&A flow, see `references/config-flow.md`.
For keychain/auth fix details, see `references/keychain-fix.md`.
For opencode auto-confirm details, see `references/opencode-permission.md`.
For available config templates, see `references/templates.md`.
