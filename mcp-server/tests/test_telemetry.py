"""Opt-in telemetry (A24): default-off, PII-free, fail-open."""
from __future__ import annotations

import json

from stumblestack_mcp import telemetry


def test_disabled_by_default(monkeypatch, capsys):
    monkeypatch.delenv("STUMBLESTACK_TELEMETRY", raising=False)
    assert telemetry.enabled() is False
    telemetry.emit("search_pitfalls", latency_ms=1.0, result_count=3, cache_age_seconds=0, ok=True)
    assert capsys.readouterr().err == ""


def test_enable_parsing(monkeypatch):
    for v in ("1", "true", "YES", "on"):
        monkeypatch.setenv("STUMBLESTACK_TELEMETRY", v)
        assert telemetry.enabled() is True
    for v in ("0", "false", "", "off"):
        monkeypatch.setenv("STUMBLESTACK_TELEMETRY", v)
        assert telemetry.enabled() is False


def test_emits_exactly_seven_keys_to_stderr(monkeypatch, capsys):
    monkeypatch.setenv("STUMBLESTACK_TELEMETRY", "1")
    telemetry.emit("get_pitfall", latency_ms=12.345, result_count=1, cache_age_seconds=42, ok=True)
    err = capsys.readouterr().err.strip()
    rec = json.loads(err)
    assert set(rec) == {"event", "tool", "latency_ms", "result_count", "cache_age_seconds", "ok"}
    assert rec["tool"] == "get_pitfall"
    assert rec["latency_ms"] == 12.35  # rounded
    # No query / id / content fields leak.
    assert "query" not in rec and "id" not in rec


def test_fail_open(monkeypatch, capsys):
    monkeypatch.setenv("STUMBLESTACK_TELEMETRY", "1")
    # A non-serializable result_count type must not raise.
    telemetry.emit("x", latency_ms=1.0, result_count=None, cache_age_seconds=None, ok=False)
    # No exception => pass; line still emitted with nulls.
    rec = json.loads(capsys.readouterr().err.strip())
    assert rec["result_count"] is None and rec["ok"] is False
