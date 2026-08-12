---
name: dev
description: >-
  Standard development workflow: requirement -> plan -> cross-review ->
  CCB worker code -> review -> cross-review -> git commit. Works across
  Claude Code, Antigravity, and Gemini-cli. Triggers on: 開發, 實作, 寫功能,
  加功能, 修 bug, 修復, implement, develop, build feature, fix bug, 做這個功能,
  幫我寫, 幫我做, 從頭到尾做, end-to-end, 全流程開發, 完整開發流程.
  Examples: "/dev add user login feature", "/dev fix pagination bug in user list",
  "/dev --resume".
metadata:
  short-description: End-to-end dev workflow (primary draft → worker code → cross-review → commit)
---

# Dev: End-to-End Development Workflow

Unified development workflow that chains planning, coding, review, and commit
into a single skill. Primary reviewer drafts the plan, CCB worker generates code,
and a cross-platform AI provides the final quality gate.

## Usage

```
/dev [requirement description]
/dev --resume
```

## Platform Support

This skill works across three platforms with role-based adapter pattern:

| Platform | Primary Reviewer | Plan Reviewer | Code Writer | Code Reviewer |
|----------|-----------------|---------------|-------------|---------------|
| Claude Code | Claude | analyst (agy) | worker2 → worker1 | reviewer1 → reviewer2 |
| Antigravity | Gemini | analyst (agy) | worker2 → worker1 | Claude |
| Gemini-cli | Gemini | analyst (agy) | worker2 → worker1 | Claude |

## Execution Flow

For full instructions, see `references/flow.md`
For platform-specific details, see `adapters/{platform}.md`
