"""Security unit tests for the stumblestack MCP server.

Covers A42 (token redaction), A39 (link validation), A38 (rate guard).
Run: pytest mcp-server/tests
"""
from __future__ import annotations

import tempfile

import pytest

from stumblestack_mcp import submit


# ── A42: redaction ──
def test_redact_masks_exact_token():
    token = "ghp_" + "A" * 36
    msg = f"file create failed: 401 {{\"token\": \"{token}\"}}"
    out = submit.redact(msg, token)
    assert token not in out
    assert "***REDACTED***" in out


def test_redact_masks_token_shapes_without_being_told():
    for tok in ("ghp_" + "x" * 36, "gho_" + "y" * 36, "github_pat_" + "z" * 30):
        out = submit.redact(f"error body containing {tok} inline")
        assert tok not in out, tok


def test_redact_leaves_benign_text_untouched():
    msg = "branch create failed: 422 reference already exists"
    assert submit.redact(msg, "ghp_" + "A" * 36) == msg


def test_redact_ignores_short_secrets():
    # too short to be a real token; must not nuke arbitrary substrings
    out = submit.redact("the value abc appears here", "abc")
    assert out == "the value abc appears here"


# ── A39: link validation ──
@pytest.mark.parametrize("url", [
    "https://example.com",
    "http://docs.example.org/page#frag",
    "https://github.com/Wisdoverse/stumblestack/issues/1",
])
def test_validate_link_accepts_public_https(url):
    assert submit.validate_link(url) is None


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "javascript:alert(1)",
    "gopher://evil",
    "http://localhost/x",
    "http://127.0.0.1/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data",
    "http://metadata.google.internal/",
    "http://no-tld-here",
    "",
])
def test_validate_link_rejects_unsafe(url):
    assert submit.validate_link(url) is not None


# ── A38: rate guard ──
def test_rate_guard_blocks_after_cap(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("XDG_CACHE_HOME", tmp)
    monkeypatch.setattr(submit, "RATE_WINDOW_SECONDS", 60)
    monkeypatch.setattr(submit, "RATE_MAX_SUBMITS", 3)
    token = "ghp_" + "R" * 36
    for _ in range(3):
        submit._enforce_rate_limit(token)  # should not raise
    with pytest.raises(submit.SubmitError) as exc:
        submit._enforce_rate_limit(token)
    assert "rate limit" in str(exc.value).lower()
