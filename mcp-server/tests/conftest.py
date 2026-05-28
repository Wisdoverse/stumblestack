"""Shared test fixtures. Makes both the MCP package and the repo-root scripts/
importable so one `pytest mcp-server/tests` run covers server + scripts."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

for p in (str(SCRIPTS),):
    if p not in sys.path:
        sys.path.insert(0, p)


def repo_root() -> Path:
    return REPO_ROOT
