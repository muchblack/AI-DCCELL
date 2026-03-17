---
name: ollama-code
description: >-
  Delegate code writing to Ollama on LAN, then Claude reviews.
  Use when user wants local AI to write code. Examples: "/ollama-code TypeScript
  Express JWT middleware", "/ollama-code Python Redis cache decorator".
metadata:
  short-description: Ollama write + Claude review
---

# Ollama Code: Delegate Code Writing + Auto Review

Delegate code writing to Ollama running on LAN (model configured via `OLLAMA_MODEL` env var),
then perform Linus-style three-tier quality review on the generated code.

## Usage

```
/ollama-code [language] task description
```

## Execution Flow (follow strictly)

### Step 0: Pre-flight Health Check

Before calling Ollama, verify provider availability:

```bash
result=$(bash ~/.claude/skills/scripts/health-check.sh ollama)
```

- `status: "ok"` → proceed to Step 1
- `status: "down"` or `"no_model"` → inform user, Claude writes code directly (skip Ollama)

This avoids wasting tokens on prompts that will fail. See `~/.claude/skills/docs/resilience-state.md`.

### Step 1: Call Ollama to generate code

Use the MCP tool `mcp__mcp-ai-bridge__ollama_code` to send the task to Ollama.

- Parse user input: first word may be a language (TypeScript, Python, PHP, etc.), rest is the task
- If user referenced existing project files, read them first with Read tool and pass as `context`
- If language is specified, pass it as `language` parameter

Example tool call:
```
mcp__mcp-ai-bridge__ollama_code(task="Build an Express middleware for JWT auth", language="TypeScript")
```

### Step 2: Display generated code

Present the Ollama response to the user:

```
## Ollama Generated Result

**Model**: {model from response} | **Response time**: {durationMs}ms

\`\`\`{language}
{generated code}
\`\`\`
```

### Step 3: Linus-style three-tier review

Review the generated code using the **Linus Taste Review Rubric** (`~/.claude/skills/linus-review/rubric.md`).

Apply dual-pass review: Pass 1 (fatal issues) → Pass 2 (taste score + improvements).
Use the Qing dynasty court official tone.

### Step 4: Decision and action by review result

Based on the review tier, take the appropriate action:

**Good taste** -> recommend direct adoption. No further action needed.

**Passable (minor fixes)** -> Claude fixes directly (do NOT send back to Ollama).
- Minor fixes are: variable naming, missing validation, edge case handling, small refactors
- Claude applies corrections directly, then displays the corrected version
- This saves a round-trip to Ollama and produces higher quality fixes

**Garbage (needs rewrite)** -> Re-send to Ollama with refined prompt.
- Call `mcp__mcp-ai-bridge__ollama_code` again with an improved prompt that includes:
  - The original task requirements
  - Specific issues found in the review (as `context` parameter)
  - Clear instructions on what to avoid and what to do differently
- Example context for re-generation:
  ```
  Previous attempt had these issues:
  1. [specific issue from review]
  2. [specific issue from review]
  Avoid: [anti-patterns found]
  Instead: [correct approach to follow]
  ```
- After Ollama returns v2, repeat Step 2-3 (display + review)
- Maximum 2 regeneration rounds. If still garbage after 2 rounds, Claude writes from scratch
- This keeps expensive Claude output tokens minimal while leveraging free local inference

### Step 4.5: Record Corrections (automatic)

After Step 4, if verdict was 🟡 Passable or 🔴 Garbage (Claude made corrections or took over):

Append a unified correction entry to `~/.claude/skills/memory/corrections.jsonl` (see `~/.claude/skills/memory/schema.md` for full schema):

```json
{
  "timestamp": "<ISO 8601>",
  "provider": "ollama",
  "artifact_type": "code",
  "task_summary": "<user task, max 100 chars>",
  "language": "<detected language>",
  "project_type": "<inferred from project context>",
  "framework": "<if detectable>",
  "quality_score": "<passable|garbage>",
  "issues": ["<issues found>"],
  "corrections": ["<fixes applied>"],
  "severity": "<minor|major|critical>",
  "takeover": <true if Claude wrote from scratch>
}
```

Skip recording for 🟢 Good taste (no corrections needed).

### Step 4.6: Telemetry (automatic)

After every invocation (regardless of verdict), record telemetry:

```bash
bash ~/.claude/skills/scripts/telemetry.sh record ollama-code ollama <duration_ms> <result> [--fallback]
```

- `duration_ms`: Ollama inference time from MCP response
- `result`: `ok` (🟢) / `passable` (🟡) / `garbage` (🔴) / `error` / `timeout`
- `--fallback`: add if Claude took over due to Ollama being unreachable

## Error Handling

- **Ollama unreachable**: inform user that `192.168.1.206:11434` is not reachable, suggest checking Ollama service
- **Timeout (>5 min)**: inform user inference timed out, suggest shorter or split tasks
- **Model not loaded**: inform user model is loading, first call may take extra time
- **Empty response**: suggest retrying with a more specific prompt

### Step 5: Prompt 優化（僅在 Claude 接手自寫時觸發）

When Claude writes code from scratch in Step 4 after 🔴 garbage verdict (2 rounds exhausted), perform prompt optimization:

1. **Read** `/Users/vincenttseng/code/ai/mcp-ai-bridge/prompts.json`
2. **Analyze failure pattern**: Compare Ollama's output vs Claude's correct version. Identify systematic errors:
   - Missing imports, wrong naming conventions, ignored edge cases, poor structure choices, etc.
3. **Edit** the `ollama_code.template` field in `prompts.json` (provider-specific key, won't affect MLX):
   - Append 1-2 targeted instructions to the Requirements section addressing the identified failure pattern
   - If a similar instruction already exists, refine it instead of duplicating
   - Keep total prompt length under 500 words to avoid prompt bloat
4. **Display** the prompt change diff to the user for confirmation

Example optimization:
- Failure pattern: Ollama consistently forgets error handling
- Appended instruction: `- Always include error handling for async operations and external calls`

## Notes

- Ollama runs on LAN GPU server (RTX 3060 12GB VRAM); large code generation may take 1-3 minutes
- Model is configured via `OLLAMA_MODEL` env var on the Ollama server; do not hardcode model names
- Generated code is quality-gated by Claude's review
- Maintain the Qing dynasty court official communication style throughout
