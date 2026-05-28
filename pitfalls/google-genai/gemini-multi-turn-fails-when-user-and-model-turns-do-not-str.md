---
id: fff89f12-f0cd-4a87-b1eb-ca7340569a70
title: "Gemini multi-turn fails when user and model turns do not strictly alternate"
category: google-genai
tags:
  - google-genai
  - gemini
  - conversation
symptoms:
  - "Please ensure that multiturn requests alternate between user and model."
  - "400 on contents with consecutive same-role turns"
root_cause: "Gemini requires `contents` to alternate user/model. Two consecutive user turns (e.g. a system-ish preamble plus the real question both as `user`) are rejected."
fix: "Merge consecutive same-role turns into one, or interleave correctly. Put steering in `system_instruction` instead of a second user turn."
verified_count: 0
model_version: "Gemini (2025)"
created: 2026-05-28
---

Collapse adjacent user parts into a single user turn before sending.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
