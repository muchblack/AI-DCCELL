# AutoFlow Run

Execute current step while Claude stays in plan mode and Codex performs all file I/O.

**File formats**: See `~/.claude/skills/docs/formats.md`
**Protocol**: See `~/.claude/skills/docs/protocol.md`

---

## Execution Flow

**Auto-loop daemon**: started by `/tp` (`bash ~/.claude/skills/tr/scripts/autoloop.sh start`). `/tr` should assume it is running and only ensure the finalize request doesn't stop it.

### 1. Sync Current State (Codex)

Claude does not read/modify repo files directly. Request Codex to:
1) read `.ccb/state.json`
2) validate `current`
3) enforce attempt limits
4) (if proceeding) increment attempts and persist back to `.ccb/state.json`
5) return a compact step context for design

Call `/file-op` with `FileOpsREQ`:
- Template: `../templates/preflight.json`

Interpret `FileOpsRES`:
- If no plan → show `No plan. Use /tp first.` → Stop
- If `current.type == "none"` → All done → Show summary → Stop
- If attempts exceeded → request `autoflow_state_mark_blocked` with a reason → Stop
- Otherwise use `data.stepContext` + `data.state.current` for Step Design

### 1.5 Resolve Roles Config

Goal: support `reviewer` / `designer` routing.

Two-layer resolution:

1. **CLAUDE.md Role Assignment table** (primary): Read the Role Assignment table from CLAUDE.md context. The `reviewer` and `designer` roles map to providers.
2. **`.autoflow/roles.json`** (override): If this file exists in the repo, and `enabled == true` and `schemaVersion == 1`, use its fields to override.

Default roles:
- `executor = "codex"`
- `reviewer = "codex"`
- `designer = ["claude", "codex"]`

Implementation detail: Claude must not read repo files directly; request reads via `/file-op` (`read_file`) and parse JSON locally.

### 2. Step Design (Dual Independent Design)

Perform a lightweight dual design for the current step (not the full `/all-plan` flow — step-level design is smaller scope with context already provided by preflight).

#### 2.1 Claude Independent Design (local, no provider call)

Input: current step title + task objective + relevant files + dependencies from preflight

Output JSON:
```json
{
  "approach": "description of implementation approach",
  "doneConditions": [
    { "type": "grep_match", "pattern": "export function Button", "path": "src/components/Button.tsx" },
    { "type": "manual", "description": "Verify the button renders correctly in browser" }
  ],
  "risks": ["risk 1"],
  "needsSplit": false,
  "splitReason": null,
  "proposedSubsteps": null
}
```

#### 2.2 Codex Independent Design (via `/ask codex`)

```
/ask codex "Independent step design:
Step: [title]
Context: [objective, relevant files, dependencies]
Use structured doneConditions from ~/.claude/skills/docs/done-conditions.md.
Return JSON only: { approach, doneConditions, risks, needsSplit, splitReason, proposedSubsteps }"
```

#### 2.3 Claude Merge (1-2 rounds, Claude leads)

Compare both designs:
- Take union of `doneConditions` (deduplicate, max 2)
- Take union of `risks` (deduplicate)
- Resolve `approach` conflicts — Claude has final decision
- Resolve `needsSplit` — if either says true, evaluate carefully; Claude decides

`doneConditions` should prefer machine-verifiable structured objects. Legacy string entries are allowed only for backward compatibility and are treated as `manual` downstream.

**Output contract** (merged JSON):
```json
{
  "approach": "string",
  "doneConditions": [
    { "type": "file_exists", "pattern": "path/to/file" },
    { "type": "manual", "description": "human verification note" }
  ],
  "risks": ["string"],
  "needsSplit": true|false,
  "splitReason": "string (optional, if needsSplit=true)",
  "proposedSubsteps": ["string (3-7 items, optional, if needsSplit=true)"]
}
```

### 3. Split Check (Before Execution)

After the design merge, decide whether this step must be split into substeps:

- If `needsSplit=false` → continue to Step 4 (execution path)
- If `needsSplit=true` → validate and apply split, then skip execution and jump to Step 9 (Finalize output)

Validation rules for `proposedSubsteps`:
- Count: 3-7
- Atomic: single action each
- No overlap; correct order

If valid, apply split via `/file-op` (use `data.state.current.stepIndex` from Preflight):
- Template: `../templates/split.json`

Then go to Step 9 (Finalize) and output the split result (no execution performed).

### 4. Build Step FileOpsREQ (Execution)

Based on merged approach:
- Build `FileOpsREQ` JSON (see `~/.claude/skills/docs/protocol.md`)
- Include agreed done conditions
- Note identified risks

Key rule: Codex may modify code and artifacts needed to satisfy done conditions, but must **not** advance the step to `done` until Claude approves in Review.

### 5. Send FileOpsREQ (FileOps)

Send the constructed FileOpsREQ via `/file-op`:

```
/file-op <the FileOpsREQ JSON>
```

(`/file-op` handles routing to Codex via `CCB_CALLER=claude ask codex`)

### 6. Execute (Executor Routing)

- If `executor == "codex"`:
  - Codex directly executes FileOpsREQ operations and returns FileOpsRES.
- If `executor == "opencode"`:
  - Codex uses the internal `oask` skill to call OpenCode.
  - Codex acts as supervisor:
    - Translate FileOpsREQ ops into OpenCode-friendly instructions
    - Guide OpenCode step-by-step to apply changes and run commands
    - Review OpenCode results and validate against done conditions
    - If fixes are needed, guide OpenCode to iterate (respect `constraints.max_attempts`)
  - Codex returns the final FileOpsRES (JSON only) back to Claude.

### 7. Handle FileOpsRES (Codex or OpenCode)

**status = ok** → Go to Taste Pre-screen (Step 7.5)

**status = ask** → Show questions to user → Re-run

**status = fail** → Request `autoflow_state_mark_blocked` with `fail.reason` → Stop

Note: `status = split` should be handled by Step 3 (Split Check). Treat unexpected `split` here as `fail` and re-run design to decide `needsSplit`.

### 7.5 Taste Pre-screen (Linus Review)

Quick Claude-local taste check before investing in formal cross-review. Invoke `/linus-review` on the changed files from FileOpsRES:

```
/linus-review <changed files from FileOpsRES>
```

**Decision based on result:**

- **🔴 Garbage or CRITICAL fatal issues** → Short-circuit: skip Step 8 formal review. Back to Step 4 with linus-review feedback as fix guidance (counts toward step attempt limit). **Auto-log to `.ccb/notepad.md`** (if exists): append `[LINUS 🔴] <step title>: <fatal issue summary>` (max 3 lines).
- **🟡 Passable** → Proceed to Step 8 formal `/review`.
- **🟢 Good taste** → Proceed to Step 8 formal `/review`.

This step is Claude-local (no external provider calls) and acts as a fast-fail gate to avoid wasting Codex tokens on code that clearly needs rework.

**Notepad integration**: When result is 🔴, the failure summary is persisted to `.ccb/notepad.md` so it survives context compression. This is especially valuable for recurring quality issues that inform future sessions.

### 7.6 Security Scan (Conditional)

**Trigger condition**: Run when changed files include any of:
- API route definitions or controllers
- Authentication/authorization logic (middleware, guards, policies)
- Database queries (especially raw/custom)
- File upload handling
- User input processing

If triggered, invoke `security-reviewer` agent (model: sonnet) on the changed files:

```
Agent(subagent_type: "general-purpose", model: "sonnet")
  "You are security-reviewer. Review these files for OWASP Top 10 issues: [changed files]"
```

**Decision:**
- 🔴 CRITICAL found → Back to Step 4 with security fix guidance (counts toward attempt limit). Auto-log to `.ccb/notepad.md`: `[SEC 🔴] <step title>: <vulnerability summary>`.
- 🟡 WARNING only → Proceed to Step 8. Log warnings to notepad for tracking.
- 🟢 Clean → Proceed to Step 8.

This step uses a sonnet subagent (cost-aware: security checklists don't need opus reasoning depth).

### 8. Review (Claude + Cross-Review)

Invoke `/review` skill:

```
/review step
  target: [step title]
  doneConditions: [from design output]
  changedFiles: [from FileOpsRES]
  proof: [execution summary]
```

See `../../review/references/flow.md` for full flow (Claude assessment → role-routed cross-review → Final decision).

Output: Review result with verdict (PASS/FIX/BLOCKED).

### 8.5 Test (Optional)

**Claude decides whether testing is needed** based on step nature:
- Code changes → usually needs testing
- Config/doc changes → usually not
- Refactoring → needs regression testing

If testing is needed, send test task to Codex:

```
Bash(CCB_CALLER=claude ask codex "Run tests for this change:

Step: [step title]
Changed files: [list]
Test scope: [unit/integration/e2e]

Execute relevant tests and report:
1. Test command(s) executed
2. Pass/Fail summary
3. Any failures with details", run_in_background=true)
```

**Claude reviews test results**:
- All pass → Continue to Verification Gate (Step 8.6)
- Failures → Analyze cause, decide:
  - Fix issue (Back to step 5 with fix)
  - Mark as known issue (Continue with note)
  - Block (Mark blocked)

**Final Decision** (based on Review + Test):
- Both PASS → Verification Gate
- Either FIX → Merge fix items → Back to step 5 (max 1 retry)
- Disagreement → Claude makes final call with explanation

### 8.6 Verification Gate (Ralph)

Mandatory auto-verification of structured doneConditions before finalize. Reference: `~/.claude/skills/docs/done-conditions.md`.

**8.6.1 Iterate doneConditions**

For each doneCondition from the Step 2 design output:

1. **String (legacy)** → convert to `{ type: "manual", description: <string> }` → skip auto-verify
2. **Object with type** → execute type-specific verification:

| Type | Verification | Tool |
|------|-------------|------|
| `file_exists` | Glob(pattern) returns >= 1 match | Glob |
| `grep_match` | Grep(pattern, path) returns >= 1 match | Grep |
| `test_passes` | Bash(cmd) exit code == 0 | Bash |
| `build_succeeds` | Bash(cmd) exit code == 0 | Bash |
| `no_lint_errors` | Bash(cmd) exit code == 0 | Bash |
| `manual` | Skip — flag for human confirmation | — |

**8.6.2 Design-Execution Consistency Check**

Compare the Step 2 design `approach` description against actual `changedFiles` from FileOpsRES:
- If design mentions files/modules that were NOT changed → flag as warning
- If changed files were NOT mentioned in design → flag as warning
- Warnings are informational, not blocking — but logged to notepad if notepad exists

**8.6.3 Result Handling**

- **All auto-verifiable PASS** + manual skipped → proceed to Step 9 (Finalize)
- **Any auto-verifiable FAIL** → enter auto-fix loop:
  1. Send fix request back to Step 5 (FileOpsREQ with failure details)
  2. After fix, run **linus-review re-check** on changed files:
     - If taste stays 🟡 or improves to 🟢 → re-verify doneConditions
     - If taste degrades to 🔴 → force BLOCKED (do not retry further)
  3. Max 2 auto-fix attempts total (shared with step attempt limit)
  4. If retries exhausted → mark step BLOCKED with failure summary
- **BLOCKED** → write failure summary + `pit_stop_needed: true` to `.ccb/notepad.md` (if notepad mechanism is active)

### 8.7 De-Sloppify Pass (Optional)

**Trigger condition**: Run when the step involved substantial code generation (new files, large diffs). Skip for config changes, docs, or small edits.

Invoke `refactor-cleaner` agent (model: sonnet) on changed files:

```
Agent(subagent_type: "general-purpose", model: "sonnet")
  "You are refactor-cleaner. De-sloppify these files (subtraction-only, no behavior changes): [changed files]
   Remove: defensive bloat, dead code, over-abstraction, AI noise, test bloat.
   Keep: boundary error handling, audit logging, public API types."
```

**Rules:**
- This is subtraction-only — never adds code or changes behavior
- Applied AFTER review passes, not before (don't clean code that might get rejected)
- If the pass removes > 20% of lines, flag for human review before applying
- Uses sonnet subagent (cost-aware: checklist-based work)

### 9. Finalize (Codex)

If Step 3 applied a split (`needsSplit=true`):
- Output: `Split applied. Next: first substep. Use /tr (autoloop will trigger if running).`
- Do not mark the step `done` (no execution happened yet).

If PASS (execution path), ask Codex to:
1) mark current step/substep `status: "done"` and advance `current`
2) regenerate `.ccb/todo.md` from `.ccb/state.json`
3) append completion entry to `.ccb/plan_log.md`

Send `FileOpsREQ` with `purpose: "finalize_step"` via `/file-op`. Codex returns `FileOpsRES` JSON only.

Auto-loop requirement (reliable next-step trigger):
- After finalizing, Codex must run the auto-loop trigger (see `autoflow_auto_loop` in `~/.claude/skills/docs/protocol.md`; implemented as an explicit `run` op).
- If there are remaining steps, it must trigger the next `/tr` automatically.
- It must be executed via the FileOpsREQ protocol (no manual copy/paste).

Recommended: combine finalize + auto-loop in one request (ops execute in order):
- Template: `../templates/finalize.json`

Output result:
- If more steps: `Step N complete. Next: [title]. Use /tr`
- If all done: `Task complete!` + acceptance checklist → Continue to Step 10 (Final Review)

### 10. Final Review (Task Completion Only)

Triggered when Step 9 Finalize detects all steps completed (`current.type == 'none'`).

#### 10.1 Full Task Review

Invoke `/review` skill with task mode:

```
/review task
  target: [task name from state.json]
  doneConditions: [acceptance criteria]
  changedFiles: [all files changed during task]
  proof: [all step summaries]
```

See `../../review/references/flow.md` for full flow.

Output: Task-level review result.

#### 10.2 Issue Handling

Based on review results:

- **No issues** → Go to 10.3 Summary Report
- **Minor issues** (typo, minor fix) → Have Codex fix directly, optionally re-test, then go to 10.3
- **Medium issues** (need 1-2 extra steps) → Append steps to current task:
  1. Claude designs 1-2 fix steps
  2. Call `/file-op` to append steps to `.ccb/state.json`:
     - Template: `../templates/append-steps.json`
  3. Continue executing `/tr` to complete appended steps
  4. After completion, re-enter Step 10
- **Large issues** (need >2 steps) → Create follow-up task:
  1. Record unresolved issues in final report
  2. Prompt user: "Found N larger issues, suggest creating new task: /tp [follow-up description]"
  3. Go to 10.3 to complete current task report
- **Unreasonable requirement** → Record reason, skip fix, go to 10.3

#### 10.3 Summary Report

Claude plans report structure and generates `reportContent`:
- `documenter = "codex"` (default): Claude generates `reportContent` directly
- `documenter = "gemini"`: Claude calls `/ask gemini` to generate `reportContent` (markdown), then has Codex write the file

Codex writes `reportContent` to `final/` folder:

- Template: `../templates/final-report.json`

**Report structure**:
- Task Overview
- Implementation Summary
- Steps Executed
- Key Decisions
- Issues Encountered & Resolutions
- Final Verification Results
- Notepad Archive (if `.ccb/notepad.md` exists and is non-empty, include its contents)
- Recommendations (if any)

---

## Principles

1. **Shortest path**: Execute directly, split only when necessary
2. **Binary review**: PASS or FIX, no scoring
3. **Limited iterations**: Max 2 per step
4. **Auto-advance**: State transitions via file updates
