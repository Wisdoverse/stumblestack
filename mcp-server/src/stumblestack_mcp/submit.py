"""Build, validate, and submit a new pitfall via GitHub REST API.

Flow:
  1. Caller passes raw fields (title, category, tags, symptoms, root_cause, fix, ...).
  2. We generate a uuid, slug, frontmatter, and full markdown body.
  3. Validate the frontmatter against the upstream schema (fetched from the repo).
  4. Search the index for near-duplicates and return them as advisory hits.
  5. If dry_run, return preview + dup info, no API calls.
  6. Otherwise: create a branch, PUT the file, open a PR. Return the PR URL.

Auth: needs `GITHUB_TOKEN` with `repo` scope (or fine-grained PR: write + Contents: write).
Repo: `STUMBLESTACK_SUBMIT_REPO` (default: same as STUMBLESTACK_REMOTE / Wisdoverse/stumblestack@main).
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path as _Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

from .search import search
from .source import StumblestackSource

GITHUB_API = "https://api.github.com"

REQUIRED_FIELDS = ("title", "category", "tags", "symptoms", "root_cause", "fix")

_SLUG_INVALID = re.compile(r"[^a-z0-9]+")
_KEBAB = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


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


def validate_link(url: str) -> str | None:
    """Return None if `url` is safe to link from a pitfall, else a reason string.

    A39 from docs/DESIGN_REVIEW.md: links are submitter-controlled and end up rendered
    on stumblestack.dev plus the PR description. Reject SSRF-prone or local-only URLs.
    """
    if not isinstance(url, str) or not url.strip():
        return "empty url"
    raw = url.strip()
    try:
        parsed = urlparse(raw)
    except ValueError as exc:
        return f"unparseable url: {exc}"

    if parsed.scheme not in {"http", "https"}:
        return f"unsupported scheme `{parsed.scheme or '<none>'}`; only http and https are allowed"
    if not parsed.hostname:
        return "url is missing a hostname"

    host = parsed.hostname.strip().lower().rstrip(".")
    if host in _BLOCKED_HOSTS:
        return f"host `{host}` is blocked (local or cloud-metadata)"

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
            return f"host `{host}` resolves to a non-routable / private address"
    elif "." not in host:
        return f"host `{host}` is not a public FQDN"

    return None


class SubmitError(Exception):
    """Raised for any caller-correctable submit problem (bad input, dup-by-id, auth)."""


# A38 — advisory client-side rate guard. We cannot trust callers to behave, but we can
# refuse to participate when a single token would burst above the documented contract.
# This is *in addition to* GitHub's hard server-side limits, not a replacement for them.
RATE_WINDOW_SECONDS = int(os.environ.get("STUMBLESTACK_RATE_WINDOW", 600))
RATE_MAX_SUBMITS = int(os.environ.get("STUMBLESTACK_RATE_MAX", 10))


def _rate_cache_dir() -> _Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    path = _Path(base) / "stumblestack"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _rate_cache_path(token: str) -> _Path:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    return _rate_cache_dir() / f"submits-{digest}.json"


def _enforce_rate_limit(token: str) -> None:
    path = _rate_cache_path(token)
    now = time.time()
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        existing = []
    fresh = [t for t in existing if isinstance(t, (int, float)) and now - t < RATE_WINDOW_SECONDS]
    if len(fresh) >= RATE_MAX_SUBMITS:
        oldest = min(fresh)
        retry_in = int(RATE_WINDOW_SECONDS - (now - oldest))
        raise SubmitError(
            f"local rate limit reached: {len(fresh)} submissions in the last "
            f"{RATE_WINDOW_SECONDS}s (cap {RATE_MAX_SUBMITS}). Try again in ~{retry_in}s. "
            "Override via STUMBLESTACK_RATE_MAX / STUMBLESTACK_RATE_WINDOW only for trusted bots."
        )
    fresh.append(now)
    try:
        path.write_text(json.dumps(fresh), encoding="utf-8")
    except OSError:
        pass


def _slugify(title: str, max_len: int = 60) -> str:
    s = _SLUG_INVALID.sub("-", title.lower()).strip("-")
    if not s:
        s = "pitfall"
    if len(s) > max_len:
        s = s[:max_len].rstrip("-") or "pitfall"
    return s


def _frontmatter_yaml(record: dict) -> str:
    ordered_keys = [
        "id",
        "title",
        "category",
        "tags",
        "symptoms",
        "root_cause",
        "fix",
        "agent",
        "model_version",
        "verified_count",
        "superseded_by",
        "created",
        "updated",
        "links",
    ]
    ordered = {k: record[k] for k in ordered_keys if k in record}
    return yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=120).rstrip()


def build_markdown(record: dict, body: str | None) -> str:
    fm = _frontmatter_yaml(record)
    body_text = (body or "").strip()
    if not body_text:
        body_text = (
            "## Reproduction\n\n"
            "TODO: brief reproduction steps.\n\n"
            "## Correct usage\n\n"
            "TODO: minimal corrected example.\n"
        )
    return f"---\n{fm}\n---\n\n{body_text}\n"


def _err(field: str, message: str, suggestion: str | None = None) -> dict:
    out = {"field": field, "message": message}
    if suggestion:
        out["suggestion"] = suggestion
    return out


def _validate_record(record: dict, schema: dict | None) -> list[dict]:
    """A21 — return structured errors so callers can fix them programmatically."""
    errors: list[dict] = []
    for field_name in REQUIRED_FIELDS:
        if field_name not in record or record[field_name] in (None, "", []):
            errors.append(
                _err(
                    field_name,
                    f"missing required field `{field_name}`",
                    "include a non-empty value; see schemas/pitfall.schema.json",
                )
            )
    if "category" in record and not _KEBAB.match(str(record["category"])):
        errors.append(
            _err(
                "category",
                f"category `{record['category']}` is not lowercase kebab-case",
                "use letters, digits, and hyphens only; e.g. claude-code",
            )
        )
    for idx, tag in enumerate(record.get("tags", []) or []):
        if not _KEBAB.match(str(tag)):
            errors.append(
                _err(
                    f"tags[{idx}]",
                    f"tag `{tag}` is not lowercase kebab-case",
                    "use letters, digits, and hyphens only; e.g. edit-tool",
                )
            )
    for idx, url in enumerate(record.get("links", []) or []):
        reason = validate_link(str(url))
        if reason:
            errors.append(
                _err(
                    f"links[{idx}]",
                    f"unsafe link `{url}`: {reason}",
                    "use a public https:// URL; private IPs and non-http schemes are blocked",
                )
            )
    if not schema:
        return errors
    try:
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        for err in validator.iter_errors(record):
            loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(_err(loc, err.message))
    except ImportError:
        pass
    return errors


@dataclass
class BuildResult:
    record: dict
    markdown: str
    path: str
    branch: str
    duplicates: list[dict]
    errors: list[str]
    schema_origin: str | None


@dataclass
class SubmitResult:
    pr_url: str | None
    branch: str
    path: str
    record: dict
    dry_run: bool
    duplicates: list[dict] = field(default_factory=list)


def build(
    source: StumblestackSource,
    *,
    title: str,
    category: str,
    tags: list[str],
    symptoms: list[str],
    root_cause: str,
    fix: str,
    body: str | None = None,
    agent: str | None = None,
    model_version: str | None = None,
    links: list[str] | None = None,
    schema_url: str | None = None,
) -> BuildResult:
    record: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "title": (title or "").strip(),
        "category": (category or "").strip(),
        "tags": [t.strip() for t in (tags or []) if t and t.strip()],
        "symptoms": [s for s in (symptoms or []) if s],
        "root_cause": (root_cause or "").strip(),
        "fix": (fix or "").strip(),
        "verified_count": 0,
        "created": date.today().isoformat(),
    }
    if agent:
        record["agent"] = agent.strip()
    if model_version:
        record["model_version"] = model_version.strip()
    if links:
        record["links"] = [l for l in links if l]

    slug = _slugify(record["title"] or "pitfall")
    short = record["id"].split("-", 1)[0]
    path = f"pitfalls/{record['category'] or 'uncategorized'}/{slug}.md"
    branch = f"pitfall/{slug}-{short}"

    schema = _fetch_schema(source, schema_url)
    errors = _validate_record(record, schema)

    dup_query_parts = [record["title"], *record["symptoms"], record["root_cause"]]
    dup_query = " ".join(p for p in dup_query_parts if p)
    duplicates: list[dict] = []
    try:
        hits = search(source.entries(), dup_query, top_k=3)
        duplicates = [
            {
                "id": h.entry.get("id"),
                "title": h.entry.get("title"),
                "path": h.entry.get("path"),
                "score": round(h.score, 2),
            }
            for h in hits
        ]
    except Exception:
        duplicates = []

    markdown = build_markdown(record, body)

    return BuildResult(
        record=record,
        markdown=markdown,
        path=path,
        branch=branch,
        duplicates=duplicates,
        errors=errors,
        schema_origin=schema_url or (f"{source.origin()}/schemas/pitfall.schema.json"),
    )


def _fetch_schema(source: StumblestackSource, override_url: str | None) -> dict | None:
    try:
        if source.local_path:
            schema_path = source.local_path / "schemas" / "pitfall.schema.json"
            if schema_path.exists():
                return json.loads(schema_path.read_text(encoding="utf-8"))
        url = override_url or (
            f"https://raw.githubusercontent.com/{source.remote_owner}/"
            f"{source.remote_repo}/{source.remote_ref}/schemas/pitfall.schema.json"
        )
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url)
            if r.status_code == 200:
                return r.json()
    except Exception:
        return None
    return None


def _submit_repo() -> tuple[str, str, str]:
    """Return (owner, repo, base_ref) for the target submit repo."""
    raw = os.environ.get("STUMBLESTACK_SUBMIT_REPO") or os.environ.get("STUMBLESTACK_REMOTE", "")
    owner, repo, ref = "Wisdoverse", "stumblestack", "main"
    if raw:
        if "@" in raw:
            slug, ref = raw.split("@", 1)
        else:
            slug = raw
        if "/" in slug:
            owner, repo = slug.split("/", 1)
    return owner, repo, ref


def redact(text: str, *secrets_to_mask: str) -> str:
    """A42 — mask any provided secret (and common GitHub token shapes) in a string
    before it can reach a log, an error message, or a tool response.
    """
    out = text or ""
    for secret in secrets_to_mask:
        if secret and len(secret) >= 8:
            out = out.replace(secret, "***REDACTED***")
    # Defense in depth: scrub anything that looks like a GitHub token even if the
    # exact value was not passed in.
    out = re.sub(r"gh[opsur]_[A-Za-z0-9]{20,}", "***REDACTED***", out)
    out = re.sub(r"github_pat_[A-Za-z0-9_]{20,}", "***REDACTED***", out)
    return out


def _gh_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "stumblestack-mcp",
    }


def submit(source: StumblestackSource, build_result: BuildResult, *, dry_run: bool = False) -> SubmitResult:
    if build_result.errors:
        raise SubmitError("invalid pitfall: " + "; ".join(build_result.errors))

    if dry_run:
        return SubmitResult(
            pr_url=None,
            branch=build_result.branch,
            path=build_result.path,
            record=build_result.record,
            dry_run=True,
            duplicates=build_result.duplicates,
        )

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SubmitError(
            "GITHUB_TOKEN (or GH_TOKEN) not set. Required scopes: repo (classic) or "
            "Contents+Pull requests: write (fine-grained)."
        )

    _enforce_rate_limit(token)

    owner, repo, base = _submit_repo()
    headers = _gh_headers(token)

    branch = build_result.branch
    suffix = secrets.token_hex(2)

    with httpx.Client(timeout=20.0, headers=headers) as client:
        base_ref = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{base}")
        if base_ref.status_code != 200:
            raise SubmitError(redact(f"base ref lookup failed: {base_ref.status_code} {base_ref.text}", token))
        base_sha = base_ref.json()["object"]["sha"]

        created = client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )
        if created.status_code == 422:
            branch = f"{build_result.branch}-{suffix}"
            created = client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": base_sha},
            )
        if created.status_code not in (200, 201):
            raise SubmitError(redact(f"branch create failed: {created.status_code} {created.text}", token))

        content_b64 = base64.b64encode(build_result.markdown.encode("utf-8")).decode("ascii")
        put = client.put(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{build_result.path}",
            json={
                "message": f"pitfall({build_result.record['category']}): {build_result.record['title']}",
                "content": content_b64,
                "branch": branch,
            },
        )
        if put.status_code not in (200, 201):
            raise SubmitError(redact(f"file create failed: {put.status_code} {put.text}", token))

        pr_body_lines = [
            f"Submitted via stumblestack-mcp by `{build_result.record.get('agent', 'unknown')}`",
            f"Model: `{build_result.record.get('model_version', 'unknown')}`",
            "",
            "## Symptoms",
            *[f"- `{s}`" for s in build_result.record.get("symptoms", [])],
            "",
            "## Root cause",
            build_result.record.get("root_cause", ""),
            "",
            "## Fix",
            build_result.record.get("fix", ""),
        ]
        if build_result.duplicates:
            pr_body_lines += [
                "",
                "## Possible duplicates (advisory)",
                *[f"- `{d['id']}` — {d['title']} (score {d['score']})" for d in build_result.duplicates],
            ]
        pr_body = "\n".join(pr_body_lines)

        pr = client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
            json={
                "title": f"pitfall({build_result.record['category']}): {build_result.record['title']}",
                "head": branch,
                "base": base,
                "body": pr_body,
                "maintainer_can_modify": True,
            },
        )
        if pr.status_code not in (200, 201):
            raise SubmitError(redact(f"PR create failed: {pr.status_code} {pr.text}", token))
        pr_url = pr.json().get("html_url")

    return SubmitResult(
        pr_url=pr_url,
        branch=branch,
        path=build_result.path,
        record=build_result.record,
        dry_run=False,
        duplicates=build_result.duplicates,
    )
