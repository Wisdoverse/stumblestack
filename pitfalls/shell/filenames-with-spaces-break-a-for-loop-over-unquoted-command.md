---
id: 48e64fec-4204-49fc-83bb-5cd150ab1873
title: "Filenames with spaces break a for loop over unquoted command substitution"
category: shell
tags:
  - shell
  - bash
  - word-splitting
symptoms:
  - "loop iterates over fragments of a filename"
  - "No such file or directory for a name that exists"
root_cause: "`for f in $(ls)` and unquoted `$(...)` split on whitespace, so a file named `my file.txt` becomes two iterations."
fix: "Avoid parsing `ls`. Use a glob, or `find … -print0` piped to `while IFS= read -r -d ''`."
verified_count: 0
created: 2026-05-28
---

## Robust

```bash
find . -type f -print0 | while IFS= read -r -d '' f; do
  printf '%s\n' "$f"
done
```

Or a simple glob: `for f in ./*.txt; do …; done` (quote `"$f"` inside).

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
