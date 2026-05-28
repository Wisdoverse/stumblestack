"""Differential test: the MCP ranker (search.py) and the eval-harness ranker
(scripts/eval_search.py) MUST produce identical rankings. They are independent
copies of the same algorithm (DESIGN.md 9c); this converts "remember to edit both"
into an enforced invariant. The JS copy in build_site.py is checked structurally
(weights) in test_scripts.py."""
from __future__ import annotations

import eval_search  # from scripts/ via conftest path
from stumblestack_mcp.search import FIELD_WEIGHTS, search


def _corpus():
    return [
        {"id": "a", "title": "Edit failed string not found", "symptoms": ["old_string does not match"],
         "tags": ["edit"], "root_cause": "line number prefix", "category": "claude-code", "verified_count": 0},
        {"id": "b", "title": "max_tokens required", "symptoms": ["field required"],
         "tags": ["api"], "root_cause": "param omitted", "category": "anthropic-api", "verified_count": 3},
        {"id": "c", "title": "reasoning model rejects max_tokens", "symptoms": ["use max_completion_tokens"],
         "tags": ["openai"], "root_cause": "renamed", "category": "openai-api", "verified_count": 0},
        {"id": "d", "title": "git reset hard data loss", "symptoms": ["uncommitted gone"],
         "tags": ["git"], "root_cause": "overwrites tree", "category": "git", "verified_count": 1},
        {"id": "e", "title": "unrelated entry", "symptoms": ["nothing"],
         "tags": ["misc"], "root_cause": "n/a", "category": "misc", "verified_count": 9},
    ]


QUERIES = [
    "old_string not found",
    "max_tokens required",
    "max_completion_tokens",
    "git reset",
    "zebra unicorn nonexistent",  # no match
    "",                            # empty
    "model",                       # multi-entry partial
]


def test_weights_identical():
    assert eval_search.FIELD_WEIGHTS == FIELD_WEIGHTS


def test_rankings_identical_across_queries():
    corpus = _corpus()
    for q in QUERIES:
        for k in (5, 10):
            py = [h.entry["id"] for h in search(corpus, q, top_k=k)]
            ev = eval_search.rank(corpus, q, k)
            assert py == ev, f"divergence for query={q!r} k={k}: search={py} eval={ev}"
