#!/usr/bin/env python3
"""A28 — compare the locally rebuilt index.json against the main branch's published
copy and fail if the new entry count is more than 10% lower.

This protects against:
  - a PR that accidentally deletes a category directory,
  - a schema bump that silently drops records from the projection,
  - a build_index.py regression that crashes mid-walk.

Override the threshold with --max-drop-percent (default 10).

The published comparison source defaults to
https://stumblestack.dev/index.json. Override with STUMBLESTACK_BASELINE_URL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

DEFAULT_BASELINE = os.environ.get(
    "STUMBLESTACK_BASELINE_URL",
    "https://stumblestack.dev/index.json",
)


def _fetch_baseline_count(url: str) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.load(r)
    except Exception as exc:
        print(f"index_check: baseline fetch failed ({exc}); skipping comparison.")
        return None
    if not isinstance(data, dict):
        return None
    return int(data.get("count") or 0)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--new", default="index.json", help="Path to locally built index.json")
    p.add_argument("--baseline-url", default=DEFAULT_BASELINE)
    p.add_argument("--max-drop-percent", type=float, default=10.0)
    args = p.parse_args()

    new_path = Path(args.new)
    if not new_path.exists():
        print(f"index_check: {new_path} not found")
        return 1
    new_count = int(json.loads(new_path.read_text(encoding="utf-8")).get("count") or 0)

    baseline = _fetch_baseline_count(args.baseline_url)
    if baseline is None:
        print(f"index_check: ok (baseline unavailable). new count = {new_count}")
        return 0
    if baseline == 0:
        print(f"index_check: ok (baseline empty). new count = {new_count}")
        return 0

    drop_pct = (baseline - new_count) / baseline * 100.0
    print(f"index_check: baseline={baseline} new={new_count} drop={drop_pct:.1f}%")
    if drop_pct > args.max_drop_percent:
        print(
            f"::error::index.json entry count dropped {drop_pct:.1f}% (baseline {baseline}, "
            f"new {new_count}); threshold is {args.max_drop_percent:.1f}%. "
            "If this drop is intentional, set --max-drop-percent higher in this run."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
