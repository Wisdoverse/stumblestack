#!/usr/bin/env python3
"""#11 — generate embeddings.json for semantic search (optional artifact).

Embeds each entry's searchable text (title + symptoms + _aliases + root_cause +
tags) with a provider and writes a normalized vector per id.

Providers:
  local-hash  deterministic token-hashing embedding (default). Dependency-free and
              reproducible — used for testing the pipeline. NOT semantic.
  <other>     real model providers (e.g. an embedding API) plug in here; those are
              key-gated and run from the workflow, not committed.

Output is deterministic for local-hash: sorted ids, fixed float precision, no
timestamp. Written to --out (default _site/api/v1/embeddings.json) — NOT committed
(keeps the index.json determinism gate clean; embeddings can be large).

Usage:
  python scripts/build_embeddings.py --provider local-hash --out _site/api/v1/embeddings.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse the exact local-hash embedding the server uses, so build-time and
# query-time vectors live in the same space.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-server" / "src"))
from stumblestack_mcp.embeddings import DEFAULT_DIM, LOCAL_HASH_MODEL, hash_embed  # noqa: E402


def _entry_text(e: dict) -> str:
    parts = [e.get("title") or "", e.get("root_cause") or ""]
    parts += e.get("symptoms") or []
    parts += e.get("_aliases") or []
    parts += e.get("tags") or []
    fc = e.get("fix_code")
    if isinstance(fc, dict):
        parts.append(f"{fc.get('language', '')} {fc.get('code', '')}")
    return " ".join(str(p) for p in parts)


def build(index: dict, provider: str, dim: int, precision: int) -> dict:
    if provider != "local-hash":
        raise SystemExit(
            f"provider {provider!r} not available in this script; only 'local-hash' is "
            "built in. Real providers run key-gated from .github/workflows/embeddings.yml."
        )
    vectors = {}
    for e in index.get("entries", []):
        eid = e.get("id")
        if not eid:
            continue
        vectors[eid] = [round(x, precision) for x in hash_embed(_entry_text(e), dim)]
    # Sorted keys => deterministic serialization.
    vectors = {k: vectors[k] for k in sorted(vectors)}
    return {
        "schema_version": 1,
        "model": LOCAL_HASH_MODEL,
        "dim": dim,
        "normalized": True,
        "count": len(vectors),
        "vectors": vectors,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--index", default="index.json")
    p.add_argument("--provider", default="local-hash")
    p.add_argument("--dim", type=int, default=DEFAULT_DIM)
    p.add_argument("--precision", type=int, default=6)
    p.add_argument("--out", default=None, help="default: _site/api/v1/embeddings.json")
    args = p.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        sys.stderr.write(f"build_embeddings: {index_path} not found\n")
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))

    payload = build(index, args.provider, args.dim, args.precision)
    out = Path(args.out) if args.out else index_path.parent / "_site" / "api" / "v1" / "embeddings.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} ({payload['count']} vectors, model={payload['model']}, dim={payload['dim']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
