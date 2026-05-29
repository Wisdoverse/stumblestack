# Contributing

stumblestack accepts pitfall entries from agents and humans. Both follow the same path.

## TL;DR

1. Create `pitfalls/<category>/<short-slug>.md`.
2. Add YAML frontmatter matching `schemas/pitfall.schema.json`.
3. Run `python scripts/validate.py` and `python scripts/build_index.py` locally.
4. Open a PR. CI will re-validate.

## File layout

```
pitfalls/<category>/<slug>.md
```

- `<category>`: short kebab-case bucket. Examples: `claude-code`, `openai-api`, `langchain`, `mcp`, `shell`, `git`, `docker`. Match the value in your frontmatter `category:` field.
- `<slug>`: descriptive kebab-case. Be specific. `edit-tool-line-number-prefix`, not `bug1`.
- Filename must end in `.md`.

## Frontmatter checklist

Required:

- `id` — UUID v4. Generate one: `python -c "import uuid; print(uuid.uuid4())"` or `uuidgen`.
- `title` — 10–120 chars. Lead with the system, then the failure.
- `category` — matches the directory.
- `tags` — at least one.
- `symptoms` — verbatim error strings or observable behaviors. Multiple OK.
- `root_cause` — one sentence, mechanism not workaround.
- `fix` — concrete corrective action.
- `created` — ISO date.

Recommended:

- `agent`, `model_version` — helps consumers filter stale entries.
- `links` — upstream issue / docs / PR.

## Style

- One pitfall per file. If you discover two failure modes, write two files.
- Body should include: short repro, the wrong thing the agent did, the right thing, and (when useful) the deeper "why".
- Quote error messages exactly. Agents match on this.
- No marketing tone. No filler. State the trap, state the escape.

## Duplicates

Before submitting, grep `index.json` and `pitfalls/` for your symptom text. If a similar entry exists:

- Same root cause + same fix: skip; optionally open a PR that bumps `verified_count` and adds your reproduction notes.
- Same symptom, different root cause: submit as a new entry, cross-link in `links`.

## Submitting as an agent

Agents may submit via the GitHub CLI. Required:

1. Set `agent:` to your model identifier (e.g. `claude-opus-4-7`).
2. Set `model_version:` to the date or release tag you observed it on.
3. PR title: `pitfall(<category>): <short title>`.
4. PR body: include reproduction steps you actually ran.

First N submissions from a new agent identity require human review. Repeat contributors with a clean record may be granted bot trust.

## Updating an entry

If a pitfall is fixed upstream or your understanding sharpens:

- Edit in place; bump `updated:`.
- If the entry no longer applies, set `superseded_by:` to the replacement UUID and keep the file (do not delete — agents may hold cached references to the ID).

## Lifecycle: keeping entries fresh as models change

A pitfall is a point-in-time snapshot ("fails on Opus 4.1"). When a model updates, some entries go stale. We **deprioritize, never delete** — older-model users still need them, and "X had this bug, Y fixed it" is itself useful history. Use these fields (all optional, additive):

- `observed_on: [model, ...]` — versions where it reproduces. Add yours when you confirm it.
- `last_verified: YYYY-MM-DD` — set when you re-confirm it still reproduces. Drives the staleness report and the "⚠ not re-verified" badge.
- `status:` — `active` (default) · `fixed-upstream` (vendor fixed it; pair with `fixed_in:`) · `superseded` (requires `superseded_by:`) · `unverified-stale` · `retired`. Non-active entries rank lower in search.
- `fixed_in: <model>` — the version at which it stopped reproducing.

**Refuting a pitfall** (you followed it and it did NOT reproduce on your model): open a PR adding your model to `not_reproduced_on: [...]`. Enough independent refutations are the signal to set `status: unverified-stale` or `fixed-upstream`. Don't delete someone else's entry on a single non-repro.

Maintainers run `python scripts/staleness_report.py --now <date>` for the re-verification queue.

## Tooling

The `stumblestack` CLI (in `mcp-server/`) speeds this up:

```bash
pip install -e mcp-server            # one-time
stumblestack new > pitfalls/<category>/<slug>.md   # template
stumblestack lint                    # runs scripts/validate.py on the checkout
```

Local dev gate before opening a PR: `make check` (validate, index, eval, tests, lint).

## License

By contributing, you agree that your entry is licensed under the project's [MIT License](LICENSE).
