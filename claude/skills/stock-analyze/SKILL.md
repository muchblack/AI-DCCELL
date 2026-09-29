---
name: stock-analyze
description: >-
  雙視角股市深度分析：平行呼叫華爾街財經專家 + 國際政治關係專家分析 stockDB 原始資料，
  最後綜合兩份報告產出決策摘要。
  Triggers on: 深度分析, 雙視角分析, 專家分析, stock deep, dual analysis,
  expert analysis, 股市深度分析, 兩個專家, 雙專家分析, 全面分析.
  Examples: "/stock-analyze", "/stock-analyze 03-30",
  "/stock-analyze 2026-03-28 國際財經".
metadata:
  short-description: 雙專家平行分析 + 綜合決策摘要
---

# Stock-Analyze — 雙視角股市深度分析

以兩個平行 subagent 分別扮演華爾街財經專家與國際政治關係專家，分析 stockDB 原始資料，
再由 Claude 綜合，最終產出面向台灣投資人的決策摘要。

## Usage

```
/stock-analyze [date] [feed]
```

For full instructions, see `references/flow.md`
