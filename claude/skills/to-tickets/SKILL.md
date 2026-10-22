---
name: to-tickets
description: Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring its blocking edges, published to Linear with native blocking links.
disable-model-invocation: true
---

# To Tickets

Break a plan, spec, or conversation into a set of **tickets** — tracer-bullet vertical slices, each declaring the tickets that **block** it.

The issue tracker is **Linear**. Run this once whenever a requirement is about to be opened into Linear — whether it came from `/to-spec`, `/grill-with-docs`, an existing Linear issue being decomposed, or straight from conversation — instead of publishing a single undifferentiated issue directly.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) — vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

Give each ticket its **blocking edges** — the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

Give each ticket a **severity** tier too, on a four-level scale (Critical/High/Medium/Low) that maps one-to-one onto Linear's native priority: Critical → Urgent (`1`), High → High (`2`), Medium → Medium (`3`), Low → Low (`4`). If the source material already grades severity (e.g. a security review's 🔴🟠🟡🟢, or its own vocabulary), keep its grading — map its four levels in order onto the four tiers rather than re-deriving them, and mention the source's own term in the ticket body if it helps. Otherwise assess the tier from impact and urgency. A ticket that isn't itself a graded finding (a performance improvement, a process/tech-debt item) still gets a tier — judge it by the same impact/urgency lens, never leave priority at No priority.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket — green is promised only there.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Severity**: Critical / High / Medium / Low
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct — does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown.

### 5. Publish the tickets to Linear

Publish one issue per ticket, in dependency order (blockers first) so each ticket's blocking edges can reference real identifiers that already exist:

- **Find the team/project**: match the repo's directory name (or git remote name) against Linear project names via `list_projects`. Exactly one match → use that project and its team. None or several matches → ask the user which Linear team/project to file under; don't guess. If this ticket set decomposes an existing parent issue, reuse that issue's project/team — don't re-derive it.
- **Ensure the triage label exists**: check `list_issue_labels` (scoped to that team) for `ready-for-agent`; create it with `create_issue_label` if missing.
- **Create each issue** with `save_issue`, in dependency order: `title` = ticket title, `team`/`project` = as found above, `description` = the ticket body per the template below (as Markdown), `labels` = `["ready-for-agent"]`, `priority` = the severity tier's Linear priority (Critical `1` / High `2` / Medium `3` / Low `4`). Severity lives only in `priority` — never create or apply severity labels.
- **Set native blocking edges**: on the blocked ticket's `save_issue` call, pass `blockedBy` = the just-created blocker issue identifier(s) (this is why creation order matters — a blocker must exist before you can reference it). A ticket with no blockers omits `blockedBy` entirely.
- If the source was an existing parent issue, add a link back to it (`links` param) rather than nesting — do NOT close or modify the parent issue itself.
- Report the created issues' identifiers and URLs back to the user, in the same dependency order.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

<issue-template>

## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective — not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

- A reference to each blocking ticket, or "None — can start immediately".

</issue-template>

Avoid specific file paths or code snippets in ticket descriptions — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.
