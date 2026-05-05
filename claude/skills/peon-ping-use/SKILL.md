---
name: peon-ping-use
description: Set which voice pack (character voice) plays for the current chat session. Automatically enables agentskill rotation mode if not already set. Use when user wants a specific character voice like GLaDOS, Peon, or Kerrigan for this conversation. Triggers on: 換語音, 用 GLaDOS, 用 Peon, 換角色聲音, change voice, use voice pack, 這場用, switch voice.
user_invocable: true
license: MIT
metadata:
  author: PeonPing
  version: "1.0"
---

# peon-ping-use

Set which voice pack plays for the current chat session.

## How it works

`/peon-ping-use <packname>` is intercepted by a **beforeSubmitPrompt hook** (`scripts/hook-handle-use.sh` / `.ps1`) that validates the pack, enables `agentskill` rotation mode, maps the session to the pack in `.state.json`, and returns instant confirmation — zero model tokens used. This SKILL.md exists only for `/` autocomplete discoverability.

## Usage

```
/peon-ping-use peasant
/peon-ping-use glados
/peon-ping-use sc_kerrigan
```

Common packs: `peon`, `peasant`, `glados`, `sc_kerrigan`, `hk47`.

## Manual fallback (hook not installed / failing)

### 1. Verify pack exists

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/peon.sh packs list
```

### 2. Get session ID

```bash
echo "$CLAUDE_SESSION_ID"
```

If empty (Cursor users): use `"default"` as the key in `session_packs` — applies to all sessions without explicit assignment.

### 3. Update config.json

Set `pack_rotation_mode` to `"agentskill"` and ensure the pack is in `pack_rotation`:

```json
"pack_rotation_mode": "agentskill",
"pack_rotation": ["peasant", "peon", "ra2_kirov"]
```

Path: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/config.json`

### 4. Update .state.json

Add/update the session → pack mapping:

```json
{
  "session_packs": {
    "SESSION_ID_HERE": {"pack": "pack_name", "last_used": UNIX_TIMESTAMP}
  }
}
```

Path: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/.state.json`

### 5. Confirm

```
Voice set to [PACK_NAME] for this session
Rotation mode: agentskill
```

## Error handling

- **Pack not found** → list available packs, ask user to choose
- **No session ID** → use `"default"` key (Cursor fallback)
- **Invalid pack at runtime** → peon-ping falls back to `active_pack` and removes the stale assignment

## Reset

Remove the session ID from `session_packs` in `.state.json`, or change `pack_rotation_mode` back to `"random"` / `"round-robin"`.
