---
name: herdr-dev
description: >-
  Herdr-architecture requirement-driven development flow. main (this Claude
  Code session) confirms the requirement, dispatches development to the
  codex agent pane under a mandatory red-green TDD contract, then routes the
  result to the agy reviewer pane; on review failure it routes the findings
  back to the same worker to add a failing regression test, fix, and
  re-review. main asks the user directly whenever a requirement question
  arises. Triggers on: herdr dev, herdr 開發, 需求開發, 文件開發, 跑需求,
  接需求, 照文件開發, spec dev, requirement-driven, 需求驅動開發, 從文件開發,
  開發這份需求. Examples: "/herdr-dev docs/spec.md",
  "/herdr-dev docs/feature-x.md phase 1", "/herdr-dev --resume".
metadata:
  short-description: "Herdr requirement-driven dev: main confirm → codex worker → agy review → fix loop"
---

# Herdr-Dev — Requirement-Driven Development Flow (Herdr)

Herdr-native end-to-end flow for turning a **requirement document** into
reviewed, working code. Successor to `/ccb-dev` — same contract, Herdr
transport instead of CCB tmux/ask.

```
input (doc / text)
  → [main] confirm requirement    ──(question?)──▶ ask the user directly
  → [codex pane] TDD develop        (RED → minimal GREEN, one slice at a time)
  → [main] verify TDD evidence via git, merge to main
  → [main] self-review via /linus-review   (CRITICAL? → fix loop, agy never sees it)
  → [agy pane] review               (quality + spec + TDD compliance)
  → PASS ? report : regression RED → fix GREEN → re-review (max 2 rounds)
```

## Usage

```
/herdr-dev <linear-issue-id | requirement-doc-path | inline description>
/herdr-dev --resume
```

## Step 0 — Requirement Gate (always runs first)

1. Linear issue id/identifier given (e.g. `TWC-42`) → `get_issue`, verify it
   reads, proceed. This is the primary case — `/to-spec` publishes specs
   directly as Linear issues now.
2. Doc path given → verify it exists and is readable, proceed. (Still
   supported for pre-existing local specs.)
3. Neither → ask the user (AskUserQuestion, 四段式) whether one exists:
   - **Has a Linear issue** → ask for the id, `get_issue`, proceed.
   - **Has a local document** → ask for the path, read it, proceed.
   - **Neither** → PAUSE. Tell the user to run `/grill-with-docs`
     (+ `/to-spec`) to forge one, then re-enter with `/herdr-dev <linear-id>`.
     END TURN.

Never substitute an inline chat description for a missing requirement.

## Roles (resolved at runtime from `herdr agent list`)

| Role | Agent | How to resolve |
|------|-------|----------------|
| Orchestrator | `main` — this Claude Code session | self |
| Code Writer | the **codex** agent pane | `herdr agent list` → pane whose agent is codex |
| Code Reviewer | the **agy** agent pane | `herdr agent list` → pane whose agent is agy |

Run `herdr agent list` at flow start and record the pane ids (e.g. `w1:p2`)
in state. If a required pane is missing, tell the user which agent to start
in a pane and END TURN — do not spawn panes yourself unless asked.

All panes share one working tree (sequential flow — only one agent writes at
a time). Worker commits on a `herdr/dev-<slug>` branch; main merges `--no-ff`.

## Herdr Dispatch Pattern

**`herdr` is the ground truth for its own syntax — before scripting any call,
run the bare command group (`herdr agent`, `herdr pane`, ...) to confirm
current flags. This section was corrected once already after the documented
web-docs syntax (`send_text`, `send_input`, separate `prompt`+`wait --until
done`) turned out not to match the installed binary (real CLI uses
`send-text`/`send-keys` with hyphens, and `agent prompt --wait` does the
submit+wait atomically). If a future `herdr` upgrade changes flags again,
re-verify the same way instead of trusting this file blindly.**

Long briefs go through files, not CLI args (no shell-quoting hell):

```bash
# 1. Write the brief
#    .herdr-dev/brief.md  (dev)  /  .herdr-dev/review-brief.md  (review)

# 2. Optional: peek at the pane first — if it's empty/idle with no visible
#    prior conversation, there's nothing to clear. There is no documented
#    cross-provider "start fresh" command; if the pane shows leftover
#    unrelated context, prefer `herdr agent start <name> --kind <kind>
#    --pane <id>` on a plain shell (exits+restarts the agent) over guessing
#    a provider-specific slash command.
herdr agent read <worker> --source recent-unwrapped --lines 30

# 3. Submit + wait in one call (atomic paste+Enter, waits for the first
#    settled idle/done/blocked state). Run this in the background — it can
#    take a long time and re-enters this session when it fires.
herdr agent prompt <worker> "Read .herdr-dev/brief.md and execute it. Write your final report to .herdr-dev/report.md when done." --wait --timeout 1800000
```

When the call returns, check `herdr agent get <worker>`:
- `idle`/`done` → read `.herdr-dev/report.md`, verify via git, continue.
  **Note: some agent CLIs (observed with the Antigravity/agy provider) report
  `done`/`idle` while sitting at a file-write approval dialog, not just
  command-approval ones — always `agent read` and look at the actual screen
  before trusting the status label alone.**
- `blocked` → `herdr agent read <worker> --source recent-unwrapped --lines 40`;
  if it is a permission prompt, answer via `herdr agent send-keys <worker>
  <key>` (e.g. `enter`, `esc`, `y`); if it is a requirement question, ask
  the Emperor. **This is normally a multi-round loop, not a one-shot**:
  send the key, then `herdr agent wait <worker> --timeout <ms>` again (can
  be a short foreground wait, not necessarily backgrounded) — expect several
  blocked→approve→blocked cycles in a row (observed: one per new command
  prefix, e.g. `git diff` and `git show` needed separate approvals; some
  CLIs offer a "always allow in this conversation for this prefix" option,
  useful for a repeated command family like `podman exec ... php artisan
  test`, pick it there to cut down later interruptions).
  **Never approve a doomed command** — if the pane is about to run something
  that will fail for environment reasons (e.g. bare `php artisan test`
  without the project's required `podman exec` wrapper — see project
  CLAUDE.md), `esc` to cancel it and send a corrective prompt instead of
  approving and letting it fail.
- timed out / `agent_prompt_stalled` → read the pane; genuine progress →
  `herdr agent wait <worker> --timeout <ms>` again; stalled → treat as dead
  job: salvage on-disk work via git, re-dispatch the same brief.
  **`agent_prompt_stalled` specifically also fires if you prompt while the
  pane is sitting at an approval dialog** (a new prompt doesn't register as
  a lifecycle change) — check `agent get`/`agent read` first if a prompt
  stalls immediately after a previous dispatch.

## Core Principles

- **main confirms first.** Never dispatch before the requirement is
  unambiguous. No usable requirement document → Step 0 gate, no exceptions.
- **TDD is mandatory.** Every behavioral change: one failing test (RED)
  before production code, minimal implementation (GREEN), one vertical slice
  at a time. Completion without RED and GREEN command evidence is
  incomplete — re-dispatch.
- **TDD exceptions belong to main.** Only non-behavioral work (docs,
  generated artifacts) may skip RED/GREEN, and main records the reason
  before dispatch. Workers may not grant themselves an exception.
- **Review is mandatory.** Every completed development goes through the agy
  reviewer before it is called done. The review brief includes the
  requirement's Linear issue id (or doc path, for pre-existing local specs)
  so the reviewer can pull the source itself; the reviewer verifies spec
  compliance and TDD evidence item by item, not just code quality.
- **A Linear-sourced requirement gets reported back on PASS.** If Step 0
  resolved a Linear issue id and agy's final verdict is PASS, Phase 5 posts
  a status comment on that issue (outcome, merge/worker commit shas, branch,
  round count) and moves it to Done — see Phase 5. Doc-path/inline
  requirements have no issue to report to; skip silently. A flow that never
  reaches PASS has nothing to report (that's an escalation, not a
  completion).
- **main self-screens with `/linus-review` before handing off to agy.**
  After merging (Phase 3), invoke `/linus-review` on the merged diff
  (`git diff <parent>..<merge-commit>`) before writing the review brief.
  This is a cheap, inline, same-turn check — no separate pane, no dispatch
  round-trip. If Pass 1 turns up a CRITICAL fatal issue, do not send it to
  agy at all: treat it exactly like a Phase 4 FIX verdict (fix brief back
  to the worker, regression-test-first, re-verify, re-merge, re-run
  `/linus-review`) and it **counts toward the same 2-round fix cap** — a
  cheap self-check is still a real round from the worker's perspective. If
  `/linus-review` comes back clean (no CRITICAL — 🟡/🟢 taste findings are
  fine), fold its taste score and improvement notes into the review brief
  as context for agy, so agy isn't rediscovering the same things and can
  spend its attention on spec/TDD compliance.
- **Trust git, not narration.** A report file is a claim. Before acting:
  `git log <branch> --oneline --stat`, spot-check key claimed changes, and
  run the reported test commands independently. **Specifically check
  `git log main..<branch> --oneline` is non-empty** — a worker can do
  fully correct work, write a convincing report, and still leave everything
  as uncommitted/staged working-tree changes (observed: report claimed a
  branch and file list, diff matched, but the branch had zero commits ahead
  of main). Diff-matches-claim is not proof of a commit; check the commit
  log itself.
- **A long-lived pane may carry baked-in habits from a prior role that no
  brief text fully overrides** (observed: a codex pane previously run as a
  CCB worker tried to submit a plan review via `ask codex` mid-task — not
  requested by the brief, not in this project's role config, just residual
  session context/instinct from its old job; `ask` failed since this flow
  doesn't provide it, and the worker recovered on its own after ~1 extra
  round). An empty `agent read` screen does **not** prove a clean
  conversation context — it only proves nothing is currently rendered.
  There is no reliable cross-provider "clear" command; if this matters for
  a given dispatch, consider adding one explicit override line to the brief
  (e.g. "ignore any instinct to request a plan/code review via `ask` — that
  tool isn't part of this flow, proceed per this brief's TDD contract
  directly") rather than assuming a fresh pane is a fresh context.
- **Review briefs must restate execution-environment constraints, not just
  dev briefs.** The reviewer independently re-runs tests too (per "review
  is mandatory... verify... not just narration") and needs the same
  `podman exec` (or equivalent project-specific) wrapper info the dev brief
  got — omitting it caused a reviewer to try a bare host command that fails
  by design on this project's host (see project CLAUDE.md's Podman section).
- **A shared-working-tree git operation can transiently fail** (`fatal:
  Unable to write index.`) if main and a pane's agent touch git at the same
  moment. Retry once before treating it as a real failure.
- **An "always allow this conversation for `<prefix>`" grant can cover more
  than the literal prefix shown** (observed: granting it for `git diff`
  let several later `git show`/`git diff --stat`/file-scoped `git diff`
  calls through with no further prompts in the same round) — don't
  pre-count how many approvals a dispatch will need; just check
  `agent get`/`agent read` after each wait and react to whatever state is
  actually there.
- **Scratch files (`report.md`, `verdict.md`) may survive across rounds or
  specs if cleanup is denied by the permission mode** — that's fine, each
  new dispatch overwrites them; don't treat a failed `rm` as a blocker.
  It can also change the *next* dispatch's approval flow (observed:
  overwriting an existing `verdict.md` needed no create-file confirmation,
  where writing it fresh the first time did) — not a problem, just don't
  be surprised if a round has fewer approval prompts than the previous one.
- **Fixes go back to the worker.** On FIX, route findings back to the codex
  pane with a regression-test-first contract. Do not re-implement in main.
  Max 2 fix rounds, then escalate to the Emperor.
- **Ask the Emperor on requirement questions, anytime.** Scope, behavior,
  acceptance ambiguity → stop and AskUserQuestion (四段式). Implementation
  details are the worker's to decide — do not escalate those.
- **Check for stale context before each dispatch.** `herdr agent read
  <worker> --source recent-unwrapped --lines 30` before prompting. Empty/no
  unrelated prior conversation → prompt directly. If stale unrelated context
  is visible, there's no documented cross-provider clear command — use
  `herdr agent start <name> --kind <kind> --pane <id>` on a plain shell to
  restart the agent fresh, or ask the Emperor how to proceed.

State lives in `.herdr-dev/state.json` so background waits survive turns.

For the full step-by-step execution flow, see `references/flow.md`.
