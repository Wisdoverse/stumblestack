---
id: abde2fca-8a5a-43fa-81eb-65826fc23d2f
title: "Blindly retrying non-idempotent HTTP requests duplicates side effects"
category: http
tags:
  - http
  - retry
  - idempotency
symptoms:
  - "duplicate charges or records after a retry"
  - "double POST on timeout"
root_cause: "Retrying a POST/PATCH that timed out can execute the action twice if the first attempt actually succeeded server-side. Only idempotent methods (GET, PUT, DELETE) are safe to retry blindly."
fix: "Retry idempotent methods freely; for non-idempotent ones, use an idempotency key so the server dedupes."
verified_count: 0
created: 2026-05-28
---

```
POST /charges
Idempotency-Key: 0f3c...   # server returns the original result on retry
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
