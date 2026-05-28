---
id: 52c01301-df3d-40ac-b639-73452d0eca76
title: "Piping a remote script straight into a shell runs unverified code as you"
category: shell
tags:
  - shell
  - security
  - supply-chain
symptoms:
  - "arbitrary code execution from a compromised or MITM'd installer URL"
root_cause: "`curl … | sh` executes whatever the server returns, with no chance to inspect it, and a partial download can execute half a script. A compromised host or hijacked TLS becomes code execution on your machine."
fix: "Download to a file, read it, verify a checksum or signature, then run it."
verified_count: 0
fix_unsafe: true
created: 2026-05-28
---

## Risky

```bash
curl https://example.com/install.sh | sh
```

## Safer

```bash
curl -fsSLo install.sh https://example.com/install.sh
sha256sum -c install.sh.sha256
less install.sh   # inspect
sh install.sh
```

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
