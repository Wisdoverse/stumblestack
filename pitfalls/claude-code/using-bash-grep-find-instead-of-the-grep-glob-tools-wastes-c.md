---
id: 3eeb4033-7140-4990-8cbd-9a6f8f2bd902
title: "Using Bash grep/find instead of the Grep/Glob tools wastes context and misses .gitignore handling"
category: claude-code
tags:
  - claude-code
  - search
  - tools
symptoms:
  - "huge bash grep output floods context"
  - "slow ad-hoc find in a large repo"
root_cause: "The dedicated Grep and Glob tools are optimized for code search (ripgrep-backed, respect ignore files, compact output). Shelling out to `grep -r`/`find` is slower and dumps noisy output into context."
fix: "Prefer the Grep and Glob tools for searching; reserve Bash for things they cannot do."
verified_count: 0
created: 2026-05-28
---

Grep for content, Glob for filename patterns. They return compact, relevant results.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
