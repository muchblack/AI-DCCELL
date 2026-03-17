# Learn Execution Flow

Review and manage instincts extracted from development sessions.

## Input

- `$ARGUMENTS`: Optional subcommand (`extract`, `review`, or empty = review)

## Execution Flow

### Mode A: Review Pending Instincts (default)

#### Step 1: Load Pending Instincts

Read all `.md` files from `~/.claude/instincts/pending/`.

If no pending instincts exist, report to the user:
```
目前沒有待審查的 instinct。
如需手動萃取，請執行 /learn extract
```

#### Step 2: Present Instincts for Review

For each pending instinct, display:

```
### Instinct: {id}
- **觸發條件**: {trigger}
- **行為**: {action}
- **領域**: {domain}
- **信心分數**: {confidence}
- **證據**: {evidence}
- **來源**: {source session/project}
```

#### Step 3: Claude Quality Review

For each instinct, evaluate:
1. **實用性** — Is this pattern genuinely useful for future sessions?
2. **原子性** — Is it truly one trigger + one action, not a compound behavior?
3. **準確性** — Does the evidence support this pattern?

Rate each instinct: 🟢 Approve / 🟡 Revise / 🔴 Reject

#### Step 4: Execute Decisions

- 🟢 **Approve**: Move file from `pending/` to `approved/`, update `status: approved` in frontmatter
- 🟡 **Revise**: Edit the instinct content (fix trigger/action/confidence), then move to `approved/`
- 🔴 **Reject**: Move file to `rejected/` with reason noted

#### Step 5: Summary

Display summary table:
```
| Instinct | 判定 | 理由 |
|----------|------|------|
| {id}     | 🟢/🟡/🔴 | {reason} |
```

---

### Mode B: Manual Extract (`/learn extract`)

#### Step 1: Find Observations

Locate observation files by scanning `~/.claude/observations/` for the current project.
Use the current working directory to determine the project ID.

If no observations exist, report and exit.

#### Step 2: Read Recent Observations

Read the last 100 lines of `observations.jsonl` for the current project.

#### Step 3: Send to MLX for Pattern Extraction

Use `mcp__mcp-ai-bridge__mlx_analyze` with this prompt:

```
Analyze these Claude Code tool usage observations and extract recurring development patterns.

OBSERVATIONS:
{recent observations}

RULES:
1. Only extract patterns appearing 2+ times or representing significant workflow decisions
2. Each instinct: one trigger, one action (atomic)
3. Focus on: coding style, tool usage, error resolution, workflow sequences
4. Assign confidence 0.3-0.7 based on evidence strength

Output as JSON array:
[{"id": "kebab-case", "trigger": "when...", "action": "do...", "domain": "code-style|testing|git|debugging|workflow|architecture", "confidence": 0.5, "evidence": "..."}]
```

#### Step 4: Write Pending Instincts

For each extracted pattern, create a file in `~/.claude/instincts/pending/` with frontmatter format:

```yaml
---
id: {id}
trigger: "{trigger}"
confidence: {confidence}
domain: {domain}
source: manual-extract-{date}
created: {ISO 8601}
status: pending
---

## Action
{action}

## Evidence
{evidence}
```

#### Step 5: Auto-Review

Immediately proceed to Mode A (review) for the newly created instincts.

---

## Instinct Lifecycle

```
observations.jsonl → MLX extract → pending/ → Claude review → approved/ or rejected/
```

Approved instincts in `~/.claude/instincts/approved/` are loaded by Claude at session start as behavioral guidelines.
