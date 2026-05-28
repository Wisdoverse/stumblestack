"""Ranker semantics (search.py). Locks the scoring contract in DESIGN.md section 9c."""
from __future__ import annotations

from stumblestack_mcp.search import FIELD_WEIGHTS, search


def _entry(**kw):
    base = {
        "id": kw.pop("id", "00000000-0000-4000-8000-000000000000"),
        "title": "",
        "symptoms": [],
        "tags": [],
        "root_cause": "",
        "category": "misc",
        "verified_count": 0,
    }
    base.update(kw)
    return base


def test_symptoms_outweighs_category():
    sym = _entry(id="a", symptoms=["zebra happens"])
    cat = _entry(id="b", category="zebra")
    hits = search([sym, cat], "zebra", top_k=5)
    assert [h.entry["id"] for h in hits] == ["a", "b"]
    assert FIELD_WEIGHTS["symptoms"] > FIELD_WEIGHTS["category"]


def test_substring_bonus_matches_non_tokenized_fragment():
    e = _entry(id="a", title="use old_string carefully")
    hits = search([e], "old_string", top_k=5)
    assert hits and hits[0].entry["id"] == "a"


def test_no_match_returns_nothing_even_if_verified():
    # A zero-lexical-match entry must NOT surface just because it is verified.
    e = _entry(id="a", title="completely unrelated", verified_count=10)
    assert search([e], "zebra", top_k=5) == []


def test_verified_count_breaks_ties():
    a = _entry(id="a", title="match", verified_count=0)
    b = _entry(id="b", title="match", verified_count=5)
    hits = search([a, b], "match", top_k=5)
    assert [h.entry["id"] for h in hits] == ["b", "a"]


def test_equal_score_tiebreak_by_id_ascending():
    a = _entry(id="bbb", title="match")
    b = _entry(id="aaa", title="match")
    hits = search([a, b], "match", top_k=5)
    assert [h.entry["id"] for h in hits] == ["aaa", "bbb"]


def test_category_filter_excludes_others():
    git = _entry(id="a", title="match", category="git")
    py = _entry(id="b", title="match", category="python")
    hits = search([git, py], "match", category="git", top_k=5)
    assert [h.entry["id"] for h in hits] == ["a"]


def test_model_filter_excludes_different_model_but_keeps_model_less():
    m1 = _entry(id="a", title="match", model_version="x")
    m2 = _entry(id="b", title="match", model_version="y")
    none = _entry(id="c", title="match")  # no model_version
    hits = search([m1, m2, none], "match", model="x", top_k=5)
    ids = {h.entry["id"] for h in hits}
    assert "a" in ids and "c" in ids and "b" not in ids


def test_empty_query_returns_nothing():
    assert search([_entry(title="anything")], "", top_k=5) == []


def test_top_k_truncates():
    entries = [_entry(id=f"{i:02d}", title="match") for i in range(10)]
    assert len(search(entries, "match", top_k=3)) == 3
