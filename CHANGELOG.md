# Changelog

All notable changes to stumblestack are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Note on versioning: the **project** is versioned by signed git tags (`v1.0.0`).
The MCP server Python package version in `mcp-server/pyproject.toml` is tracked
separately and is intentionally decoupled — the package is not published to PyPI
(install via git; see `docs/RELEASING.md`).

## [Unreleased]

### Added
- **Entry lifecycle (staleness management as models change).** Additive optional
  fields `status`, `observed_on`, `fixed_in`, `not_reproduced_on`, `last_verified`
  (`schema_version` stays 1). Search applies a status multiplier so stale/fixed/
  superseded entries rank below active ones (never deleted). New
  `scripts/staleness_report.py` produces a deterministic maintainer re-verification
  queue; the site shows status + "not re-verified" badges; `validate.py` enforces
  `superseded_by` referential integrity. Provenance signing via GitHub-native
  attestation (`.github/workflows/attest-index.yml`); update notifications via
  native GitHub webhooks / releases.atom (see API.md). See DESIGN.md §9d.

## [1.0.0] - 2026-05-28

First tagged release. The corpus, the validation/CI pipeline, the static site at
[stumblestack.dev](https://stumblestack.dev), the MCP server, and the HTTP API
are all in place and gated.

### Added
- **Corpus**: 54 curated pitfalls across 12 categories (anthropic-api, openai-api,
  claude-code, mcp, git, google-genai, python, shell, docker, typescript, http,
  langchain).
- **Schema** (`schemas/pitfall.schema.json`): required + recommended fields, plus
  additive optional fields `applies_to`, `severity`, `fix_code`, `_aliases`, and a
  reserved `provenance` shape. Additive — `index.json` stays `schema_version: 1`.
- **MCP server** with six tools: `search_pitfalls`, `get_pitfall`, `get_pitfalls`,
  `list_categories`, `describe_source`, `submit_pitfall` (opens a PR). Mirror-chain
  failover, TTL+jitter caching, structured submit errors, token redaction, and an
  advisory "treat fix as a hint" banner on every content response.
- **CLI** (`stumblestack`): `search`, `get`, `new`, `lint`, `submit`.
- **Static site + HTTP API**: client-side search mirroring the server ranker,
  per-entry pages, `/api/v1/index.json`, `/api/v1/p/<uuid>.json`, raw markdown
  mirrors, and a strict CSP on every page.
- **Search**: deterministic lexical ranker, specified in DESIGN.md 9c and identical
  across the Python, JS, and eval copies (enforced by a parity test). Eval harness
  with a precision@5 / recall@10 regression gate in CI.
- **Security/CI**: schema validation, unsafe-shell lint with `fix_unsafe` opt-out,
  link safety (SSRF-prone hosts rejected), index shrinkage guard, gitleaks→trufflehog
  secret scan, Dependabot, CodeQL, SHA-pinned Actions, `SECURITY.md`, and a 90-test
  suite (security, ranker parity, source failover, sanitizer XSS, schema).
- **Governance**: `docs/DESIGN.md`, `docs/DESIGN_REVIEW.md` (10-round + STRIDE),
  `docs/API.md`, `docs/STEWARDSHIP.md`, `CONTRIBUTING.md`.

### Security
- Markdown bodies and `fix_code` are sanitized/escaped before reaching the site
  (no stored XSS). The static-site CSP is delivered via `<meta http-equiv>` because
  GitHub Pages cannot set HTTP headers; header-only directives are not enforced
  (documented in `SECURITY.md`).

### Deferred
- Cross-forge mirror, cosign index signing, update webhooks, embeddings backend,
  and category sharding were scoped in the design review and intentionally deferred
  (they need external infrastructure that cannot be verified in CI). Each is tracked
  as a GitHub issue and documented with its trigger in `docs/RUNBOOK.md`.
