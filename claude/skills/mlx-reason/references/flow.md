# MLX Reason Execution Flow

Delegate reasoning analysis to local MLX, Claude performs reasoning quality review.

## Input

- `$ARGUMENTS`: User's requirement description, technical question, or architecture evaluation request

## Execution Flow

### Step 0: Pre-flight Health Check

Before calling MLX, verify provider availability:

```bash
result=$(bash ~/.claude/skills/scripts/health-check.sh mlx)
```

- `status: "ok"` → proceed to Step 1
- `status: "down"` or `"no_model"` → inform user, Claude performs reasoning analysis directly (skip MLX)

This avoids wasting tokens on prompts that will fail. See `~/.claude/skills/docs/resilience-state.md`.

### Step 1: Prepare and Send to MLX

Use MCP tool `mcp__mcp-ai-bridge__mlx_analyze` to send the analysis task.

- Parse user input as `requirement` parameter
- If user references existing project files, read them first with Read tool and pass as `context`
- Enable thinking mode by default (`thinking: true`), unless user explicitly requests fast response

Example tool call:
```
mcp__mcp-ai-bridge__mlx_analyze(
  requirement="Design a user authentication system supporting OAuth2 + JWT",
  context="Existing project uses Laravel 10, PostgreSQL",
  thinking=true
)
```

### Step 2: Display MLX Analysis Result

Present in this format:

```
## MLX (Qwen3-14B) Reasoning Analysis

**Model**: mlx-community/Qwen3-14B-4bit | **Inference time**: {durationMs}ms | **Thinking mode**: {on/off}

{MLX analysis result verbatim}
```

### Step 3: Claude Reasoning Quality Review

This is NOT code review — it is reasoning quality review. Uses a different framework.

**Dimension 1: Logical Consistency**

- Is the reasoning chain internally consistent? Any contradictions?
- Does the conclusion follow logically from the premises?
- Are there logical jumps missing intermediate steps?
- Rating: ✅ Consistent / ⚠️ Partial contradiction / ❌ Logic broken

**Dimension 2: Completeness**

- Are key dimensions covered?
- Does risk analysis cover main scenarios?
- Do data structures cover core entities?
- Rating: ✅ Complete / ⚠️ Gaps exist / ❌ Severely lacking

**Dimension 3: Accuracy**

- Are technical judgments correct? (framework selection, performance estimates, constraints)
- Are there factual errors or hallucinations?
- Are tool/technology descriptions accurate?
- Rating: ✅ Accurate / ⚠️ Partially wrong / ❌ Major errors

**Dimension 4: Practicality**

- Are suggestions executable? (not abstract theory)
- Is complexity assessment reasonable?
- Are existing system constraints considered?
- Rating: ✅ Actionable / ⚠️ Needs adjustment / ❌ Armchair theorizing

### Step 4: Composite Decision and Action

**All four dimensions ✅ → Direct adoption**

Display format:

```
[REASONING REVIEW PASSED] Four-dimensional quality confirmed
- Logical consistency: ✅
- Completeness: ✅
- Accuracy: ✅
- Practicality: ✅

This analysis can be used directly as basis for subsequent decisions.
```

**Any dimension ⚠️ → Claude supplemental correction**

- Claude directly supplements/corrects the ⚠️ dimensions
- No resend to MLX (small correction volume, Claude handles more efficiently)
- Display the corrected complete analysis

Display format:

```
[REASONING REVIEW PASSED (with corrections)]
- Logical consistency: ✅
- Completeness: ⚠️ → Claude supplemented [specific items]
- Accuracy: ✅
- Practicality: ✅

[Display corrected complete analysis]
```

**Any dimension ❌ → Re-analyze**

- Package specific issues as context and resend to MLX
- Clearly indicate which parts need correction in the context
- Maximum 1 resend. If still ❌ after resend, Claude writes that part directly.

Resend context format example:

```
Previous analysis had these critical issues:
1. [Dimension name]: [Specific error description]
2. [Dimension name]: [Specific error description]

Please re-analyze with corrections. Focus on:
- [Aspects needing re-analysis]
```

### Step 5: Prompt 優化（僅在 Claude 接手分析時觸發）

When any dimension scores ❌ AND the MLX resend also scores ❌, after Claude completes the analysis directly, perform prompt optimization:

1. **Read** `/Users/vincenttseng/code/ai/mcp-ai-bridge/prompts.json`
2. **Analyze failure pattern**: Compare MLX's analysis vs Claude's corrected version. Identify systematic reasoning weaknesses:
   - Risk analysis too vague, missing key data entities, overly optimistic feasibility assessment, etc.
3. **Edit** the `analyze.template` field in `prompts.json`:
   - Append 1-2 targeted hints within the relevant section of the six-part analysis structure
   - Example: Under "## 4. Risk Analysis", add "- Consider data consistency and migration risks"
   - If a similar hint already exists, refine it instead of duplicating
   - Keep total prompt length reasonable to avoid prompt bloat
4. **Display** the prompt change diff to the user for confirmation

### Step 6: Follow-up Action Guidance

Guide to appropriate follow-up workflows based on analysis results:

| Analysis Conclusion | Recommended Next | Description |
|---------------------|------------------|-------------|
| Worth doing + Complex feature | `/tp` or `/all-plan` | Enter collaborative task planning |
| Worth doing + Needs coding | `/ollama-code` | Delegate code writing to LAN Ollama |
| Worth doing + Simple change | Direct implementation | No additional planning needed |
| Needs deeper analysis | `/linus-analyze` | Five-layer Linus-style deep analysis |
| Not worth doing | Report to user | Explain reasoning |

## Error Handling

- **MLX unreachable**: Inform user that localhost:8090 is not responding, suggest checking `launchctl list | grep mlx`
- **Timeout (>2 min)**: Inform user inference timed out, suggest shorter requirement description or disabling thinking mode
- **Empty response**: Suggest retrying with a more specific description
- **Thinking chain too long**: If thinking mode output is excessively verbose, suggest disabling thinking mode and retrying

## Principles

1. MLX generates reasoning, Claude controls quality gates — each handles its specialty
2. Reasoning review uses four-dimensional framework, distinct from code review three-tier framework
3. Maximum 1 resend (diminishing returns on re-analysis)
4. Maintain the Qing dynasty court official communication style
5. Before each analysis, assess whether deep reasoning is truly needed (answer simple questions directly)
