#!/usr/bin/env python3
"""Lifecycle staleness report — the maintainer's re-verification queue.

Flags entries that likely need a human/agent to re-confirm against current models:
  - status is already non-active (fixed-upstream / superseded / unverified-stale / retired)
  - last_verified is older than --stale-days (default 180), relative to --now
  - has accumulated >= --refute-threshold not_reproduced_on entries while still active
  - is active with no last_verified at all (never confirmed)

Deterministic: the clock is injected via --now (no wall-clock read), so a CI run is
reproducible. Exit code is always 0 (advisory); use --fail-if-any for a gate.

Usage:
  python scripts/staleness_report.py --now 2026-05-29 [--index index.json]
                                     [--stale-days 180] [--refute-threshold 2] [--json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path


def _days_between(a: str, b: str) -> int | None:
    try:
        da = _dt.date.fromisoformat(str(a)[:10])
        db = _dt.date.fromisoformat(str(b)[:10])
    except (ValueError, TypeError):
        return None
    return (db - da).days


def assess(entries: list[dict], now: str, stale_days: int, refute_threshold: int) -> list[dict]:
    flagged = []
    for e in entries:
        status = e.get("status") or "active"
        reasons = []
        if status != "active":
            reasons.append(f"status={status}")
        lv = e.get("last_verified")
        if lv:
            age = _days_between(lv, now)
            if age is not None and age > stale_days:
                reasons.append(f"last_verified {age}d ago (> {stale_days})")
        else:
            # Never explicitly verified — only flag once it has AGED past the
            # threshold (by created date), so freshly-curated entries are not noise.
            created_age = _days_between(e.get("created") or "", now)
            if created_age is not None and created_age > stale_days:
                reasons.append(f"never verified and {created_age}d old (> {stale_days})")
        refutes = e.get("not_reproduced_on") or []
        if status == "active" and len(refutes) >= refute_threshold:
            reasons.append(f"{len(refutes)} refutations while still active")
        if reasons:
            flagged.append({
                "id": e.get("id"),
                "title": e.get("title"),
                "category": e.get("category"),
                "status": status,
                "model_version": e.get("model_version"),
                "last_verified": lv,
                "reasons": reasons,
            })
    flagged.sort(key=lambda r: (r.get("category") or "", r.get("id") or ""))
    return flagged


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--now", required=True, help="ISO date (injected; no clock is read)")
    p.add_argument("--index", default="index.json")
    p.add_argument("--stale-days", type=int, default=180)
    p.add_argument("--refute-threshold", type=int, default=2)
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-if-any", action="store_true", help="exit 1 if anything is flagged")
    args = p.parse_args()

    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    entries = index.get("entries", [])
    flagged = assess(entries, args.now, args.stale_days, args.refute_threshold)

    if args.json:
        print(json.dumps({"now": args.now, "flagged": flagged, "total": len(entries)}, indent=2, ensure_ascii=False))
    else:
        print(f"staleness report ({args.now}): {len(flagged)}/{len(entries)} entries need review")
        for f in flagged:
            print(f"  [{f['category']}] {f['id']}  {(f['title'] or '')[:60]}")
            for r in f["reasons"]:
                print(f"      - {r}")
        if not flagged:
            print("  none — corpus is fresh")

    if args.fail_if_any and flagged:
        sys.stderr.write(f"::warning::{len(flagged)} entries need re-verification\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
