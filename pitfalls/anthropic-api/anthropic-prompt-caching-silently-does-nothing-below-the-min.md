---
id: 1b30d861-0777-4234-8689-8f07a158c8eb
title: "Anthropic prompt caching silently does nothing below the minimum cacheable length"
category: anthropic-api
tags:
  - anthropic-api
  - prompt-caching
  - performance
symptoms:
  - "cache_creation_input_tokens is 0"
  - "no cache hit despite cache_control set"
  - "prompt caching has no effect on cost"
root_cause: "A `cache_control` breakpoint only creates a cache entry when the prefix up to that point meets the model's minimum: ~1024 tokens for Opus/Sonnet and ~2048 tokens for Haiku. Shorter prefixes are silently not cached."
fix: "Place the cache breakpoint after a prefix that exceeds the minimum, and verify via `usage.cache_creation_input_tokens` / `cache_read_input_tokens` in the response."
verified_count: 0
created: 2026-05-28
---

## Symptom

You set `cache_control` on a small system prompt and see no cost reduction.

## Why

The cached prefix must be long enough. Check the response usage block:

```json
{"usage": {"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}
```

Zeros mean nothing was cached.

## Fix

Cache large, stable prefixes (long system prompts, tool definitions, documents). Put the breakpoint at the end of the stable region.

---

_Curated seed entry. Not yet independently reproduced via the PR flow (`verified_count: 0`)._
