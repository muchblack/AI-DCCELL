# AutoFlow Plan

Create executable plan artifacts: `.ccb/todo.md` + `.ccb/state.json` + `.ccb/plan_log.md`

---

## Architecture Note

- Plan mode is optional (recommended for structured planning + review).
- **All file I/O is performed by Claude directly** using Read/Edit/Write tools.
- All reasoning subtasks (e.g. independent design second opinion) route to local MLX via `/mlx-reason`.
- Codex is NOT used in this flow.

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
4. Reviewer scoring (codex if mounted, otherwise `/mlx-reason` per Reviewer Fallback Protocol)

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

### 4. Save Files (Claude Direct)

After user confirms, Claude writes the three plan artifacts directly using Write/Edit. No external delegation.

#### 4.1 Build the in-memory plan object

```json
{
  "taskName": "<Task Name>",
  "objective": { "goal": "<goal>", "nonGoals": "<non-goals>", "doneWhen": "<one-line summary>" },
  "context": { "repoType": "<type>", "keyFiles": ["<path>"], "background": "<why>" },
  "constraints": ["<constraint>"],
  "current": { "type": "step", "stepIndex": 1 },
  "steps": [
    {
      "index": 1,
      "title": "S1 title",
      "status": "pending",
      "attempts": 0,
      "substeps": [],
      "doneConditions": [
        { "type": "file_exists", "path": "path/to/file" },
        { "type": "test_passes", "command": "test command" }
      ]
    },
    {
      "index": 2,
      "title": "S2 title",
      "status": "pending",
      "attempts": 0,
      "substeps": [],
      "doneConditions": [
        { "type": "grep_match", "pattern": "pattern", "path": "path" }
      ]
    }
  ],
  "finalDone": ["criterion 1", "criterion 2"]
}
```

#### 4.2 Write `.ccb/state.json`

Use `Write` to create `.ccb/state.json` with the JSON above (formatted with 2-space indent, UTF-8, trailing newline).

#### 4.3 Write `.ccb/todo.md`

Render the plan as Markdown checklist:

```markdown
# <Task Name>

**Goal**: <goal>
**Done when**: <doneWhen>

## Steps
- [ ] S1: <title>
- [ ] S2: <title>
...

## Acceptance
- [ ] <criterion 1>
- [ ] <criterion 2>
```

Mark a step `- [x]` only when its `status == "done"` in `state.json`. On initial write all are unchecked.

#### 4.4 Write `.ccb/plan_log.md`

Append-only log. Initial entry:

```markdown
# Plan Log — <Task Name>

## <ISO timestamp> — Plan created
- Steps: N
- Reviewer: <codex|mlx|claude-fallback>  (from /all-plan output)
- Notes: <any key decisions>
```

#### 4.5 Start the auto-loop daemon

```
Bash: bash ~/.claude/skills/tr/scripts/autoloop.sh start
```

Run this from the project root (where `.ccb/` lives). The script is idempotent — if already running it's a no-op.

### 5. Output

```
Plan saved:
- .ccb/todo.md
- .ccb/state.json
- .ccb/plan_log.md

Auto-loop daemon: started

Next: Use /tr to start execution
```

---

## Principles

1. **Collaborative Design**: Uses `/all-plan` for full collaborative planning flow
2. **Coarse-grained**: Titles only, details in /tr
3. **Recoverable**: Context enables continuity after /clear
4. **Research-driven**: Use WebSearch and WebFetch to gather info on unfamiliar tech/APIs/best practices before finalizing the plan
5. **Local-first**: All file I/O by Claude; reasoning second-opinions by local MLX. No codex dependency.
