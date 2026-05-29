#!/usr/bin/env python3
"""A13 — search quality eval harness.

Runs every {query, expected_ids} pair in eval/queries.jsonl through the same
lexical ranker the MCP server uses, and reports precision@5 and recall@10.

This is the gate for ranker changes: any PR touching the scoring in
mcp-server (search.py) or _site/assets/search.js MUST report these numbers
before and after, per docs/DESIGN.md section 9c.

Usage:
  python scripts/eval_search.py [--index index.json] [--queries eval/queries.jsonl]
                                [--min-p5 FLOAT] [--min-r10 FLOAT]

Exits non-zero if a --min threshold is set and not met.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Vendored copy of the ranker so the harness has no dependency on the installed
# MCP package. MUST stay in sync with stumblestack_mcp/search.py (DESIGN.md 9c).
_TOKEN_RE = re.compile(r"[a-z0-9]+")
FIELD_WEIGHTS = {
    "title": 3.0,
    "symptoms": 4.0,
    "_aliases": 3.5,
    "tags": 2.0,
    "root_cause": 1.5,
    "category": 1.0,
    "fix_code": 1.0,
}
# Mirror of search.STATUS_WEIGHTS (DESIGN.md 9c; parity test enforces equality).
STATUS_WEIGHTS = {
    "active": 1.0,
    "unverified-stale": 0.6,
    "fixed-upstream": 0.4,
    "superseded": 0.3,
    "retired": 0.2,
}


def _tokens(text: str):
    return _TOKEN_RE.findall(text.lower())


def _field_text(entry, field):
    v = entry.get(field)
    if v is None:
        return ""
    if field == "fix_code" and isinstance(v, dict):
        return f"{v.get('language', '')} {v.get('code', '')}".strip()
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def rank(entries, query, top_k):
    terms = _tokens(query)
    raw = query.lower().strip()
    scored = []
    for e in entries:
        score = 0.0
        for field, w in FIELD_WEIGHTS.items():
            ft = _field_text(e, field)
            if not ft:
                continue
            toks = _tokens(ft)
            for t in terms:
                c = toks.count(t)
                if c:
                    score += w * c
            if raw and raw in ft.lower():
                score += w * 2.0
        # No lexical match => excluded before the verified bonus (mirrors search.py).
        if score <= 0:
            continue
        score += min(e.get("verified_count") or 0, 10) * 0.1
        score *= STATUS_WEIGHTS.get(e.get("status") or "active", 1.0)
        scored.append((score, e.get("id"), e))
    scored.sort(key=lambda r: (-r[0], r[1] or ""))
    return [e_id for _, e_id, _ in scored[:top_k]]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", default="index.json")
    p.add_argument("--queries", default="eval/queries.jsonl")
    p.add_argument("--min-p5", type=float, default=None)
    p.add_argument("--min-r10", type=float, default=None)
    args = p.parse_args()

    entries = json.loads(Path(args.index).read_text(encoding="utf-8")).get("entries", [])
    cases = [
        json.loads(line)
        for line in Path(args.queries).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases:
        print("no eval cases found")
        return 1

    p5_sum = 0.0
    r10_sum = 0.0
    print(f"{'p@5':>6} {'r@10':>6}  query")
    print("-" * 70)
    for case in cases:
        query = case["query"]
        expected = set(case["expected_ids"])
        top5 = rank(entries, query, 5)
        top10 = rank(entries, query, 10)
        hits5 = sum(1 for x in top5 if x in expected)
        hits10 = sum(1 for x in top10 if x in expected)
        p5 = hits5 / 5.0
        r10 = hits10 / len(expected) if expected else 0.0
        p5_sum += p5
        r10_sum += r10
        flag = "" if (not expected or hits10) else "  <- MISS"
        print(f"{p5:6.2f} {r10:6.2f}  {query[:50]}{flag}")

    n = len(cases)
    mean_p5 = p5_sum / n
    mean_r10 = r10_sum / n
    print("-" * 70)
    print(f"mean precision@5 = {mean_p5:.3f}   mean recall@10 = {mean_r10:.3f}   ({n} queries)")

    rc = 0
    if args.min_p5 is not None and mean_p5 < args.min_p5:
        print(f"::error::precision@5 {mean_p5:.3f} below threshold {args.min_p5}")
        rc = 1
    if args.min_r10 is not None and mean_r10 < args.min_r10:
        print(f"::error::recall@10 {mean_r10:.3f} below threshold {args.min_r10}")
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
