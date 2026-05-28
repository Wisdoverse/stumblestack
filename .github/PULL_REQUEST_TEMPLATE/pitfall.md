<!-- Adding a pitfall. See CONTRIBUTING.md. One pitfall per file at
     pitfalls/<category>/<slug>.md. CI will validate against the schema. -->

## Pitfall

- **System / category:**
- **What goes wrong (symptoms):**
- **Root cause (one sentence):**
- **Fix:**

## Reproduction

<!-- The steps you actually ran. -->

## Checklist

- [ ] One `.md` file under `pitfalls/<category>/<slug>.md` with valid frontmatter
- [ ] Symptoms are verbatim error text where possible
- [ ] `fix` is a hint, not something an agent should blindly execute
      (if it must show a dangerous shell pattern, set `fix_unsafe: true`)
- [ ] Ran `python3 scripts/validate.py` (or `stumblestack lint`) — passes
- [ ] Regenerated `index.json` (`python3 scripts/build_index.py`)
- [ ] Checked for duplicates (searched existing symptoms)
