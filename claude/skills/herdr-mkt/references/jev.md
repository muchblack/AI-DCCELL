# Jev Checkpoints (advisory, never a gate)

Same mechanism as herdr-dev Phase 1 step 5: a same-turn call to TypeSafe Jev
via Vercel AI Gateway. No pane, no dispatch. It gives main a second signal
at judgment points. **It never blocks, never approves, and is never cited
as the reason** ("Jev said X"). Name the concrete problem in the text
instead.

## Call pattern

```bash
set -a; source ~/.config/herdr-dev/.env 2>/dev/null; source .herdr-mkt/.env 2>/dev/null; set +a
# request body always goes through a file
curl -sS --max-time 10 https://ai-gateway.vercel.sh/v1/evaluate \
  -H "Authorization: Bearer $AI_GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d @.herdr-mkt/campaigns/<slug>/tasks/jev-<checkpoint>.json
```

```json
{
  "model": "typesafe-ai/jev",
  "state": "<text under evaluation, verbatim>",
  "questions": {
    "<name>": {"type": "boolean", "instructions": "<question>"}
  }
}
```

- No key, error, timeout or non-200 → **skip silently**, continue the flow.
  (A missing key is reported to the user once at Phase 0 preflight; see
  flow.md. Don't repeat it at every checkpoint.)
- Never write the key's value anywhere outside this shell.
- Read `answers.<name>.probability` (0–1). No calibrated confidence field
  (empty in herdr-dev testing, 2026-09-23). Uncertainty proxy:
  `abs(p - 0.5) < 0.3`.
- A question is **flagged** when it lands on the "bad" side (see each
  table) or is uncertain.
- Log every call's probabilities into `state.json` → `jev[]`
  (checkpoint, target, question, p). This lets us tune the questions after a few campaigns.

## J1 — Brief Gate (Step 0, after required-field check)

`state` = the brief's goal + audience + deliverables + forbidden claims sections.

| name | instructions | bad side |
|------|--------------|----------|
| goal_is_measurable | Does this brief state exactly one goal with a number and a deadline that can be checked afterward? | p < 0.5 |
| audience_is_specific | Is the target audience described specifically enough to choose wording and channels for them? | p < 0.5 |
| deliverables_are_specified | Is every deliverable specified with channel, quantity and format constraints? | p < 0.5 |

Flagged → main re-reads that section. If main also finds a gap, ask
the user about **that concrete gap** (四段式). If main thinks it's fine, proceed.

## J2 — Strategy, before user approval (Phase 2)

`state` = strategy.md positioning + key message + proof points + the
research.md facts those proof points reference (verbatim).

| name | instructions | bad side |
|------|--------------|----------|
| single_key_message | Does this strategy commit to one clear key message rather than several competing ones? | p < 0.5 |
| proofs_supported | Is every proof point directly supported by the quoted research facts? | p < 0.5 |
| fits_goal | Would executing this strategy plausibly move the stated goal? | p < 0.5 |

Flagged → main revises strategy.md first if it agrees. Otherwise, add one line
naming the concrete risk to the approval question for the user to weigh.

## J3 — Copy variant, after humanize, before reviewer (Phase 4)

One call per variant. `state` = the strategy's key message + the brief's
forbidden-claims list + the variant text (post-polish), labelled.

| name | instructions | bad side |
|------|--------------|----------|
| carries_key_message | Does the copy clearly convey the stated key message? | p < 0.5 |
| has_single_cta | Does the copy end with exactly one clear call to action? | p < 0.5 |
| risky_claim | Does the copy contain an absolute, superlative, guaranteed or comparative claim, or anything matching the forbidden list? | p > 0.5 |
| reads_human | Does this read like a native Taiwanese marketer wrote it, not an AI? | p < 0.5 |

Flagged → main inspects that variant against the rubric item:
- main confirms a BLOCK/SHOULD issue → FIX to the copywriter (counts as a round).
- main isn't sure → put a concrete attention note in review-brief.md
  ("ig-1 Variant B line 3: check whether 「最安心」 needs a source"),
  framed as main's note. Don't mention Jev.
- main disagrees → drop it, keep the log entry.
