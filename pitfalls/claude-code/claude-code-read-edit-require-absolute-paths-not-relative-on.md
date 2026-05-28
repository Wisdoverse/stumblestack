---
id: 482abe33-28ab-4832-8f3b-899b3fda6d35
title: "Claude Code Read/Edit require absolute paths, not relative ones"
category: claude-code
tags:
  - claude-code
  - tools
  - paths
symptoms:
  - "file_path must be absolute"
  - "relative path rejected by Read/Edit"
root_cause: "The Read, Edit, and Write tools require an absolute `file_path`. Relative paths are rejected."
fix: "Pass an absolute path. Resolve against the known working directory if you only have a relative one."
verified_count: 0
created: 2026-05-28
---

Use `/abs/path/to/file`, not `./file` or `src/file.py`, in Read/Edit/Write.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
