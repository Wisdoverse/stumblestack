---
id: 9615adbb-3603-40b5-890a-aa057d7cbf50
title: "Ignoring Retry-After on a 429 makes rate limiting worse"
category: http
tags:
  - http
  - rate-limits
  - http-429
symptoms:
  - "429 Too Many Requests in a tight loop"
  - "ban or longer backoff from the server"
root_cause: "A `429` (and some `503`) responses include a `Retry-After` header telling you when to retry. Ignoring it and hammering extends the limit window."
fix: "Honor `Retry-After` (seconds or HTTP-date); otherwise back off exponentially with jitter."
verified_count: 0
created: 2026-05-28
---

```python
if r.status_code == 429:
    wait = int(r.headers.get("Retry-After", 1))
    time.sleep(wait)
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
