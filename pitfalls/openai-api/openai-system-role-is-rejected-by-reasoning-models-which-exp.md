---
id: 8358c2d4-b1a7-4284-bc5d-9d5b5c9747b2
title: "OpenAI 'system' role is rejected by reasoning models, which expect 'developer'"
category: openai-api
tags:
  - openai-api
  - reasoning-models
  - roles
symptoms:
  - "Unsupported value: 'messages[0].role' does not support 'system' with this model"
  - "developer role expected"
root_cause: "Reasoning models renamed the steering role from `system` to `developer`. Sending `role: system` to them is rejected."
fix: "Use `role: developer` for o1/o3/o4. For chat models, `system` still works; branch on model family."
verified_count: 0
model_version: "o1 / o3 / o4 (2025+)"
created: 2026-05-28
---

```python
role = "developer" if model.startswith(("o1", "o3", "o4")) else "system"
messages = [{"role": role, "content": instructions}, ...]
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
