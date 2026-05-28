---
id: c44f14f3-ebd4-4ba5-b7e6-1ed6c763d5aa
title: "git clean -fdx deletes untracked files including ignored ones like .env and build caches"
category: git
tags:
  - git
  - clean
  - data-loss
symptoms:
  - ".env or local config deleted by git clean"
  - "untracked but important files removed"
root_cause: "`git clean -fdx` removes all untracked files and directories, and `-x` additionally removes git-ignored files — which often includes local `.env`, credentials, and caches you wanted to keep."
fix: "Dry-run first with `git clean -ndx` to see what would be deleted. Drop `-x` unless you truly want ignored files gone."
verified_count: 0
created: 2026-05-28
---

```bash
git clean -ndx   # n = dry run, lists targets
# review, then run without -n
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
