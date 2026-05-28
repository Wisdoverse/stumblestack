---
id: c09d5356-bba0-47c1-8463-4bcaf52080e7
title: "Claude Code Edit fails when old_string is not unique in the file"
category: claude-code
tags:
  - claude-code
  - tools
  - edit
symptoms:
  - "Edit failed: old_string appears multiple times"
  - "found N matches for old_string; expected 1"
root_cause: "The Edit tool replaces a single unique occurrence by default. If `old_string` matches more than once, it refuses rather than guess."
fix: "Add enough surrounding context to make `old_string` unique, or pass `replace_all: true` when every occurrence should change."
verified_count: 0
created: 2026-05-28
---

## Fix options

- Include neighboring lines so the match is unique.
- Use `replace_all: true` for a mechanical rename across all occurrences.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
