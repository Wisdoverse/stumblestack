---
id: 33b311c7-9dc1-4b02-a67a-d30a14dab6b4
title: "Assistant message prefill fails when the content ends with trailing whitespace"
category: anthropic-api
tags:
  - anthropic-api
  - prefill
  - assistant-turn
symptoms:
  - "final assistant content block must not end with trailing whitespace"
  - "messages: assistant message cannot have trailing whitespace"
root_cause: "When you prefill the assistant turn (to constrain output), the Messages API rejects a final assistant text block that ends in whitespace or a newline."
fix: "Strip trailing whitespace from the prefill string before sending."
verified_count: 0
created: 2026-05-28
---

## Wrong

```python
messages=[{"role": "user", "content": "List 3"},
          {"role": "assistant", "content": "1. "}]  # trailing space -> 400
```

## Correct

```python
{"role": "assistant", "content": "1."}
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
