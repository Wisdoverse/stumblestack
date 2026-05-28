---
id: 0dcd35a6-14a9-4019-9e84-e966fc67e450
title: "Commits made on a detached HEAD are orphaned after checkout"
category: git
tags:
  - git
  - detached-head
  - data-loss
symptoms:
  - "my commits vanished after switching branches"
  - "You are in 'detached HEAD' state"
root_cause: "Committing while HEAD is detached (e.g. after `git checkout <sha>`) creates commits no branch points to. Switching away leaves them unreferenced and eventually garbage-collected."
fix: "Create a branch to keep the work: `git switch -c <name>` before or right after committing. Recover with `git reflog` if already detached."
verified_count: 0
created: 2026-05-28
---

```bash
# rescue
git reflog            # find the lost commit sha
git branch rescue <sha>
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
