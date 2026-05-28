"""stumblestack MCP server: expose the pitfall knowledge base to agents."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .search import search
from .source import StumblestackSource

log = logging.getLogger("stumblestack_mcp")

SERVER_NAME = "stumblestack"

source = StumblestackSource.from_env()
server: Server = Server(SERVER_NAME)


def _format_hit(hit) -> dict[str, Any]:
    e = hit.entry
    return {
        "id": e.get("id"),
        "title": e.get("title"),
        "category": e.get("category"),
        "tags": e.get("tags", []),
        "symptoms": e.get("symptoms", []),
        "root_cause": e.get("root_cause"),
        "agent": e.get("agent"),
        "model_version": e.get("model_version"),
        "verified_count": e.get("verified_count", 0),
        "path": e.get("path"),
        "score": round(hit.score, 3),
        "matched_terms": hit.matched_terms,
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_pitfalls",
            description=(
                "Search the stumblestack knowledge base of agent pitfalls. "
                "Pass an error message, symptom, or short description of what went wrong. "
                "Returns ranked matches with id, title, root cause, and fix metadata. "
                "Use get_pitfall(id) to retrieve the full markdown including reproduction and fix details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Free-text query: error message, symptom, or description.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. claude-code, openai-api, mcp, shell, git).",
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 5,
                    },
                    "model_version": {
                        "type": "string",
                        "description": "Optional filter to only entries observed on a specific model version.",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_pitfall",
            description=(
                "Fetch the full markdown of a pitfall entry by id. "
                "Returns frontmatter + body (reproduction, correct usage, why)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Pitfall UUID.",
                    }
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="list_categories",
            description="List all categories present in the index, with entry counts.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        Tool(
            name="describe_source",
            description="Return metadata about the stumblestack data source (origin, entry count).",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}
    try:
        if name == "search_pitfalls":
            query = args.get("query") or ""
            hits = search(
                source.entries(),
                query,
                category=args.get("category"),
                top_k=int(args.get("top_k") or 5),
                model=args.get("model_version"),
            )
            payload = {
                "query": query,
                "count": len(hits),
                "origin": source.origin(),
                "results": [_format_hit(h) for h in hits],
            }
            return [TextContent(type="text", text=json.dumps(payload, indent=2, ensure_ascii=False))]

        if name == "get_pitfall":
            pid = args.get("id")
            if not pid:
                raise ValueError("missing required argument: id")
            try:
                record, body = source.entry_body(pid)
            except KeyError:
                return [TextContent(type="text", text=json.dumps({"error": "not_found", "id": pid}))]
            payload = {"record": record, "markdown": body, "origin": source.origin()}
            return [TextContent(type="text", text=json.dumps(payload, indent=2, ensure_ascii=False))]

        if name == "list_categories":
            counts: dict[str, int] = {}
            for entry in source.entries():
                cat = entry.get("category") or "uncategorized"
                counts[cat] = counts.get(cat, 0) + 1
            payload = {
                "origin": source.origin(),
                "categories": sorted(
                    ({"category": k, "count": v} for k, v in counts.items()),
                    key=lambda r: (-r["count"], r["category"]),
                ),
            }
            return [TextContent(type="text", text=json.dumps(payload, indent=2, ensure_ascii=False))]

        if name == "describe_source":
            idx = source.index()
            payload = {
                "origin": source.origin(),
                "schema_version": idx.get("schema_version"),
                "count": idx.get("count", 0),
            }
            return [TextContent(type="text", text=json.dumps(payload, indent=2, ensure_ascii=False))]

        raise ValueError(f"unknown tool: {name}")
    except Exception as exc:
        log.exception("tool %s failed", name)
        return [TextContent(type="text", text=json.dumps({"error": str(exc), "tool": name}))]


async def _run() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(_run())
    finally:
        source.close()


if __name__ == "__main__":
    main()
