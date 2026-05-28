#!/usr/bin/env python3
"""A19/A25 — build the public aggregate stats file (_stats.json).

Deterministic: the build reads index.json only and NEVER touches the wall clock.
The single time value (`generated_at`) is injected via --now so two runs with the
same corpus + same --now are byte-identical. The CI workflow is the only place a
clock is read (it passes `date -u` into --now).

Output (default <root>/_site/_stats.json):
  {
    "generated_at": "<--now, Z-normalized>",
    "last_updated": "<latest entry date in the corpus>",
    "total_entries": N,
    "categories": [{"category": ..., "count": ...}, ...],   # sorted -count, name
    "top_tags": [{"tag": ..., "count": ...}, ...],           # top 20
    "severity": {"blocker": n, ...},                          # counts (omit absent)
    "verified_entries": M
  }

Usage: python scripts/build_stats.py --now 2026-05-28T00:00:00Z [--index index.json] [--out _site/_stats.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path


def _normalize_now(value: str) -> str:
    v = value.strip()
    if not v:
        raise SystemExit("build_stats: --now must be a non-empty ISO-8601 timestamp")
    # Normalize a trailing +00:00 to Z; otherwise pass through unchanged (no clock read).
    if v.endswith("+00:00"):
        v = v[: -len("+00:00")] + "Z"
    return v


def build_stats(index: dict, now: str) -> dict:
    entries = index.get("entries", [])
    cat_counts = collections.Counter(e.get("category") or "uncategorized" for e in entries)
    tag_counts: collections.Counter[str] = collections.Counter()
    sev_counts: collections.Counter[str] = collections.Counter()
    verified = 0
    dates = []
    for e in entries:
        for t in e.get("tags") or []:
            tag_counts[t] += 1
        if e.get("severity"):
            sev_counts[e["severity"]] += 1
        if (e.get("verified_count") or 0) > 0:
            verified += 1
        d = e.get("updated") or e.get("created")
        if d:
            dates.append(str(d))

    return {
        "generated_at": now,
        "last_updated": max(dates) if dates else "",
        "total_entries": len(entries),
        "categories": [
            {"category": c, "count": n}
            for c, n in sorted(cat_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "top_tags": [
            {"tag": t, "count": n}
            for t, n in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
        ],
        "severity": dict(sorted(sev_counts.items())),
        "verified_entries": verified,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--now", required=True, help="ISO-8601 timestamp (injected; no clock is read)")
    p.add_argument("--index", default="index.json")
    p.add_argument("--out", default=None, help="default: <index dir>/_site/_stats.json")
    args = p.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        sys.stderr.write(f"build_stats: {index_path} not found\n")
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))

    stats = build_stats(index, _normalize_now(args.now))
    out = Path(args.out) if args.out else index_path.parent / "_site" / "_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} (total_entries={stats['total_entries']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
