# AutoFlow Plan

Create executable plan artifacts: `.ccb/todo.md` + `.ccb/state.json` + `.ccb/plan_log.md`

**File formats**: See `~/.claude/skills/docs/formats.md`
**Protocol**: See `~/.claude/skills/docs/protocol.md`

---

## Architecture Note

- Plan mode is optional (recommended for structured planning + review).
- **All file I/O (create/modify)** is executed by **Codex** via `FileOpsREQ` / `FileOpsRES`.
- This command must never directly write files; it only prepares the plan content and delegates writes to Codex.

---

## Execution Flow

### 1. Initialize
- Get requirement from `$ARGUMENTS`
- Analyze project: tech stack, key files, background
- If requirement involves unfamiliar technologies/APIs/libraries, use WebSearch/WebFetch to review official docs + best practices before finalizing the plan

### 2. Collaborative Design (Plan)

Invoke the `/all-plan` skill with the requirement:

```
/all-plan <requirement from $ARGUMENTS>
```

The `/all-plan` skill provides a complete collaborative design flow including:
1. Requirement clarification
2. Inspiration consultation (if applicable)
3. Designer planning
4. Reviewer scoring

Extract from the `/all-plan` output:
- **goal**: the task objective
- **nonGoals**: what NOT to do
- **steps**: ordered list of step titles, each with **verifiable done conditions**
- **acceptance criteria**: done conditions (finalDone)

For each step, extract or generate **structured done conditions** that can be automatically verified (Step 8.6 Ralph verification gate in `/tr`). Each condition should specify a `type`:

| Type             | Example                                                                   | Auto-verifiable |
| ---------------- | ------------------------------------------------------------------------- | --------------- |
| `file_exists`    | `{"type":"file_exists","path":"app/Models/Foo.php"}`                      | Yes (Glob)      |
| `grep_match`     | `{"type":"grep_match","pattern":"class Foo","path":"app/Models/Foo.php"}` | Yes (Grep)      |
| `test_passes`    | `{"type":"test_passes","command":"php artisan test --filter=FooTest"}`    | Yes (Bash)      |
| `build_succeeds` | `{"type":"build_succeeds","command":"npm run build"}`                     | Yes (Bash)      |
| `no_lint_errors` | `{"type":"no_lint_errors","command":"npm run lint"}`                      | Yes (Bash)      |
| `manual`         | `{"type":"manual","description":"UI renders correctly"}`                  | No (skipped)    |

If `/all-plan` output only has prose done conditions, Claude converts them to structured format before saving. Prefer auto-verifiable types; use `manual` only when no automation is possible.

### 3. User Confirmation

Show final plan from `/all-plan` output:

```
## Plan Summary

**Goal**: [goal]
**Non-goals**: [non-goals]

**Steps** (N total):
1. [S1 title]
2. [S2 title]
...

**Acceptance**:
- [done 1]
- [done 2]

**Review notes**: [key decisions from all-plan]

Confirm? (Y/adjust)
```

### 4. Save Files

After user confirms, delegate file creation to `/file-op` using `FileOpsREQ`:

Call:

```json
{
  "proto": "autoflow.fileops.v1",
  "id": "TP",
  "purpose": "write_plan_files",
  "summary": "Initialize .ccb/todo.md/.ccb/state.json/.ccb/plan_log.md from confirmed plan",
  "done": ["Plan files exist and match formats"],
  "ops": [
    {
      "op": "autoflow_plan_init",
      "plan": {
        "taskName": "<Task Name>",
        "objective": { "goal": "<goal>", "nonGoals": "<non-goals>", "doneWhen": "<one-line summary>" },
        "context": { "repoType": "<type>", "keyFiles": ["<path>"], "background": "<why>" },
        "constraints": ["<constraint>"],
        "steps": [
          {
            "title": "S1 title",
            "doneConditions": [
              { "type": "file_exists", "path": "path/to/file" },
              { "type": "test_passes", "command": "test command" }
            ]
          },
          {
            "title": "S2 title",
            "doneConditions": [
              { "type": "grep_match", "pattern": "pattern", "path": "path" }
            ]
          }
        ],
        "finalDone": ["criterion 1", "criterion 2"]
      }
    },
    { "op": "run", "cmd": "bash ~/.claude/skills/tr/scripts/autoloop.sh start", "cwd": "." }
  ],
  "report": { "changedFiles": true, "diffSummary": true, "commandOutputs": "never" }
}
```

Then run:

```
/file-op <the JSON above>
```

Codex returns `FileOpsRES` JSON only (via `/file-op`).

### 5. Output

```
Plan saved:
- .ccb/todo.md
- .ccb/state.json
- .ccb/plan_log.md

Next: Use /tr to start execution
```

---

## Principles

1. **Collaborative Design**: Uses `/all-plan` for full collaborative planning flow
2. **Coarse-grained**: Titles only, details in /tr
3. **Recoverable**: Context enables continuity after /clear
4. **Research-driven**: Use WebSearch and WebFetch to gather info on unfamiliar tech/APIs/best practices before finalizing the plan
