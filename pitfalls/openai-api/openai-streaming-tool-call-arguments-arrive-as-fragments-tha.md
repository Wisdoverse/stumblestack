---
id: 4863ac9b-c691-4c6d-9466-65e5a1f3483f
title: "OpenAI streaming tool-call arguments arrive as fragments that must be concatenated"
category: openai-api
tags:
  - openai-api
  - streaming
  - tool-calls
symptoms:
  - "json.decoder.JSONDecodeError when parsing tool call arguments"
  - "tool call arguments look truncated in streamed chunks"
root_cause: "In a streamed completion, `tool_calls[].function.arguments` is delivered as a sequence of string deltas across many chunks. Parsing any single chunk's fragment as JSON fails."
fix: "Accumulate `arguments` deltas by tool-call index until the stream finishes, then `json.loads` the concatenated string."
verified_count: 0
created: 2026-05-28
---

## Fix

```python
from collections import defaultdict
args = defaultdict(str)
for chunk in stream:
    for tc in chunk.choices[0].delta.tool_calls or []:
        if tc.function and tc.function.arguments:
            args[tc.index] += tc.function.arguments
# after stream:
parsed = {i: json.loads(s) for i, s in args.items()}
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
