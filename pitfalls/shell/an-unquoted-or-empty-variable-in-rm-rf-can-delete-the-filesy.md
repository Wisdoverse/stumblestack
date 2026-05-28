---
id: 3064f3c4-bd54-4518-8d8c-673b4b05d6ec
title: "An unquoted or empty variable in rm -rf can delete the filesystem root"
category: shell
tags:
  - shell
  - rm
  - data-loss
symptoms:
  - "rm: it is dangerous to operate recursively on '/'"
  - "files outside the intended directory deleted"
root_cause: "If a variable in `rm -rf \"$DIR/\"` is empty or unset, the command expands to `rm -rf /`. Word-splitting on unquoted variables compounds the danger."
fix: "Quote variables, guard against empty values with `${VAR:?}`, and prefer `--` to terminate options."
verified_count: 0
fix_unsafe: true
created: 2026-05-28
---

## Dangerous

```bash
rm -rf $DIR/        # if DIR is empty -> rm -rf /
```

## Safer

```bash
rm -rf -- "${DIR:?DIR is unset}"/
```

`${DIR:?msg}` aborts if `DIR` is empty or unset.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
