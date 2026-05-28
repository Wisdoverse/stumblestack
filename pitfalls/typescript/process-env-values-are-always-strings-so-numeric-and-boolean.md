---
id: c21d3297-878b-46f2-a4cf-a24b753d3c85
title: "process.env values are always strings, so numeric and boolean comparisons mislead"
category: typescript
tags:
  - typescript
  - node
  - env
symptoms:
  - "PORT comparison or arithmetic behaves oddly"
  - "process.env.DEBUG === true is always false"
root_cause: "Every `process.env.X` is a string or undefined. `process.env.FLAG === true` is always false; `process.env.PORT + 1` concatenates."
fix: "Coerce explicitly: `Number(process.env.PORT)`, and compare booleans against the string `'true'`."
verified_count: 0
created: 2026-05-28
---

```ts
const port = Number(process.env.PORT ?? 3000);
const debug = process.env.DEBUG === "true";
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
