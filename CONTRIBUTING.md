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

## License

By contributing, you agree your entry is dedicated to the public domain under CC0.
