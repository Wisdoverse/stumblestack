---
id: 7586d573-6202-4761-8b1e-a1177a5e5e42
title: "Anthropic vision request fails without media_type on a base64 image source"
category: anthropic-api
tags:
  - anthropic-api
  - vision
  - images
symptoms:
  - "messages.X.content.Y.image.source.media_type: Field required"
  - "image not accepted"
root_cause: "An image content block with `source.type=base64` requires both `media_type` (e.g. image/png) and base64 `data`. Omitting `media_type` is rejected."
fix: "Provide `media_type` matching the image bytes alongside the base64 `data`."
verified_count: 0
created: 2026-05-28
---

```python
{"type": "image", "source": {
  "type": "base64", "media_type": "image/png", "data": b64}}
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
