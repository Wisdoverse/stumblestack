"""build_stats.py — deterministic aggregates, injected clock (A19/A25)."""
from __future__ import annotations

import inspect
import json

import build_stats


def _index():
    return {
        "schema_version": 1,
        "count": 3,
        "entries": [
            {"category": "git", "tags": ["git", "x"], "severity": "blocker",
             "verified_count": 1, "created": "2026-05-01"},
            {"category": "git", "tags": ["git"], "created": "2026-05-10"},
            {"category": "mcp", "tags": ["mcp", "x"], "severity": "minor",
             "verified_count": 0, "updated": "2026-05-28"},
        ],
    }


def test_aggregates():
    s = build_stats.build_stats(_index(), "2026-05-28T03:00:00Z")
    assert s["total_entries"] == 3
    assert s["last_updated"] == "2026-05-28"
    assert s["categories"][0] == {"category": "git", "count": 2}
    tags = {t["tag"]: t["count"] for t in s["top_tags"]}
    assert tags["git"] == 2 and tags["x"] == 2 and tags["mcp"] == 1
    assert s["severity"] == {"blocker": 1, "minor": 1}
    assert s["verified_entries"] == 1
    assert s["generated_at"] == "2026-05-28T03:00:00Z"


def test_deterministic_same_now():
    a = build_stats.build_stats(_index(), "2026-05-28T03:00:00Z")
    b = build_stats.build_stats(_index(), "2026-05-28T03:00:00Z")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_now_offset_normalized_to_z():
    s = build_stats.build_stats(_index(), build_stats._normalize_now("2026-05-28T03:00:00+00:00"))
    assert s["generated_at"].endswith("Z")


def test_no_clock_source_in_module():
    # The build must never read the wall clock; the timestamp is injected via --now.
    src = inspect.getsource(build_stats)
    assert "datetime.now" not in src
    assert "date.today" not in src
    assert "time.time(" not in src
