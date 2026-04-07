# Dispatch — Multi-Provider Task Router

Split a work requirement into subtasks and route each to the optimal AI provider.

**Provider matrix**: See `references/providers.md`

---

## Input

From `$ARGUMENTS`: a work requirement in natural language (Chinese or English).

---

## Execution Flow

### Step 1: Health Check

Run provider availability check:

```bash
bash ~/.claude/skills/scripts/health-check.sh 2>/dev/null
```

Parse result to build available provider list. Also check CCB providers:

```bash
ccb-mounted 2>/dev/null
```

Build `available_providers` map:

- `mlx`: health-check status
- `ollama`: health-check status
- `codex`: ccb-mounted status
- `gemini`: ccb-mounted status
- `opencode`: ccb-mounted status
- `droid`: ccb-mounted status
- `claude`: always available

### Step 2: Analyze & Decompose

Claude (designer) analyzes the requirement and decomposes into subtasks.

For each subtask, determine:

- **task_type**: one of `review`, `brainstorm`, `research`, `reason`, `draft-code`, `score`, `summarize`, `classify`, `refactor`, `architect`, `file-op`, `second-opinion`, `prototype`, `explore`
- **complexity**: `simple` | `medium` | `complex`
- **security_sensitive**: `true` | `false`
- **context_needed**: how much project context the subtask requires (`none`, `partial`, `full`)
- **estimated_size**: rough token estimate for the prompt

### Step 3: Route

For each subtask, apply routing rules in order:

```
Rule 1: security_sensitive == true → claude (no delegation)
Rule 2: context_needed == "full" AND complexity == "complex" → claude
Rule 3: Match task_type against Provider Mapping table (providers.md)
         → Pick highest-priority AVAILABLE provider
Rule 4: If primary provider unavailable → try fallback chain
Rule 5: If all fallbacks unavailable → claude (always available)
```

**Local provider preference**: When a subtask can be handled by local providers (mlx/ollama), prefer them to save cost — UNLESS the subtask quality is critical.

**Parallel dispatch**: Subtasks routed to different CCB providers can be dispatched simultaneously. Subtasks routed to the same provider must be batched into one message.

### Step 4: Present Routing Plan

Display the routing plan to the user:

```markdown
## Dispatch Plan — [requirement summary]

**Available providers**: claude, codex, gemini, mlx, ollama
**Unavailable**: [list, or "none"]

| #   | Subtask               | Type       | Provider | Reason                      |
| --- | --------------------- | ---------- | -------- | --------------------------- |
| 1   | [subtask description] | review     | codex    | Code review specialist      |
| 2   | [subtask description] | brainstorm | gemini   | Creative exploration        |
| 3   | [subtask description] | reason     | mlx      | Local reasoning, free       |
| 4   | [subtask description] | architect  | claude   | Complex, needs full context |

**Cost estimate**: [N] cloud calls + [N] local calls
**Parallel groups**: [which subtasks can run simultaneously]

Confirm? (Y / adjust / skip [N])
```

### Step 5: Dispatch

After user confirms:

**5.1 Local providers first** (synchronous, immediate result):

For MLX tasks:

```bash
bash ~/.claude/skills/scripts/mlx-chat.sh \
  -s "<task-specific system prompt>" \
  -t 0.3 -m 4096 \
  "<subtask prompt>"
```

For Ollama tasks:

- Use MCP tools `ollama_code` / `ollama_review` / `ollama_chat`

Collect local results immediately.

**5.2 CCB providers** (asynchronous via /ask):

For each CCB subtask, craft a focused prompt that includes:

- The subtask description
- Relevant context (files, code snippets) — only what's needed
- Expected output format
- Any results from local providers that inform this subtask

Dispatch via:

```bash
CCB_CALLER=claude ask <provider> "<crafted prompt>"
```

**Important**: Follow Async Guardrail — after all `/ask` calls are submitted, report status and END TURN.

**5.3 Batch same-provider tasks**:

If multiple subtasks route to the same provider, combine them into a single prompt with numbered sections:

```
Please handle these tasks:

1. [Task A description]
2. [Task B description]

For each task, provide your response under the corresponding number.
```

### Step 6: Report

After dispatching:

```markdown
## Dispatched

| #   | Subtask | Provider | Status                     |
| --- | ------- | -------- | -------------------------- |
| 1   | [desc]  | mlx      | Done (inline result below) |
| 2   | [desc]  | codex    | Submitted                  |
| 3   | [desc]  | gemini   | Submitted                  |

### Local Results

#### Subtask 1: [desc]

[MLX result]

### Pending

Use `/pend codex` and `/pend gemini` to retrieve async results.
```

---

## Adjustment Commands

User can adjust the routing plan before confirmation:

- `skip 2` — remove subtask 2
- `move 3 to claude` — override provider for subtask 3
- `merge 1,2` — combine subtasks 1 and 2
- `add "new subtask description"` — add a subtask
- `reorder 3,1,2` — change execution order

After adjustment, re-display the updated plan.

---

## Principles

1. **User confirms before dispatch** — never auto-send to CCB without confirmation
2. **Local first** — prefer mlx/ollama for cost savings when quality permits
3. **Parallel when possible** — different providers can work simultaneously
4. **Async guardrail** — respect CCB async rules, end turn after submission
5. **Focused prompts** — each provider gets only the context it needs, not the entire conversation
6. **Batch same-provider** — don't send 3 separate messages to codex when 1 will do
7. **Fallback gracefully** — provider down → next in chain → claude as last resort
