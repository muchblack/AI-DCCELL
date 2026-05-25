# Review

Dual review by Claude (initial assessment) and a configurable cross-review provider (Codex by default).

## Modes

- `mode=step`: Review single step execution (used by /tr Step 7)
- `mode=task`: Review entire task completion (used by /tr Step 9.1)

## Input

| Field | step mode | task mode |
|-------|-----------|-----------|
| target | Step title | Task name |
| doneConditions | Step done conditions | Acceptance criteria |
| changedFiles | Files changed in step | All files changed |
| proof | Execution output | All step summaries |

## Execution Flow

### 0. Resolve Cross-Review Provider

Resolve the `reviewer` role using a three-layer lookup:

1. **CLAUDE.md Role Assignment table** (primary): Read the Role Assignment table in CLAUDE.md. The `reviewer` role maps to a provider (e.g., `codex`, `gemini`).
2. **`.autoflow/roles.json`** (override): If this file exists in the repo, and `enabled == true` and `schemaVersion == 1`, use its `reviewer` field to override.
3. **Availability fallback** (MANDATORY): if the resolved provider is `codex`, run `ccb-mounted` and parse JSON. If `"codex"` ∉ `mounted` → demote to `mlx` (local MLX via `/mlx-reason`), then apply the Claude audit gate in Step 2.5 before using the verdict.

Default: `codex` → falls back to `mlx` when not mounted.

Implementation detail: Claude must not read repo files directly; request file reads via `/file-op` (`read_file`) and parse the JSON response. `ccb-mounted` runs via Bash and does not need `/file-op`.

### 1. Claude Initial Assessment

Evaluate against done conditions / acceptance criteria:
- What was accomplished?
- Are all conditions met?
- Any issues or risks?

Preliminary verdict: **PASS** / **FIX** / **UNCERTAIN**

### 2. Cross-Review (Provider)

If provider is:
- `codex` → use `/ask codex`
- `gemini` → use `/ask gemini`
- `mlx` (codex fallback) → use `/mlx-reason` with the same Cross-review payload below; then go through Step 2.5 Claude audit gate before using the output.

```
/ask <provider> "Cross-review:

Mode: [step|task]
Target: [step title / task name]
Conditions: [done conditions / acceptance]
Claude verdict: [PASS/FIX/UNCERTAIN] - [reason]

Your assessment:
1. Agree with Claude's verdict?
2. Issues Claude missed?
3. Final recommendation: PASS or FIX?

If FIX, list specific items (max 3).
Return JSON only."
```

### 2.5 Claude Audit Gate (MLX fallback only)

Triggered only when Step 2 ran `/mlx-reason`. Claude MUST audit the MLX output before the verdict is trusted:

- **Grounding check**: Do the reasoning / fix items reference real files, symbols, or plan sections from the submitted artifact? Reject hallucinations.
- **Verdict defensibility**: Is PASS/FIX consistent with the evidence? No rubber-stamp PASS, no unjustified FIX.
- **Actionability**: Each fix item points to a specific location.

Audit outcomes:

| Audit result | Action |
|--------------|--------|
| Accept | Treat MLX output as the `crossAssessment`; set `crossReviewer: "mlx"`, add `claudeAudit: "accepted"` with one-line note. |
| Accept with edits | Claude rewrites the fix items / verdict based on real evidence; set `crossReviewer: "mlx"`, `claudeAudit: "edited"` with rationale. |
| Reject | Discard MLX output; Claude issues the verdict directly; set `crossReviewer: "claude-fallback"`, `claudeAudit: "rejected"` with reason. |

### 3. Final Decision

| Claude | Cross-review | Result |
|--------|-------------|--------|
| PASS | PASS | → PASS (continue) |
| PASS | FIX | → FIX (Claude decides) |
| FIX | PASS | → FIX (merge items) |
| FIX | FIX | → FIX (merge items) |
| UNCERTAIN | * | → Claude makes final call |

## Output Schema

```json
{
  "mode": "step|task",
  "target": "<step title or task name>",
  "crossReviewer": "codex|gemini|mlx|claude-fallback",
  "claudeAudit": "n/a|accepted|edited|rejected",
  "claudeAuditNote": "<one-line rationale when claudeAudit != n/a>",
  "verdict": "PASS|FIX|BLOCKED",
  "claudeAssessment": {
    "verdict": "PASS|FIX|UNCERTAIN",
    "reason": "<reason>"
  },
  "crossAssessment": {
    "verdict": "PASS|FIX",
    "agreedWithClaude": true,
    "missedIssues": ["<issue>"],
    "fixItems": ["<item>"]
  },
  "finalDecision": {
    "verdict": "PASS|FIX|BLOCKED",
    "reason": "<reason>",
    "fixItems": ["<if FIX>"]
  }
}
```

`claudeAudit` is `n/a` when `crossReviewer` ∈ {`codex`, `gemini`}; mandatory when `crossReviewer` ∈ {`mlx`, `claude-fallback`}.

## Mode-Specific Checklist

### step mode
- Done conditions satisfied?
- Code changes correct?
- No regressions introduced?

### task mode
- All acceptance criteria met?
- Gaps or missing pieces?
- Code quality issues?
- Documentation complete?
- Tests passing?

## Principles

1. **Unified schema**: Same output format for both modes
2. **Mode-specific prompts**: Different checklists per mode
3. **Traceable**: Full assessment captured for plan_log/report
