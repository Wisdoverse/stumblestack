---
id: 8007305a-6b8e-49eb-87a0-4d56eac9583a
title: "OpenAI reasoning models reject max_tokens; they require max_completion_tokens"
category: openai-api
tags:
  - openai-api
  - reasoning-models
  - max-tokens
symptoms:
  - "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead."
  - "400 invalid_request_error on o1/o3/o4 calls"
root_cause: "Reasoning models (o1, o3, o4 family) count hidden reasoning tokens toward output and replaced `max_tokens` with `max_completion_tokens`, which bounds reasoning + visible output together."
fix: "Use `max_completion_tokens` for reasoning models. Budget extra headroom because reasoning tokens are consumed before any visible output."
verified_count: 0
model_version: "o1 / o3 / o4 (2025+)"
status: active
observed_on:
  - "o1"
  - "o3"
  - "o4"
last_verified: 2026-05-29
created: 2026-05-28
---

## Wrong

```python
client.chat.completions.create(model="o3", max_tokens=500, messages=[...])
```

## Correct

```python
client.chat.completions.create(model="o3", max_completion_tokens=4000, messages=[...])
```

If `max_completion_tokens` is too small, the visible answer can come back empty because reasoning ate the whole budget.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
