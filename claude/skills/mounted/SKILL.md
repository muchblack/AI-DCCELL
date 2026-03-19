---
name: mounted
description: Report which CCB providers are mounted (session exists AND daemon is online). Outputs JSON. Triggers on: 哪些 provider 在線, mounted providers, 誰在線上, who is online, provider 狀態, provider status, 有哪些可用.
metadata:
  short-description: Show mounted CCB providers as JSON
---

# Mounted Providers

Reports which CCB providers are considered "mounted" for the current project.

## Definition

`mounted = has_session && daemon_on`

## Execution

```bash
ccb-mounted
```
