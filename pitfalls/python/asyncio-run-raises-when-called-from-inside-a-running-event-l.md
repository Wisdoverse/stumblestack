---
id: 1cf67936-24fc-4392-818a-fec6806903d4
title: "asyncio.run() raises when called from inside a running event loop"
category: python
tags:
  - python
  - asyncio
  - event-loop
symptoms:
  - "RuntimeError: asyncio.run() cannot be called from a running event loop"
  - "This event loop is already running"
root_cause: "`asyncio.run()` creates and manages a new loop; calling it while a loop is already running (Jupyter, an async framework, a nested call) errors."
fix: "Inside a running loop, `await` the coroutine directly, or use a task. Only call `asyncio.run()` at the top level of a sync program."
verified_count: 0
created: 2026-05-28
---

```python
# inside async context
result = await my_coro()
# top-level sync entrypoint only:
asyncio.run(main())
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
