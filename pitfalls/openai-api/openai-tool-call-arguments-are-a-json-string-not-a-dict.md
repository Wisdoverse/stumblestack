---
id: ca1da3d4-b1e4-4f0f-adb3-f4377cdef23a
title: "OpenAI tool-call arguments are a JSON string, not a dict"
category: openai-api
tags:
  - openai-api
  - tool-calls
  - function-calling
symptoms:
  - "TypeError: string indices must be integers"
  - "treating arguments as a dict raises"
root_cause: "`tool_calls[].function.arguments` is always a JSON-encoded string, even in non-streaming responses. It is never pre-parsed into an object."
fix: "Call `json.loads()` on `arguments` before using it."
verified_count: 0
created: 2026-05-28
---

```python
args = json.loads(tool_call.function.arguments)
```

The model can also emit invalid JSON; wrap the parse in error handling and consider Structured Outputs / strict function schemas.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
