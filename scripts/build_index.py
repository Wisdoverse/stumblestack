#!/usr/bin/env python3
"""Build index.json from all pitfall entries.

The index is a flat array of compact records for fast lookup by agents.
Body content is excluded — agents pull the full .md only when needed.

Usage: python scripts/build_index.py [--root REPO_ROOT] [--out index.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("Missing dependency: PyYAML. Install: pip install pyyaml\n")
    sys.exit(2)


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

INDEX_FIELDS = (
    "id",
    "title",
    "category",
    "tags",
    "symptoms",
    "root_cause",
    "agent",
    "model_version",
    "verified_count",
    "verification_prs",
    "superseded_by",
    "created",
    "updated",
    "fix_unsafe",
    # Additive schema fields (schema_version stays 1, DESIGN.md 9b). fix_code is
    # projected so the ranker can up-weight code-shaped fixes; raw `fix`/`links`
    # remain body-only and out of the index.
    "applies_to",
    "severity",
    "_aliases",
    "fix_code",
    # Lifecycle (v1.1, additive): status drives the ranker's deprioritization of
    # stale/fixed/superseded entries; the rest inform the staleness report + badges.
    "status",
    "observed_on",
    "fixed_in",
    "not_reproduced_on",
    "last_verified",
)


def _stringify_dates(value):
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _stringify_dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify_dates(v) for v in value]
    return value


def parse_entry(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: missing YAML frontmatter")
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")
    return _stringify_dates(data)


SHARD_THRESHOLD_BYTES = 2 * 1024 * 1024  # A17 — shard the browser index above ~2 MB.


def _dump(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _write_shards(shard_dir: Path, records: list[dict], schema_version: int) -> dict:
    """Write index/<category>.json + index/_manifest.json. Deterministic: sorted
    categories, records already id-sorted, sha256 over the exact written bytes, no
    timestamps. Returns the manifest dict."""
    if shard_dir.exists():
        shutil.rmtree(shard_dir)
    shard_dir.mkdir(parents=True)

    by_category: dict[str, list[dict]] = {}
    for r in records:
        by_category.setdefault(r.get("category") or "uncategorized", []).append(r)

    shards = []
    for category in sorted(by_category):
        entries = by_category[category]
        body = _dump({"schema_version": schema_version, "category": category,
                      "count": len(entries), "entries": entries})
        (shard_dir / f"{category}.json").write_text(body, encoding="utf-8")
        shards.append({
            "category": category,
            "path": f"index/{category}.json",
            "count": len(entries),
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        })

    manifest = {"schema_version": schema_version, "count": len(records), "shards": shards}
    (shard_dir / "_manifest.json").write_text(_dump(manifest), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--out", default=None, help="Output path (default: <root>/index.json)")
    parser.add_argument("--shard", choices=["auto", "always", "never"], default="auto",
                        help="Emit per-category shards: auto (when index.json exceeds the "
                             "threshold), always, or never. Default auto.")
    parser.add_argument("--shard-threshold-bytes", type=int, default=SHARD_THRESHOLD_BYTES)
    args = parser.parse_args()

    root = Path(args.root)
    pitfalls_dir = root / "pitfalls"
    out_path = Path(args.out) if args.out else root / "index.json"

    records: list[dict] = []
    for path in sorted(pitfalls_dir.rglob("*.md")):
        data = parse_entry(path)
        record = {key: data[key] for key in INDEX_FIELDS if key in data}
        record["path"] = str(path.relative_to(root)).replace("\\", "/")
        records.append(record)

    records.sort(key=lambda r: r.get("id", ""))

    schema_version = 1
    body = _dump({"schema_version": schema_version, "count": len(records), "entries": records})
    out_path.write_text(body, encoding="utf-8")
    size = len(body.encode("utf-8"))
    print(f"wrote {out_path} ({len(records)} entries, {size} bytes)")

    # Sharding (A17). The full index.json above is always kept (server/API/back-compat);
    # shards are an additive browser-delivery optimization consumed by search.js.
    shard_dir = out_path.parent / "index"
    do_shard = args.shard == "always" or (args.shard == "auto" and size > args.shard_threshold_bytes)
    if do_shard:
        manifest = _write_shards(shard_dir, records, schema_version)
        print(f"wrote {shard_dir}/ ({len(manifest['shards'])} category shards)")
    elif shard_dir.exists():
        # Below threshold in auto/never mode: remove stale shards so they are not
        # committed or served out of date.
        shutil.rmtree(shard_dir)
        print(f"removed stale {shard_dir}/ (index under threshold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
