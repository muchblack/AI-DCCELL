# Provider Capability Matrix

Providers are agents running in herdr panes. Availability is decided at run
time from `herdr agent list`; a provider with no live pane for this project is
unavailable. Claude (this session) is always available.

## Herdr Providers

### codex

- **Strengths**: Code review, structured scoring (rubric), file operations, deterministic evaluation, diff analysis, TDD implementation
- **Weaknesses**: Not creative, slower turnaround, no web access
- **Best for**: `review`, `score`, `audit`, `file-op`, `draft-code`

### agy

- **Strengths**: Independent review (quality, spec compliance, security, performance), second look at a finished diff
- **Weaknesses**: May report idle while sitting at an approval dialog
- **Best for**: `review`, `second-opinion`

### gemini

- **Strengths**: Creative brainstorming, long-context analysis, web search / research, divergent thinking
- **Weaknesses**: Unreliable for precise code, hallucination-prone
- **Best for**: `brainstorm`, `research`, `explore`, `summarize-large`, `name`

### opencode

- **Strengths**: General coding, alternative perspective, independent implementation
- **Weaknesses**: Less integrated with project context
- **Best for**: `code-alt`, `second-opinion`, `prototype`

### droid

- **Strengths**: Task execution, shell operations
- **Weaknesses**: Limited reasoning
- **Best for**: `execute`, `shell-task`

## Claude (self, always available)

- **Strengths**: Strongest reasoning, best code quality, architecture design, security-sensitive tasks, full project context
- **Weaknesses**: Most expensive, cannot delegate to itself
- **Best for**: `architect`, `security`, `complex-code`, `decision`, `integrate-results`

---

## Task Type → Provider Mapping (Priority Order)

| Task Type                   | Primary  | Fallback 1         | Fallback 2 |
| --------------------------- | -------- | ------------------ | ---------- |
| `review` (code/plan)        | codex    | agy                | claude     |
| `brainstorm` / `creative`   | gemini   | claude             | —          |
| `research` / `explore`      | gemini   | claude (WebSearch) | —          |
| `reason` / `analyze`        | claude   | —                  | —          |
| `draft-code` (non-critical) | codex    | opencode           | claude     |
| `draft-code` (security)     | claude   | —                  | —          |
| `score` / `evaluate`        | codex    | claude             | —          |
| `summarize` (large doc)     | gemini   | claude             | —          |
| `classify` / `tag`          | claude   | —                  | —          |
| `refactor`                  | codex    | opencode           | claude     |
| `architect` / `design`      | claude   | —                  | —          |
| `file-op`                   | codex    | claude             | —          |
| `second-opinion`            | agy      | opencode           | gemini     |
| `prototype`                 | opencode | codex              | claude     |
