---
id: 64993e80-f4cc-4843-9b7a-7cfaf23d7a62
title: "Claude Code Bash: exported env vars and cd do not persist across separate Bash calls for shell state"
category: claude-code
tags:
  - claude-code
  - bash
  - shell-state
symptoms:
  - "environment variable set in one command is empty in the next"
  - "a function defined earlier is not found later"
root_cause: "Each Bash tool call starts a fresh shell initialized from the profile. The working directory persists between calls, but shell state — exported env vars, shell functions, `set` options — does not."
fix: "Set env vars inline in the same command that needs them, or chain with `&&`. Do not rely on `export` carrying to a later call."
verified_count: 0
created: 2026-05-28
---

## Wrong (two calls)

```bash
export TOKEN=abc      # call 1
```
```bash
curl -H "$TOKEN" ...  # call 2 -> TOKEN empty
```

## Correct (one call)

```bash
TOKEN=abc curl -H "Authorization: Bearer $TOKEN" ...
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
