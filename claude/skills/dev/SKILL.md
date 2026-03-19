---
name: dev
description: >-
  Standard development workflow: requirement -> MLX plan -> review ->
  Ollama code -> review -> cross-review -> git commit. Works across
  Claude Code, Antigravity, and Gemini-cli. Triggers on: 開發, 實作, 寫功能,
  加功能, 修 bug, 修復, implement, develop, build feature, fix bug, 做這個功能,
  幫我寫, 幫我做, 從頭到尾做, end-to-end, 全流程開發, 完整開發流程.
  Examples: "/dev add user login feature", "/dev fix pagination bug in user list",
  "/dev --resume".
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
