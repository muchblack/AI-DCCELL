---
name: herdr-mkt
description: >-
  Herdr-architecture AI marketing team flow (DRAFT). main (this Claude Code
  session) acts as marketing director: gates on a campaign brief, dispatches
  research → strategy → copy + visual spec → review to dedicated herdr panes
  (default researcher=agy, copywriter=codex, visual=codex, reviewer=agy),
  hands off via files under .herdr-mkt/campaigns/<slug>/, and routes FIX
  verdicts back to the original author (max 2 rounds). Every copy file is
  polished by speak-human-tw (auto-apply + summary) before review; Jev gives
  advisory signals at brief, strategy and copy checkpoints. Content production
  only — never publishes. Triggers on: herdr mkt, 行銷團隊, AI 行銷, 跑行銷,
  行銷活動, 做檔活動, campaign, marketing team, 行銷企劃, 產文案,
  社群貼文企劃. Examples: "/herdr-mkt briefs/autumn-sale.md",
  "/herdr-mkt briefs/x.md --lite", "/herdr-mkt --resume",
  "/herdr-mkt briefs/x.md --researcher=w5:p3 --reviewer=w5:p5".
metadata:
  short-description: "Herdr marketing team: brief → research → strategy → copy/visual → review loop"
  status: draft
---

# Herdr-Mkt — AI Marketing Team Flow (Herdr)

Same skeleton as `herdr-dev`, with TDD replaced by a **review rubric**.
Output is reviewed marketing content on disk. Publishing, ad spend and
anything outward-facing stay with the user.

```
brief.md
  → [main]        Brief Gate (missing fields? → ask user)      + Jev J1
  → [researcher]  research.md        (sourced facts, competitors, audience)
  → [main]        strategy.md  + Jev J2 → USER APPROVES strategy (hard gate)
  → [copywriter]  copy/*.md   ┐ parallel
  → [visual]      visual-spec.md ┘   → [main] renders images via /hf-image
  → [main]        /speak-human-tw on EVERY copy file (mandatory, every round)
  → [main]        fidelity check + rubric self-screen          + Jev J3
  → [reviewer]    verdict.md   PASS → deliver / FIX → back to author (max 2)
```

## Usage

```
/herdr-mkt <brief-path | linear-issue-id> [--lite] [--researcher=<pane>] [--copywriter=<pane>] [--visual=<pane>] [--reviewer=<pane>]
/herdr-mkt --resume
```

Role flags take a pane id (`w5:p3`) or an agent name (`agy`); an agent name
resolves to the first matching pane in this project's cwd that isn't already
bound to another role.

## Step 0 — Brief Gate (always first)

1. Brief path / Linear id given → read it, check against
   `references/brief-template.md`. Required fields: product, goal (one
   measurable outcome), audience, channels, deliverables list, brand voice,
   forbidden claims / legal constraints, deadline.
2. Missing required fields → AskUserQuestion (四段式), one field per
   question. Never invent a goal, audience or claim on the user's behalf.
   All fields present → run Jev J1 (`references/jev.md`); a flag only
   prompts main to re-read that section.
3. No brief at all → offer to copy `references/brief-template.md` to
   `briefs/<slug>.md` and grill the user (`/grilling`) to fill it. END TURN
   until it exists.

## Roles

| # | Role | Default | Writes | Never does |
|---|------|---------|--------|------------|
| 1 | Director | main (self) | `strategy.md`, `delivery.md`, images via `/hf-image` | write final copy |
| 2 | Researcher | `agy` | `research.md` | recommend strategy |
| 3 | Copywriter | `codex` | `copy/<channel>-<n>.md` | invent facts not in `research.md`/brief |
| 4 | Visual | `codex` (2nd pane) | `visual-spec.md` (layout + image prompts) | generate images itself |
| 5 | Reviewer | `agy` (2nd pane) | `verdict.md` | rewrite content |

Role prompts: `references/roles.md`. Review rubric: `references/rubric.md`.
Jev checkpoints: `references/jev.md`.

**Pane separation rules (hard):**
- One pane = one role per campaign. Record the binding in state.
- Reviewer pane ≠ any author pane (researcher, copywriter, visual). A pane
  that produced something can't be the one that reviews it.
- Missing panes → tell the user exactly which agents to start (e.g.
  "start a second agy pane in w5") and END TURN. Don't spawn panes unless
  asked.

**`--lite` mode** (3 panes: main + codex + agy). Fits the current w5 layout:
main does research itself (WebSearch, sources mandatory), codex is
copywriter and writes the visual spec, agy reviews. Use for the first
campaigns until handoff formats are stable.

## File Layout

```
.herdr-mkt/
  state.json                         # phase, pane bindings, round counts
  campaigns/<slug>/
    brief.md                         # copy of the gated brief (frozen)
    tasks/<role>-brief.md            # dispatch briefs (main writes)
    research.md
    strategy.md
    copy/<channel>-<n>.md            # polished (post speak-human-tw) — the live version
    copy/.raw/<channel>-<n>.r<round>.md  # copywriter's original, kept per round
    humanize/<channel>-<n>.r<round>.md   # speak-human-tw change summary
    visual-spec.md
    assets/                          # rendered images
    review-brief.md
    verdict.md                       # reviewer writes; overwritten per round
    delivery.md                      # final index for the user
```

Each output file starts with a front-matter header the author must fill:
`status: done|blocked`, `round: <n>`, `sources: [...]` (research/copy).

## Dispatch

Use the exact pattern in `herdr-dev` → "Herdr Dispatch Pattern" (brief via
file, `herdr agent prompt <pane> "..." --wait` in the background,
`agent get` + `agent read` on return, approval loop, stall handling).
Don't duplicate it here. **Verify current `herdr` flags first** by running
bare `herdr agent`.

Copywriter and visual have no dependency on each other → dispatch both in
the same turn, each as its own backgrounded call.

**Completion = the output file exists, not the pane status.** Observed
(2026-10-01, agy/Gemini reviewer): `agent prompt --wait` returned and `agent
wait --until idle` settled while the pane was still mid-task, because agy
flips to `idle` between tool steps. The same can happen with any provider.
After `--wait` returns, check the expected output file (`research.md`,
`copy/*`, `verdict.md`, report). If it's missing and the pane isn't `blocked`,
poll for the file in a backgrounded loop. Don't re-prompt, because that
interrupts the running task:

```bash
f=<dir>/verdict.md
for i in $(seq 1 150); do
  [ -s "$f" ] && { sleep 5; echo ready; break; }      # sleep: let the write finish
  herdr agent get <pane> | grep -q '"agent_status":"blocked"' && { echo BLOCKED; break; }
  sleep 10
done
```

## Core Principles

- **Strategy is the user's call.** After `strategy.md`, stop and get explicit
  approval (AskUserQuestion, 四段式) before any copy is dispatched. Copy
  written on an unapproved strategy is wasted work.
- **Every factual claim has a source.** Numbers, competitor facts, product
  specs, prices → must trace to `research.md` (with URL) or `brief.md`.
  Unsourced claim = automatic FIX. This replaces "trust git, not narration".
- **Forbidden claims are a hard gate.** main greps all copy against the
  brief's forbidden-claims list before review (`grep -niE`). Any hit goes
  back to the copywriter without reaching the reviewer, and counts as a round.
- **Every copy file goes through `/speak-human-tw` before anyone judges it.**
  main runs it, because codex/agy panes can't invoke Claude skills. It runs on
  every copy file in every round, including fix rounds, since a fix adds
  new text. Mode is fixed by the user (2026-10-01): **auto-apply + post-hoc
  summary** (the skill's 「跳過確認、事後摘要」). Don't ask per file. The
  reviewer and the user only ever see polished copy. Details: `flow.md`
  Phase 4.
- **Polish must not change facts.** speak-human-tw's protected list is
  extended with: every K-id-cited claim, numbers, prices, dates, product
  names, campaign codes, URLs, hashtags, CTA wording from strategy.md.
  After polishing, main runs the fidelity check (numbers/URLs identical to
  raw, forbidden-claims grep, `sources:` header untouched). Any mismatch →
  revert that change from the raw copy.
- **main self-screens before the reviewer**: rubric pass (R1, R2, R3, R7) on
  the polished copy. A blocking issue goes straight back to the author.
- **Jev assists judgment at three checkpoints and is advisory only**
  (`references/jev.md`): J1 brief readiness, J2 strategy before user
  approval, J3 each copy variant after polish. A flag makes main look
  harder at that spot. It never blocks or approves anything by itself, and
  it's never cited as a reason to the user or reviewer. No API key or call
  failure → skip silently.
- **FIX goes back to the original author**, with the reviewer's line-level
  findings attached. main does not rewrite copy. Max 2 rounds per
  deliverable, then escalate to the user with the verdict history.
- **Reviewer judges, never rewrites.** Its verdict cites file:line and rubric
  item. "Rewrite the whole thing" isn't a valid finding.
- **Variants, not one answer.** Copywriter delivers ≥2 variants per
  deliverable with differing angles, so the user picks (or A/B tests).
- **No publishing, no external writes.** No posting, scheduling, emailing or
  ad-platform calls from any pane. `delivery.md` is the end of the flow.
- **No performance data → say so.** Without user-provided analytics (CSV
  export etc.), research must not fabricate baseline metrics; the strategy
  states the KPI and how the user should measure it.
- **Briefs and pane talk in English; deliverables in the brief's target
  language** (default 繁體中文, Taiwan usage).
- **Stale pane context**: same caveat as herdr-dev. Add an override line to
  each brief: "You are the <ROLE> for campaign <slug>. Ignore prior roles or
  tools from earlier sessions."

State lives in `.herdr-mkt/state.json`. Full step-by-step: `references/flow.md`.
