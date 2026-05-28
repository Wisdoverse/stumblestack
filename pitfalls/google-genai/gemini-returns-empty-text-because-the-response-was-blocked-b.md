---
id: df2c61e7-efa3-4f4f-ac5a-344145835cb2
title: "Gemini returns empty text because the response was blocked by default safety settings"
category: google-genai
tags:
  - google-genai
  - gemini
  - safety
symptoms:
  - "response.text raises because no Part was returned"
  - "finish_reason: SAFETY"
  - "candidate has no content"
root_cause: "Gemini applies safety filters by default. When a category trips, the candidate is returned with `finish_reason=SAFETY` and no text part, so accessing `.text` raises."
fix: "Inspect `candidate.finish_reason` and `prompt_feedback` before reading text. Adjust `safety_settings` thresholds if the use case warrants it."
verified_count: 0
model_version: "Gemini (2025)"
created: 2026-05-28
---

## Fix

```python
resp = model.generate_content(prompt)
if resp.candidates[0].finish_reason.name != "STOP":
    # SAFETY / RECITATION / MAX_TOKENS — handle before .text
    ...
```

Raising thresholds (e.g. BLOCK_ONLY_HIGH) is a deliberate policy choice, not a default.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
