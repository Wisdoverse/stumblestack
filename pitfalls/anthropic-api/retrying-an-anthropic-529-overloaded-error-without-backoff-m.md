---
id: 9070a723-1641-45ef-bdc6-0004fbad78b2
title: "Retrying an Anthropic 529 overloaded_error without backoff makes the overload worse"
category: anthropic-api
tags:
  - anthropic-api
  - rate-limits
  - retry
symptoms:
  - "529 overloaded_error"
  - "Error: Overloaded"
root_cause: "A 529 means the service is temporarily overloaded. Tight retry loops add load and prolong the failure."
fix: "Retry with exponential backoff and jitter; respect `Retry-After` when present. Cap attempts."
verified_count: 0
created: 2026-05-28
---

```python
for attempt in range(5):
    try:
        return client.messages.create(...)
    except anthropic.InternalServerError:
        time.sleep(min(2 ** attempt, 30))  # + jitter
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
