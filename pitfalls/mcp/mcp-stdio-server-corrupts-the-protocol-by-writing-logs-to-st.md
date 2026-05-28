---
id: d4b238fa-7427-4a75-9f05-4d59dfc9562e
title: "MCP stdio server corrupts the protocol by writing logs to stdout"
category: mcp
tags:
  - mcp
  - stdio
  - logging
symptoms:
  - "client fails to parse server message"
  - "Unexpected token in JSON"
  - "MCP handshake hangs or errors after a print() call"
root_cause: "An MCP stdio server speaks JSON-RPC over stdout. Any stray `print()` or library log that writes to stdout interleaves with protocol frames and corrupts them."
fix: "Send all logging to stderr. Never write non-protocol bytes to stdout in a stdio server."
verified_count: 0
created: 2026-05-28
---

## Wrong

```python
print("server started")  # goes to stdout -> corrupts JSON-RPC
```

## Correct

```python
import sys
print("server started", file=sys.stderr)
# or configure logging to a stderr StreamHandler
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
