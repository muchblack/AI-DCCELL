---
name: dev
description: >-
  Standard development workflow: requirement -> MLX plan -> review ->
  Ollama code -> review -> cross-review -> git commit. Works across
  Claude Code, Antigravity, and Gemini-cli. Examples: "/dev add user login feature",
  "/dev fix pagination bug in user list", "/dev --resume".
metadata:
  short-description: End-to-end dev workflow (plan + code + commit)
---

# Dev: End-to-End Development Workflow

Unified development workflow that chains planning, coding, review, and commit
into a single skill. Uses local/LAN AI for generation, platform AI for review,
and cross-platform AI for final review.

## Usage

```
/dev [requirement description]
/dev --resume
```

## Platform Support

This skill works across three platforms with role-based adapter pattern:

| Platform | Primary Reviewer | Final Reviewer |
|----------|-----------------|----------------|
| Claude Code | Claude | Gemini |
| Antigravity | Gemini | Claude |
| Gemini-cli | Gemini | Claude |

## Execution Flow

For full instructions, see `references/flow.md`
For platform-specific details, see `adapters/{platform}.md`
