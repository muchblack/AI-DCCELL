---
name: continue
description: Load the newest context-transfer Markdown from the current project's ./.ccb/history/ to resume a previous session. Use when the user types /continue or asks to resume with the latest transfer file.
---

# Continue (Load Latest History)

## Overview

Find the newest Markdown in `./.ccb/history/` (or legacy `./.ccb_config/history/`) and load it into the conversation.

## Workflow

1. Locate the newest `.md` under the current project's history folder.
2. If none exists, report that no history file was found.
3. Read the file content and present it to resume context.

## Execution (MANDATORY)

```bash
latest="$(ls -t "$PWD"/.ccb/history/*.md 2>/dev/null | head -n 1)"
if [[ -z "$latest" ]]; then
  latest="$(ls -t "$PWD"/.ccb_config/history/*.md 2>/dev/null | head -n 1)"
fi
if [[ -z "$latest" ]]; then
  echo "No history file found in ./.ccb/history."
  exit 0
fi
echo "$latest"
```

After finding the file path, read its full content and use it as context for the current session.

## Output Rules

- When a history file exists: read and display its content to resume the session context.
- When none exists: output the error message and stop.

## Examples

- `/continue` -> finds and reads the latest context-transfer file to restore session state
