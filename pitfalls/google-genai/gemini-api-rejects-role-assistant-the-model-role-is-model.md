---
id: f510deea-98fb-4fc0-ad9b-547500f541e1
title: "Gemini API rejects role 'assistant'; the model role is 'model'"
category: google-genai
tags:
  - google-genai
  - gemini
  - roles
symptoms:
  - "Please use a valid role: user, model."
  - "400 INVALID_ARGUMENT on contents role"
root_cause: "The Gemini API uses `user` and `model` as the two conversation roles. `assistant` (the OpenAI/Anthropic name) is invalid."
fix: "Map assistant turns to role `model` when constructing `contents`."
verified_count: 0
model_version: "Gemini (2025)"
created: 2026-05-28
---

```python
contents = [
  {"role": "user", "parts": [{"text": "Hi"}]},
  {"role": "model", "parts": [{"text": "Hello"}]},
]
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
