---
id: e89f1cf7-8378-4e09-8ae3-0c11101a5c9e
title: "MCP tool inputSchema must be a JSON Schema object with type 'object' at the root"
category: mcp
tags:
  - mcp
  - tools
  - schema
symptoms:
  - "tool arguments not validated or passed"
  - "client cannot construct a form for the tool"
root_cause: "A tool's `inputSchema` must be a JSON Schema whose root `type` is `object` with a `properties` map. A non-object root (array, string) or a missing `type` prevents clients from building/validating arguments."
fix: "Define `inputSchema` as `{ 'type': 'object', 'properties': {...}, 'required': [...] }`."
verified_count: 0
created: 2026-05-28
---

```python
Tool(name="search", description="...",
     inputSchema={"type": "object",
                  "properties": {"query": {"type": "string"}},
                  "required": ["query"]})
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
