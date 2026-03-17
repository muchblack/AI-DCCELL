# AutoFlow Plan

Create executable plan artifacts: `.ccb/todo.md` + `.ccb/state.json` + `.ccb/plan_log.md`

**File formats**: See `~/.claude/skills/docs/formats.md`
**Protocol**: See `~/.claude/skills/docs/protocol.md`

---

## Architecture Note

- This skill replaces Plan Mode for structured planning — it includes deep codebase exploration + MLX-First collaborative design, which Plan Mode cannot provide.
- **All file I/O (create/modify)** is executed by **Codex** via `FileOpsREQ` / `FileOpsRES`.
- This command must never directly write files; it only prepares the plan content and delegates writes to Codex.

---

## Execution Flow

### 1. Initialize & Deep Exploration

**1.1 Basic Setup**
- Get requirement from `$ARGUMENTS`
- **Spec Sync**: 檢查專案 CLAUDE.md 是否有 `spec-source:` 宣告，若有：
  1. 解析路徑（展開 `~` 為 `$HOME`）
  2. 執行 `git -C <spec-path> pull --rebase`
  3. 回報同步結果（updated / already up to date / failed）
  4. 若 pull 失敗，警告但不中斷流程

**1.2 Deep Codebase Exploration**

Launch up to 3 Explore agents **in parallel** (single message, multiple Agent tool calls) to build comprehensive understanding of the affected codebase:

- **Agent A — Existing Implementation**: Search for existing functions, patterns, and utilities related to the requirement. Focus on what can be reused.
- **Agent B — Architecture & Dependencies**: Map the relevant module structure, data flow, tech stack, and dependency graph.
- **Agent C — Related Changes & Tests**: Check git history for recent related changes, existing test patterns, and edge cases already handled.

**Scaling rules**:
- Use 1 agent when the task is isolated to known files or user provided specific paths
- Use 2-3 agents when scope is uncertain, multiple areas involved, or you need to understand existing patterns
- Quality over quantity — use the minimum agents necessary

**1.3 Exploration Summary**

After all agents return, synthesize into a structured brief:

```
EXPLORATION SUMMARY
===================
Tech Stack: [language, framework, key dependencies]
Key Files: [paths directly relevant to the requirement]
Existing Patterns: [reusable functions, utilities, conventions found]
Recent Changes: [related git history if relevant]
Test Coverage: [existing test patterns for affected areas]
Gaps: [areas with no tests, unclear architecture, missing docs]
```

Save as `exploration_summary` — this feeds into `/all-plan` Phase 1.2 (Project Context).

**1.4 Research (if needed)**
- If requirement involves unfamiliar technologies/APIs/libraries, use WebSearch/WebFetch to review official docs + best practices

### 2. Collaborative Design (Plan)

Invoke the `/all-plan` skill, passing the exploration summary as context:

```
/all-plan <requirement from $ARGUMENTS>

Context from exploration:
<exploration_summary>
```

When `/all-plan` reaches Phase 1.2 (Analyze Project Context), it should leverage the `exploration_summary` rather than re-exploring from scratch. This avoids duplicate work.

The `/all-plan` skill provides a complete collaborative design flow including:
0. **Scope challenge** (lock scope before any planning)
1. Requirement clarification (5-dimension model)
2. Inspiration consultation (if applicable)
3. **MLX plan drafting** + Claude quality review (MLX-First)
4. Reviewer scoring (Rubric A, must pass >= 7.0)

Extract from the `/all-plan` output:
- **goal**: the task objective
- **nonGoals**: what NOT to do
- **steps**: ordered list of step titles
- **acceptance criteria**: done conditions (finalDone)

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

### 4. Cross-AI Review

After user confirms the plan, send it to another AI for an independent review. This catches blind spots that the `designer` + `reviewer` pipeline may have missed.

**4.1 Send Plan for Cross-Review**

Send the confirmed plan to `inspiration` (via `/ask`) for an independent review:

```
[CROSS-AI PLAN REVIEW]

You are an independent reviewer. Critically evaluate this implementation plan. Focus on:
1. **Blind spots**: Anything the plan overlooks or assumes incorrectly?
2. **Over-engineering**: Are any steps unnecessarily complex?
3. **Missing edge cases**: What could go wrong that isn't addressed?
4. **Alternative approaches**: Is there a simpler way to achieve the same goal?
5. **Integration risks**: Will this plan cause issues with existing systems?

Be direct and critical. Praise is not needed — only flag real issues.

--- PLAN START ---
[confirmed plan content]
--- PLAN END ---

Respond with:
CROSS-REVIEW RESULT
====================
Issues Found: [N]

Critical (must fix before proceeding):
- [issue]: [why it matters]

Warnings (consider fixing):
- [issue]: [suggestion]

Observations (informational):
- [observation]

Verdict: PROCEED / REVISE
```

**4.2 Present Cross-Review to User**

Display the cross-review result:

```
CROSS-AI REVIEW (by {provider})
================================
Issues Found: [N]

Critical:
- [issue]

Warnings:
- [issue]

Verdict: [PROCEED / REVISE]
```

**4.3 Decision**

- **Verdict = PROCEED** (or no critical issues): Inform user and move to step 5 (Save Files)
- **Verdict = REVISE** (critical issues found):
  Present issues to user with options:
  ```
  Cross-review 發現重大問題，建議：

  A) 修正計畫後再存檔（Claude 直接修正）
  B) 忽略審查意見，照原計畫存檔
  C) 回到 /all-plan 重新規劃
  ```
  - If user selects A: Claude fixes the plan based on cross-review feedback, then proceeds to save
  - If user selects B: Proceed to save as-is
  - If user selects C: Restart from step 2

**4.4 Error Handling**

- **`inspiration` provider unreachable**: Skip cross-review, inform user, proceed to save
- **Response timeout or garbled**: Skip cross-review, inform user, proceed to save

---

### 5. Save Files

After cross-review passes (or user overrides), delegate file creation to `/file-op` using `FileOpsREQ`:

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
        "steps": ["S1 title", "S2 title"],
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

### 6. Output

```
Plan saved:
- .ccb/todo.md
- .ccb/state.json
- .ccb/plan_log.md

Cross-review: [PASSED / SKIPPED / OVERRIDDEN] (by {provider})

Next: Use /tr to start execution
```

---

## Principles

1. **Replaces Plan Mode**: This skill provides deep exploration + MLX-First collaborative design. Use `/tp` instead of entering Plan Mode.
2. **Explore Before Plan**: Parallel Explore agents build codebase understanding before any design work begins. This prevents planning in a vacuum.
3. **MLX-First**: Plan drafting is delegated to MLX (via `/all-plan` Phase 3), with Claude quality review. Claude writes directly only as fallback.
4. **Collaborative Design**: Uses `/all-plan` for full collaborative planning flow (scope → clarify → inspire → draft → review)
5. **Cross-AI Review**: After user confirms, an independent AI (e.g., Gemini via `inspiration` role) reviews the plan for blind spots before saving. Gracefully skipped if provider is unavailable.
6. **Ask, Don't Assume**: When encountering ambiguity, missing context, or multiple valid interpretations, ALWAYS ask the user for clarification. Never fill in blanks with assumptions — wrong assumptions compound through every downstream step.
7. **User Approval Before Action**: Every destructive or irreversible action (writing files, delegating to external providers, modifying existing code) requires explicit user confirmation. Present what you intend to do, wait for approval, then execute. The user is the Emperor — nothing happens without the Emperor's decree.
8. **Coarse-grained**: Titles only, details in /tr
9. **Recoverable**: Context enables continuity after /clear
10. **Research-driven**: Use WebSearch and WebFetch to gather info on unfamiliar tech/APIs/best practices before finalizing the plan
