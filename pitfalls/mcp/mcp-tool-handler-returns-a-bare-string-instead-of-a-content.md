---
id: 61811aca-c838-421e-8c3f-77a0299ee235
title: "MCP tool handler returns a bare string instead of a content list"
category: mcp
tags:
  - mcp
  - tools
  - content
symptoms:
  - "validation error: content is not a list"
  - "client shows nothing for a tool that 'worked'"
root_cause: "An MCP `call_tool` handler must return a list of content blocks (e.g. `TextContent`), not a raw string or dict. A bare return value fails validation or renders as empty."
fix: "Return `[TextContent(type='text', text=...)]` (or other content block types)."
verified_count: 0
created: 2026-05-28
---

```python
from mcp.types import TextContent

@server.call_tool()
async def call_tool(name, args):
    return [TextContent(type="text", text=json.dumps(result))]
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
