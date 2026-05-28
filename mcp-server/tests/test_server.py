"""Server-level tests: top_k coercion (pure) and the A8 advisory-banner contract
(end-to-end over stdio against the real local corpus)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from stumblestack_mcp import server as srv

REPO = Path(__file__).resolve().parents[2]


# ── pure: top_k coercion ──
def test_coerce_top_k_default():
    assert srv._coerce_top_k(None) == srv.DEFAULT_TOP_K


def test_coerce_top_k_clamps():
    assert srv._coerce_top_k(1000) == srv.MAX_TOP_K
    assert srv._coerce_top_k(0) == 1


def test_coerce_top_k_rejects_non_numeric():
    with pytest.raises(ValueError):
        srv._coerce_top_k("abc")


# ── A8: advisory banner present in every content-returning tool ──
def _call(tool: str, args: dict) -> dict:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    async def run():
        params = StdioServerParameters(command="stumblestack-mcp", env={"STUMBLESTACK_REPO": str(REPO)})
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                res = await session.call_tool(tool, args)
                return json.loads(res.content[0].text)

    return asyncio.run(run())


def test_banner_in_search():
    d = _call("search_pitfalls", {"query": "edit", "top_k": 1})
    assert d["advisory"].startswith("stumblestack advisory")
    assert "do not" in d["advisory"].lower() or "NOT" in d["advisory"]


def test_banner_in_get_pitfall():
    s = _call("search_pitfalls", {"query": "edit", "top_k": 1})
    pid = s["results"][0]["id"]
    d = _call("get_pitfall", {"id": pid})
    assert "advisory" in d and d["advisory"].startswith("stumblestack advisory")


def test_banner_in_get_pitfalls():
    s = _call("search_pitfalls", {"query": "edit", "top_k": 1})
    pid = s["results"][0]["id"]
    d = _call("get_pitfalls", {"ids": [pid]})
    assert "advisory" in d and d["advisory"].startswith("stumblestack advisory")
