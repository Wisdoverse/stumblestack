---
id: 34cd7f75-ca5d-4054-9610-7d65d4dc5de1
title: "git push --force clobbers a teammate's commits; --force-with-lease would have refused"
category: git
tags:
  - git
  - push
  - force
symptoms:
  - "a colleague's commits disappeared from the remote branch"
  - "remote history rewritten over someone else's work"
root_cause: "`git push --force` overwrites the remote ref unconditionally, even if someone pushed after your last fetch. Their commits are lost from the branch tip."
fix: "Use `git push --force-with-lease`, which refuses if the remote moved since your last fetch."
verified_count: 0
created: 2026-05-28
---

```bash
git push --force-with-lease origin feature
```

`--force-with-lease` only overwrites if the remote is where you last saw it, turning a silent clobber into a safe rejection.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
