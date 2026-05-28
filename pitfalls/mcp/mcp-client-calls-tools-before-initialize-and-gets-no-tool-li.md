---
id: 2baa0712-b832-4b56-a8c0-8b7519758c06
title: "MCP client calls tools before initialize and gets no tool list"
category: mcp
tags:
  - mcp
  - handshake
  - initialize
symptoms:
  - "tools/list returns empty before initialize"
  - "server rejects requests until initialized"
root_cause: "The MCP lifecycle requires the `initialize` request/response handshake before any `tools/list` or `tools/call`. Skipping it yields empty or rejected responses."
fix: "Complete `initialize` (and send `initialized` notification) before issuing tool calls. Most client SDKs expose `session.initialize()`."
verified_count: 0
created: 2026-05-28
---

```python
async with ClientSession(read, write) as session:
    await session.initialize()   # required first
    tools = await session.list_tools()
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
