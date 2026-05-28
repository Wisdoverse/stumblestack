---
id: ae3a19f6-7d93-4f17-9db0-63108ee018e0
title: "JSON.parse returns any, erasing type safety on external data"
category: typescript
tags:
  - typescript
  - json
  - validation
symptoms:
  - "runtime shape errors on parsed JSON that 'typechecked'"
  - "undefined property access on API responses"
root_cause: "`JSON.parse` is typed as returning `any`, so the compiler trusts whatever type you assert. Malformed or unexpected payloads pass typechecking and explode at runtime."
fix: "Validate parsed data at the boundary with a schema validator (zod, valibot, io-ts) instead of a bare type assertion."
verified_count: 0
created: 2026-05-28
---

```ts
const data = MySchema.parse(JSON.parse(raw));  // throws on mismatch
// not: const data = JSON.parse(raw) as MyType;
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
