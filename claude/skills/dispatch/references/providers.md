# Provider Capability Matrix

## Cloud Providers (via CCB /ask)

### codex (reviewer)

- **Strengths**: Code review, structured scoring (Rubric), file operations, deterministic evaluation, diff analysis
- **Weaknesses**: Not creative, slower turnaround, no web access
- **Best for**: `review`, `score`, `audit`, `file-op`
- **Cost**: Medium (async, API)
- **Availability**: CCB session required

### gemini (inspiration)

- **Strengths**: Creative brainstorming, long-context analysis (1M tokens), web search/research, multi-modal, divergent thinking
- **Weaknesses**: Unreliable for precise code, hallucination-prone, session fragile (runtime_dir issue)
- **Best for**: `brainstorm`, `research`, `explore`, `summarize-large`, `name`
- **Cost**: Medium (async, API)
- **Availability**: CCB session required, may need re-register after reboot

### opencode

- **Strengths**: General coding, alternative perspective, independent implementation
- **Weaknesses**: Less integrated with project context
- **Best for**: `code-alt`, `second-opinion`, `prototype`
- **Cost**: Medium (async, API)
- **Availability**: CCB session required

### droid

- **Strengths**: Task execution, shell operations
- **Weaknesses**: Limited reasoning
- **Best for**: `execute`, `shell-task`
- **Cost**: Medium (async, API)
- **Availability**: CCB session required

## Local Providers (direct call)

### mlx (local, free)

- **Strengths**: Reasoning, analysis, summarization, classification, privacy-safe, zero cost
- **Weaknesses**: OOM on large prompts (>5000 tokens), slower on complex generation, Gemma 4 is reasoning model (needs sufficient max_tokens)
- **Best for**: `reason`, `analyze`, `classify`, `summarize`, `translate`
- **Cost**: Free (local GPU)
- **Availability**: localhost:8090, health-check.sh
- **Call**: `mlx-chat.sh`

### ollama (LAN, free)

- **Strengths**: Code generation, code review, medium-quality drafts, zero cost
- **Weaknesses**: 12GB VRAM limit, slower than cloud, quality varies by model
- **Best for**: `draft-code`, `code-review-light`, `refactor`
- **Cost**: Free (LAN GPU)
- **Availability**: 192.168.1.206:11434, health-check.sh
- **Call**: via MCP `ollama_code` / `ollama_review`

## Claude (self, always available)

### claude (designer + executor)

- **Strengths**: Strongest reasoning, best code quality, architecture design, security-sensitive tasks, full project context
- **Weaknesses**: Most expensive (token cost), single-threaded (can't delegate to self async)
- **Best for**: `architect`, `security`, `complex-code`, `decision`, `integrate-results`
- **Cost**: High (direct token usage)
- **Availability**: Always

---

## Task Type → Provider Mapping (Priority Order)

| Task Type                   | Primary  | Fallback 1         | Fallback 2 |
| --------------------------- | -------- | ------------------ | ---------- |
| `review` (code/plan)        | codex    | ollama             | claude     |
| `brainstorm` / `creative`   | gemini   | claude             | —          |
| `research` / `explore`      | gemini   | claude (WebSearch) | —          |
| `reason` / `analyze`        | mlx      | claude             | —          |
| `draft-code` (non-critical) | ollama   | claude             | —          |
| `draft-code` (security)     | claude   | —                  | —          |
| `score` / `evaluate`        | codex    | claude             | —          |
| `summarize` (large doc)     | gemini   | mlx                | claude     |
| `classify` / `tag`          | mlx      | claude             | —          |
| `refactor`                  | ollama   | claude             | —          |
| `architect` / `design`      | claude   | —                  | —          |
| `file-op`                   | codex    | claude             | —          |
| `second-opinion`            | opencode | gemini             | —          |
| `prototype`                 | opencode | ollama             | —          |
