---
id: 6fc9ab6f-5c25-4094-9990-83c9b0a64ed9
title: "OpenAI reasoning models reject temperature and top_p"
category: openai-api
tags:
  - openai-api
  - reasoning-models
  - sampling
symptoms:
  - "Unsupported value: 'temperature' does not support 0.7 with this model. Only the default (1) value is supported."
  - "400 on o1/o3 when sampling params are set"
root_cause: "Reasoning models do not accept custom `temperature`, `top_p`, `presence_penalty`, or `frequency_penalty`; only default values are allowed."
fix: "Omit sampling parameters for reasoning models. Control determinism with the prompt and `seed` where supported instead."
verified_count: 0
model_version: "o1 / o3 / o4 (2025+)"
created: 2026-05-28
---

Remove `temperature`/`top_p` from the call when targeting o1/o3/o4. Code that hardcodes `temperature=0` for all models must special-case them.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
