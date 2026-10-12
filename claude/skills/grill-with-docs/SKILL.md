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
