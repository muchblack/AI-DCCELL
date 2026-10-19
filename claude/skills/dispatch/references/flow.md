# Dispatch — Multi-Provider Task Router

Split a work requirement into subtasks and route each to the optimal AI
provider running in a herdr pane.

**Provider matrix**: See `references/providers.md`

---

## Input

From `$ARGUMENTS`: a work requirement in natural language (Chinese or English).

---

## Execution Flow

### Step 1: Resolve Available Providers

```bash
herdr agent list
```

Keep the entries whose `cwd` matches this project's root, and record each
provider's pane id. Build `available_providers`:

- `codex`, `agy`, `gemini`, `opencode`, `droid`: available only if a live pane
  for this project exists
- `claude`: always available

No herdr panes at all → say so and offer to handle every subtask with Claude
directly; do not invent a transport.

### Step 2: Analyze & Decompose

Claude analyzes the requirement and decomposes it into subtasks.

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
Rule 3: Match task_type against the Provider Mapping table (providers.md)
         → Pick highest-priority AVAILABLE provider
Rule 4: If primary provider unavailable → try fallback chain
Rule 5: If all fallbacks unavailable → claude (always available)
```

**Parallel dispatch**: subtasks routed to different panes can run at the same
time. Subtasks routed to the same pane must be batched into one message.

**Writers**: at most one pane writes to a given working tree at a time. If two
subtasks would write code, give each its own git worktree (see the
`herdr-dev` skill) or run them sequentially.

### Step 4: Present Routing Plan

```markdown
## Dispatch Plan — [requirement summary]

**Available providers**: claude, codex, gemini
**Unavailable**: [list, or "none"]

| #   | Subtask               | Type       | Provider | Reason                      |
| --- | --------------------- | ---------- | -------- | --------------------------- |
| 1   | [subtask description] | review     | codex    | Code review specialist      |
| 2   | [subtask description] | brainstorm | gemini   | Creative exploration        |
| 3   | [subtask description] | architect  | claude   | Complex, needs full context |

**Parallel groups**: [which subtasks can run simultaneously]

Confirm? (Y / adjust / skip [N])
```

### Step 5: Dispatch

After the user confirms:

**5.1 Claude subtasks**: do them yourself, inline.

**5.2 Herdr subtasks**: for each one, write a focused brief to a scratch file
(subtask description, only the context needed, expected output format, and a
reply file path). Default reply contract unless the subtask needs prose: first
line = the answer or verdict; then findings as `path:line — note` bullets; then
open risks. No restating the brief, no process narration; long evidence goes in
a separate file cited by path. Then, for each pane:

```bash
herdr agent read <pane> --source recent-unwrapped --lines 30   # stale context?
herdr agent prompt <pane> "Read <brief-file> and respond. Write your findings to <reply-file> when done." --wait --timeout 900000
```

Run each `prompt --wait` call with the Bash tool's `run_in_background: true`;
it re-enters this session when it settles. Different panes can be started in
the same turn. For state handling (blocked / stalled / approval dialogs), follow
the "Herdr Dispatch Pattern" in the `herdr-dev` skill.

**5.3 Batch same-pane tasks** into one brief with numbered sections:

```
Please handle these tasks:

1. [Task A description]
2. [Task B description]

For each task, provide your response under the corresponding number.
```

### Step 6: Report

After dispatching, end the turn with a status table. When results arrive, read
each `<reply-file>` (or `herdr agent read`), then integrate them.

```markdown
## Dispatched

| #   | Subtask | Provider | Status    |
| --- | ------- | -------- | --------- |
| 1   | [desc]  | claude   | Done      |
| 2   | [desc]  | codex    | Submitted |
| 3   | [desc]  | gemini   | Submitted |
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

1. **User confirms before dispatch** — never send to a pane without confirmation
2. **Parallel when possible** — different panes can work simultaneously
3. **Verify status by reading the pane** — idle/done can hide an approval dialog
4. **Focused prompts** — each provider gets only the context it needs, not the entire conversation
5. **Batch same-pane** — don't send 3 separate messages to codex when 1 will do
6. **Fallback gracefully** — provider missing → next in chain → claude as last resort
