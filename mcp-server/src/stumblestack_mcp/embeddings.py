"""#11 — optional semantic-search seam.

Lexical search (search.py) is the default and always available. When an
`embeddings.json` artifact is published AND an embedding provider is configured
(STUMBLESTACK_EMBED_PROVIDER), the server can rank by cosine similarity instead —
catching paraphrases that share no keywords with the stored symptoms.

Design notes:
- DEFAULT IS OFF. STUMBLESTACK_EMBED_PROVIDER unset / "none" => embed_query returns
  None => the server stays on lexical search. Live behavior is unchanged unless an
  operator opts in.
- Provider is pluggable. "local-hash" is a deterministic, dependency-free token-
  hashing embedding — good for testing the whole pipeline offline, but it is NOT
  semantic; plug a real model provider for real semantic recall.
- The query MUST be embedded with the same provider/model used to build
  embeddings.json, or cosine scores are meaningless. The server compares the
  artifact's `model` against the active provider and refuses to mix them.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re

from .search import Hit

_TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_DIM = 256
LOCAL_HASH_MODEL = "local-hash-v1"


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def hash_embed(text: str, dim: int = DEFAULT_DIM) -> list[float]:
    """Deterministic local embedding: bag-of-tokens hashed into `dim` buckets,
    L2-normalized. No randomness, no external calls. Test/fallback provider."""
    vec = [0.0] * dim
    for tok in _tokens(text):
        h = int.from_bytes(hashlib.sha256(tok.encode("utf-8")).digest()[:8], "big")
        idx = h % dim
        sign = 1.0 if (h >> 63) & 1 else -1.0
        vec[idx] += sign
    return _l2_normalize(vec)


def active_provider() -> str:
    return os.environ.get("STUMBLESTACK_EMBED_PROVIDER", "none").strip().lower()


def provider_model(provider: str | None = None) -> str | None:
    """The model id the active provider produces, or None when disabled."""
    p = provider or active_provider()
    if p in ("", "none"):
        return None
    if p == "local-hash":
        return LOCAL_HASH_MODEL
    # Real providers (e.g. openai:text-embedding-3-large) resolve here when added.
    return p


def embed_query(text: str) -> list[float] | None:
    """Embed a query with the active provider. None when disabled/unavailable —
    the caller then falls back to lexical search."""
    p = active_provider()
    if p in ("", "none"):
        return None
    if p == "local-hash":
        return hash_embed(text)
    return None  # real providers plug in here (network/SDK); absent by default


def load_embeddings(source) -> dict | None:
    """Fetch embeddings.json via the source mirror chain. None if absent."""
    try:
        raw = source.optional_artifact("api/v1/embeddings.json")
    except Exception:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) and "vectors" in data else None


def usable(embeddings: dict | None, provider_model_id: str | None) -> bool:
    """The artifact is usable only if it exists and was built with the SAME model
    the active provider produces (mixing models gives meaningless cosines)."""
    if not embeddings or provider_model_id is None:
        return False
    return embeddings.get("model") == provider_model_id


def cosine_search(
    entries,
    query_vec: list[float],
    embeddings: dict,
    *,
    category: str | None = None,
    top_k: int = 5,
    model: str | None = None,
) -> list[Hit]:
    """Rank entries by cosine similarity (vectors are stored normalized, so this is
    a dot product). Same category/model filters and id tiebreak as lexical search."""
    vectors = embeddings.get("vectors", {})
    scored: list[Hit] = []
    for entry in entries:
        if category and entry.get("category") != category:
            continue
        if model and entry.get("model_version") and entry["model_version"] != model:
            continue
        vec = vectors.get(entry.get("id"))
        if not vec:
            continue
        score = sum(a * b for a, b in zip(query_vec, vec, strict=False))
        if score <= 0:
            continue
        scored.append(Hit(entry=entry, score=score, matched_terms=[]))
    scored.sort(key=lambda h: (-h.score, h.entry.get("id", "")))
    return scored[:top_k]
