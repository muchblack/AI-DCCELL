---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
disable-model-invocation: true
---

Run a `/grilling` session, using the `/domain-modeling` skill.

When you state a fact about the codebase or existing docs, tag it:

- `EXTRACTED: <path:line>` — you read it directly (code, `CONTEXT.md`, an ADR).
- `INFERRED: <why>` — you reasoned it without seeing it confirmed.

Look up an `INFERRED` fact before building on it. If the environment can't confirm it, put it to the user as a question rather than letting it pass as settled. Only `EXTRACTED` facts go into `CONTEXT.md` or an ADR.

## Before the first question: recon

Read what the plan touches before asking anything: `CONTEXT.md` / `CONTEXT-MAP.md`, relevant `docs/adr/`, and the code involved (entry points, callers, writers of shared state). Greenfield with no code → say so and go straight to the questions.

Show one **assumptions ledger**: each line a fact the plan relies on, tagged as above. Then ask only about what the ledger leaves open — `INFERRED` items you couldn't confirm, and decisions. Never ask the user something an `EXTRACTED` line already answers. Questions stay one at a time.

## When shared understanding is reached: handoff

End with a **handoff summary** in the conversation (not a new file) so `/to-spec` can synthesize without re-interviewing:

- **Problem / goal** — from the user's perspective.
- **Decisions made** — each with the answer the user gave.
- **Acceptance scenarios** — observable behavior, one per line.
- **Test seams and known verification commands** — `EXTRACTED` where the repo shows them.
- **Out of scope.**
- **Open risks / unconfirmed `INFERRED` items.**

Don't write a spec, a PLAN.md, or tickets here — that's `/to-spec` and `/to-tickets`.
