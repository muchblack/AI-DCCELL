---
name: herdr-dev
description: >-
  Herdr-architecture requirement-driven development flow. main (this Claude
  Code session) confirms the requirement, dispatches development to a
  worker agent pane (default: codex) under a mandatory red-green TDD
  contract, then routes the result to a reviewer agent pane (default: agy);
  on review failure it routes the findings back to the same worker to add a
  failing regression test, fix, and re-review. Worker/reviewer are
  overridable via --worker/--reviewer. main asks the user directly whenever
  a requirement question arises. Triggers on: herdr dev, herdr 開發, 需求開發,
  文件開發, 跑需求, 接需求, 照文件開發, spec dev, requirement-driven,
  需求驅動開發, 從文件開發, 開發這份需求. Examples: "/herdr-dev docs/spec.md",
  "/herdr-dev docs/feature-x.md phase 1", "/herdr-dev --resume",
  "/herdr-dev VIN-44 --worker=agy".
metadata:
  short-description: "Herdr requirement-driven dev: main confirm → worker (default codex) → reviewer (default agy) → fix loop"
---

# Herdr-Dev — Requirement-Driven Development Flow (Herdr)

Herdr-native end-to-end flow for turning a **requirement document** into
reviewed, working code. Successor to `/ccb-dev` — same contract, Herdr
transport instead of CCB tmux/ask.

```
input (doc / text)
  → [main] confirm requirement    ──(question?)──▶ ask the user directly
  → [worker pane] TDD develop       (RED → minimal GREEN, one slice at a time)
  → [main] verify TDD evidence via git, merge to main
  → [main] self-review via /linus-review   (CRITICAL? → fix loop, reviewer never sees it)
  → [reviewer pane] review          (quality + spec + TDD + security + perf)
  → PASS ? report : regression RED → fix GREEN → re-review (max 2 rounds)
```

Default worker = `codex`, default reviewer = `agy`; override with
`--worker`/`--reviewer` (see Usage).

## Usage

```
/herdr-dev <linear-issue-id | requirement-doc-path | inline description> [--worker=<agent>] [--reviewer=<agent>]
/herdr-dev --resume
```

`--worker` and `--reviewer` name the Herdr agent (as it appears in `herdr
agent list`, e.g. `codex`, `agy`, `opencode`) to use for each role. Defaults:
`--worker=codex`, `--reviewer=agy`. The two must resolve to different
panes — one CLI cannot both write and review the same change.

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

| Role | Agent (default) | How to resolve |
|------|-------|----------------|
| Orchestrator | `main` — this Claude Code session | self |
| Code Writer | **worker** — `codex` unless `--worker=<agent>` given | `herdr agent list` → pane whose agent matches the worker agent name |
| Code Reviewer | **reviewer** — `agy` unless `--reviewer=<agent>` given | `herdr agent list` → pane whose agent matches the reviewer agent name |

Resolve the worker/reviewer agent names first (from `--worker`/`--reviewer`,
defaulting to `codex`/`agy`); if they name the same agent, stop and ask the
user to pick two different agents — one CLI cannot both write and review
the same change. Then run `herdr agent list` and record the matching pane
ids (e.g. `w1:p2`) in state, along with the agent names used. If a required
pane is missing, tell the user which agent to start in a pane and END TURN —
do not spawn panes yourself unless asked.

**If the project is under git version control**: each dispatched pane gets
its own `git worktree` before it starts — worker at
`.herdr-dev/worktrees/worker-<slug>` on new branch `herdr/dev-<slug>`;
reviewer at `.herdr-dev/worktrees/reviewer-<slug>` checked out (detached) at
the merge commit. This is what actually fixes the transient
`fatal: Unable to write index.` failure noted below — separate worktrees
mean separate index files, so main and a pane's agent no longer race on the
same lock. Worker commits on `herdr/dev-<slug>`; main merges `--no-ff` into
main from main's own checkout. See `references/flow.md` Phase 2/3 for the
exact commands.

**If the project is not under git version control**: fall back to the
legacy shared-working-tree flow — all panes operate directly in the project
directory, sequentially (only one writes at a time).

**Responsibility boundary — who creates the worktree.** Only **main**
(the dispatcher) creates or switches worktrees, and only *before*
dispatching — `git worktree add` for the worker/reviewer path happens in
Phase 2 step 0 / Phase 3 step 5, run by main, before the brief is written.
The worker and reviewer panes never call `git worktree add`/`switch`
themselves. A dispatched brief states the pane's cwd, branch, and base
commit as facts to **verify**, not choices to make — if a pane's read of
`git status`/`pwd` doesn't match what the brief says, that is a blocker to
report back, not something to silently fix by creating or switching to a
different worktree.

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
- **Review is mandatory.** Every completed development goes through the
  reviewer before it is called done. The review brief includes the
  requirement's Linear issue id (or doc path, for pre-existing local specs)
  so the reviewer can pull the source itself; the reviewer verifies spec
  compliance and TDD evidence item by item, not just code quality.
- **A Linear-sourced requirement gets reported back on PASS.** If Step 0
  resolved a Linear issue id and the reviewer's final verdict is PASS, Phase 5 posts
  a status comment on that issue (outcome, merge/worker commit shas, branch,
  round count) and moves it to Done — see Phase 5. Doc-path/inline
  requirements have no issue to report to; skip silently. A flow that never
  reaches PASS has nothing to report (that's an escalation, not a
  completion).
- **main self-screens with `/linus-review` before handing off to the
  reviewer.** After merging (Phase 3), invoke `/linus-review` on the merged
  diff (`git diff <parent>..<merge-commit>`) before writing the review
  brief. This is a cheap, inline, same-turn check — no separate pane, no
  dispatch round-trip. If Pass 1 turns up a CRITICAL fatal issue, do not
  send it to the reviewer at all: treat it exactly like a Phase 4 FIX
  verdict (fix brief back to the worker, regression-test-first, re-verify,
  re-merge, re-run `/linus-review`) and it **counts toward the same
  2-round fix cap** — a cheap self-check is still a real round from the
  worker's perspective. If `/linus-review` comes back clean (no CRITICAL —
  🟡/🟢 taste findings are fine), fold its taste score and improvement
  notes into the review brief as context for the reviewer, so it isn't
  rediscovering the same things and can spend its attention on spec/TDD
  compliance.
- **Jev spec-readiness pre-flight is advisory only, never a gate.** Phase 1
  step 5 (`references/flow.md`) can run a same-turn Vercel AI Gateway check
  on the Requirement Brief before dispatch, to catch an ambiguous spec
  before it burns a full TDD round. No API key, or the call fails/times out
  → skip silently, never block dispatch on a third-party outage. A low or
  uncertain result is one input to main's own judgment on whether to raise
  a question — it can never auto-block, auto-approve, or be cited to the
  Emperor as the reason on its own.
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
  moment. Per-pane worktrees (the git-repo case above) eliminate this by
  construction; it can still happen in the non-git fallback flow. Retry once
  before treating it as a real failure.
- **Worktrees persist across fix rounds, don't recreate them.** A fix
  dispatch (Phase 4) reuses the existing `worker-<slug>` worktree and branch
  — `git worktree add` only runs once per slug, the first time. If the
  worktree path exists but `git worktree list` doesn't know about it (e.g.
  stale after manual cleanup), that's a real error — surface it rather than
  silently re-adding, since it usually means the `.git` metadata and the
  directory disagree.
- **Container bind-mounts may not cover a worktree path.** If the project
  runs its build/test commands inside a container (e.g. this environment's
  Podman `php-fpm` container, which only bind-mounts the main checkout under
  `/var/www/html/...`), a worktree created under `.herdr-dev/worktrees/...`
  may not be visible inside the container. Check this before dispatching a
  brief that assumes an in-container command will find the worktree files —
  if the mount doesn't cover it, flag it to the Emperor instead of guessing
  a fix (e.g. widening the compose mount) on their behalf.
- **Clean up worktrees automatically once development is complete and the
  Linear issue is Done** (Phase 5; standing order from the Emperor,
  2026-09-24 — do not ask again). `git worktree remove` the worker/reviewer
  paths and delete flow-created scratch dirs under `.herdr-dev/`, keeping the
  branch itself. Check `git status` in a worktree first; uncommitted changes
  → stop and report, never `--force` blindly. Before Done (still In Review,
  or a Phase 4 escalation the Emperor hasn't resolved) worktrees stay.
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
- **Fixes go back to the worker.** On FIX, route findings back to the worker
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
