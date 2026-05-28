---
id: 88507e60-b9a8-4441-a7bc-3f598e8a01e9
title: "Anthropic Messages API rejects a system prompt sent as a role:system message"
category: anthropic-api
tags:
  - anthropic-api
  - messages
  - system-prompt
symptoms:
  - "messages: Input should be 'user' or 'assistant'"
  - "system role is not supported in the messages array"
root_cause: "The Messages API takes the system prompt as a top-level `system` parameter, not as an entry in the `messages` array. Only `user` and `assistant` roles are valid inside `messages`."
fix: "Move the system prompt to the top-level `system=` argument."
verified_count: 0
created: 2026-05-28
---

## Wrong

```python
client.messages.create(
    model="claude-opus-4-1",
    messages=[
        {"role": "system", "content": "You are terse."},
        {"role": "user", "content": "Hi"},
    ],
)
```

## Correct

```python
client.messages.create(
    model="claude-opus-4-1",
    system="You are terse.",
    messages=[{"role": "user", "content": "Hi"}],
    max_tokens=1024,
)
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
