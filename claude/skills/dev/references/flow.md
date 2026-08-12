# Dev Workflow Execution Flow

Unified end-to-end development workflow. Platform-agnostic core logic.
For platform-specific tool syntax and role mappings, see `adapters/`.

## Input

- `$ARGUMENTS`: Requirement description, or `--resume` to continue from a blocking point

## Terminology

- **Primary Reviewer (主審)**: The platform's own AI. Drafts the plan, reviews code.
- **Plan Reviewer (計劃終審)**: CCB analyst agent. Reviews plan for architectural soundness. On Claude Code: `analyst` (agy + localroles.analyst).
- **Code Reviewer (程式碼終審)**: CCB code-review agent. Cross-reviews final code. On Claude Code: `reviewer1` (coordinator, auto-dispatches to `reviewer2`).
- **Code Writer**: CCB coder agent (`worker2` first, `worker1` as fallback). Outputs code as text; primary reviewer applies files.

Role assignments are defined in each platform's adapter file.

## Resume Handling

If `$ARGUMENTS` is `--resume`:

1. Read `.dev-state.json` from project root
2. If file doesn't exist, inform user: "No active /dev workflow found."
3. Based on `step` field:
   - `final_review_plan_pending`: Execute Phase 2 resume (fetch final reviewer reply for plan)
   - `final_review_code_pending`: Execute Phase 6 resume (fetch final reviewer reply for code)
   - Other: inform user of current state and continue from that phase

---

## Phase 1: Primary Reviewer — Plan Draft + Self-Review

### Step 1.1: Prepare Context

1. Parse user requirement from `$ARGUMENTS`
2. Analyze project structure using Glob/Read (tech stack, key files, existing patterns)
3. **Spec Sync**: 檢查專案 CLAUDE.md 是否有 `spec-source:` 宣告，若有：
   1. 解析路徑（展開 `~` 為 `$HOME`）
   2. 執行 `git -C <spec-path> pull --rebase`
   3. 回報同步結果（updated / already up to date / failed）
   4. 若 pull 失敗，警告但不中斷流程
4. **若任務涉及資料庫**：使用 `/db` 查詢相關表結構（欄位、型別、索引），附在計劃 context 中
5. Read `~/.claude/skills/memory/corrections.jsonl`:
   - If file exists, take last 5 entries (newest first), filter by `project_type` if known
   - Format as correction notes for context injection
   - If file doesn't exist or is empty, skip injection

### Step 1.2: Complexity Classification

Classify task complexity before drafting:

- **simple**: single-file change, no new dependencies, no schema changes, no auth/security path
- **medium**: multi-file change, or touches existing service/controller logic
- **complex**: new feature spanning multiple layers, schema migration, auth change, or cross-service impact

Override: if user includes `--full-review` in requirement, force `complex`.

Output:
```
[COMPLEXITY: simple|medium|complex]
Reason: <one-line justification>
```

### Step 1.3: Draft Plan

Primary reviewer writes the implementation plan directly, covering:

- **Goal**: What this change accomplishes
- **Architecture**: Which files/layers are touched and why
- **Steps**: Ordered implementation steps with clear deliverables
- **Risks**: Main technical risks and mitigation

Inject historical corrections context (from Step 1.1) to avoid repeated mistakes.

### Step 1.4: Four-Dimension Self-Review

Evaluate the drafted plan across four dimensions:

| Dimension | Pass | Warn | Fail |
|-----------|------|------|------|
| Step Completeness | All steps present, deliverables clear | Gaps exist | Major steps missing |
| Dependency Order | Dependencies correctly sequenced | Minor ordering issues | Critical ordering errors |
| Risk Coverage | Main risks identified with mitigations | Partially covered | Major risks ignored |
| Requirement Alignment | Plan solves the stated requirement | Partial drift | Misaligned |

If any dimension is Warn/Fail: revise the plan inline. Record what was corrected.

### Step 1.5: Initialize State and Display

Initialize `.dev-state.json` in project root:

```json
{
  "version": 1,
  "phase": "planning",
  "step": "primary_drafting",
  "requirement": "<user requirement>",
  "complexity": "simple|medium|complex",
  "attempt": { "worker_code": 0 },
  "maxAttempts": { "worker_code": 2 },
  "artifacts": {},
  "corrections": { "plan": [], "code": [] },
  "startedAt": "<ISO timestamp>"
}
```

Display:
```
## Plan Draft (Primary Reviewer)

[COMPLEXITY: {complexity}]

{plan content}

**Self-Review**: [all ✅ / supplemented N dimensions]
```

---

## Phase 2: Final Review — Plan (Blocking, Cross-Review)

**Smart Trimming**: If `complexity` is `simple` or `medium`, skip entirely.
Output: `[Phase 2 SKIPPED — complexity: {complexity}]`. Proceed to Phase 3.

### Step 2.1: Prepare

1. Store final plan text in `.dev-state.json` → `artifacts.plan_draft`
2. Update state: `step: "final_review_plan_pending"`
3. Record any self-review corrections in `corrections.plan`

### Step 2.2: Send to Plan Reviewer

Use platform's async delegation (see adapter for exact command):

```
ask <analyst> "Please review the following implementation plan for architectural soundness:

--- PLAN START ---
<final plan>
--- PLAN END ---

Reply format:
1. Overall assessment (one sentence)
2. Architectural issues or risks found (if any)
3. Missing steps or dependencies (if any)
4. Conclusion: PASS / CONCERN"
```

### Step 2.3: Block and End Turn

After async submission:
- Reply with one line: `analyst processing...`
- **END TURN IMMEDIATELY** (mandatory async guardrail)

### Step 2.4: Resume (when user runs `/dev --resume`)

1. Fetch analyst reply (see adapter for pend command)
2. Process reply:
   - **PASS**: Proceed to Phase 3
   - **CONCERN**: Primary reviewer evaluates the concerns:
     - Agree → apply fix, record correction
     - Disagree → note reason, proceed anyway
3. Update state: `step: "plan_complete"`

---

## Phase 3: Record Plan Corrections

If primary reviewer made any corrections to the plan (self-review supplements, or from final reviewer concerns):

Append to `~/.claude/skills/memory/corrections.jsonl` (unified schema from `~/.claude/skills/memory/schema.md`):

```jsonl
{"timestamp":"<ISO>","provider":"claude","artifact_type":"plan","task_summary":"<one-line summary>","language":"","project_type":"<type>","quality_score":"supplemented","issues":["<what was wrong>"],"corrections":["<what was fixed>"],"severity":"minor","takeover":false}
```

Key fields:
- `provider`: `"claude"` (primary reviewer drafted it)
- `quality_score`: `"pass"` | `"supplemented"`
- `severity`: `"minor"` for ⚠️ dimensions, `"critical"` for ❌ dimensions

If plan passed all dimensions without changes, skip this phase.

Update state: `phase: "development"`, `step: "worker_coding"`

---

## Phase 4: CCB Worker Code Generation

### Step 4.1: Prepare Coding Context

1. Extract implementation steps from the final plan
2. Read `~/.claude/skills/memory/corrections.jsonl`:
   - Take last 5 entries (newest first), filter by `project_type`
   - Format as correction notes for context injection
3. Read existing files referenced in the plan (using Read tool)
4. Determine language from plan content or project context

### Step 4.2: Send to Code Writer

Use `worker2` (primary). If worker2 fails or times out, fall back to `worker1`.
See adapter for exact command syntax.

```
ask worker2 "Implement the following plan. Output only the final code — do not write files yourself, just return the code.

Plan:
<implementation steps>

Existing code context:
<relevant file contents>

Language: <detected language>

Historical corrections (avoid repeating these mistakes):
<last 5 corrections>
"
```

### Step 4.3: Display Result

```
## <code_writer> Code Output

```{language}
{generated code}
```
```

### Step 4.4: Handle Code Writer Errors

- **worker2 no response / timeout** (>5 min): Fall back to `worker1` once. Record the switch.
- **worker1 also fails**: Primary reviewer writes code directly. Record takeover.
- **Empty response from either**: Retry once with simplified prompt. If still empty, primary reviewer takes over.

---

## Phase 5: Primary Reviewer — Code Review (Linus Style)

Apply the **Linus Taste Review Rubric** (`~/.claude/skills/linus-review/rubric.md`).

Dual-pass review: Pass 1 (fatal issues) → Pass 2 (taste score 🟢🟡🔴 + max 3 improvements).

### Decision Logic

| Result | Action |
|--------|--------|
| 🟢 Good taste | Adopt directly. Proceed to Phase 6. |
| 🟡 Passable | Primary reviewer fixes directly. No worker resend. Record corrections. |
| 🔴 Garbage AND `attempt.worker_code < 2` | Send back to `worker1` (fallback coder) with review feedback. Increment `attempt.worker_code`. Return to Step 4.2. |
| 🔴 Garbage AND `attempt.worker_code >= 2` | Primary reviewer takes over coding entirely. Record takeover. |

### Worker Resend Context Format

```
Previous attempt had these issues:
1. [specific issue]
2. [specific issue]
Avoid: [anti-patterns found]
Instead: [correct approach]
```

### Display Review Result

```
## Code Review (Primary Reviewer, Linus Style)

**Taste Score**: [🟢/🟡/🔴] [brief assessment]

**Fatal Issues**: [list or "None"]

**Improvements**:
1. [highest impact]
2. [second]
3. [third]

**Verdict**: [ADOPT / FIXED / RETURNED TO WORKER / TAKEOVER]
```

---

## Phase 6: Final Review — Code (Blocking, Cross-Review)

**Smart Trimming**: If `complexity` is `simple`, skip entirely.
Output: `[Phase 6 SKIPPED — complexity: simple]`. Proceed to Phase 7.

### Step 6.1: Prepare

1. Store final code in `artifacts.code_output`
2. Store changed file list in `artifacts.changed_files`
3. Update state: `step: "final_review_code_pending"`
4. Record any corrections from Phase 5 in `corrections.code`

### Step 6.2: Send to Final Reviewer

```
ask <final_reviewer> "Please review the following code changes:

--- CHANGES START ---
<final code or git diff>
--- CHANGES END ---

Reply format:
1. Security: PASS / CONCERN
2. Performance: PASS / CONCERN
3. Maintainability: PASS / CONCERN
4. Specific issues (if any)
5. Conclusion: PASS / CONCERN"
```

### Step 6.3: Block and End Turn

- Reply with one line: `<final_reviewer> processing...`
- **END TURN IMMEDIATELY** (mandatory async guardrail)

### Step 6.4: Resume

1. Fetch final reviewer reply (see adapter for pend command)
2. Process:
   - **PASS**: Proceed to Phase 7
   - **CONCERN**: Primary reviewer evaluates, apply fixes if agreed
3. Update state: `step: "code_complete"`

---

## Phase 7: Record Code Corrections

If primary reviewer made any corrections to the worker's code:

Append to `~/.claude/skills/memory/corrections.jsonl`:

```jsonl
{"timestamp":"<ISO>","provider":"worker1","artifact_type":"code","task_summary":"<summary>","language":"TypeScript","project_type":"<type>","quality_score":"passable","issues":["missing validation"],"corrections":["added zod schema"],"severity":"minor","takeover":false}
```

Key fields:
- `provider`: `"worker1"` / `"worker2"` / `"claude"` (if takeover)
- `quality_score`: `"good"` | `"passable"` | `"garbage"`
- `severity`: `"minor"` for 🟡, `"major"` for 🔴
- `takeover`: `true` if primary reviewer wrote the code entirely

If no corrections needed (🟢), skip this phase.

---

## Phase 8: Git Commit (No Push)

### Step 8.1: Apply Code Changes

Write the final reviewed code to files using Write/Edit tools.
Only modify the files specified in `artifacts.changed_files`.

### Step 8.2: Pre-commit Check

1. Run `git status` to verify working tree state
2. If there are unrelated uncommitted changes, warn user and ask whether to proceed
3. If there are merge conflicts, inform user and stop
4. **Repo hygiene**: scan `git status --porcelain` untracked entries not in
   `artifacts.changed_files`. Flag any that look like accidental droppings —
   0-byte files, or names with no extension / stray trailing punctuation
   (classic sign of a Chinese phrase pasted into a shell command and
   word-split, e.g. `touch 上架, 下架`). Never `git add -A`/`git add .` these
   in by accident. List them for the user and ask before deleting — do not
   delete without confirmation.

### Step 8.3: Commit

```bash
git add <specific_files>
git commit -m "$(cat <<'EOF'
<type>: <plan goal in one sentence>

- <change summary 1>
- <change summary 2>

Plan: primary review <PASS/SUPPLEMENTED>
Code: <code_writer> + primary review <🟢/🟡/TAKEOVER>

Co-Authored-By: <platform AI signature>
EOF
)"
```

**Type prefix rules** (auto-detected from plan goal):
- `feat`: New feature or capability
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `docs`: Documentation only
- `style`: Formatting, no logic change
- `test`: Adding or updating tests
- `chore`: Build, config, tooling changes

### Step 8.4: Cleanup and Summary

1. Delete `.dev-state.json`
2. Display completion summary:

```
## /dev Workflow Complete

**Requirement**: <one line>
**Plan**: primary review <verdict>
**Code**: <code_writer> + primary review <verdict>
**Final Review**: <final_reviewer> <verdict>
**Commit**: <first 7 chars of commit hash>

Learning feedback recorded: <N> entries (plan: <n1>, code: <n2>)
```

---

## State File Schema

`.dev-state.json` complete structure:

```json
{
  "version": 1,
  "phase": "planning|development|committing|done",
  "step": "primary_drafting|final_review_plan_pending|plan_complete|worker_coding|primary_reviewing_code|final_review_code_pending|code_complete|committing",
  "requirement": "original requirement text",
  "complexity": "simple|medium|complex",
  "attempt": {
    "worker_code": 0
  },
  "maxAttempts": {
    "worker_code": 2
  },
  "artifacts": {
    "plan_draft": "final plan text (after review)",
    "code_output": "final code (after review)",
    "changed_files": ["file1.ts", "file2.ts"]
  },
  "corrections": {
    "plan": [{"dimension": "...", "issue": "...", "fix": "..."}],
    "code": [{"tier": "...", "issue": "...", "fix": "..."}]
  },
  "startedAt": "ISO timestamp"
}
```

---

## Principles

1. Primary reviewer drafts — CCB workers implement — cross-reviewer provides blind-spot check
2. No self-assessment: final reviewer is always a different AI from primary reviewer
3. Maximum 2 worker resend rounds (diminishing returns past that)
4. Learning feedback accumulates: corrections injected into future worker prompts
5. Blocking at final review is a hard quality gate — no skipping for "obvious" changes
6. Git commit is the last step — no push, user decides when to push
7. Maintain the Qing dynasty court official communication style (Traditional Chinese)
