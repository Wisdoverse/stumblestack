# stumblestack-mcp

An MCP server that exposes the [stumblestack](https://github.com/Wisdoverse/stumblestack) pitfall knowledge base to agents.

## Tools

- `search_pitfalls(query, category?, top_k?, model_version?)` — ranked lexical search over title, symptoms, tags, and root cause. Pass an error message or short description of what went wrong.
- `get_pitfall(id)` — full markdown of a single entry (frontmatter + body).
- `list_categories()` — categories with entry counts.
- `describe_source()` — source origin and entry total.

Search is lexical for now (substring + token scoring with field weights). A vector backend can drop in later without changing the public surface.

## Install

```bash
pip install stumblestack-mcp
# or, from source:
pip install -e mcp-server/
```

Requires Python 3.10+.

## Data source

By default the server fetches `index.json` and entries from the public GitHub raw mirror of `Wisdoverse/stumblestack@main`, cached in memory.

Override with env vars:

| Variable | Purpose | Example |
| --- | --- | --- |
| `STUMBLESTACK_REPO` | Use a local clone instead of GitHub raw | `/path/to/stumblestack` |
| `STUMBLESTACK_REMOTE` | Custom remote slug + ref | `Wisdoverse/stumblestack@dev` |
| `STUMBLESTACK_TTL` | Cache TTL seconds (default 600) | `60` |

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

## Manual smoke test

```bash
pip install -e .
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | stumblestack-mcp
```

Or talk to it from any MCP-aware client over stdio.

## License

CC0-1.0.
