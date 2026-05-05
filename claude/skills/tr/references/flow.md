# AutoFlow Run

Execute current step. Claude performs all file I/O directly (Read/Edit/Write/Bash). Reasoning second-opinions route to local MLX via `/mlx-reason`. Codex is NOT used in this flow.

---

## Execution Flow

**Auto-loop daemon**: started by `/tp` (`bash ~/.claude/skills/tr/scripts/autoloop.sh start`). `/tr` should assume it is running. The finalize step re-triggers the loop via `autoloop.py --once`.

### 1. Preflight (Claude direct)

Claude performs state preflight directly — no external delegation.

1. `Read` `.ccb/state.json`. If not found → output `No plan. Use /tp first.` → Stop.
2. Inspect `current`:
   - If `current.type == "none"` → All done → Show summary → jump to Step 10.
   - Otherwise locate the active step/substep:
     - `step` → `state.steps[stepIndex - 1]` (1-based) or `state.steps[stepIndex]` if 0-based; honour whichever the file already uses.
     - `substep` → `state.steps[stepIndex].substeps[subIndex]`.
3. Enforce attempt limit: if active node's `attempts >= 2` and current run is a retry → mark the node `status: "blocked"`, write back to `.ccb/state.json`, append a `blocked` entry to `.ccb/plan_log.md`, then Stop.
4. Increment `attempts` on the active node and `Write` the updated JSON back to `.ccb/state.json` (atomic: write whole file).
5. Build a compact step context for design:

```
{
  "title": "<step title>",
  "objective": <state.objective>,
  "keyFiles": <state.context.keyFiles>,
  "doneConditions": <node.doneConditions>,
  "previousSummary": "<from last plan_log entry, if any>"
}
```

### 1.5 Resolve Roles Config

Two-layer resolution:

1. **CLAUDE.md Role Assignment table** (primary): `reviewer` and `designer` roles map to providers. Reviewer Fallback Protocol applies — codex unavailable falls back to MLX with Claude audit gate.
2. **`.autoflow/roles.json`** (override): If this file exists in repo with `enabled == true` and `schemaVersion == 1`, its fields override.

Defaults for this flow:

- `executor = "smart-router"` (local-first: ollama/mlx → claude)
- `reviewer = "mlx"` via `/mlx-reason` + Claude audit gate (codex usage removed from `/tp` and `/tr`; if user wants codex review, invoke `/review` skill explicitly which handles its own routing per CLAUDE.md)
- `designer = ["claude", "mlx"]` — Claude leads, MLX provides second opinion

When `executor = "smart-router"` (default), Step 4 uses `route-task.sh` to dynamically select the provider. When `executor` is set to a specific provider (e.g., `"claude"`, `"mlx"`), skip the router and use that provider directly.

Implementation: `Read` `.autoflow/roles.json` if present; otherwise rely on CLAUDE.md defaults above.

### 2. Step Design (Dual Independent Design)

Lightweight dual design for the current step (not the full `/all-plan` flow — step-level is smaller scope with context already provided by preflight).

#### 2.1 Claude Independent Design

Input: current step title + task objective + relevant files + dependencies from preflight.

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

#### 2.2 MLX Independent Design (via `/mlx-reason`)

```
/mlx-reason "Independent step design — produce a second opinion.
Step: [title]
Context: [objective, relevant files, dependencies]
Return JSON only with keys: approach, doneConditions, risks, needsSplit, splitReason, proposedSubsteps"
```

Claude MUST audit the MLX response before merging:

- **Grounding**: does the approach reference the actual files / objective from preflight, or hallucinate unrelated artifacts?
- **Schema**: does the JSON parse and contain all required keys?
- **Sanity**: are `doneConditions` testable; are `risks` real?

If audit fails → discard MLX output, proceed with Step 2.1 only, record `secondaryDesigner: "claude-fallback"` in the merge output.

#### 2.3 Claude Merge (Claude leads)

Compare both designs:

- Take union of `doneConditions` (deduplicate, max 3)
- Take union of `risks` (deduplicate)
- Resolve `approach` conflicts — Claude has final decision
- Resolve `needsSplit` — if either says true, evaluate carefully; Claude decides

**Output contract** (merged JSON):

```json
{
  "approach": "string",
  "doneConditions": [
    {"type": "file_exists|grep_match|test_passes|build_succeeds|no_lint_errors|manual", "...": "type-specific fields"}
  ],
  "risks": ["string"],
  "needsSplit": true|false,
  "splitReason": "string (optional, if needsSplit=true)",
  "proposedSubsteps": ["string (3-7 items, optional, if needsSplit=true)"],
  "secondaryDesigner": "mlx | claude-fallback"
}
```

If `/tp` already provided structured `doneConditions` in `state.json`, prefer those; otherwise Claude generates them. See `/tp` flow for type definitions.

### 3. Split Check (Before Execution)

After the design merge, decide whether this step must be split into substeps:

- If `needsSplit=false` → continue to Step 4 (execution path)
- If `needsSplit=true` → validate and apply split, skip execution and jump to Step 9 (Finalize output)

Validation rules for `proposedSubsteps`:

- Count: 3-7
- Atomic: single action each
- No overlap; correct order

If valid, apply split directly:

1. `Read` `.ccb/state.json`
2. Set `state.steps[stepIndex].substeps = [{ index: 1, title, status: "pending", attempts: 0, doneConditions: [] }, ...]` (one entry per proposed substep, Claude assigns reasonable doneConditions per substep or leaves empty for later refinement)
3. Set `state.steps[stepIndex].status = "doing"`
4. Update `state.current = { type: "substep", stepIndex, subIndex: <first substep index> }`
5. `Write` `.ccb/state.json` back
6. Regenerate `.ccb/todo.md` (re-render Markdown checklist from updated `state.json`)
7. Append entry to `.ccb/plan_log.md`: `## <ISO ts> — Step N split into M substeps`

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

If provider is down → fall back to `fallback` provider from router output (typically `claude`).

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

### 6. Collect Changed Files

After execution, compile the list of changed files for review. Claude already knows which files were changed from its own Edit/Write tool calls — keep an internal list as you edit.

This list feeds into Step 7 (Handle result) and subsequent review steps.

### 7. Handle Execution Result

Code was applied directly. If all Edit/Write operations succeeded → Go to Step 7.5 (Linus taste).

If any file operation failed (e.g., Edit match failure):

- Diagnose and retry (max 2 attempts total per step, shared with later retry counters)
- If still failing → mark step `status: "blocked"` in `.ccb/state.json` with a `blockedReason`, log to `.ccb/plan_log.md`, Stop.

### 7.5 Linus Quick Taste (Pre-Review Gate)

Before the formal review, Claude performs a quick Linus-style taste check on the changed files using the `/linus-review` rubric (`~/.claude/skills/linus-review/references/flow.md`).

**Input**: Changed files from Step 6.

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
  changedFiles: [from Step 6]
  proof: [execution summary]
  linusFindings: [from Step 7.5, if 🟡 with issues]
```

The `/review` skill applies the Reviewer Fallback Protocol: probe codex via `ccb-mounted`, route to MLX with Claude audit gate when codex is unavailable. `/tr` does not call codex directly — `/review` owns that decision.

Output: Review result with verdict (PASS/FIX/BLOCKED).

### 8.5 Test (Optional)

**Claude decides whether testing is needed** based on step nature:

- Code changes → usually needs testing
- Config/doc changes → usually not
- Refactoring → needs regression testing

If testing is needed, Claude runs the test command directly via Bash:

```
Bash: <test command, e.g. `php artisan test --filter=FooTest` or `npm test`>
```

For Laravel/PHP projects, prefer the `/php-exec` route (which wraps `podman exec` per project conventions).

**Claude reviews test results**:

- All pass → Continue to Step 8.6
- Failures → Analyze cause, decide:
  - Fix issue (Back to step 5 with fix)
  - Mark as known issue (Continue with note)
  - Block (Mark blocked, write to state.json, log to plan_log.md)

**Final Decision** (based on Review + Test):

- Both PASS → Continue to Step 8.6 Verification Gate
- Either FIX → Merge fix items → Back to step 5 (max 1 retry)
- Disagreement → Claude makes final call with explanation

### 8.6 Verification Gate (Ralph)

**Mandatory** functional verification against step's done conditions. Complements Step 7.5 (code quality) and Step 8 (review) with automated correctness checks.

#### Input

- `doneConditions` from Step 2 design output (merged)
- `changedFiles` from Step 6

#### Verification Types

Claude maps each done condition to the appropriate check type:

| Type             | Check Method          | Tool                              |
| ---------------- | --------------------- | --------------------------------- |
| `file_exists`    | File/path existence   | Glob                              |
| `grep_match`     | Content pattern match | Grep                              |
| `test_passes`    | Test command exits 0  | Bash (run `command`, check `$?`)  |
| `build_succeeds` | Build/compile exits 0 | Bash                              |
| `no_lint_errors` | Lint command exits 0  | Bash                              |
| `manual`         | Cannot auto-verify    | Skip, note in report              |

#### Execution

1. For each done condition, determine check type
2. Execute checks directly:
   - `file_exists` → `Glob` with the path
   - `grep_match` → `Grep` with pattern + path
   - `test_passes` / `build_succeeds` / `no_lint_errors` → `Bash` with the supplied command (timeout 120s default; surface stdout/stderr for diagnostic)
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

### 9. Finalize (Claude direct)

If Step 3 applied a split (`needsSplit=true`):

- Output: `Split applied. Next: first substep. Use /tr (autoloop will trigger).`
- Do not mark the step `done` (no execution happened yet).

If PASS (execution path), Claude finalizes by:

1. **Update `.ccb/state.json`**:
   - Mark current step/substep `status: "done"`
   - Advance `current`:
     - If a substep just finished and more substeps remain → `current = { type: "substep", stepIndex, subIndex: <next> }`
     - If last substep finished → mark parent step `done`, advance to next pending step → `current = { type: "step", stepIndex: <next> }`
     - If last step finished → `current = { type: "none" }`
   - `Write` the file atomically (whole file rewrite).
2. **Regenerate `.ccb/todo.md`** from the updated `.ccb/state.json` (re-render checklist with `[x]` for `done`, `[ ]` for `pending`/`doing`, `[!]` for `blocked`).
3. **Append to `.ccb/plan_log.md`**:

```markdown
## <ISO ts> — Step N (<title>) complete
- Verification: <one-liner from /review or Step 8.6>
- Changed files: <list>
- Reviewer: <codex|mlx|claude-fallback>
```

4. **Auto-commit** (if repo is a git repo):

```
Bash: git add -A && git commit -m "Step N: <title>" --allow-empty || true
```

5. **Trigger auto-loop**:

```
Bash: python3 ~/.claude/skills/tr/scripts/autoloop.py --repo-root . --once
```

This re-fires `/tr` for the next step if any remain. The autoloop script handles cooldown and context-budget checks.

Output:

- If more steps: `Step N complete. Next: [title]. Use /tr (autoloop triggered)`
- If all done: `Task complete!` + acceptance checklist → Continue to Step 10 (Final Review)

### 10. Final Review (Task Completion Only)

Triggered when Step 9 detects `current.type == 'none'`.

#### 10.0 Full-Task Linus Taste Audit

Before formal task review, perform a Linus-style taste audit on ALL changes across the entire task (equivalent to `git diff` from task start).

Apply the full `/linus-review` flow (`~/.claude/skills/linus-review/references/flow.md`):

- Pass 1: Fatal issues across all changed files
- Pass 2: Taste score for the task as a whole

| Result         | Action                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------- |
| 🔴 or CRITICAL | → Append fix steps (Step 10.2 medium issue path). Do NOT proceed to formal review until resolved. |
| 🟡             | → Record taste findings. Proceed to 10.1 with findings attached.                                  |
| 🟢             | → Proceed to 10.1.                                                                                |

#### 10.1 Full Task Review

Invoke `/review` skill with task mode (include Linus audit results from 10.0 if any):

```
/review task
  target: [task name from state.json]
  doneConditions: [acceptance criteria]
  changedFiles: [all files changed during task]
  proof: [all step summaries]
```

`/review` routes to codex/mlx per Reviewer Fallback Protocol. `/tr` does not call codex directly.

Output: Task-level review result.

#### 10.2 Issue Handling

Based on review results:

- **No issues** → Go to 10.3 Summary Report
- **Minor issues** (typo, minor fix) → Claude fixes directly with Edit/Write, optionally re-test, then go to 10.3
- **Medium issues** (need 1-2 extra steps) → Append steps to current task:
  1. Claude designs 1-2 fix steps (with `doneConditions`)
  2. `Read` `.ccb/state.json`, append the new steps to `state.steps`, set `current = { type: "step", stepIndex: <appended index> }`, `Write` back
  3. Regenerate `.ccb/todo.md`
  4. Re-trigger `/tr` via `python3 ~/.claude/skills/tr/scripts/autoloop.py --repo-root . --once` to execute appended steps
  5. After completion, re-enter Step 10
  - Cap: max 2 appended steps per task; if exceeded → escalate to "large issues"
- **Large issues** (need >2 steps) → Create follow-up task:
  1. Record unresolved issues in final report
  2. Prompt user: `Found N larger issues, suggest creating new task: /tp [follow-up description]`
  3. Go to 10.3 to complete current task report
- **Unreasonable requirement** → Record reason, skip fix, go to 10.3

#### 10.3 Summary Report

Claude generates the report content directly and writes it to `final/<taskName>-report.md`:

1. Claude composes Markdown `reportContent` (see structure below)
2. `Bash: mkdir -p final`
3. `Write` to `final/<sanitized-taskName>-report.md`

Optional documenter override (rare): if `documenter = "gemini"` is set in `.autoflow/roles.json`, Claude calls `/ask gemini` to generate the markdown body, then writes the file itself with Write. Default is Claude direct.

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

1. **Local-first execution**: Smart Router (Step 4) prioritizes Ollama/MLX → Claude. Claude applies code directly via Edit/Write tools.
2. **Local-first reasoning**: Second-opinion design routes to MLX via `/mlx-reason`; Claude audits MLX output before merging.
3. **Claude-direct file I/O**: All `.ccb/*` mutations performed by Claude with Read/Edit/Write/Bash. No FileOpsREQ, no codex.
4. **Shortest path**: Execute directly, split only when necessary.
5. **Binary review**: PASS or FIX, no scoring at step level.
6. **Limited iterations**: Max 2 per step.
7. **Auto-advance**: State transitions via direct file writes; autoloop re-fires `/tr` after each finalize.
8. **Taste gate**: Linus quick taste (Step 7.5) catches structural problems before formal review — 🔴 rejects early, saving cross-reviewer time.
9. **Verification gate (Ralph)**: Step 8.6 enforces automated functional verification against done conditions — no step finalizes without passing checks.
10. **Graceful fallback**: If local provider fails or produces garbage (max 1 retry), fall back to Claude direct without blocking.
