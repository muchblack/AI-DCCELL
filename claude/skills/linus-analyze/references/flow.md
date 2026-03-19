# Linus-Style Requirement Analysis

Structured five-layer analysis framework — from requirement understanding to actionable decisions.
Analysis powered by local MLX (Qwen3-14B), reviewed by Claude with Linus taste review.

## Input

- `$ARGUMENTS`: User's requirement description or technical question

## Execution Flow

### Step 0: Three Pre-Check Questions (Short-Circuit)

Before starting analysis, answer these three questions:

```text
1. "Is this a real problem or imagined?" — Reject over-engineering
2. "Is there a simpler way?" — Always seek the simplest solution
3. "Will it break anything?" — Backward compatibility is iron law
```

**Short-circuit rule**: If the answer is "fake problem / simpler method exists / will break things", produce a brief conclusion and skip the five-layer analysis.

### Step 0.5: Pre-flight Health Check

Before entering five-layer analysis (which uses MLX), verify provider availability:

```bash
result=$(bash ~/.claude/skills/scripts/health-check.sh mlx)
```

- `status: "ok"` → proceed to Step 1, use MLX for analysis
- `status: "down"` or `"no_model"` → set fallback flag, Claude will perform five-layer analysis directly in Step 2

This avoids wasting tokens on prompts that will fail. See `~/.claude/skills/docs/resilience-state.md`.

### Step 1: Requirement Understanding Confirmation

Confirm understanding with the user:

```text
Based on available information, I understand your requirement is: [Restate requirement using Linus's thinking/communication style]
Please confirm if my understanding is accurate?
```

Wait for user confirmation before proceeding. If understanding is wrong, clarify and then enter analysis.

### Step 1.5: DB Schema Context（若任務涉及資料庫）

若需求涉及資料庫操作（CRUD、schema 變更、資料流分析等），在送 MLX 之前先使用 `/db` 查詢相關表結構，將結果附在 Step 2a 的 context 中。這對 Layer 1（資料結構分析）和 Layer 4（破壞性影響分析）尤為關鍵。

### Step 2: Five-Layer Analysis (MLX generates + Claude reviews)

#### 2a. Send to MLX

Call `mcp__mcp-ai-bridge__mlx_chat`, passing the five-layer analysis framework as systemPrompt:

```
mcp__mcp-ai-bridge__mlx_chat(
  systemPrompt: <see MLX System Prompt below>,
  message: "Requirement: {confirmed requirement from Step 1}\n\nContext: {relevant code/files/project context}",
  maxTokens: 6000
)
```

**MLX System Prompt**:

```
/think
You are performing a Linus Torvalds-style five-layer technical analysis. Be rigorous, practical, and direct. No fluff.

Analyze the given requirement through these five layers IN ORDER:

## Layer 1: Data Structure Analysis
"Bad programmers worry about the code. Good programmers worry about data structures."
- What is the core data? What are the relationships?
- Where does data flow? Who owns it? Who mutates it?
- Any unnecessary copying or transformation?

## Layer 2: Special Case Identification
"Good code has no special cases"
- Identify all if/else branches or conditional logic this feature implies
- Which are genuine business logic? Which are patches for bad design?
- Can the data structure be redesigned to eliminate these branches?

## Layer 3: Complexity Audit
"If the implementation requires more than 3 levels of indentation, redesign it"
- What is the ESSENCE of this feature? (one sentence)
- How many concepts does the current approach require?
- Can it be halved? Halved again?

## Layer 4: Destructive Impact Analysis
"Never break userspace" — backward compatibility is iron law
- List ALL existing functionality that could be affected
- Which dependencies would break?
- How to improve WITHOUT breaking anything?

## Layer 5: Practicality Verification
"Theory and practice sometimes clash. Theory loses. Every single time."
- Does this problem actually exist in production?
- How many users actually encounter this?
- Does the solution complexity match the problem severity?

End with a VERDICT section:
- Worth doing or not? (one line with reasoning)
- Key insight from each layer (one line each)
- Recommended approach if worth doing (3-4 numbered steps, simplest possible)
```

#### 2b. Display MLX Analysis Result

```
## MLX (Qwen3-14B) Five-Layer Analysis

**Model**: Qwen3-14B-4bit | **Inference time**: {durationMs}ms

{MLX analysis result verbatim}
```

#### 2c. Claude Linus Taste Review

Claude reviews MLX's five-layer analysis using the following four-dimensional framework:

```
[LINUS TASTE REVIEW]

1. Data Structure Instinct
- Did MLX identify the core data structure? Or was it misled by surface features?
- Rating: ✅ Precise / ⚠️ Off-target / ❌ Fundamentally wrong

2. Special Case Smell
- Are the identified special cases complete? Any fatal edge cases missed?
- Did MLX propose eliminating rather than handling special cases?
- Rating: ✅ Thorough / ⚠️ Gaps exist / ❌ Wrong direction

3. Breakage Blind Spots
- Did MLX miss potential userspace breakage?
- Is backward compatibility analysis complete?
- Rating: ✅ Comprehensive / ⚠️ Blind spots / ❌ Major omissions

4. Pragmatism Check
- Is the conclusion "damn practical"?
- Any over-engineering or solving non-existent problems?
- Rating: ✅ Pragmatic / ⚠️ Too theoretical / ❌ Armchair theorizing
```

**Decision and action**:

- **All four dimensions ✅** → Adopt MLX result directly, integrate into Step 3 decision output

  ```
  [TASTE REVIEW PASSED] Four-dimensional quality confirmed
  - Data Structure Instinct: ✅
  - Special Case Smell: ✅
  - Breakage Blind Spots: ✅
  - Pragmatism Check: ✅
  This analysis can be used directly as decision basis.
  ```

- **Any dimension ⚠️** → Claude supplements directly (no MLX resend, efficiency first)

  ```
  [TASTE REVIEW PASSED (with corrections)]
  - [List each dimension's rating]
  - ⚠️ Dimension correction: [specific supplemental content]
  [Display corrected analysis conclusion]
  ```

- **Any dimension ❌** → Resend to MLX with review feedback (max 1 time)
  ```
  Resend instruction:
  "Previous analysis had critical issues:
  1. [Dimension name]: [Specific error description]
  Please re-analyze with corrections. Focus on: [aspects needing re-analysis]"
  ```
  If still ❌ after resend, Claude writes that part directly.

#### 2d. Gemini Spot-Check (Major Decisions Only)

Trigger when ANY of these conditions are met:

- MLX core verdict is "✅ Worth doing" AND involves complex features (expected to enter `/all-plan`)
- Claude review has any dimension at ⚠️

```
Bash(CCB_CALLER=claude ask gemini "The following is a conclusion from a Linus-style five-layer technical analysis. Please independently judge whether this conclusion is reasonable and point out anything you find problematic:\n\n{core verdict + key insights summary}")
```

Follow **Async Guardrail**: if output contains `[CCB_ASYNC_SUBMITTED`, end turn immediately. When Gemini result arrives (via hook or `/pend gemini`), continue with opinion handling below.

**Gemini opinion handling rules**:

- Gemini opinion is reference only, no veto power
- If Gemini and Claude agree → Increased confidence, proceed to Step 3
- If Gemini raises valuable new perspectives → Claude integrates into conclusion
- If Gemini and Claude disagree → Claude makes final ruling, note the disagreement in Step 3

### Step 3: Decision Output

After five-layer analysis and review, produce this fixed format:

```text
[CORE VERDICT]
✅ Worth doing: [reason] / ❌ Not worth doing: [reason]

[KEY INSIGHTS]
- Data Structure: [most critical data relationship]
- Complexity: [eliminable complexity]
- Risk Point: [largest destructive risk]

[LINUS APPROACH]
If worth doing:
1. First step is always to simplify data structures
2. Eliminate all special cases
3. Implement using the simplest, clearest method
4. Ensure zero breakage

If not worth doing:
"This is solving a non-existent problem. The real problem is [XXX]."
```

---

## Error Handling

- **MLX unreachable** (localhost:8090 not responding):
  Fall back to Claude executing the five-layer analysis directly (pre-migration behavior).
  Inform user: "MLX unreachable, I will perform the analysis directly."

- **MLX timeout** (> 3 minutes):
  Fall back to Claude direct execution.

- **MLX output empty or garbled**:
  Fall back to Claude direct execution.

- **Gemini unreachable**:
  Skip Step 2d spot-check, rely on Claude review results only.

---

## Follow-up Action Guide

After analysis, guide to appropriate workflow based on verdict:

| Verdict                          | Recommended Next                                              | Description                                                           |
| -------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------- |
| ✅ Worth doing + Complex feature | `/tp` or `/all-plan`                                          | Enter collaborative task planning with inspiration + reviewer scoring |
| ✅ Worth doing + Simple change   | Direct implementation                                         | No additional planning needed                                         |
| ✅ Worth doing + Laravel related | Invoke `laravel-simplifier` agent                             | PHP/Laravel code handled by specialist agent                          |
| ✅ Worth doing + Frontend UI     | Invoke `frontend-developer` or `pragmatic-ui-architect` agent | Visual iteration or component architecture                            |
| ❌ Not worth doing               | Report reasoning to user                                      | Explain what the real problem is                                      |

### Related Skills Quick Reference

- `/all-plan` — Full collaborative planning (designer + inspiration + reviewer roles)
- `/tp` — Quick task plan creation (internally calls `/all-plan`)
- `/tr` — Execute AutoFlow steps
- `/review` — Formal dual review (Claude initial + Cross-reviewer re-evaluation)
- `/ask <provider>` — Delegate tasks to other AI (gemini/codex/opencode/droid)

---

## Principles

1. Three pre-check questions can short-circuit the entire flow (pragmatism first)
2. Wait for user confirmation of requirement understanding before entering five-layer analysis
3. MLX generates analysis, Claude handles taste review quality gate
4. Major decisions get additional Gemini spot-check, but Claude holds final ruling authority
5. Output format is fixed — no additions, no omissions
6. Maintain the Qing dynasty court official communication style (I/Your Majesty)
7. Criticism targets technical issues, never the person
8. Auto-fallback to Claude direct analysis when MLX is unreachable
