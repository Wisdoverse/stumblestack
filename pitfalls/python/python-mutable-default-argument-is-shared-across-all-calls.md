---
id: c46c7cb8-444d-4237-b880-48e22cf10a1b
title: "Python mutable default argument is shared across all calls"
category: python
tags:
  - python
  - gotcha
  - functions
symptoms:
  - "a list/dict default 'remembers' values between calls"
  - "unexpected accumulation in a default argument"
root_cause: "Default argument values are evaluated once at function definition, so a mutable default (`[]`, `{}`) is shared by every call that uses the default."
fix: "Default to `None` and create the mutable inside the function."
verified_count: 0
created: 2026-05-28
---

## Wrong

```python
def f(x, acc=[]):
    acc.append(x); return acc   # acc persists!
```

## Correct

```python
def f(x, acc=None):
    acc = [] if acc is None else acc
    acc.append(x); return acc
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
