---
id: ff3e3d7f-bf91-4a42-b59c-6e1056682714
title: "CMD in shell form does not forward SIGTERM, so the container ignores graceful shutdown"
category: docker
tags:
  - docker
  - signals
  - pid1
symptoms:
  - "container takes 10s to stop then is SIGKILLed"
  - "app never receives SIGTERM"
root_cause: "Shell-form `CMD app` runs the process as a child of `/bin/sh`, which is PID 1 and does not forward signals. `docker stop` sends SIGTERM to PID 1 (the shell), not your app."
fix: "Use exec form `CMD [\"app\", \"arg\"]` so the app is PID 1, or add an init like `tini`."
verified_count: 0
created: 2026-05-28
---

## Wrong

```dockerfile
CMD node server.js        # shell form
```

## Correct

```dockerfile
CMD ["node", "server.js"]  # exec form, app is PID 1
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
