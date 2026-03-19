# MAGI Consensus Engine

Three-system consensus voting with veto power. Inspired by Evangelion MAGI supercomputer.

**Roles** (resolve via CLAUDE.md Role Assignment):
- MELCHIOR-1 (Scientist) → `claude` — analytical, technical quality, logic
- BALTHASAR-2 (Mother) → `codex` — protective, risk-averse, backward compatibility
- CASPER-3 (Woman) → `gemini` — creative, user experience, intuitive

---

## Input Parameters

From `$ARGUMENTS`:
- `proposal`: The decision or artifact to evaluate (plan, code diff, design choice, etc.)
- `context`: Optional background context

---

## Execution Flow

### Phase 1: MELCHIOR-1 Self-Evaluation (Claude, before async)

Claude evaluates the proposal FIRST, before delegating to other systems.
This MUST complete before any /ask calls to preserve state across END TURN.

**1.1 Generate MELCHIOR-1 Vote**

Evaluate the proposal from the Scientist/Logic perspective:

```json
{
  "system": "MELCHIOR-1",
  "vote": "APPROVE | VETO",
  "risk_mass": 0.0-1.0,
  "reasoning": "Technical analysis of the proposal",
  "conditions": ["optional conditions for approval"]
}
```

- `risk_mass > 0.7` → vote = VETO
- `risk_mass <= 0.7` → vote = APPROVE (may include conditions)

**1.2 Save Session State**

Write `.ccb/magi_state.json` with:

```json
{
  "session_id": "magi-<timestamp>",
  "status": "WAITING_VOTES",
  "proposal": "<proposal text or hash>",
  "proposal_hash": "<sha256 first 8 chars>",
  "created_at": "<ISO timestamp>",
  "sync_window_seconds": 120,
  "melchior_vote": { "system": "MELCHIOR-1", "vote": "APPROVE", "risk_mass": 0.3, "reasoning": "...", "conditions": [] },
  "received_votes": [],
  "pending_tasks": {},
  "expected_providers": ["codex", "gemini"]
}
```

### Phase 2: Delegate to BALTHASAR-2 and CASPER-3 (Async)

**2.1 Send Vote Requests**

Send to both providers via `/ask`. Each `/ask` returns a `[CCB_ASYNC_SUBMITTED]` line
containing a task ID. Save these task IDs to `magi_state.json` for later correlation.

```
/ask codex [MAGI_VOTE_REQ session_id=<session_id>]
<vote prompt from references/vote-prompt.md with BALTHASAR-2 preamble>

Proposal:
<proposal text>
```

```
/ask gemini [MAGI_VOTE_REQ session_id=<session_id>]
<vote prompt from references/vote-prompt.md with CASPER-3 preamble>

Proposal:
<proposal text>
```

**2.2 Save Task IDs**

After each `/ask`, extract the task ID from `[CCB_ASYNC_SUBMITTED]` output and
update `magi_state.json`:

```json
{
  "pending_tasks": {
    "codex": "20260318-112345-123-45678",
    "gemini": "20260318-112345-456-78901"
  }
}
```

**2.3 Async Guardrail Compliance**

After sending both /ask calls:
1. Output: `MAGI 投票已送出。等待 BALTHASAR-2 和 CASPER-3 回覆...`
2. **END TURN** — mandatory, do not poll or wait

---

### Phase 3: Vote Collection (Hook-Driven)

The existing `ccb-completion-hook` automatically sends provider responses back to
Claude's terminal pane when providers complete. **No hook modification needed.**

The hook injects text in this format:
```
CCB_REQ_ID: <task_id>

[CCB_TASK_COMPLETED]
Provider: <Codex|Gemini>
Status: Completed

Result: <provider's full response including vote JSON>
```

**3.1 Session Re-hydration (Detecting MAGI Votes)**

When Claude receives a `[CCB_TASK_COMPLETED]` message:

1. Check if `.ccb/magi_state.json` exists and `status == "WAITING_VOTES"`
2. Match `CCB_REQ_ID` against `pending_tasks` in `magi_state.json`
3. If match found → this is a MAGI vote response, enter aggregation mode
4. If no match → treat as normal CCB completion (not MAGI-related)

**Important**: The hook sends `\r` (Enter) to the terminal after injecting text,
but Claude Code still requires user to confirm submission. This is a **known MVP
limitation** — user must press Enter once per provider response (max 2 times).

**3.2 Vote Parsing (with fallback)**

Parse the `Result:` content from the hook-injected message:

1. **JSON parse** — look for `{ "system": ..., "vote": ..., "risk_mass": ... }` block
2. **Regex fallback** — extract `"vote"\s*:\s*"(APPROVE|VETO)"` and `"risk_mass"\s*:\s*([0-9.]+)`
3. **ABSTAIN** — if both fail, record as `{ "system": "<name>", "vote": "ABSTAIN", "risk_mass": null, "reasoning": "Response could not be parsed" }`

**3.3 Completeness Check**

After parsing each vote:
- Update `magi_state.json`: add vote to `received_votes`, remove from `pending_tasks`
- If all expected votes received → proceed to Phase 4
- If partial votes received → inform user: `已收到 N/2 票。等待剩餘投票...`
  (user may need to confirm next hook injection)
- If sync window expired (120s from `created_at`) → proceed with available votes (DEGRADED mode)

**3.4 Handling Both Votes in Single Turn**

If both providers complete before user confirms, the hook may inject both responses
consecutively. In this case, parse both `[CCB_TASK_COMPLETED]` blocks in a single
turn and proceed directly to Phase 4.

---

### Phase 4: Consensus Aggregation

**4.1 Decision Table**

```
DECISION TABLE (Formal)
========================
Individual threshold: risk_mass > 0.7 = VETO by that system

Aggregation rules (priority order):
  1. Any system vote == VETO (risk_mass > 0.7)
     -> PATTERN_BLUE (overall VETO)
     -> Report: which system vetoed and why

  2. All systems vote == APPROVE (risk_mass <= 0.7)
     -> SYNCHRONIZED (overall APPROVE)
     -> Report: consensus summary

  3. Mixed votes but no VETO (disagreement within approve range)
     -> DISSENT_DETECTED (DEADLOCK)
     -> Escalate to Emperor with three options:
       A) Adopt majority opinion (if 2:1)
       B) Adopt specific system opinion (user chooses)
       C) Reject, revise proposal and re-vote

  4. 1+ system ABSTAIN, remaining unanimous
     -> Follow remaining consensus (DEGRADED)
     -> Note: reduced confidence

  5. 1+ system ABSTAIN, remaining split
     -> INCONCLUSIVE
     -> Escalate to Emperor

  6. 2+ systems ABSTAIN
     -> INCONCLUSIVE
     -> Escalate to Emperor
```

**4.2 Display Result**

```
MAGI CONSENSUS RESULT
=====================
Session: <session_id>
Status: SYNCHRONIZED | PATTERN_BLUE | DISSENT_DETECTED | INCONCLUSIVE

| System       | Vote    | Risk Mass | Key Reasoning          |
|-------------|---------|-----------|------------------------|
| MELCHIOR-1  | APPROVE | 0.3       | Technically sound      |
| BALTHASAR-2 | APPROVE | 0.4       | Low risk, compatible   |
| CASPER-3    | VETO    | 0.8       | UX concerns identified |

Result: PATTERN_BLUE (VETO by CASPER-3)
Reason: [primary veto reasoning]

Dissent Record: saved to .ccb/apocrypha.jsonl
```

---

### Phase 5: Dissent Logging

Append to `.ccb/apocrypha.jsonl` (one JSON object per line):

```json
{
  "session_id": "magi-<timestamp>",
  "timestamp": "<ISO timestamp>",
  "proposal_hash": "<sha256 first 8 chars>",
  "proposal_summary": "<first 100 chars of proposal>",
  "votes": [
    { "system": "MELCHIOR-1", "provider": "claude", "vote": "APPROVE", "risk_mass": 0.3, "reasoning": "...", "conditions": [] },
    { "system": "BALTHASAR-2", "provider": "codex", "vote": "APPROVE", "risk_mass": 0.4, "reasoning": "...", "conditions": [] },
    { "system": "CASPER-3", "provider": "gemini", "vote": "VETO", "risk_mass": 0.8, "reasoning": "...", "conditions": [] }
  ],
  "consensus_result": "PATTERN_BLUE",
  "degraded": false,
  "abstained": [],
  "emperor_override": null
}
```

---

## State Machine

```
IDLE -> EVALUATION (/magi invoked)
EVALUATION -> MELCHIOR_VOTED (Claude self-evaluates, saves state)
MELCHIOR_VOTED -> WAITING_VOTES (/ask codex + /ask gemini sent, END TURN)
WAITING_VOTES -> COLLECTING (hook returns vote(s), session re-hydrated)
COLLECTING -> COLLECTING (partial votes, waiting for more)
COLLECTING -> AGGREGATION (all votes collected)
COLLECTING -> DEGRADED (sync window 120s timeout)
DEGRADED -> AGGREGATION (proceed with available votes, 2-system quorum)
AGGREGATION -> SYNCHRONIZED (all approve)
AGGREGATION -> PATTERN_BLUE (any veto)
AGGREGATION -> DISSENT_DETECTED (mixed, no veto)
AGGREGATION -> INCONCLUSIVE (too many abstains)
SYNCHRONIZED -> LOG_AND_RETURN
PATTERN_BLUE -> LOG_AND_RETURN
DISSENT_DETECTED -> ESCALATE_TO_EMPEROR -> LOG_AND_RETURN
INCONCLUSIVE -> ESCALATE_TO_EMPEROR -> LOG_AND_RETURN
LOG_AND_RETURN -> IDLE
```

---

## Error Handling

- **Provider unreachable**: /ask fails -> mark that system as ABSTAIN, continue
- **Malformed response**: Regex fallback -> ABSTAIN if still unparseable
- **Session file missing**: Create new session (treat as first invocation)
- **Session ID mismatch**: Warn user, do not aggregate (possible stale injection)
- **Sync window expired**: Proceed with available votes, set degraded: true

---

## Principles

1. **Independent Evaluation**: Each system evaluates blind — no system sees another vote before voting
2. **Veto is Absolute**: One VETO blocks the decision (PATTERN_BLUE)
3. **Emperor is Supreme**: DEADLOCK and INCONCLUSIVE always escalate to user
4. **State Survives END TURN**: All context saved to magi_state.json before async delegation
5. **Graceful Degradation**: 2-system quorum > 1-system advisory > INCONCLUSIVE
6. **Async Guardrail Preserved**: /ask then END TURN, never poll or wait
7. **Dissent is Sacred**: Every vote recorded with full reasoning (Supreme Court analogy)
