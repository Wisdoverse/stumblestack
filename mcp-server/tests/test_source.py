"""Mirror chain, failover, and TTL cache (source.py)."""
from __future__ import annotations

import json

import httpx
import pytest

from stumblestack_mcp.source import Mirror, StumblestackSource


# ── Mirror invariants ──
def test_mirror_requires_exactly_one_backing():
    with pytest.raises(ValueError):
        Mirror(label="x", local=None, base_url=None)
    with pytest.raises(ValueError):
        Mirror(label="x", local=__import__("pathlib").Path("/tmp"), base_url="https://h")


def test_mirror_rejects_trailing_slash():
    with pytest.raises(ValueError):
        Mirror(label="x", local=None, base_url="https://h/")


# ── chain construction ──
def test_chain_from_env(monkeypatch):
    monkeypatch.setenv("STUMBLESTACK_MIRRORS", "owner/repo@dev, https://m1.test/base")
    monkeypatch.setenv("STUMBLESTACK_REMOTE", "other/repo")
    s = StumblestackSource.from_env()
    chain = s.mirrors()
    # first two are the explicit mirrors, then remote, then canonical, then github fallback
    assert chain[0].startswith("github:owner/repo@dev")
    assert "https://m1.test/base" in chain
    assert any("stumblestack.dev" in m for m in chain)


def test_local_repo_short_circuits(tmp_path):
    s = StumblestackSource(local_path=tmp_path)
    assert s.mirrors() == [f"local:{tmp_path}"]


def test_missing_local_repo_raises_clearly(tmp_path):
    with pytest.raises(RuntimeError, match="does not point to an existing directory"):
        StumblestackSource(local_path=tmp_path / "nope")


def test_bad_ttl_raises(monkeypatch):
    monkeypatch.setenv("STUMBLESTACK_TTL", "soon")
    with pytest.raises(RuntimeError, match="STUMBLESTACK_TTL"):
        StumblestackSource.from_env()


# ── failover + cache (httpx.MockTransport, fully offline) ──
def _source_with_mock(handler, ttl=3600):
    s = StumblestackSource(ttl_seconds=ttl)
    s._mirrors = [
        Mirror(label="m1", local=None, base_url="https://m1.test"),
        Mirror(label="m2", local=None, base_url="https://m2.test"),
    ]
    s._client = httpx.Client(transport=httpx.MockTransport(handler))
    return s


def test_failover_advances_on_5xx():
    idx = json.dumps({"schema_version": 1, "count": 1, "entries": [{"id": "x"}]})

    def handler(request):
        if request.url.host == "m1.test":
            return httpx.Response(503, text="down")
        return httpx.Response(200, text=idx)

    s = _source_with_mock(handler)
    data = s.index()
    assert data["count"] == 1
    assert s.origin() == "m2"
    s.close()


def test_failover_advances_on_404():
    idx = json.dumps({"schema_version": 1, "count": 2, "entries": []})

    def handler(request):
        if request.url.host == "m1.test":
            return httpx.Response(404, text="missing")
        return httpx.Response(200, text=idx)

    s = _source_with_mock(handler)
    assert s.index()["count"] == 2
    assert s.origin() == "m2"
    s.close()


def test_all_mirrors_fail_raises():
    def handler(request):
        return httpx.Response(500, text="boom")

    s = _source_with_mock(handler)
    with pytest.raises(RuntimeError, match="mirror"):
        s.index()
    s.close()


def test_ttl_cache_hit_and_force():
    calls = {"n": 0}
    idx = json.dumps({"schema_version": 1, "count": 1, "entries": []})

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, text=idx)

    s = _source_with_mock(handler, ttl=3600)
    s.index()
    s.index()  # within TTL -> served from cache, no new fetch
    assert calls["n"] == 1
    s.index(force=True)  # forced refetch
    assert calls["n"] == 2
    assert s.cache_age_seconds() is not None
    s.close()


def test_ttl_zero_always_refetches():
    calls = {"n": 0}
    idx = json.dumps({"schema_version": 1, "count": 1, "entries": []})

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, text=idx)

    s = _source_with_mock(handler, ttl=0)
    s.index()
    s.index()
    assert calls["n"] == 2
    s.close()


def test_entry_body_unknown_id_raises():
    idx = json.dumps({"schema_version": 1, "count": 1,
                      "entries": [{"id": "known", "path": "pitfalls/x/y.md"}]})

    def handler(request):
        if request.url.path.endswith("index.json"):
            return httpx.Response(200, text=idx)
        return httpx.Response(200, text="body")

    s = _source_with_mock(handler)
    with pytest.raises(KeyError):
        s.entry_body("unknown")
    s.close()
