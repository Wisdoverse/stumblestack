# Stewardship

This document records who maintains stumblestack, how decisions are made, and what the project will not do.

## Maintainers

At v0.1 the project is maintained by **Wisdoverse** (`dev@wisdoverse.com`). Maintainership is single-owner; when this changes, the change ships as a PR against this file.

## Review window

For the first **90 days** of public submissions (counted from the announce date, not the repo creation date), **every PR is reviewed by a human maintainer before merge**. No bot-grade autoland is enabled in this window.

After the window, any move toward automated merge requires:

1. A documented agent in `.github/agent_allowlist.yaml` with a clean history (≥10 accepted PRs, zero rejections in the prior 30 days).
2. An additional CI gate: signed provenance (sigstore via GitHub OIDC) on the submission commit.
3. A second human review on the PR that enables autoland for that agent.

## Decision authority

| Change class                                | Authority required                                       |
|---------------------------------------------|----------------------------------------------------------|
| Pitfall entry add / edit                     | Single maintainer merge                                  |
| Additive schema field (existing schema_version) | Single maintainer merge after review                  |
| Breaking schema bump (new `schema_version`)  | Maintainer + 7-day RFC issue with at least one external comment |
| Ranker change (`scripts/build_index.py` or `search.py`) | Maintainer + reported precision\@5 / recall\@10 from `eval/queries.jsonl` (A13, deferred) |
| Security policy change (`SECURITY.md`)       | Maintainer                                               |
| Maintainer roster change                      | Outgoing maintainer + PR signed by incoming maintainer  |
| License change                                | All maintainers + 14-day public notice; would invalidate prior contributors' implicit terms |

## Vendor neutrality

stumblestack does not advantage any model vendor in ranking, schema, or listing. Concretely:

- No vendor's pitfalls are boosted in the ranker.
- No category (claude-code, openai-api, etc.) is privileged in the UI.
- No paid placement of any kind, ever, in the public corpus.
- Vendors are welcome to contribute. Vendors are not exempt from review.

## What stumblestack will not do at v0.1

- Will not paywall the public corpus, ever.
- Will not require account creation to read.
- Will not collect or log per-query identifiers, IPs, or user-agent strings of search clients beyond what GitHub Pages already aggregates.
- Will not run a paid bug-bounty program.
- Will not publish to PyPI until the MCP tool surface is stable enough that registry-level versioning carries useful semantics.

## Sustainability

The static topology costs effectively nothing to run at v0.1 scale. Sustainability work is deferred until the corpus is large enough to justify it, with these guardrails:

- The public corpus stays public and free, indefinitely.
- A future paid surface, if any, would be confined to **private mirrors for proprietary stacks** and **verified-author plans for vendors** — never the public corpus.
- A maintainer transition will be announced at least 30 days in advance.

## Reference

- Security disclosure: [SECURITY.md](../SECURITY.md)
- Submission contract: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Architecture and trust model: [docs/DESIGN.md](./DESIGN.md)
- Allowlist (record-only, grants nothing): `.github/agent_allowlist.yaml`
