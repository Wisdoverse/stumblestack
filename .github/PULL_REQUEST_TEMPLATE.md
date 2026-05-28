<!-- For a NEW PITFALL, you can use the pitfall template:
     append ?template=pitfall.md to the PR URL, or follow CONTRIBUTING.md. -->

## What

<!-- One line: what this PR changes. -->

## Why

<!-- The motivation / the trap it documents or the bug it fixes. -->

## Checklist

- [ ] `make check` passes locally (validate, index, eval, tests, lint)
- [ ] `index.json` regenerated and committed if I touched `pitfalls/` or `schemas/`
- [ ] If I changed the ranker (`search.py` / `eval_search.py` / `build_site.py` JS),
      all copies match and `test_ranker_parity` passes
- [ ] No secrets, no `fix` that should be auto-executed, links are public https
