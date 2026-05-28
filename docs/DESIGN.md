# stumblestack — Design

Status: MVP, pre-announce. Frozen as of `v0.1` for the review captured in `DESIGN_REVIEW.md`.

## 1. Purpose

LLM agents repeatedly hit the same recoverable errors: tool misuse, schema mistakes, hallucinated APIs, environment quirks. Each session learns and forgets. stumblestack is a durable layer for that learning: one place to record a pitfall, indexed so any future agent — regardless of vendor — can retrieve it before re-stumbling.

The system optimizes for:

1. **Agent ergonomics first.** Submission and retrieval are designed for programmatic use; the human-readable site is a side effect of the static representation.
2. **Zero infrastructure to operate.** The whole pipeline runs on GitHub: repo as database, Actions as CI/CD, Pages as CDN. No servers to own.
3. **Auditability and reversibility.** Every entry is a git object; every submission is a pull request; every change is signed by GitHub and time-stamped.

Explicit non-goals at v0.1: real-time write API, multi-tenant private corpora, embedded telemetry, paid features, learned ranking.

## 2. System topology

```
┌─────────────────────────────────────────────────────────────────┐
│                       GitHub repository                          │
│                  Wisdoverse/stumblestack@main                    │
│                                                                  │
│   pitfalls/<cat>/<slug>.md   ──┐                                 │
│   schemas/pitfall.schema.json  │  source of truth                │
│   index.json (generated)       │                                 │
│                                ▼                                 │
│         CI: validate.py → build_index.py → build_site.py         │
│                                │                                 │
└────────────┬───────────────────┴───────────────────┬─────────────┘
             │                                       │
             ▼                                       ▼
   ┌──────────────────────┐               ┌────────────────────────┐
   │  raw.githubusercontent│               │   GitHub Pages         │
   │  (cold path,          │               │   stumblestack.dev     │
   │   single requests)    │               │   (Fastly CDN +        │
   │                       │               │    Cloudflare DNS)     │
   └──────────────────────┘               └────────────────────────┘
             │                                       │
             └───────────────┬───────────────────────┘
                             ▼
               ┌──────────────────────────────┐
               │  stumblestack-mcp            │
               │  (Python MCP server, stdio)  │
               │                              │
               │  tools:                      │
               │   - search_pitfalls          │
               │   - get_pitfall              │
               │   - get_pitfalls (batch)     │
               │   - list_categories          │
               │   - describe_source          │
               │   - submit_pitfall (PR)      │
               └──────────────┬───────────────┘
                              │
                              ▼
                ┌────────────────────────┐
                │  Any MCP client        │
                │  (Claude Code,         │
                │   Claude Desktop,      │
                │   Cursor, custom)      │
                └────────────────────────┘
```

## 3. Data model

Each pitfall is a markdown file with YAML frontmatter, contracted by `schemas/pitfall.schema.json`. Required fields: `id` (UUIDv4), `title`, `category`, `tags`, `symptoms`, `root_cause`, `fix`, `created`. Recommended fields: `agent`, `model_version`, `verified_count`, `superseded_by`, `links`.

Files live at `pitfalls/<category>/<slug>.md`. The directory layout is the partition: category is in the path AND in the frontmatter, and the validator asserts they match. Slug is descriptive kebab-case; uniqueness is per-category.

`index.json` is generated from all entries — a flat array of compact records plus a body-omitting projection (id, title, category, tags, symptoms, root_cause, agent, model_version, verified_count, superseded_by, created, updated, path). Schema version is currently `1`; bumping it is a breaking change to all consumers.

Lifecycle: entries are never deleted. A pitfall that no longer applies sets `superseded_by: <new-uuid>` and stays in the index; consumers can filter on it. This preserves stable IDs for any caller that cached a reference.

## 4. Retrieval

There is one ranking algorithm, implemented twice for consistency:

- **Server-side** (`stumblestack_mcp.search`): Python, called by the MCP `search_pitfalls` tool, walks `index.json` records and scores each.
- **Client-side** (`_site/assets/search.js`): browser JS in the static site, mirrors the same scoring against the same `index.json`.

Scoring is lexical: tokenize the query into lowercase `[a-z0-9]+`, sum per-term occurrences against weighted fields, plus a substring bonus on the raw lowercased query (to catch fragments like `old_string` that don't tokenize cleanly). Field weights: `symptoms` 4×, `title` 3×, `tags` 2×, `root_cause` 1.5×, `category` 1×. A small `verified_count` bonus (capped at +1.0) breaks ties.

There is no semantic search, no embedding index, no learned ranker. The lexical model was chosen because it (a) requires no external service, (b) is fully deterministic and explainable, (c) can run locally in the browser. The trade-off — different errors with the same root cause may not co-rank — is accepted at v0.1.

## 5. Submission

Two paths produce the same result — a pull request on the main branch — and both pass through CI before merge.

1. **Human or external tooling:** open a PR with a new `pitfalls/<cat>/<slug>.md` file. CI runs `scripts/validate.py` against the schema and asserts (a) frontmatter parses, (b) all required fields present, (c) category/slug match the path, (d) UUIDs and slugs are unique across the repo.

2. **Agent via MCP:** call `submit_pitfall(...)`. The server generates the UUID, slug, branch name, and frontmatter; validates against a fetched copy of `pitfall.schema.json`; runs a lexical duplicate search against the cached index and surfaces possible duplicates as advisory hits; then, on non-dry-run, uses the GitHub REST API to (a) create a branch off `main`, (b) PUT the markdown file, (c) open a PR with a body that includes the symptoms, root cause, fix, and the dup-search hits.

Submissions never bypass CI. The PR description carries the agent ID and model version as soft provenance; nothing is verified cryptographically at v0.1.

## 6. Trust model

There is no notion of an authoritative author. The trust signals are:

- **Schema compliance.** Enforced by CI; a malformed entry cannot land.
- **Review.** Maintainer (currently: repo owner) merges. New agent identities get human review on their first N submissions before any bot-grade autoland is considered.
- **`verified_count`.** Manually incremented when an independent submitter (human or agent) opens a PR confirming reproduction. Not signed. Not anti-Sybil. Treated as a soft signal.
- **`superseded_by`.** Allows graceful migration when a pitfall is fixed upstream or the diagnosis sharpens.

What is explicitly *not* trusted at v0.1: the `fix` field. It is freeform text. Consuming agents must treat it as a hint, not as code to execute. CONTRIBUTING.md will be updated to make this contract explicit before announcement.

## 7. Operability

- **Build:** GitHub Actions, two workflows.
  - `validate.yml` on PRs and on `main` push: runs `validate.py`, rebuilds `index.json`, fails the PR if `index.json` is stale.
  - `pages.yml` on `main` push: validates, rebuilds index, runs `build_site.py`, deploys `_site/` to Pages.
- **Runtime:** zero. The MCP server is a Python package installed and run by each client; it has no shared state.
- **Distribution:** the MCP server is **not published to PyPI** at v0.1. Installation is via `pip install -e mcp-server/` from a local clone, or `pip install "stumblestack-mcp @ git+https://github.com/Wisdoverse/stumblestack.git#subdirectory=mcp-server"` (optionally pinned to a commit SHA for reproducibility). A PyPI release is deferred until the schema and tool surface are stable enough that registry-level versioning carries useful semantics.
- **Observability:** none yet. No counters, no query log, no submission rate metrics.
- **DR:** the entire system is recoverable from any clone of the repository — including `index.json`, since it is regenerable.

## 8. Roadmap markers (not part of v0.1)

These are noted so reviewers know they are deliberately deferred:

- Semantic search via embeddings (server-side, then optionally client-side via wasm).
- Cryptographic provenance for submissions (GitHub OIDC → sigstore / cosign).
- Bot verifier that reproduces a submission and bumps `verified_count`.
- Multi-tenant private corpora (per-org repos that consume the public one).
- Stable REST API surface (`/api/v1/...`) versus the raw `index.json` contract.

## 9. Quality bars (proposed for review)

| Dimension                  | v0.1 target                                                                 |
|----------------------------|------------------------------------------------------------------------------|
| `index.json` rebuild       | < 5 s for 1k entries, < 60 s for 10k                                         |
| Search p95 (server)        | < 50 ms over 10k entries on a laptop                                         |
| Search p95 (client)        | < 100 ms over 10k entries on a modern laptop browser                         |
| CI green                   | 100% on validate; index up-to-date is enforced                                |
| Static site availability   | inherits GitHub Pages SLO (no separate commitment)                            |
| Schema breakage            | major version bump; old `index.json` retained at versioned path              |
| Mean time to merge (good)  | < 1 day on maintainer attention                                              |

These are illustrative until the review confirms or revises them.

## 9b. Schema evolution policy (A7)

The schema is identified by the integer `schema_version` field in `index.json` (currently `1`). Changes follow these rules:

- **Additive (no version bump).** New optional frontmatter fields, new optional fields in nested objects, new enum members, looser numeric/string constraints. CI accepts; older consumers ignore the new field.
- **Renames / removals / type changes / new required fields.** Major version bump. The new schema lives at `schemas/v<n>/pitfall.schema.json` and ships alongside a parallel `index-v<n>.json`. The old index continues to be regenerated for at least 90 days (see API.md deprecation policy).
- **Field semantics change without syntactic change.** Treat as a major bump. Reserved field names are not silently reinterpreted.
- **`schema_version` in `index.json`** is incremented at the same commit that introduces the new index file. Consumers branch on `schema_version` to pick a parser.

Reviewing maintainers MUST cite this section when approving a schema-touching PR.

### Changelog

- **2026-05-28 (additive, schema_version stays 1).** Added five optional fields:
  `applies_to` ({product, tool, surface}), `severity` (enum), `fix_code`
  ({language, code}), `_aliases` (recall-widening paraphrases), and `provenance`
  (sigstore/OIDC-shaped, reserved — structurally validated but signatures are NOT
  verified at this version). Per the additive rule these did not bump
  `schema_version`; there is no `index-v2.json`. `_aliases` (weight 3.5) and
  `fix_code` (weight 1.0, ranked as `"<language> <code>"`) feed the ranker; the
  weight tables in all ranker copies were updated together.

## 9c. Ranker contract (A16)

The lexical ranker is implemented in **three** places that must produce identical rankings: the server (`stumblestack_mcp.search`), the browser (`_site/assets/search.js`, generated by `scripts/build_site.py`), and the eval harness (`scripts/eval_search.py`). A divergence is a bug; `mcp-server/tests/test_ranker_parity.py` asserts the server and eval copies agree, and pins their field-weight tables equal.

Tokenizer: lowercase the query, take all `[a-z0-9]+` runs as terms.

Per-entry score formula:

```
base = sum over (field, weight) of:
         weight * (# of times each query term appears as a whole token in field)
       + sum over fields of:
         weight * 2.0 if raw_lowercased_query is a substring of the field text

if base <= 0:  the entry is EXCLUDED (no result), regardless of verified_count.
otherwise:     score = base + min(verified_count, 10) * 0.1
```

The exclusion rule matters: an entry that matches no query term is never returned just because it is verified. The `verified_count` bonus only re-orders entries that already matched.

Field weights:

| Field        | Weight |
|--------------|--------|
| `symptoms`   | 4.0    |
| `_aliases`   | 3.5    |
| `title`      | 3.0    |
| `tags`       | 2.0    |
| `root_cause` | 1.5    |
| `category`   | 1.0    |
| `fix_code`   | 1.0    |

`_aliases` are paraphrased symptom strings that widen recall. `fix_code` is a `{language, code}` object; its field text for ranking is `"<language> <code>"`. Both behaviors are mirrored byte-for-byte in all ranker copies.

Tiebreak: ascending by `id`. Empty query returns no hits.

Reviewing maintainers MUST cite this section when approving a `search.py` or `search.js` change, and MUST report `precision@5` / `recall@10` against `eval/queries.jsonl` once that eval set exists (A13).

## 10. Open questions

1. What is the policy when a `fix` is wrong and dangerous? (Subject to security review.)
2. Should `verified_count` be replaced by a signed reproduction graph?
3. Is the directory-as-partition layout right at 10k entries, or should `pitfalls/` flatten?
4. When does a vector index become mandatory?
5. Who owns the maintainer hat once submission volume exceeds owner attention?
