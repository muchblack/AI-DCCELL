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
   - **`owns`** — paths/globs the worker may change, including test files;
     optional **`may_touch_with_reason`**. Declared here so the brief
     review checks it; Phase 2 copies it verbatim (see Phase 2 step 1).
   - **Constraints** — stack versions, env (podman exec for PHP, host npm),
     branch `herdr/dev-<slug>`, security-sensitive paths.
   - **Acceptance criteria** — concrete, checkable bullets. The reviewer
     judges against these.
   - **Test seams** — public behavior boundaries; prefer existing seams and
     the highest practical integration boundary.
   - **Test commands** — smallest targeted command per slice + full-suite.
   - **Task-specific checks** — pick only the sections of
     `references/task-checks.md` the requirement or touched code triggers,
     and paste them here. This brief travels whole into the dev brief
     (Phase 2) and the review brief (Phase 3), so Worker and Reviewer lines
     reach their pane with no extra step. They add no scope or ownership.
   - **TDD exception** — normally none; if granted, the specific reason.
   - **Known pitfalls** — read the project's `.herdr/lessons.md` (if it
     exists) and the cross-project `~/.claude/herdr-lessons/lessons.md`, both
     written by Phase 5 step 6. Refresh the cross-project file first:
     `git -C ~/.claude/herdr-lessons pull --ff-only -q`. Directory missing →
     create it once by running `bootstrap.sh` step 1e's commands (or the
     whole idempotent `bash ~/agentSkill/bootstrap.sh`). Any of this fails → use what is
     on disk or skip it; never block the brief on it. Paste only the lines that match: project
     lines by layer, file or command; cross-project lines by their stack tags
     against the stack found in step 2. Verbatim, project line first when
     two say the same thing; none match → `none`. Like
     task-specific checks, this travels whole into the dev and review briefs,
     so both panes see the trap before they step in it. Pitfalls add no
     scope or ownership.
   - **Assumptions / Open questions.**
5. **Brief review by the reviewer pane — before any TDD.** An ambiguous
   brief otherwise only surfaces after a full TDD round plus code review.
   The reviewer pane is idle at this point; use it.
   - **Jev pre-signal (advisory, best-effort, first round only).** Before
     saving the brief, run the `/linus-analyze` Step 1.2 request (same two
     Nouls) with `state.requirement` = the Brief's Goal + Scope +
     Acceptance criteria, verbatim, via
     `bash ~/.claude/skills/scripts/jev.sh <request.json>`. Same data note:
     skip it if the brief carries secrets or customer data. Non-zero exit →
     skip silently. Flagged (`noul < 0.5` or `abs(noul - 0.5) < 0.3`) →
     main re-reads that part; if main agrees, tighten the brief now,
     otherwise name the specific spot in `brief-review.md` as one of main's
     attention points. Never cite Jev to the user or the reviewer, and
     never let it replace or skip the reviewer round. Record the values
     in state (`jev_preflight`).
   - `mkdir -p .herdr-dev/tasks/<slug>`; save the Requirement Brief to `.herdr-dev/tasks/<slug>/requirement.md`
     and record `brief_sha256` (`sha256sum`) in state.
   - Write `.herdr-dev/tasks/<slug>/brief-review.md` (English): new
     `dispatch_id` on line 1 (Phase 2 step 1 rule), the same no-herdr /
     no-delegation line as every brief, **read-only — edit nothing but the
     verdict file**, the source (Linear issue id or doc path — the reviewer
     pulls it itself), the project root to read, and `requirement.md`.
     Ask it to check, against the source and the code:
     - every source requirement is in scope or explicitly out of scope —
       nothing silently dropped or added;
     - every acceptance criterion is observable and testable at a named seam;
     - test commands exist and fit the project's execution environment
       (restate the container wrapper, as for the review brief);
     - `owns` covers what the change must touch, and nothing it shouldn't;
     - no conflict with `CONTEXT.md` terms or `docs/adr/` decisions;
     - edge cases the source implies but the brief misses.
   - Output `.herdr-dev/tasks/<slug>/brief-verdict.md`, same shape as the
     code verdict (Phase 3 step 4) with `brief_sha256: <sha>` in place of
     `reviewed_sha` and `verdict: APPROVED | REVISE | BLOCKED`. Findings
     use the same `EXTRACTED:` / `INFERRED:` evidence tags.
   - Dispatch + background wait like Phase 2 step 3 (prompt points at
     `brief-review.md` → `brief-verdict.md`), reply `<reviewer agent> 審需求中…`,
     END TURN. Accept the verdict only if `dispatch_id` and `brief_sha256`
     match.
   - **main arbitrates every finding** — accept (edit the brief), reject
     (one-line reason), or, if it changes *what gets built*, take it to
     step 6 as a question. The reviewer advises; main and the Emperor decide.
     Record dispositions in state (`brief_findings`).
   - **One rule decides whether to review again:** the brief changed
     beyond pure wording (any change to what it commits to — scope,
     acceptance criteria, test commands, `owns`, `may_touch_with_reason`,
     constraints) since the last reviewed sha (from accepted findings here, or from a step-6 answer)
     **and** fewer than 2 brief-review rounds were used → re-dispatch the
     revised brief (new sha, new id) with the dispositions, so rejected
     points aren't relitigated without new evidence. Otherwise go on to
     step 6 / step 7 — this covers APPROVED, a REVISE whose findings were
     all rejected or turned into questions, and the round cap. Never
     re-send an unchanged brief to fish for APPROVED, and never relabel a
     REVISE as APPROVED. The 2-round cap is separate from the fix cap.
     **BLOCKED** → fix the stated cause, re-dispatch; not a round.
   - Requirement questions always go through step 6, cap or not.
   - Approval is bound to `brief_sha256`. In step 7 main states the brief's
     review status: `approved` (current sha has an APPROVED verdict),
     `reviewed, findings rejected` (with reasons), or `changed after last
     review` (listing what changed, when the cap stopped a re-review).
   - The later code review is a separate dispatch with its own
     self-contained brief; this round does not stand in for it.
6. **Gate on questions.** Open questions that change *what gets built* —
   main's own, plus brief-review findings routed here in step 5 →
   AskUserQuestion (四段式), one decision per question.
   Implementation details → worker decides.
7. Present the brief to the Emperor (繁中) with its review status from
   step 5, proceed. No separate "approve the brief" round-trip unless
   step 6 raised a real question.

State during step 5: `{ "step": "brief_review_dispatched", "brief_sha256": "<sha>", "brief_review_round": <n>, "dispatch_seq": <k>, "dispatch_id": "<slug>-<k>", "jev_preflight": {"is_spec_actionable": <p>, "has_unambiguous_acceptance_criteria": <p>} | "skipped", "brief_findings": [{"id": "F1", "disposition": "accepted|rejected|asked", "reason": "..."}] }`

State: `{ "step": "requirement_confirmed", "worker_agent": "codex", "worker": "w1:p2", "reviewer_agent": "agy", "reviewer": "w1:p3" }`

---

## Phase 2: Dispatch Development → worker pane

0. **If `git_repo`**: create the worker's worktree (skip if it already
   exists on disk — a fix round, or a resumed dispatch, reuses it):
   ```bash
   # first dispatch for this slug — branch doesn't exist yet.
   # Pin the base to an exact SHA, never a floating branch name.
   BASE_SHA=$(git rev-parse main)
   git worktree add .herdr-dev/worktrees/worker-<slug> -b herdr/dev-<slug> "$BASE_SHA"
   # re-dispatch onto an already-existing branch (e.g. after a salvage) — no -b;
   # keep the base_sha already recorded in state, do not recompute it
   git worktree add .herdr-dev/worktrees/worker-<slug> herdr/dev-<slug>
   ```
   Record the absolute worktree path and the pinned base in state
   (`worker_worktree: "<abs-path>"`, `base_sha: "<sha>"`). The base is
   written once on first dispatch and never changes across fix rounds —
   the boundary check in Phase 3 diffs against it.
   `.herdr-dev/` must be gitignored (see
   Input section) so the worktree itself isn't tracked by main's checkout.
   If the project's build/test commands run inside a container with a fixed
   bind-mount (see project CLAUDE.md), confirm the mount covers this path
   before dispatching — if it doesn't, flag it to the Emperor rather than
   silently falling back to the shared tree.
   **Dependency dirs: real copy, never a symlink.** A worktree has no
   gitignored `vendor/` (or `node_modules/`). For PHP give it a real copy:
   `cp -Rc vendor <worktree>/vendor` (APFS clone — instant, no extra disk).
   A `vendor` symlink makes Composer's `$baseDir` resolve to the main
   checkout, so `App\` and `Tests\` silently load main's classes and the
   worker's PHP changes are never exercised (VIN-128, 2026-10-15: RED never
   turned GREEN). Before dispatch, verify inside the container:
   `php -r 'require "vendor/autoload.php"; echo (new ReflectionClass(<any app class>::class))->getFileName();'`
   must print a path under the worktree. Same for the reviewer worktree.
   Also `mkdir -p .herdr-dev/tasks/<slug>` (all per-task files go there).
1. Write the **dev brief** (English) to `.herdr-dev/tasks/<slug>/brief.md`: the
   Requirement Brief + this mandatory TDD contract:
   - **No herdr, no delegation (mandatory first line of every dev, fix and
     review brief).** State verbatim near the top: "You are the worker (or
     reviewer) — do the work yourself. Do NOT run any `herdr` command
     (`herdr agent|pane|worktree|workspace ...`), do NOT spawn, open or
     prompt other agents/panes/workspaces, and do NOT use `ask`." Observed
     2026-10-07 (VIN-85): a freshly `/new`-cleared codex pane read a brief
     that mentioned herdr worktrees, ran `herdr agent list`, then tried
     `herdr worktree open ... --label claude-vin-85` to hand the job to a
     new agent — so a fresh context does not prevent this; only the brief
     does. If a pane still tries it, `esc` the approval and send a short
     corrective prompt restating this rule; never approve a herdr command
     from a worker or reviewer pane.
   - **Write files with the built-in edit tool (mandatory line in every dev,
     fix and tuning brief).** State verbatim: "Create and edit files with
     your built-in file-editing tool (e.g. apply_patch). Do NOT write files
     through shell heredocs (`cat > file <<'EOF'`), `python3 - <<'PY'`, `sed
     -i` or similar, and do NOT chain a file write with a test command in one
     shell call — edit first, then run the test command on its own." Observed
     2026-10-16 (VIN-115): codex wrote every TDD slice as `cat > … <<'EOF' …
     && podman exec … php artisan test` or a `python3 - <<'PY'` patch script.
     approve-loop.sh cannot parse those dialogs (`NEEDS_REVIEW: <no command
     line found>`), so every slice needed a manual approval and the wait
     script woke main on several false alarms. The tuning round, briefed
     with this line, used the edit tool and only needed approval for `npm run
     build`.
   - **Dispatch id (every brief-review, dev, fix, tuning and review brief).** Before
     writing any brief, main increments `dispatch_seq` in state and puts
     `dispatch_id: <slug>-<dispatch_seq>` on the brief's first line. The
     brief requires the pane's output file (`report.md` / `verdict.md`) to
     start with that exact line. On return, main accepts the file only if
     its first line matches the id of the **latest** dispatch — anything
     else is a leftover from an earlier ticket, round or stalled attempt,
     never evidence. This one check replaces judging staleness by mtime,
     title or header text (the cause of three stale `VERDICT: PASS` files
     being trusted, 2026-09-24). A re-dispatch of an unchanged brief after a
     stall still gets a new id.
   - **If `git_repo`**: state the worker's working directory is
     `<worker_worktree>` (absolute path) — a dedicated git worktree already
     checked out on `herdr/dev-<slug>`, created by main before this
     dispatch. The worker's job is to **verify** cwd/branch/base match this
     brief (`pwd`, `git status`, `git log -1`) and stop with a blocker in
     the report if they don't — never to run `git worktree add/switch`
     itself, and never to `cd` back to the main checkout or re-clone. All
     commands (including any container-wrapped ones per project CLAUDE.md)
     run against files under this path. State the pinned `base_sha` too;
     `git merge-base HEAD <base_sha>` must equal it.
   - **File boundary.** The dev brief carries the `owns:` and optional
     `may_touch_with_reason:` lists from the reviewed `requirement.md`
     (Phase 1 step 4) verbatim — widening them later is a brief change
     under Phase 1 step 5's re-review rule, not a dispatch-time edit. The whole repo is readable; only `owns` is writable. Touching a
     `may_touch_with_reason` path requires a one-line justification in the
     report's "boundary expansion" field; touching anything else is a
     violation, not a judgment call. If the work seems to need an
     out-of-boundary file, stop and write the blocker to the report
     (`status: BLOCKED`) instead of editing it. Lockfiles, route registries
     and migration files are out of bounds unless listed in `owns`.
   - Work in vertical slices: one behavioral test, one minimal implementation.
   - **RED:** write the test first, run the targeted command, confirm it
     fails for the expected missing behavior (not setup/syntax errors).
   - **GREEN:** write only enough production code to pass, rerun the same
     command.
   - Repeat per slice; do not batch all tests before all implementation.
   - Test public behavior, not private methods.
   - Run the relevant full suite after the final GREEN.
   - **Stop at acceptance (verify-and-stop).** Once every acceptance
     criterion has a passing test and the full suite is green, commit and
     write the report — stop there. No cleanup, renames, extra tests,
     comment polish or refactors beyond the brief; list anything worth
     doing under the report's `follow-ups` field instead.
   - **Keep raw output on disk, not in the report.** Tee every suite run to
     `.herdr-dev/tasks/<slug>/logs/<step>.log`. The report quotes only the
     summary line plus the first failure (≤20 lines) and cites the log path.
   - Commit on branch `herdr/dev-<slug>`.
   - Write the final report to `.herdr-dev/tasks/<slug>/report.md` (per-task
     path — concurrent or successive tasks never overwrite each other) with
     these fields: `dispatch_id` (first line, verbatim from the brief),
     `status` (`DONE` | `BLOCKED`), `attempt` (1 = first
     dispatch, +1 per fix round), `result_sha` (`git rev-parse HEAD` after
     the final commit), TDD evidence table (per slice: RED command +
     expected failure, GREEN command + result), final suite result, changed
     files, branch name, boundary expansion (`none` or per-file reason),
     `follow-ups` (`none` or one line each). The report is a receipt, not a
     narrative: no restating the brief, no process story.
     `result_sha` is a claim to be checked, not proof — see Phase 3.
   - If no test can express the behavior and no TDD exception was granted,
     stop and write the blocker to the report before touching production code.
   - **Blocker format (every `status: BLOCKED` report, and any question the
     pane asks main).** Adapted from ESR's "How To Ask Questions The Smart
     Way". A bare "X doesn't work" costs main a round-trip to pry the
     real question out. Five fields:
     - **goal** — the acceptance criterion or slice being worked on, not
       just the step that failed (lets main suggest a different route);
     - **symptom** — the exact command and its raw output, trimmed to the
       relevant ~20 lines, unparaphrased;
     - **tried** — what was already attempted and each result, so main
       does not suggest it again;
     - **hypothesis** — optional, explicitly labeled as a guess, kept
       separate from the symptom;
     - **ask** — one explicit question: a decision with options, or the
       specific missing fact.
2. **Check for stale context**: `herdr agent read <worker> --source
   recent-unwrapped --lines 30`. Empty/no unrelated prior conversation →
   proceed directly. If stale context is visible, no documented
   cross-provider clear exists — restart via `herdr agent start <name>
   --kind <kind> --pane <id>` on a plain shell, or ask the Emperor.
3. Dispatch without `--wait`, then wait with `scripts/wait-result.sh` in the
   background (one call, returns once — see SKILL.md › Herdr Dispatch
   Pattern). Worker gets `--approve` so allowlisted commands are approved
   while it waits:
   ```bash
   herdr agent prompt <worker> "Read .herdr-dev/tasks/<slug>/brief.md and execute it. Write your final report to .herdr-dev/tasks/<slug>/report.md when done." >/dev/null
   ~/.claude/skills/herdr-dev/scripts/wait-result.sh <worker> .herdr-dev/tasks/<slug>/report.md <dispatch_id> \
     --approve <worker_worktree> "podman exec -w <container_worktree_path> <container> "
   ```
   Reviewer dispatches (brief review, code review, confirmation review) use
   the same script without `--approve`, pointed at `brief-verdict.md` /
   `verdict.md`. On `NEEDS_REVIEW`, judge the command by hand, approve or
   `esc`, and re-run the script. Never fall back to a bare `--wait` /
   `agent wait` / `approve-loop.sh` wait: each early idle flicker becomes a
   wasted full-context main turn.
4. Reply one short line (`<worker agent> 開發中…`) and **END TURN**. The
   background call re-enters this session exactly once, with one of
   `RESULT_READY | NEEDS_REVIEW | BLOCKED | SETTLED_NO_RESULT | TIMEOUT`.

State: `{ "step": "dev_dispatched", "round": 0, "base_sha": "<sha>", "owns": [...], "dispatch_seq": <k>, "dispatch_id": "<slug>-<k>" }` — `dispatch_seq` continues from the brief review; it never resets per phase.

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

Step 1's checks are mechanical — per the global Model Tiering rule, hand
them to a Sonnet subagent (report `dispatch_id`/`result_sha`, `git log
main..branch`, boundary diff vs `owns`, clean worktree, independent test
re-runs), unless the change is ≲ 30 lines; main still decides the merge.

1. **Verify against git, not the report**:
   - `report.md` first line must equal this dispatch's `dispatch_id`
     (Phase 2 step 1). Mismatch or missing → the worker has not written
     this round's report yet: `agent read` the pane; still working → re-wait;
     settled without a report → dead job (below).
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
   - `git rev-parse herdr/dev-<slug>` must equal the report's `result_sha`;
     mismatch → commits were added or missing after the report, re-check
     before trusting anything in it.
   - **Boundary gate (hard, mechanical).** `git diff --name-only
     <base_sha>..herdr/dev-<slug>` — every path must match `owns`, or
     `may_touch_with_reason` *and* be justified in the report. Any other
     path → do not merge, do not review: send a fix brief to revert the
     out-of-boundary change (regression-test-first does not apply to a pure
     revert; the worker just removes it and re-commits). Counts as a fix
     round. Run this before the test re-runs — it is cheap and needs no
     container.
   - `git log herdr/dev-<slug> --oneline --stat` — commits exist, touch the
     expected files. Spot-check 2–3 key claimed changes in the diff.
   - Unless a TDD exception was recorded: require changed behavioral tests,
     credible RED evidence, GREEN evidence for the same command, and a
     passing full suite. **Run the reported targeted and full-suite commands
     independently.** Missing/invalid evidence → incomplete: do not merge,
     re-dispatch with the missing TDD requirement.
   - Empty branch / no report file → dead job: salvage, re-dispatch.
   - Report contains a **requirement-level blocker** → AskUserQuestion,
     then re-dispatch as needed. Build the question from the blocker's
     goal/symptom/ask fields (Phase 2 step 1), not a paraphrase. A blocker
     missing them → one-line prompt asking the worker to complete the
     format before escalating.
   - **Clean worktree gate (hard).** `git -C <worker_worktree> status
     --porcelain` must be empty before merge (non-git fallback: the shared
     tree's status must show nothing beyond the claimed, committed
     changes). Anything listed is either an uncommitted deliverable or
     stray junk, and neither may be merged around: an uncommitted claimed
     file → short follow-up prompt to commit exactly that file; stray
     entries (0-byte files, stray-punctuation names from mis-pasted shell
     commands) → confirm deletion with the Emperor. Never let them ride in via
     `git add -A`. Build/test artifacts belong in `.gitignore`, not in an
     exception list here.
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
4. Write the **review brief** (English) to `.herdr-dev/tasks/<slug>/review-brief.md`:
   open with the same no-herdr / no-delegation line as the dev brief (Phase 2
   step 1); then the
   Requirement Brief + acceptance criteria + main @ merge commit + the
   requirement's **Linear issue id** (or doc path, for pre-existing local
   specs) so the reviewer pulls the source itself instead of relying on a
   copied summary + the worker's TDD evidence + the **change manifest**
   (`git diff --stat <base_sha>..<merge-commit>`, which the reviewer must
   open file by file, including added files) + **main's own
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

   **Review scope is the whole task, every round.** The verdict covers
   `<base_sha>..<merge-commit>` (pinned base from state) against the full
   acceptance criteria. On a re-review after a fix round, also give the
   increment `<previous merge>..<merge-commit>` so the reviewer can confirm
   each prior finding is resolved — but a PASS still certifies the whole
   task, never just the patch. (Phase 4.5's scoped confirmation review is
   the one exception, and it explicitly builds on an earlier whole-task
   PASS.)

   First, **detect which stacks this diff actually touches**: `git diff
   --name-only <base_sha>..<merge-commit>` and bucket the paths by
   extension/location using the table below. Then write into the brief
   **only the stack-specific tells for buckets present in this diff** —
   drop every row that doesn't match, so agy gets a short, targeted
   checklist instead of a multi-stack dump it has to self-filter. If a
   touched file's extension isn't in the table, still include the three
   language-neutral categories and ask agy to apply its own knowledge of
   that stack's equivalent patterns.

   | Bucket | Path match | Security tells | DB/perf tells |
   |---|---|---|---|
   | PHP/Laravel | `**/*.php` | raw `DB::raw`/`whereRaw` string interpolation instead of bindings or the query builder; mass-assignment vs fillable/guarded; route-model binding or `find($id)` on a user-owned/tenant-owned model with no policy/`authorize()` or owner/tenant scope; `unserialize()` or dynamic `eval`/`include` on attacker-reachable data | Eloquent N+1 (missing `with()`), `->get()` without pagination on a possibly-large table |
   | JS/TS/frontend | `**/*.{js,ts,jsx,tsx}` | `dangerouslySetInnerHTML`/`innerHTML` from unescaped input; URLs/HTML built via string concatenation; unhandled promise rejection on a path with side effects | client-side loops re-fetching per item instead of batching |
   | SQL/mapper | `**/*.sql`, `**/*mapper*.xml` | string-concatenated SQL instead of bound parameters, especially dynamic `LIKE`/`IN` clauses | missing WHERE (full-table-scan risk), missing LIMIT/pagination on a large table |
   | Go | `**/*.go` | SQL/shell/paths built from untrusted input without parameterization/escaping; `math/rand` used for tokens/session ids instead of `crypto/rand` | goroutine/resource leak on an early-return path, unreleased `sql.Rows`/lock |

   All buckets share these **language-neutral categories** regardless of
   which rows apply:
   - **(1) Security** — server-side authz enforced (not just hidden in a
     client/template); object-level authz: a record/tenant id taken from
     the request is checked against the authenticated user/tenant, not
     trusted as-is (IDOR/BOLA); untrusted input reaching a query, shell,
     template, or dynamic-eval sink without parameterization/escaping/
     allowlisting; outbound URLs built from untrusted input without
     scheme/host/private-network restrictions (SSRF); file uploads trusted
     by client name/extension/MIME instead of server-side type checks and
     generated storage paths; token verification that skips signature
     algorithm pinning, `exp`, `aud`, or `iss`; secrets hardcoded in source
     or committed config, or logged/returned in error output;
     weak/predictable randomness for tokens or session ids; the same state
     change reachable through a second path (API vs UI, bulk/batch,
     export/import, job/console) that checks a weaker permission or skips
     per-item authz; check-then-act without a lock/atomic update on money,
     quota, approval, or state-machine steps (double-spend, replayed or
     skipped step); soft-deleted/revoked records still reachable (e.g.
     `withTrashed`, route binding, restore re-granting access current
     policy no longer allows); cache/queue/storage keys that omit the
     tenant or owner.
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
   **Security finding gate** (adapted from cloudflare/security-audit-skill):
   a security finding must name all six — lower-trust principal, the
   input/action it controls, the intended control, the boundary crossed,
   the affected principal/resource, and the concrete result. Missing any
   one → not a finding. A checklist deviation, a missing defense-in-depth
   layer when another layer already blocks the attack, same-principal
   self-impact, or guessed deployment/proxy/IAM behavior is never a
   finding. Classify each candidate:
   - `confirmed` — complete source trace plus concrete result; assign
     severity. **critical**: unauthenticated code execution, full
     data-store access, or arbitrary account takeover. **high**: fully
     defeats an explicit control with real consequences (auth bypass,
     cross-tenant/cross-user read or write, stored XSS affecting others,
     authenticated code execution). **medium**: real boundary violation
     with limited blast radius or uncommon preconditions. **low**:
     non-secret internals disclosed, or high effort for minimal gain.
     High vs medium: does it *fully defeat* the control or only weaken
     it? If you cannot state the concrete damage, it's lower than it feels.
   - `needs_validation` — source-grounded but blocked on one fact not in
     the repo (deployment, proxy, provider config); state that exact fact
     and a safe check; no severity.
   - `rejected` — disproved; omit from the verdict.
   Mapping: `confirmed` critical/high → FIX-blocking CRITICAL;
   `confirmed` medium/low and `needs_validation` → 🟡 findings, not gates.
   Require an explicit verdict per axis, findings ranked by severity,
   written to `.herdr-dev/tasks/<slug>/verdict.md` in this shape (the
   header lines are what main checks mechanically; everything else is for
   reading):
   ```
   dispatch_id: <id from the review brief>
   reviewed_sha: <merge commit the reviewer actually checked out>
   verdict: PASS | FIX | BLOCKED

   ## Axes
   (a) quality: PASS|FIX  (b) spec: …  (c) tdd: …  (d) security: …  (e) perf: …

   ## Findings
   | id | axis | class | path:line | evidence | fix |
   |----|------|-------|-----------|----------|-----|
   | F1 | b | CRITICAL | app/X.php:42 | EXTRACTED: <file:line read / command + output showing the failing case> | <concrete fix> |
   | F2 | a | 🟡 | ... | INFERRED: <what is assumed and why it wasn't confirmed> | ... |

   ## Coverage
   files opened, acceptance criteria checked, commands actually run + results

   ## Limitations
   what could not be checked and why (zero is fine — say "none")
   ```
   Consistency rules main enforces on read: `PASS` contains no CRITICAL
   row; `FIX` contains at least one CRITICAL row; every evidence cell starts
   with `EXTRACTED:` (seen directly — a file:line the reviewer read, or a
   command it ran and its output) or `INFERRED:` (reasoned, not observed);
   a CRITICAL row must be `EXTRACTED` — an `INFERRED` finding is 🟡 at most
   (this is the same "evidence, not suspicion" rule as the security gate
   above, made checkable per row); `BLOCKED`
   means required evidence was unavailable (tests could not run, worktree
   or commit mismatch, missing access) and names the missing thing under
   Limitations. A verdict that breaks these rules, or whose `dispatch_id`
   / `reviewed_sha` don't match the dispatch, is not a verdict — send the
   reviewer a one-line correction, don't interpret it. Zero findings is a
   valid PASS; a long findings list is not a quality score. Axes:
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
   `.herdr-dev/tasks/<slug>/review-brief.md` → `.herdr-dev/tasks/<slug>/verdict.md`).
8. Reply one short line (`<reviewer agent> 審查中…`) and **END TURN**.

State: `{ "step": "review_dispatched", "round": <n>, "merge_commit": "<sha>", "dispatch_seq": <k>, "dispatch_id": "<slug>-<k>" }`

---

## Phase 4: Handle the Verdict

On the reviewer wait firing (handle blocked/stalled as in Phase 3 preamble),
read `.herdr-dev/tasks/<slug>/verdict.md`. Accept it only if the pane is
settled, `dispatch_id` matches the latest dispatch, `reviewed_sha` equals
`merge_commit` in state, and the consistency rules (Phase 3 step 4) hold.
Otherwise it is stale or malformed — re-wait or correct, never act on it.

- **PASS on all axes, no 🟡 tuning suggestions** → Phase 5.
- **PASS with 🟡 tuning suggestions** (and `tuning_round` not yet done) →
  **Phase 4.5**. Do not report to Linear or move the issue to Done first.
- **BLOCKED** → the reviewer could not get the evidence it needs. Fix the
  stated cause (environment wrapper, worktree/commit, permission) or ask
  the Emperor if it is outside main's reach, then re-dispatch the same review
  with a new `dispatch_id`. Not a fix round, and never read as PASS.
- **FIX** → route findings back to the worker pane:
  1. Write the fix brief to `.herdr-dev/tasks/<slug>/brief.md`: findings verbatim
     (ranked), unmet acceptance criteria, and the contract to add a
     regression test reproducing each behavioral finding (**RED**) before
     fixing it (**GREEN**), re-commit on the same branch, same report format,
     and the same no-herdr and built-in-edit-tool lines as the dev brief.
     **Round 2 also carries an "already tried" section**: the round-1 fix
     commits and why the reviewer rejected them (the finding plus its
     evidence). Without it the worker tends to re-apply a variant of the
     rejected fix.
  2. Clear + dispatch + background wait (Phase 2 steps 2–4). END TURN.
  3. On the fix reply → **return to Phase 3** (verify → merge → re-review).
  - **Round cap**: after **2 fix rounds** still failing → stop, escalate to
    the Emperor (AskUserQuestion): sticking point + options
    (accept-with-debt / change approach / change scope).
  - A finding that is a **requirement disagreement** → the Emperor's call;
    don't let worker and reviewer ping-pong.

State per transition: `{ "step": "fix_dispatched", "round": <n>, "dispatch_seq": <k>, "dispatch_id": "<slug>-<k>" }`

---

## Phase 4.5: Tuning Round (reviewer's 🟡 suggestions)

Triggered by a PASS verdict that lists 🟡 tuning suggestions (code taste,
robustness, ergonomics — anything below FIX). **Does not count toward the
2-round fix cap**, and `round` is not incremented. Runs **at most once**
per task (`tuning_round: 1` in state).

1. **Triage** each 🟡 (main, inline). Default is **adopt**. Skip only when
   the suggestion (a) contradicts the requirement or a decision the Emperor
   made, (b) is pure process feedback about past commits that cannot be
   changed retroactively (e.g. "slice 3 batched tests") — carry it into the
   next ticket's brief instead, or (c) is `needs_validation` blocked on a
   fact outside the repo. Every skip gets a one-line reason, reported to
   the Emperor in Phase 5 and in the Linear comment. A suggestion that would
   change *what gets built* (scope/behavior the spec doesn't cover) →
   AskUserQuestion before adopting it.
2. **Tuning brief** → `.herdr-dev/tasks/<slug>/brief.md` (same opening
   no-herdr line, same built-in-edit-tool line, same cwd/branch/base, same `owns` boundary, plus "do not
   merge — main merges"). List the adopted suggestions verbatim. Contract:
   a behavioral change gets a failing test first (**RED**) then the fix
   (**GREEN**); a pure refactor with no behavior change needs no new RED —
   the brief names which existing tests guard it, and the full suite must
   stay green. Reuse the existing worker worktree and branch (the branch is
   behind main's merge commit; that's fine — it is re-merged `--no-ff`).
   Report `attempt: <n+1>` with a "tuning" label.
3. Clear + dispatch + background wait (Phase 2 steps 2–4). END TURN.
4. On the reply → **Phase 3 steps 1–3** as usual (verify via git, boundary
   gate, independent test run, merge, `/linus-review`). A CRITICAL found
   here is a normal fix round (counts toward the cap).
5. **Confirmation review**: re-add the reviewer worktree at the new merge
   commit (Phase 3 step 5) and dispatch a *scoped* review brief: the diff
   is `<previous merge>..<new merge>`, the task is (a) confirm each adopted
   🟡 is resolved, (b) check the tuning diff introduced no regression on
   any axis. Same environment constraints and verdict format.
6. Verdict:
   - **PASS** → Phase 5. Any *new* 🟡 raised here are recorded as debt in
     the Phase 5 report and the Linear comment — no second tuning round.
   - **FIX** (the tuning broke something) → normal Phase 4 FIX handling;
     **this one counts** toward the 2-round cap.

State: `{ "step": "tuning_dispatched", "tuning_round": 1, "dispatch_seq": <k>, "dispatch_id": "<slug>-<k>", "tuning_adopted": [...], "tuning_skipped": [{"item": "...", "reason": "..."}] }`
→ `{ "step": "tuning_review_dispatched", "merge_commit": "<sha>", "dispatch_seq": <k+1>, "dispatch_id": "<slug>-<k+1>" }`

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
     count, and test result summary. If Phase 4.5 ran: the tuning merge
     sha, which 🟡 were adopted, which were skipped (with reasons), and any
     new 🟡 from the confirmation review recorded as debt.
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
6. **Distill lessons, then archive the notepad.** Without this step a pitfall
   found on one ticket is cleared with the notepad and the next ticket's
   panes hit it again. Sources: `.herdr/notepad.md` pitfall entries
   (problem + root cause + fix) and fix-round findings that were confirmed
   real (state `round` > 0). Keep only what would recur on another ticket;
   a ticket-specific detail is not a lesson. Route each by what its trigger
   names:
   - **A tool, framework or command** (Composer, Laravel, Podman, Vite, an
     AI pane's habit with a language or tool) → cross-project
     `~/.claude/herdr-lessons/lessons.md`, under its stack section
     (`## <stack>`), as
     `- [YYYY-MM-DD] [<stack tags>] <trigger> — <pitfall> → <fix>`.
     **De-identify before writing** — this file is version-controlled and
     read by every project: no project, company, client or product names, no
     ticket ids, no hostnames, URLs, credentials or customer data, no
     project paths (tool-generic paths like `vendor/` are fine). Rewrite
     domain names into generic ones ("an order service", "a money column").
     If the lesson makes no sense once de-identified, it is a project
     lesson. Same pitfall already listed → append `×N+1` to that line
     instead of a new one. Cap 60 lines; over the cap, drop the oldest line
     without a `×` mark. The file lives on its own `lessons` branch (a
     worktree of the skills repo, shared by the `company` and `main`
     branches). After writing, commit it there
     (`git -C ~/.claude/herdr-lessons commit -qam "lessons：<一行摘要>"`)
     and show the user the added lines; push
     (`git pull --rebase -q && git push -q` in that directory) only after
     the user confirms. `.gitattributes` sets `merge=union`, so appends
     from two machines merge without conflict. Directory still missing
     (Phase 1's setup failed) → write nothing there and tell the user.
   - **This project's code or domain** → `.herdr/lessons.md` as
     `- [YYYY-MM-DD <slug>] <trigger: layer/file/command> — <pitfall> → <fix>`.
     Drop lines the new one replaces or whose trigger no longer exists in
     the code. Cap 30 lines; over the cap, drop the oldest.
   - **The herdr-dev flow itself** (a brief rule, a herdr quirk) → propose a
     skill edit to the user instead — the dated rules in this file came
     from exactly that.
   Nothing recurring → write nothing; never pad. Tell the user in one line
   what was added where. Then move the notepad to `.herdr/history/<slug>.md`.
7. **One ticket per session.** After reporting, recommend the Emperor start
   the next ticket in a fresh session (state, notepad and Linear carry the
   context; `/handoff` if anything is left mid-air) rather than chaining it
   here. Every main turn re-reads the whole conversation, so a session that
   already carries one ticket's briefs, verdicts and tool output makes every
   turn of the next ticket cost more (2026-10-15: three tickets plus
   planning in one session drained the Claude 5h quota).

---

## Resume Handling (`--resume`)

1. Read `.herdr-dev/state.json`. Absent → "No active /herdr-dev flow found."
2. Branch on `step`:
   - `dev_dispatched` / `fix_dispatched` → `herdr agent get <worker>`:
     `done` → Phase 3; `working` → background wait again, END TURN;
     `blocked` → Phase 3 preamble.
   - `review_dispatched` → same check on `<reviewer>`; `done` → Phase 4.
   - `tuning_dispatched` → same as `fix_dispatched` (worker), then Phase 4.5 step 4.
   - `tuning_review_dispatched` → same check on `<reviewer>`; `done` → Phase 4.5 step 6.
   - In every `*_dispatched` case, the output file only counts if its first
     line matches state's latest `dispatch_id`. Old state files with no
     `dispatch_seq` (flows started before this rule): verify via git as in
     Phase 3, then re-dispatch the pending step with a fresh id rather than
     trusting whatever report/verdict is on disk.
   - `brief_review_dispatched` → check `<reviewer>`; `done` → Phase 1 step 5
     (verify `brief-verdict.md`, arbitrate).
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
