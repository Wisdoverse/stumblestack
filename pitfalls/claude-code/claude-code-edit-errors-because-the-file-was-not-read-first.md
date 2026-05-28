---
id: 24353f30-491e-46e5-9396-d669ca0b1317
title: "Claude Code Edit errors because the file was not Read first in the session"
category: claude-code
tags:
  - claude-code
  - tools
  - edit
  - read
symptoms:
  - "Edit failed: file has not been read"
  - "you must read the file before editing it"
root_cause: "The Edit tool requires the file to have been Read earlier in the same session so the harness can verify the pre-edit content. Editing an unread file is refused."
fix: "Read the file once before the first Edit. No need to re-read between successive edits the harness has tracked."
verified_count: 0
created: 2026-05-28
---

Read → Edit. After a successful Edit the harness knows the new state; a redundant re-read just to 'verify' is unnecessary.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
