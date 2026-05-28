---
id: 7a2ba103-4b26-4078-928c-18fc9d555a47
title: "Anthropic Messages API request fails because max_tokens was omitted"
category: anthropic-api
tags:
  - anthropic-api
  - messages
  - max-tokens
symptoms:
  - "max_tokens: Field required"
  - "TypeError: create() missing 1 required keyword-only argument: 'max_tokens'"
root_cause: "Unlike some APIs where the token cap is optional, the Anthropic Messages API requires `max_tokens` on every request."
fix: "Always pass `max_tokens`. It is the maximum to generate, not a target."
verified_count: 0
created: 2026-05-28
---

## Correct

```python
client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hi"}],
)
```

`max_tokens` bounds output only; it does not reserve or pre-bill tokens.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
