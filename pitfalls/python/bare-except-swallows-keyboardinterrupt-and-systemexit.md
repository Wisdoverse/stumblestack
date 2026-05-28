---
id: 224cb5e7-3e84-445c-b777-c22ee6f1839d
title: "Bare 'except:' swallows KeyboardInterrupt and SystemExit"
category: python
tags:
  - python
  - exceptions
  - gotcha
symptoms:
  - "Ctrl-C does not stop the program"
  - "process won't exit cleanly"
root_cause: "A bare `except:` (or `except BaseException`) catches `KeyboardInterrupt` and `SystemExit`, which inherit from `BaseException`, not `Exception`. Control-C gets swallowed."
fix: "Catch `except Exception:` for normal error handling; let `BaseException` propagate."
verified_count: 0
created: 2026-05-28
---

## Wrong

```python
try:
    work()
except:        # catches Ctrl-C too
    log()
```

## Correct

```python
except Exception:
    log()
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
