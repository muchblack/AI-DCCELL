---
name: career-ops
description: >-
  AI 求職助手：職缺評估（A-F 評分）、履歷客製化、面試故事庫、Pipeline 追蹤。
  Triggers on: 求職, 職缺評估, 評估職缺, 履歷, career-ops, job evaluation,
  evaluate job, 客製化履歷, 面試準備, interview prep, pipeline, 求職追蹤.
  Examples: "/career-ops evaluate <url>",
  "/career-ops resume <url>",
  "/career-ops stories",
  "/career-ops pipeline".
argument-hint: "<subcommand> [args]"
metadata:
  short-description: AI 求職助手（評估 + 履歷 + 面試 + 追蹤）
---

# Career-Ops：AI 求職助手

基於 [career-ops](https://github.com/santifer/career-ops) 的核心概念，用 Claude Code 原生能力實現。
定位是「幫你篩選值得投的職缺」，不是亂槍打鳥的自動投遞工具。

完整流程見 `references/flow.md`
