---
id: 5dcbc0a5-ed7f-4b02-83bb-54faffc0be85
title: "LangChain output truncated because max_tokens defaulted too low on the chat model"
category: langchain
tags:
  - langchain
  - chat-models
  - max-tokens
symptoms:
  - "completions are cut short through LangChain but fine via the raw SDK"
  - "long generations stop early"
root_cause: "Some LangChain chat-model wrappers set a conservative default `max_tokens`. The cap silently truncates long outputs even though the underlying API would allow more."
fix: "Set `max_tokens` (or the provider-specific field) explicitly on the chat model constructor."
verified_count: 0
created: 2026-05-28
---

```python
ChatAnthropic(model="claude-sonnet-4-5", max_tokens=4096)
```

Verify the wrapper's default rather than assuming it matches the API default.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
