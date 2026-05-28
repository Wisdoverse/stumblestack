"""Additive schema fields (applies_to, severity, fix_code, _aliases, provenance)
and their ranker integration. schema_version stays 1 (DESIGN.md 9b)."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from stumblestack_mcp.search import _field_text, search

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "schemas" / "pitfall.schema.json").read_text())


def _valid_base():
    return {
        "id": "11111111-1111-4111-8111-111111111111",
        "title": "A sufficiently descriptive pitfall title",
        "category": "mcp",
        "tags": ["mcp"],
        "symptoms": ["something"],
        "root_cause": "because",
        "fix": "do x",
        "created": "2026-05-28",
    }


def _check(record):
    jsonschema.Draft202012Validator(SCHEMA).validate(record)


def test_accepts_all_new_fields():
    r = _valid_base()
    r.update({
        "severity": "blocker",
        "applies_to": {"product": "mcp", "tool": "stdio"},
        "fix_code": {"language": "python", "code": "print(1)"},
        "_aliases": ["alt phrasing"],
        "provenance": {"identity": {"github_login": "x"}, "signature": {"format": "none"}},
    })
    _check(r)  # no raise


def test_rejects_bad_severity():
    r = _valid_base(); r["severity"] = "catastrophic"
    with pytest.raises(jsonschema.ValidationError):
        _check(r)


def test_rejects_unknown_applies_to_key():
    r = _valid_base(); r["applies_to"] = {"platform": "x"}
    with pytest.raises(jsonschema.ValidationError):
        _check(r)


def test_fix_code_requires_code():
    r = _valid_base(); r["fix_code"] = {"language": "bash"}
    with pytest.raises(jsonschema.ValidationError):
        _check(r)


def test_schema_version_unchanged():
    # Additive policy: the live index must still be schema_version 1.
    idx = json.loads((REPO / "index.json").read_text())
    assert idx["schema_version"] == 1


def test_fix_code_field_text_flattens():
    entry = {"fix_code": {"language": "bash", "code": "git stash"}}
    assert _field_text(entry, "fix_code") == "bash git stash"


def test_aliases_widen_recall():
    entry = {
        "id": "a", "title": "Git reset destroyed work", "symptoms": [],
        "tags": [], "root_cause": "", "category": "git",
        "_aliases": ["lost my changes after git reset"],
        "verified_count": 0,
    }
    # A query that only matches the alias phrasing still finds the entry.
    hits = search([entry], "lost my changes", top_k=5)
    assert hits and hits[0].entry["id"] == "a"
