---
name: ccb-dev
description: >-
  CCB-architecture requirement-driven development flow. Drives work from an
  existing requirement document (or, later, a task-system ticket such as Jira):
  main confirms the requirement, dispatches development to the codex-backed
  worker first under a mandatory red-green TDD contract, then routes the result
  to the codeReview group; on review failure it routes the issues back to the
  same worker group to add a failing regression test, fix, and re-review. main
  asks the user directly whenever a requirement question arises. Triggers on:
  需求開發, 文件開發, 跑需求, 接需求, 照文件開發, spec dev, ccb dev, ticket dev,
  requirement-driven, 需求驅動開發, 從文件開發, 開發這份需求.
  Examples: "/ccb-dev docs/spec.md", "/ccb-dev docs/feature-x.md phase 1",
  "/ccb-dev JIRA-123", "/ccb-dev --resume".
metadata:
  short-description: "CCB requirement-driven dev: main confirm → codex worker → codeReview → fix loop"
---

# CCB-Dev — Requirement-Driven Development Flow (CCB)

A CCB-native end-to-end flow for turning a **requirement document** (or, in
future, a **task-system ticket** like Jira) into reviewed, working code with
minimal hand-holding.

```
input (doc / ticket / text)
  → [main] confirm requirement   ──(question?)──▶ ask the user directly
  → [worker group] TDD develop     (RED → minimal GREEN, one slice at a time)
  → [main] verify TDD evidence
  → [codeReview group] review      (quality + spec + TDD compliance)
  → PASS ? report : regression RED → fix GREEN → re-review (loop)
```

## Usage

```
/ccb-dev <requirement-doc-path | ticket-id | inline description>
/ccb-dev --resume
```

## Step 0 — Requirement Document Gate (always runs first)

Before anything else, `main` MUST establish a requirement document:

1. If the invocation already includes a doc path (e.g. `/ccb-dev docs/spec.md`),
   verify the file exists and is readable, then proceed to requirement
   confirmation.
2. Otherwise, ask the user (AskUserQuestion, 四段式) whether a requirement
   document exists:
   - **Has a document** → ask for the path, read it, proceed.
   - **No document** → PAUSE the flow. Tell the user to run
     `/grill-with-docs` (a user-invoked skill; the model cannot call it) to
     forge the requirement through interview, then `/to-spec` if needed to
     produce the document. End the turn there. The user re-enters with
     `/ccb-dev <doc-path>` (or `--resume`) once the document exists.

Never substitute an inline chat description for a missing document, and never
start development without passing this gate.

## Roles (resolved from `.ccb/ccb.config`)

| Role | Agent | Notes |
|------|-------|-------|
| Orchestrator | `main` (self) | Confirms requirement, dispatches, decides, reports |
| Code Writer (primary) | **the codex-backed worker** (provider `codex` in the `work` window) | The Emperor's required default for development |
| Code Writer (fallback) | the opencode-backed worker (provider `opencode` in the `work` window) | Used only if the codex worker is unavailable/stalls |
| Code Reviewers | EVERY agent in the `codeReview` group (e.g. reviewer1 agy + reviewer2 codex) | `main` dispatches to each reviewer DIRECTLY (parallel), collects every verdict, and synthesizes. Do not rely on reviewer1 to fan out — in practice it does not actually dispatch. |

Always re-read `.ccb/ccb.config` at runtime; never hardcode if the config
disagrees. Resolve concrete agent names from the `work` window's provider
column (do not assume fixed names like `worker1`/`worker2`/`worker3` — they
vary per project). The "worker group" = the `work` window agents; the
"codeReview group" = the `codeReview` window agents.

## Core Principles

- **main confirms first.** Never dispatch development before the requirement is
  understood and unambiguous. A muddy requirement wastes a worker round-trip.
  If no usable requirement document exists, do NOT proceed — apply the
  Requirement Document Gate (Step 0) below.
- **codex worker is the default developer.** Route development to the
  codex-backed worker first; fall back to the opencode-backed worker only if
  the codex worker cannot run.
- **TDD is mandatory.** For every behavioral change, the worker must write and
  run one failing test before production code, implement only enough to pass,
  then repeat one vertical slice at a time. Completion without RED and GREEN
  command evidence is incomplete and must be re-dispatched.
- **TDD exceptions belong to main.** Only non-behavioral work that cannot
  reasonably be tested (for example documentation or generated artifacts) may
  skip RED/GREEN, and `main` must record the reason before dispatch. Workers
  may not grant themselves an exception.
- **Review is mandatory, not optional.** Every completed development goes
  through the codeReview group before it is called done. The review brief
  must include the requirement document path, and reviewers must verify
  spec compliance and TDD evidence against it item by item, not just code
  quality.
- **Full reviewer coverage (main fans out).** `main` dispatches the review
  **directly to every agent in the codeReview group** (parallel `ask` calls,
  one per reviewer), then collects and synthesizes their verdicts itself. Do
  NOT delegate fan-out to a single coordinator reviewer — empirically reviewer1
  replies "reviewer2 processing…" without ever creating a real job, so coverage
  silently drops to zero. Before deciding PASS/FIX, verify a real verdict came
  back from **each** group member (check each reviewer's job/reply, not just one
  agent's narration); if any is missing, re-dispatch that reviewer.
- **Trust git, not narration.** A worker's completion summary is a claim, not
  evidence. Before acting on it, `git log` the worker's branch and spot-check
  the key claimed changes. Empirically a worker has written into main's
  directory with an empty branch and no completion report — verify on disk.
- **Merge discipline.** Workers commit on their own `ccb/<worker>` branch;
  `main` spot-checks then merges `--no-ff` into main; reviews run against main
  at that commit. Before any fix re-dispatch, reset the worker's worktree to
  current main.
- **Fixes go back to whoever wrote the code.** On a FIX verdict, route the
  specific findings back to the same worker group, then re-review. Do not
  re-implement in `main`.
- **Stalls and incomplete replies.** A reply with `status=incomplete`, or a job
  silent well past its expected size, is a dead job: cancel it, salvage any
  on-disk work via git, and re-dispatch the same brief (opencode: `ccb clear`
  first). Do not wait on a corpse.
- **Ask the Emperor on requirement questions, anytime.** If a requirement-level
  ambiguity surfaces in any phase, stop and ask via AskUserQuestion (四段式).
  Do not guess on scope/acceptance; guessing on requirements is the expensive
  mistake.
- **Submit-then-stop.** CCB `ask` is async. After a submit returns
  `[CCB_ASYNC_SUBMITTED`, end the turn; the reply re-enters this session.

## CCB Ask Pattern

Below, `<codex-worker>` is the codex-backed agent resolved from the `work`
window (e.g. `worker1`) — substitute the real name from `.ccb/ccb.config`.

```bash
CCB_CALLER=main ask <codex-worker> <<'EOF'
<dev brief>
EOF

# Review: fan out to EVERY reviewer in the codeReview group, one ask each.
CCB_CALLER=main ask reviewer1 <<'EOF'
<review brief>
EOF
CCB_CALLER=main ask reviewer2 <<'EOF'
<review brief>
EOF
```

Async guardrail: when output contains `[CCB_ASYNC_SUBMITTED`, reply with one
short line (e.g. `<codex-worker> 開發中…`) and **END TURN**. Do not
poll/sleep/pend. On `--resume`, fetch with `pend <agent>`.

For the full step-by-step execution flow, see `references/flow.md`.
