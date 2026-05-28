#!/usr/bin/env python3
"""Validate every pitfall entry under pitfalls/ against schemas/pitfall.schema.json.

Exit code 0 on success, 1 on any failure. Prints one issue per line.

Usage: python scripts/validate.py [--root REPO_ROOT]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("Missing dependency: PyYAML. Install: pip install pyyaml jsonschema\n")
    sys.exit(2)

try:
    import jsonschema
except ImportError:
    sys.stderr.write("Missing dependency: jsonschema. Install: pip install pyyaml jsonschema\n")
    sys.exit(2)


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


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
        raise ValueError("missing YAML frontmatter (must start with `---` block)")
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return _stringify_dates(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    root = Path(args.root)
    schema_path = root / "schemas" / "pitfall.schema.json"
    pitfalls_dir = root / "pitfalls"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    errors: list[str] = []
    ids: dict[str, Path] = {}
    slugs_by_category: dict[str, dict[str, Path]] = defaultdict(dict)

    paths = sorted(pitfalls_dir.rglob("*.md"))
    if not paths:
        errors.append("no pitfall entries found under pitfalls/")

    for path in paths:
        rel = path.relative_to(root)
        try:
            data = parse_entry(path)
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
            continue

        for err in validator.iter_errors(data):
            loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"{rel}: schema: {loc}: {err.message}")

        # filesystem consistency
        parts = path.relative_to(pitfalls_dir).parts
        if len(parts) != 2:
            errors.append(f"{rel}: must live at pitfalls/<category>/<slug>.md")
            continue
        fs_category, filename = parts
        if data.get("category") and data["category"] != fs_category:
            errors.append(
                f"{rel}: category `{data['category']}` does not match directory `{fs_category}`"
            )

        # uniqueness
        pid = data.get("id")
        if pid:
            if pid in ids:
                errors.append(f"{rel}: duplicate id `{pid}` (also in {ids[pid].relative_to(root)})")
            else:
                ids[pid] = path

        slug = filename[:-3]
        if slug in slugs_by_category[fs_category]:
            errors.append(
                f"{rel}: duplicate slug `{slug}` in category `{fs_category}`"
            )
        else:
            slugs_by_category[fs_category][slug] = path

    if errors:
        for line in errors:
            print(line)
        print(f"\n{len(errors)} issue(s) across {len(paths)} entries", file=sys.stderr)
        return 1

    print(f"ok: {len(paths)} entries validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
