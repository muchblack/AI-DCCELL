---
name: peon-ping
description: Control peon-ping sound notifications and the Peon Trainer — toggle sounds on/off, change settings (volume, pack rotation, categories, active pack), set the voice pack for the current session, and log exercise reps. Triggers on: 靜音, 關聲音, mute, unmute, 暫停音效, 恢復音效, 開聲音, toggle sound, 安靜, 調音量, 改音效設定, peon config, sound config, 輪播設定, rotation config, 音效分類, 改 peon 設定, 換語音, 用 GLaDOS, 用 Peon, 換角色聲音, change voice, use voice pack, 這場用, switch voice, 做了伏地挺身, 做了深蹲, pushups, squats, 記錄運動, log reps, 幾下, 做完了. Examples - "/peon-ping toggle", "/peon-ping volume 0.5", "/peon-ping use glados", "/peon-ping log 25 pushups".
user_invocable: true
---

# peon-ping

One skill for everything peon-ping. Pick the section that matches the request.

Base paths (use `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` for the config dir):

- Script: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/peon.sh`
- Config: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/config.json`
- State: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/.state.json`

If the `hooks/peon-ping` directory does not exist, peon-ping is not installed on
this machine: say so and stop.

## toggle — sounds on/off

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/peon.sh toggle
```

On Windows use `peon.ps1 toggle` from the same directory via PowerShell.
The command prints `peon-ping: sounds paused` or `peon-ping: sounds resumed`;
report it to the user.

## config — change settings

Read the config file, edit the relevant field(s), confirm the change.

- **volume** (0.0–1.0): sound volume
- **active_pack** (string): current pack (e.g. `"peon"`, `"sc_kerrigan"`, `"glados"`)
- **enabled** (boolean): master on/off switch
- **pack_rotation** (array): packs to rotate through per session; `[]` uses `active_pack` only
- **pack_rotation_mode**: `"random"` (default), `"round-robin"`, or `"agentskill"` (explicit per-session assignments from `use`; invalid or missing packs fall back to `active_pack` and the stale assignment is removed)
- **categories** (object of booleans): `session.start`, `task.acknowledge`, `task.complete`, `task.error`, `input.required`, `resource.limit`, `user.spam`
- **annoyed_threshold** / **annoyed_window_seconds**: rapid-prompt threshold and window for `user.spam` sounds
- **silent_window_seconds**: suppress `task.complete` sounds for tasks shorter than this
- **session_ttl_days** (default 7): expire stale per-session pack assignments (agentskill mode)
- **desktop_notifications** (boolean, default `true`): notification popups, independent of sounds
- **use_sound_effects_device** (boolean, default `true`): macOS only — route audio through the Sound Effects device or default output via afplay

List available packs:

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/peon.sh packs list
```

## use — voice pack for this session

`/peon-ping-use <pack>` was handled by a beforeSubmitPrompt hook (zero model
tokens). If that hook is installed it still intercepts that exact text; this
section is the manual path for `/peon-ping use <pack>` or when the hook is
missing or failing.

1. Verify the pack exists (`packs list` above). Not found → list packs and ask.
2. Get the session id: `echo "$CLAUDE_SESSION_ID"`. Empty (Cursor) → use the key `"default"`.
3. In `config.json`, set `pack_rotation_mode` to `"agentskill"` and make sure the pack is in `pack_rotation`.
4. In `.state.json`, add or update the mapping:
   ```json
   { "session_packs": { "SESSION_ID": {"pack": "pack_name", "last_used": UNIX_TIMESTAMP} } }
   ```
5. Confirm: `Voice set to [PACK] for this session; rotation mode: agentskill`.

Common packs: `peon`, `peasant`, `glados`, `sc_kerrigan`, `hk47`.
Reset: remove the session id from `session_packs`, or set `pack_rotation_mode` back to `"random"` / `"round-robin"`.

## log — Peon Trainer reps

```bash
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/hooks/peon-ping/peon.sh trainer log <count> <exercise>
```

`<exercise>` is `pushups` or `squats`, e.g. `trainer log 25 pushups`. Report the
output (updated rep count). If the user asks for progress, also run
`peon.sh trainer status`. If the output says the trainer is not enabled, tell
the user to run `/peon-ping toggle` or `peon trainer on` first.
