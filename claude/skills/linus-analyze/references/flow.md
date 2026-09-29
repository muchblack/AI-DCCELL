# Linus-Style Requirement Analysis

Five-layer analysis framework, from requirement understanding to an actionable
decision. Claude performs the analysis directly; no external model is involved.

## Relationship to the grill skills

- Requirement is vague, or decisions are still open → run `/grill-with-docs`
  (or `/grilling`) **first**. Those skills draw the decisions out of the user;
  this skill judges a requirement that is already understood.
- Requirement is clear, but you need a verdict on whether and how to build
  it → run this skill.
- Do not run both on the same question at once. Grill first, analyze after
  the shared understanding is confirmed.

## Input

- `$ARGUMENTS`: the user's requirement description or technical question

## Execution Flow

### Step 0: Three Pre-Check Questions (Short-Circuit)

```text
1. "Is this a real problem or imagined?" — Reject over-engineering
2. "Is there a simpler way?" — Always seek the simplest solution
3. "Will it break anything?" — Backward compatibility is iron law
```

**Short-circuit rule**: if the answer is "fake problem / simpler method
exists / will break things", give a brief conclusion and skip the five layers.

### Step 1: Confirm Understanding

Restate the requirement in one or two sentences and ask whether it is
accurate. Wait for confirmation before continuing. If it is wrong, clarify
first. If the restatement keeps failing, the requirement is not ready — hand
off to `/grill-with-docs`.

### Step 1.2: Jev Spec-Readiness Pre-flight (advisory, optional, best-effort)

Run right after the user confirms the restatement, before spending effort on
the five layers. A cheap same-turn check via Vercel AI Gateway on whether the
confirmed requirement is concrete enough to analyze. Same mechanism as the
`herdr-dev` Phase 1 pre-flight; if that one is retuned, retune this to match.

**Data note**: this sends the requirement text to a third-party service. If
the requirement contains secrets, customer data or anything the user would not
paste into an external API, skip this step.

- Write the request body to a scratch file first (long text in a shell `-d`
  string is quoting hell):
  ```bash
  REQ=$(mktemp)
  cat > "$REQ" <<'EOF'
  {
    "model": "typesafe-ai/jev",
    "state": "<the confirmed requirement from Step 1, verbatim>",
    "questions": {
      "is_spec_actionable": {"type": "boolean", "instructions": "Is this requirement specific and actionable enough for a developer to implement without further clarification?"},
      "has_unambiguous_acceptance_criteria": {"type": "boolean", "instructions": "Does this requirement include clear, checkable acceptance criteria?"}
    }
  }
  EOF
  ```
- Call it, reading `AI_GATEWAY_API_KEY` from the environment (**never** write
  the key's value into any file, brief, note or output):
  ```bash
  curl -sS --max-time 10 https://ai-gateway.vercel.sh/v1/evaluate \
    -H "Authorization: Bearer $AI_GATEWAY_API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$REQ"
  rm -f "$REQ"
  ```
- **No key set, call errors, times out, or non-200 → skip silently and go to
  the next step.** Never block or delay the analysis on a third-party outage.
- Read `answers.<question>.probability` (0–1). The endpoint does not fill a
  separate confidence field, so use distance from 0.5 as the uncertainty
  proxy: `abs(probability - 0.5) < 0.3` on either question → uncertain.
- **Advisory only, never a gate.** Uncertain or low → it is one input to your
  own judgment. If your own read agrees the requirement is loose, name the
  actual ambiguity to the user and suggest `/grill-with-docs` before the
  five layers. Do not cite "Jev said X" as the reason, and do not auto-stop.
  Confident on both → say nothing, proceed.
- Do not use it to skip Step 0 or the analysis itself: it judges how
  specified the requirement is, not whether it is worth doing.

### Step 1.5: DB Schema Context (only if the task touches the database)

For CRUD, schema changes or data-flow questions, run `/db` first to get the
real table structure. This matters most for Layer 1 and Layer 4.

### Step 2: Five-Layer Analysis

Go through the layers in order. Look up facts in the codebase instead of
asking the user; only real decisions go back to the user.

**Layer 1 — Data structure**
"Bad programmers worry about the code. Good programmers worry about data
structures."
- What is the core data and how is it related?
- Where does it flow, who owns it, who mutates it?
- Any unnecessary copying or transformation?

**Layer 2 — Special cases**
"Good code has no special cases."
- List every if/else the feature implies.
- Which are genuine business rules, and which patch a bad design?
- Can the data structure be redesigned so the branches disappear?

**Layer 3 — Complexity**
"If the implementation needs more than 3 levels of indentation, redesign it."
- What is the essence of the feature, in one sentence?
- How many concepts does the current approach need? Can it be halved?

**Layer 4 — Destructive impact**
"Never break userspace."
- What existing behavior could be affected?
- Which dependencies would break?
- How to improve without breaking any of it?

**Layer 5 — Practicality**
"Theory and practice sometimes clash. Theory loses."
- Does the problem exist in production? How many users hit it?
- Does the solution's complexity match the problem's severity?

### Step 2.5: Self-Check Before Output

Before writing the decision, check the analysis against these four points and
fix the analysis if any fails:

1. Did you identify the real core data structure, not a surface feature?
2. Are the special cases complete, and did you try to eliminate them rather
   than handle them?
3. Is the breakage analysis complete — any userspace you did not check?
4. Is the conclusion practical, or is it over-engineering / solving a
   non-existent problem?

### Step 3: Decision Output

Use this fixed format, no additions and no omissions:

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

## Follow-up Guide

| Verdict                          | Next                                                          |
| -------------------------------- | ------------------------------------------------------------- |
| ✅ Worth doing + spec still loose | `/grill-with-docs` → `/to-spec`                               |
| ✅ Worth doing + ready to build   | `/herdr-dev <linear-id \| doc-path>`                          |
| ✅ Worth doing + simple change    | Implement directly and self-review with `/linus-review`      |
| ✅ Worth doing + Laravel          | `laravel-simplifier` agent                                    |
| ✅ Worth doing + frontend UI      | `frontend-developer` or `pragmatic-ui-architect` agent        |
| ❌ Not worth doing                | Report the reasoning and what the real problem is             |

## Principles

1. The three pre-check questions can short-circuit the whole flow.
2. Wait for the user to confirm the requirement before the five layers.
3. Decisions belong to the user; facts belong to the codebase.
   The Jev pre-flight is advisory input, never a gate, and never a stated reason.
4. The output format is fixed.
5. Criticism targets technical issues, never the person.
