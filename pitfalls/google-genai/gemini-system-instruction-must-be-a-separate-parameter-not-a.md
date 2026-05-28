---
id: 47e5ce9a-a824-4a68-ae9a-b6e9254e72fd
title: "Gemini system instruction must be a separate parameter, not a contents entry"
category: google-genai
tags:
  - google-genai
  - gemini
  - system-instruction
symptoms:
  - "system instruction ignored when placed in contents"
  - "model does not follow the system prompt"
root_cause: "Gemini takes the system prompt via `system_instruction` on the model/config, not as a turn in `contents`. A 'system' turn in `contents` is invalid or ignored."
fix: "Pass `system_instruction` when constructing the model or in the generation config."
verified_count: 0
model_version: "Gemini (2025)"
created: 2026-05-28
---

```python
model = genai.GenerativeModel(
    "gemini-2.5-pro",
    system_instruction="You are terse.",
)
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
