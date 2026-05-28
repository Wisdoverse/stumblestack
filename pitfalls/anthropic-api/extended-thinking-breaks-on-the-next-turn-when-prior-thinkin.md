---
id: abd63bb2-3ac4-4210-be89-ff23eb33073a
title: "Extended thinking breaks on the next turn when prior thinking blocks are dropped"
category: anthropic-api
tags:
  - anthropic-api
  - extended-thinking
  - tool-use
symptoms:
  - "messages.X.content: thinking block is required"
  - "Expected `thinking` block before tool_use when extended thinking is enabled"
root_cause: "When extended thinking is enabled together with tool use, the assistant's `thinking` (and `redacted_thinking`) blocks from a turn must be passed back verbatim in the conversation history for subsequent turns. Stripping them to 'save tokens' invalidates the turn."
fix: "Echo the complete assistant content array — including `thinking` blocks — back into `messages` on the following request."
verified_count: 0
model_version: "claude (extended thinking, 2025+)"
created: 2026-05-28
---

## Why

The model signs thinking blocks and expects them intact to continue a tool-use loop. Removing them breaks signature verification.

## Fix

Append the assistant message exactly as returned (all blocks), then add the `tool_result` in a new user message.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
