"""A17 index sharding: deterministic produce, manifest integrity, auto-cleanup."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"


def _seed(tmp: Path, n_per_cat=2):
    (tmp / "schemas").mkdir(parents=True)
    (tmp / "schemas" / "pitfall.schema.json").write_text(
        (REPO / "schemas" / "pitfall.schema.json").read_text(), encoding="utf-8")
    for cat in ("git", "mcp"):
        d = tmp / "pitfalls" / cat
        d.mkdir(parents=True)
        for i in range(n_per_cat):
            pid = f"{cat[0]}{i}111111-1111-4111-8111-111111111111"
            (d / f"e{i}.md").write_text(
                f'---\nid: {pid}\ntitle: "A descriptive pitfall title here {i}"\n'
                f'category: {cat}\ntags: [{cat}]\nsymptoms: ["s"]\n'
                f'root_cause: "c"\nfix: "f"\ncreated: 2026-05-29\n---\nbody\n',
                encoding="utf-8")


def _build(tmp: Path, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "build_index.py"), "--root", str(tmp), *extra],
        capture_output=True, text=True)


def test_shard_always_produces_manifest_and_shards(tmp_path):
    _seed(tmp_path)
    r = _build(tmp_path, "--shard", "always")
    assert r.returncode == 0, r.stdout + r.stderr
    manifest = json.loads((tmp_path / "index" / "_manifest.json").read_text())
    # one shard per category, manifest count == sum of shard counts
    cats = {s["category"] for s in manifest["shards"]}
    assert cats == {"git", "mcp"}
    assert manifest["count"] == sum(s["count"] for s in manifest["shards"])
    # sha256 in the manifest matches the actual shard bytes
    for s in manifest["shards"]:
        body = (tmp_path / s["path"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == s["sha256"]


def test_shard_deterministic(tmp_path):
    _seed(tmp_path)
    _build(tmp_path, "--shard", "always")
    first = (tmp_path / "index" / "_manifest.json").read_text()
    git_first = (tmp_path / "index" / "git.json").read_text()
    _build(tmp_path, "--shard", "always")
    assert (tmp_path / "index" / "_manifest.json").read_text() == first
    assert (tmp_path / "index" / "git.json").read_text() == git_first


def test_auto_below_threshold_removes_stale_shards(tmp_path):
    _seed(tmp_path)
    _build(tmp_path, "--shard", "always")
    assert (tmp_path / "index").is_dir()
    # auto with the default 2MB threshold: tiny corpus -> shards removed
    _build(tmp_path, "--shard", "auto")
    assert not (tmp_path / "index").exists()


def test_shard_concatenation_reconstructs_full_index(tmp_path):
    _seed(tmp_path)
    _build(tmp_path, "--shard", "always")
    full = json.loads((tmp_path / "index.json").read_text())
    manifest = json.loads((tmp_path / "index" / "_manifest.json").read_text())
    from_shards = []
    for s in manifest["shards"]:
        from_shards.extend(json.loads((tmp_path / s["path"]).read_text())["entries"])
    assert sorted(e["id"] for e in from_shards) == sorted(e["id"] for e in full["entries"])
