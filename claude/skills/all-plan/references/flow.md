# All Plan (Claude Version)

Planning skill using abstract roles defined in CLAUDE.md Role Assignment table.
Phase 3 (plan drafting) delegated to local MLX (Qwen3-14B), with Claude quality review before submission to `reviewer`.

**Usage**: For complex features or architectural decisions requiring thorough planning.

**Roles used by this skill** (resolve to providers via CLAUDE.md `CCB_ROLES`):
- `designer` — Primary planner, owns the plan from start to finish. Orchestrates MLX and reviews its output.
- `inspiration` — Creative brainstorming consultant (unreliable, use with judgment)
- `reviewer` — Scored quality gate, evaluates the plan using Rubric A (must pass >= 7.0)

---

## Input Parameters

From `$ARGUMENTS`:
- `requirement`: User's initial requirement or feature request
- `context`: Optional project context or constraints

---

## Execution Flow

### Phase 0: Scope Challenge

Before any planning begins, challenge the scope. This prevents scope creep and ensures we build the right amount.

**0.1 Scope Assessment**

Analyze the requirement and present THREE scope options:

```
SCOPE CHALLENGE
===============
Requirement: [user's requirement]

A) SCOPE EXPANSION — Build more than asked
   [What additional value could be delivered]
   Risk: Over-engineering, longer delivery

B) HOLD SCOPE — Build exactly what's asked
   [Restate the requirement clearly]
   Risk: [any risks of this scope]

C) SCOPE REDUCTION — Build less, ship faster
   [What's the MVP that delivers core value]
   Risk: May need follow-up work

RECOMMENDATION: Choose [X] because [reason]
```

**0.2 Lock Scope**

After user selects, lock the scope decision:

```
SCOPE LOCKED: [EXPANSION / HOLD / REDUCTION]
Decision: [1-sentence summary of what we're building]
```

**Once locked, scope does not change for the remainder of this planning session.** If new information surfaces that challenges the scope, flag it but do not re-open the scope discussion without user approval.

Proceed to Phase 1 with the locked scope.

---

### Phase 1: Requirement Clarification

**1.1 Structured Clarification (Option-Based)**

Use the **5-Dimension Planning Readiness Model** to ensure comprehensive requirement capture.

#### Readiness Dimensions (100 pts total)

| Dimension | Weight | Focus | Priority |
|-----------|--------|-------|----------|
| Problem Clarity | 30pts | What problem? Why solve it? | 1 |
| Functional Scope | 25pts | What does it DO? Key features | 2 |
| Success Criteria | 20pts | How to verify done? | 3 |
| Constraints | 15pts | Time, resources, compatibility | 4 |
| Priority/MVP | 10pts | What first? Phased delivery? | 5 |

#### Clarification Flow

```
ROUND 1:
  1. Parse initial requirement
  2. Identify 2 lowest-confidence dimensions (use Priority order for ties)
  3. Present 2 questions with options (1 per dimension)
  4. User selects options
  5. Update dimension scores based on answers
  6. Display Scorecard to user

IF readiness_score >= 80: Skip Round 2, proceed to 1.2
ELSE:
  ROUND 2:
    1. Re-identify 2 lowest-scoring dimensions
    2. Ask 2 more questions
    3. Update scores
    4. Proceed regardless (with gap summary)

QUICK-START OVERRIDE:
  - User can select "Proceed anyway" at any point
  - All dimensions marked as "assumption" in summary
```

#### Option Bank Reference

**Problem Clarity (30pts)**
```
Question: "What type of problem are you solving?"
Options:
  A. "Specific bug or defect with clear reproduction" → 27pts
  B. "New feature with defined business value" → 27pts
  C. "Performance/optimization improvement" → 24pts
  D. "General improvement or refactoring" → 18pts
  E. "Not sure yet - need exploration" → 9pts (flag)
  F. "Other: ___" → 12pts (flag)
```

**Functional Scope (25pts)**
```
Question: "What is the scope of functionality?"
Options:
  A. "Single focused component/module" → 23pts
  B. "Multiple related components" → 20pts
  C. "Cross-cutting system change" → 18pts
  D. "Unclear - need codebase analysis" → 10pts (flag)
  E. "Other: ___" → 10pts (flag)
```

**Success Criteria (20pts)**
```
Question: "How will you verify success?"
Options:
  A. "Automated tests (unit/integration/e2e)" → 18pts
  B. "Performance benchmarks with targets" → 18pts
  C. "Manual testing with checklist" → 14pts
  D. "User feedback/acceptance" → 12pts
  E. "Not defined yet" → 6pts (flag)
  F. "Other: ___" → 8pts (flag)
```

**Constraints (15pts)**
```
Question: "What are the primary constraints?"
Options:
  A. "Time-sensitive (deadline driven)" → 14pts
  B. "Must maintain backward compatibility" → 14pts
  C. "Resource/budget limited" → 12pts
  D. "Security/compliance critical" → 14pts
  E. "No specific constraints" → 10pts
  F. "Other: ___" → 8pts (flag)
```

**Priority/MVP (10pts)**
```
Question: "What is the delivery approach?"
Options:
  A. "MVP first, iterate later" → 9pts
  B. "Full feature, single release" → 9pts
  C. "Phased rollout planned" → 9pts
  D. "Exploratory - scope TBD" → 5pts (flag)
  E. "Other: ___" → 5pts (flag)
```

#### Gap Classification Rules

| Dimension Score | Classification | Handling |
|-----------------|----------------|----------|
| ≥70% of weight | ✓ Defined | Include in Design Brief |
| 50-69% of weight | ⚠️ Assumption | Carry forward as risk |
| <50% of weight | 🚫 Gap | Flag in brief, may need validation |

Example thresholds:
- Problem Clarity: ≥21 Defined, 15-20 Assumption, <15 Gap
- Functional Scope: ≥18 Defined, 13-17 Assumption, <13 Gap
- Success Criteria: ≥14 Defined, 10-13 Assumption, <10 Gap
- Constraints: ≥11 Defined, 8-10 Assumption, <8 Gap
- Priority/MVP: ≥7 Defined, 5-6 Assumption, <5 Gap

#### Clarification Summary Output

After clarification, generate:

```
CLARIFICATION SUMMARY
=====================
Readiness Score: [X]/100

Dimensions:
- Problem Clarity: [X]/30 [✓/⚠️/🚫]
- Functional Scope: [X]/25 [✓/⚠️/🚫]
- Success Criteria: [X]/20 [✓/⚠️/🚫]
- Constraints: [X]/15 [✓/⚠️/🚫]
- Priority/MVP: [X]/10 [✓/⚠️/🚫]

Assumptions & Gaps:
- [Dimension]: [assumption or gap description]

Proceeding to project analysis...
```

Save as `clarification_summary`.

**1.2 Analyze Project Context**

Use available tools to understand:
- Existing codebase structure (Glob, Grep, Read)
- Current architecture patterns
- Dependencies and tech stack
- Related existing implementations
- **若任務涉及資料庫**：使用 `/db` 查詢相關表結構（欄位、型別、索引），納入 design brief context

**1.3 Research (if needed)**

If the requirement involves:
- New technologies or frameworks
- Industry best practices
- Performance benchmarks
- Security considerations

Use WebSearch to gather relevant information.

**1.4 Formulate Design Brief**

Create a comprehensive design brief incorporating clarification results:

```
DESIGN BRIEF
============
Readiness Score: [X]/100

Problem: [clear problem statement]
Context: [project context, tech stack, constraints]

Requirements:
- [requirement 1]
- [requirement 2]

Success Criteria:
- [criterion 1]
- [criterion 2]

Assumptions (from clarification):
- [assumption 1]

Gaps to Validate:
- [gap 1]

Research Findings: [if applicable]
```

Save as `design_brief`.

---

### Phase 2: Inspiration Brainstorming

Send the design brief to `inspiration` for creative input. The `inspiration` provider excels at divergent thinking, aesthetic ideas, and unconventional approaches — but is often unreliable, so treat all output as **reference only**.

**2.1 Request Inspiration**

Send to `inspiration` (via `/ask`):

```
You are a creative brainstorming partner. Based on this design brief, provide INSPIRATION and CREATIVE IDEAS — not a full implementation plan.

DESIGN BRIEF:
[design_brief]

Provide:
1) 3-5 creative approaches or angles others might miss
2) Naming suggestions (for features, APIs, components) if applicable
3) UX/UI ideas or visual design inspiration if applicable
4) Unconventional solutions worth considering
5) Analogies from other domains that could inform the design

Be bold and creative. Practical feasibility is secondary — inspiration is the goal.
```

Save response as `inspiration_response`.

**2.2 The `designer` Filters Inspiration Ideas**

After receiving the response, the `designer` MUST:

1. Read all suggestions critically
2. Classify each idea:
   - **Adopt** — genuinely improves the design, feasible within constraints
   - **Adapt** — interesting kernel but needs reworking to be practical
   - **Discard** — creative but impractical, off-target, or contradicts requirements
3. Present the filtered list to the user:

```
INSPIRATION FILTER
==========================
Adopted:
- [idea]: [why it's valuable]

Adapted:
- [idea] → [how the `designer` will modify it]: [rationale]

Discarded:
- [idea]: [why it doesn't fit]
```

4. Ask user: "Do you agree with this selection, or want to override any decisions?"

Save filtered result as `adopted_inspiration`.

---

### Phase 3: MLX Drafts the Plan (Claude Reviews)

The `designer` orchestrates MLX to generate the plan draft, then reviews it before submission to `reviewer`.

**3.1 Send to MLX for Plan Drafting**

Claude packages the design brief, adopted inspiration, and project context, then sends to MLX:

```
mcp__mcp-ai-bridge__mlx_chat(
  systemPrompt: <see Plan Writer System Prompt below>,
  message: "DESIGN BRIEF:\n{design_brief}\n\nADOPTED INSPIRATION:\n{adopted_inspiration}\n\nPROJECT CONTEXT:\n{project context from Phase 1.2}",
  maxTokens: 8192
)
```

**Plan Writer System Prompt**:

```
/think
You are a senior software architect drafting an implementation plan. Write precisely, concisely, and actionably.

Based on the provided design brief, inspiration ideas, and project context, create a complete implementation plan with this EXACT structure:

IMPLEMENTATION PLAN (Draft v1)
==============================
Goal: [1-sentence goal]
Scope: [EXPANSION / HOLD / REDUCTION — locked from Phase 0]

Architecture:
- Approach: [chosen approach with rationale]
- Key Components: [bulleted list with descriptions]
- Data Flow: [if applicable]

Diagrams (MANDATORY — include at least 2 of the following):
- Sequence Diagram: [Mermaid syntax — show key interactions between components]
- State Machine: [Mermaid syntax — show state transitions if stateful logic exists]
- Component Diagram: [Mermaid syntax — show system components and their relationships]
- Data Flow Diagram: [Mermaid syntax — show how data moves through the system]

Implementation Steps:
For each step:
### Step N: [Title]
- **Actions**: [specific, concrete actions]
- **Deliverables**: [what will be produced]
- **Dependencies**: [what must come first]

Technical Considerations:
- [consideration 1]
- [consideration 2]

Risks & Mitigations:
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
[fill table with concrete entries]

Acceptance Criteria:
- [ ] [concrete, verifiable criterion]

Inspiration Credits:
| Idea | Status | How Integrated |
[credit adopted/adapted ideas from the inspiration input]

RULES:
- Every step must be independently executable
- No step should take more than 1 hour of focused work
- Acceptance criteria must be testable (not vague)
- Risks must have concrete mitigations (not "monitor carefully")
- Use English for technical terms, structure in English
- MANDATORY: Include at least 2 diagrams in Mermaid syntax (sequence, state, component, or data-flow). Diagrams force hidden assumptions to surface.
```

**3.2 Display MLX Plan Draft**

```
## MLX (Qwen3-14B) Plan Draft

**Model**: Qwen3-14B-4bit | **Inference time**: {durationMs}ms

{MLX plan draft verbatim}
```

**3.3 Claude Plan Quality Review**

Claude reviews the MLX-generated plan using this four-dimensional framework:

```
[PLAN QUALITY REVIEW]

1. Step Completeness
- Do steps cover the full path from current state to goal? Any gaps?
- Are each step's Actions specific and executable? Or vague directives?
- Rating: ✅ Complete / ⚠️ Gaps exist / ❌ Path broken

2. Dependency Correctness
- Does step ordering reflect real dependencies?
- Any circular dependencies or contradictions?
- Rating: ✅ Correct / ⚠️ Partially misordered / ❌ Dependencies confused

3. Risk Coverage
- Are major technical and integration risks identified?
- Are mitigation strategies specific and actionable (not "monitor closely")?
- Rating: ✅ Adequate / ⚠️ Gaps exist / ❌ Severely lacking

4. Requirement Alignment
- Does the plan actually solve the problem in the design_brief?
- Are acceptance criteria testable and unambiguous?
- Rating: ✅ Aligned / ⚠️ Off-target / ❌ Completely misaligned

5. Diagram Coverage
- Are at least 2 diagrams present (sequence, state, component, or data-flow)?
- Do diagrams accurately reflect the architecture described in text?
- Do diagrams expose any hidden assumptions or contradictions?
- Rating: ✅ Adequate / ⚠️ Missing or superficial / ❌ No diagrams
```

**Decision and action**:

- **All five dimensions ✅** → Adopt as `plan_draft_v1`, proceed to Phase 4
  ```
  [PLAN REVIEW PASSED] Five-dimensional quality confirmed
  - Step Completeness: ✅
  - Dependency Correctness: ✅
  - Risk Coverage: ✅
  - Requirement Alignment: ✅
  - Diagram Coverage: ✅
  This plan is ready for reviewer scoring.
  ```

- **Any dimension ⚠️** → Claude supplements directly (no MLX resend), corrected version becomes `plan_draft_v1`
  ```
  [PLAN REVIEW PASSED (with corrections)]
  - [List each dimension's rating]
  - ⚠️ Dimension correction: [specific correction content]
  [Display corrected plan]
  ```

- **Any dimension ❌** → Resend to MLX with review feedback (max 1 time)
  ```
  mcp__mcp-ai-bridge__mlx_chat(
    systemPrompt: <same Plan Writer System Prompt>,
    message: "Previous plan draft had critical issues:\n1. [Dimension name]: [Specific error description]\n\nPlease revise the plan. Focus on:\n- [aspects needing redesign]\n\nOriginal inputs:\nDESIGN BRIEF:\n{design_brief}\n\nADOPTED INSPIRATION:\n{adopted_inspiration}",
    maxTokens: 8192
  )
  ```
  After resend, Claude reviews again. If still ❌, Claude writes the problematic parts directly.

**3.4 Save as `plan_draft_v1`**

Save the reviewed (and possibly corrected) plan as the standardized `plan_draft_v1`.

---

### Phase 4: Scored Review

Submit the plan to `reviewer` for scored review using Rubric A (defined in CLAUDE.md).

**4.1 Submit Plan for Review**

Send to `reviewer` (via `/ask`):

```
[PLAN REVIEW REQUEST]
Review the following implementation plan using Rubric A. Score EACH dimension individually with detailed feedback.
Return your response as JSON with this exact structure:
{
  "review_type": "plan",
  "dimensions": {
    "clarity": {
      "score": N,
      "strengths": ["..."],
      "weaknesses": ["..."],
      "fix": "specific action to improve"
    },
    "completeness": {
      "score": N,
      "strengths": ["..."],
      "weaknesses": ["..."],
      "fix": "specific action to improve"
    },
    "feasibility": {
      "score": N,
      "strengths": ["..."],
      "weaknesses": ["..."],
      "fix": "specific action to improve"
    },
    "risk_assessment": {
      "score": N,
      "strengths": ["..."],
      "weaknesses": ["..."],
      "fix": "specific action to improve"
    },
    "requirement_alignment": {
      "score": N,
      "strengths": ["..."],
      "weaknesses": ["..."],
      "fix": "specific action to improve"
    }
  },
  "overall": N.N,
  "critical_issues": ["..."],
  "summary": "one-paragraph overall assessment"
}

--- PLAN START ---
[plan_draft_v1]
--- PLAN END ---
```

**4.2 Parse and Judge**

After receiving the `reviewer`'s JSON response:

```
iteration = 1

CHECK:
  - If overall >= 7.0 AND no single dimension score <= 3 → PASS
  - Otherwise → FAIL
```

**4.3 Auto-Correction Loop (on FAIL)**

```
WHILE result == FAIL AND iteration <= 3:
  1. Read each dimension's weaknesses and fix suggestions
  2. Read critical_issues list
  3. Determine correction scale:
     - MINOR (< 3 issues): Claude directly revises plan_draft
     - MAJOR (>= 3 issues): Resend to MLX with reviewer feedback for revision,
       then Claude reviews the new MLX output before resubmission
  4. Save as plan_draft_v{iteration+1}
  5. Re-submit to `reviewer` via /ask (same template)
  6. iteration += 1
  7. Re-check PASS/FAIL

IF iteration > 3 AND still FAIL:
  Present all review rounds to user
  Ask: "Review did not pass after 3 rounds. How would you like to proceed?"
```

**MLX Resend for Major Corrections** (used in step 3 above when MAJOR):

```
mcp__mcp-ai-bridge__mlx_chat(
  systemPrompt: <same Phase 3 Plan Writer System Prompt>,
  message: "The reviewer found these issues with the plan:\n{reviewer weaknesses and critical_issues}\n\nPlease revise the plan to address ALL issues.\n\nOriginal design brief:\n{design_brief}\n\nPrevious plan:\n{plan_draft_v{iteration}}",
  maxTokens: 8192
)
```

Claude reviews MLX's revised output (same 4-dimension review as Phase 3.3) before resubmitting to `reviewer`.

**4.4 Display Score Summary (on PASS)**

```
REVIEW: PASSED (Round [N])
=================================
| Dimension             | Score | Weight | Weighted |
|-----------------------|-------|--------|----------|
| Clarity               | X/10  | 20%    | X.XX     |
| Completeness          | X/10  | 25%    | X.XX     |
| Feasibility           | X/10  | 25%    | X.XX     |
| Risk Assessment       | X/10  | 15%    | X.XX     |
| Requirement Alignment | X/10  | 15%    | X.XX     |
|-----------------------|-------|--------|----------|
| OVERALL               |       |        | X.XX/10  |

Key Strengths:
- [from `reviewer` response]

Addressed Issues:
- [issues fixed during iteration, if any]
```

---

### Phase 5: Final Output

**5.1 Save Plan Document**

Write the final plan to a markdown file:

**File path**: `plans/{feature-name}-plan.md`

Use this template:

```markdown
# {Feature Name} - Solution Design

> Generated by all-plan (`designer` + `inspiration` + `reviewer`) | Plan drafted by MLX (Qwen3-14B)

## Overview

**Goal**: [Clear, concise goal statement]

**Readiness Score**: [X]/100

**Review Score**: [X.XX]/10 (passed round [N])

**Generated**: [Date]
```

The plan document should also include these sections (continue the markdown template):

```markdown
## Requirements Summary

### Problem Statement
[Clear problem description]

### Scope
[What's in scope and out of scope]

### Success Criteria
- [ ] [criterion 1]
- [ ] [criterion 2]

### Constraints
- [constraint 1]

### Assumptions
- [assumption from clarification]
```

Continue the plan document with:

```markdown
## Architecture

### Approach
[Chosen architecture approach with rationale]

### Key Components
- **[Component 1]**: [description]
- **[Component 2]**: [description]

### Data Flow
[If applicable, describe data flow]

### Diagrams
[At least 2 Mermaid diagrams — sequence, state, component, or data-flow]
```

Continue with implementation and risk sections:

```markdown
## Implementation Plan

### Step 1: [Title]
- **Actions**: [specific actions]
- **Deliverables**: [what will be produced]
- **Dependencies**: [what's needed first]

### Step 2: [Title]
- **Actions**: [specific actions]
- **Deliverables**: [what will be produced]
- **Dependencies**: [what's needed first]

[Continue for all steps...]

---

## Technical Considerations

- [consideration 1]
- [consideration 2]

---

## Risk Management

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [risk 1] | High/Med/Low | High/Med/Low | [strategy] |
| [risk 2] | High/Med/Low | High/Med/Low | [strategy] |

---

## Acceptance Criteria

- [ ] [criterion 1]
- [ ] [criterion 2]
- [ ] [criterion 3]
```

Finish the plan document with credits and appendix:

```markdown
---

## Inspiration Credits

| Idea | Status | How Integrated |
|------|--------|----------------|
| [idea 1] | Adopted | [how it was used] |
| [idea 2] | Adapted | [how it was modified] |

---

## Review Summary

| Dimension | Score |
|-----------|-------|
| Clarity | X/10 |
| Completeness | X/10 |
| Feasibility | X/10 |
| Risk Assessment | X/10 |
| Requirement Alignment | X/10 |
| **Overall** | **X.XX/10** |

Review rounds: [N]

---

## Appendix

### Clarification Summary
[Include the clarification summary from Phase 1.1]

### Discarded Inspiration Ideas
[Ideas considered but not adopted, with rationale]

### Alternative Approaches Considered
[Brief notes on approaches evaluated but not chosen]
```

**5.2 Output to User**

After saving the file, display to user:

```
PLAN COMPLETE
=============

✓ Plan saved to: plans/{feature-name}-plan.md

Summary:
- Goal: [1-sentence goal]
- Steps: [N] implementation steps
- Risks: [N] identified with mitigations
- Readiness: [X]/100
- Review Score: [X.XX]/10 (round [N])
- Inspiration Ideas: [N] adopted, [N] adapted, [N] discarded
- Plan drafted by: MLX (Qwen3-14B) + Claude review

Next: Review the plan and proceed with implementation when ready.
```

---

## Error Handling

- **MLX unreachable** (localhost:8090 not responding):
  Phase 3 falls back to Claude writing the plan directly (pre-migration behavior).
  Inform user: "MLX unreachable, I will write the plan directly."

- **MLX timeout** (> 3 minutes):
  Fall back to Claude direct authoring.

- **MLX output empty or garbled**:
  Fall back to Claude direct authoring.

- **`inspiration` provider unreachable**:
  Skip Phase 2, proceed directly to Phase 3.

- **`reviewer` provider unreachable**:
  Skip Phase 4, present the plan directly to user.

---

## Principles

1. **`designer` Owns the Design**: The `designer` orchestrates everything; MLX is a drafting tool, not the decision maker
2. **Structured Clarification**: Use option-based questions to systematically capture requirements
3. **Readiness Scoring**: Quantify requirement completeness before proceeding
4. **MLX Drafts, Claude Reviews**: MLX generates the plan, Claude ensures quality before `reviewer` submission
5. **`inspiration` for Ideas Only**: Leverage creativity but never blindly follow it
6. **User Controls Inspiration**: User decides which ideas to adopt/discard
7. **`reviewer` as Quality Gate**: Plan must pass Rubric A (>= 7.0) before proceeding
8. **Dimension-Level Feedback**: The `reviewer` scores each dimension individually with actionable fixes
9. **Auto-Correction with Limits**: Max 3 review rounds; major corrections re-invoke MLX
10. **Concrete Deliverables**: Output actionable plan document, not just discussion notes
11. **Research When Needed**: Use WebSearch for external knowledge when applicable
12. **Graceful Degradation**: MLX failure triggers seamless fallback to Claude direct authoring

---

## Notes

- This skill is designed for complex features or architectural decisions
- For simple tasks, use direct implementation instead
- Resolve `inspiration` and `reviewer` to providers via CLAUDE.md Role Assignment, then use `/ask <provider>`
- If `inspiration` provider is not available, skip Phase 2 and proceed directly to Phase 3
- If `reviewer` provider is not available, skip Phase 4 and present the plan directly to user
- Plans are saved to `plans/` directory with descriptive filenames
