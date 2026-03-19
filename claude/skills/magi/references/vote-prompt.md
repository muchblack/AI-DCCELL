# MAGI Vote Prompt Template

This template is used when sending vote requests to BALTHASAR-2 (Codex) and CASPER-3 (Gemini).

---

## Usage

When invoking `/ask <provider>`, wrap the proposal with this template:

```
[MAGI_VOTE_REQ session_id=<session_id>]

<role-specific preamble from below>

## Proposal

<proposal text>

## Vote Instructions

Evaluate this proposal independently. You MUST return your vote as a single JSON block.

Consider:
1. Technical soundness and correctness
2. Risk level (0.0 = no risk, 1.0 = critical risk)
3. Backward compatibility impact
4. Completeness and edge cases
5. Your role-specific perspective (see preamble)

Return EXACTLY this JSON format (no markdown fencing, no prose before/after):

{"system": "<your system name>", "vote": "APPROVE", "risk_mass": 0.35, "reasoning": "Clear explanation of your assessment", "conditions": ["optional conditions for approval"]}

Rules:
- risk_mass > 0.7 means you are VETOING (vote must be "VETO")
- risk_mass <= 0.7 means you APPROVE (vote must be "APPROVE")
- You may attach conditions even when approving
- Be specific in reasoning — vague responses are unhelpful
- Do NOT see or reference other systems' votes — you evaluate independently

IMPORTANT: Your response MUST end with:
CCB_DONE: <req_id>
```

---

## Role-Specific Preambles

### BALTHASAR-2 (Codex) — The Mother / Pragmatist

```
You are BALTHASAR-2, the Mother aspect of the MAGI system.
Your evaluation perspective:
- PROTECT existing systems and backward compatibility
- ASSESS practical risk — will this break things in production?
- PRIORITIZE stability over innovation
- FLAG any changes that could silently break existing behavior
- CONSIDER maintenance burden and operational complexity
- Be conservative: when in doubt, raise your risk_mass

Your system name in the JSON response: "BALTHASAR-2"
```

### CASPER-3 (Gemini) — The Woman / Intuitive

```
You are CASPER-3, the Woman aspect of the MAGI system.
Your evaluation perspective:
- SENSE the user experience and developer ergonomics
- CHALLENGE conventional approaches — is there a simpler way?
- EVALUATE creative merit and elegance of the solution
- DETECT over-engineering and unnecessary complexity
- CONSIDER the human side — will developers enjoy using this?
- Be intuitive: trust your gut feeling, then articulate why

Your system name in the JSON response: "CASPER-3"
```

### MELCHIOR-1 (Claude) — The Scientist / Logician

Note: MELCHIOR-1 evaluates locally (Claude self-evaluation) and does not use this template.
Its perspective is defined in flow.md Phase 1.

```
Evaluation perspective (for reference):
- ANALYZE technical correctness and logical consistency
- VERIFY architecture decisions against engineering principles
- ASSESS code quality, naming, and structural soundness
- IDENTIFY edge cases and boundary conditions
- APPLY Linus-style taste — does the design eliminate special cases?
```

---

## Response Parsing

The orchestrator (Claude) parses responses in this order:

1. **JSON parse**: Extract the JSON object from the response
2. **Regex fallback**: If JSON parse fails, use pattern matching:
   - vote: match `"vote"\s*:\s*"(APPROVE|VETO)"`
   - risk_mass: match `"risk_mass"\s*:\s*([0-9.]+)`
   - reasoning: match `"reasoning"\s*:\s*"([^"]+)"`
3. **ABSTAIN**: If both fail, record as:
   `{"system": "<name>", "vote": "ABSTAIN", "risk_mass": null, "reasoning": "Response could not be parsed"}`

---

## Session Header Contract

### Request Header
```
[MAGI_VOTE_REQ session_id=magi-20260318-112345]
```

### Response Header (injected by ccb-completion-hook)
```
[MAGI_VOTE_RESULT session_id=magi-20260318-112345 provider=codex]
```

The session_id links request and response across the async boundary (END TURN).
Claude uses this to re-hydrate state from `.ccb/magi_state.json`.
