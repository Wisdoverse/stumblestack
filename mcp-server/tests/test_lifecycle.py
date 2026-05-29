"""Lifecycle (v1.1): status field, ranker deprioritization, staleness report,
schema acceptance, and superseded_by referential integrity."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import staleness_report

from stumblestack_mcp.search import STATUS_WEIGHTS, search

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
SCHEMA = json.loads((REPO / "schemas" / "pitfall.schema.json").read_text())


def _e(**kw):
    base = {"id": kw.pop("id", "a"), "title": "match", "symptoms": [], "tags": [],
            "root_cause": "", "category": "git", "verified_count": 0}
    base.update(kw)
    return base


# ── ranker deprioritization ──
def test_active_outranks_fixed_upstream():
    active = _e(id="a", status="active")
    fixed = _e(id="b", status="fixed-upstream")
    hits = search([fixed, active], "match", top_k=5)
    assert [h.entry["id"] for h in hits] == ["a", "b"]  # active first despite equal base


def test_status_weights_ordering():
    assert (STATUS_WEIGHTS["active"] > STATUS_WEIGHTS["unverified-stale"]
            > STATUS_WEIGHTS["fixed-upstream"] > STATUS_WEIGHTS["superseded"]
            > STATUS_WEIGHTS["retired"])


def test_missing_status_treated_as_active():
    plain = _e(id="a")
    active = _e(id="b", status="active")
    # Identical base + identical (active) weight => tiebreak by id ascending.
    hits = search([plain, active], "match", top_k=5)
    assert [h.entry["id"] for h in hits] == ["a", "b"]


def test_retired_still_returned_just_lower():
    retired = _e(id="a", status="retired")
    hits = search([retired], "match", top_k=5)
    assert hits and hits[0].entry["id"] == "a"  # not filtered out, just penalized


# ── schema ──
def _valid():
    return {"id": "11111111-1111-4111-8111-111111111111",
            "title": "A sufficiently descriptive title", "category": "git",
            "tags": ["git"], "symptoms": ["s"], "root_cause": "c", "fix": "f",
            "created": "2026-05-29"}


def test_schema_accepts_lifecycle_fields():
    r = _valid()
    r.update({"status": "fixed-upstream", "fixed_in": "claude-opus-4-5",
              "observed_on": ["claude-opus-4-1"], "not_reproduced_on": ["claude-opus-4-5"],
              "last_verified": "2026-05-29"})
    jsonschema.Draft202012Validator(SCHEMA).validate(r)


def test_schema_rejects_bad_status():
    r = _valid()
    r["status"] = "deprecated"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(r)


# ── staleness report ──
def test_staleness_flags_non_active_and_aged():
    entries = [
        _e(id="fresh", created="2026-05-20", last_verified="2026-05-20"),
        _e(id="stale", created="2025-01-01", last_verified="2025-01-01"),
        _e(id="fixed", status="fixed-upstream", created="2026-05-20"),
        _e(id="refuted", status="active", not_reproduced_on=["m1", "m2"], created="2026-05-20"),
    ]
    flagged = {f["id"]: f for f in staleness_report.assess(entries, "2026-05-29", 180, 2)}
    assert "fresh" not in flagged
    assert "stale" in flagged and "fixed" in flagged and "refuted" in flagged


# ── validate referential integrity (subprocess over a tmp repo) ──
def _write(root: Path, slug: str, *, pid: str, extra: str = ""):
    d = root / "pitfalls" / "git"
    d.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"id: {pid}",
        'title: "A sufficiently descriptive pitfall title"',
        "category: git",
        "tags: [git]",
        'symptoms: ["s"]',
        'root_cause: "c"',
        'fix: "f"',
    ]
    if extra:
        lines.extend(extra.split("\n"))
    lines += ["created: 2026-05-29", "---", "", "body", ""]
    (d / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")


def _seed(tmp: Path):
    (tmp / "schemas").mkdir(parents=True)
    (tmp / "schemas" / "pitfall.schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")


def _validate(tmp: Path):
    return subprocess.run([sys.executable, str(SCRIPTS / "validate.py"), "--root", str(tmp)],
                          capture_output=True, text=True)


def test_validate_rejects_dangling_superseded_by(tmp_path):
    _seed(tmp_path)
    _write(tmp_path, "a", pid="11111111-1111-4111-8111-111111111111",
           extra='status: superseded\nsuperseded_by: "99999999-9999-4999-8999-999999999999"')
    r = _validate(tmp_path)
    assert r.returncode == 1 and "superseded_by" in r.stdout


def test_validate_rejects_superseded_without_pointer(tmp_path):
    _seed(tmp_path)
    _write(tmp_path, "a", pid="22222222-2222-4222-8222-222222222222", extra="status: superseded")
    r = _validate(tmp_path)
    assert r.returncode == 1 and "requires a `superseded_by`" in r.stdout


def test_validate_accepts_valid_supersession(tmp_path):
    _seed(tmp_path)
    new = "33333333-3333-4333-8333-333333333333"
    old = "44444444-4444-4444-8444-444444444444"
    _write(tmp_path, "new", pid=new)
    _write(tmp_path, "old", pid=old, extra=f'status: superseded\nsuperseded_by: "{new}"')
    r = _validate(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
