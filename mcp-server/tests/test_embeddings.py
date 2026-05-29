"""#11 semantic-search seam: provider gating, cosine ranking, fallback, determinism."""
from __future__ import annotations

from stumblestack_mcp import embeddings as emb


def test_provider_off_by_default(monkeypatch):
    monkeypatch.delenv("STUMBLESTACK_EMBED_PROVIDER", raising=False)
    assert emb.active_provider() == "none"
    assert emb.embed_query("anything") is None      # disabled => caller stays lexical
    assert emb.provider_model() is None


def test_local_hash_provider(monkeypatch):
    monkeypatch.setenv("STUMBLESTACK_EMBED_PROVIDER", "local-hash")
    assert emb.provider_model() == emb.LOCAL_HASH_MODEL
    v = emb.embed_query("context window exceeded")
    assert v is not None and len(v) == emb.DEFAULT_DIM


def test_hash_embed_deterministic_and_normalized():
    a = emb.hash_embed("max tokens limit reached")
    b = emb.hash_embed("max tokens limit reached")
    assert a == b
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_usable_requires_matching_model():
    art = {"model": emb.LOCAL_HASH_MODEL, "vectors": {"a": [0.0]}}
    assert emb.usable(art, emb.LOCAL_HASH_MODEL) is True
    assert emb.usable(art, "openai:text-embedding-3-large") is False   # model mismatch
    assert emb.usable(None, emb.LOCAL_HASH_MODEL) is False
    assert emb.usable(art, None) is False                              # provider off


def test_cosine_ranks_by_similarity():
    # Build vectors so the query is closest to entry "b".
    q = emb.hash_embed("token limit exceeded")
    entries = [
        {"id": "a", "category": "x"},
        {"id": "b", "category": "x"},
        {"id": "c", "category": "y"},
    ]
    art = {
        "model": emb.LOCAL_HASH_MODEL, "dim": emb.DEFAULT_DIM, "normalized": True,
        "vectors": {
            "a": emb.hash_embed("completely unrelated git reset"),
            "b": emb.hash_embed("token limit exceeded"),       # identical to query
            "c": emb.hash_embed("docker layer cache"),
        },
    }
    hits = emb.cosine_search(entries, q, art, top_k=3)
    assert hits[0].entry["id"] == "b"
    assert abs(hits[0].score - 1.0) < 1e-9    # cosine with itself == 1


def test_cosine_category_filter():
    q = emb.hash_embed("anything")
    entries = [{"id": "a", "category": "git"}, {"id": "b", "category": "mcp"}]
    art = {"model": emb.LOCAL_HASH_MODEL, "vectors": {"a": q, "b": q}}
    hits = emb.cosine_search(entries, q, art, category="git", top_k=5)
    assert [h.entry["id"] for h in hits] == ["a"]


def test_load_embeddings_absent_returns_none():
    class _Src:
        def optional_artifact(self, _):
            return None
    assert emb.load_embeddings(_Src()) is None
