---
name: herdr-dev
description: "Requirement-driven development: a worker pane builds under red-green TDD, a reviewer pane reviews, and failures loop back to the worker. Triggers on: herdr dev, herdr 開發, 需求開發, 文件開發, 跑需求, 接需求, 照文件開發, spec dev, requirement-driven, 需求驅動開發, 從文件開發, 開發這份需求."
argument-hint: "<linear-id|doc-path|description> [--worker=<agent>] [--reviewer=<agent>] | --resume"
metadata:
  short-description: "Herdr requirement-driven dev: main confirm → worker (default codex) → reviewer (default agy) → fix loop"
---

# Herdr-Dev — Requirement-Driven Development Flow (Herdr)

Herdr-native end-to-end flow for turning a **requirement document** into
reviewed, working code, dispatched over the Herdr CLI.

```
input (doc / text)
  → [main] confirm requirement    ──(question?)──▶ ask the user directly
  → [reviewer pane] review the brief (APPROVED/REVISE, max 2 rounds; main arbitrates)
  → [worker pane] TDD develop       (RED → minimal GREEN, one slice at a time)
  → [main] verify TDD evidence via git, merge to main
  → [main] self-review via /linus-review   (CRITICAL? → fix loop, reviewer never sees it)
  → [reviewer pane] review          (quality + spec + TDD + security + perf)
  → PASS ? report : regression RED → fix GREEN → re-review (max 2 rounds)
  → PASS with 🟡 tuning suggestions → one tuning round → confirm review → report
     (tuning round does NOT count toward the 2-round fix cap)
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
   reads, proceed.
2. Doc path given → verify it exists and is readable, proceed.
3. Neither → ask the user (AskUserQuestion, 四段式) whether one exists:
   - **Has a Linear issue** → ask for the id, `get_issue`, proceed.
   - **Has a local document** → ask for the path, read it, proceed.
   - **Neither** → PAUSE. Tell the user to run `/grill-with-docs`
     (+ `/to-spec`) to forge one, then re-enter with `/herdr-dev <linear-id>`.
     END TURN.

Never substitute an inline chat description for a missing requirement.

## Roles (resolved at runtime from `$CTL list`)

| Role | Agent (default) | How to resolve |
|------|-------|----------------|
| Orchestrator | `main` — this Claude Code session | self |
| Code Writer | **worker** — `codex` unless `--worker=<agent>` given | `$CTL list` → id whose agent matches the worker agent name |
| Code Reviewer | **reviewer** — `agy` unless `--reviewer=<agent>` given | `$CTL list` → id whose agent matches the reviewer agent name |

Resolve the worker/reviewer agent names first (from `--worker`/`--reviewer`,
defaulting to `codex`/`agy`); if they name the same agent, stop and ask the
user to pick two different agents — one CLI cannot both write and review
the same change. Then run `$CTL list` (see Backend Adapter) and record the
matching ids (e.g. `w1:p2` on TUI, `t4` on Herdr desktop) in state, along
with the agent names used and `$CTL backend`. If a required
pane is missing, tell the user which agent to start in a pane and END TURN —
do not spawn panes yourself unless asked.

**If the project is under git version control**: each development and
code-review dispatch gets its own `git worktree` before it starts (the
Phase 1 brief review is the one exception: it is read-only, reads
main's own checkout, writes only its verdict file, and needs no
worktree) — worker at
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

## Backend Adapter (`scripts/herdr-ctl.sh`)

The same flow runs on two Herdr backends; **every pane call in this skill
goes through the adapter**, never straight to the `herdr` / `hc` CLIs:

```bash
CTL=~/.claude/skills/herdr-dev/scripts/herdr-ctl.sh
```

Backend (`$CTL backend` prints it): `HERDR_BACKEND=hc|tui` if set →
`hc` when `HC_TERMINAL_ID` is set (main runs inside a Herdr desktop pane)
→ `tui` when the TUI `herdr` answers → otherwise it errors out (exit 3):
tell the user, do not guess.

| Verb | Output / behaviour |
|------|--------------------|
| `$CTL list` | one line per agent: `<id>\t<agent>\t<status>\t<cwd>`; agent names normalized (`antigravity`→`agy`, `claude-code`→`claude`) |
| `$CTL status <id>` | exactly one of `idle｜working｜blocked｜done｜unknown` (hc `error` → `blocked`) |
| `$CTL prompt <id> "<text>"` | paste + submit, no wait, no stdout; refused (non-zero) while the pane is blocked |
| `$CTL wait <id> <seconds>` | until not working; still working at timeout → exit 124. **Seconds on both backends** |
| `$CTL read <id> <lines>` | last N screen lines |
| `$CTL keys <id> <key>…` | `enter`, `esc`, `y`, `down`, `ctrl+c`… |
| `$CTL start <agent> <cwd> [--pane <id>] [-- <agent args>]` | start an agent, print its id (hc: new terminal; tui: needs `--pane`, an existing pane at a shell prompt) |

Ids: TUI pane ids look like `w2:p2`; hc ids look like `t4` (remote:
`machine/t4`). Record whatever `$CTL list` prints — scripts accept both.

hc backend notes (verified 2026-11-04):
- `hc read` has no `recent-unwrapped`; the adapter trims trailing blank
  lines and returns the last N lines. While a terminal is `working`/
  `blocked`, hc returns only the visible screen (no history).
- `hc send` from inside a desktop pane wraps the prompt as
  `<hc from="<main id>">…</hc>` (observed 2026-11-04; the docs say it may
  also carry a `reach="hc send …"` hint). Briefs already forbid every
  `herdr`/`hc`/`herdr-ctl.sh` command, and approve-loop never approves one,
  so a worker replying that way is a brief violation: `esc` it.
- `$CTL start` on hc runs `hc run --bg --outlive-parent --no-notify --cwd
  <cwd>` (codex gets `--no-daemon`, required by hc; the agent is resolved
  to an absolute path first because herdr-core's PATH may lack
  `~/.local/bin`). Extra agent flags go after `--`, e.g. `$CTL start codex
  <wt> -- -s workspace-write`. A codex started in a new folder first shows
  its "Trust this folder?" dialog (status `unknown`): `$CTL read` it, then
  `$CTL keys <id> enter`, and wait for `idle` before the first prompt. If a
  codex hook is new or changed, a second dialog follows ("Hooks need review",
  also status `unknown`, so `wait-result.sh` won't wake on it): never trust
  hooks on the Emperor's behalf — pick "Continue without trusting"
  (`$CTL keys <id> down down enter`; `$CTL read` first to confirm it is
  option 3) and tell the Emperor which hook needs review (verified on hc
  2026-11-06). There is no hc
  equivalent of herdr's worktree workspaces: main creates the git worktree
  itself (`git worktree add …`, Phase 2 step 0 / Phase 3 step 5 — same as on
  TUI), then either tells the existing pane to `cd` into it (the brief
  already does) or starts a fresh agent there with `$CTL start <agent>
  <worktree>`.
- Tests: `bash scripts/test-herdr-ctl.sh` (both backends via stubs).

## Herdr Dispatch Pattern

**The installed `herdr` / `hc` binaries are the ground truth for their own
syntax — before changing `scripts/herdr-ctl.sh`, run `herdr --help`,
`hc --help` and `hc <cmd> --help` to confirm current flags; the web docs
have diverged from the binary before. Flag changes are fixed in the adapter
(and its test) only — nothing else in this skill names backend flags.**

Long briefs go through files, not CLI args (no shell-quoting hell):

```bash
# 1. Write the brief
#    .herdr-dev/tasks/<slug>/brief.md  (dev)  /  .herdr-dev/tasks/<slug>/review-brief.md  (review)

# 2. Optional: peek at the pane first — if it's empty/idle with no visible
#    prior conversation, there's nothing to clear. There is no documented
#    cross-provider "start fresh" command; if the pane shows leftover
#    unrelated context, prefer `$CTL start <agent> <cwd> [--pane <id>]`
#    (TUI: restarts the agent on a plain-shell pane; hc: a new terminal —
#    record its new id) over guessing a provider-specific slash command.
$CTL read <worker> 30

# 3. Submit WITHOUT --wait, then wait with scripts/wait-result.sh in the
#    background. It returns ONLY when the result file's first line is this
#    dispatch's id and the pane has settled — early idle/done flickers are
#    swallowed in the background instead of waking main.
$CTL prompt <reviewer> "Read .herdr-dev/tasks/<slug>/review-brief.md and execute it. Write verdict.md when done."
~/.claude/skills/herdr-dev/scripts/wait-result.sh <reviewer> .herdr-dev/tasks/<slug>/verdict.md <dispatch_id>
# worker: add --approve so allowlisted commands are auto-approved meanwhile
~/.claude/skills/herdr-dev/scripts/wait-result.sh <worker> .herdr-dev/tasks/<slug>/report.md <dispatch_id> \
  --approve <host_worktree> "podman exec -w <container_worktree_path> <container> "
```

**Always wait with `wait-result.sh`, never with a bare `$CTL wait` /
a backend's own prompt-and-wait / `approve-loop.sh`**. Each of those
returns on the first idle/done/blocked flicker; agy and codex flicker often,
and every early return costs main a full-context turn just to learn "still
working". `wait-result.sh` prints exactly one line:
`RESULT_READY` → read the file and continue; `NEEDS_REVIEW: <cmd>` → judge the
command (below), approve or `esc`, re-run the script; `BLOCKED` → `$CTL read`
the pane; `SETTLED_NO_RESULT` → the pane stopped ~2 min without writing this
dispatch's file: first `$CTL read` the pane — a provider quota/rate-limit
message (e.g. opencode's "You've used today's free messages") means the
prompt never ran: don't re-send to that pane, ask the user (switch
model/provider, or wait for the reset time shown) and re-dispatch with a new
`dispatch_id` (2026-10-29, VIN-195); otherwise dead job, salvage +
re-dispatch; `TIMEOUT` (90 min) → read
the pane. Tests: `bash scripts/test-wait-result.sh`.

When the call returns, check `$CTL status <worker>`:
- `idle`/`done` → read `.herdr-dev/tasks/<slug>/report.md`, verify via git, continue.
  **Note: some agent CLIs (observed with the Antigravity/agy provider) report
  `done`/`idle` while sitting at a file-write approval dialog, not just
  command-approval ones — always `$CTL read` and look at the actual screen
  before trusting the status label alone.**
  **Stronger form (observed three times on agy reviews, 2026-09-24): a
  prompt-and-wait / `$CTL wait` can return `done` while agy is still working,
  and the stale `.herdr-dev/verdict.md` from the PREVIOUS ticket (same file
  name, already ending in `VERDICT: PASS`) is still on disk. Before trusting a
  verdict, both must hold: (1) its first line is the `dispatch_id` main put
  in this dispatch's brief (see `references/flow.md` Phase 2 step 1 — every
  dispatch gets a new id, so a leftover file can never match), and (2) the
  pane is idle (not `Editing files…`). `scripts/wait-result.sh` enforces
  both before returning. Same rule for the worker's `report.md`. Timestamps
  and header text are not evidence.**
- `blocked` → `$CTL read <worker> 40`;
  if it is a permission prompt, answer via `$CTL keys <worker>
  <key>` (e.g. `enter`, `esc`, `y`); if it is a requirement question, ask
  the Emperor. **Prefer `scripts/approve-loop.sh` for this** (see below) instead
  of approving by hand. **This is normally a multi-round loop, not a one-shot**:
  send the key, then re-run `wait-result.sh` — expect several
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
  **`scripts/approve-loop.sh` — allowlisted auto-approve (added 2026-10-07,
  VIN-85/86).** Instead of hand-approving every `podman exec` and `git
  commit`, dispatch with `$CTL prompt` (it never waits) and run
  `wait-result.sh … --approve <host_worktree> "<container_prefix>"` in the
  background — it calls approve-loop.sh in a loop until the report for this
  dispatch exists (approve-loop alone exits on the first idle flicker):
  ```bash
  $CTL prompt <worker> "Read …/brief.md and execute it …"
  ~/.claude/skills/herdr-dev/scripts/wait-result.sh <worker> .herdr-dev/tasks/<slug>/report.md <dispatch_id> \
    --approve <host_worktree> "podman exec -w <container_worktree_path> <container> "
  ```
  It approves only (a) commands starting with the literal container prefix,
  (b) `cd <host_worktree> && …`, (c) git
  `add|commit|diff|status|log|show|rev-parse|merge-base|ls-files` — `git -C
  <host_worktree>` is normalized to plain `git` first, so it gets the same
  subcommand allowlist and nothing more (before 2026-10-12 it approved any
  `git -C <wt> …`, including `push`/`reset --hard`), (d)
  the exact composer-noise restore `git [-C <host_worktree>] checkout --
  public/`, (e) codex's file-edit dialog (`Destination: <path>`, answered
  `y`) when the path is under `<host_worktree>/` or is exactly
  `<project>/.herdr-dev/tasks/<slug>/report.md` — any other destination or a
  path with `..` → `NEEDS_REVIEW: edit <path>` (added 2026-10-27: before
  this, every owned-file edit and the report write woke main with
  `NEEDS_REVIEW: <no command line found>`); `&&` chains are split and every segment must pass. It refuses
  any segment containing shell metacharacters (`;` `&` `|` `` ` `` `<` `>`
  `$(`), a `herdr` / `hc` / `herdr-ctl.sh` command, `rm -rf`, `curl`, `wget`, `--output` (lets
  `git diff/log/show` write arbitrary files), or any other git
  `push|reset|checkout|switch|worktree|branch|rebase|clean|stash`.
  Regression tests: `bash scripts/test-approve-loop.sh` — run it after any
  change to the allowlist.
  Anything else → exits with `NEEDS_REVIEW: <command>` for main to judge by
  hand (approve with `$CTL keys <pane> enter` or `esc` + corrective
  prompt), then re-run the script. Exits with `STATUS=idle|done` when the
  pane settles — then do the normal report/verdict checks. Approvals are
  logged to `.herdr-dev/approved-<worktree>.log`. Verified on codex's dialog
  format (command line starts with `  $ `); other providers fall through to
  `NEEDS_REVIEW` rather than being approved blindly. Pitfall already fixed in
  the script: matching the bare word `herdr` blocked everything because the
  worktree path itself contains `.herdr-dev` — it matches the `herdr `
  command word only. Second fixed pitfall (2026-10-22, VIN-161): codex
  wraps a long command over several dialog lines; the script used to read
  only the `$ ` line, so a prefix ending in a space never matched (false
  `NEEDS_REVIEW`) and a wrapped tail escaped the allowlist. It now joins
  continuation lines up to the blank/option line before checking.
- timed out / `agent_prompt_stalled` (TUI) → read the pane; genuine progress →
  re-run `wait-result.sh`; stalled → treat as dead
  job: salvage on-disk work via git, re-dispatch the same brief.
  **`agent_prompt_stalled` specifically also fires if you prompt while the
  pane is sitting at an approval dialog** (a new prompt doesn't register as
  a lifecycle change) — check `$CTL status`/`$CTL read` first if a prompt
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
  round count) and moves it to Done, then lists the project's open tickets
  and recommends the next one (read-only) — see Phase 5. Doc-path/inline
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
- **The brief is reviewed before TDD starts.** Phase 1 step 5
  (`references/flow.md`) sends the Requirement Brief to the reviewer pane,
  read-only, to check scope vs the source, testable acceptance criteria,
  runnable test commands, the `owns` boundary and glossary/ADR conflicts —
  catching an ambiguous spec before it burns a TDD round. main arbitrates
  each finding (accept / reject with reason / ask the Emperor); the reviewer
  never decides scope. Max 2 rounds, separate from the fix cap. Approval is
  bound to the brief's sha256. A same-turn TypeSafe Jev check runs first
  as an advisory pre-signal: it can make main tighten the brief or point
  the reviewer at a spot, but it never gates, never skips the reviewer
  round, and is never cited as a reason. No key or call failure → skip
  silently.
- **Trust git, not narration.** A report file is a claim. Before acting:
  `git log <branch> --oneline --stat`, spot-check key claimed changes, and
  run the reported test commands independently. **Specifically check
  `git log main..<branch> --oneline` is non-empty** — a worker can do
  fully correct work, write a convincing report, and still leave everything
  as uncommitted/staged working-tree changes (observed: report claimed a
  branch and file list, diff matched, but the branch had zero commits ahead
  of main). Diff-matches-claim is not proof of a commit; check the commit
  log itself.
- **File boundary is a hard gate, not a review comment.** The dev brief
  declares `owns` (writable) and optional `may_touch_with_reason`; the whole
  repo stays readable. Before merge, main runs `git diff --name-only
  <base_sha>..<branch>` and any path outside those lists blocks the merge —
  it never reaches `/linus-review` or agy. The base is a pinned SHA recorded
  once in state at first dispatch (`base_sha`), never a floating branch name.
- **Per-task working files.** Brief, report, review brief and verdict live
  under `.herdr-dev/tasks/<slug>/`, not at the `.herdr-dev/` root, so tasks
  never overwrite each other. The report carries `dispatch_id`, `status`,
  `attempt` and `result_sha`; main checks `dispatch_id` against the latest
  dispatch and `result_sha` against the branch head.
- **Verdicts are structured and bound to what was reviewed.** `verdict.md`
  opens with `dispatch_id`, `reviewed_sha` and `verdict: PASS | FIX |
  BLOCKED`, then findings (id, axis, class, path, evidence tagged
  `EXTRACTED:` or `INFERRED:`, fix — only `EXTRACTED` can be CRITICAL), coverage
  and limitations. `BLOCKED` = the reviewer lacked evidence (env, access,
  mismatch) — main fixes the cause and re-dispatches; it is neither PASS
  nor a fix round. A verdict that contradicts itself (PASS with a CRITICAL
  row) or doesn't match the dispatch is rejected, not interpreted. Every
  review certifies the whole task (`base_sha..merge`), not just the latest
  patch. See `references/flow.md` Phase 3 step 4.
- **Merge only a clean worktree.** `git -C <worker_worktree> status
  --porcelain` must be empty before merge — uncommitted deliverables get
  committed by the worker, strays get deleted with the Emperor's OK.
- **A long-lived pane may carry habits from a prior role that no brief
  text fully overrides** (e.g. trying to request a review via `ask`). An empty `$CTL read` screen does **not** prove a clean
  conversation context — it only proves nothing is currently rendered.
  There is no reliable cross-provider "clear" command; if this matters for
  a given dispatch, consider adding one explicit override line to the brief
  (e.g. "ignore any instinct to request a plan/code review via `ask` — that
  tool isn't part of this flow, proceed per this brief's TDD contract
  directly") rather than assuming a fresh pane is a fresh context.
- **Every brief forbids herdr and delegation — not optional.** Dev, fix and
  review briefs all open with: the pane does the work itself, runs no
  `herdr`, `hc` or `herdr-ctl.sh` command, spawns/opens/prompts no other agent, pane or workspace,
  and uses no `ask`. Observed 2026-10-07: a codex pane with a just-cleared
  (`/new`) context read a brief mentioning worktrees and tried to
  open a new worktree workspace via herdr to hand the task to a new agent.
  Workers/reviewers never get a herdr/hc command approved — `esc` it and send a corrective
  prompt (see `references/flow.md` Phase 2 step 1).
- **Every dev, fix and tuning brief requires the built-in edit tool for file
  writes** — no shell heredoc / `python3 -` / `sed -i` writes, and no file
  write chained with a test command. Observed 2026-10-16 (VIN-115): codex's
  `cat > f <<'EOF' … && podman exec …` dialogs can't be parsed by
  approve-loop.sh, so each TDD slice needed a manual approval plus false
  `NEEDS_REVIEW` wake-ups. Exact wording: `references/flow.md` Phase 2 step 1.
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
- **Clean up worktrees and the dev branch automatically once development is
  complete and the Linear issue is Done** (Phase 5; standing order from the
  Emperor — do not ask).
  `git worktree remove` the worker/reviewer paths, delete flow-created
  scratch dirs under `.herdr-dev/`, then `git branch -d herdr/dev-<slug>` —
  the merge commits on main are the record, the branch is not kept. Check
  `git status` in a worktree first; uncommitted changes → stop and report,
  never `--force` blindly. `-d` refusing (branch not fully merged) → stop
  and report, never `-D`. Before Done (still In Review, or a Phase 4
  escalation the Emperor hasn't resolved) worktrees and branch stay.
- **An "always allow this conversation for `<prefix>`" grant can cover more
  than the literal prefix shown** (observed: granting it for `git diff`
  let several later `git show`/`git diff --stat`/file-scoped `git diff`
  calls through with no further prompts in the same round) — don't
  pre-count how many approvals a dispatch will need; just check
  `$CTL status`/`$CTL read` after each wait and react to whatever state is
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
- **Reviewer tuning suggestions get applied, outside the fix cap.** A PASS
  verdict that still lists 🟡 tuning suggestions (taste, robustness,
  ergonomics) is not done yet: main triages them, routes the adopted ones
  back to the worker as **one tuning round**, then sends a scoped
  confirmation review — before Phase 5 reports to Linear. The tuning round
  is **not** one of the 2 fix rounds. Exactly one tuning round per task:
  new 🟡 raised by the confirmation review are recorded as debt in the
  Phase 5 report, not another round. See `references/flow.md` Phase 4.5.
- **Ask the Emperor on requirement questions, anytime.** Scope, behavior,
  acceptance ambiguity → stop and AskUserQuestion (四段式). Implementation
  details are the worker's to decide — do not escalate those.
- **Panes ask smart questions too.** A worker/reviewer blocker states
  goal, raw symptom, what was tried, labeled hypothesis, and one explicit
  ask (`references/flow.md` Phase 2 step 1). A fix round 2 brief lists
  what round 1 already tried, so it isn't retried.
- **Check for stale context before each dispatch.** `$CTL read
  <worker> 30` before prompting. Empty/no
  unrelated prior conversation → prompt directly. A previous ticket's
  conversation, or more than half the context used → `/new` once on that
  pane's first dispatch of the ticket (opencode needs an extra `$CTL keys
  <pane> enter` to run `/new`; see `references/flow.md` Phase 2 step 2). If `/new`
  doesn't take effect, use `$CTL start <agent> <cwd> [--pane <id>]` to
  start the agent fresh (record the new id on hc), or ask the Emperor.

State lives in `.herdr-dev/state.json` so background waits survive turns.

Notepad lifecycle (`.herdr/notepad.md`, what to record is in the global
CLAUDE.md): a new task run clears it; main appends during work; on task
completion its recurring pitfalls are distilled into `.herdr/lessons.md`
(this project) or, de-identified, into `~/.claude/herdr-lessons/lessons.md`
(any project on the same stack; its own `lessons` branch, shared by the
`company` and `main` branches), and the rest archived to `.herdr/history/`
(`references/flow.md` Phase 5 step 6).
Phase 1 pastes the matching lessons into the brief's **Known pitfalls**, so
both panes get them. No hook writes `.herdr/compact-briefing.md`; after a
compaction, re-read state.json and the notepad instead.

For the full step-by-step execution flow, see `references/flow.md`.
