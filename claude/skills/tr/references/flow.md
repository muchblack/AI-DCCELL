# AutoFlow Run

Execute current step with local-first code routing. Claude writes code directly when routed to local providers; Codex handles state management (preflight/finalize/split).

**File formats**: See `~/.claude/skills/docs/formats.md`
**Protocol**: See `~/.claude/skills/docs/protocol.md`

---

## Execution Flow

**Auto-loop daemon**: started by `/tp` (`bash ~/.claude/skills/tr/scripts/autoloop.sh start`). `/tr` should assume it is running and only ensure the finalize request doesn't stop it.

### 1. Sync Current State (Codex)

State management (read/update `.ccb/state.json`) is still delegated to Codex. Request Codex to:

1. read `.ccb/state.json`
2. validate `current`
3. enforce attempt limits
4. (if proceeding) increment attempts and persist back to `.ccb/state.json`
5. return a compact step context for design

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

- `executor = "smart-router"` (local-first: ollama/mlx → claude → codex)
- `reviewer = "codex"`
- `designer = ["claude", "codex"]`

When `executor = "smart-router"` (default), Step 4 uses `route-task.sh` to dynamically select the provider. When `executor` is set to a specific provider (e.g., `"codex"`, `"claude"`), skip the router and use that provider directly.

Implementation detail: Claude must not read repo files directly; request reads via `/file-op` (`read_file`) and parse JSON locally.

### 2. Step Design (Dual Independent Design)

Perform a lightweight dual design for the current step (not the full `/all-plan` flow — step-level design is smaller scope with context already provided by preflight).

#### 2.1 Claude Independent Design (local, no provider call)

Input: current step title + task objective + relevant files + dependencies from preflight

Output JSON:

```json
{
  "approach": "description of implementation approach",
  "doneConditions": ["condition 1", "condition 2"],
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
Return JSON only: { approach, doneConditions, risks, needsSplit, splitReason, proposedSubsteps }"
```

#### 2.3 Claude Merge (1-2 rounds, Claude leads)

Compare both designs:

- Take union of `doneConditions` (deduplicate, max 2)
- Take union of `risks` (deduplicate)
- Resolve `approach` conflicts — Claude has final decision
- Resolve `needsSplit` — if either says true, evaluate carefully; Claude decides

**Output contract** (merged JSON):

```json
{
  "approach": "string",
  "doneConditions": [
    {"type": "file_exists|grep_match|test_passes|build_succeeds|no_lint_errors|manual", "...": "type-specific fields"},
    "max 3 conditions"
  ],
  "risks": ["string"],
  "needsSplit": true|false,
  "splitReason": "string (optional, if needsSplit=true)",
  "proposedSubsteps": ["string (3-7 items, optional, if needsSplit=true)"]
}
```

`doneConditions` use structured format for Step 8.6 Ralph verification. If `/tp` already provided structured conditions in `state.json`, use those; otherwise Claude generates them based on step context. See `/tp` flow for type definitions.

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

### 4. Route Execution (Smart Router)

Before writing code, determine the optimal provider using the Smart Router.

#### 4.1 Estimate Task Characteristics

From the merged design (Step 2), estimate:

- `type`: `coding` (default for most steps) or `reasoning`
- `complexity`: `simple` (<30 lines, 1 file) / `medium` / `complex` (>200 lines or >5 files)
- `lines`: estimated lines of code to write/modify
- `files`: number of files to change
- `lang`: primary language (e.g., `php`, `vue`, `ts`)
- `security`: `true` if step involves auth, encryption, payment, or user input validation

#### 4.2 Call Smart Router

```bash
bash ~/.claude/skills/scripts/route-task.sh \
  --type <type> --complexity <complexity> --lines <lines> \
  --files <files> --lang <lang> --security <security>
```

Returns JSON: `{"provider":"ollama|mlx|claude","reason":"...","fallback":"claude"}`

Report routing to user: `路由：<Provider>（<reason>，~<lines> 行 <lang>）`

#### 4.3 Health Check (for local providers)

If routed to `ollama` or `mlx`, verify availability:

```bash
bash ~/.claude/skills/scripts/health-check.sh <provider>
```

If provider is down → fall back to `fallback` provider from router output.

### 5. Execute (Provider-Routed)

Execute code writing based on the routed provider. **Claude applies all file changes directly** using Read/Edit/Write tools.

#### 5a. Local Provider (Ollama / MLX)

1. Call the appropriate MCP bridge:
   - Ollama: `mcp__mcp-ai-bridge__ollama_code(task, language, context)`
   - MLX: `mcp__mcp-ai-bridge__mlx_code(task, language, context)`
2. The `task` should include: step approach, target file paths, existing code context, done conditions
3. Review generated code (Claude reviews locally, no separate `/linus-review` yet — that happens in Step 7.5)
4. If code is usable → Claude applies changes via Edit/Write tools
5. If code is garbage → retry once with refined prompt; if still garbage → Claude writes from scratch (counts as fallback to `claude`)
6. Record to `~/.claude/skills/memory/corrections.jsonl` if takeover occurred

#### 5b. Claude Direct

Claude writes code directly using Edit/Write tools based on the merged design approach. No external delegation needed.

#### 5c. Codex Fallback (legacy path)

Only used when explicitly configured (`executor == "codex"` in `.autoflow/roles.json`) or as last-resort fallback:

1. Build `FileOpsREQ` JSON (see `~/.claude/skills/docs/protocol.md`)
2. Send via `/file-op`:
   ```
   /file-op <the FileOpsREQ JSON>
   ```
3. Codex executes and returns `FileOpsRES`

### 6. Collect Changed Files

After execution (regardless of provider), compile the list of changed files for review:

- **Local/Claude path**: Claude already knows which files were changed (from Edit/Write tool calls)
- **Codex path**: Extract from `FileOpsRES.changedFiles`

This list feeds into Step 7 (Handle result) and subsequent review steps.

### 7. Handle Execution Result

#### Local/Claude path (Step 5a / 5b)

Code was applied directly. If all Edit/Write operations succeeded → Go to Step 7.5 (Linus taste).

If any file operation failed (e.g., Edit match failure) → diagnose and retry (max 2 attempts total). If still failing → mark step blocked.

#### Codex path (Step 5c)

Parse `FileOpsRES`:

- **status = ok** → Go to Step 7.5
- **status = ask** → Show questions to user → Re-run
- **status = fail** → Request `autoflow_state_mark_blocked` with `fail.reason` → Stop

### 7.5 Linus Quick Taste (Pre-Review Gate)

Before the formal review, Claude performs a quick Linus-style taste check on the changed files using the `/linus-review` rubric (`~/.claude/skills/linus-review/references/flow.md`).

**Input**: Changed files from FileOpsRES.

**Dual-pass review** (Pass 1: fatal issues → Pass 2: taste score):

| Result               | Action                                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------------------------- |
| 🔴 or CRITICAL found | → Back to Step 5 with fix items. Skip formal `/review` — no point reviewing garbage. (Counts as 1 attempt) |
| 🟡 with HIGH issues  | → Attach findings to Step 8 review context. Formal review proceeds with Linus issues as known concerns.    |
| 🟡 clean or 🟢       | → Proceed to Step 8. No additional action needed.                                                          |

This gate saves cross-reviewer time by catching structural problems early.

### 8. Review (Claude + Cross-Review)

Invoke `/review` skill (include Linus findings from Step 7.5 if any):

```
/review step
  target: [step title]
  doneConditions: [from design output]
  changedFiles: [from FileOpsRES]
  proof: [execution summary]
  linusFindings: [from Step 7.5, if 🟡 with issues]
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

- All pass → Continue to Finalize
- Failures → Analyze cause, decide:
  - Fix issue (Back to step 5 with fix)
  - Mark as known issue (Continue with note)
  - Block (Mark blocked)

**Final Decision** (based on Review + Test):

- Both PASS → Continue to Step 8.6 Verification Gate
- Either FIX → Merge fix items → Back to step 5 (max 1 retry)
- Disagreement → Claude makes final call with explanation

### 8.6 Verification Gate (Ralph)

**Mandatory** functional verification against step's done conditions. Complements Step 7.5 (code quality) and Step 8 (review) with automated correctness checks.

#### Input

- `doneConditions` from Step 2 design output (merged)
- `changedFiles` from FileOpsRES

#### Verification Types

Claude maps each done condition to the appropriate check type:

| Type             | Check Method          | Tool                            |
| ---------------- | --------------------- | ------------------------------- |
| `file_exists`    | File/path existence   | Glob                            |
| `grep_match`     | Content pattern match | Grep                            |
| `test_passes`    | Test command exits 0  | `/file-op` with verify template |
| `build_succeeds` | Build/compile exits 0 | `/file-op` with verify template |
| `no_lint_errors` | Lint command exits 0  | `/file-op` with verify template |
| `manual`         | Cannot auto-verify    | Skip, note in report            |

#### Execution

1. For each done condition, determine check type
2. Execute checks:
   - `file_exists` / `grep_match` → Claude uses Glob/Grep directly (no Codex needed)
   - `test_passes` / `build_succeeds` / `no_lint_errors` → Send to Codex via `/file-op` (template: `../templates/verify.json`)
   - `manual` → Skip, record as `skipped` with reason
3. Compile verification report:

```json
{
  "passed": ["condition 1 description"],
  "failed": [{ "condition": "description", "error": "what went wrong" }],
  "skipped": [{ "condition": "description", "reason": "cannot auto-verify" }]
}
```

#### Decision

| Result                    | Action                                                    |
| ------------------------- | --------------------------------------------------------- |
| All passed (+ skipped OK) | → Step 9 Finalize                                         |
| Any failed, attempts < 2  | → Auto-generate fix, back to Step 5 (counts as 1 attempt) |
| Any failed, attempts >= 2 | → Mark BLOCKED, report to user with failure details       |

#### Key Rules

- Step 8.6 is **always executed** after Step 8 PASS (not optional like 8.5)
- Verification failures generate **targeted fix items** (not generic "please fix"), based on the specific failed condition and error output
- Max 2 total attempts per step (shared counter with Step 7.5 and Step 8 retries)
- `skipped` conditions don't block — they're informational

### 9. Finalize (Codex)

If Step 3 applied a split (`needsSplit=true`):

- Output: `Split applied. Next: first substep. Use /tr (autoloop will trigger if running).`
- Do not mark the step `done` (no execution happened yet).

If PASS (execution path), ask Codex to:

1. mark current step/substep `status: "done"` and advance `current`
2. regenerate `.ccb/todo.md` from `.ccb/state.json`
3. append completion entry to `.ccb/plan_log.md`

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

#### 10.0 Full-Task Linus Taste Audit

Before the formal task review, perform a Linus-style taste audit on ALL changes across the entire task (equivalent to `git diff` from task start).

Apply the full `/linus-review` flow (`~/.claude/skills/linus-review/references/flow.md`):

- Pass 1: Fatal issues across all changed files
- Pass 2: Taste score for the task as a whole

| Result         | Action                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------- |
| 🔴 or CRITICAL | → Append fix steps (Step 10.2 medium issue path). Do NOT proceed to formal review until resolved. |
| 🟡             | → Record taste findings. Proceed to 10.1 with findings attached.                                  |
| 🟢             | → Proceed to 10.1.                                                                                |

This ensures the final deliverable meets taste standards before formal acceptance.

#### 10.1 Full Task Review

Invoke `/review` skill with task mode (include Linus audit results from 10.0 if any):

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
- Recommendations (if any)

---

## Principles

1. **Local-first execution**: Smart Router (Step 4) prioritizes Ollama/MLX → Claude → Codex. Claude applies code directly via Edit/Write tools
2. **Shortest path**: Execute directly, split only when necessary
3. **Binary review**: PASS or FIX, no scoring
4. **Limited iterations**: Max 2 per step
5. **Auto-advance**: State transitions via file updates (Codex handles state management in preflight/finalize)
6. **Taste gate**: Linus quick taste (Step 7.5) catches structural problems before formal review — 🔴 rejects early, saving cross-reviewer time
7. **Verification gate (Ralph)**: Step 8.6 enforces automated functional verification against done conditions — no step finalizes without passing checks
8. **Graceful fallback**: If local provider fails or produces garbage (max 1 retry), fall back through the chain without blocking
