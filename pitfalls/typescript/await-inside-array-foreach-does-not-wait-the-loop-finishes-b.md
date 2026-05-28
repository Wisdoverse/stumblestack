---
id: 33d05c96-109e-4f9f-afa9-a87e8782cd74
title: "await inside Array.forEach does not wait; the loop finishes before the promises resolve"
category: typescript
tags:
  - typescript
  - javascript
  - async
symptoms:
  - "code after a forEach runs before the async work finishes"
  - "unhandled promise rejections from a forEach callback"
root_cause: "`Array.prototype.forEach` ignores the return value of its callback, so an `async` callback's promise is never awaited. The loop returns immediately."
fix: "Use a `for...of` loop with `await`, or `await Promise.all(arr.map(async ...))` for concurrency."
verified_count: 0
created: 2026-05-28
---

## Wrong

```ts
items.forEach(async (i) => { await save(i); });
done();  // runs before saves finish
```

## Correct

```ts
for (const i of items) { await save(i); }
// or, concurrent:
await Promise.all(items.map((i) => save(i)));
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
