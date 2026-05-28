---
id: c1c83eb0-8e0d-4cda-93d2-5a4b29a820f5
title: "Setting seed does not guarantee identical OpenAI completions"
category: openai-api
tags:
  - openai-api
  - determinism
  - seed
symptoms:
  - "outputs differ run-to-run despite a fixed seed"
root_cause: "`seed` makes sampling best-effort reproducible but is not a hard guarantee; backend changes shift `system_fingerprint` and outputs can still vary."
fix: "Treat `seed` as best-effort. Compare `system_fingerprint` across runs; for hard determinism, cache results or post-process."
verified_count: 0
created: 2026-05-28
---

Check `response.system_fingerprint`; a change signals the backend moved and reproducibility is not guaranteed.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
