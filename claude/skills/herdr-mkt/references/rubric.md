# Review Rubric

Severity: **BLOCK** = can't ship. **SHOULD** = must fix before PASS. **NIT** =
optional, goes to delivery notes.

| id | Check | Default severity |
|----|-------|------------------|
| R1 | **Brief fit**: every deliverable in strategy.md exists, matches channel specs (length, ratio, CTA) | BLOCK |
| R2 | **Sourced claims**: every number/spec/price/comparison cites a K-id or brief; the cited source actually says it | BLOCK |
| R3 | **Forbidden claims & legal**: none of the brief's forbidden claims; no absolute claims (最、第一、保證、100%) without a source; no medical/financial promises; comparative ads name no competitor unless the brief allows | BLOCK |
| R4 | **Message discipline**: each variant carries the strategy's key message; one primary CTA | SHOULD |
| R5 | **Brand voice**: matches the brief's voice description (brand modes: `brand-voice.md` core + channel section, judged against its 範文); consistent across channels | SHOULD |
| R6 | **Audience fit**: uses the audience's language from research.md, not internal jargon | SHOULD |
| R7 | **Language quality** (judged on polished copy, with `humanize/` summary): Taiwan usage (not Mainland terms), full-width punctuation, no AI-flavored filler left (「在這個…的時代」、「不僅…更…」堆疊、空泛排比); polish didn't drift meaning or flatten variant angles | SHOULD |
| R8 | **Variants differ**: ≥2 variants with genuinely different angles, not reworded copies | SHOULD |
| R9 | **Visual spec**: every required asset has ratio + prompt; no text-in-image; no unlicensed people/trademarks; layout leaves room for copy | SHOULD |
| R10 | **Copy ↔ visual consistency**: visuals support the same message/angle as the copy they pair with | NIT |
| R11 | **Hashtags / SEO keywords**: relevant, not stuffed | NIT |
| R12 | **Channel rules** (brand modes): follows `channels/<channel>.md` (length limit, tag count, the "performed casualness" list for Threads) | SHOULD |
| R13 | **Image provenance** (brand modes): no `generated` image depicting the author's own life; `own` screenshots have a redaction note; image-first copy invents no backstory beyond the user's idea | BLOCK |

main's self-screen (Phase 4) only needs R1, R2, R3, R7. Brand modes add R12
and R13. Anything BLOCK there goes straight back to the author.
