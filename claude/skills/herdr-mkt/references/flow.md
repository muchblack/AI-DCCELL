# Herdr-Mkt — Execution Flow

## Phase 0 — Setup

0. **Tool preflight (tell the user once, up front).** Check:
   ```bash
   set -a; source ~/.config/herdr-dev/.env 2>/dev/null; source .herdr-mkt/.env 2>/dev/null; set +a
   [ -n "${AI_GATEWAY_API_KEY:-}" ] && echo jev=on || echo jev=off
   [ -n "${HF_TOKEN:-}" ] && echo images=on || echo images=off
   ```
   If either is off, tell the user before Step 0 (one short line each:
   what gets skipped, how to enable it, e.g. put the key in
   `~/.config/herdr-dev/.env`, or run `! export HF_TOKEN=...`). Then proceed
   without waiting. Mid-flow skips stay silent; record the preflight result
   in `state.json` (`tools: {jev, images}`). The first campaign only found
   out at the end that Jev never ran and images couldn't render.
1. Run Step 0 Brief Gate (SKILL.md).
2. `slug` = kebab-case from brief title + `YYYYMMDD`.
3. `mkdir -p .herdr-mkt/campaigns/<slug>/{tasks,copy,assets}`; copy brief to
   `brief.md` (frozen; brief changes later → new round of strategy approval).
4. `herdr agent list` → bind panes per role (flags first, then defaults).
   Enforce pane separation rules. Write `state.json`:

```json
{
  "slug": "autumn-sale-20261001",
  "mode": "full",
  "phase": "research",
  "panes": { "researcher": "w5:p3", "copywriter": "w5:p2", "visual": "w5:p4", "reviewer": "w5:p5" },
  "rounds": { "copy": 0, "visual": 0, "research": 0 },
  "strategy_approved": false,
  "humanize_mode": "auto-apply+summary",
  "tools": { "jev": "on|off", "images": "on|off" },
  "jev": []
}
```

## Phase 1 — Research

1. main writes `tasks/researcher-brief.md` from the Researcher prompt in
   `roles.md` + brief path + specific questions derived from the brief
   (competitors to check, audience questions, channel norms).
2. Dispatch (background). On return verify:
   - `research.md` exists, header `status: done`.
   - Every claim in "Facts" has a URL; spot-check 2–3 URLs yourself
     (WebFetch). A dead or mismatched source → re-dispatch with the specific
     claims listed (counts as a research round, max 2).
3. `--lite`: main does this phase itself, same output format and the same
   rules as the Researcher prompt in roles.md: terms/pricing/FAQ pages,
   raw-HTML quotes.
4. **Brief-contradiction gate.** If research contradicts the brief on
   pricing, offer, features or the goal, stop and ask the user
   (AskUserQuestion, 四段式, quote the source verbatim). Then update both
   `briefs/<file>.md` and the frozen `brief.md` copy, and record the answer
   as a K-id sourced to「產品方確認（brief），<date>」. Strategy can't start
   until this is resolved.

## Phase 2 — Strategy (main) + User Gate

1. main writes `strategy.md`: one-line positioning, key message, 2–3
   supporting proof points (each referencing a research.md fact id),
   per-channel angle, deliverable list with specs (length, format, CTA),
   KPI + how the user measures it.
2. Run Jev J2 (`jev.md`). If main agrees with a flag, revise strategy.md first.
   If main disagrees but the risk is real, add one line naming it to the
   approval question.
3. Show the user a summary and AskUserQuestion (四段式):
   A) approve, B) adjust (which part), C) back to research.
4. Only on A: `strategy_approved: true`, proceed. END TURN otherwise.

## Phase 3 — Production (parallel)

1. Write `tasks/copywriter-brief.md` and `tasks/visual-brief.md` (roles.md
   prompts + file paths to brief/research/strategy + deliverable specs).
2. Dispatch both in the same turn, each backgrounded.
3. On copywriter return:
   - files exist per deliverable list, ≥2 variants each, headers filled;
   - forbidden-claims grep (hard gate);
   - every number/spec appears in research.md or brief.md.
4. On visual return:
   - `visual-spec.md` has one entry per required asset with ratio, layout
     notes, and an English image prompt;
   - main renders each with `/hf-image --ratio <r> <prompt>` and moves
     outputs to `assets/`. Render failure → note it, don't block copy review.
     (In WSL `--open` is meaningless; skip it.)

## Phase 4 — Humanize + Self-Screen (main)

Runs on every copy file, every round. Order matters: polish first, then
judge the polished text.

1. **Snapshot raw.** `cp copy/<f>.md copy/.raw/<f>.r<round>.md` before
   touching anything.
2. **Polish with `/speak-human-tw`.** Mode is **跳過確認、事後摘要**,
   chosen by the user on 2026-10-01 and recorded in `state.humanize_mode`.
   Don't ask per file; re-ask only if the brief's content type is clearly
   different (e.g. support-reply templates instead of campaign copy).
   Per file:
   - scene = the channel (社群貼文 / EDM / 銷售頁 / 電商文案), so the
     skill picks the right intensity;
   - protected list += every K-id-cited claim, numbers, prices, dates,
     product names, campaign codes, URLs, hashtags, the CTA wording from
     strategy.md, and the brief's must-include elements;
   - polish each variant separately. Variants must keep their different
     angles, so don't converge them toward one "best" voice;
   - the skill only removes AI flavor. It doesn't apply the brand voice.
     Brand voice is the copywriter's job and R5's check.
   - write the change summary to `humanize/<f>.r<round>.md`: total count
     first, then 原句／為什麼要改／改成了什麼 per change. 0 changes →
     still write the file and say so.
3. **Fidelity check (hard).** Compare raw vs polished:
   ```bash
   diff <(grep -oE '[0-9][0-9,.%/:-]*|https?://[^ )]+|#[^ ]+' copy/.raw/<f>.r<n>.md | sort) \
        <(grep -oE '[0-9][0-9,.%/:-]*|https?://[^ )]+|#[^ ]+' copy/<f>.md | sort)
   ```
   Also check the forbidden-claims grep on the polished file and confirm the
   front-matter `sources:` is unchanged. Any mismatch → restore the affected
   sentence from raw and note it in the humanize summary as "reverted".
4. **Recompute character counts** after polish with the fixed rule
   (`len(body.replace('\n',''))`: spaces count, newlines don't; same as
   roles.md). The count line is derived data, so update it; it isn't a
   polish change. Exclude `（字數：N）` lines from the step 3 number diff,
   otherwise every count update shows up as a fidelity mismatch.
   Before the first polish, verify the copywriter's stated counts match the
   script. A mismatch means the copywriter used a different rule, so FIX it.
5. **Rubric pass** (R1, R2, R3, R7) on polished copy. BLOCK → treat as FIX
   (Phase 5 step 3). The reviewer never sees it, and it counts as a round.
6. **Jev J3** per variant (`jev.md`). Handle flags as described there:
   confirmed → FIX; unsure → concrete attention note for review-brief;
   disagree → drop.

## Phase 5 — Review

1. Write `review-brief.md`: paths to brief, research, strategy, all
   (polished) copy, visual-spec, assets list, rubric path, and main's
   self-screen notes, including the J3 attention notes. Point the reviewer to
   the `humanize/` summaries for R7, so it can see what was already
   de-AI'd and judge whether meaning drifted.
2. Dispatch to reviewer and wait for the **file**, not the pane status
   (SKILL.md → Dispatch: agy reports idle between steps). Expect `verdict.md`:

```
verdict: PASS | FIX
round: <n>
findings:
  - id: F1
    severity: BLOCK | SHOULD | NIT
    rubric: R3
    target: copy/ig-1.md:4
    issue: <what is wrong>
    expected: <what would satisfy the rubric>
```

3. FIX → group BLOCK/SHOULD findings by author (copy/visual/research), write
   `tasks/<role>-fix-r<n>.md` with only that author's findings, dispatch to
   the same pane, then repeat Phase 3 checks → Phase 4 → Phase 5.
   The copywriter edits the **polished** `copy/<f>.md`, not `.raw/`. Phase 4
   then snapshots and polishes again under the new round number.
   NITs go to `delivery.md` as optional notes, no round consumed.
4. Round > 2 for any deliverable → stop, show the user the verdict history
   and ask: accept as-is / give direction / drop deliverable.

## Phase 6 — Delivery

1. main writes `delivery.md`: deliverable table (file, channel, variant
   angle), assets, remaining NITs, a link to each file's latest
   `humanize/` summary (with how many changes and reverts), the KPI and how to measure it, and
   "not done by this flow: publishing / scheduling / ad setup".
2. Report to the user in 繁體中文 with the path. Optionally log via `/worklog`.
3. Linear-sourced brief → post a status comment summarizing the delivery
   (deliverables, rounds). Don't change issue state; the campaign isn't
   "done" until it's published, which is the user's call.
4. `state.json` → `phase: delivered`.

## Resume

`/herdr-mkt --resume` → read `state.json`, re-run `herdr agent list`; if a
bound pane is gone, ask the user to restart it (same role, same campaign),
then continue from `phase`.
