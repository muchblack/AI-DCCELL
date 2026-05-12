# AutoFlow Plan

Create executable plan artifacts: `.ccb/todo.md` + `.ccb/state.json` + `.ccb/plan_log.md`

---

## Architecture Note

- Plan mode is optional (recommended for structured planning + review).
- **All file I/O is performed by Claude directly** using Read/Edit/Write tools.
- All reasoning subtasks (e.g. independent design second opinion) route to local MLX via `/mlx-reason`.
- codex retired 2026-05-05; reviewer chain is now mlx → ollama → claude self-audit.

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
4. Reviewer scoring (mlx primary → ollama fallback → claude self-audit, per Reviewer Fallback Protocol)

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

### 2.5 Gemini Consensus Check (MAGI Fallback)

**Purpose**: While MAGI three-AI consensus is unavailable, use Gemini as an adversarial reviewer to challenge the plan before user confirmation. This is the fallback decision gate that replaces the original mandatory MAGI gate. When MAGI is restored, this phase should be replaced (or augmented) by a `/magi` invocation.

**Skip conditions**:
- `cping gemini` fails → log `consensus=claude-only` and proceed to Step 3
- User passed `--no-consensus` in `$ARGUMENTS` → skip with note

**2.5.1 Submit plan for adversarial review**

Send to Gemini via `/ask gemini` (English payload to save tokens, per CLAUDE.md):

```
[ADVERSARIAL PLAN REVIEW — MAGI FALLBACK]

You are an adversarial reviewer. The plan below already passed quantitative scoring (>= 7.0). Your job is to challenge it, NOT rubber-stamp.

Focus on:
1) Hidden assumptions that could break the plan
2) Missed risks or edge cases the scoring reviewer overlooked
3) Better alternative approaches worth considering
4) Steps that are vague, redundant, or in wrong order

Return EXACTLY this format:
VERDICT: agree | disagree | partial
CRITICAL: [list, empty if none]
MAJOR: [list, empty if none]
MINOR: [list, empty if none]
ALTERNATIVES: [list, empty if none]
SUMMARY: one paragraph

--- PLAN START ---
[full plan from /all-plan output, including goal, steps, acceptance, risks]
--- PLAN END ---
```

**Async Guardrail**: if `/ask gemini` returns `[CCB_ASYNC_SUBMITTED`, reply with `Gemini processing...` and END TURN immediately. Resume Phase 2.5.2 when Gemini's response arrives in a later turn.

**2.5.2 Claude evaluates Gemini's critique**

Read Gemini's response with independent judgment — Gemini is unreliable per CLAUDE.md, never rubber-stamp its findings. Classify each flag:

| Gemini's flag                   | Claude's judgment           | Action                                       |
|---------------------------------|-----------------------------|----------------------------------------------|
| Technically sound critical/major | Accept                      | Integrate fix into plan, note in plan_log    |
| Hallucinated / off-topic         | Reject                      | Log as `gemini-drift-rejected`               |
| Style/preference disagreement    | Defer to user               | Present both views in Step 3                 |
| Alternative approach with merit  | Defer to user               | Present both views in Step 3                 |

**2.5.3 Decision outcomes**

Three outcomes feed into Step 3:

- **CONSENSUS** — Gemini agrees, OR all flags rejected as hallucination → proceed to Step 3 unchanged, tag `consensus=gemini-agree`
- **REFINED** — Claude accepted Gemini's flags and integrated fixes → Step 3 presents the revised plan, tag `consensus=gemini-refined`
- **SPLIT** — Genuine disagreement Claude cannot adjudicate → Step 3 presents BOTH views for user to arbitrate, tag `consensus=user-arbitrate`

**2.5.4 Log entry**

Stage this entry for later inclusion in `.ccb/plan_log.md` (written in Step 4.4):

```markdown
## <ISO timestamp> — Gemini Consensus Check (MAGI fallback)
- Provider: gemini
- Verdict: <agree|disagree|partial>
- Counts: critical=N major=N minor=N
- Outcome: <gemini-agree|gemini-refined|user-arbitrate|claude-only>
- Notes: <one-line summary; for refined, list integrated fixes>
```

---

### 3. User Confirmation

Show final plan from `/all-plan` output (revised if Phase 2.5 outcome was `REFINED`):

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
**Consensus**: [gemini-agree | gemini-refined | user-arbitrate | claude-only]
  - If gemini-refined: list integrated fixes
  - If user-arbitrate: present BOTH views below

Confirm? (Y/adjust)
```

If `consensus=user-arbitrate`, append a section:

```
## Disagreement requiring your decision

**Designer (Claude) view**: [position + rationale]
**Adversary (Gemini) view**: [position + rationale]

Which approach do you choose? (designer / gemini / merge / other)
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
- Reviewer: <mlx|ollama|claude-fallback>  (from /all-plan output)
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
2. **Adversarial gate**: Gemini consensus check (Phase 2.5) is the MAGI fallback — challenges the plan before user sees it
3. **Coarse-grained**: Titles only, details in /tr
4. **Recoverable**: Context enables continuity after /clear
5. **Research-driven**: Use WebSearch and WebFetch to gather info on unfamiliar tech/APIs/best practices before finalizing the plan
6. **Local-first**: All file I/O by Claude; reasoning second-opinions by local MLX. No codex dependency.
7. **Reviewer independence**: Phase 2.5 Gemini critique is advisory — Claude must independently judge each flag, never rubber-stamp.
