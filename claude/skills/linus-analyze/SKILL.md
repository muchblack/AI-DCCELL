---
name: linus-analyze
description: Five-layer Linus-style requirement analysis with structured decision output. Use for a clear but complex requirement that needs a worth-doing verdict and a simplest approach. For vague requirements, run /grill-with-docs first. Triggers on: 深度分析, 需求分析, requirement analysis, deep analysis, 五層分析, 分析一下這個需求, analyze this requirement, 決策分析, decision analysis.
metadata:
  short-description: Linus five-layer analysis + structured decisions
---

# Linus-Style Requirement Analysis

Three pre-check questions, then a five-layer analysis (data structure, special
cases, complexity, breakage, practicality), then a fixed-format verdict.
Claude does the analysis directly.

Vague requirement or open decisions → `/grill-with-docs` first; this skill
comes after the shared understanding is confirmed.

For full instructions, see `references/flow.md`
