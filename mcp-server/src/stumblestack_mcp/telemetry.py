"""A24 — opt-in, PII-free telemetry for the MCP server.

Disabled by default. Enable by setting STUMBLESTACK_TELEMETRY to a truthy value
(1/true/yes/on). When enabled, the server emits ONE structured JSON line per tool
call to stderr (never stdout — that is the JSON-RPC channel). The payload carries
no query text, ids, or any user content — only the tool name, latency, result
count, cache age, and an ok flag. Emission is fail-open: a telemetry error never
affects the tool result.
"""
from __future__ import annotations

import json
import os
import sys

_TRUTHY = {"1", "true", "yes", "on"}

# Exactly these keys are emitted. No field can carry user content / PII.
_KEYS = ("event", "tool", "latency_ms", "result_count", "cache_age_seconds", "ok")


def enabled() -> bool:
    return os.environ.get("STUMBLESTACK_TELEMETRY", "").strip().lower() in _TRUTHY


def emit(
    tool: str,
    *,
    latency_ms: float,
    result_count: int | None,
    cache_age_seconds: int | None,
    ok: bool,
) -> None:
    """Emit one telemetry line to stderr. No-op when disabled; never raises."""
    if not enabled():
        return
    try:
        record = {
            "event": "stumblestack.tool_call",
            "tool": tool,
            "latency_ms": round(latency_ms, 2),
            "result_count": result_count,
            "cache_age_seconds": cache_age_seconds,
            "ok": ok,
        }
        # Defensive: only ever serialize the allowlisted keys.
        line = json.dumps({k: record[k] for k in _KEYS}, ensure_ascii=False)
        print(line, file=sys.stderr, flush=True)
    except Exception:
        # Telemetry must never break a tool call.
        pass
