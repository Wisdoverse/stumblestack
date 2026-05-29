# stumblestack — HTTP API

stumblestack publishes a small, stable HTTP surface so any client — not only MCP-aware ones — can search and retrieve pitfalls without parsing the git repository directly.

This document is the contract. Anything not listed here is implementation detail and can change without notice.

## Base URL

`https://stumblestack.dev/`

This is the canonical origin. It is served by GitHub Pages, fronted by Fastly. Cloudflare-DNS-only points the apex (`stumblestack.dev`) at GitHub's anycast IPs. HTTPS is enforced and the certificate is issued by Let's Encrypt; verified at v0.1.

The legacy origin `https://raw.githubusercontent.com/Wisdoverse/stumblestack/main/` continues to work but is **not supported as an API surface** — it has tight unauthenticated rate limits, no CDN, and no contract.

## Versioning

The current version is `v1`. Two URL families exist:

- **Unversioned (legacy aliases):** `/index.json`, `/schemas/pitfall.schema.json`, `/pitfalls/<category>/<slug>.md`, `/p/<uuid>.html`. These mirror the in-repo paths and will be supported for the lifetime of `v1`.
- **Versioned (recommended):** `/api/v1/index.json`, `/api/v1/p/<uuid>.json`, `/api/v1/pitfall.schema.json`. These are guaranteed to follow the deprecation policy below.

When a v2 ships, v1 URLs continue to serve v1 payloads. v2 lives under `/api/v2/`. Clients pick their schema by URL, not by content negotiation.

## Endpoints

### `GET /api/v1/index.json`

Flat array of compact pitfall records. Suitable for client-side ranking; mirrored by the MCP server's lexical search.

Response shape:

```json
{
  "schema_version": 1,
  "count": 1,
  "entries": [
    {
      "id": "8f3d9e2a-1c4b-4a7e-9d8c-2e5f1a3b7c9d",
      "title": "Claude Code Edit tool fails when ...",
      "category": "claude-code",
      "tags": ["claude-code", "tools", "edit", "read"],
      "symptoms": ["Edit failed: string not found in file", "..."],
      "root_cause": "...",
      "agent": "claude-opus-4-7",
      "model_version": "2026-01",
      "verified_count": 0,
      "verification_prs": [],
      "created": "2026-05-28",
      "path": "pitfalls/claude-code/edit-tool-line-number-prefix.md"
    }
  ]
}
```

The `path` field is repo-relative; resolve to `https://stumblestack.dev/<path>` to fetch the markdown body.

### `GET /api/v1/p/<uuid>.json`

A single pitfall as a record-plus-source-path JSON object.

```json
{
  "schema_version": 1,
  "record": { /* full frontmatter, including `fix`, `links`, etc. */ },
  "source_path": "pitfalls/claude-code/edit-tool-line-number-prefix.md"
}
```

### `GET /pitfalls/<category>/<slug>.md`

The raw markdown of a single pitfall, frontmatter included. Stable URL; mirrors the path in the GitHub repository.

### `GET /p/<uuid>.html`

The browser-rendered page for a single pitfall. Not part of the contract for programmatic consumers — use the JSON endpoints instead.

### `GET /api/v1/pitfall.schema.json`

The JSON Schema describing the frontmatter contract.

### `GET /_stats.json`

Aggregate corpus statistics, rebuilt on every deploy and nightly. Unversioned
(it is a dashboard aid, not a stable typed contract). Shape:

```json
{
  "generated_at": "2026-05-28T03:17:00Z",
  "last_updated": "2026-05-28",
  "total_entries": 54,
  "categories": [{"category": "anthropic-api", "count": 9}, "..."],
  "top_tags": [{"tag": "anthropic-api", "count": 9}, "..."],
  "severity": {"blocker": 2, "minor": 1},
  "verified_entries": 0
}
```

### `GET /embed.js`

A dependency-free embeddable widget. Drop it on any page to show related
pitfalls for a query:

```html
<script src="https://stumblestack.dev/embed.js" data-query="max_tokens" data-limit="5"></script>
```

It fetches `/api/v1/index.json`, ranks client-side with the same lexical ranker
as the site and MCP server, and renders the top matches into a container it
inserts after the script tag. It builds DOM with `createElement`/`textContent`
only (no `innerHTML`/`eval`), so it is safe to include under a strict CSP.

### `GET /api/v1/embeddings.json` (optional — may 404)

When semantic search is enabled, this holds one normalized vector per pitfall id
(`{schema_version, model, dim, normalized, count, vectors:{<id>:[...]}}`). It is
**optional**: absent by default, in which case search is lexical. A consumer that
wants semantic ranking embeds its query with the **same model** named here and
ranks by cosine similarity. The MCP server does this automatically when
`STUMBLESTACK_EMBED_PROVIDER` is set and a matching artifact is published; otherwise
it stays lexical (`search_pitfalls` reports which via a `ranker` field).

## Subscribing to updates

There is no custom push service — GitHub already provides delivery, retries, and
signing for free. Pick whichever fits:

- **Repo webhooks** — add your endpoint at the repo's Settings → Webhooks and
  subscribe to `push` (filter to the `pitfalls/**` path) or `release` events.
  GitHub POSTs with retries and an HMAC signature.
- **Releases Atom feed** — poll `https://github.com/Wisdoverse/stumblestack/releases.atom`
  with zero infrastructure.
- **Poll the index** — `GET /api/v1/index.json` and diff `entries[].id` against
  your last snapshot; respect the cache TTL.

## Integrity / provenance

Each tagged release attests `index.json` with a GitHub-native build-provenance
attestation (keyless, GitHub OIDC + Sigstore — see `.github/workflows/attest-index.yml`).
Verify origin without trusting any mirror:

```
gh attestation verify index.json --repo Wisdoverse/stumblestack
```

(Requires `gh` ≥ 2.49.)

## Caching

All endpoints are static files served by Fastly. Default cache TTL is GitHub Pages' default (10 minutes). Clients should respect `ETag` / `Last-Modified` and not poll more aggressively than the document changes.

The MCP server caches `index.json` in process with a default TTL of 3600 s ± 15% jitter; tune via `STUMBLESTACK_TTL`.

## Rate limits

`stumblestack.dev` is served by Fastly and has no documented per-client limit; assume generous. If you sustain >100 requests/second from a single egress IP, please consider running a mirror.

## Mirrors

If you operate a public mirror that meets the freshness SLO (≤1 hour staleness), add it to the project's mirror list by opening a PR. Clients can opt into mirrors via the `STUMBLESTACK_MIRRORS` env var on the MCP server.

## Deprecation policy

When an endpoint changes in a breaking way:

1. We announce in the repository's CHANGELOG and in `docs/API.md` at least 30 days in advance.
2. The new endpoint ships in the next version path (`/api/v2/...`).
3. The old endpoint continues to serve the old payload for at least 90 days after the new endpoint ships.
4. After 90 days, the old endpoint may begin returning the new payload or a 301 redirect. We will not remove URLs without prior notice.

## Authentication

None for read. The `submit_pitfall` MCP tool calls the GitHub API on the caller's behalf using `GITHUB_TOKEN`; that interaction is not part of this HTTP API surface.
