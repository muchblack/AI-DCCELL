# Dev Workflow Execution Flow

Unified end-to-end development workflow. Platform-agnostic core logic.
For platform-specific tool syntax and role mappings, see `adapters/`.

## Input

- `$ARGUMENTS`: Requirement description, or `--resume` to continue from a blocking point

## Terminology

- **Primary Reviewer (主審)**: The platform's own AI. Performs plan and code review.
- **Final Reviewer (終審)**: A different AI (cross-review). Provides second opinion.
- **MLX**: Local reasoning model (Qwen3-14B on localhost:8090). Drafts plans.
- **Ollama**: LAN code generation model (192.168.1.206:11434, model configured via `OLLAMA_MODEL` env var). Writes code.

Role assignments are defined in each platform's adapter file.

## Resume Handling

If `$ARGUMENTS` is `--resume`:

1. Read `.dev-state.json` from project root
2. If file doesn't exist, inform user: "No active /dev workflow found."
3. Based on `step` field:
   - `final_review_plan_pending`: Execute Phase 3 resume (fetch final reviewer reply for plan)
   - `final_review_code_pending`: Execute Phase 7 resume (fetch final reviewer reply for code)
   - Other: inform user of current state and continue from that phase

---

## Phase 1: MLX Plan Drafting

### Step 1.1: Prepare Context

1. Parse user requirement from `$ARGUMENTS`
2. Analyze project structure using Glob/Read (tech stack, key files, existing patterns)
3. **Spec Sync**: 檢查專案 CLAUDE.md 是否有 `spec-source:` 宣告，若有：
   1. 解析路徑（展開 `~` 為 `$HOME`）
   2. 執行 `git -C <spec-path> pull --rebase`
   3. 回報同步結果（updated / already up to date / failed）
   4. 若 pull 失敗，警告但不中斷流程
4. **若任務涉及資料庫**：使用 `/db` 查詢相關表結構（欄位、型別、索引），附在 MLX context 中
4. Read `~/.claude/skills/memory/corrections.jsonl`:
   - If file exists, take last 5 entries (by timestamp, newest first)
   - Format as human-readable correction notes for context injection
   - If file doesn't exist or is empty, skip injection
4. Initialize `.dev-state.json` in project root:

```json
{
  "version": 1,
  "phase": "planning",
  "step": "mlx_drafting",
  "requirement": "<user requirement>",
  "attempt": { "mlx_plan": 0, "ollama_code": 0 },
  "maxAttempts": { "mlx_plan": 2, "ollama_code": 2 },
  "artifacts": {},
  "corrections": { "plan": [], "code": [] },
  "startedAt": "<ISO timestamp>"
}
```

### Step 1.1b: Complexity Classification

After analyzing the project structure, classify task complexity using the **Complexity Classifier** (`~/.claude/skills/docs/complexity-classifier.md`).

Output:
```
[COMPLEXITY: simple|medium|complex]
Reason: <one-line justification>
```

Store in `.dev-state.json` as `complexity` field. This determines which phases to skip:
- **simple**: skip Phase 3 (plan cross-review) + Phase 7 (code cross-review)
- **medium**: skip Phase 3 (plan cross-review)
- **complex**: full workflow

Override: if user includes `--full-review` in requirement, force `complex`.

### Step 1.2: Send to MLX

Call MCP tool (see adapter for exact syntax):

```
mlx_analyze(
  requirement="Based on the following requirement, write an implementation plan including: goal, architecture, implementation steps, risks:\n<requirement>",
  context="Project structure:\n<summary>\n\nHistorical corrections (avoid repeating mistakes):\n<last 5 corrections>",
  thinking=true
)
```

### Step 1.3: Display Result

```
## MLX (Qwen3-14B) Plan Draft

**Model**: mlx-community/Qwen3-14B-4bit | **Inference time**: {durationMs}ms

{MLX plan draft verbatim}
```

### Step 1.4: Handle MLX Errors

- **Unreachable** (localhost:8090): Inform user, primary reviewer writes plan directly. Skip to Phase 2 with reviewer-authored plan.
- **Timeout** (>3 min): Same fallback.
- **Empty response**: Retry once with simplified requirement. If still empty, fallback to primary reviewer.

---

## Phase 2: Primary Reviewer — Four-Dimension Plan Review

The primary reviewer (platform's own AI) evaluates the MLX plan using four dimensions:

### Four-Dimension Framework

**Dimension 1: Step Completeness**
- Are all necessary implementation steps included?
- Are deliverables clear for each step?
- Rating: ✅ Complete / ⚠️ Gaps exist / ❌ Major steps missing

**Dimension 2: Dependency Correctness**
- Are step dependencies correctly ordered?
- Are external dependencies (libraries, services) identified?
- Rating: ✅ Correct / ⚠️ Minor ordering issues / ❌ Critical dependency errors

**Dimension 3: Risk Coverage**
- Are main technical risks identified?
- Are mitigation strategies reasonable?
- Rating: ✅ Covered / ⚠️ Partially covered / ❌ Major risks ignored

**Dimension 4: Requirement Alignment**
- Does the plan actually solve the stated requirement?
- Are there scope creep or missing requirements?
- Rating: ✅ Aligned / ⚠️ Partial drift / ❌ Misaligned

### Decision Logic

| Result | Action |
|--------|--------|
| All four ✅ | Pass. Proceed to Phase 3. |
| Any ⚠️ (no ❌) | Primary reviewer supplements directly. No MLX resend. Record corrections. |
| Any ❌ AND `attempt.mlx_plan < 2` | Send back to MLX with specific error feedback. Increment `attempt.mlx_plan`. Return to Step 1.2. |
| Any ❌ AND `attempt.mlx_plan >= 2` | Primary reviewer takes over plan writing entirely. Record takeover. |

### MLX Resend Context Format

When sending back to MLX:

```
The previous plan had these critical issues:
1. [Dimension]: [Specific error description]
2. [Dimension]: [Specific error description]

Please rewrite the plan, focusing on correcting the above issues.
Original requirement: <requirement>
```

### Display Review Result

```
## Plan Review (Primary Reviewer)

- Step Completeness: [✅/⚠️/❌] [brief note]
- Dependency Correctness: [✅/⚠️/❌] [brief note]
- Risk Coverage: [✅/⚠️/❌] [brief note]
- Requirement Alignment: [✅/⚠️/❌] [brief note]

**Verdict**: [PASS / SUPPLEMENTED / RETURNED TO MLX / TAKEOVER]
```

---

## Phase 3: Final Review — Plan (Blocking, Cross-Review)

**Smart Trimming**: If `complexity` is `simple` or `medium`, skip this phase entirely. Output: `[Phase 3 SKIPPED — complexity: {complexity}]`. Proceed to Phase 4.

### Step 3.1: Prepare

1. Store final plan text in `.dev-state.json` → `artifacts.plan_draft`
2. Update state: `step: "final_review_plan_pending"`
3. Record any corrections from Phase 2 in `corrections.plan`

### Step 3.2: Send to Final Reviewer

Use platform's async delegation (see adapter for exact command):

```
ask <final_reviewer> "Please review the following implementation plan:

--- PLAN START ---
<final plan>
--- PLAN END ---

Reply format:
1. Overall assessment (one sentence)
2. Issues found (if any)
3. Improvement suggestions (if any)
4. Conclusion: PASS / CONCERN"
```

### Step 3.3: Block and End Turn

After async submission:
- Reply with one line: `<Final Reviewer> processing...`
- **END TURN IMMEDIATELY** (mandatory async guardrail)

### Step 3.4: Resume (when user runs `/dev --resume`)

1. Fetch final reviewer reply (see adapter for pend command)
2. Process reply:
   - **PASS**: Proceed to Phase 4
   - **CONCERN**: Primary reviewer evaluates the concerns:
     - Agree with concern → apply fix, record correction
     - Disagree → note disagreement reason, proceed anyway
3. Update state: `step: "plan_complete"`

---

## Phase 4: Record Plan Learning Feedback

If primary reviewer made ANY corrections to the MLX plan (⚠️ supplements, ❌ fixes, or takeover):

Append to `~/.claude/skills/memory/corrections.jsonl`:

```jsonl
{"timestamp":"<ISO>","task_summary":"<one-line summary>","error_dimensions":["Step Completeness","Risk Coverage"],"original_issue":"<what was wrong>","correction":"<what was fixed>","severity":"warning","takeover":false}
```

Fields:
- `timestamp`: ISO 8601 format
- `task_summary`: One-line summary of the requirement
- `error_dimensions`: Which dimensions had issues (array)
- `original_issue`: What was wrong (concise)
- `correction`: What was fixed (concise)
- `severity`: `"warning"` for ⚠️, `"critical"` for ❌
- `takeover`: `true` if primary reviewer took over entirely

If no corrections were needed (all ✅), skip this phase.

Update state: `phase: "development"`, `step: "ollama_coding"`

---

## Phase 5: Ollama Code Generation

### Step 5.1: Prepare Coding Context

1. Extract implementation steps from the final plan
2. Read `~/.claude/skills/memory/corrections.jsonl`:
   - Take last 5 entries, format as correction notes
3. Read existing files referenced in the plan (using Read tool)
4. Determine language from plan content or project context

### Step 5.2: Send to Ollama

Call MCP tool (see adapter for exact syntax):

```
ollama_code(
  task="Implement according to the following plan:\n<implementation steps>\n\nNotes:\n<historical corrections summary>",
  context="Existing code:\n<relevant file contents>",
  language="<detected language>"
)
```

### Step 5.3: Display Result

```
## Ollama Code Output

**Model**: {model from response} | **Response time**: {durationMs}ms

```{language}
{generated code}
```
```

### Step 5.4: Handle Ollama Errors

- **Unreachable** (192.168.1.206:11434): Inform user, primary reviewer writes code directly. Skip to Phase 6 with reviewer-authored code.
- **Timeout** (>5 min): Same fallback.
- **Empty response**: Retry once. If still empty, fallback.

---

## Phase 6: Primary Reviewer — Three-Tier Code Review (Linus Style)

### Three-Tier Framework

Apply the **Linus Taste Review Rubric** (`~/.claude/skills/linus-review/rubric.md`).

Dual-pass review: Pass 1 (fatal issues) → Pass 2 (taste score 🟢🟡🔴 + max 3 improvements).

### Decision Logic

| Result | Action |
|--------|--------|
| 🟢 Good taste | Adopt directly. Proceed to Phase 7. |
| 🟡 Passable | Primary reviewer fixes directly (variable naming, validation, edge cases). No Ollama resend. Record corrections. |
| 🔴 Garbage AND `attempt.ollama_code < 2` | Send back to Ollama with review feedback. Increment `attempt.ollama_code`. Return to Step 5.2. |
| 🔴 Garbage AND `attempt.ollama_code >= 2` | Primary reviewer takes over coding entirely. Record takeover. |

### Ollama Resend Context Format

```
Previous attempt had these issues:
1. [specific issue from review]
2. [specific issue from review]
Avoid: [anti-patterns found]
Instead: [correct approach to follow]
```

### Display Review Result

```
## Code Review (Primary Reviewer, Linus Style)

**Taste Score**: [🟢/🟡/🔴] [brief assessment]

**Fatal Issues**: [list or "No fatal issues"]

**Improvements**:
1. [highest impact]
2. [second]
3. [third]

**Verdict**: [ADOPT / FIXED / RETURNED TO OLLAMA / TAKEOVER]
```

---

## Phase 7: Final Review — Code (Blocking, Cross-Review)

**Smart Trimming**: If `complexity` is `simple`, skip this phase entirely. Output: `[Phase 7 SKIPPED — complexity: simple]`. Proceed to Phase 8.

### Step 7.1: Prepare

1. Store final code in `artifacts.code_output`
2. Store changed file list in `artifacts.changed_files`
3. Update state: `step: "final_review_code_pending"`
4. Record any corrections from Phase 6 in `corrections.code`

### Step 7.2: Send to Final Reviewer

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

### Step 7.3: Block and End Turn

Same as Phase 3 — async guardrail, end turn immediately.

### Step 7.4: Resume

1. Fetch final reviewer reply
2. Process:
   - **PASS**: Proceed to Phase 8
   - **CONCERN**: Primary reviewer evaluates, apply fixes if agreed
3. Update state: `step: "code_complete"`

---

## Phase 8: Record Code Learning Feedback

If primary reviewer made ANY corrections to Ollama's code:

Append to `~/.claude/skills/memory/corrections.jsonl`:

```jsonl
{"timestamp":"<ISO>","task_summary":"<summary>","language":"TypeScript","taste_score":"passable","issues":["missing validation","incomplete error handling"],"corrections":["added zod schema","added try-catch with custom errors"],"severity":"minor"}
```

Fields:
- `timestamp`: ISO 8601
- `task_summary`: One-line requirement summary
- `language`: Programming language
- `taste_score`: `"good"`, `"passable"`, or `"garbage"`
- `issues`: Array of issues found (concise)
- `corrections`: Array of corrections applied (concise)
- `severity`: `"minor"` for 🟡, `"major"` for 🔴
- `takeover`: `true` if primary reviewer took over (add this field only when true)

If no corrections needed (🟢), skip this phase.

---

## Phase 9: Git Commit (No Push)

### Step 9.1: Apply Code Changes

Write the final reviewed code to files using Write/Edit tools.
Only modify the files specified in `artifacts.changed_files`.

### Step 9.2: Pre-commit Check

1. Run `git status` to verify working tree state
2. If there are unrelated uncommitted changes, warn user and ask whether to proceed
3. If there are merge conflicts, inform user and stop

### Step 9.3: Commit

```bash
git add <specific_files>
git commit -m "$(cat <<'EOF'
<type>: <plan goal in one sentence>

- <change summary 1>
- <change summary 2>

Plan: MLX draft + primary review <PASS/SUPPLEMENTED/TAKEOVER>
Code: Ollama + primary review <🟢/🟡/TAKEOVER>

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

### Step 9.4: Cleanup and Summary

1. Delete `.dev-state.json`
2. Display completion summary:

```
## /dev Workflow Complete

**Requirement**: <one line>
**Plan**: MLX draft + primary review <verdict>
**Code**: Ollama + primary review <verdict>
**Final Review**: <final reviewer> <verdict>
**Commit**: <first 7 chars of commit hash>

Learning feedback recorded: <N> entries (MLX: <n1>, Ollama: <n2>)
```

---

## State File Schema

`.dev-state.json` complete structure:

```json
{
  "version": 1,
  "phase": "planning|development|committing|done",
  "step": "mlx_drafting|primary_reviewing_plan|final_review_plan_pending|plan_complete|ollama_coding|primary_reviewing_code|final_review_code_pending|code_complete|committing",
  "requirement": "original requirement text",
  "attempt": {
    "mlx_plan": 0,
    "ollama_code": 0
  },
  "maxAttempts": {
    "mlx_plan": 2,
    "ollama_code": 2
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

1. Local/LAN AI generates, platform AI reviews — each handles its specialty
2. Cross-review ensures no self-assessment blind spots
3. Maximum 2 resend rounds (diminishing returns)
4. Learning feedback accumulates over time, making future prompts more precise
5. Blocking at final review ensures complete quality gate
6. Git commit is the last step — no push, user decides when to push
7. Maintain the Qing dynasty court official communication style (Traditional Chinese)
