---
id: 93f4fb49-5a74-4906-9564-079c7081d34f
title: "Missing .dockerignore sends the whole working tree as build context"
category: docker
tags:
  - docker
  - dockerignore
  - build-context
symptoms:
  - "docker build is slow and uploads gigabytes of context"
  - "node_modules or .git copied into the image"
root_cause: "Without a `.dockerignore`, `docker build` sends everything in the context dir to the daemon, and `COPY . .` can pull in `.git`, `node_modules`, caches, and secrets."
fix: "Add a `.dockerignore` excluding VCS, dependencies, build artifacts, and secrets."
verified_count: 0
created: 2026-05-28
---

```
.git
node_modules
*.log
.env
dist
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
