# Review

Dual review by Claude (initial assessment) and a configurable cross-review provider (MLX by default; codex retired 2026-05-05).

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

1. **CLAUDE.md Role Assignment table** (primary): Read the Role Assignment table in CLAUDE.md. The `reviewer` role maps to a provider (e.g., `mlx`, `ollama`).
2. **`.autoflow/roles.json`** (override): If this file exists in the repo, and `enabled == true` and `schemaVersion == 1`, use its `reviewer` field to override.
3. **Availability fallback** (MANDATORY): per the CLAUDE.md Reviewer Fallback Protocol, the chain is `mlx` → `ollama` → `claude-fallback`. Probe each in order: MLX server reachable at `localhost:8090`? else Ollama reachable at `192.168.1.206:11434`? else self-audit. The Claude audit gate in Step 2.5 applies whenever the cross-reviewer is `mlx` or `ollama` (always for non-Claude reviewers post-codex retirement).

Default: `mlx` (primary) → `ollama` (fallback) → `claude-fallback` (last resort).

Implementation detail: Claude reads repo files directly via Read/Edit tools (no `/file-op` indirection). Server availability probes run via Bash.

### 1. Claude Initial Assessment

Evaluate against done conditions / acceptance criteria:
- What was accomplished?
- Are all conditions met?
- Any issues or risks?

Preliminary verdict: **PASS** / **FIX** / **UNCERTAIN**

### 2. Cross-Review (Provider)

If provider is:
- `mlx` (default) → invoke `/mlx-reason` with the Cross-review payload below; then go through Step 2.5 Claude audit gate.
- `ollama` (MLX fallback) → call `ollama_review` via MCP Bridge with the same payload; then go through Step 2.5 Claude audit gate.
- `gemini` → use `/ask gemini` (only if explicitly configured in `.autoflow/roles.json`; not in default chain).
- `claude-fallback` → Claude issues verdict directly with explicit `claudeAudit: "rejected"` rationale.

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

### 2.5 Claude Audit Gate (MANDATORY for mlx / ollama)

Triggered whenever Step 2 ran `/mlx-reason` or `ollama_review`. Claude MUST audit the cross-reviewer output before the verdict is trusted:

- **Grounding check**: Do the reasoning / fix items reference real files, symbols, or plan sections from the submitted artifact? Reject hallucinations.
- **Verdict defensibility**: Is PASS/FIX consistent with the evidence? No rubber-stamp PASS, no unjustified FIX.
- **Actionability**: Each fix item points to a specific location.

Audit outcomes:

| Audit result | Action |
|--------------|--------|
| Accept | Treat cross-reviewer output as the `crossAssessment`; set `crossReviewer: "mlx"` or `"ollama"`, add `claudeAudit: "accepted"` with one-line note. |
| Accept with edits | Claude rewrites the fix items / verdict based on real evidence; preserve `crossReviewer`, set `claudeAudit: "edited"` with rationale. |
| Reject | Discard cross-reviewer output; Claude issues the verdict directly; set `crossReviewer: "claude-fallback"`, `claudeAudit: "rejected"` with reason. |

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
  "crossReviewer": "mlx|ollama|gemini|claude-fallback",
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

`claudeAudit` is mandatory when `crossReviewer` ∈ {`mlx`, `ollama`, `claude-fallback`}; `n/a` only when explicitly using `gemini` via `.autoflow/roles.json` override.

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
