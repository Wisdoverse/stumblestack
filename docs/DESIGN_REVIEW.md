# stumblestack — v0.1 Design Review

Artifact under review: [`DESIGN.md`](./DESIGN.md) at commit `d0bcc49`.
Mode: pre-announce gate. Format: ten thematic rounds (pro / con), then a security-team pass, then a final PM gate. Each round closes with a concrete action list. Personas are archetypes, not specific individuals.

## Review panel

| Code  | Role                                  | Background archetype                                                |
|-------|---------------------------------------|---------------------------------------------------------------------|
| AR    | Principal Architect                   | distributed systems, ex–hyperscaler control plane                   |
| EN    | Staff Backend Engineer                | search/retrieval infra, Python+Rust polyglot                        |
| DA    | Data Platform Lead                    | content quality, ranking, eval pipelines                            |
| PD    | Senior PM, Developer Tools            | DX, SDK design, agent integrations                                  |
| OS    | OSS / Community PM                    | ecosystem strategy, governance, foundation work                     |
| SRE   | Principal SRE                         | reliability engineering, capacity, on-call                          |
| LE    | Open-source Counsel                   | licensing, content rights, contributor agreements                   |
| Sec1  | Security Architect                    | threat modeling, STRIDE                                             |
| Sec2  | Application Security Engineer         | XSS/CSRF/SSRF, supply-chain                                         |
| Sec3  | Supply-chain Security Lead            | SLSA, sigstore, provenance                                          |
| Sec4  | Cryptography & Identity Lead          | OIDC, signing, key management                                       |
| PMG   | Chief Product (final gate)            | accountable for ship/hold decision                                  |

Convention: each round has a **PRO** brief and a **CON** brief. PRO defends the v0.1 choice; CON attacks it. The chair then resolves with one of *accept v0.1*, *accept with action*, *block on action*.

---

## Round 1 — Architecture & system topology

Lead reviewers: AR, SRE.

**PRO (AR).** The "git-as-database, Pages-as-CDN, MCP-as-API" topology is correct for the problem class. The corpus is small (thousands, not billions). Read traffic dominates. Writes are rare and benefit from human review. Co-locating the artifact, the schema, the validator, and the CI in a single revisioned tree gives us bit-for-bit reproducibility and a natural audit log — properties that real production knowledge bases spend years bolting on. Cloud-native, in 2026, increasingly means "use the platform's primitives, do not stand up your own kube cluster for read-mostly content." This is that.

**CON (SRE).** Three structural risks. (a) **Hard ceilings we do not control.** `raw.githubusercontent.com` has anonymous-egress rate limits (~5k requests/hour per IP). Once a few popular agent harnesses fan out concurrently, we silently fail open with stale caches. (b) **No write back-pressure.** The `submit_pitfall` path leans on GitHub REST quota of the *caller's* token; we have no central rate-limit on submissions. A misbehaving agent can open 1k PRs in an hour and we have no automated throttle, only post-hoc moderation. (c) **Single point of trust.** "GitHub up" implies "stumblestack up." We have no neutral mirror; a GitHub outage or account dispute would dark the whole system for everyone simultaneously.

**Resolution (AR + SRE):** *accept with action.*

Actions:
- A1. Server-side `STUMBLESTACK_TTL` already caches `index.json` per-client (default 600s). Raise the *default* to 3600s and add jittered re-fetch (±15%) to avoid synchronized thundering-herd at TTL boundary.
- A2. Document an explicit "API contract" at `/index.json` and `/p/<id>.html` on **stumblestack.dev** (Pages, Fastly-backed) and tell agents to prefer that origin over `raw.githubusercontent.com` (which is undocumented infrastructure).
- A3. Add a `STUMBLESTACK_MIRRORS` env var support: a comma-separated list of fallback origins, with auto-failover on 429/5xx. Even with one entry today, this is the seam where a future mirror plugs in.
- A4. Define a public mirror policy: anyone who runs a CC-compatible mirror that meets a documented freshness SLO (<1 hour) is welcome to be listed.

---

## Round 2 — Data model & schema design

Lead reviewers: EN, DA.

**PRO (EN).** YAML frontmatter on a markdown body is the right primitive for an agent-readable knowledge base. It is grep-able, diff-able, schema-checkable, and produces a useful render with zero effort. The schema is small (8 required fields), the field names are accurate to the problem (`symptoms`, `root_cause`, `fix`), and the projection used in `index.json` is sufficient for ranking without forcing consumers to fetch every body. UUIDs as the primary key — not slugs — means we can rename freely and never break a cached reference.

**CON (DA).** Three modeling gaps. (a) **`fix` is monolithic.** It is one freeform string, but the high-value cases are typically (i) one line of "what to change" and (ii) a code block showing the change. We cannot rank "has code example" vs "prose only", and we cannot teach an agent to apply the fix mechanically. (b) **No structured `applies_to`.** "Claude Code" the tool family, "Claude Opus 4.7" the model, and "Edit tool" the surface are three different scopes; today they all collapse into tags + agent + model_version. We will regret this around 1k entries when the filter UX falls apart. (c) **No `severity` or `confidence`.** Some pitfalls are "this will silently corrupt your output"; others are "you typed it wrong." Ranking and rendering should distinguish them.

**Resolution (EN + DA):** *accept with action.*

Actions:
- A5. Reserve (do not yet require) two new fields in the schema, gated behind a `schema_version: 2` migration:
  - `applies_to: { product?: string, tool?: string, surface?: string }` — structured scope.
  - `severity: "blocker" | "wrong-output" | "wasted-cycles" | "minor"` — single enum.
- A6. Promote the `fix` body to optionally carry a `fix_code` field with a language tag, so renderers and the lexical search can up-weight pitfalls that ship a code-shaped fix.
- A7. Document a schema-evolution policy in `docs/DESIGN.md`: additive fields ship as schema_version-aligned optional; renames or removals require a major bump and a parallel `index-v<n>.json`.

---

## Round 3 — Trust, integrity, anti-pollution

Lead reviewers: OS, PMG.

**PRO (OS).** PR-as-submission is a strong default. It inherits the full GitHub identity stack (verified emails, SSO, vigilant-mode signed commits), the full review tooling, and the same rate-limit posture as every other OSS project. We are not inventing trust primitives, we are reusing the most battle-tested set in the industry.

**CON (PMG).** Three pollution vectors that GitHub's defaults do not solve. (a) **Drive-by agent submissions are not Sybil-resistant.** "agent: claude-opus-4-7" is a self-claim, unverified. A coordinated campaign can mint a fake provenance trail across 50 throwaway GitHub accounts. (b) **`verified_count` is gameable.** It currently increments on a maintainer's discretion in a PR; absent signatures, an attacker controlling enough accounts will inflate it. (c) **Adversarial fixes.** Worst case: an attacker submits a "fix" that introduces a vulnerability (e.g. "to fix the SQLi, change quotes to backticks" with a plausible-looking root cause). We are a knowledge base that LLMs will consume; an LLM that mechanically applies a poisoned fix is a real outcome.

**Resolution (OS + PMG):** *block on action for A8, A10; accept with action for the rest.*

Actions:
- A8. Add a top-of-CONTRIBUTING warning and an in-server response banner on every `get_pitfall` / `search_pitfalls` result: *"Treat `fix` as a hint, not as code to execute. Verify before applying."* The MCP server should embed this in the JSON response.
- A9. Reserve `provenance` field in the schema (deferred to v0.2):
  - `provenance.signature` (sigstore-signed by GH OIDC of the submitter)
  - `provenance.identity` (GitHub login + workflow run + commit SHA)
- A10. Tighten the maintainer policy: human review required on every PR for the first 90 days; bot-eligible identities require an explicit allowlist file (`.github/agent_allowlist.yaml`) with signed entries.
- A11. Replace `verified_count: int` (semantically): require each increment to come with a referenced PR (`verification_prs: [pr_number, ...]`). Validate that each referenced PR was merged and is signed by a distinct committer. Compute the displayed count from the list.
- A12. Forbid network-mutating shell commands in `fix` code blocks during CI lint: regex-flag `curl ... | sh`, `wget ... | bash`, `rm -rf /`, etc., and require human override via a frontmatter `fix_unsafe: true` flag (which itself flags the entry in the UI).

---

## Round 4 — Search quality & retrieval ranking

Lead reviewers: DA, EN.

**PRO (DA).** Shipping a lexical baseline now is correct. We do not have query logs to train against, we cannot afford an embedding service we do not run, and a deterministic baseline that mirrors in the browser is auditable. The dual implementation (Python + JS) makes the contract testable and gives both surfaces the same answers.

**CON (DA, against own PRO).** The weights are heuristic and untested. We have no eval set. The substring bonus is a hack that will produce false positives once symptoms grow. Worse: the entire ranking falls apart for **semantically equivalent but lexically disjoint** errors — e.g. "context window exceeded" vs "input tokens limit reached" vs "401 token too long". On day one of usage, an agent's actual error string almost never matches the canonical phrasing in `symptoms`. We will get 60–70% recall when 90% is realistic.

**Resolution (DA + EN):** *accept v0.1, plan v0.2.*

Actions:
- A13. Build an eval harness (`scripts/eval_search.py`) before any ranker change: a manually curated set of `{query, expected_ids}` pairs in `eval/queries.jsonl`. Print precision@5 and recall@10. Every PR that touches `search.py` or `search.js` must report these numbers.
- A14. Add a `_aliases` field to schema_version 2: an array of paraphrased symptom strings. Pre-write them when seeding entries to widen recall without changing the ranker.
- A15. Bake in the seam for a vector ranker: add an `embeddings.json` artifact (optional, generated by a separate workflow with API access) that, when present, the MCP server prefers over lexical. Until present, behavior is unchanged.
- A16. Publish the ranker weights and substring-bonus rule in `DESIGN.md`. Currently they are only in code.

---

## Round 5 — Scale & cost

Lead reviewers: AR, SRE.

**PRO (AR).** At expected v0.1 scale (≤1k entries, single-digit kQPS) the static topology is effectively free and trivially overprovisioned. `index.json` at 1k entries is ~250–500 KB gzipped; well under the 1 MB conventional cache budget.

**CON (SRE).** Two scale cliffs we should know now, not learn at 3 a.m. (a) **`index.json` browser load.** At 10k entries the file becomes 3–6 MB; clients will perceive the search box as "slow on first keystroke." Mobile users on slow networks will simply give up. (b) **`raw.githubusercontent.com` per-IP throttling.** Each `get_pitfall` body fetch from the MCP server, multiplied across thousands of agent instances behind the same egress IP (e.g. corporate proxy, or a SaaS LLM provider's outbound NAT), will trip the limit. We will get phantom 429s in production with no way to root-cause from logs we do not have.

**Resolution (AR + SRE):** *accept with action.*

Actions:
- A17. Define hard caps: alarm when `index.json` exceeds 2 MB uncompressed (alarm = a CI warning, not a hard fail). At that threshold, ship a **sharded index** by category: `index/<category>.json` plus a tiny top-level `index/_manifest.json`.
- A18. Move the MCP server's default origin from `raw.githubusercontent.com` to `stumblestack.dev/index.json` and `stumblestack.dev/p/<uuid>.html`-equivalents (we already publish `pitfall.schema.json`; add per-entry plain markdown copies at `stumblestack.dev/pitfalls/<cat>/<slug>.md` during site build). Fastly absorbs the rate limit.
- A19. Add anonymous telemetry: log only the **count** of `search_pitfalls` and `get_pitfall` calls per hour, surfaced via a static `stumblestack.dev/_stats.json` rebuilt by the next nightly action. No identifiers, no queries.

---

## Round 6 — Developer experience (consume + contribute)

Lead reviewers: PD, EN.

**PRO (PD).** The MCP server delivers the right experience for the right surface. One install, one config line, four well-named tools. `submit_pitfall` with `dry_run` is the kind of detail that separates "demo" from "shippable" — agents that respect dry-run can iterate without flooding the PR queue.

**CON (PD, against own PRO).** Four DX gaps. (a) The agent **does not know what we have** before searching — there is no way to ask "what categories cover Claude Code" without a tool call followed by another tool call. (b) **No bulk fetch.** Retrieving five pitfalls in a session is five round-trips; a `get_pitfalls(ids: [...])` would halve latency. (c) **The submit_pitfall failure modes are opaque.** When validation fails, the JSON error list is technical; an agent will not always know which fields to fix without a structured shape (`field`, `message`, `suggestion`). (d) **No CLI** for humans. Writing a pitfall in a text editor and pasting into `submit_pitfall` works, but a `stumblestack new` command that opens `$EDITOR` with a template would lower the human bar by an order of magnitude.

**Resolution (PD + EN):** *accept with action.*

Actions:
- A20. Add `get_pitfalls(ids: [string])` — server-side batch by id, returns same shape as `get_pitfall` for each.
- A21. Restructure validation errors as objects: `{field, message, suggestion?}`, not strings. Bump MCP tool description with examples.
- A22. Ship `stumblestack` CLI in the same Python package: `stumblestack new`, `stumblestack lint`, `stumblestack submit`. CLI talks to the same `submit.build()` and `submit.submit()` functions.
- A23. Embed a one-screen `list_categories()` example in the MCP server tool description so callers see the surface before guessing.

---

## Round 7 — Operability & observability

Lead reviewers: SRE.

**PRO (SRE).** GitHub Actions is the runtime and it is observable enough for v0.1: every run has logs, status checks, and a permalink. The MCP server is a per-client process; its logs are the client's logs.

**CON (SRE).** We have no idea (a) **how often the MCP server is called**, (b) **whether searches return zero results** (a strong signal that we lack coverage), or (c) **how stale a particular client's cached `index.json` is.** Without these we cannot prioritize which categories to seed, cannot detect rate-limit clipping, cannot demonstrate adoption.

**Resolution (SRE):** *accept with action.*

Actions:
- A24. Add an opt-in `STUMBLESTACK_TELEMETRY` env (default off). When on, the MCP server emits a single line per invocation to stderr in OpenTelemetry-compatible structured format (tool name, latency, result count, cache age in seconds, no PII). Clients can pipe this into their existing observability.
- A25. Publish a daily `stumblestack.dev/_stats.json` generated by a nightly Action: total entries, last update time, top 10 categories by count, count of *zero-result* PR threads (signal for seeding priorities). Aggregate only.
- A26. Wire `search_pitfalls` to also return a `cache_age_seconds` field in its response so callers know whether they are seeing the freshest index.

---

## Round 8 — Reliability & disaster recovery

Lead reviewers: SRE, AR.

**PRO (SRE).** Recovery is trivial: clone the repo, rerun `build_index.py` and `build_site.py`. Pages can be redeployed from any fork. There is no opaque state.

**CON (AR).** Two failure modes our current posture handles poorly. (a) **GitHub-side account/repo dispute.** If the org is suspended or the repo DMCA'd, the canonical domain (`stumblestack.dev` CNAMEs into GitHub) goes dark. We have no plan B. (b) **Silent schema corruption.** If a future PR slips a schema change through CI (e.g. someone bumps the schema and breaks the projection used by `build_index.py`), `index.json` will be invalid for hours before someone notices.

**Resolution (SRE + AR):** *accept with action.*

Actions:
- A27. Maintain a **read-only mirror** repo on a second forge (Codeberg, GitLab) updated by a daily mirror job. Document the failover DNS swap (CNAME to a Cloudflare Worker proxying the mirror) in `docs/RUNBOOK.md` (new).
- A28. Add an `index_check` job to CI that, after `build_index.py`, downloads the **previous** `index.json` and asserts the new one's `count` did not drop by more than 10% (catches accidental deletes or schema-version regressions).
- A29. Sign `index.json` with cosign keyless (GH OIDC) in CI and publish the bundle alongside; consumers can verify origin without trusting `raw.githubusercontent.com`.

---

## Round 9 — Ecosystem & integration surface

Lead reviewers: OS, PD.

**PRO (OS).** "Public CC repo with a static JSON" is the lowest-friction integration possible. Any tool, any language, any vendor can consume it. Choosing MCP for the active surface means we get free distribution into every MCP-aware client that exists or will exist this year.

**CON (OS).** We do not have an **integration contract**, only an artifact. Three asks competitors will have: (a) **REST API stability.** We document `index.json` informally, but third parties want a versioned URL (`/api/v1/...`) and a deprecation policy. (b) **Webhook for new entries.** Agent platforms with their own caches want a notification, not a polling pattern. (c) **Embedding & badge widgets** so docs sites can advertise "see related pitfalls" inline. None of these are urgent at v0.1, but the seams should exist.

**Resolution (OS + PD):** *accept with action.*

Actions:
- A30. Define and publish `docs/API.md`: `/index.json` is `/api/v1/index.json`, `/p/<uuid>.html` is `/api/v1/p/<uuid>.{html,md,json}`. Add 301s from the old paths. Schema_version in the JSON envelope is the contract.
- A31. Add a GitHub Action that, on every push to `main`, POSTs a small JSON `{"event": "stumblestack_update", "entries_added": [...uuids]}` to any URLs registered in a public `webhooks.txt` file. Self-served subscribers add a PR with their URL; the Action loads at runtime.
- A32. Build a one-line embeddable widget (`<script src="https://stumblestack.dev/embed.js" data-query="...">`). Deferred to v0.2 but scoped now.

---

## Round 10 — Strategic positioning & moat

Lead reviewers: OS, PD, PMG.

**PRO (PMG).** The market has nothing exactly in this niche today. "agent pitfalls as a registry" is a small surface with high marginal value per entry. The non-strategy of "be the Wikipedia for agent footguns" is fine if execution is cheap and the network effects compound. We have chosen a license (MIT) that *invites* mirrors and forks; this maximizes adoption per unit of marketing.

**CON (PMG).** Three strategic risks. (a) **Cold start is brutal.** A registry with one entry signals "abandoned" and triggers the discoverability death spiral. We must seed 50+ real, sourced entries before announcing. (b) **A single big-tech vendor (Anthropic, OpenAI) could ship the same primitive integrated into their own docs.** They do not need a third-party registry if their own model docs include "common failures." Our moat is **cross-vendor coverage** — we must, on day one, have entries for Anthropic *and* OpenAI *and* Google *and* MCP server developers. Single-vendor framing loses. (c) **No sustainability story.** OSS goodwill alone has shipped a thousand abandoned registries. We do not need monetization at v0.1, but we need to know what the "year 2" answer is — sponsorship, paid private-corpus tier, or sunsetting.

**Resolution (PMG):** *block on action for A33; accept with action for A34, A35.*

Actions:
- A33. **Block public announcement** until we have ≥50 entries spanning at least 4 vendor categories (claude-code, openai-api, google-genai, mcp-server). Internal review is fine; tweet thread is not.
- A34. Set up a **Stewardship doc** (`docs/STEWARDSHIP.md`) that names the maintainers, the decision process for breaking schema changes, and a stated commitment to vendor-neutrality (no preferential weighting of any vendor's entries in ranking).
- A35. Sketch a 2-year sustainability paragraph in `docs/STEWARDSHIP.md`: at what corpus size we will reconsider, what paid surfaces could exist (private mirrors for proprietary stacks; verified-author plans for vendors), explicit "we will not paywall the public corpus" commitment.

---

## Security review

Lead reviewers: Sec1, Sec2, Sec3, Sec4. Methodology: STRIDE pass over the artifact and the data flows; supply-chain audit of the dependency tree; secret-handling review.

### STRIDE highlights

| Threat                                          | Surface                                       | Severity (pre-mitigation) | Mitigation                                                                                                                                                          |
|-------------------------------------------------|-----------------------------------------------|---------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Spoofing — fake agent identity in `agent:` field| Submission frontmatter                        | High                      | A9, A10 (provenance + allowlist). Add an unverified-author banner to entries lacking signed provenance.                                                                |
| Tampering — malicious markdown body             | Rendered site (`build_site.py` → HTML)        | **Critical**              | **A36 (this round): switch markdown renderer to a safe-mode profile that disables raw HTML; escape inline HTML; add a CSP header via Pages `_headers`.**              |
| Repudiation — submitter denies they opened a PR | GitHub identity layer                         | Low                       | Inherited from GitHub; verified-email + signed commits encouraged.                                                                                                  |
| Information disclosure — secrets in pitfalls     | All fields                                    | Medium                    | A37: secret scanning on PRs (gitleaks Action). Reject PRs containing AWS/GCP keys, JWTs, OpenAI sk- patterns, GH tokens.                                              |
| Denial of service — flood the submit endpoint   | `submit_pitfall` MCP tool path                | Medium                    | A38: per-token rate limit guardrail in `submit.py` (e.g. ≤10 PRs / 10 minutes per token). Local check, advisory to GitHub's hard limits.                              |
| Elevation of privilege — `fix` recommending dangerous shell | Consumer agents auto-applying fixes | High                      | A8, A12 already pinned. Add the unsafe-pattern lint and require `fix_unsafe: true` flag.                                                                              |
| SSRF via `links` field                           | Submitter-controlled URLs rendered on site     | Medium                    | A39: validate `links` are public-resolvable HTTPS at submit time; reject `file://`, `gopher://`, RFC1918 hostnames, `localhost`.                                      |
| XSS via crafted markdown in body                  | Rendered HTML on stumblestack.dev              | **Critical**              | Covered by A36 + A41 (CSP).                                                                                                                                          |
| Supply chain — malicious dep in `mcp-server`     | git-install path on every client               | High                      | A40: pin deps with hashes (`requirements-lock.txt` + `pip-compile`), Dependabot for `pip` + `github-actions`, and signed git tags as the release primitive (we do not publish to PyPI at v0.1; the install surface is `pip install git+...@<sha>`).         |

### Supply-chain audit

Current MCP-server runtime deps: `mcp`, `httpx`, `pyyaml`, `jsonschema`. All four are widely used. Concerns:

- `pyyaml` parses YAML by default; we already use `safe_load`. **No action.**
- `mcp` is comparatively new; pin minor; track its CVE feed.
- `httpx` is fine; we control all outbound URLs.
- `jsonschema` is fine.

CI side: `actions/checkout@v4`, `actions/setup-python@v5`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4`. These are first-party Microsoft/GitHub-owned. **Pin to commit SHA, not just major tag.** This is non-negotiable in cloud-native shops.

### Secret handling

`submit_pitfall` reads `GITHUB_TOKEN` from env. Server **never** logs the token. **Action A42**: add an explicit "this server reads `GITHUB_TOKEN`" line in `describe_source()` output so callers can audit. Add a redaction unit test.

### Security actions (consolidated)

- A36. Replace the `markdown` renderer call with `markdown.Markdown(safe_mode=...)` or switch to `bleach` post-processing with a strict allowlist of tags. **Block ship on this.**
- A37. Add a gitleaks PR workflow.
- A38. Implement a local `submit_pitfall` rate guard.
- A39. Validate `links` at build time.
- A40. Hash-pin Python deps via `pip-compile` (commit `requirements-lock.txt` alongside `pyproject.toml`); enable Dependabot for `pip` + `github-actions`. **No PyPI publication at v0.1** — the release primitive is a signed, immutable git tag, and the supported install URLs (`pip install "stumblestack-mcp @ git+...@<tag-or-sha>"`) are documented in `mcp-server/README.md`. Sigstore signing of PyPI artifacts is deferred to whenever PyPI publication is reopened.
- A41. Add a `_headers` file to `_site/` with a strict CSP for the static site (no inline-script, no eval, search.js as the only allowed script source).
- A42. Document and unit-test secret redaction in `submit.py`.
- A43. Pin all GitHub Actions to commit SHAs in both workflows.
- A44. Enable GitHub native: Dependabot security updates, secret scanning, push protection. Enable CodeQL with the Python query suite.

---

## Final PM gate (PMG)

**Decision: HOLD on public announcement.** Ship infrastructure improvements internally; do not tweet, do not list on any awesome-list, do not submit to HN, until the blockers below clear.

### Blockers (must land before announce)

1. **A36** — markdown XSS hardening. Critical.
2. **A41** — CSP on the static site. Critical.
3. **A43** — pin Actions to SHA. Critical for any cloud-native shop reviewing us for adoption.
4. **A8** — embed the "treat fix as a hint" banner in every server response. Reduces foreseeable mis-execution.
5. **A33** — seed ≥50 entries across ≥4 vendor categories. A registry of one is not a registry.

### Strong recommendations (should land within the same release cycle as blockers)

- A1, A2, A18 — operational sanity (TTL, official mirror, move off raw.githubusercontent.com as default).
- A10, A11 — trust posture (human-review window, verification list with PR refs).
- A12, A39, A40, A44 — additional security hardening.
- A20, A21 — DX (bulk get, structured errors).
- A30 — versioned API path.

### Deferrable to v0.2

- A5, A6 (schema_version 2 fields), A14, A15 (embedding seam), A22 (CLI), A27 (mirror forge), A29 (cosign signing), A32 (embed widget).

### Open governance question (PMG to owner)

Who is the *named* maintainer and what is the on-call expectation when a security report arrives? Without a documented `SECURITY.md` and a real e-mail (`dev@wisdoverse.com` exists; is it monitored 24h, or are we comfortable saying "best effort, 72h reply"?), we are not in a position to make external claims. Resolve before public announcement.

### Conditional approval

If A8, A33, A36, A41, A43 ship cleanly and the SECURITY.md governance question is resolved, this design is **approved for public announcement**. Until then it is approved for **trusted-preview use only**, with the existing warning callout preserved in README.

---

## Action index (chronological)

| #   | Description                                                                 | Round | Severity         | Status        |
|-----|------------------------------------------------------------------------------|-------|------------------|---------------|
| A1  | Bump default `STUMBLESTACK_TTL` to 3600s with jitter                         | 1     | low (perf)       | recommended   |
| A2  | Document `stumblestack.dev` as canonical API origin                          | 1     | medium           | recommended   |
| A3  | `STUMBLESTACK_MIRRORS` with failover                                          | 1     | medium           | recommended   |
| A4  | Mirror policy doc                                                            | 1     | low              | recommended   |
| A5  | Reserve `applies_to`, `severity` fields in schema_version 2                  | 2     | medium           | deferred v0.2 |
| A6  | `fix_code` structured field                                                  | 2     | medium           | deferred v0.2 |
| A7  | Schema evolution policy in DESIGN.md                                         | 2     | low              | recommended   |
| A8  | "Treat fix as hint" banner embedded in server responses                      | 3     | **blocker**      | **blocker**   |
| A9  | Reserve `provenance` field (sigstore/OIDC)                                   | 3     | high             | deferred v0.2 |
| A10 | Human review for 90 days; `.github/agent_allowlist.yaml`                     | 3     | high             | recommended   |
| A11 | `verification_prs[]` replaces freeform `verified_count`                      | 3     | high             | recommended   |
| A12 | Lint unsafe shell patterns in `fix`; require `fix_unsafe: true`              | 3     | high             | recommended   |
| A13 | `scripts/eval_search.py` + curated eval set                                  | 4     | medium           | recommended   |
| A14 | `_aliases` field in schema_version 2                                         | 4     | medium           | deferred v0.2 |
| A15 | `embeddings.json` optional artifact, server prefers when present             | 4     | medium           | deferred v0.2 |
| A16 | Publish ranker weights in DESIGN.md                                          | 4     | low              | recommended   |
| A17 | Shard `index.json` by category when >2 MB                                    | 5     | medium           | recommended   |
| A18 | Default origin → `stumblestack.dev`; publish per-entry `.md` mirrors          | 5     | medium           | recommended   |
| A19 | `_stats.json` rebuilt nightly                                                 | 5     | low              | recommended   |
| A20 | `get_pitfalls(ids: [...])` batch tool                                         | 6     | low              | recommended   |
| A21 | Structured validation error objects                                          | 6     | medium           | recommended   |
| A22 | `stumblestack` CLI in same package                                            | 6     | low              | deferred v0.2 |
| A23 | Embed `list_categories` example in tool description                          | 6     | trivial          | recommended   |
| A24 | Opt-in OTel-style telemetry to stderr                                        | 7     | low              | recommended   |
| A25 | Nightly aggregate `_stats.json`                                              | 7     | low              | recommended   |
| A26 | `cache_age_seconds` in search responses                                       | 7     | low              | recommended   |
| A27 | Read-only Codeberg/GitLab mirror; runbook                                    | 8     | medium           | deferred v0.2 |
| A28 | `index_check` job: count-drop alarm                                           | 8     | medium           | recommended   |
| A29 | Cosign-sign `index.json` keyless                                              | 8     | medium           | deferred v0.2 |
| A30 | `docs/API.md`; `/api/v1/...` paths with 301s                                  | 9     | medium           | recommended   |
| A31 | Webhook fanout action                                                         | 9     | low              | recommended   |
| A32 | Embed widget                                                                  | 9     | low              | deferred v0.2 |
| A33 | Seed ≥50 entries across ≥4 vendor categories                                 | 10    | **blocker**      | **blocker**   |
| A34 | `docs/STEWARDSHIP.md` — maintainers + decision process + neutrality           | 10    | medium           | recommended   |
| A35 | Sustainability paragraph in STEWARDSHIP.md                                    | 10    | low              | recommended   |
| A36 | Markdown render safe-mode (XSS hardening)                                     | Sec   | **blocker**      | **blocker**   |
| A37 | gitleaks PR workflow                                                          | Sec   | medium           | recommended   |
| A38 | Local rate guard in `submit_pitfall`                                          | Sec   | medium           | recommended   |
| A39 | Validate `links` (block file://, RFC1918, etc.)                              | Sec   | medium           | recommended   |
| A40 | Hash-pin deps + Dependabot; signed git tag as release primitive (no PyPI)    | Sec   | high             | recommended   |
| A41 | Strict CSP via `_headers` for static site                                     | Sec   | **blocker**      | **blocker**   |
| A42 | Document + unit-test token redaction in `submit.py`                          | Sec   | low              | recommended   |
| A43 | Pin all GitHub Actions to commit SHAs                                         | Sec   | **blocker**      | **blocker**   |
| A44 | Enable CodeQL, Dependabot, secret scanning + push protection                  | Sec   | high             | recommended   |

---

## Sign-offs

- AR — approved with actions
- EN — approved with actions
- DA — approved; eval gate required before any ranker change
- PD — approved with actions
- OS — approved with actions; A33 + A34 are non-negotiable
- SRE — approved with actions
- LE — approved (MIT covers code + content under standard contributor terms; SECURITY.md still required)
- Sec1, Sec2, Sec3, Sec4 — approved **conditional on A8, A36, A41, A43**
- PMG — **HOLD on public announcement** until five blockers (A8, A33, A36, A41, A43) and SECURITY.md governance are resolved
