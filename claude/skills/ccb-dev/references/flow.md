# CCB-Dev Execution Flow

Requirement-driven development on the CCB architecture. All inter-AI messages
are in **English** (token economy); all user-facing output is **Traditional
Chinese** in Grand Council minister tone.

## Input

`$ARGUMENTS` is one of:

- A **requirement document path** (e.g. `docs/spec.md`) — primary case.
- A **task-system ticket id** (e.g. `JIRA-123`) — future case, see Phase 0.
- An **inline requirement description** — freeform text.
- `--resume` — continue from a pending async wait.

State is tracked in `.ccb/ccb-dev-state.json` so async waits survive turns.

---

## Step 0: Requirement Document Gate

Run this before Phase 0. Full rules live in SKILL.md's "Step 0 — Requirement
Document Gate" section — do not duplicate them here:

- Doc path already given → verify it exists/readable, proceed.
- No doc path → ask the user (AskUserQuestion) whether one exists; if not,
  PAUSE and point them to `/grill-with-docs` (+ `/to-spec`), then END TURN.
- Never treat an inline chat description as a substitute document.

---

## Phase 0: Resolve Input Source

1. If `$ARGUMENTS == --resume` → go to **Resume Handling**.
2. If `$ARGUMENTS` is an existing file path → `Read` it; this is the requirement.
3. If `$ARGUMENTS` matches a ticket pattern (e.g. `[A-Z]+-\d+`):
   - **Task-system adapter (extension point).** If a configured fetcher exists
     (e.g. `gh`, a Jira MCP tool, or `.ccb/ccb.config` integration), fetch the
     ticket body + acceptance criteria and treat it as the requirement.
   - If no fetcher is wired yet, tell the Emperor the ticket source is not
     connected and ask for the doc/path instead (AskUserQuestion).
4. Otherwise treat `$ARGUMENTS` as an inline requirement description.

> Keep the source resolution dumb and explicit. Jira/ticket support is a single
> swappable fetcher — do not build a plugin framework for it now (YAGNI).

---

## Phase 1: main — Confirm the Requirement

main (self) does this directly; no worker involved yet.

1. **Read the requirement** fully. If it is large/multi-phase, scope to what the
   Emperor asked (e.g. "phase 1"); if scope is unstated, infer the smallest
   coherent unit and state your assumption.
2. **Analyze the project**: tech stack, existing patterns, key files (Glob/Read).
3. **If the task touches the DB**: run `/db` to confirm the relevant schema
   (tables, columns, indexes) and fold it into the brief.
4. **Produce a Requirement Brief** (this is the contract handed to the worker):
   - **Goal** — what this delivers, in one or two sentences.
   - **Scope** — in / out of scope, explicit.
   - **Affected layers/files** — best-effort map.
   - **Constraints** — stack versions, env (podman exec for PHP, host npm, etc.),
     branch strategy, security-sensitive paths.
   - **Acceptance criteria** — concrete, checkable bullet points. The reviewer
     will judge against these.
   - **Test seams** — public behavior boundaries to test; prefer existing seams
     and the highest practical integration boundary.
   - **Test commands** — the smallest targeted command for each slice and the
     relevant full-suite command.
   - **TDD exception** — normally none. For non-behavioral work that cannot
     reasonably be tested, `main` records the specific reason before dispatch.
   - **Assumptions** — anything you filled in for the Emperor.
   - **Open questions** — anything genuinely ambiguous.
5. **Gate on questions.** If there are open questions that change *what gets
   built* (scope, behavior, acceptance), **ask the Emperor now** with
   AskUserQuestion (四段式: Re-ground → Simplify → Recommend → Options, one
   decision per question). Do **not** dispatch with unresolved requirement
   ambiguity. Pure implementation details (which the worker can decide) are not
   blockers — let the worker decide.
6. Present the Requirement Brief to the Emperor (繁中) and proceed to Phase 2.
   Re-asking the Emperor to "approve the brief" is unnecessary unless step 5
   raised a real question — main confirming the requirement *is* the gate.

Write state: `{ "step": "requirement_confirmed", "source": "...", "brief": "..." }`.

---

## Phase 2: Dispatch Development → Worker Group (codex first)

1. Resolve the primary developer from `.ccb/ccb.config`: the **codex-backed
   worker** in the `work` window (e.g. `worker1`). Fallback: the
   opencode-backed worker (e.g. `worker3`), used only if the codex worker is
   unavailable or stalls (>~5 min with no progress).
2. Build the **dev brief** in English from the Requirement Brief: goal, scope,
   acceptance criteria, constraints/env, branch strategy, test seams, test
   commands, and exactly what to output. Include this mandatory TDD contract:
   - Work in vertical slices: one behavioral test, one minimal implementation.
   - **RED:** write the test first and run the targeted command; confirm it
     fails for the expected missing behavior, not for setup or syntax errors.
   - **GREEN:** write only enough production code to pass, then rerun the same
     command.
   - Repeat RED/GREEN for the next slice; do not batch all tests before all
     implementation.
   - Test public behavior, not private methods or internal call structure.
   - Run the relevant full suite after the final GREEN.
   - Return committed code plus a concise TDD evidence table containing each
     slice, RED command and expected failure, GREEN command and result, final
     suite result, changed test files, branch, and worktree path.
   - If no test can reasonably express the behavior and `main` did not provide
     a TDD exception, stop and return a blocker before changing production code.
3. **Clear the opencode session before dispatching to it.** This applies
   whenever the resolved worker is `opencode`-provider — primary or fallback,
   whatever it is named this project (e.g. `worker3`): run
   `ccb clear <opencode-worker>` and confirm `clear_status: ok`. `ask`/`ccb ask`
   has no per-call "fresh session" flag; `ccb clear` is what actually sends
   OpenCode's native `/clear` and starts it on a clean session. Skipping this
   is a likely cause of opencode stalling mid-task on accumulated session
   state. Not needed for the codex worker (codex/agy/claude have their own
   session isolation) — since codex is now primary, this step is normally
   only relevant on the opencode fallback path.
4. Dispatch (example uses `worker1` as the codex-backed primary; substitute
   the real name from `.ccb/ccb.config`):
   ```bash
   CCB_CALLER=main ask worker1 <<'EOF'
   <dev brief>
   EOF
   ```
5. **Async guardrail**: output contains `[CCB_ASYNC_SUBMITTED` → reply one short
   line (`worker1 開發中…`) and **END TURN**.

Write state: `{ "step": "dev_dispatched", "worker": "worker1", "job": "<id>" }`.

When the worker's reply arrives in-session, continue to Phase 3.

---

## Phase 3: Verify → Merge → Dispatch Review

1. On the worker's completion reply, **verify against git, not the narration**:
   - `git log ccb/<worker> --oneline -5` — commits exist and touch the expected
     files (`--stat`). Spot-check 2–3 key claimed changes in the diff.
   - Unless `main` recorded a TDD exception, require changed behavioral tests,
     RED evidence showing the expected failure before implementation, GREEN
     evidence for the same targeted command, and a passing relevant full suite.
     Run the reported targeted and full-suite commands independently. Missing
     or invalid evidence means the job is incomplete: do not merge; re-dispatch
     the worker with the missing TDD requirement.
   - **Empty branch / work landed in the wrong tree / `status=incomplete`** →
     dead job. Cancel it, salvage any on-disk work (commit it where it lies if
     usable), and re-dispatch the same brief (opencode: `ccb clear` first).
   - If the worker reports a **blocker that is a requirement question** → jump to
     "Ask the Emperor" (AskUserQuestion), then re-dispatch as needed.
   - **Repo hygiene**: `git -C <worktree> status --porcelain` — flag any
     untracked entry outside the claimed changed files. 0-byte files or names
     with stray punctuation/no extension are the signature of a mis-pasted
     shell command run in the wrong place (e.g. a Chinese phrase word-split by
     the shell into separate `touch` args). Not a merge blocker by itself, but
     never let it ride into main via `git merge`/`git add -A` — call it out to
     the Emperor and confirm deletion before merging.
2. **Merge before review**: `git merge --no-ff ccb/<worker>` into main. Record
   the resulting main commit — the review brief references **main @ that
   commit**, not the worker branch.
3. Resolve the codeReview group from `.ccb/ccb.config` (the `codeReview` window
   agents, e.g. `reviewer1` agy + `reviewer2` codex). **`main` fans out** —
   dispatch the review **directly to every reviewer in the group**, one `ask`
   per reviewer. Do NOT delegate fan-out to reviewer1: empirically it replies
   "reviewer2 processing…" without creating a real job, so coverage drops to
   zero.
4. Build the **review brief** in English: the Requirement Brief + acceptance
   criteria + main @ the merged commit + **the requirement document path**
   (the one that passed Step 0) + the worker's TDD evidence, and ask for an
   explicit verdict on **three axes**:
   - **(a) code quality** — taste, correctness, maintainability (Linus
     standards — data structures, edge cases, no needless complexity).
   - **(b) spec compliance** — check the diff against the requirement
     document item by item; any unimplemented, partially implemented, or
     out-of-scope-added behavior is a FIX finding.
   - **(c) TDD compliance** — tests cover public behavior at the declared seams;
     each behavioral slice has credible RED/GREEN evidence; the final relevant
     suite passes. An unapproved missing test or missing evidence is a FIX.
   Require `PASS`/`FIX` per axis, with findings ranked by severity. Send the
   SAME brief to each reviewer.
5. Dispatch to each reviewer (parallel, in one turn):
   ```bash
   CCB_CALLER=main ask reviewer1 <<'EOF'
   <review brief>
   EOF
   CCB_CALLER=main ask reviewer2 <<'EOF'
   <review brief>
   EOF
   ```
6. **Async guardrail** → reply one short line (e.g. `reviewers 審查中…`) and
   **END TURN**. The reviewer replies re-enter the session as they complete.
7. **Verify coverage before judging.** Wait until a real verdict has returned
   from **every** group member (confirm via each reviewer's reply/job, not one
   agent's narration). If a member is missing, re-dispatch that reviewer. Then
   **`main` synthesizes** all verdicts into the PASS/FIX decision (FIX if any
   reviewer raises a Critical/Major that holds up).

Write state: `{ "step": "review_dispatched", "round": <n>, "reviewers_pending": [...] }`.

---

## Phase 4: Handle the Verdict

On the reviewer's reply, classify:

- **PASS** → go to Phase 5.
- **FIX** → route the specific findings **back to the same worker group** that
  wrote the code (Phase 2's worker), not to `main`:
  1. **Reset the worker's worktree to current main first**
     (`git -C <worktree> reset --hard main` or equivalent) — otherwise the fix
     is built on a stale base and the merge will conflict or regress.
  2. Build a fix brief: the findings (verbatim, ranked), the acceptance criteria
     still unmet, and the expectation to add a regression test that reproduces
     each behavioral finding (**RED**) before fixing it (**GREEN**), then
     re-commit and return the same TDD evidence.
  3. If `<same-worker>` is the opencode-backed worker, run
     `ccb clear <same-worker>` first (see Phase 2 step 3 — same reasoning
     applies to every re-dispatch, not just the first one). Not needed if
     `<same-worker>` is the codex-backed worker.
  4. `CCB_CALLER=main ask <same-worker> <<'EOF' ... EOF`, async guardrail, END TURN.
  5. On the fix reply, **return to Phase 3** (verify → merge → re-review).
  - **Round cap**: after **2 fix rounds** still failing, stop the loop and
    escalate to the Emperor (AskUserQuestion): summarize the sticking point and
    options (accept-with-debt / change approach / change scope).
  - If a finding is actually a **requirement disagreement** (reviewer and brief
    conflict), that is the Emperor's call → ask, don't let the workers ping-pong.

Write state on each transition: `{ "step": "fix_dispatched", "round": <n> }`.

---

## Phase 5: Report (and optionally land the work)

1. Summarize for the Emperor (繁中): what was built, the RED/GREEN and final
   test commands/results, the review outcome, how many rounds, the
   branch/worktree, and any deferred items / `ponytail:` debt.
2. Merges into main already happened per round (Phase 3 step 2). Any extra
   commit/push beyond that only when asked. Commit messages in Traditional
   Chinese, with the current model's standard `Co-Authored-By:` trailer (do not
   hardcode a model name).
3. Clear/disable the state file (`step: "done"`).

---

## Ask the Emperor (cross-cutting)

At any phase, if a **requirement-level** question arises (scope, behavior,
acceptance, conflicting instructions), stop and ask via AskUserQuestion using
the 四段式 format from CLAUDE.md:

1. **Re-ground** (1–2 sentences): which project/branch/task we are in.
2. **Simplify**: explain the question plainly (assume 20 min away from screen).
3. **Recommend**: `建議選 [X]，因為 [原因]`.
4. **Options**: A) B) C), each with a one-line note. One decision per question.

Implementation-level choices are the worker's to make — do not escalate those.

---

## Resume Handling (`--resume`)

1. Read `.ccb/ccb-dev-state.json`. If absent → "No active /ccb-dev flow found."
2. Branch on `step`:
   - `dev_dispatched` → `pend <recorded worker>` (see `state.worker`), then
     Phase 3.
   - `review_dispatched` → `pend` EACH reviewer in `reviewers_pending` (every
     codeReview-group member); once all verdicts are in, synthesize, then Phase 4.
   - `fix_dispatched` → `pend <recorded worker>`, then Phase 3 (re-review).
   - `requirement_confirmed` → re-dispatch Phase 2.
   - `done` → nothing pending; report last outcome.
3. Any reply (live or pended) with `status=incomplete` → dead job (Phase 3
   step 1): cancel, salvage on-disk work via git, re-dispatch the same brief.
