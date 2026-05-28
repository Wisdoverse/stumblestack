---
id: 7153009b-f97a-4ad1-92a5-57f197202c35
title: "Anthropic tool_result must be in a user message and reference the matching tool_use_id"
category: anthropic-api
tags:
  - anthropic-api
  - tool-use
  - tool-result
symptoms:
  - "tool_result block(s) provided when previous message does not contain tool_use"
  - "Each tool_result must have a tool_use_id matching a prior tool_use"
root_cause: "Tool results are delivered as a `tool_result` content block inside a `user` message, and each must carry the `tool_use_id` of the corresponding `tool_use` block from the previous assistant turn."
fix: "After the assistant returns `tool_use`, append a user message whose content is one `tool_result` block per `tool_use`, each with the right `tool_use_id`."
verified_count: 0
created: 2026-05-28
---

## Correct shape

```json
{"role": "user", "content": [
  {"type": "tool_result", "tool_use_id": "toolu_abc", "content": "42"}
]}
```

Order of results does not matter; the `tool_use_id` linkage does.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
