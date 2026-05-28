---
id: 67b1c108-4517-4380-bdfe-afe185db9305
title: "Output truncated silently because stop_reason was max_tokens, not end_turn"
category: anthropic-api
tags:
  - anthropic-api
  - max-tokens
  - truncation
symptoms:
  - "response cut off mid-sentence"
  - "JSON output from the model fails to parse"
  - "stop_reason: max_tokens"
root_cause: "When generation hits the `max_tokens` ceiling, the API returns a complete, successful response whose `stop_reason` is `max_tokens`. The text is truncated but no error is raised."
fix: "Check `stop_reason` on every response. If it is `max_tokens`, raise the cap or continue the generation rather than treating the partial text as final."
verified_count: 0
created: 2026-05-28
---

## Fix

```python
resp = client.messages.create(...)
if resp.stop_reason == "max_tokens":
    # truncated — continue or raise max_tokens
    ...
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
