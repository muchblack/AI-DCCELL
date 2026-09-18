# Herdr-Dev Execution Flow

All inter-AI briefs are in **English** (token economy); all user-facing
output is **Traditional Chinese** in Grand Council minister tone.

## Input

`$ARGUMENTS` is one of:

- A **Linear issue id/identifier** (e.g. `TWC-42`) — primary case; `get_issue`
  fetches the spec `/to-spec` published.
- A **requirement document path** (e.g. `docs/spec.md`) — pre-existing local specs.
- An **inline requirement description** — freeform text (still gated by Step 0).
- `--resume` — continue from a pending background wait.

State: `.herdr-dev/state.json`. Working files live under `.herdr-dev/`
(add it to `.gitignore` if not already).

---

## Step 0: Requirement Gate

See SKILL.md. Linear id → `get_issue`, proceed. Doc path → verify, proceed.
Neither → AskUserQuestion; if none exists, PAUSE, point to `/grill-with-docs`
(+ `/to-spec`), END TURN.

---

## Phase 0: Resolve Panes

1. `$ARGUMENTS == --resume` → go to **Resume Handling**.
2. `herdr agent list` → record codex pane id (worker) and agy pane id
   (reviewer) in state. Missing pane → tell the user which agent CLI to
   start in a Herdr pane, END TURN.
3. Detect version control: `git rev-parse --is-inside-work-tree` in the
   project root. Record `"git_repo": true` or `false` in state.
   - `true` → this flow uses **per-pane git worktrees**: worker gets
     `.herdr-dev/worktrees/worker-<slug>` (Phase 2), reviewer gets
     `.herdr-dev/worktrees/reviewer-<slug>` (Phase 3). This is what avoids
     the shared-index race noted in SKILL.md's Core Principles.
   - `false` → legacy shared-working-tree flow: all panes operate directly
     in the project directory, sequentially (only one writes at a time).
     Skip every worktree step below.

---

## Phase 1: main — Confirm the Requirement

main (self) does this directly; no worker involved yet.

1. **Read the requirement** fully (Linear issue via `get_issue`, or the local
   doc). Large/multi-phase → scope to what the Emperor asked; if unstated,
   infer the smallest coherent unit and state the assumption.
2. **Analyze the project**: tech stack, existing patterns, key files.
3. **Task touches the DB** → run `/db` to confirm schema, fold into brief.
4. **Produce a Requirement Brief** (the contract handed to the worker):
   - **Goal** — one or two sentences.
   - **Scope** — in / out, explicit.
   - **Affected layers/files** — best-effort map.
   - **Constraints** — stack versions, env (podman exec for PHP, host npm),
     branch `herdr/dev-<slug>`, security-sensitive paths.
   - **Acceptance criteria** — concrete, checkable bullets. The reviewer
     judges against these.
   - **Test seams** — public behavior boundaries; prefer existing seams and
     the highest practical integration boundary.
   - **Test commands** — smallest targeted command per slice + full-suite.
   - **TDD exception** — normally none; if granted, the specific reason.
   - **Assumptions / Open questions.**
5. **Gate on questions.** Open questions that change *what gets built* →
   AskUserQuestion (四段式) now. Implementation details → worker decides.
6. Present the brief to the Emperor (繁中), proceed. No separate "approve
   the brief" round-trip unless step 5 raised a real question.

State: `{ "step": "requirement_confirmed", "worker": "w1:p2", "reviewer": "w1:p3" }`

---

## Phase 2: Dispatch Development → codex pane

0. **If `git_repo`**: create the worker's worktree (skip if it already
   exists on disk — a fix round, or a resumed dispatch, reuses it):
   ```bash
   # first dispatch for this slug — branch doesn't exist yet
   git worktree add .herdr-dev/worktrees/worker-<slug> -b herdr/dev-<slug> main
   # re-dispatch onto an already-existing branch (e.g. after a salvage) — no -b
   git worktree add .herdr-dev/worktrees/worker-<slug> herdr/dev-<slug>
   ```
   Record the absolute worktree path in state
   (`worker_worktree: "<abs-path>"`). `.herdr-dev/` must be gitignored (see
   Input section) so the worktree itself isn't tracked by main's checkout.
   If the project's build/test commands run inside a container with a fixed
   bind-mount (see project CLAUDE.md), confirm the mount covers this path
   before dispatching — if it doesn't, flag it to the Emperor rather than
   silently falling back to the shared tree.
1. Write the **dev brief** (English) to `.herdr-dev/brief.md`: the
   Requirement Brief + this mandatory TDD contract:
   - **If `git_repo`**: state the worker's working directory is
     `<worker_worktree>` (absolute path) — a dedicated git worktree already
     checked out on `herdr/dev-<slug>`, created by main before this
     dispatch. The worker's job is to **verify** cwd/branch/base match this
     brief (`pwd`, `git status`, `git log -1`) and stop with a blocker in
     the report if they don't — never to run `git worktree add/switch`
     itself, and never to `cd` back to the main checkout or re-clone. All
     commands (including any container-wrapped ones per project CLAUDE.md)
     run against files under this path.
   - Work in vertical slices: one behavioral test, one minimal implementation.
   - **RED:** write the test first, run the targeted command, confirm it
     fails for the expected missing behavior (not setup/syntax errors).
   - **GREEN:** write only enough production code to pass, rerun the same
     command.
   - Repeat per slice; do not batch all tests before all implementation.
   - Test public behavior, not private methods.
   - Run the relevant full suite after the final GREEN.
   - Commit on branch `herdr/dev-<slug>`.
   - Write the final report to `.herdr-dev/report.md`: TDD evidence table
     (per slice: RED command + expected failure, GREEN command + result),
     final suite result, changed files, branch name.
   - If no test can express the behavior and no TDD exception was granted,
     stop and write the blocker to the report before touching production code.
2. **Check for stale context**: `herdr agent read <worker> --source
   recent-unwrapped --lines 30`. Empty/no unrelated prior conversation →
   proceed directly. If stale context is visible, no documented
   cross-provider clear exists — restart via `herdr agent start <name>
   --kind <kind> --pane <id>` on a plain shell, or ask the Emperor.
3. Dispatch + wait, atomic, run in background (can take a long time):
   ```bash
   herdr agent prompt <worker> "Read .herdr-dev/brief.md and execute it. Write your final report to .herdr-dev/report.md when done." --wait --timeout 1800000
   ```
4. Reply one short line (`codex 開發中…`) and **END TURN**. The background
   call re-enters this session when it settles (idle/done/blocked) or times out.

State: `{ "step": "dev_dispatched", "round": 0 }`

---

## Phase 3: Verify → Merge → Self-Review → Dispatch Review

On the wait firing, `herdr agent get <worker>`:

- `blocked` → `herdr agent read <worker> --source recent-unwrapped --lines
  40`. Permission prompt on a legitimate command → `herdr agent send-keys
  <worker> enter` (or the right key), then `herdr agent wait <worker>
  --timeout <ms>` again — expect several such cycles in a row, not just
  one. Permission prompt on a command that will fail for environment
  reasons (wrong host, missing wrapper) → `esc` to cancel, send a
  corrective prompt instead of approving. Requirement question →
  AskUserQuestion, then re-wait, END TURN.
- `working` (timeout) → read the pane. Progress → re-wait. Stalled → dead
  job: salvage on-disk work via git, re-dispatch the same brief (Phase 2
  steps 2–4).
- `idle`/`done` → continue, but first `agent read` to confirm it's actually
  finished and not just sitting at an unrendered approval dialog (some
  providers report idle/done even at a file-write confirmation prompt).

1. **Verify against git, not the report**:
   - `git log main..herdr/dev-<slug> --oneline` — **must be non-empty**. A
     worker can produce a fully correct diff, a convincing report, and
     still leave everything uncommitted (observed in practice: report
     claimed a branch + file list, `git diff` matched the claim, but the
     branch had zero commits ahead of main — the actual `git commit` step
     was skipped). If empty: the work is real but unfinished — send a short
     follow-up prompt asking the worker to `git add` the exact claimed
     files (nothing else) and `git commit`; do not restart from the full
     brief, and do not commit on the worker's behalf. Re-check `git log
     main..branch` after.
   - `git log herdr/dev-<slug> --oneline --stat` — commits exist, touch the
     expected files. Spot-check 2–3 key claimed changes in the diff.
   - Unless a TDD exception was recorded: require changed behavioral tests,
     credible RED evidence, GREEN evidence for the same command, and a
     passing full suite. **Run the reported targeted and full-suite commands
     independently.** Missing/invalid evidence → incomplete: do not merge,
     re-dispatch with the missing TDD requirement.
   - Empty branch / no report file → dead job: salvage, re-dispatch.
   - Report contains a **requirement-level blocker** → AskUserQuestion,
     then re-dispatch as needed.
   - **Repo hygiene**: `git status --porcelain` — flag untracked entries
     outside the claimed changes (0-byte files, stray-punctuation names are
     mis-pasted shell commands). Confirm deletion with the Emperor before
     merging; never let them ride in via `git add -A`.
2. **Merge before review**: from main's own checkout (the repo's primary
   working tree — not the worker's worktree), `git merge --no-ff
   herdr/dev-<slug>` into main branch. Record the merge commit — the review
   references main @ that commit. (Retry once on a transient `fatal: Unable
   to write index.` — see SKILL.md's shared-working-tree note; with
   per-pane worktrees this should no longer happen, so a repeat is worth
   investigating rather than just retrying blindly.)
3. **Self-review with `/linus-review`** on `git diff <parent-of-merge>..<merge-commit>`
   (main runs this itself, inline, same turn — no pane, no dispatch):
   - **CRITICAL fatal issue found** → do NOT proceed to agy. Handle exactly
     like a Phase 4 FIX: write a fix brief (the finding verbatim, expected
     regression test reproducing it RED-first, then GREEN); if `git_repo`,
     the worker's existing worktree is already on `herdr/dev-<slug>` which
     now sits behind main's merge commit — that's fine, the fix commits
     land on top of it, no rebase needed since the branch will be re-merged
     `--no-ff` again in the next Phase 3 pass; re-dispatch (Phase 2 steps
     2–4, minus the plan-review-override line if already sent once, and
     minus step 0 since the worktree already exists), END TURN.
     On the fix reply, return to **Phase 3 step 1** (re-verify → re-merge →
     re-run `/linus-review`). This consumes one of the 2 fix rounds — a
     self-caught issue is still a real round from the worker's side.
   - **No CRITICAL** (🟡/🟢 taste findings, or none) → keep the taste score
     and improvement notes, continue to step 4. Do not block on 🟡 findings
     — those are exactly the kind of thing to hand agy as context, not a
     gate.
4. Write the **review brief** (English) to `.herdr-dev/review-brief.md`:
   Requirement Brief + acceptance criteria + main @ merge commit + the
   requirement's **Linear issue id** (or doc path, for pre-existing local
   specs) so agy pulls the source itself instead of relying on a copied
   summary + the worker's TDD evidence + **main's own
   `/linus-review` taste score and improvement notes from step 3** (so agy
   isn't rediscovering the same things and can spend its attention on spec/
   TDD compliance — explicitly invite agy to confirm, dispute, or add to
   main's taste read rather than silently ignoring it). **Restate the
   same execution-environment constraints the dev brief got** (e.g. this
   project's `podman exec -w /var/www/html/<project> php-fpm <cmd>`
   requirement for PHP/artisan — see project CLAUDE.md) — the reviewer
   independently re-runs tests too and will otherwise try a bare host
   command that fails by design. Require an explicit verdict per axis,
   findings ranked by severity, written to `.herdr-dev/verdict.md`:
   - **(a) code quality** — taste, correctness, maintainability (Linus
     standards: data structures, edge cases, no needless complexity).
   - **(b) spec compliance** — diff vs requirement document item by item;
     unimplemented / partial / out-of-scope-added behavior is a FIX finding.
   - **(c) TDD compliance** — tests cover public behavior at declared
     seams; credible RED/GREEN per slice; full suite passes.
5. **If `git_repo`**: create/reuse the reviewer's worktree, checked out
   (detached — the reviewer doesn't commit) at the merge commit so review
   and any independent test runs don't touch main's own checkout:
   ```bash
   git worktree add --detach .herdr-dev/worktrees/reviewer-<slug> <merge-commit-sha>
   ```
   On a re-review round, remove and re-add at the new merge commit rather
   than reusing the old checkout (`git worktree remove --force
   .herdr-dev/worktrees/reviewer-<slug>` first — check `git status` in it;
   it's detached and reviewer-only, so it should never hold anything worth
   keeping). Record the path in state (`reviewer_worktree`). Same
   container-bind-mount caution as the worker worktree (Phase 2 step 0)
   applies here.
6. Include the reviewer's working directory (`<reviewer_worktree>` if
   `git_repo`, else the shared project root) in the review brief alongside
   the execution-environment constraints from step 4. Same boundary as the
   dev brief: the reviewer **verifies** cwd/commit match (`pwd`, `git log
   -1`) and blocks on mismatch — it never creates or switches worktrees
   itself; that already happened in step 5, run by main.
7. Clear + dispatch the reviewer + background wait (same pattern as
   Phase 2 steps 2–3, targeting `<reviewer>`, prompt pointing at
   `.herdr-dev/review-brief.md` → `.herdr-dev/verdict.md`).
8. Reply one short line (`agy 審查中…`) and **END TURN**.

State: `{ "step": "review_dispatched", "round": <n>, "merge_commit": "<sha>" }`

---

## Phase 4: Handle the Verdict

On the reviewer wait firing (handle blocked/stalled as in Phase 3 preamble),
read `.herdr-dev/verdict.md`:

- **PASS on all axes** → Phase 5.
- **FIX** → route findings back to the codex pane:
  1. Write the fix brief to `.herdr-dev/brief.md`: findings verbatim
     (ranked), unmet acceptance criteria, and the contract to add a
     regression test reproducing each behavioral finding (**RED**) before
     fixing it (**GREEN**), re-commit on the same branch, same report format.
  2. Clear + dispatch + background wait (Phase 2 steps 2–4). END TURN.
  3. On the fix reply → **return to Phase 3** (verify → merge → re-review).
  - **Round cap**: after **2 fix rounds** still failing → stop, escalate to
    the Emperor (AskUserQuestion): sticking point + options
    (accept-with-debt / change approach / change scope).
  - A finding that is a **requirement disagreement** → the Emperor's call;
    don't let worker and reviewer ping-pong.

State per transition: `{ "step": "fix_dispatched", "round": <n> }`

---

## Phase 5: Report

1. Summarize for the Emperor (繁中): what was built, RED/GREEN and final
   test results, review outcome, rounds, branch, deferred items /
   `ponytail:` debt.
2. Merges already happened per round. Extra commit/push only when asked.
   Commit messages in Traditional Chinese with the current model's standard
   `Co-Authored-By:` trailer.
3. **If the requirement was a Linear issue id** (Step 0 case 1) **and the
   final verdict is PASS**: report back on that issue before declaring
   done. A doc-path or inline-description requirement has no issue to
   report to — skip this step silently, don't invent one.
   - `save_comment` (param is `issueId`, not `issue` — mismatched param
     name fails validation) with a Traditional Chinese status comment:
     processing outcome (PASS), the final merge commit sha(s) — one per
     fix round if more than one — worker commit sha(s), branch name, round
     count, and test result summary.
   - `save_issue` with `id: "<issue-id>"` and `state` moved to the team's
     "Done" state (or equivalent completed-type state — check
     `list_issue_statuses` for the team if unsure of the exact name).
   - A flow that never reached PASS (escalated to the Emperor after the
     2-round fix cap) has nothing to report here — that's a Phase 4
     escalation, not a Phase 5 completion.
4. **If `git_repo`**: remove the pane worktrees now that the branch's fate
   is settled — `git worktree remove .herdr-dev/worktrees/worker-<slug>`
   and `.../reviewer-<slug>` (check `git status` in each first; `--force`
   only after confirming there's nothing worth keeping). The branch
   `herdr/dev-<slug>` itself stays. An escalation to the Emperor (Phase 4
   round cap) is not a Phase 5 completion — leave its worktrees in place
   until the Emperor decides the outcome.
5. State: `{ "step": "done" }`. Clean up `.herdr-dev/*.md` working files.

---

## Resume Handling (`--resume`)

1. Read `.herdr-dev/state.json`. Absent → "No active /herdr-dev flow found."
2. Branch on `step`:
   - `dev_dispatched` / `fix_dispatched` → `herdr agent get <worker>`:
     `done` → Phase 3; `working` → background wait again, END TURN;
     `blocked` → Phase 3 preamble.
   - `review_dispatched` → same check on `<reviewer>`; `done` → Phase 4.
   - `requirement_confirmed` → re-dispatch Phase 2.
   - `done` → nothing pending; report last outcome.
3. Pane ids in state may be stale after a Herdr restart — re-run
   `herdr agent list` and re-resolve if `agent get` errors.
4. **If `git_repo`**: `worker_worktree`/`reviewer_worktree` paths in state
   should still be valid — worktrees survive process/session restarts.
   Confirm with `git worktree list`; if a recorded path is missing from
   that output (manually deleted, or `.herdr-dev/` was wiped), re-add it
   from Phase 2 step 0 / Phase 3 step 5 rather than assuming it's still
   there.
