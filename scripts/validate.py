#!/usr/bin/env python3
"""Validate every pitfall entry under pitfalls/ against schemas/pitfall.schema.json.

Exit code 0 on success, 1 on any failure. Prints one issue per line.

Usage: python scripts/validate.py [--root REPO_ROOT]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import ipaddress
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

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


# Keep in sync with stumblestack_mcp.submit._BLOCKED_HOSTS (a parity test asserts equality).
_BLOCKED_HOSTS = frozenset({
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "broadcasthost",
    "metadata.google.internal",
    "169.254.169.254",
    "[fd00:ec2::254]",
})


def link_problem(url: str) -> str | None:
    """A39 — reject SSRF-prone or local URLs at CI time. Mirrors submit.py."""
    if not isinstance(url, str) or not url.strip():
        return "empty url"
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return f"unsupported scheme `{parsed.scheme or '<none>'}`"
    if not parsed.hostname:
        return "missing hostname"
    host = parsed.hostname.strip().lower().rstrip(".")
    if host in _BLOCKED_HOSTS:
        return f"host `{host}` is blocked"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return f"host `{host}` is non-routable / private"
    elif "." not in host:
        return f"host `{host}` is not a public FQDN"
    return None


_UNSAFE_SHELL_RE = re.compile(
    r"(curl\s+[^|]*\|\s*(sh|bash|zsh|fish))"
    r"|(wget\s+[^|]*\|\s*(sh|bash|zsh|fish))"
    r"|(\brm\s+-rf?\s+/(?:\s|$))"
    r"|(\bsudo\s+rm\s+-rf?\s+/)"
    r"|(:\(\)\s*\{\s*:\|:&\s*\};\s*:)"  # fork bomb
    r"|(\bmkfs\.(?:ext[234]|xfs|btrfs)\b\s+/dev/)"
    r"|(\bdd\s+if=\S+\s+of=/dev/sd[a-z])",
    re.IGNORECASE,
)


def unsafe_shell_hits(text: str) -> list[str]:
    """A12 — flag dangerous shell patterns in `fix` or body code blocks."""
    return [m.group(0) for m in _UNSAFE_SHELL_RE.finditer(text or "")]


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


def parse_entry(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("missing YAML frontmatter (must start with `---` block)")
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return _stringify_dates(data), text[m.end():]


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
    # (rel, superseded_by, status) collected for a post-pass once all ids are known.
    lifecycle_refs: list[tuple[Path, str | None, str | None]] = []

    paths = sorted(pitfalls_dir.rglob("*.md"))
    if not paths:
        errors.append("no pitfall entries found under pitfalls/")

    for path in paths:
        rel = path.relative_to(root)
        try:
            data, body = parse_entry(path)
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
            continue

        for err in validator.iter_errors(data):
            loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"{rel}: schema: {loc}: {err.message}")

        # A11 — verified_count is derived from verification_prs when present.
        vps = data.get("verification_prs")
        vcount = data.get("verified_count")
        if vps is not None:
            verifiers = [str(p.get("verifier") or p.get("repo") or i) for i, p in enumerate(vps)]
            if len(set(verifiers)) != len(verifiers):
                errors.append(
                    f"{rel}: verification_prs contains duplicate verifiers; each entry must be from a distinct submitter"
                )
            if vcount is not None and int(vcount) != len(vps):
                errors.append(
                    f"{rel}: verified_count ({vcount}) does not match len(verification_prs) ({len(vps)})"
                )

        # Lifecycle (v1.1): collect for the referential-integrity post-pass, and
        # check status/superseded_by consistency. status==superseded REQUIRES a
        # superseded_by pointer; a superseded_by present implies a non-active status.
        status = data.get("status")
        superseded_by = data.get("superseded_by")
        lifecycle_refs.append((rel, superseded_by, status))
        if status == "superseded" and not superseded_by:
            errors.append(f"{rel}: status `superseded` requires a `superseded_by` UUID")
        if superseded_by and status in (None, "active"):
            errors.append(
                f"{rel}: superseded_by is set but status is `{status or 'active'}`; "
                "set status to superseded (or fixed-upstream/retired)"
            )

        # A39 — link safety
        for url in data.get("links", []) or []:
            problem = link_problem(str(url))
            if problem:
                errors.append(f"{rel}: unsafe link `{url}`: {problem}")

        # A12 — unsafe shell pattern lint. Allow opt-out via `fix_unsafe: true`,
        # which itself is a flag the renderer surfaces to readers. Covers the
        # freeform `fix`, the body, and the structured `fix_code.code` (additive).
        if not data.get("fix_unsafe"):
            fix_code = data.get("fix_code")
            fix_code_text = ""
            if isinstance(fix_code, dict):
                fix_code_text = str(fix_code.get("code") or "")
            scan_fields = {"fix": str(data.get("fix") or ""), "fix_code.code": fix_code_text}
            for source_field, text in scan_fields.items():
                for hit in unsafe_shell_hits(text):
                    errors.append(
                        f"{rel}: unsafe shell pattern in `{source_field}`: `{hit.strip()}` — "
                        "set `fix_unsafe: true` in frontmatter to acknowledge"
                    )
            for hit in unsafe_shell_hits(body):
                errors.append(
                    f"{rel}: unsafe shell pattern in body: `{hit.strip()}` — "
                    "set `fix_unsafe: true` in frontmatter to acknowledge"
                )

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

    # Lifecycle post-pass: superseded_by must point to a real entry id (now that
    # every id is known) and must not be a self-reference.
    for rel, superseded_by, _status in lifecycle_refs:
        if superseded_by and superseded_by not in ids:
            errors.append(f"{rel}: superseded_by `{superseded_by}` does not match any entry id")

    if errors:
        for line in errors:
            print(line)
        print(f"\n{len(errors)} issue(s) across {len(paths)} entries", file=sys.stderr)
        return 1

    print(f"ok: {len(paths)} entries validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
