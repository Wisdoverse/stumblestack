---
id: 2cc975a1-9f47-4dc5-8962-9c9d9d4d6eb7
title: "MCP resources are read-only data and are not the right primitive for actions"
category: mcp
tags:
  - mcp
  - resources
  - tools
symptoms:
  - "client never 'runs' a resource"
  - "expected a side effect from a resource read"
root_cause: "MCP `resources` expose readable content (files, records) addressed by URI; `tools` perform actions. Modeling an action as a resource means it never executes."
fix: "Use a `tool` for anything with a side effect or computation; use a `resource` for fetchable context."
verified_count: 0
created: 2026-05-28
---

Rule of thumb: noun the model reads -> resource; verb the model invokes -> tool.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
