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

Optional flags, combinable with any of the above (not with `--resume`):

- `--worker=<agent>` — Herdr agent name for the Code Writer role (default `codex`).
- `--reviewer=<agent>` — Herdr agent name for the Code Reviewer role (default `agy`).

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
2. Parse `--worker=<agent>` / `--reviewer=<agent>` if given; default to
   `codex` / `agy`. If they name the same agent, stop and ask the user to
   pick two different agents — one CLI cannot both write and review the
   same change — END TURN.
3. `herdr agent list` → record the pane id whose agent matches the worker
   agent name, and the pane id whose agent matches the reviewer agent name.
   Missing pane for either role → tell the user which agent CLI to start in
   a Herdr pane, END TURN.
4. Detect version control: `git rev-parse --is-inside-work-tree` in the
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
5. **Jev spec-readiness pre-flight (advisory, optional, best-effort).**
   Before the question gate below, run a same-turn check on the Brief's
   Goal + Scope + Acceptance criteria text via Vercel AI Gateway — no pane,
   no dispatch, same pattern as the Phase 3 `/linus-review` self-check.
   Piloted and verified working 2026-09-23; not yet run in anger on a real
   flow, so treat early misses as signal to retune the prompt, not proof the
   step is wrong.
   - Write the request body to a file first (long/multi-line spec text in a
     shell `-d` string is quoting hell — same reasoning as the "long briefs
     go through files" rule in SKILL.md's Dispatch Pattern):
     ```bash
     cat > .herdr-dev/jev-preflight-request.json <<'EOF'
     {
       "model": "typesafe-ai/jev",
       "state": "<Goal + Scope + Acceptance criteria from the Brief, verbatim>",
       "questions": {
         "is_spec_actionable": {"type": "boolean", "instructions": "Is this requirement specific and actionable enough for a developer to implement without further clarification?"},
         "has_unambiguous_acceptance_criteria": {"type": "boolean", "instructions": "Does this requirement include clear, checkable acceptance criteria?"}
       }
     }
     EOF
     ```
   - Call it, reading `AI_GATEWAY_API_KEY` from the environment, else from
     the global `~/.config/herdr-dev/.env` (works in every project; lives
     outside any repo), with an optional per-project `.herdr-dev/.env`
     overriding it — **never** write the key's value into a brief, report,
     note, or anything that leaves this shell:
     ```bash
     set -a; source ~/.config/herdr-dev/.env 2>/dev/null; source .herdr-dev/.env 2>/dev/null; set +a
     ```
     ```bash
     curl -sS --max-time 10 https://ai-gateway.vercel.sh/v1/evaluate \
       -H "Authorization: Bearer $AI_GATEWAY_API_KEY" \
       -H "Content-Type: application/json" \
       -d @.herdr-dev/jev-preflight-request.json
     ```
   - **No key set, call errors, times out, or returns non-200 → skip this
     step silently and proceed to step 6 as if it didn't exist.** Never
     block or delay dispatch because a third-party service is unreachable —
     this mirrors the graceful-fallback rule already governing this feature.
   - Read `answers.<question>.probability` (0–1) from the response. **This
     endpoint does not populate a separate calibrated-confidence field** —
     `providerMetadata.typesafe.confidence` came back empty `{}` in testing
     (2026-09-23) despite TypeSafe's own docs describing a confidence score
     distinct from probability. Use distance from 0.5 as the uncertainty
     proxy instead: `abs(probability - 0.5) < 0.3` on either question →
     treat as uncertain.
   - **This is advisory input to step 6's judgment, never a standalone
     gate.** Uncertain or low-probability result → weigh it alongside main's
     own read of the requirement when deciding whether to raise a question;
     do not auto-block dispatch on this signal alone, and do not cite "Jev
     said X" to the Emperor as the reason — name the actual ambiguity in the
     requirement text. Confident/high-probability on both → no action,
     proceed silently (don't clutter the brief presentation with a
     pre-flight pass notice).
6. **Gate on questions.** Open questions that change *what gets built* →
   AskUserQuestion (四段式) now — fold in step 5's signal if it fired.
   Implementation details → worker decides.
7. Present the brief to the Emperor (繁中), proceed. No separate "approve
   the brief" round-trip unless step 6 raised a real question.

State: `{ "step": "requirement_confirmed", "worker_agent": "codex", "worker": "w1:p2", "reviewer_agent": "agy", "reviewer": "w1:p3" }`

---

## Phase 2: Dispatch Development → worker pane

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
4. Reply one short line (`<worker agent> 開發中…`) and **END TURN**. The
   background call re-enters this session when it settles (idle/done/blocked)
   or times out.

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
   - **CRITICAL fatal issue found** → do NOT proceed to the reviewer. Handle exactly
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
     — those are exactly the kind of thing to hand the reviewer as context,
     not a gate.
4. Write the **review brief** (English) to `.herdr-dev/review-brief.md`:
   Requirement Brief + acceptance criteria + main @ merge commit + the
   requirement's **Linear issue id** (or doc path, for pre-existing local
   specs) so the reviewer pulls the source itself instead of relying on a
   copied summary + the worker's TDD evidence + **main's own
   `/linus-review` taste score and improvement notes from step 3** (so the
   reviewer isn't rediscovering the same things and can spend its attention
   on spec/TDD compliance — explicitly invite it to confirm, dispute, or add
   to main's taste read rather than silently ignoring it). **Restate the
   same execution-environment constraints the dev brief got** (e.g. this
   project's `podman exec -w /var/www/html/<project> php-fpm <cmd>`
   requirement for PHP/artisan — see project CLAUDE.md) — the reviewer
   independently re-runs tests too and will otherwise try a bare host
   command that fails by design. **Priority review focus — call these out
   explicitly even if the axes below don't surface them.**

   First, **detect which stacks this diff actually touches**: `git diff
   --name-only <parent-of-merge>..<merge-commit>` and bucket the paths by
   extension/location using the table below. Then write into the brief
   **only the stack-specific tells for buckets present in this diff** —
   drop every row that doesn't match, so agy gets a short, targeted
   checklist instead of a multi-stack dump it has to self-filter. If a
   touched file's extension isn't in the table, still include the three
   language-neutral categories and ask agy to apply its own knowledge of
   that stack's equivalent patterns.

   | Bucket | Path match | Security tells | DB/perf tells |
   |---|---|---|---|
   | PHP/Laravel | `**/*.php` | raw `DB::raw`/`whereRaw` string interpolation instead of bindings or the query builder; mass-assignment vs fillable/guarded; `unserialize()` or dynamic `eval`/`include` on attacker-reachable data | Eloquent N+1 (missing `with()`), `->get()` without pagination on a possibly-large table |
   | JS/TS/frontend | `**/*.{js,ts,jsx,tsx}` | `dangerouslySetInnerHTML`/`innerHTML` from unescaped input; URLs/HTML built via string concatenation; unhandled promise rejection on a path with side effects | client-side loops re-fetching per item instead of batching |
   | SQL/mapper | `**/*.sql`, `**/*mapper*.xml` | string-concatenated SQL instead of bound parameters, especially dynamic `LIKE`/`IN` clauses | missing WHERE (full-table-scan risk), missing LIMIT/pagination on a large table |
   | Go | `**/*.go` | SQL/shell/paths built from untrusted input without parameterization/escaping; `math/rand` used for tokens/session ids instead of `crypto/rand` | goroutine/resource leak on an early-return path, unreleased `sql.Rows`/lock |

   All buckets share these **language-neutral categories** regardless of
   which rows apply:
   - **(1) Security** — server-side authz enforced (not just hidden in a
     client/template); untrusted input reaching a query, shell, template,
     or dynamic-eval sink without parameterization/escaping/allowlisting;
     secrets or tokens logged or returned in error output; weak/predictable
     randomness for tokens or session ids.
   - **(2) Runtime execution performance** — hot-path algorithmic
     complexity, unbounded loops/recursion, blocking I/O on a request
     path without timeout, resources (files/sockets/locks/goroutines/
     promises) not released or awaited on every reachable path.
   - **(3) Database query performance** — N+1 queries (missing eager
     load), full-table-scan risk (query with no usable WHERE/index),
     unbounded result sets missing pagination/LIMIT, repeated identical
     subqueries that should be hoisted, transactions left open across an
     early-return/exception path (missing rollback).
   Require **evidence, not suspicion**, for every finding in these three
   areas: name the reachable input/caller and the concrete consequence —
   and check whether the project's own static analysis for the touched
   bucket (e.g. Larastan/PHPStan for PHP, ESLint/tsc for TS, staticcheck/
   go vet for Go) would already catch it; if so, don't re-report it
   unless the diff shows a concrete consequence that tooling doesn't
   express. When the full execution context can't be confirmed, favor
   **not reporting** over a false positive — a security/perf finding with
   no demonstrated exploit or reachable path is 🟡 at most, never
   CRITICAL. Only an exploitable,
   evidenced security finding is a FIX-blocking CRITICAL; unevidenced
   suspicions belong in the findings list as 🟡, not as gates.
   Require an explicit verdict per axis, findings ranked by severity,
   written to `.herdr-dev/verdict.md`:
   - **(a) code quality** — taste, correctness, maintainability (Linus
     standards: data structures, edge cases, no needless complexity).
   - **(b) spec compliance** — diff vs requirement document item by item;
     unimplemented / partial / out-of-scope-added behavior is a FIX finding.
   - **(c) TDD compliance** — tests cover public behavior at declared
     seams; credible RED/GREEN per slice; full suite passes.
   - **(d) security** — the priority-focus items above; treat this axis as
     a hard gate, not advisory, but gate only on evidenced findings.
   - **(e) performance** — execution and database query performance per
     the priority-focus items above.
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
8. Reply one short line (`<reviewer agent> 審查中…`) and **END TURN**.

State: `{ "step": "review_dispatched", "round": <n>, "merge_commit": "<sha>" }`

---

## Phase 4: Handle the Verdict

On the reviewer wait firing (handle blocked/stalled as in Phase 3 preamble),
read `.herdr-dev/verdict.md`:

- **PASS on all axes** → Phase 5.
- **FIX** → route findings back to the worker pane:
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
4. **If `git_repo`**: remove the pane worktrees **as soon as development is
   complete and the Linear issue is Done** (Emperor's standing order,
   2026-09-24 — no need to ask again). Trigger = step 3's `save_issue`
   → Done succeeded (doc-path/inline requirement with no issue: trigger =
   final PASS). Run `git status --short` in each first; if a worktree has
   uncommitted changes, stop and report instead of forcing. Otherwise
   `git worktree remove .herdr-dev/worktrees/worker-<slug>` and
   `.../reviewer-<slug>`, then `git worktree prune`. Also delete scratch
   dirs this flow created under `.herdr-dev/` (e.g. `cleancheck`). The
   branch `herdr/dev-<slug>` itself stays. If the Linear issue is left
   In Review (e.g. waiting for push approval), worktrees stay until it
   reaches Done. An escalation to the Emperor (Phase 4 round cap) is not a
   Phase 5 completion — leave its worktrees in place until the Emperor
   decides the outcome.
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
