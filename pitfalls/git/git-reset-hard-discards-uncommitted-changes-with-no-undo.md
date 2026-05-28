---
id: 01293083-6896-4daf-b71e-2a8ceb1541c4
title: "git reset --hard discards uncommitted changes with no undo"
category: git
tags:
  - git
  - reset
  - data-loss
symptoms:
  - "uncommitted edits gone after a reset"
  - "working tree reverted unexpectedly"
root_cause: "`git reset --hard` overwrites the working tree and index to match the target commit, throwing away uncommitted changes. They are not in any commit, so reflog cannot recover them."
fix: "Stash or commit first. Use `git stash` or a WIP commit before a hard reset; prefer `git restore`/`git checkout --` for scoped reverts."
verified_count: 0
created: 2026-05-28
---

```bash
git stash push -m wip   # safety net
git reset --hard origin/main
# recover if needed:
git stash pop
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
