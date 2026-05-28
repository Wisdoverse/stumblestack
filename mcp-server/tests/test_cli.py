"""CLI smoke tests (stumblestack_mcp.cli)."""
from __future__ import annotations

import json
from pathlib import Path

from stumblestack_mcp import cli

REPO = Path(__file__).resolve().parents[2]


def test_new_prints_template(capsys):
    rc = cli.cli_main(["new"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "title:" in out and "TODO" in out and "created:" in out


def test_search_json(capsys, monkeypatch):
    monkeypatch.setenv("STUMBLESTACK_REPO", str(REPO))
    rc = cli.cli_main(["search", "edit", "--top-k", "2", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list) and len(data) <= 2
    if data:
        assert {"id", "title", "category", "score"} <= set(data[0])


def test_submit_dry_run(capsys, monkeypatch):
    monkeypatch.setenv("STUMBLESTACK_REPO", str(REPO))
    rc = cli.cli_main([
        "submit", "--dry-run",
        "--title", "Some sufficiently long pitfall title",
        "--category", "mcp", "--tag", "mcp",
        "--symptom", "boom", "--root-cause", "because", "--fix", "do y",
        "--severity", "minor",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "severity: minor" in out and "title:" in out


def test_submit_invalid_reports_fields(capsys, monkeypatch):
    monkeypatch.setenv("STUMBLESTACK_REPO", str(REPO))
    rc = cli.cli_main([
        "submit", "--dry-run",
        "--title", "x",            # too short
        "--category", "BadCat",    # not kebab
        "--tag", "mcp", "--symptom", "s", "--root-cause", "c", "--fix", "f",
    ])
    err = capsys.readouterr().err
    assert rc == 1
    assert "category" in err and "title" in err
