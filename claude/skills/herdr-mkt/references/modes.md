# Herdr-Mkt — Brand Modes (init / quick / weekly)

Campaign mode (`/herdr-mkt <brief>`) serves one campaign at a time. Brand
modes serve one long-running brand: the **workspace is the cwd**, which holds
the brand files. Nothing here hardcodes a path; run the skill from the brand
workspace on whatever machine does the marketing.

```
<cwd>/
  brand-voice.md        # core voice + per-channel sections (author fills)
  content-calendar.md   # topic pool + weekly queue (main is the only writer)
  drafts/               # YYYY-MM-DD-<slug>.md, waiting for the user
  published/            # user moves posted drafts here
  .herdr-mkt/           # working files, same as campaign mode
```

Channel rules live in `channels/<channel>.md` (`threads`, `ig`). Every brand
mode reads `brand-voice.md` core + the matching channel section + the
channel file.

---

## Brand preflight (quick and weekly)

1. Tool preflight from `flow.md` Phase 0 step 0 (Jev, images).
2. `brand-voice.md` missing → tell the user to run `/herdr-mkt init`. END TURN.
3. `grep -n '待作者填寫' brand-voice.md` has hits → list the unfilled
   sections and END TURN. Those sections (立場, 範文) are the author's own
   voice. Without them the copy comes out generic, and main must not fill
   them in on the author's behalf.
4. Build the forbidden list once per run:
   ```bash
   awk '/^#+ 禁用清單/{f=1;next} f&&/^```/{if(c++)exit;next} f&&c' brand-voice.md \
     | grep -vE '^\s*(#|$)' > .herdr-mkt/forbidden.txt
   ```
   Every polished draft is checked with `grep -niE -f .herdr-mkt/forbidden.txt`.
   A hit → back to the copywriter (or main reverts the sentence if the
   polish introduced it). The user never sees a draft that has a hit.

---

## `/herdr-mkt init`

1. Refuse to overwrite: if `brand-voice.md` or `content-calendar.md` already
   exists in cwd, say which and stop.
2. Copy `references/brand-voice-template.md` → `brand-voice.md`,
   `references/calendar-template.md` → `content-calendar.md`,
   `mkdir -p drafts published .herdr-mkt`.
3. Don't `git init`. Version control is the user's call; mention it in one line.
4. Tell the user which sections are marked 「待作者填寫」 and that quick or
   weekly won't run until they're filled. main may draft the other
   sections only if the user asks.

---

## `/herdr-mkt quick "<idea or link>" [--image=<path>] [--channel=threads|ig] [--copywriter=<pane>]`

One idea → one draft file. Panes: main + one copywriter (default `codex`).
**No reviewer pane**: the user reviews every draft before posting, and a
one-off post isn't worth another handoff. Quick runs are one-shot. There's
no `--resume`; if one is interrupted, re-run it.

`slug` = `YYYY-MM-DD-<short-english-kebab>`. Working dir: `.herdr-mkt/quick/<slug>/`
with `tasks/`, `.raw/`, `humanize/`.

### Step 0 — Image question (always first)

Skip if `--image` is given (→ A). Otherwise ask one AskUserQuestion
(四段式):

- **A) 我有圖** → user gives a path → image-first flow (Step 2a)
- **B) 沒圖，幫我配** → copywriter proposes the image (`card` / `generated` / `own`)
- **C) 純文字** → `image: none`

Non-interactive run (`claude -p`, cron, CI): nobody can answer, so take C
and still put one image suggestion in `image_note`. Don't stop on a question
nobody will answer.

Ask only this one question. The idea text is the image's context. Ask a
follow-up only when the idea is too thin to tell what the post is about (e.g. a
bare link with no comment, or a single word).

### Step 1 — Angle (main as strategist)

1. Channel: `--channel`, else `threads`.
   If the channel is `ig` and `channels/ig.md` still has `style: TBD`,
   produce the caption only, set `image: own|generated` with an
   `image_note`, render nothing, and tell the user why.
2. Pick one angle that fits the brand-voice core and the channel section.
   Write it down in one line.
3. Link in the idea → fetch the raw page (same raw-HTML rule as the
   Researcher in `roles.md`) and record each usable fact as K1, K2… with URL and
   date in `tasks/copywriter-brief.md`. News-based posts are where fabricated
   numbers and quotes show up. No source → the claim doesn't go in.

### Step 2a — Image-first (A only)

1. main reads the image and writes an **objective description** of what is
   visible (objects, text on screen, people, setting) into the task brief.
   The user's idea is the meaning. The description only fills in detail.
   Copy must not invent a backstory the user didn't give.
2. **Privacy check** on the image: faces of other people, names or company
   info on screens, addresses, house numbers, licence plates. Any hit →
   tell the user what and where, ask them to crop or blur, and wait.
3. **Location metadata:**
   `command -v exiftool >/dev/null && exiftool -s -gps:all <img>`. GPS
   present → tell the user. Don't modify their file. No exiftool → say the
   check couldn't run.
4. Set `image: own`, `image_file: <path>`.

### Step 3 — Dispatch copywriter

Task brief = Copywriter prompt (`roles.md`) + "Brand-mode additions" block
+ the angle, K-ids, image description or B instruction, and output path
`.herdr-mkt/quick/<slug>/draft.md`. Dispatch per SKILL.md → Dispatch;
completion = the file exists.

### Step 4 — Polish + checks (main)

Same as `flow.md` Phase 4 steps 1–4 (snapshot raw → `/speak-human-tw`
auto-apply + summary → fidelity diff → char counts), with:

- scene = 社群貼文; protected list adds the image description facts and
  every K-id claim.
- forbidden grep uses `.herdr-mkt/forbidden.txt`.
- self-screen rubric R2, R3, R7, R12, R13 (`rubric.md`). A BLOCK goes back
  to the copywriter, max 2 rounds, then hand it to the user as-is with the finding.

### Step 5 — Image production (B only)

- `card` → main renders a plain text card per `channels/<channel>.md`
  (HTML → screenshot), saves next to the draft.
- `generated` → `/hf-image` with the copywriter's prompt. Refuse prompts
  that depict the author's own life (see channel file), and set `own` instead.
- `own` → nothing to render; the draft stays `status: needs-image`.

### Step 6 — Hand off

1. Move to `drafts/<slug>.md` (+ image files as `drafts/<slug>-<n>.<ext>`).
2. Append a row to the weekly queue in `content-calendar.md` with status
   `draft` (or `needs-image`).
3. Report in 繁體中文: path, the two variant angles, humanize change count,
   and anything the user must do (supply photo, crop, GPS).

---

## `/herdr-mkt weekly [--copywriter=<pane>] [--reviewer=<pane>]`

One week = one campaign run with a generated brief. Reuses the campaign
machinery (`flow.md` Phases 3–6) with `slug = week-YYYY-Www`, `mode: weekly`
in `state.json`, so `--resume` works.

### Step 1 — Candidates (main)

1. Read `content-calendar.md`: `每週篇數` (default 2) and topic pool rows with
   status `idea`.
2. Candidates = `每週篇數 × 2`, from the pool first. If the pool is short,
   main may add current-events topics via WebSearch, **each with a source
   URL**. The pool always comes first.
3. Show the candidates as a numbered list (id, topic, channel, one-line
   angle, why now). Ask the user to reply with the ids they want. Picking
   topics is the strategy gate: nothing is dispatched before the user answers.
4. Mark picked rows `picked`, dropped-by-user rows stay `idea`.

### Step 2 — Brief + strategy (main)

Write `.herdr-mkt/campaigns/<slug>/brief.md` from brand-voice.md (voice,
forbidden list) + picked topics, and `strategy.md` = one deliverable per
topic (channel, angle, image source guess, K-ids for any news topic, fetched
by main as in quick Step 1.3). The user's pick counts as strategy approval
(`strategy_approved: true`). No separate research phase.

### Step 3 — Production → review → delivery

`flow.md` Phase 3 (copywriter only, no visual pane; the copywriter fills the
image fields) → Phase 4 (with `forbidden.txt`, R12, R13) → Phase 5 with a
reviewer pane ≠ copywriter → Phase 6.

Phase 6 additions:
- copy each final deliverable to `drafts/<YYYY-MM-DD>-<slug>.md`, render
  `card`/`generated` images as in quick Step 5;
- update the weekly queue rows (`draft` / `needs-image`);
- `delivery.md` lists every `own` image the user still has to shoot or
  screenshot, with each `image_note`.

---

## Draft file format (both modes)

```markdown
---
id: T-017
channel: threads
mode: quick | weekly
status: draft | needs-image | approved | published
sources: [K1, brief]          # [] when there are no factual claims
image: none | own | card | generated
image_note: "截上週 PR review 的留言畫面（遮掉人名）"
image_file: drafts/2026-10-15-pr-review-1.png
humanized: true
verdict: none | PASS          # quick = none (user reviews)
---
## Variant A — <angle>
...
（字數：N）
## Variant B — <angle>
...
（字數：N）
```

The user changes `status` and moves posted files to `published/`. No pane
posts, schedules or calls a platform API.
