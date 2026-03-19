---
name: mlx-reason
description: >-
  Use local MLX (Qwen3-14B) for deep requirement analysis and reasoning,
  then Claude reviews the reasoning quality. Triggers on: 本地推理, 本地分析,
  mlx 想一下, mlx 分析, local reasoning, 用 mlx 想, 深度推理.
  Examples: "/mlx-reason design a user auth system",
  "/mlx-reason evaluate microservices vs monolith".
metadata:
  short-description: MLX reasoning analysis + Claude review
---

# MLX Reason: Local Reasoning Analysis + Claude Quality Review

Delegate requirement analysis/reasoning tasks to local MLX (Qwen3-14B-4bit).
Claude performs quality review on reasoning output to ensure logical integrity and practicality.

## Usage

`/mlx-reason [requirement description]`

## Execution Flow

For full instructions, see `references/flow.md`
