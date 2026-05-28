---
id: 9e6f11d9-09b8-461f-a1a2-6b3484486837
title: "set -e does not abort on a failing command in the middle of a pipeline"
category: shell
tags:
  - shell
  - bash
  - error-handling
symptoms:
  - "script continues after a piped command failed"
  - "exit code of the pipeline is 0 despite an upstream failure"
root_cause: "Under `set -e`, only the pipeline's last command's exit status matters by default. A failure in `cmd1 | cmd2` is hidden if `cmd2` succeeds."
fix: "Add `set -o pipefail` (with `set -e`) so any pipeline element's failure fails the pipeline."
verified_count: 0
created: 2026-05-28
---

```bash
set -euo pipefail
false | cat   # now fails the script; without pipefail it would not
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
