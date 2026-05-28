"""Data source: load index.json + pitfall markdown from local repo or GitHub raw."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

DEFAULT_REMOTE_OWNER = "Wisdoverse"
DEFAULT_REMOTE_REPO = "stumblestack"
DEFAULT_REMOTE_REF = "main"
DEFAULT_TTL_SECONDS = 600


def _raw_url(owner: str, repo: str, ref: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"


@dataclass
class StumblestackSource:
    """Loads pitfall data from a local repo path or from a GitHub raw mirror.

    Resolution order:
      1. Explicit `local_path` constructor arg.
      2. `STUMBLESTACK_REPO` environment variable.
      3. Falls back to GitHub raw (Wisdoverse/stumblestack@main by default,
         overridable via `STUMBLESTACK_REMOTE` as "owner/repo@ref").
    """

    local_path: Path | None = None
    remote_owner: str = DEFAULT_REMOTE_OWNER
    remote_repo: str = DEFAULT_REMOTE_REPO
    remote_ref: str = DEFAULT_REMOTE_REF
    ttl_seconds: int = DEFAULT_TTL_SECONDS

    _index: dict | None = field(default=None, init=False, repr=False)
    _index_fetched_at: float = field(default=0.0, init=False, repr=False)
    _entry_cache: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _client: httpx.Client | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "StumblestackSource":
        local = os.environ.get("STUMBLESTACK_REPO")
        local_path = Path(local).expanduser().resolve() if local else None

        remote = os.environ.get("STUMBLESTACK_REMOTE", "")
        owner, repo, ref = DEFAULT_REMOTE_OWNER, DEFAULT_REMOTE_REPO, DEFAULT_REMOTE_REF
        if remote:
            if "@" in remote:
                slug, ref = remote.split("@", 1)
            else:
                slug = remote
            if "/" in slug:
                owner, repo = slug.split("/", 1)

        ttl = int(os.environ.get("STUMBLESTACK_TTL", DEFAULT_TTL_SECONDS))
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
        if self.local_path:
            return f"local:{self.local_path}"
        return f"github:{self.remote_owner}/{self.remote_repo}@{self.remote_ref}"

    def index(self, *, force: bool = False) -> dict:
        now = time.time()
        if (
            not force
            and self._index is not None
            and now - self._index_fetched_at < self.ttl_seconds
        ):
            return self._index

        if self.local_path:
            path = self.local_path / "index.json"
            raw = path.read_text(encoding="utf-8")
        else:
            url = _raw_url(self.remote_owner, self.remote_repo, self.remote_ref, "index.json")
            response = self._http().get(url)
            response.raise_for_status()
            raw = response.text

        self._index = json.loads(raw)
        self._index_fetched_at = now
        self._entry_cache.clear()
        return self._index

    def entries(self) -> list[dict]:
        idx = self.index()
        return list(idx.get("entries", []))

    def entry_body(self, pitfall_id: str) -> tuple[dict, str]:
        idx = self.index()
        for record in idx.get("entries", []):
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

        if self.local_path:
            text = (self.local_path / rel_path).read_text(encoding="utf-8")
        else:
            url = _raw_url(self.remote_owner, self.remote_repo, self.remote_ref, rel_path)
            response = self._http().get(url)
            response.raise_for_status()
            text = response.text

        self._entry_cache[rel_path] = text
        return text
