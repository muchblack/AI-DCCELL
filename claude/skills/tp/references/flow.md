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
- **steps**: ordered list of step titles
- **acceptance criteria**: done conditions (finalDone)

### 2.1 Mark Critical Steps

During planning, the designer SHOULD identify steps that warrant MAGI consensus during execution. A step should be marked `critical: true` when it involves:

- **Breaking changes**: API signature changes, database migrations, schema changes
- **Security-sensitive**: Authentication, authorization, encryption logic
- **Cross-cutting**: Changes affecting multiple systems or services
- **Irreversible**: Data transformations, production deployments

In the plan output, steps are represented as objects:

```json
"steps": [{"title": "S1 title", "critical": false}, {"title": "S2 title", "critical": true}]
```

When `critical` is omitted, it defaults to `false`.

---

### 2.5 MAGI Plan Consensus (Mandatory)

After /all-plan completes with a passing review, invoke /magi to obtain three-system consensus on the plan before user confirmation.

#### 2.5.1 Prepare Proposal

Package the /all-plan output as the MAGI proposal:

```
/magi The following implementation plan has passed designer review (score: X.XX/10).
Evaluate whether this plan is architecturally sound, risk-appropriate, and complete.

--- PLAN START ---
[plan_draft from /all-plan output - include goal, steps, architecture, risks, acceptance criteria]
--- PLAN END ---
```

#### 2.5.2 Async Boundary

/magi internally:
1. Claude evaluates as MELCHIOR-1 (sync)
2. Sends /ask codex (BALTHASAR-2) + /ask gemini (CASPER-3)
3. **END TURN** - mandatory async guardrail

Wait for vote completion (hook-driven). Resume when all votes collected.

#### 2.5.3 Handle MAGI Result

| Result | Action |
|--------|--------|
| **SYNCHRONIZED** (all approve) | Proceed to Step 3 (User Confirmation) with consensus summary |
| **PATTERN_BLUE** (any veto) | Show veto reasoning. Revise plan addressing veto concerns, then re-run /magi (max 1 retry). If still vetoed, escalate to user with full vote details. |
| **DISSENT_DETECTED** (mixed, no veto) | Show all votes to user. User decides: adopt majority, choose specific system view, or revise. |
| **INCONCLUSIVE** (abstains) | Show available votes. Proceed to Step 3 with reduced confidence note. |

#### 2.5.4 Display Consensus Summary

After MAGI passes, include in Step 3 confirmation display:

```
**MAGI Consensus**: SYNCHRONIZED (score: M=0.X / B=0.X / C=0.X)
```

---

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
        "steps": [{"title": "S1 title", "critical": false}, {"title": "S2 title", "critical": true}],
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
