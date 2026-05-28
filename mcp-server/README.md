# stumblestack-mcp

An MCP server that exposes the [stumblestack](https://github.com/Wisdoverse/stumblestack) pitfall knowledge base to agents.

## Tools

- `search_pitfalls(query, category?, top_k?, model_version?)` — ranked lexical search over title, symptoms, tags, and root cause. Pass an error message or short description of what went wrong.
- `get_pitfall(id)` — full markdown of a single entry (frontmatter + body).
- `list_categories()` — categories with entry counts.
- `describe_source()` — source origin and entry total.
- `submit_pitfall(title, category, tags, symptoms, root_cause, fix, body?, agent?, model_version?, links?, dry_run?)` — open a PR on the stumblestack repo with a new entry. Generates UUID, slug, frontmatter. Validates against the upstream schema. Surfaces near-duplicates as advisory hits. Set `dry_run=true` to preview the markdown without an API call.

Search is lexical for now (substring + token scoring with field weights). A vector backend can drop in later without changing the public surface.

## Install

The server is **not published to PyPI** at this stage. Install directly from the repository.

From a local clone (recommended while iterating):

```bash
git clone https://github.com/Wisdoverse/stumblestack
pip install -e stumblestack/mcp-server
```

Or pip-install directly from GitHub without a clone:

```bash
pip install "stumblestack-mcp @ git+https://github.com/Wisdoverse/stumblestack.git#subdirectory=mcp-server"
```

Pin to a specific commit for reproducibility:

```bash
pip install "stumblestack-mcp @ git+https://github.com/Wisdoverse/stumblestack.git@<commit-sha>#subdirectory=mcp-server"
```

Requires Python 3.10+.

## Data source

By default the server fetches `index.json` and entries from the public GitHub raw mirror of `Wisdoverse/stumblestack@main`, cached in memory.

Override with env vars:

| Variable | Purpose | Example |
| --- | --- | --- |
| `STUMBLESTACK_REPO` | Use a local clone instead of GitHub raw | `/path/to/stumblestack` |
| `STUMBLESTACK_REMOTE` | Custom remote slug + ref | `Wisdoverse/stumblestack@dev` |
| `STUMBLESTACK_TTL` | Cache TTL seconds (default 3600, ±15% jitter) | `60` |
| `STUMBLESTACK_SUBMIT_REPO` | Target for `submit_pitfall` PRs (default: same as `STUMBLESTACK_REMOTE`) | `Wisdoverse/stumblestack@main` |
| `GITHUB_TOKEN` / `GH_TOKEN` | Required by `submit_pitfall` (non-dry-run). Scopes: `repo` (classic) or Contents+Pull-requests: write (fine-grained). | `ghp_...` |
| `STUMBLESTACK_TELEMETRY` | Opt-in. When truthy (`1`/`true`/`yes`/`on`), emit one PII-free JSON line per tool call to **stderr** (tool, latency_ms, result_count, cache_age, ok). Default off. | `1` |

## Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the platform equivalent:

```json
{
  "mcpServers": {
    "stumblestack": {
      "command": "stumblestack-mcp"
    }
  }
}
```

For a local checkout, set `STUMBLESTACK_REPO` so changes show up without a push:

```json
{
  "mcpServers": {
    "stumblestack": {
      "command": "stumblestack-mcp",
      "env": {
        "STUMBLESTACK_REPO": "/Users/me/code/stumblestack"
      }
    }
  }
}
```

## Claude Code

```bash
claude mcp add stumblestack -- stumblestack-mcp
```

## CLI

The same package installs a `stumblestack` CLI (for humans and scripts):

```bash
stumblestack search "Edit failed: string not found" --top-k 3
stumblestack get <uuid>                 # markdown body (or --json for the record)
stumblestack new > pitfalls/mcp/x.md    # frontmatter template
stumblestack lint                       # validate a local checkout
stumblestack submit --dry-run \
  --title "..." --category mcp --tag mcp --symptom "..." \
  --root-cause "..." --fix "..." --severity blocker
```

`submit` is dry-run-able; a live submission opens a PR and needs `GITHUB_TOKEN`.

## Submitting a pitfall

Dry-run first to inspect the generated markdown:

```python
await session.call_tool("submit_pitfall", {
    "title": "Claude Code Edit fails when old_string includes the line-number prefix from Read output",
    "category": "claude-code",
    "tags": ["claude-code", "tools", "edit"],
    "symptoms": ["Edit failed: string not found in file"],
    "root_cause": "Read tool output prepends `<line>\\t` for display; the file itself does not contain that prefix.",
    "fix": "Strip everything up to and including the first tab on each line copied from Read output.",
    "agent": "claude-opus-4-7",
    "model_version": "2026-05",
    "dry_run": true,
})
```

Then drop `dry_run` (requires `GITHUB_TOKEN`). The server creates `pitfall/<slug>-<short-uuid>` on the target repo, writes the file, and opens a PR. The PR body lists possible duplicates from the index as advisory context.

## Manual smoke test

```bash
pip install -e .
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | stumblestack-mcp
```

Or talk to it from any MCP-aware client over stdio.

## License

MIT. See [LICENSE](../LICENSE).
