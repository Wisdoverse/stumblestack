"""Data source: load index.json + pitfall markdown from local repo, the canonical
stumblestack.dev mirror, or a chain of fallback mirrors.

Resolution order:
  1. Explicit `local_path` constructor arg.
  2. `STUMBLESTACK_REPO` environment variable.
  3. The mirror chain: `STUMBLESTACK_MIRRORS` (comma-separated origins, each
     either a full https://host/[prefix] base URL or an `owner/repo[@ref]`
     GitHub slug), then `STUMBLESTACK_REMOTE` if that's a GitHub slug,
     then the canonical `https://stumblestack.dev` site, then a GitHub-raw
     fallback to `Wisdoverse/stumblestack@main`.

On 429 / 5xx / network error the source advances to the next mirror automatically.
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
import httpx

DEFAULT_CANONICAL_BASE = "https://stumblestack.dev"
DEFAULT_REMOTE_OWNER = "Wisdoverse"
DEFAULT_REMOTE_REPO = "stumblestack"
DEFAULT_REMOTE_REF = "main"

# A1 — generous default TTL with jitter so a fleet of clients does not
# refetch in lockstep at the TTL boundary.
DEFAULT_TTL_SECONDS = 3600
JITTER_FRACTION = 0.15  # ±15%


def _raw_github_base(owner: str, repo: str, ref: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}"


def _parse_github_slug(raw: str) -> tuple[str, str, str] | None:
    owner = DEFAULT_REMOTE_OWNER
    repo = DEFAULT_REMOTE_REPO
    ref = DEFAULT_REMOTE_REF
    if not raw or "://" in raw:
        return None
    if "@" in raw:
        slug, ref = raw.split("@", 1)
    else:
        slug = raw
    if "/" not in slug:
        return None
    owner, repo = slug.split("/", 1)
    return owner.strip(), repo.strip(), ref.strip()


@dataclass(frozen=True)
class Mirror:
    """A single backing store. Exactly one of `local` (a filesystem path) or
    `base_url` (an HTTPS base, no trailing slash) is set — enforced at construction
    so callers never have to re-check, and illegal states cannot be represented."""

    label: str
    local: Path | None
    base_url: str | None  # without trailing slash

    def __post_init__(self) -> None:
        if (self.local is None) == (self.base_url is None):
            raise ValueError("Mirror requires exactly one of local / base_url to be set")
        if self.base_url is not None and self.base_url.endswith("/"):
            raise ValueError(f"Mirror.base_url must not end with '/': {self.base_url!r}")

    def origin(self) -> str:
        return self.label


def _build_mirror_chain(local_path: Path | None) -> list[Mirror]:
    mirrors: list[Mirror] = []
    if local_path is not None:
        mirrors.append(Mirror(label=f"local:{local_path}", local=local_path, base_url=None))
        return mirrors

    seen: set[str] = set()

    def add(label: str, base_url: str) -> None:
        url = base_url.rstrip("/")
        if url not in seen:
            seen.add(url)
            mirrors.append(Mirror(label=label, local=None, base_url=url))

    raw_chain = os.environ.get("STUMBLESTACK_MIRRORS", "")
    for piece in (p.strip() for p in raw_chain.split(",")):
        if not piece:
            continue
        slug = _parse_github_slug(piece)
        if slug is not None:
            o, r, ref = slug
            add(f"github:{o}/{r}@{ref}", _raw_github_base(o, r, ref))
        elif "://" in piece:
            add(piece, piece)

    remote = os.environ.get("STUMBLESTACK_REMOTE", "")
    slug = _parse_github_slug(remote)
    if slug is not None:
        o, r, ref = slug
        add(f"github:{o}/{r}@{ref}", _raw_github_base(o, r, ref))

    add(f"canonical:{DEFAULT_CANONICAL_BASE}", DEFAULT_CANONICAL_BASE)
    add(
        f"github:{DEFAULT_REMOTE_OWNER}/{DEFAULT_REMOTE_REPO}@{DEFAULT_REMOTE_REF}",
        _raw_github_base(DEFAULT_REMOTE_OWNER, DEFAULT_REMOTE_REPO, DEFAULT_REMOTE_REF),
    )

    return mirrors


@dataclass
class StumblestackSource:
    """Fetches the stumblestack index + entries from a chain of mirrors."""

    local_path: Path | None = None
    # NOTE: remote_owner/remote_repo/remote_ref do NOT configure the read mirror
    # chain — that chain is built by _build_mirror_chain() which reads
    # STUMBLESTACK_MIRRORS / STUMBLESTACK_REMOTE from the environment directly.
    # These three fields are consumed only by submit._fetch_schema() to locate the
    # schema repo. Setting them here without the matching env var will NOT change
    # where the index is fetched from.
    remote_owner: str = DEFAULT_REMOTE_OWNER
    remote_repo: str = DEFAULT_REMOTE_REPO
    remote_ref: str = DEFAULT_REMOTE_REF
    ttl_seconds: int = DEFAULT_TTL_SECONDS

    _mirrors: list[Mirror] = field(default_factory=list, init=False, repr=False)
    _index: dict | None = field(default=None, init=False, repr=False)
    _index_fetched_at: float = field(default=0.0, init=False, repr=False)
    _index_expires_at: float = field(default=0.0, init=False, repr=False)
    _index_origin: str | None = field(default=None, init=False, repr=False)
    _entry_cache: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _client: httpx.Client | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        # A misconfigured local repo path is a config error, not a transient
        # fetch failure — surface it clearly instead of letting it masquerade as
        # "all mirrors failed" deep inside _fetch_first.
        if self.local_path is not None and not self.local_path.is_dir():
            raise RuntimeError(
                f"STUMBLESTACK_REPO does not point to an existing directory: {self.local_path}"
            )
        if not self._mirrors:
            self._mirrors = _build_mirror_chain(self.local_path)

    @classmethod
    def from_env(cls) -> "StumblestackSource":
        local = os.environ.get("STUMBLESTACK_REPO")
        local_path = Path(local).expanduser().resolve() if local else None

        owner = DEFAULT_REMOTE_OWNER
        repo = DEFAULT_REMOTE_REPO
        ref = DEFAULT_REMOTE_REF
        remote = os.environ.get("STUMBLESTACK_REMOTE", "")
        slug = _parse_github_slug(remote)
        if slug is not None:
            owner, repo, ref = slug

        ttl_raw = os.environ.get("STUMBLESTACK_TTL")
        if ttl_raw is None or not ttl_raw.strip():
            ttl = DEFAULT_TTL_SECONDS
        else:
            try:
                ttl = max(0, int(ttl_raw))
            except ValueError:
                raise RuntimeError(
                    f"STUMBLESTACK_TTL must be an integer number of seconds, got {ttl_raw!r}"
                )

        return cls(
            local_path=local_path,
            remote_owner=owner,
            remote_repo=repo,
            remote_ref=ref,
            ttl_seconds=ttl,
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=15.0, follow_redirects=True)
        return self._client

    def origin(self) -> str:
        return self._index_origin or self._mirrors[0].origin()

    def mirrors(self) -> list[str]:
        return [m.origin() for m in self._mirrors]

    def cache_age_seconds(self) -> int | None:
        if not self._index_fetched_at:
            return None
        return max(0, int(time.time() - self._index_fetched_at))

    def index(self, *, force: bool = False) -> dict:
        now = time.time()
        if not force and self._index is not None and now < self._index_expires_at:
            return self._index
        raw, origin = self._fetch_first("index.json")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"index.json from {origin} is not valid JSON: {exc}") from exc
        self._index = data
        self._index_origin = origin
        self._index_fetched_at = now
        jitter = 1.0 + random.uniform(-JITTER_FRACTION, JITTER_FRACTION) if self.ttl_seconds else 0.0
        self._index_expires_at = now + max(0.0, self.ttl_seconds * jitter)
        self._entry_cache.clear()
        return data

    def entries(self) -> list[dict]:
        return list(self.index().get("entries", []))

    def entry_body(self, pitfall_id: str) -> tuple[dict, str]:
        for record in self.index().get("entries", []):
            if record.get("id") == pitfall_id:
                path = record.get("path")
                if not path:
                    raise KeyError(f"entry {pitfall_id} has no path")
                body = self._fetch_body(path)
                return record, body
        raise KeyError(pitfall_id)

    def _fetch_body(self, rel_path: str) -> str:
        if rel_path in self._entry_cache:
            return self._entry_cache[rel_path]
        text, _ = self._fetch_first(rel_path)
        self._entry_cache[rel_path] = text
        return text

    def _fetch_first(self, rel_path: str) -> tuple[str, str]:
        """Walk the mirror chain until one returns the resource. Any failure on one
        mirror — network error, OSError on a local mirror, or ANY non-2xx status
        (including 404/403: the resource may exist on a later mirror) — advances to
        the next. Only when every mirror has failed do we raise, chaining the last
        error so the real cause is visible."""
        last_error: Exception | None = None
        for mirror in self._mirrors:
            try:
                if mirror.local is not None:
                    text = (mirror.local / rel_path).read_text(encoding="utf-8")
                    return text, mirror.origin()
                # base_url is guaranteed non-None by Mirror.__post_init__.
                response = self._http().get(f"{mirror.base_url}/{rel_path}")
                response.raise_for_status()
                return response.text, mirror.origin()
            except (OSError, httpx.HTTPError) as exc:
                # httpx.HTTPError covers RequestError (network) and HTTPStatusError
                # (any 4xx/5xx). All are treated as "this mirror missed; try next".
                last_error = exc
                continue
        if last_error is None:
            raise RuntimeError(f"no mirror configured for {rel_path}")
        raise RuntimeError(
            f"all {len(self._mirrors)} mirror(s) failed for {rel_path}: {last_error}"
        ) from last_error
