---
id: 593dbf79-bdf1-4c9d-9894-392cef412aef
title: "OpenAI JSON mode errors unless the word 'json' appears in the messages"
category: openai-api
tags:
  - openai-api
  - json-mode
  - response-format
symptoms:
  - "'messages' must contain the word 'json' in some form to use 'response_format' of type 'json_object'"
root_cause: "`response_format={'type':'json_object'}` requires the string `json` to appear somewhere in the prompt, as a guard against silent infinite-whitespace generation."
fix: "Mention JSON explicitly in a system or user message, or switch to Structured Outputs (`json_schema`) which does not need the keyword."
verified_count: 0
created: 2026-05-28
---

## Fix (json_object)

```python
response_format={"type": "json_object"}
messages=[{"role": "system", "content": "Reply with JSON."}, ...]
```

## Better — Structured Outputs

```python
response_format={"type": "json_schema", "json_schema": {...}}
```

Structured Outputs enforce the schema and do not require the keyword.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
