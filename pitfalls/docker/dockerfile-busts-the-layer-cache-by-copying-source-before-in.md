---
id: 552eae0a-c25f-413d-84d0-5b6f7673a7b6
title: "Dockerfile busts the layer cache by copying source before installing dependencies"
category: docker
tags:
  - docker
  - dockerfile
  - build-cache
symptoms:
  - "every build reinstalls all dependencies"
  - "slow Docker builds on small code changes"
root_cause: "`COPY . .` before the dependency install means any source change invalidates the install layer, so dependencies reinstall on every build."
fix: "Copy only the manifest, install, then copy the rest. The install layer then caches across source-only changes."
verified_count: 0
created: 2026-05-28
---

## Better order

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
