# CCB Init — opencode Auto-Confirm

Make opencode-backed CCB workers run tools without permission prompts, so they
can work unattended when dispatched via `ask`.

## Why a project-root `opencode.json`

CCB launches each opencode agent with
`OPENCODE_CONFIG=.ccb/agents/<agent>/provider-state/opencode/opencode.json` and
regenerates that file on every memory projection — manual edits there get
clobbered. However, CCB **merges the project-root `opencode.json`** into the
agent config (seen as `project_config_path` in the agent's `events.jsonl`).
So the project root is the correct, durable place to set permissions.

opencode has **no** `config set` command and **no** `autoConfirm` key. The real
key is `permission`, with values `ask` | `allow` | `deny` (official schema:
`https://opencode.ai/config.json`, `$defs.PermissionConfig`).

## When to run

Only if `.ccb/ccb.config` contains at least one `opencode` agent (in any
window — `work`, `codeReview`, etc.). Skip entirely with `--skip-opencode`.

## Step: detect opencode agents

```bash
grep -q "opencode" .ccb/ccb.config && echo "has opencode" || echo "no opencode"
```

If none → skip this step.

## Step: write project-root `opencode.json`

If a project-root `opencode.json` already exists, **merge** rather than
overwrite: add/replace only the `permission` key, preserve the rest. Otherwise
create:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "permission": "allow"
}
```

`"permission": "allow"` opens every tool (edit / bash / webfetch / …). For a
tighter posture, set it per-tool instead — local file work open, network
gated:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "read": "allow",
    "edit": "allow",
    "bash": "allow",
    "webfetch": "ask",
    "external_directory": "ask"
  }
}
```

## Step: report

```
✅ opencode.json 已寫入（permission: allow）— opencode worker 下次啟動自動確認
```

## Notes

- **Loaded at launch**: a running opencode session won't pick up the change;
  it applies on the worker's next start/restart.
- **Full-open risk**: `"allow"` lets the worker run arbitrary bash and edit
  files without prompting. Acceptable under worktree isolation; use the
  per-tool form if network/out-of-tree access should stay gated.
