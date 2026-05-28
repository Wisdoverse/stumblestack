#!/usr/bin/env python3
"""Build index.json from all pitfall entries.

The index is a flat array of compact records for fast lookup by agents.
Body content is excluded — agents pull the full .md only when needed.

Usage: python scripts/build_index.py [--root REPO_ROOT] [--out index.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--out", default=None, help="Output path (default: <root>/index.json)")
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

    payload = {
        "schema_version": 1,
        "count": len(records),
        "entries": records,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(records)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
