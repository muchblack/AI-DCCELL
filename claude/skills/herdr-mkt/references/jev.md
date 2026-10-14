# Jev Checkpoints (advisory, never a gate)

A same-turn call to TypeSafe Jev (direct API, `jev-latest`). No pane, no
dispatch. It gives main a second signal at judgment points. **It never
blocks, never approves, and is never cited as the reason** ("Jev said X").
Name the concrete problem in the text instead.

## Call pattern

```bash
# request body always goes through a file
bash ~/.claude/skills/scripts/jev.sh .herdr-mkt/campaigns/<slug>/tasks/jev-<checkpoint>.json
```

```json
{
  "model": "jev-latest",
  "state": { "<field>": "<text under evaluation, verbatim>" },
  "questions": {
    "<name>": {"type": "noul", "instructions": "<question, may reference `field`>"}
  }
}
```

- The script reads `TYPESAFE_API_KEY` (env, else `~/.config/typesafe/.env`)
  and never prints it. Never write the key's value anywhere.
- Non-zero exit (no key, error, timeout, non-2xx) → **skip silently**,
  continue the flow. (A missing key is reported to the user once at Phase 0
  preflight; see flow.md. Don't repeat it at every checkpoint.)
- State is a JSON object with named fields; questions point at them with
  backticks (`` `key_message` ``). Field names are visible to the model, so
  name them plainly.
- Noul answer: `answers.<name>.noul` (0–1, probability of yes). A Noul has
  no confidence field by design; uncertainty proxy: `abs(p - 0.5) < 0.3`.
- Score answer: `answers.<name>.score` (0…levels-1, can land between
  levels) and `answers.<name>.confidence` (0–1).
- A question is **flagged** when it lands on the "bad" side (see each
  table) or is uncertain.
- Log every call's values into `state.json` → `jev[]`
  (checkpoint, target, question, value, confidence if any). Thresholds
  below are starting points; tune them from the log after a few campaigns.

## J1 — Brief Gate (Step 0, after required-field check)

`state` = `{goal, audience, deliverables, forbidden_claims}` from the brief.

| name | type | instructions | bad side |
|------|------|--------------|----------|
| goal_is_measurable | noul | Does `goal` state exactly one goal with a number and a deadline that can be checked afterward? | p < 0.5 |
| audience_is_specific | noul | Is `audience` described specifically enough to choose wording and channels for them? | p < 0.5 |
| deliverables_are_specified | noul | Is every item in `deliverables` specified with channel, quantity and format constraints? | p < 0.5 |

Flagged → main re-reads that section. If main also finds a gap, ask
the user about **that concrete gap** (四段式). If main thinks it's fine, proceed.

## J2 — Strategy, before user approval (Phase 2)

`state` = `{goal, positioning, key_message, proof_points, research_facts}`
— strategy.md sections plus the research.md facts the proof points
reference, verbatim.

| name | type | instructions | bad side |
|------|------|--------------|----------|
| single_key_message | noul | Does `key_message` commit to one clear message rather than several competing ones? | p < 0.5 |
| proofs_supported | noul | Is every item in `proof_points` directly supported by `research_facts`? | p < 0.5 |
| fits_goal | noul | Would executing this strategy plausibly move `goal`? | p < 0.5 |

Flagged → main revises strategy.md first if it agrees. Otherwise, add one line
naming the concrete risk to the approval question for the user to weigh.

## J3 — Copy variant, after humanize, before reviewer (Phase 4)

One call per variant. `state` = `{key_message, forbidden_claims, copy}` —
the strategy's key message, the brief's forbidden-claims list and the
variant text (post-polish).

| name | type | instructions | bad side |
|------|------|--------------|----------|
| carries_key_message | noul | Does `copy` clearly convey `key_message`? | p < 0.5 |
| has_single_cta | noul | Does `copy` end with exactly one clear call to action? | p < 0.5 |
| risky_claim | noul | Does `copy` contain an absolute, superlative, guaranteed or comparative claim, or anything matching `forbidden_claims`? | p > 0.5 |
| human_voice | score | How much does `copy` read like a native Taiwanese marketer wrote it? | score < 1.5 or confidence < 0.5 |

`human_voice` criteria (ordered levels):

```json
[
  "Reads as machine-written: stacked parallel phrases, empty abstractions, formulaic openings or endings, or Mainland Chinese wording.",
  "Mostly natural, but some sentences are templated, over-polished or use wording a Taiwanese writer would not pick.",
  "Reads like a native Taiwanese marketer: concrete, idiomatic Taiwan Mandarin with a consistent voice and no templated phrasing."
]
```

Flagged → main inspects that variant against the rubric item:
- main confirms a BLOCK/SHOULD issue → FIX to the copywriter (counts as a round).
- main isn't sure → put a concrete attention note in review-brief.md
  ("ig-1 Variant B line 3: check whether 「最安心」 needs a source"),
  framed as main's note. Don't mention Jev.
- main disagrees → drop it, keep the log entry.
