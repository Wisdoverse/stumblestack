---
id: 406a4aa7-3719-4a9a-8415-3657a581c293
title: "datetime.utcnow() returns a naive datetime and is deprecated"
category: python
tags:
  - python
  - datetime
  - timezone
symptoms:
  - "DeprecationWarning: datetime.datetime.utcnow() is deprecated"
  - "naive datetime compared to aware datetime raises TypeError"
root_cause: "`datetime.utcnow()` returns a timezone-naive object that nonetheless represents UTC, causing silent bugs and TypeErrors when mixed with aware datetimes. It is deprecated in modern Python."
fix: "Use `datetime.now(timezone.utc)` for an aware UTC timestamp."
verified_count: 0
created: 2026-05-28
---

```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc)   # aware, correct
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
